from functools import lru_cache 
from pathlib import Path

# Used to validate .env variables
from pydantic_settings import BaseSettings, SettingsConfigDict 

# Construct absolute path to .env file
env_file_location = str(Path(__file__).resolve().parent.parent / ".env")

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_HOURS: int
    REDIS_PASSWORD: str
    DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=env_file_location)

# Caches the settings instance to avoid re-parsing .env file
@lru_cache
def get_settings() -> Settings:
    # pylance doesn't understand that the Settings fields are loaded at runtime from the .env file,
    # so use type: ignore to suppress the editor error
    return Settings()  # type: ignore[call-arg]
