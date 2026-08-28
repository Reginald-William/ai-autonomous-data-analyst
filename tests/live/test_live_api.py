"""
The only tests in this suite that make real calls to the Groq API — real
network requests, real (small) cost against the free tier, and genuinely
non-deterministic LLM output. Marked live_api (registered in pytest.ini),
which addopts = -m "not live_api" excludes by default, so these never run
in a normal `pytest` invocation or in CI's default job (CLAUDE.md and
PHASES.md are explicit: never put GROQ_API_KEY in the default CI job).

Run explicitly with: pytest -m live_api

Kept intentionally small (3 tests) and loose in what they assert — real LLM
output varies run to run, so these check "did we get a live, working
response shaped correctly," not exact wording. Their real value is catching
another Groq model retirement early and cheaply (see PHASES.md Phase 1a —
this exact failure mode killed the app once already) and proving the full
real pipeline (planner -> agent -> LLM -> response) works end to end with
an actual key, which every other test in this suite deliberately avoids.
"""
import pytest

from src.config import get_settings
from src.services.llm_service import get_llm_client, MODEL_ROUTING
from src.services.analyst_service import analyse

pytestmark = pytest.mark.live_api

_settings = get_settings()

requires_real_key = pytest.mark.skipif(
    not _settings.groq_api_key,
    reason="No GROQ_API_KEY configured — set one in .env to run live_api tests",
)


@requires_real_key
@pytest.mark.parametrize("model", sorted(set(MODEL_ROUTING.values())))
def test_configured_model_responds_to_a_real_call(model):
    """Regression guard for the incident that started this whole project's
    testing effort: all three previously configured Llama model IDs were
    silently retired from the Groq API (PHASES.md Phase 1a). This calls
    each currently configured model with a trivial prompt — if Groq ever
    retires openai/gpt-oss-20b or -120b, this fails loudly here instead of
    the app dying at the planner's first real request."""
    client = get_llm_client()

    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[{"role": "user", "content": "Reply with exactly one word: hello"}],
    )

    content = response.choices[0].message.content
    assert content and content.strip() != ""


@requires_real_key
def test_real_ask_request_answers_a_simple_question(tmp_csv_file):
    """One real end-to-end request through the actual pipeline: planner
    (real routing + complexity calls) -> python or sql agent (real code
    generation + execution) -> a real AnalysisResponse. Every other
    orchestration test in this suite uses FakeGroqClient — this is the one
    place the real thing gets exercised."""
    response = analyse(
        question="What is the total revenue?",
        file_path=str(tmp_csv_file),
    )

    assert response.status == "success"
    assert response.result.strip() != ""
    assert response.model_used in MODEL_ROUTING.values()


@requires_real_key
def test_real_out_of_scope_question_is_handled(tmp_csv_file):
    """Proves the real planner (not FakeGroqClient) correctly classifies an
    unrelated question as out of scope end to end."""
    response = analyse(
        question="What is the capital of France?",
        file_path=str(tmp_csv_file),
    )

    assert response.status == "out_of_scope"
    assert response.agents_used == []
