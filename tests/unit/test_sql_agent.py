"""
Tests for src/agents/sql_agent.py's complexity-scaled prompt scaffolding —
the SQL-agent half of the same Phase 4 follow-up covered in
test_python_agent.py. complexity="high" should splice
HIGH_COMPLEXITY_SQL_SCAFFOLDING into the prompt; low/medium should not.
"""
from src.agents.sql_agent import HIGH_COMPLEXITY_SQL_SCAFFOLDING, SQLAgent


class _RecordingClient:
    """Captures the last prompt it was asked to complete, and returns a
    fixed, always-valid SQL response."""

    def __init__(self):
        self.last_prompt = None
        self.chat = self
        self.completions = self

    def create(self, model, messages, temperature=0.1, **kwargs):
        self.last_prompt = messages[-1]["content"]
        message = type("Message", (), {"content": "SELECT 1;"})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


_DB_INFO = {"table_name": "sales", "columns": ["region", "revenue"], "row_count": 1000}


def test_generate_sql_includes_scaffolding_for_high_complexity():
    client = _RecordingClient()
    agent = SQLAgent(client=client)

    agent.generate_sql("Which region grew fastest?", _DB_INFO, complexity="high")

    assert HIGH_COMPLEXITY_SQL_SCAFFOLDING.strip() in client.last_prompt


def test_generate_sql_omits_scaffolding_for_medium_complexity():
    client = _RecordingClient()
    agent = SQLAgent(client=client)

    agent.generate_sql("Show sales over 10000", _DB_INFO, complexity="medium")

    assert HIGH_COMPLEXITY_SQL_SCAFFOLDING.strip() not in client.last_prompt


def test_generate_sql_defaults_to_no_scaffolding_when_complexity_omitted():
    client = _RecordingClient()
    agent = SQLAgent(client=client)

    agent.generate_sql("Show sales over 10000", _DB_INFO)

    assert HIGH_COMPLEXITY_SQL_SCAFFOLDING.strip() not in client.last_prompt


def test_fix_sql_includes_scaffolding_for_high_complexity():
    client = _RecordingClient()
    agent = SQLAgent(client=client)

    agent.fix_sql(
        "Which region grew fastest?",
        failed_sql="SELECT * FROM sales WHERE",
        error="syntax error",
        db_info=_DB_INFO,
        complexity="high",
    )

    assert HIGH_COMPLEXITY_SQL_SCAFFOLDING.strip() in client.last_prompt


def test_fix_sql_omits_scaffolding_for_medium_complexity():
    client = _RecordingClient()
    agent = SQLAgent(client=client)

    agent.fix_sql(
        "Show sales over 10000",
        failed_sql="SELECT * FROM sales WHERE",
        error="syntax error",
        db_info=_DB_INFO,
        complexity="medium",
    )

    assert HIGH_COMPLEXITY_SQL_SCAFFOLDING.strip() not in client.last_prompt
