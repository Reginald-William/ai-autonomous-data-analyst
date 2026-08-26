"""
Shared pytest fixtures. Anything defined here is automatically available to
every test file under tests/ without needing an import — pytest finds this
file by its special name and injects fixtures by matching argument names.
"""
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_DATA_DIR = REPO_ROOT / "tests" / "data"


@pytest.fixture
def sample_csv_path() -> Path:
    """Path to the 12-row TechMart sample CSV at the repo root."""
    return REPO_ROOT / "sample_data.csv"


@pytest.fixture
def empty_csv_path() -> Path:
    """Path to a CSV with a header row but zero data rows."""
    return TEST_DATA_DIR / "empty.csv"


@pytest.fixture
def special_chars_csv_path() -> Path:
    """Path to a CSV with spaces, parens, and a slash in its headers."""
    return TEST_DATA_DIR / "special_chars.csv"


@pytest.fixture
def large_sales_csv_path() -> Path:
    """Path to the 1000-row CSV used to exercise the high-complexity tier."""
    return TEST_DATA_DIR / "large_sales.csv"


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """
    Redirects the app's file operations into a throwaway temp folder instead
    of the real data/ directory, and switches the process's working
    directory there for the duration of the test. Session/database code
    builds paths like "data/uploads/..." relative to cwd, so changing cwd is
    what makes those relative paths land in the temp folder instead of the
    real project.
    """
    (tmp_path / "data" / "uploads").mkdir(parents=True)
    (tmp_path / "data" / "charts").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def tmp_csv_file(tmp_path, sample_csv_path):
    """A writable copy of sample_data.csv inside the test's temp folder."""
    dest = tmp_path / "sample_data.csv"
    shutil.copy(sample_csv_path, dest)
    return dest
