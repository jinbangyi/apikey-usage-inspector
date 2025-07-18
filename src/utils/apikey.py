import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional

from loguru import logger

from src.settings import Metrics


@dataclass
class ApiKeyMetrics:
    """Container for metrics from a single API key"""

    key_id: str  # Masked API key for identification
    usage: int
    limit: int
    success: bool
    error: Optional[str] = None
    extra: Optional[dict] = None


class MultiApiKeyProcessor:
    """
    A general class for processing multiple API keys concurrently and returning metrics.

    This class takes a function that processes a single API key and returns metrics,
    then applies it to multiple keys concurrently and aggregates the results.
    """

    def __init__(
        self,
        provider_name: str,
        single_key_processor: Callable[[str], Awaitable[ApiKeyMetrics]],
    ):
        """
        Initialize the processor.

        Args:
            provider_name: Name of the API provider (e.g., "coinmarketcap")
            single_key_processor: Async function that takes an API key and returns ApiKeyMetrics
        """
        self.provider_name = provider_name
        self.single_key_processor = single_key_processor

    async def process_multiple_keys(self, api_keys: List[str]) -> List[Metrics]:
        """
        Process multiple API keys concurrently and return a list of Metrics.

        Args:
            api_keys: List of API keys to process

        Returns:
            List of Metrics objects, one for each API key
        """
        if not api_keys:
            raise Exception(f"No valid API keys provided for {self.provider_name}")

        logger.info(f"{self.provider_name}: Processing {len(api_keys)} API keys...")

        # Process all keys concurrently
        tasks = [self.single_key_processor(key) for key in api_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert results to Metrics objects
        metrics_list = []
        successful_count = 0
        failed_count = 0

        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                # Handle exceptions that occurred during processing
                key_id = self._mask_api_key(api_keys[i])
                logger.error(f"Exception processing API key {key_id}: {result}")

                metrics_list.append(
                    Metrics(
                        usage=0,
                        limit=0,
                        key_masked=key_id,
                        provider=self.provider_name,
                        extra={
                            "api_key_id": key_id,
                            "success": False,
                            "error": str(result),
                        },
                    )
                )
                failed_count += 1
            else:
                # Handle successful results
                api_key_metrics: ApiKeyMetrics = result

                if api_key_metrics.success:
                    successful_count += 1
                    logger.info(
                        f"{self.provider_name} API key {api_key_metrics.key_id}: "
                        f"{api_key_metrics.usage}/{api_key_metrics.limit} credits used"
                    )
                else:
                    failed_count += 1
                    logger.warning(
                        f"{self.provider_name} API key {api_key_metrics.key_id} failed: "
                        f"{api_key_metrics.error}"
                    )

                # Create extra info
                extra_info = {
                    "api_key_id": api_key_metrics.key_id,
                    "success": api_key_metrics.success,
                    "error": api_key_metrics.error,
                }

                # Add any additional extra info from the API key metrics
                if api_key_metrics.extra:
                    extra_info.update(api_key_metrics.extra)

                metrics_list.append(
                    Metrics(
                        usage=api_key_metrics.usage,
                        limit=api_key_metrics.limit,
                        key_masked=api_key_metrics.key_id,
                        provider=self.provider_name,
                        extra=extra_info,
                    )
                )

        # Log summary
        logger.info(
            f"{self.provider_name} processing complete: "
            f"{successful_count} successful, {failed_count} failed"
        )

        return metrics_list

    def _mask_api_key(self, api_key: str) -> str:
        """
        Mask an API key for safe logging.

        Args:
            api_key: The API key to mask

        Returns:
            Masked API key string
        """
        if len(api_key) > 14:
            return api_key[:10] + "..." + api_key[-4:]
        else:
            return api_key[:8] + "..."

    async def process_single_key_with_masking(self, api_key: str) -> ApiKeyMetrics:
        """
        Wrapper that adds automatic key masking to single key processing.

        Args:
            api_key: The API key to process

        Returns:
            ApiKeyMetrics with masked key_id
        """
        try:
            result = await self.single_key_processor(api_key)
            # Ensure the key_id is properly masked
            if result.key_id == api_key:  # If processor didn't mask it
                result.key_id = self._mask_api_key(api_key)
            return result
        except Exception as e:
            return ApiKeyMetrics(
                key_id=self._mask_api_key(api_key),
                usage=0,
                limit=0,
                success=False,
                error=str(e),
            )


# Convenience function for creating a processor
def create_api_key_processor(
    provider_name: str, single_key_processor: Callable[[str], Awaitable[ApiKeyMetrics]]
) -> MultiApiKeyProcessor:
    """
    Create a MultiApiKeyProcessor instance.

    Args:
        provider_name: Name of the API provider
        single_key_processor: Function that processes a single API key

    Returns:
        MultiApiKeyProcessor instance
    """
    return MultiApiKeyProcessor(provider_name, single_key_processor)
