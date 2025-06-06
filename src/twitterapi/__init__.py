from typing import List, Union

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    enabled: bool = True
    apikey: Union[str, List[str]] = "YOUR_API_KEY"

    model_config = SettingsConfigDict(
        env_prefix="TWITTERAPI_", env_file=".env", extra="ignore"
    )

    def __init__(self, **data):
        super().__init__(**data)
        if self.enabled:
            # Handle both single string and list of API keys
            if isinstance(self.apikey, str):
                if self.apikey == "YOUR_API_KEY":
                    raise ValueError(
                        "The default API key is not valid. Please provide a valid API key."
                    )
            elif isinstance(self.apikey, list):
                if not self.apikey or all(key == "YOUR_API_KEY" for key in self.apikey):
                    raise ValueError(
                        "The default API key is not valid. Please provide valid API keys."
                    )

    @property
    def api_keys(self) -> List[str]:
        """Return API keys as a list for easy iteration"""
        if isinstance(self.apikey, str):
            return [self.apikey]
        return self.apikey
