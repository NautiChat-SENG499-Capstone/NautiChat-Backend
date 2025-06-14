from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_HOURS: int
    REDIS_PASSWORD: str
    SUPABASE_DB_URL: str

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    # pylance doesn't understand that the Settings fields are loaded at runtime from the .env file,
    # so use type: ignore to suppress the editor error
    return Settings()  # type: ignore[call-arg]
