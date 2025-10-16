"""Application configuration."""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # App settings
    debug: bool = Field(default=False)
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO")
    
    # Security
    api_key: str = Field(default="", alias="API_KEY", description="API key for authentication")
    
    # Model settings
    models_cache_dir: str = Field(default="/tmp/models", alias="MODEL_CACHE_DIR")
    batch_size: int = Field(default=16, alias="BATCH_SIZE")
    
    # Redis cache settings
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_auth: str = Field(default="", alias="REDIS_AUTH")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_ssl: bool = Field(default=False, alias="REDIS_SSL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()

