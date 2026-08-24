from dotenv import load_dotenv
load_dotenv()

import os
from groq import Groq
import logging

DEFAULT_MODEL = "openai/gpt-oss-120b"

# Dynamic model routing based on task complexity.
# llama-3.1-8b-instant, llama-3.3-70b-versatile, and llama-4-scout were all
# removed from the Groq API (verified 2026-08-24 against the live API) — the
# only usable free-tier text models left are the two gpt-oss sizes below.
MODEL_ROUTING = {
    "low": "openai/gpt-oss-20b",       # Simple tasks: count, total, basic lookups
    "medium": "openai/gpt-oss-120b",   # Medium tasks: group by, filter+aggregate, charts
    "high": "openai/gpt-oss-120b",     # Complex tasks: multi-step, trend analysis, ambiguous
}

# With only two usable models, "medium" and "high" now share a model ID.
# Complexity still needs to mean something, so it also drives retry budget
# and how much of the dataset gets sampled into the prompt.
RETRY_BUDGET = {
    "low": 2,
    "medium": 3,
    "high": 5,
}

PROMPT_SAMPLE_ROWS = {
    "low": 3,
    "medium": 5,
    "high": 10,
}

logger = logging.getLogger(__name__)

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

def get_llm_client():
    return client

def get_model_for_complexity(complexity: str) -> str:
    return MODEL_ROUTING.get(complexity, DEFAULT_MODEL)

def get_retry_budget(complexity: str) -> int:
    return RETRY_BUDGET.get(complexity, RETRY_BUDGET["medium"])

def get_sample_rows(complexity: str) -> int:
    return PROMPT_SAMPLE_ROWS.get(complexity, PROMPT_SAMPLE_ROWS["medium"])
