from typing import List, Optional

from loguru import logger
from pydantic import BaseModel, Field

from src.settings import Metrics, settings
from src.utils.requests_async import async_get


class TwitterAPIUsageResponse(BaseModel):
    """Response model for TwitterAPI usage information"""

    recharge_credits: int


class TwitterAPIErrorResponse(BaseModel):
    """Error response model for TwitterAPI"""

    error: Optional[str] = None
    message: Optional[str] = None


class APIKeyMetrics(BaseModel):
    """Model for individual API key metrics"""

    api_key: str
    api_key_masked: str
    usage_response: Optional[TwitterAPIUsageResponse] = None
    error: Optional[str] = None


async def get_twitterapi_usage(api_key: str) -> TwitterAPIUsageResponse:
    """Get TwitterAPI usage information using the API key"""
    url = "https://api.twitterapi.io/oapi/my/info"

    # Mask the API key for logging (show first 8 and last 4 characters)
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"

    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "apikey-usage-inspector/1.0",
    }

    logger.info(f"🐦 Getting TwitterAPI usage information for key: {masked_key}...")

    try:
        response = await async_get(url, headers=headers)

        if response.status == 200:
            data = await response.json()
            logger.success(
                f"✅ TwitterAPI usage retrieved for {masked_key}: {data.get('recharge_credits', 0)} credits"
            )
            return TwitterAPIUsageResponse(**data)
        else:
            error_text = await response.text()
            logger.error(
                f"❌ TwitterAPI request failed for {masked_key}: {response.status} - {error_text}"
            )
            raise Exception(
                f"TwitterAPI request failed: {response.status} - {error_text}"
            )

    except Exception as e:
        logger.error(f"❌ Error getting TwitterAPI usage for {masked_key}: {str(e)}")
        raise


async def get_usage_for_all_keys() -> List[APIKeyMetrics]:
    """Get usage information for all configured API keys"""
    api_keys = settings.twitterAPISettings.api_keys
    logger.info(f"🐦 Processing {len(api_keys)} TwitterAPI key(s)...")

    results = []

    for api_key in api_keys:
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"

        try:
            usage_response = await get_twitterapi_usage(api_key)
            results.append(
                APIKeyMetrics(
                    api_key=api_key,
                    api_key_masked=masked_key,
                    usage_response=usage_response,
                )
            )
        except Exception as e:
            logger.error(f"❌ Failed to get usage for key {masked_key}: {str(e)}")
            results.append(
                APIKeyMetrics(api_key=api_key, api_key_masked=masked_key, error=str(e))
            )

    return results


async def start() -> List[Metrics]:
    """Main entry point for TwitterAPI usage collection - returns metrics for all keys"""
    if not settings.twitterAPISettings.enabled:
        logger.info("🐦 TwitterAPI monitoring is disabled")
        return [
            Metrics(
                usage=0,
                limit=0,
                provider="twitterapi",
                extra={"status": "disabled", "key_id": "disabled"},
            )
        ]

    try:
        # Get usage for all configured API keys
        all_key_metrics = await get_usage_for_all_keys()

        metrics_list = []

        for i, key_metrics in enumerate(all_key_metrics):
            if key_metrics.error:
                # Handle error case
                logger.error(
                    f"❌ Error for key {key_metrics.api_key_masked}: {key_metrics.error}"
                )
            else:
                # Handle successful case
                if key_metrics.usage_response:
                    remaining_credits = key_metrics.usage_response.recharge_credits
                    logger.info(
                        f"📊 TwitterAPI Metrics for {key_metrics.api_key_masked} - Remaining Credits: {remaining_credits}"
                    )

                    metrics_list.append(
                        Metrics(
                            usage=0,  # We don't have explicit usage info from the API
                            limit=remaining_credits,  # Using remaining credits as the limit
                            provider="twitterapi",
                            key_masked=key_metrics.api_key_masked,
                            extra={
                                "recharge_credits": remaining_credits,
                                "status": "active",
                                "key_id": f"key_{i + 1}",
                            },
                        )
                    )
                else:
                    # This shouldn't happen if there's no error, but handle it gracefully
                    logger.warning(
                        f"⚠️  No usage response for key {key_metrics.api_key_masked}"
                    )

        logger.info(f"📊 Successfully processed {len(metrics_list)} TwitterAPI key(s)")
        return metrics_list

    except Exception as e:
        logger.warning(f"❌ Failed to get TwitterAPI metrics: {str(e)}")
        raise e


# Backward compatibility function for single key usage
async def start_single() -> Metrics:
    """Backward compatibility function that returns only the first key's metrics"""
    metrics_list = await start()
    return (
        metrics_list[0]
        if metrics_list
        else Metrics(
            usage=0,
            limit=0,
            provider="twitterapi",
            extra={"status": "no_keys", "key_id": "none"},
        )
    )


if __name__ == "__main__":
    import asyncio

    async def main():
        results = await start()
        print(f"TwitterAPI Metrics ({len(results)} keys):")
        for i, result in enumerate(results, 1):
            print(f"  Key {i}: {result}")

    asyncio.run(main())
