"""Configuration management for Clip Cutter."""

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    app_name: str = "Clip Cutter"
    debug: bool = False

    # Gemini API
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")

    # Supabase
    supabase_url: Optional[str] = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: Optional[str] = Field(default=None, alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: Optional[str] = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")

    # Cloudflare R2
    r2_account_id: Optional[str] = Field(default=None, alias="R2_ACCOUNT_ID")
    r2_access_key_id: Optional[str] = Field(default=None, alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: Optional[str] = Field(default=None, alias="R2_SECRET_ACCESS_KEY")
    r2_bucket_name: str = Field(default="clip-cutter-videos", alias="R2_BUCKET_NAME")
    r2_endpoint: Optional[str] = Field(default=None, alias="R2_ENDPOINT")

    # Server settings
    host: str = "0.0.0.0"
    port: int = 7860

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def r2_configured(self) -> bool:
        """Check if R2 storage is configured."""
        return all([
            self.r2_account_id,
            self.r2_access_key_id,
            self.r2_secret_access_key,
            self.r2_endpoint,
        ])

    @property
    def supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return all([
            self.supabase_url,
            self.supabase_anon_key,
        ])

    @property
    def gemini_configured(self) -> bool:
        """Check if Gemini API is configured."""
        return bool(self.google_api_key)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience function for quick access
settings = get_settings()
