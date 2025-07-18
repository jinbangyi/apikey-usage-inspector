import asyncio
from typing import Optional

from loguru import logger
from pydantic import BaseModel
from tenacity import retry
from tenacity import stop_after_attempt, wait_fixed

from src.utils.apikey import ApiKeyMetrics, MultiApiKeyProcessor
from src.settings import Metrics, settings
from src.utils.requests_async import async_get


class KeyInfo(BaseModel):
    plan: dict
    usage: dict

    @property
    def current_month_usage(self) -> int:
        """Extract current month usage from key info"""
        return self.usage.get("current_month", {}).get("credits_used", 0)

    @property
    def monthly_credit_limit(self) -> Optional[int]:
        """Extract monthly credit limit from key info"""
        return self.plan.get("credit_limit_monthly", None)

    @property
    def plan_name(self) -> Optional[str]:
        """Extract plan name from key info"""
        return self.plan.get("name", None)


class KeyInfoResponse(BaseModel):
    status: dict
    data: KeyInfo

    @property
    def is_success(self) -> bool:
        """Check if the response is successful"""
        return self.status.get("error_code") == 0


async def get_cmc_key_info(api_key: str) -> KeyInfoResponse:
    """Get CMC API key information including usage and limits"""
    api_url = "https://pro-api.coinmarketcap.com/v1/key/info"

    headers = {
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    }

    response = await async_get(api_url, headers=headers, verify_ssl=True)

    if response.status == 200:
        data = await response.json()
        if settings.debug_enabled:
            logger.debug(f"CMC key info response: {data}")
        return KeyInfoResponse(**data)
    else:
        text = await response.text()
        raise Exception(f"Error fetching key info: {response.status} - {text}")


async def get_single_api_key_metrics(api_key: str) -> ApiKeyMetrics:
    """Get metrics for a single API key"""
    key_id = (
        api_key[:10] + "..." + api_key[-4:]
        if len(api_key) > 14
        else api_key[:8] + "..."
    )

    try:
        # Get key information
        key_info_result = await get_cmc_key_info(api_key)

        if not key_info_result.is_success:
            error_msg = key_info_result.status.get("error_message", "Unknown error")
            raise Exception(f"API error: {error_msg}")

        if settings.debug_enabled:
            logger.debug(f"CMC key info for {key_id}: {key_info_result}")

        # Extract current month usage and limit
        current_usage = key_info_result.data.current_month_usage
        credit_limit = key_info_result.data.monthly_credit_limit

        if credit_limit is None or credit_limit <= 0:
            raise Exception(f"Invalid credit limit for API key {key_id}")

        logger.info(
            f"CMC API key {key_id}: {current_usage}/{credit_limit} credits used"
        )

        if settings.debug_enabled:
            logger.debug(
                f"CMC current usage for {key_id}: {current_usage}, limit: {credit_limit}"
            )

        return ApiKeyMetrics(
            key_id=key_id,
            usage=current_usage,
            limit=credit_limit,
            success=True,
            extra={
                "plan_name": key_info_result.data.plan_name,
                "api_endpoint": "v1/key/info",
            },
        )

    except Exception as e:
        logger.error(f"Error getting metrics for API key {key_id}: {e}")
        raise e
        # return ApiKeyMetrics(
        #     key_id=key_id, usage=0, limit=0, success=False, error=str(e)
        # )


@retry(stop=stop_after_attempt(settings.cmcSettings.retry_attempts), wait=wait_fixed(settings.cmcSettings.retry_delay))
async def start() -> list[Metrics]:
    """Main function to get CMC usage metrics"""
    try:
        # Get API keys from settings
        api_keys = settings.cmcSettings.api_keys

        if not api_keys:
            raise Exception("No valid API keys configured for CMC")

        # Create processor instance
        processor = MultiApiKeyProcessor("coinmarketcap", get_single_api_key_metrics)

        # Process all API keys and return metrics
        metrics = await processor.process_multiple_keys(api_keys)
        metrics = [
            m for m in metrics if m.extra and m.extra.get("success", False)
        ]
        return metrics

    except Exception as e:
        logger.error(f"Error in CMC start function: {e}")
        raise


if __name__ == "__main__":
    result = asyncio.run(start())
    logger.debug(result)
