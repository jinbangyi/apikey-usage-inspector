import asyncio

from loguru import logger
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from src.birdeye.birdeye import start as birdeye_start
from src.cmc.cmc import start as cmc_start
from src.openai.openai import start as openai_start
from src.quicknode.quicknode import start as quicknode_start
from src.settings import Metrics, settings
from src.twitterapi.twitterapi import start as get_twitterapi_metrics

registry = CollectorRegistry()

# API key usage metrics
apikey_requests_used_total = Gauge(
    "apikey_requests_used_total",
    "Total number of API requests used for the given API key",
    ["exported_service", "key_type", "usage_calculation"],
    registry=registry,
)

apikey_requests_remaining_total = Gauge(
    "apikey_requests_remaining_total",
    "Total number of API requests remaining for the given API key",
    ["exported_service", "key_type", "usage_calculation"],
    registry=registry,
)

apikey_usage_ratio = Gauge(
    "apikey_usage_ratio",
    "Ratio of used requests to total limit (0.0 to 1.0)",
    ["exported_service", "key_type", "usage_calculation"],
    registry=registry,
)

apikey_requests_limit_total = Gauge(
    "apikey_requests_limit_total",
    "Total number of API requests allowed for the given API key",
    ["exported_service", "key_type", "usage_calculation"],
    registry=registry,
)


def push_metrics():
    """Push metrics to the Prometheus Pushgateway."""
    try:
        push_to_gateway(
            settings.push_gateway_url, job=settings.push_gateway_job, registry=registry
        )
        logger.info("✔️ Metrics pushed successfully to Pushgateway")
    except Exception as e:
        logger.error(f"❌ Failed to push metrics: {e}")


async def generate_metrics():
    """Generate metrics from Birdeye and QuickNode APIs using batched requests."""
    logger.info("🔄 Fetching usage data from APIs...")

    # Batch fetch metrics from both APIs concurrently
    try:
        logger.info(
            "📊 Fetching metrics from Birdeye, QuickNode, CMC, OpenAI, and TwitterAPI APIs..."
        )

        # Use asyncio.gather to run both API calls concurrently
        pre_tasks = [
            {
                "function": birdeye_start,
                "enabled": settings.birdeyeSettings.enabled,
            },
            {
                "function": quicknode_start,
                "enabled": settings.quickNodeSettings.enabled,
            },
            {
                "function": cmc_start,
                "enabled": settings.cmcSettings.enabled,
            },
            {
                "function": openai_start,
                "enabled": settings.openaiSettings.enabled,
            },
            {
                "function": get_twitterapi_metrics,
                "enabled": settings.twitterAPISettings.enabled,
            },
        ]
        future_tasks = [task["function"]() for task in pre_tasks if task["enabled"]]
        tasks: list[Metrics | list[Metrics] | BaseException] = await asyncio.gather(
            *future_tasks, return_exceptions=True
        )
        logger.info("📊 Metrics fetched successfully from APIs")

        # Flatten the results - some providers return List[Metrics], others return Metrics
        all_metrics: list[Metrics] = []
        for task in tasks:
            if isinstance(task, BaseException):
                logger.error(f"❌ Error fetching data: {task}")
                continue
            elif isinstance(task, list):
                # Handle providers that return List[Metrics] (like TwitterAPI with multiple keys)
                all_metrics.extend(task)
                logger.debug(
                    f"✅ Successfully fetched {len(task)} metric(s) from provider"
                )
            else:
                # Handle providers that return single Metrics object
                all_metrics.append(task)
                logger.debug(f"✅ Successfully fetched data: {task}")

        for metric in all_metrics:
            if metric.provider == "quicknode":
                usage_calc = "monthly_credits"  # Credits with monthly reset
            elif metric.provider == "birdeye":
                usage_calc = "monthly_credits"
            elif metric.provider == "coinmarketcap":
                usage_calc = "monthly_credits"
            elif metric.provider == "openai":
                usage_calc = "monthly_credits"  # OpenAI usage in credits/tokens
            elif metric.provider == "twitterapi":
                usage_calc = "long_period_package"  # Using a long period package
            else:
                usage_calc = "unknown"  # Fallback for unknown services

            key_type = metric.key_masked if metric.key_masked else "primary"

            if usage_calc == "monthly_credits":
                apikey_requests_used_total.labels(
                    exported_service=metric.provider,
                    key_type=key_type,
                    usage_calculation=usage_calc,
                ).set(metric.usage)
                apikey_requests_limit_total.labels(
                    exported_service=metric.provider,
                    key_type=key_type,
                    usage_calculation=usage_calc,
                ).set(metric.limit)
                apikey_usage_ratio.labels(
                    exported_service=metric.provider,
                    key_type=key_type,
                    usage_calculation=usage_calc,
                ).set(round(metric.usage / metric.limit, 4))
                apikey_requests_remaining_total.labels(
                    exported_service=metric.provider,
                    key_type=key_type,
                    usage_calculation=usage_calc,
                ).set(metric.limit - metric.usage)
            elif usage_calc == "long_period_package":
                apikey_requests_remaining_total.labels(
                    exported_service=metric.provider,
                    key_type=key_type,
                    usage_calculation=usage_calc,
                ).set(metric.limit - metric.usage)

    except Exception as e:
        logger.error(f"❌ Unexpected error during metrics generation: {e}")

    logger.info("📊 Metrics generation completed")


async def start():
    try:
        logger.info("🚀 Starting metrics generation and pushing...")
        await generate_metrics()

        if settings.push_gateway_enabled:
            push_metrics()

        # Display collected metrics in a beautiful format
        logger.info("📋 Collected Prometheus Metrics Summary:")
        logger.info("=" * 60)

        for metric_family in registry.collect():
            logger.info(f"📊 Metric: {metric_family.name}")
            logger.info(f"   Type: {metric_family.type}")
            logger.info(f"   Help: {metric_family.documentation}")

            for sample in metric_family.samples:
                labels_str = (
                    ", ".join([f"{k}={v}" for k, v in sample.labels.items()])
                    if sample.labels
                    else "no labels"
                )
                logger.info(f"   └── {sample.name}({labels_str}) = {sample.value}")

            logger.info("-" * 40)

        logger.info("✔️ Metrics generation and pushing completed successfully")
    except Exception as e:
        logger.exception(
            f"❌ An error occurred during metrics generation or pushing: {e}"
        )


if __name__ == "__main__":
    asyncio.run(start())
