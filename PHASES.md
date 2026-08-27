# Phases — Data Engineering Platform Build

**Purpose of this file:** the single source of truth for where this project is. Each phase is
scoped to roughly one weekend at ~10 hrs/week, has its own branch, and ends mergeable. Work
**one phase per chat session** — read this file first to find the current phase.

**Last updated:** 2026-08-27 · **Current phase:** 2 complete, 3 up next · **Branch:**
`claude/v6.1-config-di`

---

## Why this plan exists

This repo was heading toward a monetized SaaS product. That direction is dead. It is now
explicitly a **Data Engineering portfolio piece**, targeting applications from ~April 2027.

The problem with the previous direction: strip away the LLM layer and the data did almost
nothing. A CSV was read into in-process SQLite, queried once, and discarded. No ingestion, no
scheduling, no warehouse, no modeling, no lineage, no data quality. A DE interviewer would see
a competent AI app, not evidence of pipeline engineering.

**Target architecture** — the existing multi-agent system becomes the *serving layer* on top
of a real platform:

```
Public API (NYC TLC), ingested on a schedule
    -> ingestion (Python, orchestrated by Airflow)
Raw storage (local Parquet / GCS)
    -> transformation (dbt: staging -> intermediate -> marts)
Warehouse (BigQuery, free tier)
    -> data quality (dbt tests + Great Expectations)
Existing agent queries the marts layer instead of a CSV
```

**Preserved and not to be rewritten:** the hand-rolled `PlannerAgent`, complexity-based
routing, and retry loops. This is the differentiator. Almost every candidate's AI project is
LangChain plus glue; rewriting into a framework destroys what makes this repo distinctive.
LangGraph is *added alongside* in Phase 11, never as a replacement.

## Sequencing principle

> You cannot safely change code you cannot test, and you cannot test code with import-time
> side effects.

That single sentence dictates Phases 1–3, and is the answer to "why did you start with
testing?"

---

## Phase table

| # | Phase | Branch | Weekends | Target | Status |
|---|---|---|---|---|---|
| 1 | Resurrection + first tests | `claude/v6-revive-and-test` | 1 | Aug 2026 | ✅ Done |
| 2 | Config + DI refactor | `claude/v6.1-config-di` | 1 | Sep 2026 | ✅ Done |
| 3 | API + integration tests, CI | `claude/v6.2-ci` | 1 | Sep 2026 | ⬜ |
| 4 | Dynamic data context | `claude/v6.3-data-context` | 1 | Sep 2026 | ⬜ |
| 5 | Docker + Cloud Run + security | `claude/v7-deploy` | 2 | Sep–Oct 2026 | ⬜ |
| 6 | Ingestion: source TBD → Parquet | `claude/v8-ingestion` | 1 | Oct 2026 | ⬜ |
| 7 | dbt + BigQuery: staging → marts | `claude/v9-dbt-bigquery` | 2 | Oct 2026 | ⬜ |
| 8 | Data-source abstraction; agent reads marts | `claude/v10-warehouse-serving` | 2 | Nov 2026 | ⬜ |
| 9 | Airflow (Docker) + Cloud Scheduler | `claude/v11-orchestration` | 2 | Nov 2026 | ⬜ |
| 10 | Data quality: dbt tests + Great Expectations | `claude/v12-data-quality` | 1 | Dec 2026 | ⬜ |
| 11 | LangGraph dual implementation | `claude/v13-langgraph` | 1 | Dec 2026 | ⬜ |
| 12 | Streamlit demo UI | `claude/v14-streamlit` | 1 | Jan 2027 | ⬜ |
| 13 | Polish: docs, diagrams, ADR log | `claude/v15-polish` | 1 | Jan 2027 | ⬜ |

17 weekends across ~21 available. The slack is deliberate — Phases 7, 8, and 9 are the most
likely to overrun.

**If time runs short:** cut Phase 12 (Streamlit), not Phase 11 (LangGraph). See
"Career framing" below.

---

## Locked decisions — do not re-litigate

1. **Tests: hybrid.** Pure units first (CI green fast) → config/DI refactor → integration.
2. **Orchestration: Docker Airflow locally + Cloud Run Jobs & Cloud Scheduler deployed.**
   Cloud Composer has **no free tier** (~$300+/mo) — never use it.
3. **Python agent: keep both agents, dual-source.** SQL agent → BigQuery marts; Python agent
   gets a *bounded* `LIMIT`ed pull into a dataframe for pandas-shaped work.
4. **CSV and warehouse side by side**, behind one `DataSource` abstraction.
5. **Model tiers differentiated beyond model choice** — complexity drives model *and* retry
   budget *and* prompt richness (forced by the Groq retirement; see Phase 1).
6. **Monetization killed.** No SaaS tiers, no usage tracking, no API-key billing, no
   white-label. A minimal Streamlit demo UI only, no auth.
7. **Security fixes land with the Cloud Run deploy, before deploying** — not after.

## Career framing

Targeting **both** Data Engineering and Agentic AI roles. "AI agents querying a real
warehouse" is precisely the emerging AI Platform / AI Data Engineer intersection, and few
candidates occupy it — most agent projects have no data platform, most DE projects have no
agent work.

The build is **DE-weighted** (more open roles, more standardized interview loop, maps onto
existing QA/ETL experience — the stronger fallback), but the agent story stays strong. At
application time: **one repo, two README framings** — lead with the platform for DE
applications, lead with the agent architecture for AI roles.

---

## Phase 1 — Resurrection + first tests ✅

**Branch:** `claude/v6-revive-and-test` · **1 weekend**

### The problem

**The app is 100% non-functional.** Verified 2026-08-24 against the live Groq API with the
project's own key: all three models in `MODEL_ROUTING` are **absent from the API** — not
deprecated, gone. No Llama text-generation model remains on Groq at all. Every request dies at
the planner's first call.

Dead: `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`,
`meta-llama/llama-4-scout-17b-16e-instruct`. Also gone: `qwen/qwen3-32b`.

Consequently **all 31 documented outcomes in `tests/TEST_RESULTS.md` are unreproducible.**

Do not write tests against model IDs that 404. Fix the models first.

### 1a. Model remap — do this before anything else

`src/services/llm_service.py`:

```python
MODEL_ROUTING = {
    "low":    "openai/gpt-oss-20b",   # fast/cheap: counts, totals, lookups
    "medium": "openai/gpt-oss-120b",  # grouping, filtering, charts
    "high":   "openai/gpt-oss-120b",  # same model, richer prompt + more retries
}
DEFAULT_MODEL = "openai/gpt-oss-120b"
```

Only two usable free-tier text models exist, so tiering **must** mean more than model identity
or it means nothing. Add:

```python
RETRY_BUDGET       = {"low": 2, "medium": 3, "high": 5}
PROMPT_SAMPLE_ROWS = {"low": 3, "medium": 5, "high": 10}
```

`python_agent`/`sql_agent` read `max_attempts` from `RETRY_BUDGET[complexity]` instead of the
hardcoded `3`; `get_csv_context()` takes a `sample_rows` count. This keeps the two-call planner
and the 500-row `HIGH_COMPLEXITY_ROW_THRESHOLD` meaningful — they now govern retry policy and
prompt budget rather than only model choice.

**Interview answer:** "My provider retired the entire model family my routing depended on. I
re-derived the tiers around retry budget and prompt richness rather than model identity, so the
routing survives provider churn."

### 1b. Pending V5 bug fixes

Found during Postman testing after V5 shipped.

| File | Change |
|---|---|
| `src/services/database_service.py` | Wrap the SQLite connection in `contextlib.closing` / try-finally; stop erasing the original exception type with `raise Exception(...)` |
| `src/agents/sql_agent.py` (`execute_sql`) | Same connection fix — **this is the root cause of the Windows `PermissionError` on cleanup** |
| `src/services/session_service.py` | Wrap every `os.remove()` in `try/except (PermissionError, OSError)`; log and let the next cycle retry. Extend `cleanup_orphaned_files()` to sweep `data/*.db` |
| `src/main.py` | Add a `RequestValidationError` handler → clean 400 instead of the verbose Pydantic 422 |
| `requirements.txt` | Add `requests` (imported by `src/groq_all_models.py` but missing — latent CI/Docker failure), plus `pytest`, `pytest-cov`, `pytest-mock` |

### 1c. First tests — pure units only, no refactor required

**Added:** `pytest.ini`, `tests/__init__.py`, `tests/conftest.py`, and:

| Test file | ~Tests | Focus |
|---|---|---|
| `tests/unit/test_session_service.py` | 12 | create/get/expiry, TTL boundary, `_delete_session_files`, orphan sweep, thread-safety under `ThreadPoolExecutor` |
| `tests/unit/test_schemas.py` | 6 | `AnalysisResponse` required fields, `Optional` defaults, `agents_used` default isolation |
| `tests/unit/test_llm_service.py` | 8 | `get_model_for_complexity` parametrized; assert every `MODEL_ROUTING` value is a live model ID |
| `tests/unit/test_cleaners.py` | 10 | `clean_sql`/`clean_code` parametrized: bare, fenced, whitespace, empty |
| `tests/unit/test_rag_chunking.py` | 8 | `load_documents` + `split_into_chunks`: min-word threshold, paragraph splitting, filename metadata |
| `tests/unit/test_database_service.py` | 8 | table-name derivation + sanitization, `session_id` prefixing, real SQLite round-trip in `tmp_path` |

**~52 tests.** `conftest.py` provides `sample_csv`, `empty_csv`, `messy_csv`, `tmp_data_dir`
(monkeypatched cwd so nothing writes into the real `data/`), and `fake_groq_client`.

Register markers: `unit`, `integration`, `live_api`.

**Done when:** `pytest -m "not live_api"` green (~52 tests); `/upload` answers a real question
with `openai/gpt-oss-120b`; a `data/*.db` file is deleted after TTL with no `PermissionError`.

---

## Phase 2 — Config + DI refactor ✅

**Branch:** `claude/v6.1-config-di` · **1 weekend** · **Completed 2026-08-27**

September's Docker work pulled forward — you cannot ship hardcoded paths and model IDs in a
container. It also removes the test blockers.

**Added:** `src/config.py` — a `pydantic-settings` `Settings` class owning the ~18 hardcoded
values (model IDs, retry budget, prompt sample rows, `session_ttl_minutes`, `max_file_size`, row
threshold, `uploads_dir`, `charts_dir`, `data_dir`, `docs_dir`, embedding model, RAG `top_k` +
distance threshold, temperatures), cached process-wide via `get_settings()` (`@lru_cache`). Plus
`tests/unit/test_config.py` (11) and `tests/unit/test_agent_factory.py` (5).

**Modified:**
- `src/services/llm_service.py` — `client = Groq(...)` at import became a lazy,
  `@lru_cache`d `get_llm_client()`; `DEFAULT_MODEL`/`MODEL_ROUTING`/`RETRY_BUDGET`/
  `PROMPT_SAMPLE_ROWS` now derive from `Settings` instead of hardcoded literals (module
  attribute names unchanged, so no caller needed to change)
- `src/agents/*.py` — `__init__(self, client=None)` on all four agents (`chart_agent.py` also
  takes `settings=None` for `charts_dir`); falls back to `get_llm_client()`/`get_settings()`
  when nothing is injected
- `src/services/analyst_service.py` — replaced the four module-level agent singletons with a
  `build_agents(client=None)` factory called inside `analyse()`; also fixes the shared-singleton
  mutation race (risk #13) since each request now gets its own agent instances
- `src/services/rag_service.py` — `SentenceTransformer` and `faiss` imports moved inside
  methods, model construction deferred to first actual use; module globals (`model`, `index`,
  `chunks`) replaced with a `RagIndex` class holding that state, wrapped by a lazily-created
  module-level singleton so `build_index()`/`retrieve_context()` call sites are unchanged
- `src/agents/chart_agent.py` — removed the `os.makedirs` side effect from `__init__`
  (directory creation already happens once in `main.py`'s lifespan)
- `src/services/analyst_service.py` — `file_path.split("/")[-1]` (POSIX-only, broke on Windows
  paths) replaced with `os.path.basename(file_path)` (risk #15)

**Measured impact:** full non-live suite dropped from 32.82s to 2.09s (94 tests) — the ~35s
SentenceTransformer import-time tax (risk #8) is gone since nothing imports the model at
collection time anymore.

**Done when:** `python -c "import src.main"` builds no Groq client and loads no transformer
✅ verified (Groq `lru_cache` shows 0 hits/misses after import; no "Loading weights" output);
Phase 1 tests still pass ✅ (94/94, `pytest -m "not live_api"`).

---

## Phase 3 — API + integration tests, CI ⬜

**Branch:** `claude/v6.2-ci` · **1 weekend**

**Added:**
- `tests/integration/test_upload_endpoint.py` (~14) — ports TEST_RESULTS.md scenarios 1–10
- `tests/integration/test_ask_endpoint.py` (~6) — backward compat, plus a path-traversal
  rejection test marked `xfail` until Phase 5
- `tests/integration/test_analyst_orchestration.py` (~12) — routing → dispatch, the
  `python`/`sql` `elif` mutual exclusion, out-of-scope short circuit, chart-only plan (a latent
  500: `result=None` fails Pydantic validation), agent-failure path
- `tests/live/test_live_api.py` (~3) — `@pytest.mark.live_api`, deselected by default
- `.github/workflows/ci.yml` — matrix 3.11/3.13, `ruff check`, `pytest -m "not live_api"
  --cov=src --cov-fail-under=70`. **Never** put `GROQ_API_KEY` in the default CI job.

**Note:** `python_agent.execute_code` reassigns `sys.stdout`, which corrupts pytest capture if
an exception path skips the restore. Consider `contextlib.redirect_stdout`.

**Done when:** green CI badge in README; ~100 tests; ≥70% coverage.

---

## Phase 4 — Dynamic data context ⬜

**Branch:** `claude/v6.3-data-context` · **1 weekend**

`docs/business_context.txt` and `docs/data_dictionary.txt` describe TechMart Electronics
(Laptop/Phone/Tablet, 4 Indian regions) and are hardcoded to `sample_data.csv`. RAG retrieves
them for *every* question on *every* dataset. Postman testing proved the consequence: on a real
sales CSV, "how many Fruits under Item Type?" returned *"cannot be answered from the provided
data"* because the planner read TechMart context and ruled Fruits out of scope.

**The system only works on its own sample file** — fatal for a portfolio piece someone else
will clone and run.

**Added:** `src/services/data_context_service.py` — `generate_data_context(file_path,
sample_rows)` returns row/column counts, dtypes, unique counts, categorical values (≤20
unique), numeric ranges, null counts, sample rows. Pure pandas, no LLM call. Plus
`tests/unit/test_data_context_service.py` (~12) over all six fixtures.

**Modified:** `rag_service.py` gains `retrieve_routing_context()` (filters FAISS hits to
`routing_rules.txt` only); `analyst_service.py` generates the context once and passes it to all
agents (also removing several of the 7 redundant `pd.read_csv` calls); planner/python/sql
agents accept `data_context`; `sql_agent` quotes column names (fixes the observed
`WHERE Total Revenue > 10000` syntax error); `chart_agent` gets large-dataset prompt rules
(fixes the observed cluttered charts).

**Done when:** questions on `tests/data/employees.csv` and `stocks.csv` route to an agent
instead of returning out-of-scope.

---

## Phase 5 — Docker + Cloud Run + security ⬜

**Branch:** `claude/v7-deploy` · **2 weekends** — do not attempt in one

### Security — before deploy, not after

1. **`/ask` path traversal** (`src/routes/ask.py`) — caller-supplied `file_path` read with no
   validation. Harmless locally; a live arbitrary-file-read on a public URL. Resolve and
   allowlist the path, or gate the endpoint behind a setting defaulting to `False`.
2. **`exec()` of LLM-generated code** — `python_agent` and `chart_agent` both `exec` model
   output with a dict named `safe_environment` that is **not a sandbox**: `exec` auto-injects
   `__builtins__`, so `open`, `__import__`, and `os` are reachable. **This is RCE on a public
   URL.** Mitigations: restricted `__builtins__`, AST allowlist validation, wall-clock timeout,
   read-only Cloud Run filesystem, no service-account privileges, `max-instances=2`.
   **Document this honestly in `docs/THREAT_MODEL.md`** — an interviewer who spots `exec` will
   respect a documented threat model far more than a silent hope.

### The Docker size problem

`torch` + `sentence-transformers` + `faiss-cpu` is ~2.5 GB installed; a naive image is ~3.5 GB.
Artifact Registry's free tier is **0.5 GB**.

**Open question to decide here:** after Phase 4, RAG retrieves from one 3 KB file
(`routing_rules.txt`). Inlining those rules into the prompt removes 2.5 GB of dependencies and
most of this problem. *"I removed a 2.5 GB dependency that served a 3 KB corpus"* is a stronger
engineering story than *"I built a RAG pipeline"*, and the RAG work stays in git history.
Alternatives: ONNX embeddings (~90 MB), or precompute the index at build time.

**Done when:** public HTTPS URL answers a question; image <1.5 GB; `/ask` rejects traversal.

---

## Phase 6 — Ingestion ⬜

**Branch:** `claude/v8-ingestion` · **1 weekend**

### Source: not yet finalized

NYC TLC Trip Record Data was proposed as the leading candidate during initial planning, but
the owner wants to revisit the choice when this phase actually starts and pick something that
also suits their own interest — not decide it purely on paper criteria. **Confirm the source
with the owner before writing any ingestion code.** See the reference memory on this topic for
the reasoning behind NYC TLC and the other candidates considered (GH Archive, Open-Meteo,
Alpha Vantage/FRED/World Bank, GBFS).

Whatever gets chosen, the same volume-control reasoning applies: BigQuery's free tier is 10 GB
storage / 1 TB queried per month, so ingest incrementally (one month/period at a time) rather
than bulk-loading history — both to stay in budget and because incremental ingestion is itself
part of what Phase 9's orchestration needs to demonstrate.

**Added:** `ingestion/` — a per-source module under `sources/`, `storage.py`, `cli.py`
(`python -m ingestion --source <name> --month 2024-01`), `tests/unit/test_ingestion.py` (~10,
mocked HTTP — never hits the network). Exact filenames depend on the source chosen.

**Done when:** the CLI ingests one month to partitioned local Parquet, idempotently, with a
row-count assertion.

---

## Phase 7 — dbt + BigQuery ⬜

**Branch:** `claude/v9-dbt-bigquery` · **2 weekends**

Weekend 1: GCP project, BigQuery dataset, service account, dbt-bigquery connection, raw
Parquet → BigQuery, `staging` models. Weekend 2: `intermediate` + `marts`, dbt tests, docs,
lineage graph.

**Added:** `dbt_project/` — `dbt_project.yml`, `profiles.yml.example` (**never commit real
credentials**), `models/staging/stg_trips.sql`, `models/intermediate/`,
`models/marts/{fact_trips,dim_zone,dim_vendor}.sql`, `seeds/taxi_zones.csv`, `macros/`, plus
`docs/DATA_MODEL.md` explaining the star schema.

Staging does the cleanup TLC demands: cast types, snake_case renames, filter negative fares,
drop dropoff-before-pickup rows, standardize the zone join.

**⚠️ This is the phase where money is possible.** BigQuery free tier: 10 GB storage, **1 TB
queried/month**. Storage is fine; query volume is the risk — repeated full-table scans during
dbt development add up. Before writing the first model: **set a billing budget alert at $1**
and a BigQuery custom quota (e.g. 50 GB/day), partition `fact_trips` by pickup date, cluster by
zone, and set `maximum_bytes_billed` in `profiles.yml` as the hard stop.

**Done when:** `dbt build` passes; `dbt docs generate` produces a lineage graph.

---

## Phase 8 — Warehouse serving ⬜

**Branch:** `claude/v10-warehouse-serving` · **2 weekends**

The deepest architectural change. **The entire request pipeline is file-path-shaped:**
`analyse(question, file_path)` reads a CSV for `row_count`, then hands `file_path` to agents
that each re-read it. `python_agent.execute_code` does `pd.read_csv(file_path)` then
`exec(code, {"df": df})` — the Python agent *fundamentally assumes one in-memory dataframe*.
Against a 36M-row marts table, "load it all into `df`" is invalid. This is not a
`database_service` swap; it is a rethink.

**Added:** `src/datasources/` — `base.py` (`DataSource` protocol: `get_schema()`,
`run_query(sql)`, `load_sample(limit)`, `row_count()`), `csv_source.py`, `bigquery_source.py`,
`factory.py`.

**Modified:** `analyse()` takes a `DataSource`, not a `file_path`. `sql_agent` executes via
`source.run_query()` — SQLite for CSV, BigQuery SQL for marts. `python_agent` gets the
**bounded loader** `source.load_sample(limit=settings.max_pandas_rows)` (default 50k), and its
prompt states plainly that `df` is a bounded sample so the model never reports a sample
statistic as a population one. `routes/ask.py` gains `POST /warehouse/ask`.

`database_service.py` largely dissolves into `csv_source.py`. **Phases 1–3's test suite is what
makes this refactor safe** — say that in an interview.

**Cost guard — non-negotiable:** every agent-issued BigQuery query must set
`maximum_bytes_billed`. An LLM emitting `SELECT * FROM fact_trips` is exactly how a free tier
gets breached.

**Done when:** the same question is answered against both a CSV source and the marts source.

---

## Phase 9 — Orchestration ⬜

**Branch:** `claude/v11-orchestration` · **2 weekends**

**Added:** `airflow/dags/nyc_tlc_monthly.py` (ingest → load → `dbt build` → DQ),
`airflow/docker-compose.yml`, `airflow/README.md` with screenshots for the portfolio;
`deploy/cloud_run_job.yaml`, a Cloud Scheduler setup script; `tests/unit/test_dags.py` (~6 —
DAG imports, no cycles, dependencies, retries set).

**Windows caveat:** Airflow does not run natively — use **WSL2 + Docker Compose**, and budget
setup time. Cloud Composer has **no free tier** (~$300+/mo) — do not touch it.

Deployed path is Cloud Run Jobs + Cloud Scheduler (free tier: 3 jobs). Airflow is the local,
demonstrable artifact.

**Interview answer:** "I built the DAG in Airflow because it's the industry standard and I
wanted to learn its execution model, but deployed on Cloud Scheduler because Composer costs
$300/month for a portfolio project. Here's the DAG, and here's the same dependency graph
running serverless."

---

## Phase 10 — Data quality ⬜

**Branch:** `claude/v12-data-quality` · **1 weekend**

**Added:** dbt schema tests (`not_null`, `unique`, `accepted_values`, `relationships` on the
zone FK), `dbt_utils.expression_is_true` for fare > 0 and dropoff > pickup,
`great_expectations/` suite on the raw layer with checkpoints wired into the DAG,
`docs/DATA_QUALITY.md`, and a `dbt source freshness` step.

**Division of labor to defend:** Great Expectations guards the **raw boundary** (did the source
change shape?); dbt tests guard the **model** (are my transformation assumptions holding?).

---

## Phase 11 — LangGraph dual implementation ⬜

**Branch:** `claude/v13-langgraph` · **1 weekend** · **load-bearing, do not cut**

**Do not replace the hand-rolled orchestrator.** LangChain/LangGraph appears in target job
descriptions, so absence is a keyword-screen risk — but rewriting turns the interview question
from "how did you design this?" into "so you followed a tutorial?" A dual implementation solves
both.

**Added:** `src/orchestration/native.py` (today's `analyse()` logic extracted),
`src/orchestration/langgraph_impl.py` (the *same* graph as a `StateGraph`),
`src/orchestration/__init__.py` (selects on `settings.orchestrator`),
`docs/ORCHESTRATION_COMPARISON.md`, `tests/integration/test_orchestrator_parity.py` (~10 — both
implementations must return equivalent `AnalysisResponse` for identical fake-LLM inputs; **this
test is the argument**).

**Modified:** `src/config.py` gains `orchestrator: Literal["native", "langgraph"] = "native"`.
`requirements.txt` adds `langgraph` + `langchain-groq` **only** — not full `langchain`, given
the Docker weight problem.

The comparison doc must contain **real measured numbers**: p50/p95 latency, LOC, dependency size
delta, cold-start delta. A comparison without measurements is an opinion.

---

## Phase 12 — Streamlit demo ⬜

**Branch:** `claude/v14-streamlit` · **1 weekend** · **cut this first if time runs short**

`streamlit_app/app.py` — no auth, no tiers. Upload a CSV *or* query the warehouse; question
box; result + chart; and a sidebar showing which agents ran, the complexity tier, model used,
and attempt count. **That sidebar is the demo's real value** — it makes the orchestration
visible.

---

## Phase 13 — Polish ⬜

**Branch:** `claude/v15-polish` · **1 weekend**

Architecture diagram, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` (an ADR log — rare and
genuinely impressive), README rewrite with both framings, CI + coverage badges. Move
`src/groq_all_models.py` to `scripts/` or delete it.

---

## Candidate Phase 14 — eval harness

Not scheduled. Golden-question sets, routing-accuracy measurement, regression detection on
agent output. **Evals are QA for non-deterministic systems**, and a QA background is a real
differentiator for agent roles where almost no candidate thinks rigorously about test design.
Strong addition if time allows.

---

## Risk register

| # | Risk | Severity | Phase |
|---|---|---|---|
| 1 | App fully dead — all 3 model IDs absent from Groq | Critical | 1 |
| 2 | `exec()` of LLM code = RCE once public; `safe_environment` is not a sandbox | Critical | 5 |
| 3 | `/ask` path traversal — unvalidated caller-supplied `file_path` | High | 5 |
| 4 | Pipeline is file-path-shaped; Python agent assumes one in-memory df | High | 8 |
| 5 | BigQuery cost blowout — LLM `SELECT *` with no `maximum_bytes_billed` | High | 7, 8 |
| 6 | Docker image ~3.5 GB from torch/faiss for a 3 KB corpus | High | 5 |
| 7 | RAG hardcoded to TechMart — other datasets rejected out-of-scope | High | 4 |
| 8 | ~~Import-time singletons block clean testing~~ — **Resolved in Phase 2.** Confirmed 2026-08-26: `tests/unit/test_cleaners.py` took 35s because instantiating any agent imported `rag_service`, which loaded a real SentenceTransformer at import. Fixed by deferring the `SentenceTransformer`/`faiss` imports and model construction into `RagIndex` methods. Full suite time dropped 32.82s → 2.09s. | High | 2 ✅ |
| 9 | Groq 8K TPM ceiling vs 131k-context models; needs backoff | Medium | 1, 4 |
| 10 | Airflow on Windows needs WSL2; Composer has no free tier | Medium | 9 |
| 11 | `sys.stdout` reassignment corrupts pytest capture | Medium | 3 |
| 12 | 7 redundant `pd.read_csv` calls — up to 6 reads per request | Medium | 4, 8 |
| 13 | ~~Shared-singleton `self.model` mutation — races under concurrency~~ — **Resolved in Phase 2** via `build_agents()` constructing fresh agent instances per request instead of four import-time module singletons | Medium | 2 ✅ |
| 14 | Chart-only plan → `result=None` → Pydantic `ValidationError` → 500 | Medium | 3 |
| 15 | ~~POSIX-only `split("/")` breaks on Windows paths~~ — **Resolved in Phase 2**, replaced with `os.path.basename()` in `analyst_service.py` | Low | 2 ✅ |
| 16 | Table name interpolated into `to_sql` with only `-`/space sanitized | Low | 1 |
| 17 | `requests` imported by `groq_all_models.py` but not in requirements | Low | 1 |
| 18 | `HTTPException` raised from the service layer — HTTP coupling in domain code | Low | 2 |
| 19 | Global exception handler logs without `exc_info` — opaque failures | Low | 1 |
| 20 | `TEST_RESULTS.md` documents 31 unreproducible results | Low | 3 |
| 21 | `clean_code` is duplicated verbatim in `python_agent.py` and `chart_agent.py`, plus a near-identical `clean_sql` in `sql_agent.py` — found while writing `test_cleaners.py` (2026-08-26). Candidate for a shared helper, not urgent | Low | 2 |

## Cost summary — free tiers only

| Service | Free tier | Risk |
|---|---|---|
| Groq | 30 RPM, 1k RPD, 8K TPM, 200k TPD | None — throttled, not billed |
| BigQuery | 10 GB storage, **1 TB query/month** | **Real** — guard with partitioning, `maximum_bytes_billed`, custom quota, $1 budget alert |
| GCS | 5 GB, US regions only | Low — keep raw Parquet under 5 GB or stay local |
| Cloud Run | 2M requests, 360k GB-s/mo | Low — cap `max-instances` |
| Cloud Scheduler | 3 jobs | None |
| Artifact Registry | **0.5 GB** | Moderate — a 3.5 GB image exceeds it (pennies, not zero) |
| Cloud Composer | **NO FREE TIER** | **Avoid entirely** (~$300+/mo) |
| GitHub Actions | 2,000 min/mo private, unlimited public | None if the repo stays public |

**Set a GCP billing budget alert at $1 before touching BigQuery.** Non-negotiable.
