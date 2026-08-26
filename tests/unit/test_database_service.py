"""
Tests for src/services/database_service.py — CSV-to-SQLite conversion, and
the connection-closing fix landed in Phase 1b (the closing() wrapper that
was the root cause of the Windows PermissionError during session cleanup).

load_csv_to_sqlite() always builds its db_path as "data/...", relative to
the current directory — there's no way to inject a different base folder
today (see PHASES.md risk register, "no config module"). The tmp_data_dir
fixture works around this by temporarily chdir-ing the test process into a
scratch folder, so "data/..." resolves there instead of the real project.
"""
import os
import sqlite3

import pandas as pd
import pytest

from src.services.database_service import load_csv_to_sqlite


def test_table_name_derived_from_original_filename(tmp_data_dir, tmp_csv_file):
    info = load_csv_to_sqlite(str(tmp_csv_file), original_filename="Sales Report.csv")
    assert info["table_name"] == "Sales_Report"


def test_table_name_derived_from_file_path_when_no_original_filename(
    tmp_data_dir, tmp_csv_file
):
    info = load_csv_to_sqlite(str(tmp_csv_file))
    assert info["table_name"] == "sample_data"


def test_table_name_sanitizes_hyphens_and_spaces(tmp_data_dir, tmp_csv_file):
    info = load_csv_to_sqlite(str(tmp_csv_file), original_filename="q1-sales report.csv")
    assert info["table_name"] == "q1_sales_report"


def test_db_path_includes_session_id_when_provided(tmp_data_dir, tmp_csv_file):
    info = load_csv_to_sqlite(str(tmp_csv_file), session_id="abc123")
    assert info["db_path"] == "data/abc123_sample_data.db"


def test_db_path_has_no_session_prefix_when_not_provided(tmp_data_dir, tmp_csv_file):
    info = load_csv_to_sqlite(str(tmp_csv_file))
    assert info["db_path"] == "data/sample_data.db"


def test_returned_metadata_matches_source_csv(tmp_data_dir, tmp_csv_file):
    info = load_csv_to_sqlite(str(tmp_csv_file))

    assert info["row_count"] == 12
    assert info["column_count"] == 4
    assert info["columns"] == ["date", "revenue", "region", "product"]


def test_data_actually_lands_in_sqlite(tmp_data_dir, tmp_csv_file):
    """
    The real round-trip check: load the CSV, then read it back with a
    plain sqlite3 connection (bypassing the app code entirely) to prove
    the table genuinely exists on disk with the right row count — not
    just that load_csv_to_sqlite() returned a dict that looks right.
    """
    info = load_csv_to_sqlite(str(tmp_csv_file))

    with sqlite3.connect(info["db_path"]) as conn:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {info['table_name']}")
        (count,) = cursor.fetchone()

    assert count == 12


def test_connection_is_closed_after_success_no_windows_lock(tmp_data_dir, tmp_csv_file):
    """
    Regression test for the Phase 1b fix: before wrapping the connection in
    contextlib.closing(), a lingering open handle could leave the .db file
    locked on Windows. If the connection is properly closed, deleting the
    file immediately afterward should never raise.
    """
    info = load_csv_to_sqlite(str(tmp_csv_file))

    os.remove(info["db_path"])  # would raise PermissionError on Windows if still open

    assert not os.path.exists(info["db_path"])


def test_reloading_same_table_replaces_existing_data(tmp_data_dir, tmp_csv_file):
    load_csv_to_sqlite(str(tmp_csv_file))

    # Overwrite the source CSV with fewer rows, then load it again under the
    # same table name — if_exists="replace" should mean the old rows don't
    # linger alongside the new ones.
    tmp_csv_file.write_text("date,revenue,region,product\n2024-01-01,100,North,Laptop\n")

    info = load_csv_to_sqlite(str(tmp_csv_file))

    with sqlite3.connect(info["db_path"]) as conn:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {info['table_name']}")
        (count,) = cursor.fetchone()

    assert count == 1
