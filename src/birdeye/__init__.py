from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    birdeye_enabled: bool = True
    birdeye_email: str = "YOUR_EMAIL"
    birdeye_password: str = "YOUR_PASSWORD"

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
    )
