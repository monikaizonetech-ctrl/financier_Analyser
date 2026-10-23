"""
Application configuration, loaded from environment variables / .env file.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure .env is always loaded from backend directory regardless of current working directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = str(BASE_DIR / ".env")


class Settings(BaseSettings):
    PROJECT_NAME: str = "iZone Analyzer API"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql://izone_user:izone_pass@localhost:5432/financier_db"

    JWT_SECRET_KEY: str = "change_this_to_a_long_random_secret_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    FRONTEND_ORIGIN: str = "http://localhost:5173"
    CORS_ORIGINS: str = ""

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 15

    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    model_config = SettingsConfigDict(
        env_file=[ENV_FILE, ".env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """
        Retrieve and parse allowed CORS origins from .env (FRONTEND_ORIGIN and CORS_ORIGINS).
        Supports single URLs or comma-separated lists.
        """
        origins: list[str] = []
        for raw in [self.FRONTEND_ORIGIN, self.CORS_ORIGINS]:
            if not raw:
                continue
            for item in raw.split(","):
                cleaned = item.strip()
                if cleaned and cleaned not in origins:
                    origins.append(cleaned)
        return origins or ["http://localhost:5173"]


settings = Settings()

