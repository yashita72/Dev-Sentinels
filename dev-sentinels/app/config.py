"""
Application configuration management using Pydantic Settings.
Reads environment variables from system env and optional .env file.
"""

import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    """
    Application Settings schema with strict typing and defaults.
    """
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # GitHub Configurations
    GITHUB_TOKEN: str = Field(..., description="GitHub Personal Access Token or App Token with repo PR permissions")
    GITHUB_WEBHOOK_SECRET: str = Field(..., description="Secret token configured in GitHub Webhooks")

    # Google Gemini Configurations
    GEMINI_API_KEY: str = Field(..., description="API key for Google Gemini access")
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash", description="LLM model name for LangChain analysis agents")

    # Server Configurations
    APP_HOST: str = Field(default="0.0.0.0", description="Host address for FastAPI server")
    APP_PORT: int = Field(default=8000, description="Port for FastAPI server")
    DEBUG: bool = Field(default=False, description="Debug mode flag")


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of Settings to avoid repeated disk reads.
    """
    return Settings()

