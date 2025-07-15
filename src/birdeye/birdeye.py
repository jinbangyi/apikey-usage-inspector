import asyncio
from typing import Optional

from loguru import logger
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_fixed

from src.settings import Metrics, settings
from src.utils.requests_async import async_get, async_post


class RateLimit(BaseModel):
    second: int
    minute: int


class Plan(BaseModel):
    level: int
    monthlyUnits: int
    name: str
    price: int
    pricePerUnit: Optional[float] = None
    stripeUsagePriceId: Optional[str] = None
    monthlyWsUnits: Optional[int] = None
    pricePerWsUnit: Optional[float] = None
    stripeApiUsagePriceId: Optional[str] = None
    isUsageCombined: bool
    id: str


class Subscription(BaseModel):
    id: str = Field(alias="_id")
    plan: Plan
    status: str
    currentPeriodStartAt: str
    currentPeriodEndAt: str


class PlanInfo(BaseModel):
    rateLimit: RateLimit
    wsConnectionLimit: int


class AccountInfo(BaseModel):
    id: str
    stripeCustomerId: str
    name: str
    planInfo: PlanInfo
    subscription: Subscription
    isSuspended: bool


class AccountInfoResponse(BaseModel):
    success: bool
    data: AccountInfo


class UsageData(BaseModel):
    usage: int
    api_usage: int
    ws_usage: int
    csv_usage: int
    has_overage: bool


class UsageDataResponse(BaseModel):
    success: bool
    data: UsageData


async def get_birdeye_usage(subscription_id: str, token: str) -> UsageDataResponse:
    birdeye_url = f"https://multichain-api.birdeye.so/payments/subscriptions/{subscription_id}/usage"

    response = await async_get(
        birdeye_url,
        params={"token": token},
        headers={
            "origin": "https://bds.birdeye.so",
            "referer": "https://bds.birdeye.so/",
            "accept": "application/json, text/plain, */*",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0 Safari/537.36",
        },
        verify_ssl=False,
    )
    if response.status == 200:
        data = await response.json()
        return UsageDataResponse(**data)
    else:
        text = await response.text()
        raise Exception(f"Error: {response.status} - {text}")


async def birdeye_login(email: str, password: str):
    birdeye_url = "https://multichain-api.birdeye.so/user/login"

    response = await async_post(
        birdeye_url,
        json={"email": email, "password": password},
        headers={
            "origin": "https://bds.birdeye.so",
            "referer": "https://bds.birdeye.so/",
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0 Safari/537.36",
        },
        verify_ssl=False,
    )

    text = await response.text()
    if settings.debug_enabled:
        with open("birdeye_login_response.txt", "w") as f:
            f.write(text)

    if response.status == 200:
        data = await response.json()
        if "token" in data:
            return data["token"]
        else:
            raise Exception("Login failed, no token returned.")
    else:
        raise Exception(f"Error: {response.status} - {text}")


async def get_birdeye_monthly_max_usage(token: str) -> AccountInfoResponse:
    birdeye_url = "https://multichain-api.birdeye.so/accounts/default"

    response = await async_get(
        birdeye_url,
        params={"token": token},
        headers={
            "origin": "https://bds.birdeye.so",
            "referer": "https://bds.birdeye.so/",
            "accept": "application/json, text/plain, */*",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0 Safari/537.36",
        },
        verify_ssl=False,
    )
    text = await response.text()
    logger.debug(text)
    if response.status == 200:
        data = await response.json()
        return AccountInfoResponse(**data)
    else:
        raise Exception(f"Error: {response.status} - {text}")


@retry(stop=stop_after_attempt(settings.birdeyeSettings.retry_attempts), wait=wait_fixed(settings.birdeyeSettings.retry_delay))
async def start() -> Metrics:
    token = await birdeye_login(
        settings.birdeyeSettings.email,
        settings.birdeyeSettings.password,
    )
    logger.debug(f"Birdeye token: {token}")
    monthly_usage = await get_birdeye_monthly_max_usage(token)
    usage = await get_birdeye_usage(monthly_usage.data.subscription.id, token)

    _temp = {
        "usage": usage,
        "monthly_usage": monthly_usage,
    }
    logger.debug(_temp)

    return Metrics(
        usage=usage.data.usage,
        limit=monthly_usage.data.subscription.plan.monthlyUnits,
        provider="birdeye",
    )


if __name__ == "__main__":
    result = asyncio.run(start())
    logger.debug(result)
