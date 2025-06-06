from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    quicknode_enabled: bool = True
    quicknode_console_apikey: str = "YOUR_QUICKNODE_API_KEY"

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
    )
