from dotenv import load_dotenv
load_dotenv()

import os
from groq import Groq
import logging

MODEL_NAME = "llama-3.1-8b-instant"  # Using as const for now, can be made dynamic later if needed


logger = logging.getLogger(__name__)

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

def get_llm_client():
    return client
