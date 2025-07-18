from typing import List, Union

from pydantic import Field
from pydantic_settings import BaseSettings


class _GeneralApiKeySettings(BaseSettings):
    enabled: bool = False
    retry_attempts: int = 3
    retry_delay: int = 120 # 120 seconds

    apikey: Union[str, List[str]] = Field(default="YOUR_API_KEY")
    admin_apikey: Union[str, List[str]] = Field(default="YOUR_API_KEY")
    console_apikey: Union[str, List[str]] = Field(default="YOUR_API_KEY")

    def validate_apikeys(self, apikeys: Union[str, List[str]]):
        """Validate that the API keys are not the default placeholder."""
        if isinstance(apikeys, str):
            if apikeys == "YOUR_API_KEY":
                raise ValueError(
                    "The default API key is not valid. Please provide a valid API key."
                )
        elif isinstance(apikeys, list):
            if not apikeys or all(key == "YOUR_API_KEY" for key in apikeys):
                raise ValueError(
                    "The default API key is not valid. Please provide valid API keys."
                )

    @property
    def api_keys(self) -> List[str]:
        """Return API keys as a list for easy iteration"""
        if isinstance(self.apikey, str):
            return [self.apikey]
        return self.apikey

    @property
    def admin_api_keys(self) -> List[str]:
        """Return admin API keys as a list for easy iteration"""
        if isinstance(self.admin_apikey, str):
            return [self.admin_apikey]
        return self.admin_apikey


class GeneralApiKeySettings(_GeneralApiKeySettings):
    def __init__(self, **data):
        super().__init__(**data)
        if self.enabled:
            self.validate_apikeys(self.apikey)


class GeneralAdminApiKeySettings(_GeneralApiKeySettings):
    """
    Settings class for admin API keys with the same structure as GeneralApiKeySettings.
    This allows for easy extension or modification of admin-specific settings in the future.
    """

    def __init__(self, **data):
        super().__init__(**data)
        if self.enabled:
            self.validate_apikeys(self.admin_apikey)


class GeneralConsoleApiKeySettings(_GeneralApiKeySettings):
    def __init__(self, **data):
        super().__init__(**data)
        if self.enabled:
            self.validate_apikeys(self.console_apikey)
