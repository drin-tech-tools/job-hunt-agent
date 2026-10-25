"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Ordered fallback when GEMINI_CHAT_MODEL is unset.
# 2.5 models are unavailable to many new API keys — skip them.
GEMINI_MODEL_FALLBACK: list[str] = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-3.8-flash",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    gemini_chat_model: str | None = None

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    allowed_origins: str = "http://localhost:3000"

    jsearch_api_key: str | None = None

    agent_max_steps: int = 8
    agent_overall_timeout_s: float = 90.0
    tool_timeout_s: float = 20.0
    tool_max_retries: int = 2
    jobs_cache_ttl_s: int = 3600

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def chat_models(self) -> list[str]:
        if self.gemini_chat_model:
            pinned = self.gemini_chat_model
            rest = [m for m in GEMINI_MODEL_FALLBACK if m != pinned]
            return [pinned, *rest]
        return list(GEMINI_MODEL_FALLBACK)

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def jsearch_enabled(self) -> bool:
        return bool(self.jsearch_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
