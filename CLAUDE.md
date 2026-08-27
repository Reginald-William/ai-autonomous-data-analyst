# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ Read this first

**Phase 1 is complete** (model remap, pending bug fixes, first 78 automated tests, doc
rewrite). The app works again — models are `openai/gpt-oss-20b`/`openai/gpt-oss-120b`, not the
dead Llama IDs. **Phase 2 (config + DI refactor) is also complete** — `src/config.py`, a lazy
Groq client, injectable agent clients via `build_agents()`, and a lazy RAG index. **Phase 3
(API + integration tests, CI) is next**, on branch `claude/v6.2-ci`.

**Project direction changed on 2026-08-24.** This repo is no longer heading toward a monetized
SaaS product. It is now a **Data Engineering portfolio project**, targeting applications from
~April 2027. The existing multi-agent system becomes the *serving layer* on top of a real data
platform (ingestion → raw storage → dbt → BigQuery → data quality).

**Work one phase per chat session.** Read `PHASES.md` first — it is the source of truth for the
13-phase plan, current status, locked decisions, risk register, and cost limits. Do not re-plan
or re-litigate settled decisions.

**Current phase:** 3 — API + integration tests, CI · **Branch:** `claude/v6.2-ci` (not yet cut —
still on `claude/v6.1-config-di` as of this writing)

## Working agreements

- **Never change a file without asking first.** No exceptions. Read/run/explore commands don't
  need confirmation; edits do.
- **Always check the current branch and confirm it** before touching code.
- **Never remove existing code comments** unless explicitly asked.
- **Push via SSH**, not HTTPS (PATs caused repeated 403s).
- **Keep this file and `PHASES.md` updated** after every significant change or phase completion.

## Commands

**Setup**
```bash
source venv/Scripts/activate
pip install -r requirements.txt
# Create .env with: GROQ_API_KEY=your_key_here
```

**Run the server**
```bash
uvicorn src.main:app --reload
```

**Tests** (arriving in Phase 1 — there are currently zero `test_*.py` files)
```bash
pytest -m "not live_api"          # default: no real API calls
pytest -m live_api                # the 2-3 tests that hit Groq for real
pytest --cov=src --cov-report=term-missing
```

**Check which Groq models are actually live** — do this before trusting any model ID, as Groq
retires them on a short cycle:
```bash
python src/groq_all_models.py
```

**Test the API**
```bash
# Upload endpoint (multipart — for real users)
curl -X POST http://localhost:8000/upload \
  -F "question=What is total revenue?" \
  -F "file=@sample_data.csv"

# Follow-up question (reuse session, no re-upload)
curl -X POST http://localhost:8000/upload \
  -F "question=What is revenue by region?" \
  -F "session_id=<session_id_from_response>"

# Original endpoint (local file path — dev/testing only; has an unfixed path-traversal
# hole, addressed in Phase 5 before deploy)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is total revenue?", "file_path": "sample_data.csv"}'
```

## Architecture

A **FastAPI multi-agent data analysis system** that answers natural language questions about
CSV data using LLM-generated code execution. The hand-rolled planner, complexity routing, and
retry loops are the project's differentiator — **do not rewrite them into LangChain or any
framework.** LangGraph is added *alongside* in Phase 11 behind a config flag, never as a
replacement.

### Request Flow

```
POST /ask  (JSON, file_path) ─────────────────────────────────┐
                                                               ↓
POST /upload (multipart, file + question)             analyst_service.analyse()
  ↓                                                            ↓
  Validate file (CSV, ≤10MB, non-empty, parseable)    PlannerAgent (routes to one or more agents)
  ↓                                                            ↓
  Save to data/uploads/{session_id}.csv          PythonAgent | SQLAgent | ChartAgent
  ↓                                               (code generation + retry loop)
  session_service.create_session()                             ↓
  ↓                                                    AnalysisResponse (Pydantic)
  analyst_service.analyse()                            (includes session_id)
  ↓
  Return response with session_id

Follow-up: POST /upload (session_id + question, no file)
  ↓
  session_service.get_session() → reuse saved file_path
  ↓
  analyst_service.analyse()
```

### Agent Responsibilities

- **PlannerAgent** (`src/agents/planner_agent.py`): Two-call planner. Call 1 decides routing
  (agents + task_type). Call 2 classifies complexity (low/medium/high) at `temperature=0.0` for
  determinism. Complexity is capped at `medium` when `row_count < 500` —
  `HIGH_COMPLEXITY_ROW_THRESHOLD`.
- **PythonAgent** (`src/agents/python_agent.py`): Generates and executes pandas code. Captures
  stdout. On failure, sends the error back to the LLM to fix and retries.
- **SQLAgent** (`src/agents/sql_agent.py`): Converts CSV to SQLite via `database_service`,
  generates SQL, executes queries. Same retry logic.
- **ChartAgent** (`src/agents/chart_agent.py`): Generates matplotlib code, saves charts to
  `data/charts/{session_id}.png`. Receives prior analysis result as context.

### Key Services

- **`src/services/analyst_service.py`**: Main orchestration. Loads CSV, extracts metadata, calls
  PlannerAgent (passing `row_count`), dispatches to agents with `complexity` and `session_id`,
  returns a structured response. Note `python` and `sql` are mutually exclusive via `elif` —
  python wins if the planner returns both.
- **`src/services/session_service.py`**: In-memory session store. Maps `session_id` →
  `{file_path, original_filename, created_at, last_accessed}`. TTL 30 minutes. Background
  cleanup every 5 minutes; startup sweep removes orphans.
- **`src/services/rag_service.py`**: Builds a FAISS index on startup from `docs/`. **Known
  problem:** `business_context.txt` and `data_dictionary.txt` describe TechMart Electronics and
  are hardcoded to `sample_data.csv`, so questions about any other dataset get rejected as
  out-of-scope. Fixed in Phase 4.
- **`src/services/llm_service.py`**: Groq client, `DEFAULT_MODEL`, `MODEL_ROUTING`, and
  `get_model_for_complexity()`. The client is now constructed lazily via a `@lru_cache`d
  `get_llm_client()` (Phase 2) — no client is built at import time. Model routing values are
  read from `src/config.py`'s `Settings`.
- **`src/services/database_service.py`**: On-demand CSV → SQLite conversion. DB saved as
  `data/{session_id}_{table_name}.db`.

### Response Schema (`src/utils/schemas.py`)

`AnalysisResponse` includes: `question`, `result`, `status`, `attempts`, `time_taken`,
`model_used`, `row_count`, `column_count`, `file_name`, `timestamp`, `agents_used`, `task_type`,
`reasoning`, `chart_path`, `session_id`.

## Configuration

**Centralized in `src/config.py`** (Phase 2) — a `pydantic-settings` `Settings` class, accessed
via the process-cached `get_settings()`. Owns model IDs, retry budget, prompt sample rows, the
500-row complexity threshold, session TTL, max file size, all data/docs/upload/chart paths, the
embedding model name, and RAG `top_k`/distance threshold. Every field is overridable via an env
var or `.env` entry of the same name (uppercased); defaults match the values that were
previously hardcoded, so no `.env` changes are required after this refactor.

**Model routing — remapped in Phase 1.** The three previously configured Llama IDs are gone
from Groq. The only usable free-tier text models are `openai/gpt-oss-20b` (fast/cheap) and
`openai/gpt-oss-120b` (strongest). Because two tiers must share one model, **tiering means more
than model identity**: complexity drives model *and* retry budget (`Settings.retry_budget`)
*and* prompt richness (`Settings.prompt_sample_rows`). This keeps the two-call planner and the
500-row threshold meaningful.

- Embeddings: `all-MiniLM-L6-v2` via sentence-transformers, loaded lazily on first RAG use
  (Phase 2) — not at import time
- FAISS index built at startup in the `src/main.py` lifespan handler (still eager there, by
  design — the app needs it ready before serving requests)
- Environment: `GROQ_API_KEY` required in `.env`; the Groq client itself is constructed lazily
  on first use (Phase 2), not at import time
- Groq free tier: 30 RPM, 1k RPD, **8K TPM**, 200k TPD — the TPM ceiling is tight against
  131k-context models

## Data

- Sample data: `sample_data.csv` — TechMart Electronics sales (date, revenue, region, product),
  12 rows
- Test fixtures: `tests/data/` — `large_sales.csv` (1000 rows), `employees.csv`, `stocks.csv`,
  `missing_values.csv`, `special_chars.csv` (spaces/parens/slash in headers), `empty.csv`
- RAG corpus: `docs/business_context.txt`, `docs/data_dictionary.txt`,
  `docs/routing_rules.txt` (only the last is dataset-agnostic)
- Generated at runtime, all gitignored: `data/{session_id}_{table_name}.db`,
  `data/charts/{session_id}.png`, `data/uploads/{session_id}.csv`

## Known issues

Full ranked register with severities and owning phases is in `PHASES.md`. The ones most likely
to bite while working in this codebase:

- **All model IDs are dead** — nothing works until Phase 1a lands
- **`exec()` of LLM-generated code is not sandboxed.** The dict named `safe_environment` in
  `python_agent.py` and `chart_agent.py` is misleading — `exec` auto-injects `__builtins__`, so
  `open`, `__import__`, and `os` are reachable. This is RCE if deployed publicly. Phase 5.
- **`/ask` has a path-traversal hole** — caller-supplied `file_path`, unvalidated. Phase 5.
- ~~**Import-time side effects**~~ — **Fixed in Phase 2.** `llm_service.get_llm_client()` is now
  lazy (`@lru_cache`), `rag_service`'s `SentenceTransformer`/`faiss` load on first RAG use via a
  `RagIndex` class, and `analyst_service.build_agents()` replaces the four import-time agent
  singletons. `python -c "import src.main"` builds no client and loads no transformer.
- **SQLite connections aren't in try-finally** — the cause of Windows `PermissionError` during
  session cleanup. Phase 1b.
- **7 redundant `pd.read_csv` calls** — one request can read the same file up to 6 times.
- **The pipeline is file-path-shaped.** `python_agent` assumes one in-memory dataframe, which
  breaks at warehouse scale. This is the deepest change ahead — Phase 8.

## Current State (Phase 2 complete, Phase 3 next)

V5 file upload merged to `main` via PR #3 (`3a07c1f`). `POST /upload` accepts CSVs via
multipart/form-data, saved to `data/uploads/{session_id}.csv`, with a 30-minute session TTL so
users upload once and ask multiple follow-ups. Chart and DB filenames are UUID-based, fixing the
old `chart.png` collision. `POST /ask` is unchanged for backward compatibility.

Phase 1 (on `claude/v6-revive-and-test`) is done: the Groq models are remapped to
`openai/gpt-oss-20b`/`120b`, the five pending V5 bugs are fixed, 78 automated tests pass, and
`README.md`/`PROJECT_PLAN.md` reflect the data-platform direction. `tests/TEST_RESULTS.md` is
now a historical manual-testing record — its 31 documented results predate the Groq model
retirement and are unreproducible; the pytest suite supersedes it.

Phase 2 (config + DI refactor, on `claude/v6.1-config-di`) is done: `src/config.py` centralizes
the ~18 previously hardcoded values behind a `pydantic-settings` `Settings` class; the Groq
client and the RAG `SentenceTransformer`/FAISS index are now built lazily instead of at import
time; all four agents accept an injectable `client`; `analyst_service.build_agents()` replaces
the four import-time agent singletons (also closing the shared-singleton mutation race); and the
POSIX-only `split("/")` path bug is fixed. 16 new tests added (`test_config.py`,
`test_agent_factory.py`) — full non-live suite is 94 tests, and dropped from 32.82s to 2.09s
since nothing loads a SentenceTransformer at collection time anymore.

**Phase 3 (API + integration tests, CI) is next**, on branch `claude/v6.2-ci`: integration tests
for `/upload` and `/ask`, an orchestration test suite covering the python/sql `elif` mutual
exclusion and the chart-only-plan 500 bug, a `live_api`-marked test file, and a GitHub Actions
CI workflow.
