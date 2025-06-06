from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    enabled: bool = True
    console_apikey: str = "YOUR_API_KEY"

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_prefix="QUICKNODE_",
    )

    def __init__(self, **data):
        super().__init__(**data)
        if self.enabled and self.console_apikey == "YOUR_API_KEY":
            raise ValueError(
                "The default API key is not valid. Please provide a valid API key."
            )
