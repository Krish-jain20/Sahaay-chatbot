from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(REPO_ROOT / ".env",), extra="ignore")

    gemini_api_key: str = ""
    llm_model_fast: str = "gemini-3.5-flash-lite"
    llm_model_strong: str = "gemini-3.5-flash"
    daily_token_budget: int = 200_000
    llm_requests_per_minute: int = 20
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_secret_key: str = ""
    auth_required: bool = True
    freshness_days: int = 90
    data_dir: Path = REPO_ROOT / "data"
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("supabase_url")
    @classmethod
    def _supabase_url_is_full_https(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if v and not (v.startswith("https://") and "." in v[len("https://") :]):
            raise ValueError(
                "SUPABASE_URL must be the full project URL, like https://<project-id>.supabase.co "
                "(not just the project id)"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
