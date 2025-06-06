from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    cmc_enabled: bool = False
    cmc_email: str = "YOUR_EMAIL"
    cmc_password: str = "YOUR_PASSWORD"

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
    )
