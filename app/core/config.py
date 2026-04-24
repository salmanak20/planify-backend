"""
Core configuration using pydantic-settings.
Values are loaded from the .env file automatically.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    DATABASE_URL: str = "sqlite+aiosqlite:///./planify.db"
    FIREBASE_PROJECT_ID: str | None = None
    # Local dev: path to service account JSON file
    FIREBASE_CREDENTIALS_PATH: str | None = None
    # Cloud deployment: base64-encoded service account JSON string
    FIREBASE_CREDENTIALS_JSON: str | None = None
    FIREBASE_VERIFICATION_REQUIRED: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
