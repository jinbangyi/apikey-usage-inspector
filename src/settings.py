from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.anthropic import Settings as AnthropicSettings
from src.birdeye import Settings as BirdeyeSettings
from src.cmc import Settings as CMCSettings
from src.cmc.captcha import Settings as CMCCaptchaSettings
from src.cmc.cookie import Settings as CMCCookieSettings
from src.coingecko import Settings as CoinGeckoSettings
from src.openai import Settings as OpenAISettings
from src.quicknode import Settings as QuickNodeSettings
from src.twitterapi import Settings as TwitterAPISettings
from src.twitterapi.oauth import Settings as TwitterAPIOauthSettings


class Metrics(BaseModel):
    usage: int
    limit: int
    provider: str
    key_masked: Optional[str] = None
    extra: Optional[dict] = None


class CommonSettings(BaseSettings):
    # using original ip to bypass cloudflare
    dns_map: dict = {
        "multichain-api.birdeye.so": "37.59.30.17",
    }
    debug_enabled: bool = False

    push_gateway_enabled: bool = False
    push_gateway_url: str = "http://localhost:9091"
    push_gateway_job: str = "cron-apikey-usage"

    # using flaresolver bypass clouodflare
    flaresolver_enabled: bool = False
    flaresolver_endpoint: str = "http://localhost:8191/v1"
    flaresolver_proxy: Optional[str] = None

    birdeyeSettings: BirdeyeSettings = BirdeyeSettings()
    quickNodeSettings: QuickNodeSettings = QuickNodeSettings()
    cmcSettings: CMCSettings = CMCSettings()
    cmcCookieSettings: CMCCookieSettings = CMCCookieSettings()
    cmcCaptchaSettings: CMCCaptchaSettings = CMCCaptchaSettings()
    coingeckoSettings: CoinGeckoSettings = CoinGeckoSettings()
    openaiSettings: OpenAISettings = OpenAISettings()
    anthropicSettings: AnthropicSettings = AnthropicSettings()
    twitterAPISettings: TwitterAPISettings = TwitterAPISettings()
    twitterAPIOauthSettings: TwitterAPIOauthSettings = TwitterAPIOauthSettings()

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
    )


settings = CommonSettings()
