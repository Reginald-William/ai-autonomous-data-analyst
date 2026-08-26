"""
Tests for src/utils/schemas.py — the AnalysisResponse Pydantic model that
every /ask and /upload response is shaped as.

Pydantic does the actual validation work; these tests just confirm the model
is wired the way the API contract expects: which fields are required, what
the defaults are, and that the mutable-default list is safely isolated
per instance.
"""
import pytest
from pydantic import ValidationError

from src.utils.schemas import AnalysisResponse


REQUIRED_FIELDS = {
    "question": "What is total revenue?",
    "result": "153500",
    "status": "success",
    "attempts": 1,
    "time_taken": "2.1s",
    "model_used": "openai/gpt-oss-20b",
    "row_count": 12,
    "column_count": 4,
    "file_name": "sample_data.csv",
    "timestamp": "2026-08-24 10:10:10",
}


def test_builds_successfully_with_only_required_fields():
    response = AnalysisResponse(**REQUIRED_FIELDS)

    assert response.question == "What is total revenue?"
    assert response.result == "153500"


@pytest.mark.parametrize("missing_field", sorted(REQUIRED_FIELDS.keys()))
def test_missing_required_field_raises_validation_error(missing_field):
    incomplete = {k: v for k, v in REQUIRED_FIELDS.items() if k != missing_field}

    with pytest.raises(ValidationError):
        AnalysisResponse(**incomplete)


def test_agents_used_defaults_to_empty_list():
    response = AnalysisResponse(**REQUIRED_FIELDS)
    assert response.agents_used == []


def test_task_type_and_reasoning_default_to_empty_string():
    response = AnalysisResponse(**REQUIRED_FIELDS)
    assert response.task_type == ""
    assert response.reasoning == ""


def test_chart_path_and_session_id_default_to_none():
    response = AnalysisResponse(**REQUIRED_FIELDS)
    assert response.chart_path is None
    assert response.session_id is None


def test_agents_used_default_is_not_shared_between_instances():
    """
    Guards against the classic Python mutable-default-argument trap:
    `agents_used: List[str] = []` could, in the wrong implementation, hand
    every instance a reference to the SAME list, so appending to one
    instance's list would silently leak into every other instance. Pydantic
    deep-copies defaults per instance, so this should never happen — but
    the whole point of a regression test is not trusting that from memory.
    """
    first = AnalysisResponse(**REQUIRED_FIELDS)
    second = AnalysisResponse(**REQUIRED_FIELDS)

    first.agents_used.append("python")

    assert first.agents_used == ["python"]
    assert second.agents_used == []


def test_full_response_with_all_optional_fields_set():
    response = AnalysisResponse(
        **REQUIRED_FIELDS,
        agents_used=["python", "chart"],
        task_type="visualization",
        reasoning="question asks for a chart",
        chart_path="data/charts/abc123.png",
        session_id="abc123",
    )

    assert response.agents_used == ["python", "chart"]
    assert response.chart_path == "data/charts/abc123.png"
    assert response.session_id == "abc123"
