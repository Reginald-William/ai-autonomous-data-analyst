from dotenv import load_dotenv
load_dotenv()

from functools import lru_cache
from groq import Groq
import logging

from src.config import get_settings

_settings = get_settings()

DEFAULT_MODEL = _settings.default_model

# Dynamic model routing based on task complexity.
# llama-3.1-8b-instant, llama-3.3-70b-versatile, and llama-4-scout were all
# removed from the Groq API (verified 2026-08-24 against the live API) — the
# only usable free-tier text models left are the two gpt-oss sizes below.
# Values now come from Settings (src/config.py) — see there for env var names.
MODEL_ROUTING = _settings.model_routing

# With only two usable models, "medium" and "high" now share a model ID.
# Complexity still needs to mean something, so it also drives retry budget
# and how much of the dataset gets sampled into the prompt.
RETRY_BUDGET = _settings.retry_budget

PROMPT_SAMPLE_ROWS = _settings.prompt_sample_rows

logger = logging.getLogger(__name__)


@lru_cache
def get_llm_client() -> Groq:
    """Lazily construct the Groq client on first use instead of at import
    time — so importing this module (and anything that imports it) no
    longer requires GROQ_API_KEY or makes any client setup happen as a side
    effect of `import src.main`."""
    return Groq(api_key=get_settings().groq_api_key)

def get_model_for_complexity(complexity: str) -> str:
    return MODEL_ROUTING.get(complexity, DEFAULT_MODEL)

def get_retry_budget(complexity: str) -> int:
    return RETRY_BUDGET.get(complexity, RETRY_BUDGET["medium"])

def get_sample_rows(complexity: str) -> int:
    return PROMPT_SAMPLE_ROWS.get(complexity, PROMPT_SAMPLE_ROWS["medium"])
