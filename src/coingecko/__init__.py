from pydantic_settings import SettingsConfigDict

from src.typing import GeneralApiKeySettings


class Settings(GeneralApiKeySettings):
    model_config = SettingsConfigDict(
        env_prefix="COINGECKO_", env_file=".env", extra="ignore"
    )
