import asyncio
import base64
import json
import urllib.parse
import uuid
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


class CaptchaInitResponse(BaseModel):
    captchaSecurityId: str
    captchaBizCode: str


class CaptchaChallenge(BaseModel):
    sig: str
    salt: str
    path2: str  # Image path
    ek: str
    captchaType: str
    tag: str  # What to identify (airplane, car, etc.)
    fb: str
    i18n: str


class CaptchaChallengeResponse(BaseModel):
    code: str
    data: CaptchaChallenge
    success: bool


class CaptchaValidationResponse(BaseModel):
    code: str
    data: dict
    success: bool


class LoginResponse(BaseModel):
    success: bool = True
    session_token: Optional[str] = None


def generate_device_info() -> dict:
    """Generate device info for CMC requests"""
    return {
        "screen_resolution": "1920,1080",
        "available_screen_resolution": "1920,1040",
        "system_version": "unknown",
        "brand_model": "unknown",
        "timezone": "Asia/Shanghai",
        "timezoneOffset": -480,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "list_plugin": "PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF",
        "platform": "Win32",
        "webgl_vendor": "unknown",
        "webgl_renderer": "unknown",
    }


def get_bnc_uuid() -> str:
    """Generate a BNC UUID for captcha requests"""
    return str(uuid.uuid4())


def get_fvideo_id() -> str:
    """Generate a FVideo ID for captcha requests"""
    return "335fe043b6fc960292e0a5f451ee21212b6b4492"


async def get_initial_captcha() -> CaptchaInitResponse:
    """Get initial captcha information for CMC login"""
    # First, make a login attempt to get captcha requirement
    login_url = "https://portal-api.coinmarketcap.com/v1/login"

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

    # Make initial login attempt without captcha to trigger captcha requirement
    login_data = {
        "email": settings.cmcCaptchaSettings.email,
        "password": settings.cmcCaptchaSettings.password,
        "captcha": "",
        "securityId": "",
        "deviceInfo": json.dumps(generate_device_info()),
        # fingnerprint of the device, similar with FingerprintJS
        "fvideoId": get_fvideo_id(),
    }

    response = await async_post(login_url, json=login_data, headers=headers)

    if response.status in [200]:  # Expected captcha required response
        data = await response.json()
        if settings.debug_enabled:
            logger.debug(f"Initial captcha response: {data}")

        # Look for captcha requirement in response
        if "captchaSecurityId" in data and "captchaBizCode" in data:
            return CaptchaInitResponse(**data)

    text = await response.text()
    raise Exception(f"Failed to get initial captcha info: {response.status} - {text}")


async def get_captcha_challenge(security_id: str) -> CaptchaChallengeResponse:
    """Get the actual captcha challenge (image and details)"""
    captcha_url = (
        "https://api.commonservice.io/gateway-api/v1/public/antibot/getCaptcha"
    )

    device_info_b64 = base64.b64encode(
        json.dumps(generate_device_info()).encode()
    ).decode()
    bnc_uuid = get_bnc_uuid()
    fvideo_id = get_fvideo_id()

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "bnc-uuid": bnc_uuid,
        "cache-control": "no-cache",
        "captcha-sdk-version": "1.0.0",
        "clienttype": "web",
        "content-type": "text/plain; charset=UTF-8",
        "device-info": device_info_b64,
        "fvideo-id": fvideo_id,
        "origin": "https://pro.coinmarketcap.com",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://pro.coinmarketcap.com/",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "x-captcha-se": "true",
    }

    data = f"bizId=CMC_login&sv=20220812&lang=en&securityCheckResponseValidateId={security_id}&clientType=web"

    response = await async_post(captcha_url, data=data, headers=headers)
    text = await response.text()
    if settings.debug_enabled:
        logger.debug(f"Captcha challenge response: {text}")

    if response.status == 200:
        data = json.loads(text)
        return CaptchaChallengeResponse(**data)
    else:
        raise Exception(f"Failed to get captcha challenge: {response.status} - {text}")


async def validate_captcha(
    security_id: str, challenge: CaptchaChallenge, solution_data: str
) -> CaptchaValidationResponse:
    """Validate the captcha solution"""
    validate_url = (
        "https://api.commonservice.io/gateway-api/v1/public/antibot/validateCaptcha"
    )

    device_info_b64 = base64.b64encode(
        json.dumps(generate_device_info()).encode()
    ).decode()

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "bnc-uuid": 'xxx',
        "cache-control": "no-cache",
        "captcha-sdk-version": "1.0.0",
        "clienttype": "web",
        "content-type": "text/plain; charset=UTF-8",
        "device-info": device_info_b64,
        "fvideo-id": 'xxx',
        "origin": "https://pro.coinmarketcap.com",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://pro.coinmarketcap.com/",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "x-captcha-se": "true",
    }

    # The solution_data would contain the encoded solution from solving the captcha
    # For now, this is a placeholder - in practice you'd need to implement image recognition
    data = f"bizId=CMC_login&sv=20220812&lang=en&securityCheckResponseValidateId={security_id}&clientType=web&data={solution_data}&s=306704&sig={challenge.sig}"

    response = await async_post(validate_url, data=data, headers=headers)

    if response.status == 200:
        data = await response.json()
        if settings.debug_enabled:
            logger.debug(f"Captcha validation response: {data}")
        return CaptchaValidationResponse(**data)
    else:
        text = await response.text()
        raise Exception(f"Failed to validate captcha: {response.status} - {text}")


async def solve_captcha_interactive(challenge: CaptchaChallengeResponse) -> str:
    """Interactive captcha solving (for development/testing)"""
    logger.info(f"🔒 CMC Captcha Challenge Required!")
    logger.info(f"📷 Image URL: https://staticrecap.cgicgi.io{challenge.data.path2}")
    logger.info(f"🎯 Task: Please select all images with '{challenge.data.tag}'")
    logger.info(f"🔧 Captcha Type: {challenge.data.captchaType}")
    exit(0)

    # For now, return a placeholder that will fail validation
    # In a production environment, you would:
    # 1. Download and display the image
    # 2. Allow user to select the correct areas
    # 3. Encode the solution according to CMC's format
    logger.warning(
        "⚠️  Captcha solving not fully implemented yet - returning placeholder"
    )
    return "placeholder_solution_data"


async def get_captcha() -> CaptchaInitResponse:
    """Get captcha information for login (legacy function for compatibility)"""
    return await get_initial_captcha()


async def cmc_login(email: str, password: str) -> str:
    """Login to CoinMarketCap with captcha resolution and return session cookie"""
    logger.info("🚀 Starting CMC login process...")

    try:
        # Step 1: Get initial captcha information
        logger.info("🔍 Getting initial captcha information...")
        captcha_init = await get_initial_captcha()
        logger.info(f"✅ Got captcha security ID: {captcha_init.captchaSecurityId}")

        captchaSecurityId = captcha_init.captchaSecurityId
        # Step 2: Get captcha challenge
        logger.info("🖼️  Getting captcha challenge...")
        challenge = await get_captcha_challenge(captchaSecurityId)
        logger.info(
            f"✅ Got captcha challenge: {challenge.data.captchaType} - {challenge.data.tag}"
        )

        # Step 3: Solve captcha (interactive for now)
        logger.info("🧩 Solving captcha...")
        solution_data = await solve_captcha_interactive(challenge)

        # Step 4: Validate captcha
        logger.info("✅ Validating captcha solution...")
        validation = await validate_captcha(
            captchaSecurityId, challenge.data, solution_data
        )

        if not validation.success or validation.code != "000000":
            raise Exception(f"Captcha validation failed: {validation.code}")

        captcha_token = validation.data.get("token")
        if not captcha_token:
            raise Exception("No captcha token returned from validation")

        logger.info("✅ Captcha validation successful!")

        # Step 5: Login with captcha token
        logger.info("🔐 Performing login with captcha token...")
        session_token = await perform_login_with_captcha(
            email, password, captcha_token, captchaSecurityId
        )

        logger.info(f"✅ CMC login successful! Session: {session_token[:20]}...")
        return session_token

    except Exception as e:
        logger.error(f"❌ CMC login failed: {e}")
        raise


async def perform_login_with_captcha(
    email: str, password: str, captcha_token: str, security_id: str
) -> str:
    """Perform the actual login with captcha token"""
    login_url = "https://portal-api.coinmarketcap.com/v1/login"

    device_info = generate_device_info()
    fvideo_id = get_fvideo_id()

    login_data = {
        "email": email,
        "password": password,
        "captcha": captcha_token,
        "securityId": security_id,
        "deviceInfo": json.dumps(device_info),
        "fvideoId": fvideo_id,
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
        logger.debug(f"Login response status: {response.status}")
        logger.debug(f"Login response: {text}")
        with open("logs/cmc_login_response.txt", "w") as f:
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
            # Try to parse response for any session info
            try:
                response_data = await response.json()
                if "sessionToken" in response_data:
                    return response_data["sessionToken"]
            except:
                pass
            raise Exception("Login successful but no session cookie returned.")
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


async def start() -> Metrics:
    """Main function to get CMC usage metrics"""
    try:
        # Login to get session token
        session_token = await cmc_login(
            settings.cmcCaptchaSettings.email, settings.cmcCaptchaSettings.password
        )
        logger.debug(f"CMC session token obtained: {session_token[:20]}...")

        # Get usage statistics and plan info concurrently
        usage_stats_result, plan_info_result = await asyncio.gather(
            get_cmc_usage(session_token),
            get_cmc_plan_info(session_token),
            return_exceptions=True,
        )

        if isinstance(usage_stats_result, BaseException):
            logger.error(f"Error fetching usage stats: {usage_stats_result}")
            raise usage_stats_result

        # Type narrow usage_stats to ensure it's not an exception
        usage_stats: UsageStats = usage_stats_result

        if settings.debug_enabled:
            logger.debug(f"CMC usage stats: {usage_stats}")
            logger.debug(f"CMC plan info: {plan_info_result}")

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

        # Use plan limit if available, otherwise estimate based on usage patterns
        if plan_limit and plan_limit > 0:
            limit = plan_limit
            logger.info(f"CMC limit obtained from plan info: {limit}")
        else:
            raise Exception(
                "Failed to retrieve CMC plan limit. Please check your plan settings."
            )
        if settings.debug_enabled:
            logger.debug(f"CMC current usage: {current_usage}, limit: {limit}")

        return Metrics(usage=current_usage, limit=limit, provider="coinmarketcap")

    except Exception as e:
        logger.error(f"Error in CMC start function: {e}")
        raise


if __name__ == "__main__":
    # TODO: bypass captcha
    # TODO: save the cookie to a file
    result = asyncio.run(start())
    logger.debug(result)
