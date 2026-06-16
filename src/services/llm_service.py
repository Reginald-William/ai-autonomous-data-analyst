from dotenv import load_dotenv
load_dotenv()

import os
from groq import Groq
import logging

DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Dynamic model routing based on task complexity
MODEL_ROUTING = {
    "low": "llama-3.1-8b-instant",       # Simple tasks: count, total, basic lookups
    "medium": "llama-3.3-70b-versatile",  # Medium tasks: group by, filter+aggregate, charts
    "high": "meta-llama/llama-4-scout-17b-16e-instruct",  # Complex tasks: multi-step, trend analysis, ambiguous
}

logger = logging.getLogger(__name__)

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

def get_llm_client():
    return client

def get_model_for_complexity(complexity: str) -> str:
    return MODEL_ROUTING.get(complexity, DEFAULT_MODEL)
