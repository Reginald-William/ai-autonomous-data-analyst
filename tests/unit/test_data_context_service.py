"""
Tests for src/services/data_context_service.py — the dataset-agnostic
context generator that replaces the hardcoded TechMart RAG docs (Phase 4).

Covers all six fixtures under tests/data/ plus sample_data.csv, verifying:
the categorical-values cutoff (CATEGORICAL_UNIQUE_THRESHOLD), numeric range
reporting, null counting, special characters in column names, and that
high-cardinality columns never get a misleading partial value list.
"""
import logging

from src.services.data_context_service import (
    CATEGORICAL_UNIQUE_THRESHOLD,
    _build_context_dict,
    generate_data_context,
)
import pandas as pd


def test_row_and_column_counts_match_source(sample_csv_path):
    context = generate_data_context(str(sample_csv_path))
    assert "12 rows, 4 columns" in context


def test_categorical_column_lists_all_values_under_threshold(sample_csv_path):
    context = generate_data_context(str(sample_csv_path))
    assert "region" in context
    assert "North" in context and "South" in context and "East" in context and "West" in context


def test_high_cardinality_column_has_no_value_list(large_sales_csv_path):
    df = pd.read_csv(large_sales_csv_path)
    context = _build_context_dict(df, sample_rows=5)

    date_info = context["columns"]["date"]
    assert date_info["unique_count"] > CATEGORICAL_UNIQUE_THRESHOLD
    assert "values" not in date_info


def test_low_cardinality_column_in_large_file_still_lists_values(large_sales_csv_path):
    """A large row count doesn't disqualify a column from a value list —
    only that column's own unique count matters (region/product stay
    low-cardinality even across 1000 rows)."""
    df = pd.read_csv(large_sales_csv_path)
    context = _build_context_dict(df, sample_rows=5)

    region_info = context["columns"]["region"]
    assert region_info["unique_count"] <= CATEGORICAL_UNIQUE_THRESHOLD
    assert "values" in region_info


def test_numeric_column_reports_min_and_max(sample_csv_path):
    df = pd.read_csv(sample_csv_path)
    context = _build_context_dict(df, sample_rows=5)

    revenue_info = context["columns"]["revenue"]
    assert revenue_info["min"] == 7500
    assert revenue_info["max"] == 20000


def test_non_numeric_column_has_no_min_max(sample_csv_path):
    df = pd.read_csv(sample_csv_path)
    context = _build_context_dict(df, sample_rows=5)

    assert "min" not in context["columns"]["region"]


def test_null_counts_reported_per_column(missing_values_csv_path):
    df = pd.read_csv(missing_values_csv_path)
    context = _build_context_dict(df, sample_rows=5)

    assert context["columns"]["revenue"]["null_count"] == 2
    assert context["columns"]["region"]["null_count"] == 1
    assert context["columns"]["date"]["null_count"] == 0


def test_null_values_render_as_missing_not_nan(missing_values_csv_path):
    context = generate_data_context(str(missing_values_csv_path))
    assert "(missing)" in context
    assert "NaN" not in context


def test_nulls_excluded_from_categorical_value_list(missing_values_csv_path):
    """A null shouldn't appear as a literal value in the Values: list —
    it's already surfaced via null_count."""
    df = pd.read_csv(missing_values_csv_path)
    context = _build_context_dict(df, sample_rows=5)

    region_values = context["columns"]["region"]["values"]
    assert all(v is not None for v in region_values)
    assert len(region_values) == 4  # North, South, East, West — not counting the null


def test_special_char_column_names_survive_unmangled(special_chars_csv_path):
    context = generate_data_context(str(special_chars_csv_path))
    assert "total revenue (INR)" in context
    assert "region/zone" in context
    assert "transaction date" in context


def test_special_char_categorical_values_survive(special_chars_csv_path):
    context = generate_data_context(str(special_chars_csv_path))
    assert "Tablet & Pen" in context


def test_non_sales_dataset_employees_generates_context_without_error(employees_csv_path):
    """employees.csv has nothing to do with sales/regions/products — this
    is one of the two files PHASES.md names as the Phase 4 done-criterion:
    it should generate a sensible context, not error or return something
    TechMart-shaped."""
    context = generate_data_context(str(employees_csv_path))

    assert "department" in context
    assert "Engineering" in context and "Marketing" in context and "HR" in context
    assert "TechMart" not in context
    assert "Laptop" not in context


def test_non_sales_dataset_stocks_generates_context_without_error(stocks_csv_path):
    context = generate_data_context(str(stocks_csv_path))

    assert "ticker" in context
    assert "AAPL" in context
    assert "TechMart" not in context


def test_sample_rows_respects_requested_count(sample_csv_path):
    context = generate_data_context(str(sample_csv_path), sample_rows=2)
    assert "showing up to 2 of 12" in context


def test_logs_the_context_dict_at_info_level(sample_csv_path, caplog):
    """Confirms the metadata dict is actually logged (not just rendered to
    text) — this is what makes it possible to inspect exactly what's being
    pushed into the LLM prompt from the server/test logs."""
    with caplog.at_level(logging.INFO, logger="src.services.data_context_service"):
        generate_data_context(str(sample_csv_path))

    assert any("Generated data context" in record.message for record in caplog.records)
