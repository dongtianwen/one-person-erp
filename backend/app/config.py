from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "天枢"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    DATABASE_URL: str = "sqlite+aiosqlite:///./shubiao.db"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    LLM_PROVIDER: str = "none"
    LLM_LOCAL_MODEL: str = "gemma4:e2b:q4"
    LLM_LOCAL_BASE_URL: str = "http://localhost:11434"
    LLM_API_BASE: str = ""
    LLM_API_KEY: str = ""
    LLM_API_MODEL: str = ""

    model_config = ConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()
