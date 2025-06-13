from typing import List, Optional

from loguru import logger
from pydantic import BaseModel

from src.settings import Metrics, settings
from src.utils.apikey import ApiKeyMetrics, MultiApiKeyProcessor
from src.utils.requests_async import async_get


class CoinGeckoUsageResponse(BaseModel):
    """Response model for CoinGecko usage information"""
    plan: str
    rate_limit_request_per_minute: int
    monthly_call_credit: int
    current_total_monthly_calls: int
    current_remaining_monthly_calls: int


async def get_coingecko_usage(api_key: str) -> CoinGeckoUsageResponse:
    """Get CoinGecko usage information using the API key"""
    url = "https://pro-api.coingecko.com/api/v3/key"

    headers = {
        "x-cg-pro-api-key": api_key,
        "Accept": "application/json",
        "User-Agent": "apikey-usage-inspector/1.0",
    }

    response = await async_get(url, headers=headers)

    if response.status == 200:
        data = await response.json()
        return CoinGeckoUsageResponse(**data)
    else:
        error_text = await response.text()
        raise Exception(f"CoinGecko request failed: {response.status} - {error_text}")


async def get_single_api_key_metrics(api_key: str) -> ApiKeyMetrics:
    """Get metrics for a single CoinGecko API key"""
    key_id = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"

    try:
        # Get CoinGecko usage information
        usage_response = await get_coingecko_usage(api_key)

        total_credits = usage_response.monthly_call_credit
        remaining_credits = usage_response.current_remaining_monthly_calls
        used_credits = total_credits - remaining_credits

        logger.info(
            f"CoinGecko key {key_id}: {used_credits}/{total_credits} credits used, {remaining_credits} remaining"
        )

        return ApiKeyMetrics(
            key_id=key_id,
            usage=used_credits,
            limit=total_credits,
            success=True,
            extra={
                "monthly_total_calls": used_credits,
                "monthly_call_credit": total_credits,
                "monthly_remaining_credits": remaining_credits,
                "api_endpoint": "v3/account",
                "status": "active",
            },
        )

    except Exception as e:
        logger.error(f"Error getting metrics for CoinGecko key {key_id}: {e}")
        raise e


async def start(retry_count=0) -> List[Metrics]:
    try:
        # Get API keys from settings
        api_keys = settings.coingeckoSettings.api_keys

        if not api_keys:
            raise Exception("No valid API keys configured for CoinGecko")

        # Create processor instance
        processor = MultiApiKeyProcessor("coingecko", get_single_api_key_metrics)

        # Process all API keys and return metrics
        return await processor.process_multiple_keys(api_keys)

    except Exception as e:
        logger.error(f"Error in CoinGecko start function: {e}")
        if retry_count < 2:
            logger.warning(
                f"Retrying CoinGecko metrics collection ({retry_count + 1}/3)..."
            )
            return await start(retry_count + 1)
        else:
            logger.error("Max retries reached for CoinGecko metrics collection")
        raise


if __name__ == "__main__":
    import asyncio

    async def main():
        results = await start()
        print(f"CoinGecko Metrics ({len(results)} keys):")
        for i, result in enumerate(results, 1):
            print(f"  Key {i}: {result}")

    asyncio.run(main())
