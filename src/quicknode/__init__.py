from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    quicknode_enabled: bool = True
    quicknode_console_apikey: str = "YOUR_QUICKNODE_API_KEY"
