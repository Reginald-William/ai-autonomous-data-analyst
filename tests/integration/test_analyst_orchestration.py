"""
Integration tests for src/services/analyst_service.py's analyse() — the
real orchestration logic (planner -> dispatch -> agent -> response), driven
end-to-end with a FakeGroqClient (tests/conftest.py) instead of a real Groq
client. Unlike the Phase 1/2 unit tests, these exercise multiple components
together: the planner's routing decision actually determines which agent
analyse() dispatches to, exactly as it would in production.

These tests are also where PHASES.md flags two known bugs this phase is
meant to catch: the python/sql `elif` mutual exclusion, and the
chart-only-plan 500 (result=None fails AnalysisResponse's Pydantic
validation). See docs/BUGS_FOUND.md for the write-up of anything confirmed.
"""
from unittest.mock import patch

from tests.conftest import FakeGroqClient
from src.services import analyst_service


def _analyse_with_fake(fake_client, **kwargs):
    """Patch build_agents so analyse() uses our fake client instead of the
    real lazy Groq client, then run analyse() for real.

    Captures the original build_agents before patching — the replacement
    lambda must call the *original* function, not `analyst_service.build_agents`,
    since that name now points at the lambda itself once patch.object takes
    effect (self-referencing it caused infinite recursion here initially)."""
    original_build_agents = analyst_service.build_agents
    with patch.object(
        analyst_service, "build_agents", lambda client=None: original_build_agents(client=fake_client)
    ):
        return analyst_service.analyse(**kwargs)


def test_python_routing_returns_success(tmp_csv_file):
    fake_client = FakeGroqClient(
        plan={"task_type": "analysis", "agents": ["python"], "reasoning": "total revenue"},
        complexity="low",
        code="print(df['revenue'].sum())",
    )

    response = _analyse_with_fake(
        fake_client, question="What is total revenue?", file_path=str(tmp_csv_file)
    )

    assert response.status == "success"
    assert "python" in response.agents_used
    assert response.result.strip() != ""


def test_sql_routing_returns_success(tmp_csv_file):
    fake_client = FakeGroqClient(
        plan={"task_type": "query", "agents": ["sql"], "reasoning": "filter rows"},
        complexity="low",
        sql="SELECT * FROM sample_data WHERE revenue > 10000;",
    )

    response = _analyse_with_fake(
        fake_client, question="Show sales over 10000", file_path=str(tmp_csv_file)
    )

    assert response.status == "success"
    assert "sql" in response.agents_used


def test_out_of_scope_question_short_circuits(tmp_csv_file):
    fake_client = FakeGroqClient(
        plan={"task_type": "out_of_scope", "agents": ["none"], "reasoning": "unrelated to data"},
    )

    response = _analyse_with_fake(
        fake_client, question="What is the capital of France?", file_path=str(tmp_csv_file)
    )

    assert response.status == "out_of_scope"
    assert response.agents_used == []


def test_plan_with_both_python_and_sql_should_run_sql_too(tmp_csv_file):
    """PHASES.md risk register / Phase 3 scope: analyst_service.py dispatches
    with `if "python" ... elif "sql" ...`, so a plan naming both agents
    silently drops sql. See docs/BUGS_FOUND.md."""
    fake_client = FakeGroqClient(
        plan={"task_type": "analysis", "agents": ["python", "sql"], "reasoning": "needs both"},
    )

    response = _analyse_with_fake(
        fake_client, question="Compute something and also filter rows", file_path=str(tmp_csv_file)
    )

    assert "python" in response.agents_used
    assert "sql" in response.agents_used  # currently FAILS — sql is silently skipped


def test_chart_only_plan_does_not_500(tmp_csv_file):
    """PHASES.md risk register / Phase 3 scope: a plan with only "chart" (no
    python/sql) leaves result=None, which fails AnalysisResponse's Pydantic
    validation (result: str, not Optional) and should surface as a handled
    error, not an unhandled crash. See docs/BUGS_FOUND.md."""
    fake_client = FakeGroqClient(
        plan={"task_type": "visualization", "agents": ["chart"], "reasoning": "chart only, no computation"},
    )

    response = _analyse_with_fake(
        fake_client, question="Show me a chart", file_path=str(tmp_csv_file)
    )

    assert response.status in ("success", "failed")  # currently raises instead of returning a response
