# Bugs Found

A running log of bugs discovered while writing tests, separate from `PHASES.md`'s risk
register (which tracks pre-identified architectural risks). Entries here are things we
actually *found* — usually because a new test caught them — logged as they're discovered so
nothing gets fixed and forgotten, or found and lost, between chat sessions.

Each entry: what's wrong, how it was found, severity, and status. Status values:
`open` (known, not yet fixed) · `fixed` (resolved, with the commit/PR) · `deferred` (known,
intentionally left for a later phase, with which phase and why).

---

## Phase 4

### 6. `RagIndex.build_index()` crashes on an empty `docs/` folder

- **File:** `src/services/rag_service.py`, `RagIndex.build_index()`
- **Found by:** manually reproducing the app's startup after deleting `docs/business_context.txt`,
  `docs/data_dictionary.txt`, and `docs/routing_rules.txt` as part of the Phase 4 RAG cleanup
  (see PHASES.md Phase 4's "RAG correction" note).
- **What's wrong:** with zero `.txt` files in `doc_folder`, `load_documents()` returns `[]`,
  so `self.chunks = []`. `self._get_model().encode([])` (encoding an empty list) returns an
  array shaped `(0,)`, not `(0, embedding_dim)` — so `embeddings.shape[1]` raises
  `IndexError: tuple index out of range`. This propagates straight out of `build_index()`,
  which `main.py`'s startup lifespan calls unconditionally — **the entire server would fail to
  start** the moment `docs/` has no documents in it. Confirmed by direct reproduction (not just
  reasoned about): `python -c "from src.services.rag_service import build_index;
  build_index('docs')"` raised exactly this traceback before the fix.
- **Severity:** High — this isn't a degraded-behavior bug, it's a startup crash. It only
  surfaced now because `docs/` had never been empty before (TechMart docs and
  `routing_rules.txt` always provided at least one file since the project's first RAG commit).
- **Status:** `fixed` (Phase 4) — `build_index()` now checks `if not self.chunks:` before
  attempting to encode, logs a warning, sets `self.index = None`, and returns early.
  `retrieve_context()`'s existing `if self.index is None: return ""` guard already handles
  that state safely, so no other code needed to change.

### 7. `POST /upload` silently drops a file when two files are sent under the same form field

- **File:** `src/routes/ask.py`, `upload_and_ask()` — `file: UploadFile = File(None)` accepts
  exactly one file, but nothing rejects a request that sends more than one under the same
  `file` field name.
- **Found by:** owner noticed Postman allows attaching two files to the `file` field of the
  `/upload` request and asked whether this could confuse the pipeline.
- **What's wrong:** confirmed via a `TestClient` request sending two files under the same
  `file` form field name (`sample_data.csv` and `employees.csv`) — FastAPI/Starlette bound the
  single `UploadFile` parameter to the **second** file only. The first file
  (`sample_data.csv`) was silently discarded: no error, no warning, no indication anywhere in
  the response that two files were received. The response returned `200 success` with
  `file_name: "employees.csv"`, giving no signal to the caller that anything was dropped.
- **Severity:** Low in practice (a normal browser file-input can't attach two files under one
  field name; this needs a client like Postman or a hand-built multipart request to trigger),
  but genuinely silent — someone could accidentally attach the wrong second file and get a
  confident 200 response processing the wrong dataset with no indication anything was
  discarded.
- **Status:** `open` — not fixed. Fix would be validating the incoming form has at most one
  file under `file` (FastAPI's `UploadFile` alone doesn't expose "how many were sent" for a
  singular parameter — would need to inspect the raw `Request`'s form data, or switch the
  parameter to `List[UploadFile]` and explicitly reject `len(files) > 1` with a clear 400).
  Not scheduled to a specific phase yet.

### 8. Chart agent crashed re-parsing its own input after a prompt-rule addition

- **File:** `src/agents/chart_agent.py`, `generate_chart_code()`'s generated code (not the
  agent's own Python, the LLM's output)
- **Found by:** manually re-testing the large-dataset chart fix (finding #entry above) against
  `tests/data/large_sales.csv` after adding a rule to suppress value labels when bar values
  are too close together.
- **What's wrong:** the LLM-generated matplotlib code chose to re-parse the already-usable
  computed-result string via `pd.read_csv(io.StringIO(text), delim_whitespace=True)` instead
  of using the data directly. `delim_whitespace` was removed from the pandas version pinned in
  `requirements.txt`, so this raised `TypeError: read_csv() got an unexpected keyword argument
  'delim_whitespace'` every time the model chose this path. Chart agent has no retry loop
  (unlike python/sql agents' `fix_code`/`fix_sql`), so this is immediately fatal — caught by
  `analyst_service.py`'s outer `except Exception`, surfacing as `status: "failed"` with
  `agents_used: ['python']` (chart never got to append itself before crashing, misleadingly
  reading as "chart agent wasn't invoked" rather than "chart agent crashed").
- **Severity:** Medium — non-deterministic (only some LLM calls chose this parsing approach),
  and directly caused by adding more prompt instructions on top of an already-complex
  "write a full program" prompt.
- **Status:** `deferred` — not point-fixed. This motivated the chart-agent redesign (chart
  spec instead of chart code) documented in `PHASES.md` Phase 4, which structurally prevents
  this class of bug rather than patching this one instance.

### 9. Chart spec's invented `y_column` name crashed count-shaped chart requests

- **File:** `src/agents/chart_agent.py`, `prepare_chart_data()`
- **Found by:** a manual test matrix run across 13 chart questions (bar/line/pie/scatter/
  histogram, several fixtures) after the Phase 4 chart-spec redesign landed, specifically
  "Show me a pie chart of employee count by city" on `tests/data/employees.csv`.
- **What's wrong:** for a "count of rows per category" question, there's no real column to
  put in `y_column` — the LLM invented a placeholder name (`"count"` on the first run,
  `"employee_count"` on a retry) that doesn't exist in the raw CSV. `prepare_chart_data`
  dereferenced it directly (`df.groupby(x_column)[y_column]`), raising `KeyError: 'Column not
  found: ...'`, caught by the outer `except Exception` and surfacing as `status: "failed"`,
  discarding an otherwise-correct upstream python/sql result. An initial fix special-cased the
  literal string `"count"` — insufficient, since a retry produced a *different* invented name
  and crashed again the same way.
- **Severity:** Medium-High — a real crash (not just a visual defect) on a common, ordinary
  question shape ("X count by Y").
- **Status:** `fixed` — `prepare_chart_data` now checks `y_column not in df.columns` (any
  invented name, not just previously-seen ones) and falls back to `df.groupby(x_column).size()`
  — counting rows directly, never dereferencing whatever name the LLM invented.
  `ChartAgent.run()` also now fail-fasts with a clear message if `x_column` itself isn't a real
  column, instead of crashing deep inside pandas with a confusing traceback. Regression tests:
  `test_invented_y_column_falls_back_to_counting_rows`,
  `test_chart_agent_run_raises_on_missing_column`.

### 10. Chart aggregation can silently render the wrong number for a correctly-computed answer

- **File:** `src/agents/chart_agent.py`, `prepare_chart_data()`
- **Found by:** the same manual test matrix — "Show me a bar chart of average salary by
  department" on `tests/data/employees.csv`. The python agent correctly computed and printed
  means (Engineering 94750, HR 62333, Marketing 74667); the rendered chart showed
  ~379000/187000/224000 — roughly 4x too high, i.e. sums, not the requested/computed averages.
- **What's wrong:** `chart_agent` never sees what aggregation function python_agent actually
  used — it re-derives its own aggregation from the raw CSV independently, via the LLM-chosen
  chart spec. The duplicate-detection fallback (added to fix a different bug — see finding #6
  in this file's history and the docstring in `prepare_chart_data`) is intended to only correct
  an ambiguous `"none"` into `"sum"`, but the net effect for this question was still a
  sum-shaped chart despite an average being the correct, already-computed answer.
- **Severity:** Medium — wrong data rendered with no error and no visual indication anything is
  off (worse than a crash in one sense: it looks correct).
- **Status:** `deferred`. Root cause is architectural, shared with findings #11 and #12 below:
  `chart_agent` always independently re-derives data from the raw file rather than consuming
  whatever the upstream python/sql agent already correctly computed. See "Proposed real fix"
  under finding #12 for the options considered and why a full fix was deferred past Phase 4.

### 11. Chart data ignores SQL-agent filtering — can silently mix rows the user asked to exclude

- **File:** `src/agents/chart_agent.py`, `run()` (calls `pd.read_csv(file_path)` — the
  original, unfiltered file — regardless of what the SQL agent already filtered)
- **Found by:** the same manual test matrix — "Show me a line chart of closing price by date
  for AAPL" on `tests/data/stocks.csv` (3 tickers: AAPL/GOOGL/MSFT sharing the same dates). The
  SQL agent correctly filtered to AAPL-only rows (verified via the printed result: 187.2,
  185.9, 189.3, 188.4). The rendered chart's y-axis showed ~706-715 — the sum of all three
  tickers' close prices per date, since `date` repeats across tickers in the unfiltered file
  and the duplicate-detection fallback (see finding #10) summed across all of them.
- **What's wrong:** `chart_agent` has no access to the SQL agent's `WHERE` clause at all — it
  reads the raw, full CSV independently. Any SQL-routed chart question that relies on the
  filter to scope the data will silently include out-of-scope rows.
- **Severity:** High of this cluster — produces a chart that directly contradicts the user's
  explicit filtering request, with no error and no visual indication.
- **Status:** `deferred` — see finding #12's "Proposed real fix." The concrete, comparatively
  low-cost fix identified: thread the SQL agent's already-generated query string (and
  `db_path`) into `chart_agent.run()`, and when present, re-execute that exact query
  (`pd.read_sql_query(sql, conn)`) instead of reading the raw CSV — safe to replay since SQL
  filters are declarative and side-effect-free, unlike arbitrary python-agent code (see
  finding #12's discussion of why the SQL and Python paths aren't symmetric).

### 12. Scatter charts over-aggregate instead of showing per-row spread

- **File:** `src/agents/chart_agent.py`, `prepare_chart_data()` / `render_scatter()`
- **Found by:** the same manual test matrix — "Show me a scatter chart of revenue by region"
  on `tests/data/large_sales.csv` (1000 rows, 4 regions) rendered only 4 points, one per
  region, instead of a scatter of (up to) 1000 individual points.
- **What's wrong:** `prepare_chart_data`'s duplicate-detection fallback (see finding #10) fires
  for any categorical `x_column` with repeated values, forcing a `groupby` — correct for
  bar/pie/line-by-category, but wrong for scatter, whose entire purpose is showing per-row
  spread, not a per-category aggregate. `render_histogram`/the histogram branch of `run()`
  already bypasses this groupby pipeline entirely for the same reason; scatter never got the
  same treatment.
- **Severity:** Medium — produces a technically-not-wrong-per-se but semantically incorrect
  chart type (an aggregated bar-chart-shaped scatter is not what "scatter chart" implies).
- **Status:** `deferred` alongside #10/#11 as one combined fix, reasoning below.

**Proposed real fix for findings #10-#12 (not implemented in Phase 4):** all three share one
root cause — `chart_agent` always independently re-derives its data from the raw file instead
of consuming what the upstream agent already correctly computed (the right aggregation
function, the right row filter, or "no aggregation at all" for scatter). Two fix shapes were
considered:

1. **Thread the actual computed dataframe through** from `python_agent`/`sql_agent` to
   `chart_agent`, so nothing gets re-derived. Structurally correct for both agents, but
   requires changing `python_agent`'s LLM-facing contract (generated code currently only
   prints an answer; extracting a real object back out means asking it to also bind a specific
   variable, reintroducing prompt-instruction fragility this whole redesign was meant to
   reduce) — bigger footprint, deferred.
2. **Reuse what's already available cheaply**: for SQL-routed questions, replay the SQL
   agent's already-generated query string against the db (safe — SQL filters are declarative,
   side-effect-free, and idempotent to re-run) — fixes #11 completely. For python-routed
   questions, no equivalent safe reuse exists (arbitrary LLM-generated code isn't safely
   re-runnable a second time for a different purpose), so the chart still re-derives
   independently, but more carefully: skip grouping entirely for scatter (fixes #12), and stop
   letting the duplicate-detection fallback override an aggregation the LLM explicitly and
   correctly named rather than left ambiguous (fixes #10). This was the recommended shape —
   smaller footprint, no new LLM contract changes — but still deferred past Phase 4 given time
   constraints; **Phase 4's actual done-criterion (dataset-agnostic routing) doesn't depend on
   chart correctness**, and these three bugs affect a secondary, decorative feature (chart
   generation) rather than the app's core routing/analysis correctness. Revisit in Phase 13
   (Polish) or ad hoc if time allows before then.

## Phase 3

### 1. `python`/`sql` `elif` silently drops SQL when a plan names both agents

- **File:** `src/services/analyst_service.py`, `analyse()`, the dispatch block (`if "python" in
  agents: ... elif "sql" in agents: ...`)
- **Found by:** `tests/integration/test_analyst_orchestration.py::test_plan_with_both_python_and_sql_should_run_sql_too`
- **What's wrong:** If the planner ever returns `agents: ["python", "sql"]`, only the Python
  agent runs — `sql` is silently skipped because of the `elif`. No error, no log entry
  flagging it as dropped; `agents_used` just never contains `"sql"`.
- **Severity:** Medium — the planner's current prompt (`planner_agent.py`) doesn't appear to
  ever instruct combining `python` + `sql` in one plan today (its documented combos are
  `["python"]`, `["sql"]`, `["python", "chart"]`, `["sql", "chart"]`), so this may not fire in
  practice yet — but it's a live landmine if the planner prompt is ever extended, and it fails
  silently rather than loudly.
- **Status:** `fixed` (Phase 3) — `elif "sql"` changed to an independent `if "sql" in agents`;
  both agents now run if both are named, and their results are labeled and concatenated
  (`"Python result:\n...\n\nSQL result:\n..."`) instead of one silently overwriting the other.
  Regression test: `test_plan_with_both_python_and_sql_should_run_sql_too`.

### 2. Chart-only plan raises an unhandled `pydantic_core.ValidationError`, not a clean error

- **File:** `src/services/analyst_service.py`, `analyse()`, the final success-path
  `AnalysisResponse(...)` construction (bottom of the function)
- **Found by:** `tests/integration/test_analyst_orchestration.py::test_chart_only_plan_does_not_500`
- **What's wrong:** If the planner returns `agents: ["chart"]` with no `python`/`sql`, `result`
  stays `None` (chart agent is only reachable in the `if "chart" in agents and result is not
  None` guard, so it never even runs). Execution reaches the bottom of `analyse()` and tries to
  construct `AnalysisResponse(result=None, ...)` — but `result: str` in
  `src/utils/schemas.py` is required, not `Optional[str]`, so Pydantic raises
  `ValidationError`. This exception is **not inside the function's own `try/except Exception`
  block** (that block only wraps the agent-dispatch calls, not the final response
  construction), so it propagates all the way up — in production this would be caught by
  `main.py`'s global `Exception` handler and surfaced as a generic 500, but with no
  agent-specific error message; the log line would just say "Unexpected error: ...".
  Practically: **a plan with only `chart` as the sole agent, with no python/sql, is not a
  valid plan today**, and nothing currently stops the planner LLM from producing one for a
  chart-shaped question it misjudges as needing no computation first.
- **Severity:** Medium — same caveat as #1: `planner_agent.py`'s prompt currently instructs
  "chart: ... (always used after python or sql)" and only documents `["python", "chart"]`/
  `["sql", "chart"]` combos, so this shouldn't fire under normal LLM behavior today, but LLM
  outputs are not guaranteed to follow the prompt, and there's no server-side validation of
  the plan shape to catch a malformed one before dispatch.
- **Status:** `fixed` (Phase 3) — a chart-only plan (`"chart"` present, neither `"python"` nor
  `"sql"`) is now coerced to `["python", "chart"]` right after the planner call, with a
  warning logged, so ChartAgent always has a computed result to visualize. Regression test:
  `test_chart_only_plan_does_not_500`.

### 3. `python_agent.execute_code`'s raw `sys.stdout` reassignment

- **File:** `src/agents/python_agent.py`, `execute_code()`
- **Found by:** code review while addressing `PHASES.md`'s Phase 3 note ("`sys.stdout`
  reassignment corrupts pytest capture if an exception path skips the restore")
- **What's wrong:** the original code did `sys.stdout = captured_output`, then `exec()`, then
  manually restored `sys.stdout = sys.__stdout__` in both the success path and the `except
  Exception` block. Two distinct problems: (1) `except Exception` doesn't catch
  `BaseException` subclasses like `SystemExit`/`KeyboardInterrupt`, so a restore could still be
  skipped on those; (2) `sys.stdout` is a single process-wide global — under concurrent FastAPI
  requests, two simultaneous `execute_code()` calls can each reassign it, so one request's
  `exec()` output can land in the other's capture buffer, or a restore from one request can
  clobber the redirect a still-running request depends on.
- **Severity:** Low-Medium — (1) is a real correctness gap now fixed; (2) is a genuine
  concurrency bug not fixed by this change (see below).
- **Status:** `fixed` (Phase 3), partially — replaced the manual reassign/restore with
  `contextlib.redirect_stdout`, which guarantees restoration via `__exit__` even on
  `BaseException`, closing gap (1).
- **Deferred:** gap (2), the concurrency/shared-global issue, is **not** fixed by
  `redirect_stdout` — it also reassigns the same process-wide `sys.stdout`, just more safely.
  A real fix needs each execution to have its own isolated stdout (e.g. running generated code
  in a subprocess or thread with redirected I/O), which is the same underlying problem as the
  unsandboxed `exec()` risk in `PHASES.md` risk #2 — deferring this to Phase 5's sandboxing
  work rather than solving it in isolation here.

### 4. Lint cleanup found while wiring up CI (`ruff check .`)

- **Found by:** adding `.github/workflows/ci.yml`'s `ruff check .` step and running it locally
  before trusting the workflow would pass on first push.
- **What's wrong:** several small pre-existing issues, none behavior-changing:
  - `src/routes/ask.py` — an f-string with no `{}` placeholders (`f"Request received: POST
    /ask"`), just needed the unnecessary `f` prefix removed.
  - `src/services/llm_service.py` and `src/groq_all_models.py` — both had `load_dotenv()`
    called as a statement sandwiched between import lines, which is unconventional Python
    style (all imports should come first) and is what ruff's E402 rule flags.
  - `src/agents/chart_agent.py` — `import os` left over from Phase 2, when we removed the
    `os.makedirs(self.charts_dir, exist_ok=True)` side effect from `__init__` but didn't
    notice the now-unused import it left behind.
  - `tests/unit/test_database_service.py` — `import pandas as pd` and `import pytest`, both
    unused in the current version of the file.
- **Severity:** Low — none of these were functional bugs, just lint/style debt that had
  accumulated silently because nothing was checking for it until now.
- **Status:** `fixed` (Phase 3) — all four locations cleaned up; `ruff check .` passes clean.

### 5. `test_database_service.py`'s own SQLite connections leaked (the exact bug the test suite verifies is fixed elsewhere)

- **File:** `tests/unit/test_database_service.py`,
  `test_data_actually_lands_in_sqlite` and `test_reloading_same_table_replaces_existing_data`
- **Found by:** a `ResourceWarning: unclosed database` surfaced while running the full suite
  with coverage for the CI workflow — it appeared to come from an unrelated test
  (`test_rag_chunking.py`) at first, since pytest reports `ResourceWarning`s at
  garbage-collection time, not necessarily in the test that caused them. Isolating each file
  individually (`pytest tests/unit/test_database_service.py -W error::ResourceWarning`)
  confirmed the real source.
- **What's wrong:** both tests used `with sqlite3.connect(...) as conn:`. `sqlite3.Connection`
  implementing the context-manager protocol only governs the **transaction**
  (commit on success, rollback on exception) — it does **not** call `.close()` on exit. The
  connection stays open after the `with` block ends. This is the exact same bug class the
  Phase 1b fix (`contextlib.closing()` in `database_service.py`) was written to fix in the
  *application* code — the *test* verifying that fix had an unrelated instance of the same
  underlying mistake in its own setup.
- **Severity:** Low — no test assertion was ever wrong, and a `ResourceWarning` doesn't fail a
  test by default, so this had zero effect on trustworthiness of what the tests verify. Purely
  a resource-leak hygiene issue, most visible as log noise.
- **Status:** `fixed` (Phase 3) — both call sites now use
  `with closing(sqlite3.connect(...)) as conn:`, matching the pattern already used in the real
  `database_service.py`/`sql_agent.py` code.
