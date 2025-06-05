from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.birdeye import Settings as BirdeyeSettings
from src.cmc import Settings as CMCSettings
from src.quicknode import Settings as QuickNodeSettings


class Metrics(BaseModel):
    usage: int
    limit: int
    provider: str


class Settings(BaseSettings):
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

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
    )


settings = Settings()
