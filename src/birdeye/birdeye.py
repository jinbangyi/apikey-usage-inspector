from typing import Optional
from urllib.parse import urlencode
import requests
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger

class Settings(BaseSettings):
    birdeye_apikey: str = "YOUR_API_KEY"  # Default value, can be overridden by .env file
    birdeye_email: str = "YOUR_EMAIL"  # Default value, can be overridden by .env file
    birdeye_password: str = "YOUR_PASSWORD"  # Default value, can be overridden by .env file
    flaresolver_endpoint: str = "http://localhost:8191/v1"
    flaresolver_proxy: Optional[str] = None  # Optional proxy URL, can be set in .env file

    model_config = SettingsConfigDict(
        extra='ignore',
        env_file=".env",  # Specify the .env file to load environment variables from
    )

settings = Settings()


class RateLimit(BaseModel):
    second: int
    minute: int


class Plan(BaseModel):
    level: int
    monthlyUnits: int
    name: str
    price: int
    pricePerUnit: Optional[float]
    stripeUsagePriceId: Optional[str]
    monthlyWsUnits: Optional[int]
    pricePerWsUnit: Optional[float]
    stripeApiUsagePriceId: Optional[str]
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

def _base_request(url: str, method: str = 'GET', postData: dict = {}):
    if postData:
        method = 'POST'
    _url = settings.flaresolver_endpoint
    headers = {"Content-Type": "application/json"}
    data = {
        "cmd": f"request.{method.lower()}",
        "url": url,
        "maxTimeout": 60000
    }
    if postData:
        data["postData"] = urlencode(postData)
    if settings.flaresolver_proxy:
        data["proxy"] = {"url": settings.flaresolver_proxy}

    response = requests.post(_url, headers=headers, json=data)
    return response

def get_birdeye_usage(subscription_id: str, token: str) -> UsageDataResponse:
    birdeye_url = f"https://multichain-api.birdeye.so/payments/subscriptions/{subscription_id}/usage"
    
    response = requests.get(
        birdeye_url,
        params={'token': token},
        headers={
            'origin': 'https://bds.birdeye.so',
            'referer': 'https://bds.birdeye.so/',
            'accept': 'application/json, text/plain, */*',
            'Authorization': f'Bearer {settings.birdeye_apikey}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0 Safari/537.36'
        },
        allow_redirects=True,
        verify=False
    )
    if response.status_code == 200:
        data = response.json()
        return UsageDataResponse(**data)
    else:
        raise Exception(f"Error: {response.status_code} - {response.text}")

def birdeye_login(email: str, password: str):
    birdeye_url = "https://multichain-api.birdeye.so/user/login"
    
    # response = _base_request(birdeye_url, 'POST', {
    #     'email': email,
    #     'password': password
    # })
    # print(response.text)
    response = requests.post(
        birdeye_url,
        json={'email': email, 'password': password},
        headers={
            'origin': 'https://bds.birdeye.so',
            'referer': 'https://bds.birdeye.so/',
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0 Safari/537.36'
        },
        allow_redirects=True,
        verify=False
    )
    with open("birdeye_login_response.txt", "w") as f:
        f.write(response.text)
    if response.status_code == 200:
        data = response.json()
        if 'token' in data:
            return data['token']
        else:
            raise Exception("Login failed, no token returned.")
    else:
        raise Exception(f"Error: {response.status_code} - {response.text}")

def get_birdeye_monthly_max_usage(token: str) -> AccountInfoResponse:
    birdeye_url = "https://multichain-api.birdeye.so/accounts/default"
    
    response = requests.get(
        birdeye_url,
        params={'token': token},
        headers={
            'origin': 'https://bds.birdeye.so',
            'referer': 'https://bds.birdeye.so/',
            'accept': 'application/json, text/plain, */*',
            'Authorization': f'Bearer {settings.birdeye_apikey}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0 Safari/537.36'
        },
        allow_redirects=True,
        verify=False
    )
    print(response.text)
    if response.status_code == 200:
        data = response.json()
        return AccountInfoResponse(**data)
    else:
        raise Exception(f"Error: {response.status_code} - {response.text}")

def start():
    token = birdeye_login(settings.birdeye_email, settings.birdeye_password)
    logger.debug(f"Birdeye token: {token}")
    monthly_usage = get_birdeye_monthly_max_usage(token)
    usage = get_birdeye_usage(monthly_usage.data.subscription.id, token)

    return {
        "monthly_usage": monthly_usage,
        "usage": usage
    }


if __name__ == "__main__":
    # https://bds.birdeye.so/user/profile
    # add the below record to /etc/hosts
    # 37.59.30.17 multichain-api.birdeye.so
    logger.debug(start())
