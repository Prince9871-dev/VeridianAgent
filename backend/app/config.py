from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Veridian Assist Backend Configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Veridian Assist — IT Service Agent"
    app_version: str = "1.0.0"
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")

    # Networking
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./veridian.db",
        alias="DATABASE_URL",
    )

    # LLM Provider Abstraction
    # Supported: "mock", "gemini", "openai"
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gemini-1.5-flash", alias="LLM_MODEL")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # Authoritative Data Pack Path
    datapack_path: str = Field(
        default="../data/source/Assignment_2_DataPack.pdf",
        alias="DATAPACK_PATH",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
