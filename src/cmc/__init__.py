from typing import List, Union

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    enabled: bool = False
    # expires for 1 year by default
    session_token: Union[str, List[str]] = "session_token"

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_prefix="CMC_",
    )

    def __init__(self, **data):
        super().__init__(**data)

        if self.enabled:
            # Handle both single string and list of API keys
            if isinstance(self.session_token, str):
                if self.session_token == "session_token":
                    raise ValueError(
                        "The default API key is not valid. Please provide a valid API key."
                    )
            elif isinstance(self.session_token, list):
                if not self.session_token or all(
                    key == "session_token" for key in self.session_token
                ):
                    raise ValueError(
                        "The default API key is not valid. Please provide valid API keys."
                    )

    @property
    def session_tokens(self) -> List[str]:
        if isinstance(self.session_token, str):
            return [self.session_token]
        return self.session_token

    @property
    def has_multiple_tokens(self) -> bool:
        """Check if multiple session tokens are configured"""
        return len(self.session_tokens) > 1
