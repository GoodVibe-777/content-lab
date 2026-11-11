from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Content Lab API"
    app_env: str = "development"
    app_data_dir: Path = Path("./data")

    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    groq_model: str = "llama-3.3-70b-versatile"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def projects_dir(self) -> Path:
        path = self.app_data_dir / "projects"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
