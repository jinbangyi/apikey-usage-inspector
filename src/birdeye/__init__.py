from pydantic_settings import SettingsConfigDict

from src.typing import _GeneralApiKeySettings


class Settings(_GeneralApiKeySettings):
    email: str = "YOUR_EMAIL"
    password: str = "YOUR_PASSWORD"

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_prefix="BIRDEYE_",
    )

    def __init__(self, **data):
        super().__init__(**data)
        if (
            self.enabled
            and self.email == "YOUR_EMAIL"
            and self.password == "YOUR_PASSWORD"
        ):
            raise ValueError("The default email and password is not valid.")
