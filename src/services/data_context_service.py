"""
Generates a dataset-agnostic description of an uploaded CSV — row/column
counts, dtypes, unique counts, categorical values, numeric ranges, null
counts, and sample rows — computed purely with pandas, no LLM call.

This replaces docs/business_context.txt and docs/data_dictionary.txt, which
hardcoded TechMart Electronics facts (Laptop/Phone/Tablet, 4 Indian regions)
that got fed to the planner for *every* uploaded CSV regardless of what was
actually in it. See PHASES.md Phase 4 and docs/BUGS_FOUND.md for the
concrete failure this caused: a real sales CSV with an "Item Type" column
containing "Fruits" was ruled out of scope because the planner read
TechMart's fixed product list and Fruits wasn't on it.

Design note on categorical values vs. sample rows (see chat history for the
full reasoning): a column's value list is only shown when it's authoritative
— i.e. every unique value fits under CATEGORICAL_UNIQUE_THRESHOLD, so the
LLM can trust "these are all the values this column takes." Above that
threshold, only the unique count is reported, and sample rows (a separate,
explicitly-labeled "here are some examples" section) are what let the LLM
see a handful of real high-cardinality values — without the misleading
implication that a partial list is the complete set. Mixing those two
framings is what caused the original bug in the first place.
"""
import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Categorical value lists are only shown when the column's unique count is
# at or below this — beyond it, listing values stops being "the complete
# set" and starts being an arbitrary, misleadingly-partial sample.
CATEGORICAL_UNIQUE_THRESHOLD = 20


def _describe_column(series: pd.Series) -> dict:
    """Build one column's entry in the context: dtype, null count, and
    either a categorical value list (low cardinality) or a numeric range
    (numeric dtype) — a column can have both if it's a small set of
    numbers, e.g. a rating 1-5."""
    non_null = series.dropna()
    unique_count = int(non_null.nunique())
    null_count = int(series.isna().sum())

    column_info = {
        "dtype": str(series.dtype),
        "unique_count": unique_count,
        "null_count": null_count,
    }

    if unique_count <= CATEGORICAL_UNIQUE_THRESHOLD and unique_count > 0:
        # sorted for a stable, readable order regardless of row order
        column_info["values"] = sorted(non_null.unique().tolist(), key=str)

    if pd.api.types.is_numeric_dtype(series) and not non_null.empty:
        column_info["min"] = non_null.min().item()
        column_info["max"] = non_null.max().item()

    return column_info


def _build_context_dict(df: pd.DataFrame, sample_rows: int) -> dict:
    """The structured form of the context, before it's rendered to text.
    Kept separate from generate_data_context() so the exact metadata being
    sent to the LLM can be logged as a dict, not just eyeballed as a wall
    of prompt text."""
    row_count, column_count = df.shape

    columns = {}
    for column_name in df.columns:
        columns[column_name] = _describe_column(df[column_name])

    return {
        "row_count": row_count,
        "column_count": column_count,
        "columns": columns,
        "sample_rows": df.head(sample_rows).to_dict(orient="records") if row_count > 0 else [],
    }


def _render_context_text(context: dict, sample_rows: int) -> str:
    """Format the context dict as plain text for direct inclusion in an
    LLM prompt."""
    lines = [
        f"Dataset shape: {context['row_count']} rows, {context['column_count']} columns",
        "",
        "Columns:",
    ]

    for column_name, info in context["columns"].items():
        line = f"- {column_name} ({info['dtype']}, {info['unique_count']} unique"
        if info["null_count"]:
            line += f", {info['null_count']} null"
        line += ")"
        lines.append(line)

        if "values" in info:
            lines.append(f"    Values: {', '.join(str(v) for v in info['values'])}")
        if "min" in info:
            lines.append(f"    Range: {info['min']} to {info['max']}")

    if context["sample_rows"]:
        lines.append("")
        lines.append(f"Sample rows (showing up to {sample_rows} of {context['row_count']}):")
        # na_rep makes missing values an explicit, readable marker instead
        # of pandas' default "NaN" — the null_count already reported per
        # column above is where the LLM should look to know how common
        # this is; here it's just about not confusing "NaN" with a real value.
        lines.append(pd.DataFrame(context["sample_rows"]).to_string(index=False, na_rep="(missing)"))

    return "\n".join(lines)


def generate_data_context(file_path: str, sample_rows: int = 5) -> str:
    """Read file_path once and return a plain-text description of its
    shape and contents, formatted for direct inclusion in an LLM prompt.

    Logs the underlying metadata dict at INFO level before rendering it to
    text, so exactly what's being pushed into the LLM's prompt is visible
    in the server/terminal logs for every request, not just inferred from
    the final prompt string.
    """
    df = pd.read_csv(file_path)

    context = _build_context_dict(df, sample_rows)
    logger.info(f"Generated data context for {file_path}: {context}")

    return _render_context_text(context, sample_rows)
