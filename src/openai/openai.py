import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_fixed

from src.settings import Metrics, settings
from src.utils.apikey import ApiKeyMetrics, MultiApiKeyProcessor
from src.utils.requests_async import async_get


class UsageBucket(BaseModel):
    """Model for OpenAI usage bucket"""

    object: str
    start_time: int
    end_time: int
    results: List[Dict[str, Any]]


class UsageResponse(BaseModel):
    """Response model for OpenAI usage API"""

    object: str
    data: List[UsageBucket]
    has_more: bool
    next_page: Optional[str] = None


class CostAmount(BaseModel):
    """Model for cost amount"""

    value: float
    currency: str


class CostResult(BaseModel):
    """Model for cost result"""

    object: str
    amount: CostAmount
    line_item: Optional[str] = None
    project_id: Optional[str] = None


class CostBucket(BaseModel):
    """Model for cost bucket"""

    object: str
    start_time: int
    end_time: int
    results: List[CostResult]


class CostResponse(BaseModel):
    """Response model for OpenAI costs API"""

    object: str
    data: List[CostBucket]
    has_more: bool
    next_page: Optional[str] = None


class ProjectApiKey(BaseModel):
    """Model for OpenAI Project API Key"""

    object: str
    id: str
    name: str
    created_at: int
    owner: Optional[Dict[str, Any]] = None
    redacted_value: str


class ProjectApiKeysResponse(BaseModel):
    """Response model for OpenAI Project API Keys list"""

    object: str
    data: List[ProjectApiKey]
    first_id: Optional[str] = None
    last_id: Optional[str] = None
    has_more: bool


class OpenAiUsage:
    def __init__(self, admin_api_key: str) -> None:
        self.admin_api_key = admin_api_key
        self.base_url = "https://api.openai.com/v1"
        self.days = 1
        self._api_key_id_cache: Dict[str, str] = {}

    async def get_usage_data(
        self, endpoint: str, api_key_ids: Optional[List[str]] = None
    ) -> UsageResponse:
        """Get usage data from OpenAI API for a specific endpoint"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=self.days)

        url = f"{self.base_url}/organization/usage/{endpoint}"

        params = {
            "start_time": int(start_time.timestamp()),
            "end_time": int(end_time.timestamp()),
            "bucket_width": "1d",
            "limit": 7,
        }

        if api_key_ids:
            # Use the mapped API key IDs to filter usage data
            params["api_key_ids"] = api_key_ids
            params["group_by"] = ["api_key_id"]

        headers = {
            "Authorization": f"Bearer {self.admin_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "apikey-usage-inspector/1.0",
        }

        try:
            response = await async_get(url, headers=headers, params=params)

            if response.status == 200:
                data = await response.json()
                logger.debug(
                    f"OpenAI {endpoint} usage response: {len(data.get('data', []))} buckets"
                )
                if settings.debug_enabled:
                    logger.debug(f"OpenAI {endpoint} usage data: {data}")

                await asyncio.sleep(1)  # Respect OpenAI rate limits
                return UsageResponse(**data)
            else:
                error_text = await response.text()
                logger.warning(
                    f"OpenAI {endpoint} usage API error {response.status}: {error_text}"
                )
                raise Exception(
                    f"API request failed with status {response.status}: {error_text}"
                )

        except Exception as e:
            logger.warning(f"Error getting OpenAI {endpoint} usage: {e}")
            raise

    async def get_costs_data(self) -> CostResponse:
        """Get cost data from OpenAI API"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=self.days)

        url = f"{self.base_url}/organization/costs"

        params = {
            "start_time": int(start_time.timestamp()),
            "end_time": int(end_time.timestamp()),
            "bucket_width": "1d",
            "limit": 7,
        }

        headers = {
            "Authorization": f"Bearer {self.admin_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "apikey-usage-inspector/1.0",
        }

        try:
            response = await async_get(url, headers=headers, params=params)

            if response.status == 200:
                data = await response.json()
                logger.debug(
                    f"OpenAI costs response: {len(data.get('data', []))} buckets"
                )
                if settings.debug_enabled:
                    logger.debug(f"OpenAI costs data: {data}")
                return CostResponse(**data)
            else:
                error_text = await response.text()
                logger.warning(
                    f"OpenAI costs API error {response.status}: {error_text}"
                )
                raise Exception(
                    f"API request failed with status {response.status}: {error_text}"
                )

        except Exception as e:
            logger.error(f"Error getting OpenAI costs: {e}")
            raise

    async def get_input_tokens(
        self, endpoint: str, api_key_ids: List[str], count_field: str = "input_tokens"
    ) -> int:
        total_requests = 0
        input_tokens = 0

        completions_usage = await self.get_usage_data(endpoint, api_key_ids)
        for bucket in completions_usage.data:
            for result in bucket.results:
                total_requests += result.get("num_model_requests", 0)
                input_tokens += result.get(count_field, 0)

        logger.debug(
            f"OpenAI completions usage: {total_requests} requests, {input_tokens} tokens, apikey_ids: {[f'{a[:10]}...{a[-4:]}' for a in api_key_ids]}"
        )
        return input_tokens

    @retry(stop=stop_after_attempt(settings.openaiSettings.retry_attempts), wait=wait_fixed(settings.openaiSettings.retry_delay))
    async def get_single_api_key_metrics(self, api_key: str) -> ApiKeyMetrics:
        """Get metrics for a single OpenAI API key using the organization usage API"""
        key_id = (
            f"{api_key[:10]}...{api_key[-4:]}"
            if len(api_key) > 14
            else f"{api_key[:8]}..."
        )

        try:
            # First, try to map the API key to its ID
            api_key_mapping = await self.map_api_keys_to_ids([api_key])
            api_key_ids = list(api_key_mapping.values()) if api_key_mapping else None
            if not api_key_ids:
                raise Exception(f"Could not map API key {key_id} to any API key ID")

            # Get usage data for different endpoints
            total_requests = 0
            total_tokens = 0
            usage_details: dict[str, int] = {}

            # Try to get completions usage (most common)
            try:
                input_tokens = await self.get_input_tokens("completions", api_key_ids)
                usage_details["completions"] = input_tokens
                total_tokens += input_tokens
            except Exception as e:
                logger.warning(f"Could not get completions usage: {e}")
                raise e

            # Try to get embeddings usage
            # try:
            #     input_tokens = await self.get_input_tokens("embeddings", api_key_ids)
            #     usage_details["embeddings"] = input_tokens
            #     total_tokens += input_tokens
            # except Exception as e:
            #     logger.debug(f"Could not get embeddings usage: {e}")

            # Try to get moderations usage
            # try:
            #     input_tokens = await self.get_input_tokens("moderations", api_key_ids)
            #     usage_details["moderations"] = input_tokens
            #     total_tokens += input_tokens
            # except Exception as e:
            #     logger.debug(f"Could not get moderations usage: {e}")

            # Try to get images usage
            # try:
            #     images = await self.get_input_tokens(
            #         "images", api_key_ids, count_field="images"
            #     )
            #     usage_details["images"] = images
            # except Exception as e:
            #     logger.debug(f"Could not get images usage: {e}")

            # Try to get audio speeches usage
            # try:
            #     characters = await self.get_input_tokens(
            #         "audio_speeches", api_key_ids, count_field="characters"
            #     )
            #     usage_details["audio_speeches"] = characters
            # except Exception as e:
            #     logger.debug(f"Could not get audio speeches usage: {e}")

            # Try to get audio transcriptions usage
            # try:
            #     seconds = await self.get_input_tokens(
            #         "audio_transcriptions", api_key_ids, count_field="seconds"
            #     )
            #     usage_details["audio_transcriptions"] = seconds
            # except Exception as e:
            #     logger.debug(f"Could not get audio transcriptions usage: {e}")

            return ApiKeyMetrics(
                key_id=key_id,
                usage=total_tokens,
                limit=0,  # OpenAI doesn't provide limit info via API
                success=True,
                extra={
                    "total_tokens": total_tokens,
                    "api_endpoint": "organization/usage/*",
                    "estimated_limit": True,
                    "usage_available": True,
                    "validation_status": "valid",
                    "usage_details": usage_details,
                    "api_key_ids": api_key_ids,
                },
            )

        except Exception as e:
            logger.warning(f"Error getting metrics for OpenAI API key {key_id}: {e}")
            raise e

    async def get_projects_api_keys_metadata(self):
        # Try to list projects first (this may fail if admin key doesn't have project access)
        try:
            projects_url = f"{self.base_url}/organization/projects"
            headers = {
                "Authorization": f"Bearer {self.admin_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "apikey-usage-inspector/1.0",
            }

            response = await async_get(projects_url, headers=headers)
            if response.status == 200:
                projects_data = await response.json()
                projects = projects_data.get("data", [])

                # Search through each project's API keys
                for project in projects:
                    project_id = project.get("id")
                    if not project_id:
                        continue

                    try:
                        project_keys = await self.get_project_api_keys(project_id)

                        # Look for matching redacted value
                        for key_info in project_keys.data:
                            redacted_value = key_info.redacted_value
                            key_suffix = redacted_value[-4:]

                            self._api_key_id_cache[key_suffix] = key_info.id

                        logger.debug(
                            f"Found {len(project_keys.data)} API keys for project {project_id}"
                        )

                    except Exception as e:
                        raise Exception(
                            f"Failed to get API keys for project {project_id}: {e}"
                        )

            else:
                logger.debug(f"Could not list projects: {response.status}")

        except Exception as e:
            raise Exception(
                f"Failed to access OpenAI projects API. Please check your admin API key. {e}"
            )

        logger.info(
            f"OpenAI project API keys metadata loaded, {self._api_key_id_cache} keys cached"
        )

    @retry(stop=stop_after_attempt(settings.openaiSettings.retry_attempts), wait=wait_fixed(settings.openaiSettings.retry_delay))
    async def get_project_api_keys(self, project_id: str) -> ProjectApiKeysResponse:
        """Get list of API keys for a specific project"""
        url = f"{self.base_url}/organization/projects/{project_id}/api_keys"

        headers = {
            "Authorization": f"Bearer {self.admin_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await async_get(url, headers=headers)

            if response.status == 200:
                data = await response.json()
                logger.debug(
                    f"OpenAI project API keys response: {len(data.get('data', []))} keys"
                )

                await asyncio.sleep(1)  # Respect OpenAI rate limits
                return ProjectApiKeysResponse(**data)
            else:
                error_text = await response.text()
                logger.warning(
                    f"OpenAI project API keys error {response.status}: {error_text}"
                )
                raise Exception(
                    f"API request failed with status {response.status}: {error_text}"
                )

        except Exception as e:
            logger.error(f"Error getting OpenAI project API keys: {e}")
            raise

    async def map_api_keys_to_ids(self, api_keys: List[str]) -> Dict[str, str]:
        """
        Map a list of API keys to their corresponding IDs
        Returns dict mapping api_key -> api_key_id
        """
        key_id_mapping = {}

        for api_key in api_keys:
            try:
                key_suffix = api_key[-4:]
                api_key_id = self._api_key_id_cache.get(key_suffix)
                if api_key_id:
                    key_id_mapping[api_key] = api_key_id
                else:
                    logger.warning(f"Could not map API key to ID: {api_key[:10]}...")
            except Exception as e:
                logger.error(f"Error mapping API key {api_key[:10]}...: {e}")
                continue

        return key_id_mapping


@retry(stop=stop_after_attempt(settings.openaiSettings.retry_attempts), wait=wait_fixed(settings.openaiSettings.retry_delay))
async def start() -> List[Metrics]:
    """Main entry point for OpenAI usage collection"""
    if not settings.openaiSettings.enabled:
        logger.info("🤖 OpenAI monitoring is disabled")
        return [
            Metrics(
                usage=0,
                limit=0,
                provider="openai",
                extra={"status": "disabled", "key_id": "disabled"},
            )
        ]

    try:
        # Get API keys from settings
        api_keys = settings.openaiSettings.api_keys
        admin_api_keys = settings.openaiSettings.admin_api_keys
        usage = OpenAiUsage(admin_api_key=admin_api_keys[0])

        all_results: List[Metrics] = []

        # Process regular API keys to get their usage
        if api_keys:
            logger.info(f"Processing {len(api_keys)} OpenAI API keys for usage")

            await usage.get_projects_api_keys_metadata()
            not_inspect_apikeys = set(usage._api_key_id_cache.keys()) - set([key[-4:] for key in api_keys])
            if not_inspect_apikeys:
                logger.warning(
                    f"Some API keys do not have metadata: {not_inspect_apikeys}..."
                )

            # Use the multi-API key processor for parallel processing
            processor = MultiApiKeyProcessor(
                provider_name="openai",
                single_key_processor=usage.get_single_api_key_metrics,
            )

            api_key_metrics = await processor.process_multiple_keys(api_keys)

            total_usage = sum(metric.usage for metric in api_key_metrics)
            if total_usage == 0:
                raise Exception("Total usage is zero, cannot calculate percent usage")

            # Calculate total costs for all API keys
            total_cost_usd = 0.0
            try:
                costs_data = await usage.get_costs_data()
                for bucket in costs_data.data:
                    for result in bucket.results:
                        total_cost_usd += result.amount.value
            except Exception as e:
                logger.debug(f"Could not get costs data: {e}")
                raise e

            # calculate the percent usage of the total cost
            for metric in api_key_metrics:
                if metric.extra and not metric.extra.get("success", False):
                    logger.warning(
                        f"Skipping API key {metric.key_masked} due to previous errors"
                    )
                    continue

                all_results.append(
                    Metrics(
                        usage=int(total_cost_usd * (metric.usage / total_usage)),
                        limit=metric.limit,
                        key_masked=metric.key_masked,
                        provider="openai",
                        extra={
                            "total_cost_usd": total_cost_usd,
                            "usage": metric.usage,
                            "total_usage": total_usage,
                        },
                    )
                )

        if not all_results:
            raise Exception("No valid API keys configured for OpenAI")

        return all_results

    except Exception as e:
        logger.error(f"Error in OpenAI start function: {e}")
        raise e


if __name__ == "__main__":

    async def main():
        print("\n=== OpenAI API Key Usage Test ===")
        try:
            results = await start()
            print(f"Results: {len(results)} metrics")
            for result in results:
                print(result)
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(main())
