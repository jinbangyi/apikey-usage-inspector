from pydantic_settings import SettingsConfigDict

from src.typing import GeneralAdminApiKeySettings


class Settings(GeneralAdminApiKeySettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_prefix="ANTHROPIC_",
    )
