"""
Centralized configuration. Owns every value that was previously hardcoded
across llm_service, session_service, rag_service, database_service, the
agents, and routes/ask.py — model IDs, retry/prompt tiering, TTLs, file size
limits, paths, embedding model, RAG tuning, and LLM temperatures.

Settings() reads from environment variables (and a .env file, via
pydantic-settings' built-in dotenv support) with defaults matching current
behavior, so existing deployments keep working with zero env changes.
Use get_settings() rather than constructing Settings() directly — it caches
a single instance per process, mirroring the old module-level constants.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Groq API ---
    groq_api_key: str = ""

    # --- Model routing ---
    # Only two usable free-tier text models exist on Groq (see llm_service.py
    # history) — "medium" and "high" intentionally share a model ID, with
    # retry budget and prompt richness carrying the rest of the distinction.
    model_low: str = "openai/gpt-oss-20b"
    model_medium: str = "openai/gpt-oss-120b"
    model_high: str = "openai/gpt-oss-120b"
    default_model: str = "openai/gpt-oss-120b"

    retry_budget_low: int = 2
    retry_budget_medium: int = 3
    retry_budget_high: int = 5

    # Minimum rows required to justify the high complexity model/tier
    high_complexity_row_threshold: int = 500

    # --- LLM call temperatures ---
    temperature_routing: float = 0.1      # planner: agent routing call
    temperature_complexity: float = 0.0   # planner: complexity classifier call
    temperature_codegen: float = 0.1      # python/sql/chart code generation

    # --- Sessions ---
    session_ttl_minutes: int = 30

    # --- Uploads ---
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    # --- Paths ---
    data_dir: str = "data"
    uploads_dir: str = "data/uploads"
    charts_dir: str = "data/charts"
    docs_dir: str = "docs"

    # --- RAG ---
    embedding_model: str = "all-MiniLM-L6-v2"
    rag_top_k: int = 3
    rag_distance_threshold: float = 1.5

    @property
    def model_routing(self) -> dict:
        return {"low": self.model_low, "medium": self.model_medium, "high": self.model_high}

    @property
    def retry_budget(self) -> dict:
        return {"low": self.retry_budget_low, "medium": self.retry_budget_medium, "high": self.retry_budget_high}


@lru_cache
def get_settings() -> Settings:
    return Settings()
