import asyncio
from typing import Optional

from loguru import logger
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_fixed

from src.settings import Metrics, settings
from src.utils.requests_async import async_get

"""
https://www.quicknode.com/docs/console-api/usage/v0-usage-rpc
data
    object
    The data object which contains the following fields:
        credits_used
            integer
            The number of credits used within the specified time period
        credits_remaining
            integer
            The number of credits remaining in the account
        limit
            integer
            The maximum number of credits available
        overages
            integer
            The number of credits used beyond the limit
        start_time
            integer
            The start timestamp for the usage data in second in second
        end_time
            integer
            The end timestamp for the usage data in second in second
error
    string
    A string containing an error message, if any issues occur during the request
"""


class QuickNodeResponse(BaseModel):
    credits_used: int
    credits_remaining: int
    limit: int
    overages: Optional[int] = None
    start_time: int
    end_time: int


@retry(stop=stop_after_attempt(settings.quickNodeSettings.retry_attempts), wait=wait_fixed(settings.quickNodeSettings.retry_delay))
async def start() -> Metrics:
    # Replace with your actual QuickNode URL
    quicknode_url = "https://api.quicknode.com/v0/usage/rpc"
    # read from .env file
    # Ensure you have the QuickNode API key set in your environment or .env file
    quicknode_console_apikey = settings.quickNodeSettings.console_apikey

    # Example request to get the latest block number
    response = await async_get(
        quicknode_url,
        params={
            "start_time": "",
            "end_time": "",
        },
        headers={
            "x-api-key": quicknode_console_apikey,
            "accept": "application/json",
        },
    )

    if response.status == 200:
        # Parse the response JSON into a Pydantic model
        response_json = await response.json()
        data = QuickNodeResponse(**response_json.get("data", {}))
        logger.debug(f"QuickNode data: {data}")
        logger.info(
            f"QuickNode usage: {data.credits_used} credits used, {data.limit} limit"
        )
        return Metrics(
            usage=data.credits_used,
            limit=data.limit,
            provider="quicknode",
        )
    else:
        text = await response.text()
        logger.error(f"QuickNode request failed: {response.status} - {text}")
        raise Exception(f"Failed to fetch QuickNode data: {response.status} - {text}")


if __name__ == "__main__":
    result = asyncio.run(start())
    logger.debug(result)
