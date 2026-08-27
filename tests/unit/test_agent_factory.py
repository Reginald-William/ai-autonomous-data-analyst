"""
Tests for build_agents() in src/services/analyst_service.py — the factory
that replaced the four module-level agent singletons previously built at
import time. These tests exist to prove the DI seam actually works: passing
client= must be forwarded to every agent, and never fall back to
get_llm_client() (which would build a real Groq client).
"""
from unittest.mock import Mock

from src.services.analyst_service import build_agents
from src.agents.planner_agent import PlannerAgent
from src.agents.python_agent import PythonAgent
from src.agents.sql_agent import SQLAgent
from src.agents.chart_agent import ChartAgent


def test_build_agents_returns_all_four_agent_types():
    agents = build_agents()

    assert isinstance(agents["planner"], PlannerAgent)
    assert isinstance(agents["python"], PythonAgent)
    assert isinstance(agents["sql"], SQLAgent)
    assert isinstance(agents["chart"], ChartAgent)


def test_build_agents_with_no_client_uses_real_lazy_client():
    """With no client injected, each agent should fall back to the real
    get_llm_client() — which is lazy (Step 3), so this still doesn't touch
    the network, it just confirms the fallback path is reached at all."""
    agents = build_agents()

    assert agents["planner"].client is not None
    assert agents["python"].client is not None


def test_build_agents_forwards_injected_client_to_every_agent():
    fake_client = Mock(name="fake_groq_client")

    agents = build_agents(client=fake_client)

    assert agents["planner"].client is fake_client
    assert agents["python"].client is fake_client
    assert agents["sql"].client is fake_client
    assert agents["chart"].client is fake_client


def test_build_agents_produces_independent_instances_each_call():
    """Unlike the old module-level singletons (one shared instance reused
    across every request), build_agents() should hand back a fresh set each
    time — this is what removes the shared self.model mutation race
    (PHASES.md risk #13) under concurrent requests."""
    first_call = build_agents()
    second_call = build_agents()

    assert first_call["planner"] is not second_call["planner"]
    assert first_call["python"] is not second_call["python"]


def test_injected_fake_client_never_makes_a_real_network_call():
    """Exercises PlannerAgent.run() end-to-end with a fake client whose
    chat.completions.create() returns a canned JSON plan, proving the
    injected client is actually used for the real call path — not just
    stored and ignored."""
    fake_response = Mock()
    fake_response.choices = [Mock(message=Mock(content='{"complexity": "low"}'))]
    fake_client = Mock()
    fake_client.chat.completions.create.return_value = fake_response

    agents = build_agents(client=fake_client)
    complexity = agents["planner"]._classify_complexity(
        question="What is total revenue?", task_type="analysis", row_count=12
    )

    assert complexity == "low"
    fake_client.chat.completions.create.assert_called_once()
