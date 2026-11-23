from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(REPO_ROOT / ".env",), extra="ignore")

    gemini_api_key: str = ""
    llm_model_fast: str = "gemini-2.5-flash"
    llm_model_strong: str = "gemini-2.5-pro"
    daily_token_budget: int = 200_000
    llm_requests_per_minute: int = 20
    freshness_days: int = 90
    data_dir: Path = REPO_ROOT / "data"
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
