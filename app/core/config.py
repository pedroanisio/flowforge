"""
Configuration management for the application
"""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application Settings
    app_name: str = "Neural Plugin System with Chain Builder"
    app_version: str = "2.0.0"
    environment: str = Field(default="development", env="FASTAPI_ENV")
    debug: bool = Field(default=True, env="DEBUG")

    # Security Settings
    secret_key: str = Field(
        default="CHANGE_THIS_TO_A_RANDOM_SECRET_KEY_IN_PRODUCTION",
        env="SECRET_KEY"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Authentication Settings
    enable_auth: bool = Field(default=False, env="ENABLE_AUTH")

    # File Upload Settings
    max_upload_size_mb: int = Field(default=100, env="MAX_UPLOAD_SIZE_MB")
    max_upload_size_bytes: int = 100 * 1024 * 1024  # Computed from max_upload_size_mb

    # Rate Limiting Settings
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")

    # Docker Settings
    pdf2htmlex_service_host: str = Field(default="pdf2htmlex-service", env="PDF2HTMLEX_SERVICE_HOST")

    # Storage Settings
    data_dir: str = Field(default="/app/data", env="DATA_DIR")
    downloads_dir: str = Field(default="/app/data/downloads", env="DOWNLOADS_DIR")
    chains_dir: str = Field(default="/app/data/chains", env="CHAINS_DIR")
    templates_dir: str = Field(default="/app/data/templates", env="TEMPLATES_DIR")

    # Logging Settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Compute max_upload_size_bytes from max_upload_size_mb
        self.max_upload_size_bytes = self.max_upload_size_mb * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()
