from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    birdeye_email: str = "YOUR_EMAIL"
    birdeye_password: str = "YOUR_PASSWORD"
