from pydantic_settings import SettingsConfigDict

from src.typing import GeneralAdminApiKeySettings


class Settings(GeneralAdminApiKeySettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_prefix="OPENAI_",
    )

    def __init__(self, **data):
        super().__init__(**data)
        if self.enabled:
            self.validate_apikeys(self.apikey)
