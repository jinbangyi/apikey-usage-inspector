import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
from loguru import logger
from pydantic import BaseModel, Field, computed_field, field_validator

from src.settings import Metrics, settings
from src.utils.google_oauth import GoogleOAuthClient, GoogleOAuthError, OAuthConfig


class UserInfo(BaseModel):
    """User information model"""

    id: int
    api_key: str
    recharge_credits: int
    qps: int
    unused_bonuses_credits: int


class CreditLogs(BaseModel):
    """Credit consumption logs model"""

    free_credits_used: int
    paid_credits_used: int
    api_calls_count: int
    data_items_count: int


class CreditBonus(BaseModel):
    """Credit bonus model"""

    credits: int
    bonus_type: str
    promotion_code: Optional[str] = None
    description: str
    status: str
    created_at: str
    expires_at: str
    credits_unused: int


class CreditRecharge(BaseModel):
    """Credit recharge model"""

    transaction_id: str
    amount: float
    credits: int
    bonus_credits: int
    payment_method: str
    status: str
    created_at: str
    fail_msg: Optional[str] = None
    stripe_pay_url: Optional[str] = None


class APICall(BaseModel):
    """API call log model"""

    endpoint_path: str
    request_params: str
    response_data: str
    cost: int
    data_count: int
    min_cost: int
    request_time: str
    response_time: str
    time_cost_millisecond: int


class UserData(BaseModel):
    """Complete user data model"""

    user_info: UserInfo
    user_credit_bonuses: List[CreditBonus]
    user_credit_consume_logs_30min: CreditLogs
    user_credit_consume_logs_1hour: CreditLogs
    user_credit_consume_logs_1day: CreditLogs
    user_credit_consume_logs_7day: CreditLogs
    user_credit_consume_logs_30day: CreditLogs
    credit_recharges: List[CreditRecharge]
    user_api_calls: List[APICall]


class UserInfoResponse(BaseModel):
    """User info API response model"""

    status: str
    data: UserData

    @field_validator("status")
    @classmethod
    def status_must_be_success(cls, v: str) -> str:
        if v != "success":
            raise ValueError("API response status must be success")
        return v


class AuthSession(BaseModel):
    """Auth session model"""

    user: Dict[str, Any]
    expires: str
    accessToken: str


class CreditBalance(BaseModel):
    """Credit balance summary model"""

    recharge_credits: int = Field(ge=0, description="Credits purchased/recharged")
    unused_bonuses_credits: int = Field(ge=0, description="Unused bonus credits")
    free_credits_used_30day: int = Field(
        ge=0, description="Free credits used in last 30 days"
    )
    paid_credits_used_30day: int = Field(
        ge=0, description="Paid credits used in last 30 days"
    )
    api_calls_count_30day: int = Field(
        ge=0, description="API calls made in last 30 days"
    )

    @computed_field
    @property
    def total_available(self) -> int:
        """Calculate total available credits"""
        return self.recharge_credits + self.unused_bonuses_credits


class TwitterAPIClient:
    """Async client for TwitterAPI.io with Google OAuth support"""

    def __init__(self):
        """Initialize the client with settings"""
        self.settings = settings.twitterAPIOauthSettings
        self.session_token: Optional[str] = settings.twitterAPIOauthSettings.session_token
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info("TwitterAPI async client initialized")

    async def __aenter__(self):
        """Async context manager entry"""
        await self._create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()

    async def _create_session(self):
        """Create aiohttp session with proper headers and cookies"""
        timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout)

        # Set up cookies if session token is available
        jar = aiohttp.CookieJar()
        if self.session_token:
            from yarl import URL

            jar.update_cookies(
                {"next-auth.session-token": self.session_token},
                response_url=URL(self.settings.base_url),
            )

        self.session = aiohttp.ClientSession(
            timeout=timeout,
            cookie_jar=jar,
            headers={
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "content-type": "application/json",
                "origin": self.settings.base_url,
                "pragma": "no-cache",
                "referer": f"{self.settings.base_url}/",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            },
        )

    async def _close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    async def google_oauth_flow(self) -> Optional[str]:
        """
        Perform Google OAuth flow to get session token using optimized GoogleOAuthClient

        Returns:
            Session token string or None if failed
        """
        if not self.settings.google_email or not self.settings.google_password:
            logger.error("Google credentials not provided in settings")
            return None

        try:
            logger.info("Starting optimized Google OAuth flow...")

            # Create optimized OAuth configuration
            oauth_config = OAuthConfig(
                cdp_url=self.settings.chrome_cdp_url,
                headless=self.settings.headless,
                timeout=self.settings.oauth_timeout,
                retry_attempts=3,  # Enhanced retry for better reliability
                retry_delay=1.0,
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            # Use optimized OAuth client with automatic resource management
            async with GoogleOAuthClient(oauth_config) as oauth_client:
                # Extract session token with automatic retry and improved error handling
                session_token = await oauth_client.extract_session_token(
                    email=self.settings.google_email,
                    password=self.settings.google_password,
                    target_url=self.settings.base_url,
                    token_names=[
                        "next-auth.session-token",
                        "session-token",
                        "accessToken",
                    ],
                )

                if session_token:
                    logger.success(
                        "Session token extracted successfully via optimized flow"
                    )
                    self.session_token = session_token

                    # Update session with new token
                    if self.session:
                        from yarl import URL

                        self.session.cookie_jar.update_cookies(
                            {"next-auth.session-token": session_token},
                            response_url=URL(self.settings.base_url),
                        )

                    return session_token
                else:
                    logger.error("Session token not found in OAuth cookies")
                    return None

        except GoogleOAuthError as e:
            logger.error(f"OAuth flow failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Google OAuth flow: {e}")
            return None

    async def refresh_authentication(self) -> bool:
        """
        Refresh authentication using optimized OAuth flow

        Returns:
            True if authentication was refreshed successfully, False otherwise
        """
        try:
            logger.info("Refreshing authentication with optimized OAuth flow...")

            # First try to get session token
            token = await self.google_oauth_flow()
            if token:
                logger.success("Authentication refreshed successfully")
                return True

            logger.error("Authentication refresh failed completely")
            return False

        except Exception as e:
            logger.error(f"Error refreshing authentication: {e}")
            return False

    async def get_auth_session(self) -> Optional[AuthSession]:
        """
        Get authorization session data including access token with enhanced error handling

        Returns:
            AuthSession object or None if failed
        """
        if not self.session:
            await self._create_session()

        if not self.session_token:
            logger.info(
                "No session token available, attempting optimized OAuth flow..."
            )
            success = await self.refresh_authentication()
            if not success:
                logger.error("Failed to authenticate via OAuth flow")
                return None

        try:
            logger.info("Getting auth session...")
            if not self.session:
                logger.error("No session available")
                return None

            async with self.session.get(
                f"{self.settings.base_url}/api/auth/session"
            ) as response:
                logger.debug(f"Auth session status code: {response.status}")

                if response.status != 200:
                    response_text = await response.text()
                    logger.warning(
                        f"Auth session failed with status {response.status}: {response_text}"
                    )

                    # Try to refresh authentication if the session is invalid
                    logger.info(
                        "Attempting to refresh authentication due to failed session..."
                    )
                    success = await self.refresh_authentication()
                    if success:
                        # Ensure we have a valid session before retrying
                        if not self.session:
                            await self._create_session()

                        # Retry the session request
                        if not self.session:
                            logger.error("Session still not available after refresh")
                            return None

                        async with self.session.get(
                            f"{self.settings.base_url}/api/auth/session"
                        ) as retry_response:
                            if retry_response.status == 200:
                                data = await retry_response.json()
                                logger.success("Auth session successful after refresh")
                                return AuthSession(**data)
                            else:
                                retry_text = await retry_response.text()
                                logger.error(
                                    f"Auth session still failed after refresh: {retry_text}"
                                )
                                return None
                    else:
                        logger.error("Authentication refresh failed")
                        return None

                data = await response.json()
                logger.success("Auth session successful")
                logger.debug(f"Auth session data keys: {list(data.keys())}")

                return AuthSession(**data)

        except Exception as e:
            logger.error(f"Error getting auth session: {e}")
            # Try one more time with fresh authentication
            try:
                logger.info("Attempting fresh authentication due to error...")
                success = await self.refresh_authentication()
                if success:
                    # Ensure we have a valid session before retrying
                    if not self.session:
                        await self._create_session()

                    if not self.session:
                        logger.error(
                            "Session still not available after recovery attempt"
                        )
                        return None

                    async with self.session.get(
                        f"{self.settings.base_url}/api/auth/session"
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.success(
                                "Auth session successful after error recovery"
                            )
                            return AuthSession(**data)
                logger.error("Error recovery failed")
            except Exception as recovery_error:
                logger.error(f"Error during recovery attempt: {recovery_error}")
            return None


    # Helper function to test access token validity
    async def test_access_token(self, token: str) -> Optional[UserInfoResponse]:
        """Test if access token is valid by making API call"""
        try:
            headers = {
                "authorization": f"Bearer {token}",
                "accept": "*/*",
                "cache-control": "no-cache",
                "origin": self.settings.base_url,
                "referer": f"{self.settings.base_url}/",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.settings.api_base_url}/backend/user/info",
                    headers=headers,
                ) as response:
                    logger.debug(f"User info status code: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        logger.success("User info retrieved successfully")
                        return UserInfoResponse(**data)
                    elif response.status in [401, 403]:
                        # Token is invalid/expired
                        response_text = await response.text()
                        logger.warning(
                            f"Access token invalid (status {response.status}): {response_text}"
                        )
                        return None
                    else:
                        # Other error
                        response_text = await response.text()
                        logger.error(
                            f"User info failed with status {response.status}: {response_text}"
                        )
                        return None

        except Exception as e:
            logger.error(f"Error testing access token: {e}")
            return None

    async def get_user_info(
        self, access_token: Optional[str] = None
    ) -> Optional[UserInfoResponse]:
        """
        Get user information including credit balance with access token validation

        Args:
            access_token: Bearer token for API access. If None, will try to get from session

        Returns:
            UserInfoResponse object or None if failed
        """

        # If access token provided, test it first
        if access_token:
            logger.info("Testing provided access token...")
            result = await self.test_access_token(access_token)
            if result:
                return result
            logger.warning("Provided access token is invalid, getting new one...")
        else:
            logger.info("No access token provided, getting from session...")

        # Get fresh access token from session
        session_data = await self.get_auth_session()
        if not session_data:
            logger.error("No access token available from session")
            return None

        fresh_access_token = session_data.accessToken
        logger.info("Testing fresh access token...")

        # Test the fresh access token
        result = await self.test_access_token(fresh_access_token)
        if result:
            return result

        logger.error("All access token attempts failed")
        return None

    async def get_metrics(self) -> Metrics:
        """
        Get TwitterAPI metrics

        Returns:
            Metrics object or None if failed
        """
        user_info = await self.get_user_info()
        if not user_info:
            raise ValueError("Failed to retrieve user info for metrics")

        try:
            user_data = user_info.data.user_info
            credit_logs_30day = user_info.data.user_credit_consume_logs_30day

            # Calculate total available credits
            total_available = (
                user_data.recharge_credits + user_data.unused_bonuses_credits
            )

            # Calculate total usage in last 30 days
            total_usage = (
                credit_logs_30day.free_credits_used
                + credit_logs_30day.paid_credits_used
            )

            metrics = Metrics(
                usage=total_usage,
                limit=total_available,
                provider="twitterapi",
                extra={
                    "api_key": user_data.api_key,
                    "qps": user_data.qps,
                    "recharge_credits": user_data.recharge_credits,
                    "bonus_credits": user_data.unused_bonuses_credits,
                    "api_calls_30day": credit_logs_30day.api_calls_count,
                    "free_credits_used_30day": credit_logs_30day.free_credits_used,
                    "paid_credits_used_30day": credit_logs_30day.paid_credits_used,
                    "usage_percentage": (
                        (total_usage / total_available * 100)
                        if total_available > 0
                        else 0
                    ),
                },
            )

            logger.success("Metrics retrieved successfully")
            logger.info(f"Usage: {metrics.usage}/{metrics.limit}")

            return metrics

        except Exception as e:
            logger.warning(f"Error getting metrics: {e}")
            raise e

    async def print_summary(self):
        """Print a formatted summary of metrics"""
        metrics = await self.get_metrics()
        if not metrics:
            print("Failed to get metrics")
            return

        print("=" * 60)
        print("TwitterAPI.io Metrics Summary")
        print("=" * 60)
        print(f"Provider: {metrics.provider}")
        print(f"Total Usage: {metrics.usage}")
        print(f"Total Limit: {metrics.limit}")

        if metrics.extra:
            print("-" * 60)
            print("Additional Details:")
            print(f"  API Key: {metrics.extra.get('api_key', 'N/A')}")
            print(f"  QPS Limit: {metrics.extra.get('qps', 'N/A')}")
            print(f"  Recharged Credits: {metrics.extra.get('recharge_credits', 0):,}")
            print(f"  Bonus Credits: {metrics.extra.get('bonus_credits', 0):,}")
            print(f"  API Calls (30 days): {metrics.extra.get('api_calls_30day', 0):,}")
            print(
                f"  Free Credits Used: {metrics.extra.get('free_credits_used_30day', 0):,}"
            )
            print(
                f"  Paid Credits Used: {metrics.extra.get('paid_credits_used_30day', 0):,}"
            )

        print("=" * 60)


async def get_twitterapi_metrics() -> Metrics:
    """
    Convenience function to get TwitterAPI metrics

    Returns:
        Metrics object or None if failed
    """

    async with TwitterAPIClient() as client:
        return await client.get_metrics()


async def main():
    """Example usage"""

    async with TwitterAPIClient() as client:
        # Print detailed summary
        await client.print_summary()

        # Get metrics object
        metrics = await client.get_metrics()
        if metrics:
            print(f"\nMetrics JSON: {metrics.model_dump_json(indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
