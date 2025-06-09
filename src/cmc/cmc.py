import asyncio
from dataclasses import dataclass
from typing import List, Optional, TypedDict

from loguru import logger
from pydantic import BaseModel, Field

from src.settings import Metrics, settings
from src.utils.requests_async import async_get


@dataclass
class TokenMetrics:
    """Container for metrics from a single session token"""

    token_id: str  # First 20 chars of token for identification
    usage: int
    limit: int
    success: bool
    error: Optional[str] = None


class AggregatedMetrics(TypedDict):
    total_usage: int
    total_limit: int
    successful_tokens: int
    failed_tokens: int
    failed_token_ids: List[str]


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


class KeyPlan(BaseModel):
    plan: dict


class PlanInfo(BaseModel):
    keyPlan: Optional[KeyPlan] = Field(default=None)

    @property
    def monthly_call_credit_limit(self) -> Optional[int]:
        """Extract monthly credit limit from plan info"""
        if self.keyPlan and self.keyPlan.plan:
            return self.keyPlan.plan.get("limit_monthly")
        return None

    @property
    def plan_name(self) -> Optional[str]:
        """Extract plan name from plan info"""
        if self.keyPlan and self.keyPlan.plan:
            return self.keyPlan.plan.get("label")
        return None


class PlanInfoResponse(BaseModel):
    success: bool = True
    data: Optional[PlanInfo] = Field(default=None)


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


async def get_cmc_plan_info(session_token: str) -> PlanInfoResponse:
    """Get CMC API plan information including limits"""
    plan_url = "https://portal-api.coinmarketcap.com/v1/accounts/my/plan/info"

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

    response = await async_get(plan_url, headers=headers, verify_ssl=False)

    if response.status == 200:
        data = await response.json()
        if settings.debug_enabled:
            logger.debug(f"CMC plan info response: {data}")

        # Parse the data properly to extract the plan info
        if data and "keyPlan" in data:
            plan_info = PlanInfo(**data)
            return PlanInfoResponse(success=True, data=plan_info)
        else:
            logger.warning("No keyPlan found in CMC plan info response")
            return PlanInfoResponse(success=False, data=None)
    else:
        text = await response.text()
        logger.warning(f"Error fetching plan info: {response.status} - {text}")
        return PlanInfoResponse(success=False, data=None)


async def get_single_token_metrics(session_token: str) -> TokenMetrics:
    """Get metrics for a single session token"""
    token_id = session_token[:20] + "..."

    try:
        # Get usage statistics and plan info concurrently
        usage_stats_result, plan_info_result = await asyncio.gather(
            get_cmc_usage(session_token),
            get_cmc_plan_info(session_token),
            return_exceptions=True,
        )

        if isinstance(usage_stats_result, BaseException):
            raise Exception(
                f"Error fetching usage stats for token {token_id}: {usage_stats_result}"
            )

        # Type narrow usage_stats to ensure it's not an exception
        usage_stats: UsageStats = usage_stats_result

        if settings.debug_enabled:
            logger.debug(f"CMC usage stats for {token_id}: {usage_stats}")
            logger.debug(f"CMC plan info for {token_id}: {plan_info_result}")

        # Extract current month usage
        current_usage = usage_stats.month.credits_used

        # Try to get the limit from plan info first
        plan_limit = None
        if (
            isinstance(plan_info_result, PlanInfoResponse)
            and plan_info_result.success
            and plan_info_result.data
        ):
            plan_limit = plan_info_result.data.monthly_call_credit_limit

        # Use plan limit if available
        if plan_limit and plan_limit > 0:
            limit = plan_limit
            logger.info(f"CMC limit obtained from plan info for {token_id}: {limit}")
        else:
            raise Exception(f"Failed to retrieve CMC plan limit for token {token_id}")

        if settings.debug_enabled:
            logger.debug(
                f"CMC current usage for {token_id}: {current_usage}, limit: {limit}"
            )

        return TokenMetrics(
            token_id=token_id, usage=current_usage, limit=limit, success=True
        )

    except Exception as e:
        raise Exception(f"Error getting metrics for token {token_id}: {e}")


async def get_multi_token_metrics(session_tokens: List[str]) -> List[TokenMetrics]:
    """Get metrics for multiple session tokens concurrently"""
    logger.info(f"Getting metrics for {len(session_tokens)} CMC session tokens...")

    # Get metrics for all tokens concurrently
    tasks = [get_single_token_metrics(token) for token in session_tokens]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and handle any exceptions
    token_metrics = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Exception getting metrics for token {result}")
        else:
            token_metrics.append(result)

    return token_metrics


async def start() -> list[Metrics]:
    """Main function to get CMC usage metrics"""
    try:
        # Get session tokens from settings
        session_tokens = settings.cmcSettings.session_tokens

        if not session_tokens:
            raise Exception("No valid session tokens configured for CMC")

        # Multiple tokens mode
        logger.info(
            f"CMC multi-token mode: processing {len(session_tokens)} session tokens"
        )

        # Get metrics for all tokens
        token_metrics = await get_multi_token_metrics(session_tokens)
        ret: list[Metrics] = []

        for metric in token_metrics:
            logger.info(
                f"Token {metric.token_id} - Usage: {metric.usage}, Limit: {metric.limit}, Success: {metric.success}"
            )
            ret.append(
                Metrics(
                    usage=metric.usage,
                    limit=metric.limit,
                    key_masked=metric.token_id,
                    provider="coinmarketcap",
                    extra={
                        "token_id": metric.token_id,
                        "success": metric.success,
                        "error": metric.error,
                    },
                )
            )

        return ret

    except Exception as e:
        logger.error(f"Error in CMC start function: {e}")
        raise


if __name__ == "__main__":
    result = asyncio.run(start())
    logger.debug(result)
