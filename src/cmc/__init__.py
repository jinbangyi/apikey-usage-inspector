from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cmc_email: str = "YOUR_EMAIL"
    cmc_password: str = "YOUR_PASSWORD"
