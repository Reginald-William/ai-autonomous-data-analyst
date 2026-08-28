"""
Integration tests for POST /upload, using FastAPI's TestClient (real HTTP
routing, validation, and response handling — no real server process). These
port the manually-run scenarios from tests/TEST_RESULTS.md's V5 section
(unreproducible today since those models are dead — see PHASES.md Phase 1a)
into automated tests, using FakeGroqClient (conftest.py) instead of a real
Groq call.

Every test needs tmp_data_dir so uploaded files land in a throwaway temp
folder instead of the real data/ directory, and needs to patch
analyst_service.build_agents so the request's LLM calls hit the fake client
instead of attempting a real network call.
"""
from unittest.mock import patch

from src.services import analyst_service
from tests.conftest import FakeGroqClient


def _with_fake_client(fake_client):
    """Context manager that patches build_agents for the duration of one
    request, exactly as tests/integration/test_analyst_orchestration.py
    does — captures the original before patching to avoid the
    self-referencing infinite recursion hit there originally."""
    original_build_agents = analyst_service.build_agents
    return patch.object(
        analyst_service, "build_agents", lambda client=None: original_build_agents(client=fake_client)
    )


def test_first_upload_returns_answer_and_session_id(api_client, tmp_data_dir, sample_csv_path):
    fake_client = FakeGroqClient(
        plan={"task_type": "analysis", "agents": ["python"], "reasoning": "total revenue"},
        code="print(df['revenue'].sum())",
    )

    with _with_fake_client(fake_client):
        with open(sample_csv_path, "rb") as f:
            response = api_client.post(
                "/upload",
                data={"question": "What is total revenue?"},
                files={"file": ("sample_data.csv", f, "text/csv")},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["session_id"]
    assert body["file_name"] == "sample_data.csv"  # original filename, not the UUID-saved path


def test_followup_question_reuses_session(api_client, tmp_data_dir, sample_csv_path):
    fake_client = FakeGroqClient(plan={"task_type": "query", "agents": ["sql"], "reasoning": "filter"})

    with _with_fake_client(fake_client):
        with open(sample_csv_path, "rb") as f:
            first = api_client.post(
                "/upload",
                data={"question": "What is total revenue?"},
                files={"file": ("sample_data.csv", f, "text/csv")},
            )
        session_id = first.json()["session_id"]

        second = api_client.post(
            "/upload",
            data={"question": "Show sales over 10000", "session_id": session_id},
        )

    assert second.status_code == 200
    assert second.json()["session_id"] == session_id
    assert second.json()["file_name"] == "sample_data.csv"


def test_chart_question_returns_chart_path(api_client, tmp_data_dir, sample_csv_path):
    fake_client = FakeGroqClient(
        plan={"task_type": "visualization", "agents": ["python", "chart"], "reasoning": "bar chart"},
    )

    with _with_fake_client(fake_client):
        with open(sample_csv_path, "rb") as f:
            response = api_client.post(
                "/upload",
                data={"question": "Show me a bar chart of revenue by product"},
                files={"file": ("sample_data.csv", f, "text/csv")},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["chart_path"] is not None
    assert "chart" in body["agents_used"]


def test_non_csv_file_rejected(api_client, tmp_data_dir):
    response = api_client.post(
        "/upload",
        data={"question": "What is this?"},
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 400
    assert "CSV" in response.json()["detail"]


def test_empty_csv_rejected(api_client, tmp_data_dir, empty_csv_path):
    """empty.csv has a header row and zero data rows — non-empty bytes, so
    it passes routes/ask.py's "uploaded file is empty" byte-count check and
    the pd.read_csv(nrows=0) parseability check. It's actually
    analyst_service.analyse()'s row_count == 0 guard that rejects it,
    confirmed by running this exact request and reading the real response."""
    with open(empty_csv_path, "rb") as f:
        response = api_client.post(
            "/upload",
            data={"question": "How many rows?"},
            files={"file": ("empty.csv", f, "text/csv")},
        )

    assert response.status_code == 400
    assert "no data rows" in response.json()["detail"]


def test_corrupt_file_with_csv_extension_rejected(api_client, tmp_data_dir):
    # PNG magic bytes, not valid CSV text
    response = api_client.post(
        "/upload",
        data={"question": "What is this?"},
        files={"file": ("fake.csv", b"\x89PNG\r\n\x1a\n\x00\x00\x00", "text/csv")},
    )

    assert response.status_code == 400
    assert "valid CSV" in response.json()["detail"]


def test_invalid_session_id_returns_404(api_client, tmp_data_dir):
    response = api_client.post(
        "/upload",
        data={"question": "Anything", "session_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_no_file_and_no_session_id_returns_400(api_client, tmp_data_dir):
    response = api_client.post("/upload", data={"question": "Anything"})

    assert response.status_code == 400
    assert "No file uploaded" in response.json()["detail"]


def test_session_id_takes_priority_over_file(api_client, tmp_data_dir, sample_csv_path):
    """Matches TEST_RESULTS.md scenario 10: when both session_id and file are
    sent, the session is reused and the new file is ignored."""
    fake_client = FakeGroqClient(plan={"task_type": "analysis", "agents": ["python"]})

    with _with_fake_client(fake_client):
        with open(sample_csv_path, "rb") as f:
            first = api_client.post(
                "/upload",
                data={"question": "Total revenue?"},
                files={"file": ("sample_data.csv", f, "text/csv")},
            )
        session_id = first.json()["session_id"]

        with open(sample_csv_path, "rb") as f:
            second = api_client.post(
                "/upload",
                data={"question": "Total revenue again?", "session_id": session_id},
                files={"file": ("different_name.csv", f, "text/csv")},
            )

    assert second.status_code == 200
    # file_name still reflects the ORIGINAL session's filename, not the
    # ignored "different_name.csv" from this request
    assert second.json()["file_name"] == "sample_data.csv"


def test_oversized_file_rejected(api_client, tmp_data_dir, monkeypatch):
    """Exercises the 10MB MAX_FILE_SIZE guard in routes/ask.py without
    actually uploading 10MB — monkeypatches the limit down to a few bytes
    for this test only."""
    from src.routes import ask as ask_route
    monkeypatch.setattr(ask_route, "MAX_FILE_SIZE", 5)

    response = api_client.post(
        "/upload",
        data={"question": "Anything"},
        files={"file": ("sample_data.csv", b"date,revenue\n2024-01-01,100\n", "text/csv")},
    )

    assert response.status_code == 400
    assert "10MB" in response.json()["detail"] or "size" in response.json()["detail"].lower()
