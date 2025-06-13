from typing import List, Optional

from loguru import logger
from pydantic import BaseModel

from src.settings import Metrics, settings
from src.utils.apikey import ApiKeyMetrics, MultiApiKeyProcessor
from src.utils.requests_async import async_get


class TwitterAPIUsageResponse(BaseModel):
    """Response model for TwitterAPI usage information"""

    recharge_credits: int


class TwitterAPIErrorResponse(BaseModel):
    """Error response model for TwitterAPI"""

    error: Optional[str] = None
    message: Optional[str] = None


async def get_twitterapi_usage(api_key: str) -> TwitterAPIUsageResponse:
    """Get TwitterAPI usage information using the API key"""
    url = "https://api.twitterapi.io/oapi/my/info"

    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "apikey-usage-inspector/1.0",
    }

    response = await async_get(url, headers=headers)

    if response.status == 200:
        data = await response.json()
        return TwitterAPIUsageResponse(**data)
    else:
        error_text = await response.text()
        raise Exception(f"TwitterAPI request failed: {response.status} - {error_text}")


async def get_single_api_key_metrics(api_key: str) -> ApiKeyMetrics:
    """Get metrics for a single TwitterAPI key"""
    key_id = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"

    try:
        # Get TwitterAPI usage information
        usage_response = await get_twitterapi_usage(api_key)

        remaining_credits = usage_response.recharge_credits
        logger.info(f"TwitterAPI key {key_id}: {remaining_credits} remaining credits")

        return ApiKeyMetrics(
            key_id=key_id,
            usage=0,  # TwitterAPI doesn't provide explicit usage info
            limit=remaining_credits,  # Using remaining credits as the limit
            success=True,
            extra={
                "recharge_credits": remaining_credits,
                "api_endpoint": "oapi/my/info",
                "status": "active",
            },
        )

    except Exception as e:
        logger.error(f"Error getting metrics for TwitterAPI key {key_id}: {e}")
        raise e
        # return ApiKeyMetrics(
        #     key_id=key_id,
        #     usage=0,
        #     limit=0,
        #     success=False,
        #     error=str(e),
        # )


async def start(retry_count=0) -> List[Metrics]:
    try:
        # Get API keys from settings
        api_keys = settings.twitterAPISettings.api_keys

        if not api_keys:
            raise Exception("No valid API keys configured for TwitterAPI")

        # Create processor instance
        processor = MultiApiKeyProcessor("twitterapi", get_single_api_key_metrics)

        # Process all API keys and return metrics
        return await processor.process_multiple_keys(api_keys)

    except Exception as e:
        logger.error(f"Error in TwitterAPI start function: {e}")
        if retry_count < 2:
            logger.warning(f"Retrying TwitterAPI metrics collection ({retry_count + 1}/3)...")
            return await start(retry_count + 1)
        else:
            logger.error("Max retries reached for TwitterAPI metrics collection")
        raise


if __name__ == "__main__":
    import asyncio

    async def main():
        results = await start()
        print(f"TwitterAPI Metrics ({len(results)} keys):")
        for i, result in enumerate(results, 1):
            print(f"  Key {i}: {result}")

    asyncio.run(main())
