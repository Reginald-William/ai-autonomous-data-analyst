"""
Tests for src/services/llm_service.py — model routing, retry budget, and
prompt sample-row lookups by complexity tier.

Note: importing this module builds a real Groq client object at import time
(see llm_service.py line 37), which requires GROQ_API_KEY to be set in the
environment — but building the client does not make a network call, so
these tests still run instantly with no real API access. Making the client
lazy is a Phase 2 concern, not something fixed here.
"""
import pytest

from src.services import llm_service

# The only two models confirmed live against the real Groq API on 2026-08-24
# (see PHASES.md — all three previously configured Llama models were found
# to be absent from the API entirely). If MODEL_ROUTING is ever changed to
# point at something else, this is the test that should catch it.
LIVE_MODELS = {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}


@pytest.mark.parametrize(
    "complexity, expected_model",
    [
        ("low", "openai/gpt-oss-20b"),
        ("medium", "openai/gpt-oss-120b"),
        ("high", "openai/gpt-oss-120b"),
    ],
)
def test_get_model_for_complexity_returns_expected_model(complexity, expected_model):
    assert llm_service.get_model_for_complexity(complexity) == expected_model


def test_get_model_for_complexity_falls_back_to_default_for_unknown_key():
    assert llm_service.get_model_for_complexity("nonsense") == llm_service.DEFAULT_MODEL


def test_get_model_for_complexity_falls_back_to_default_for_none():
    assert llm_service.get_model_for_complexity(None) == llm_service.DEFAULT_MODEL


@pytest.mark.parametrize(
    "complexity, expected_attempts",
    [
        ("low", 2),
        ("medium", 3),
        ("high", 5),
    ],
)
def test_get_retry_budget_returns_expected_attempts(complexity, expected_attempts):
    assert llm_service.get_retry_budget(complexity) == expected_attempts


def test_get_retry_budget_falls_back_to_medium_for_unknown_key():
    assert llm_service.get_retry_budget("nonsense") == llm_service.RETRY_BUDGET["medium"]


@pytest.mark.parametrize(
    "complexity, expected_rows",
    [
        ("low", 3),
        ("medium", 5),
        ("high", 10),
    ],
)
def test_get_sample_rows_returns_expected_row_count(complexity, expected_rows):
    assert llm_service.get_sample_rows(complexity) == expected_rows


def test_get_sample_rows_falls_back_to_medium_for_unknown_key():
    assert llm_service.get_sample_rows("nonsense") == llm_service.PROMPT_SAMPLE_ROWS["medium"]


def test_all_configured_models_are_confirmed_live():
    """
    Regression guard for the incident this phase started from: all three
    previously configured model IDs were silently removed from the Groq
    API. If a future edit reintroduces a dead model ID into MODEL_ROUTING,
    this test fails immediately instead of the app dying at the planner's
    first LLM call.
    """
    configured_models = set(llm_service.MODEL_ROUTING.values())
    assert configured_models <= LIVE_MODELS


def test_default_model_is_confirmed_live():
    assert llm_service.DEFAULT_MODEL in LIVE_MODELS
