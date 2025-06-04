import asyncio

from loguru import logger
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from src.birdeye.birdeye import start as birdeye_start
from src.quicknode.quicknode import start as quicknode_start
from src.settings import settings

registry = CollectorRegistry()

_default_description = """
provider: birdeye, cmc, quicknode, etc.
name: there exists multi apikeys in one provider
category: diff provider may have different usage calculation
"""
cron_apikey_usage = Gauge(
    "cron_apikey_usage",
    "provider apikey usage" + _default_description,
    ["provider", "name", "category"],
    registry=registry,
)
cron_apikey_usage_percent = Gauge(
    "cron_apikey_usage_percent",
    "provider apikey usage percent" + _default_description,
    ["provider", "name", "category"],
    registry=registry,
)
cron_apikey_limit = Gauge(
    "cron_apikey_limit",
    "provider apikey limit" + _default_description,
    ["provider", "name", "category"],
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
        logger.info("📊 Fetching metrics from both Birdeye and QuickNode APIs...")

        # Use asyncio.gather to run both API calls concurrently
        tasks = await asyncio.gather(
            birdeye_start(), quicknode_start(),
            return_exceptions=True
        )

        for task in tasks:
            if isinstance(task, BaseException):
                logger.error(f"❌ Error fetching data: {task}")
                continue
            logger.debug(f"✅ Successfully fetched data: {task}")

            cron_apikey_usage.labels(
                provider=task.provider, name="default", category="default"
            ).set(task.usage)
            cron_apikey_limit.labels(
                provider=task.provider, name="default", category="default"
            ).set(task.limit)
            cron_apikey_usage_percent.labels(
                provider=task.provider, name="default", category="default"
            ).set(round(task.usage / task.limit, 2))

    except Exception as e:
        logger.error(f"❌ Unexpected error during metrics generation: {e}")

    logger.info("📊 Metrics generation completed")


async def start():
    try:
        logger.info("🚀 Starting metrics generation and pushing...")
        await generate_metrics()

        if settings.push_gateway_enabled:
            push_metrics()

        logger.info([i for i in registry.collect()])
        logger.info("✔️ Metrics generation and pushing completed successfully")
    except Exception as e:
        logger.exception(
            f"❌ An error occurred during metrics generation or pushing: {e}"
        )


if __name__ == "__main__":
    asyncio.run(start())
