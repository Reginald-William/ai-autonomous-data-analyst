"""
Tests for src/agents/python_agent.py's complexity-scaled prompt scaffolding
(Phase 4 follow-up — see PHASES.md's "Complexity tiering lost its third
lever" section). complexity="high" should splice HIGH_COMPLEXITY_SCAFFOLDING
into the prompt sent to the LLM; low/medium should leave the prompt
unchanged from before this feature existed.

Uses a fake client that just records the prompt it was called with — no
real Groq call, and no need to inspect generated code, since the thing
under test is what gets sent to the model, not what it sends back.
"""
from src.agents.python_agent import HIGH_COMPLEXITY_SCAFFOLDING, PythonAgent


class _RecordingClient:
    """Captures the last prompt it was asked to complete, and returns a
    fixed, always-valid response so callers don't need to handle real
    variation."""

    def __init__(self):
        self.last_prompt = None
        self.chat = self
        self.completions = self

    def create(self, model, messages, temperature=0.1, **kwargs):
        self.last_prompt = messages[-1]["content"]
        message = type("Message", (), {"content": "print(1)"})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


def test_generate_code_includes_scaffolding_for_high_complexity():
    client = _RecordingClient()
    agent = PythonAgent(client=client)

    agent.generate_code("Which region is growing fastest?", complexity="high")

    assert HIGH_COMPLEXITY_SCAFFOLDING.strip() in client.last_prompt


def test_generate_code_omits_scaffolding_for_medium_complexity():
    client = _RecordingClient()
    agent = PythonAgent(client=client)

    agent.generate_code("What is total revenue?", complexity="medium")

    assert HIGH_COMPLEXITY_SCAFFOLDING.strip() not in client.last_prompt


def test_generate_code_omits_scaffolding_for_low_complexity():
    client = _RecordingClient()
    agent = PythonAgent(client=client)

    agent.generate_code("What is total revenue?", complexity="low")

    assert HIGH_COMPLEXITY_SCAFFOLDING.strip() not in client.last_prompt


def test_generate_code_defaults_to_no_scaffolding_when_complexity_omitted():
    """generate_code()'s complexity parameter defaults to "medium" — a
    caller that doesn't pass it explicitly shouldn't silently get
    high-complexity scaffolding."""
    client = _RecordingClient()
    agent = PythonAgent(client=client)

    agent.generate_code("What is total revenue?")

    assert HIGH_COMPLEXITY_SCAFFOLDING.strip() not in client.last_prompt


def test_fix_code_includes_scaffolding_for_high_complexity():
    client = _RecordingClient()
    agent = PythonAgent(client=client)

    agent.fix_code(
        "Which region is growing fastest?",
        failed_code="df.groupby('region')",
        error="SyntaxError",
        complexity="high",
    )

    assert HIGH_COMPLEXITY_SCAFFOLDING.strip() in client.last_prompt


def test_fix_code_omits_scaffolding_for_medium_complexity():
    client = _RecordingClient()
    agent = PythonAgent(client=client)

    agent.fix_code(
        "What is total revenue?",
        failed_code="df['revenue'.sum()",
        error="SyntaxError",
        complexity="medium",
    )

    assert HIGH_COMPLEXITY_SCAFFOLDING.strip() not in client.last_prompt


def test_run_threads_complexity_into_generate_code(tmp_path, sample_csv_path):
    """End-to-end within the agent: run() classifies nothing itself (that's
    the planner's job), but it must forward whatever complexity it's given
    all the way into the actual LLM prompt, not just use it for
    model/retry-budget selection."""
    import shutil
    csv_path = tmp_path / "sample.csv"
    shutil.copy(sample_csv_path, csv_path)

    client = _RecordingClient()
    agent = PythonAgent(client=client)

    agent.run("Which region is growing fastest?", str(csv_path), complexity="high")

    assert HIGH_COMPLEXITY_SCAFFOLDING.strip() in client.last_prompt
