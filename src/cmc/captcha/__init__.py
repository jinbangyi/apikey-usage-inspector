from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    enabled: bool = False
    email: str = "YOUR_EMAIL"
    password: str = "YOUR_PASSWORD"

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_prefix="CMC_",
    )

    def __init__(self, **data):
        super().__init__(**data)
        if (
            self.enabled
            and self.email == "YOUR_EMAIL"
            and self.password == "YOUR_PASSWORD"
        ):
            raise ValueError("The default email or password is not valid.")
