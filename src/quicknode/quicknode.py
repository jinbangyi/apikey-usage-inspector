from typing import Optional
import requests
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from loguru import logger

class Settings(BaseSettings):
    quicknode_console_apikey: str = "YOUR_QUICKNODE_API_KEY"  # Default value, can be overridden by .env file

    class Config:
        env_file = ".env"  # Specify the .env file to load environment variables from

settings = Settings()
if settings.quicknode_console_apikey == "YOUR_QUICKNODE_API_KEY":
    logger.error("QuickNode API key is not set. Please set it in the .env file or directly in the code.")

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
    overages: Optional[int]
    start_time: int
    end_time: int


def start():
    # Replace with your actual QuickNode URL
    quicknode_url = "https://api.quicknode.com/v0/usage/rpc"
    # read from .env file
    # Ensure you have the QuickNode API key set in your environment or .env file
    quicknode_console_apikey = settings.quicknode_console_apikey

    # Example request to get the latest block number
    response = requests.get(
        quicknode_url,
        params={
            'start_time': '',
            'end_time': '',
        },
        headers={
            'x-api-key': quicknode_console_apikey,
            'accept': 'application/json',
        }
    )

    if response.status_code == 200:
        # Parse the response JSON into a Pydantic model
        data = QuickNodeResponse(**response.json().get('data', {}))
        return data
    else:
        logger.error(f"Error: {response.status_code} - {response.text}")
        return None


if __name__ == "__main__":
    logger.debug(start())
