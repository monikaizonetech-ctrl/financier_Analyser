"""
Application configuration, loaded from environment variables / .env file.
"""
from pathlib import Path
from typing import Any, List, Union
from pydantic import field_validator, model_validator
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

    # Domain and CORS configuration loaded from .env
    DOMAIN: str = ""
    FRONTEND_DOMAIN: str = ""
    FRONTEND_ORIGIN: str = ""
    CORS_ORIGIN: str = ""
    CORS_ORIGINS: List[str] = []
    BACKEND_CORS_ORIGINS: List[str] = []

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

    @field_validator("CORS_ORIGINS", "BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_list(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("["):
                import json
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [i.strip() for i in v_str.split(",") if i.strip()]
        elif isinstance(v, (list, set, tuple)):
            return list(v)
        return []

    @model_validator(mode="after")
    def assemble_cors_origins(self) -> "Settings":
        """
        Dynamically assemble all allowed origins from .env:
        Supports DOMAIN, FRONTEND_DOMAIN, FRONTEND_ORIGIN, CORS_ORIGIN, and CORS_ORIGINS.
        Automatically expands domain-only values to include both http:// and https://.
        """
        origins: List[str] = []

        def add_entry(val: Any):
            if not val:
                return
            if isinstance(val, (list, set, tuple)):
                for v in val:
                    add_entry(v)
                return
            for item in str(val).split(","):
                item = item.strip()
                if not item:
                    continue
                # If given a domain or host without protocol (e.g. 'localhost:5173' or 'srv1256219.com')
                if not item.startswith(("http://", "https://")) and item != "*":
                    for scheme in ("http://", "https://"):
                        full = f"{scheme}{item}"
                        if full not in origins:
                            origins.append(full)
                else:
                    if item not in origins:
                        origins.append(item)

        # Collect from all possible configuration fields in .env
        add_entry(self.CORS_ORIGINS)
        add_entry(self.BACKEND_CORS_ORIGINS)
        add_entry(self.CORS_ORIGIN)
        add_entry(self.FRONTEND_ORIGIN)
        add_entry(self.FRONTEND_DOMAIN)
        add_entry(self.DOMAIN)

        # Default fallback if nothing specified
        if not origins:
            origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

        self.CORS_ORIGINS = origins
        return self

    @property
    def cors_origins(self) -> List[str]:
        """Backward-compatible alias for CORS_ORIGINS."""
        return self.CORS_ORIGINS


settings = Settings()

