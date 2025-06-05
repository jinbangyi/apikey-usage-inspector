import asyncio
import json
import urllib.parse
from typing import Optional

from loguru import logger
from pydantic import BaseModel, Field

from src.settings import Metrics, settings
from src.utils.requests_async import async_get, async_post


class DayStats(BaseModel):
    credits_used: int
    total_calls_count: int
    unique_calls_count: int


class ApiCall(BaseModel):
    date: str
    ip: str
    httpCode: str
    url: str
    credits: int
    elapsed: int


class UsageStats(BaseModel):
    day: DayStats
    yesterday: DayStats
    month: DayStats
    last_month: DayStats
    unique_ips: list
    last_api_calls: list[ApiCall]


class LoginResponse(BaseModel):
    success: bool = True
    session_token: Optional[str] = None


async def cmc_login(email: str, password: str) -> str:
    """Login to CoinMarketCap and return session cookie"""
    login_url = "https://portal-api.coinmarketcap.com/v1/login"

    # Device info for the login request
    device_info = {
        "screen_resolution": "1920,1080",
        "available_screen_resolution": "1920,1040",
        "system_version": "Windows 10",
        "brand_model": "unknown",
        "system_lang": "zh-CN",
        "timezone": "GMT+8",
        "timezoneOffset": -480,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "list_plugin": "PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF",
        "canvas_code": "ef66438d",
        "webgl_vendor": "Google Inc. (AMD)",
        "webgl_renderer": "ANGLE (AMD, AMD Radeon(TM) Graphics (0x00001638) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "audio": "124.04347527516074",
        "platform": "Win32",
        "web_timezone": "Asia/Shanghai",
        "device_name": "Chrome V137.0.0.0 (Windows)",
        "fingerprint": "164641f59763f3fe3b7e66cc38b66dd0",
    }

    login_data = {
        "email": email,
        "password": password,
        "captcha": "captcha#a6eb2bc80e40462c84abba7373d54441-sNkbAyoyObIWPUQmrPVzQcZ4x8Khdjsum1E4u4SKpE0aIIOd",
        "securityId": "b6ad8e08033a4fa4af0a224b9ff8bd4a",
        "deviceInfo": json.dumps(device_info),
        "fvideoId": "335fe043b6fc960292e0a5f451ee21212b6b4492",
    }

    headers = {
        "accept": "application/json",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": "Basic Og==",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "origin": "https://pro.coinmarketcap.com",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://pro.coinmarketcap.com/",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "x-requested-with": "xhr",
    }

    response = await async_post(
        login_url, json=login_data, headers=headers, verify_ssl=False
    )

    if settings.debug_enabled:
        text = await response.text()
        with open("cmc_login_response.txt", "w") as f:
            f.write(text)

    if response.status == 200:
        # Extract session cookie from response headers
        cookies = response.headers.get("set-cookie", "")
        if "s=" in cookies:
            # Extract the session token from the cookie
            session_start = cookies.find("s=") + 2
            session_end = cookies.find(";", session_start)
            if session_end == -1:
                session_end = len(cookies)
            session_token = cookies[session_start:session_end]
            return session_token
        else:
            raise Exception("Login failed, no session cookie returned.")
    else:
        text = await response.text()
        raise Exception(f"Login error: {response.status} - {text}")


async def get_cmc_usage(session_token: str) -> UsageStats:
    """Get CMC API usage statistics"""
    usage_url = "https://portal-api.coinmarketcap.com/v1/accounts/my/plan/stats"

    # Prepare cookies including the session token
    cookies = f"s={session_token}; OptanonAlertBoxClosed=2024-10-08T04:33:37.283Z; OTGPPConsent=DBABLA~BVQqAAAACgA.QA"

    headers = {
        "accept": "application/json",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": "Basic Og==",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "cookie": cookies,
        "origin": "https://pro.coinmarketcap.com",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://pro.coinmarketcap.com/",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "x-requested-with": "xhr",
    }

    response = await async_get(usage_url, headers=headers, verify_ssl=False)

    if response.status == 200:
        data = await response.json()
        return UsageStats(**data)
    else:
        text = await response.text()
        raise Exception(f"Error fetching usage stats: {response.status} - {text}")


async def start() -> Metrics:
    """Main function to get CMC usage metrics"""
    try:
        # Login to get session token
        session_token = await cmc_login(
            settings.cmcSettings.cmc_email, settings.cmcSettings.cmc_password
        )
        logger.debug(f"CMC session token obtained: {session_token[:20]}...")

        # Get usage statistics
        usage_stats = await get_cmc_usage(session_token)

        if settings.debug_enabled:
            logger.debug(f"CMC usage stats: {usage_stats}")

        # Extract current month usage and assume a reasonable limit
        # Note: CMC doesn't seem to provide the limit in the response,
        # so we'll need to determine this based on the plan
        current_usage = usage_stats.month.credits_used

        # Common CMC plan limits (credits per month)
        # Basic: 10,000 credits
        # Hobbyist: 20,000 credits
        # Startup: 100,000 credits
        # Standard: 300,000 credits
        # Professional: 1,000,000 credits
        # Enterprise: 3,000,000+ credits

        # We'll estimate the limit based on usage patterns
        # If usage is very high, assume higher tier plan
        estimated_limit = 10000  # Default to basic plan
        if current_usage > 500000:
            estimated_limit = 1000000  # Professional
        elif current_usage > 100000:
            estimated_limit = 300000  # Standard
        elif current_usage > 50000:
            estimated_limit = 100000  # Startup
        elif current_usage > 15000:
            estimated_limit = 20000  # Hobbyist

        return Metrics(
            usage=current_usage, limit=estimated_limit, provider="coinmarketcap"
        )

    except Exception as e:
        logger.error(f"Error in CMC start function: {e}")
        raise


if __name__ == "__main__":
    result = asyncio.run(start())
    logger.debug(result)
