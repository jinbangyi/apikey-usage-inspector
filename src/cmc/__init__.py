from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    quicknode_console_apikey: str = "YOUR_QUICKNODE_API_KEY"
