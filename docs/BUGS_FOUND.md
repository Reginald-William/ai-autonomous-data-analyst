# Bugs Found

A running log of bugs discovered while writing tests, separate from `PHASES.md`'s risk
register (which tracks pre-identified architectural risks). Entries here are things we
actually *found* — usually because a new test caught them — logged as they're discovered so
nothing gets fixed and forgotten, or found and lost, between chat sessions.

Each entry: what's wrong, how it was found, severity, and status. Status values:
`open` (known, not yet fixed) · `fixed` (resolved, with the commit/PR) · `deferred` (known,
intentionally left for a later phase, with which phase and why).

---

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
