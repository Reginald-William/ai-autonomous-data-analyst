"""
Integration tests for POST /ask — the original JSON, file_path-based
endpoint kept for backward compatibility after /upload shipped in V5 (see
CLAUDE.md's Request Flow diagram). Uses the same api_client (lifespan
skipped) and FakeGroqClient (no real Groq calls) fixtures as
test_upload_endpoint.py.
"""
from unittest.mock import patch

import pytest

from src.services import analyst_service
from tests.conftest import FakeGroqClient


def _with_fake_client(fake_client):
    original_build_agents = analyst_service.build_agents
    return patch.object(
        analyst_service, "build_agents", lambda client=None: original_build_agents(client=fake_client)
    )


def test_ask_with_valid_file_path_returns_success(api_client, tmp_data_dir, tmp_csv_file):
    fake_client = FakeGroqClient(
        plan={"task_type": "analysis", "agents": ["python"], "reasoning": "total revenue"},
        code="print(df['revenue'].sum())",
    )

    with _with_fake_client(fake_client):
        response = api_client.post(
            "/ask",
            json={"question": "What is total revenue?", "file_path": str(tmp_csv_file)},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"


def test_ask_auto_generates_session_id(api_client, tmp_data_dir, tmp_csv_file):
    """/ask predates session_id support — analyst_service.analyse() auto-
    generates one (str(uuid4())) for backward compat rather than requiring
    the caller to supply it. See analyst_service.py's session_id is None
    branch."""
    fake_client = FakeGroqClient(plan={"task_type": "analysis", "agents": ["python"]})

    with _with_fake_client(fake_client):
        response = api_client.post(
            "/ask",
            json={"question": "What is total revenue?", "file_path": str(tmp_csv_file)},
        )

    body = response.json()
    assert body["session_id"]  # non-empty, auto-generated


def test_ask_two_calls_get_different_session_ids(api_client, tmp_data_dir, tmp_csv_file):
    """Unlike /upload, /ask has no session reuse mechanism — every call
    generates a fresh session_id, even for the same file_path."""
    fake_client = FakeGroqClient(plan={"task_type": "analysis", "agents": ["python"]})

    with _with_fake_client(fake_client):
        first = api_client.post(
            "/ask", json={"question": "Q1", "file_path": str(tmp_csv_file)}
        )
        second = api_client.post(
            "/ask", json={"question": "Q2", "file_path": str(tmp_csv_file)}
        )

    assert first.json()["session_id"] != second.json()["session_id"]


def test_ask_with_nonexistent_file_returns_404(api_client, tmp_data_dir):
    response = api_client.post(
        "/ask",
        json={"question": "Anything", "file_path": "does_not_exist.csv"},
    )

    assert response.status_code == 404


def test_ask_with_empty_csv_returns_400(api_client, tmp_data_dir, empty_csv_path):
    response = api_client.post(
        "/ask",
        json={"question": "How many rows?", "file_path": str(empty_csv_path)},
    )

    assert response.status_code == 400
    assert "no data rows" in response.json()["detail"]


def test_ask_missing_required_field_returns_400():
    """Exercises main.py's RequestValidationError handler, which converts
    FastAPI's default verbose 422 into a clean 400 (see main.py)."""
    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)
    response = client.post("/ask", json={"question": "Anything"})  # missing file_path

    assert response.status_code == 400
    assert "Invalid request" in response.json()["detail"]


@pytest.mark.xfail(
    reason="Known path-traversal hole — /ask's caller-supplied file_path is "
    "completely unvalidated. Documented in CLAUDE.md and PHASES.md risk #3 "
    "as intentionally deferred to Phase 5 (Docker + Cloud Run + security), "
    "not fixed here. This test documents the gap and should start failing "
    "(i.e. start passing, since xfail expects failure) once Phase 5 adds "
    "path validation — at which point flip it to a real assertion and drop "
    "the marker.",
    strict=False,
)
def test_ask_rejects_path_traversal(api_client, tmp_data_dir):
    response = api_client.post(
        "/ask",
        json={"question": "Anything", "file_path": "../../../etc/passwd"},
    )

    assert response.status_code in (400, 403)
