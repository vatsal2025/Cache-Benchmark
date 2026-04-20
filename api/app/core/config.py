from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://cb_user:cb_password@localhost:5432/captcha_benchmark"
    SYNC_DATABASE_URL: str = "postgresql://cb_user:cb_password@localhost:5432/captcha_benchmark"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "dev-secret-key-change-in-production-32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_PATH: str = "./storage"
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"

    MAX_UPLOAD_SIZE_MB: int = 500
    DEFAULT_N_DAY_DELAY: int = 7
    DEFAULT_HOLDOUT_PCT: int = 5
    MIN_LABELS_PER_GROUP: int = 400

    BPAS_ALERT_THRESHOLD: float = 0.10


settings = Settings()
