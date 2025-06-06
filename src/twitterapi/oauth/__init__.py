from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """TwitterAPI settings"""

    enabled: bool = Field(
        default=False, description="Enable TwitterAPI integration"
    )
    # Authentication
    session_token: Optional[str] = Field(
        default=None, description="Next-auth session token"
    )
    google_email: Optional[str] = Field(
        default=None, description="Google account email for OAuth"
    )
    google_password: Optional[str] = Field(
        default=None, description="Google account password for OAuth"
    )

    # API Configuration
    base_url: str = Field(
        default="https://twitterapi.io", description="TwitterAPI base URL"
    )
    api_base_url: str = Field(
        default="https://api.twitterapi.io", description="TwitterAPI backend URL"
    )

    # Browser automation
    chrome_cdp_url: str = Field(
        default="http://localhost:9222",
        description="Chrome CDP URL for browser automation",
    )
    headless: bool = Field(default=False, description="Run browser in headless mode")

    # Timeouts
    oauth_timeout: int = Field(
        default=30000, description="OAuth flow timeout in milliseconds"
    )
    request_timeout: int = Field(
        default=10, description="HTTP request timeout in seconds"
    )

    model_config = SettingsConfigDict(
        env_prefix="TWITTERAPI_", env_file=".env", extra="ignore"
    )
