from pydantic_settings import SettingsConfigDict

from src.typing import GeneralConsoleApiKeySettings


class Settings(GeneralConsoleApiKeySettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_prefix="QUICKNODE_",
    )
