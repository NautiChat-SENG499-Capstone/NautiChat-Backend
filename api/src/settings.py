import os
from functools import lru_cache
from pathlib import Path

# Used to validate .env variables
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str = "default_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    REDIS_PASSWORD: str = "default_redis_password"
    SUPABASE_DB_URL: str = "default_supabase_db_url"
    GROQ_API_KEY: str = "default_groq_api_key"
    ONC_TOKEN: str = "default_onc_token"
    CAMBRIDGE_LOCATION_CODE: str = "default_cambridge_location_code"
    QDRANT_API_KEY: str = "default_qdrant_api_key"
    QDRANT_URL: str = "default_qdrant_url"
    QDRANT_COLLECTION_NAME: str = "default_qdrant_collection_name"

    # guard for production environment
    model_config = (
        SettingsConfigDict(
            env_file=str(Path(__file__).resolve().parent.parent / ".env"),
            extra="allow",
        )
        if os.getenv("ENV") != "production"
        else SettingsConfigDict(extra="allow")
    )


# Caches the settings instance to avoid re-parsing .env file
@lru_cache
def get_settings() -> Settings:
    # pylance doesn't understand that the Settings fields are loaded at runtime from the .env file,
    # so use type: ignore to suppress the editor error
    return Settings()  # type: ignore[call-arg]
