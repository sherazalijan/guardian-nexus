
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(
        default="Guardian Nexus Backend",
        validation_alias="APP_NAME",
    )
    app_env: str = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    debug: bool = Field(
        default=True,
        validation_alias="DEBUG",
    )
    cors_origins: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )

    assemblyai_api_key: str | None = Field(
        default=None,
        validation_alias="ASSEMBLYAI_API_KEY",
    )
    assemblyai_provider: str = Field(
        default="mock",
        validation_alias="ASSEMBLYAI_PROVIDER",
    )
    nebius_api_key: str | None = Field(
        default=None,
        validation_alias="NEBIUS_API_KEY",
    )
    tavily_api_key: str | None = Field(
        default=None,
        validation_alias="TAVILY_API_KEY",
    )

    llm_provider: str = Field(
        default="mock",
        validation_alias="LLM_PROVIDER",
    )
    threat_intelligence_provider: str = Field(
        default="mock",
        validation_alias="THREAT_INTELLIGENCE_PROVIDER",
    )
    nebius_base_url: str = Field(
        default="https://api.tokenfactory.nebius.com/v1",
        validation_alias="NEBIUS_BASE_URL",
    )
    nebius_model: str = Field(
        default="",
        validation_alias="NEBIUS_MODEL",
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="LLM_TIMEOUT_SECONDS",
    )

    def model_post_init(self, __context: object) -> None:
        """Normalize empty optional API keys to None."""
        if self.assemblyai_api_key == "":
            self.assemblyai_api_key = None
        if self.nebius_api_key == "":
            self.nebius_api_key = None
        if self.tavily_api_key == "":
            self.tavily_api_key = None

    @property
    def cors_origin_list(self) -> list[str]:
        """Return configured CORS origins as a normalized list."""
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()
