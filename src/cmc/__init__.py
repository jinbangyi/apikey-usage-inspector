from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cmc_enabled: bool = True
    cmc_email: str = "YOUR_EMAIL"
    cmc_password: str = "YOUR_PASSWORD"
