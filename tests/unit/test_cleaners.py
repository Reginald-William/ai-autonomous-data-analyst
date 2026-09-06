"""
Tests for the clean_code / clean_sql helpers that strip markdown code-fence
formatting off LLM output before it gets exec'd or run as SQL. PythonAgent
and SQLAgent still have their own near-identical copies of this logic, so
each gets its own set of parametrized cases. ChartAgent no longer has a
clean_code method — its Phase 4 redesign has the LLM return a small JSON
chart spec (parsed via json.loads), not code to be exec'd, so there's
nothing to strip code fences from.

Building an agent instance (e.g. PythonAgent()) does construct a Groq client
via get_llm_client(), same as importing llm_service directly — but no
network call happens until an LLM method is actually called, so this stays
fast and offline.
"""
import pytest

from src.agents.python_agent import PythonAgent
from src.agents.sql_agent import SQLAgent


CODE_CASES = [
    ("total = df['revenue'].sum()\nprint(total)", "total = df['revenue'].sum()\nprint(total)"),
    ("```python\nprint(1)\n```", "print(1)"),
    ("```\nprint(1)\n```", "print(1)"),
    ("  \nprint(1)\n  ", "print(1)"),
    ("", ""),
]

SQL_CASES = [
    ("SELECT * FROM sales", "SELECT * FROM sales"),
    ("```sql\nSELECT * FROM sales\n```", "SELECT * FROM sales"),
    ("```\nSELECT * FROM sales\n```", "SELECT * FROM sales"),
    ("  \nSELECT * FROM sales\n  ", "SELECT * FROM sales"),
    ("", ""),
]


@pytest.mark.parametrize("raw, expected", CODE_CASES)
def test_python_agent_clean_code(raw, expected):
    agent = PythonAgent()
    assert agent.clean_code(raw) == expected


@pytest.mark.parametrize("raw, expected", SQL_CASES)
def test_sql_agent_clean_sql(raw, expected):
    agent = SQLAgent()
    assert agent.clean_sql(raw) == expected
