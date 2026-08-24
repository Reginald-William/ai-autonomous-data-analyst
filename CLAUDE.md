# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

**Test the API**
```bash
# Original endpoint (local file path — for dev/testing)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is total revenue?", "file_path": "sample_data.csv"}'

# Upload endpoint (multipart — for real users)
curl -X POST http://localhost:8000/upload \
  -F "question=What is total revenue?" \
  -F "file=@sample_data.csv"

# Follow-up question (reuse session, no re-upload)
curl -X POST http://localhost:8000/upload \
  -F "question=What is revenue by region?" \
  -F "session_id=<session_id_from_response>"
```

There are no automated tests currently.

## Architecture

This is a **FastAPI multi-agent data analysis system** that answers natural language questions about CSV data using LLM-generated code execution.

### Request Flow

```
POST /ask  (JSON, file_path) ─────────────────────────────────┐
                                                               ↓
POST /upload (multipart, file + question)             analyst_service.analyse()
  ↓                                                            ↓
  Validate file (CSV, ≤10MB, non-empty, parseable)    PlannerAgent (routes to one or more agents)
  ↓                                                            ↓
  Save to data/uploads/{session_id}.csv          PythonAgent | SQLAgent | ChartAgent
  ↓                                               (code generation + retry loop, max 3 attempts)
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

- **PlannerAgent** (`src/agents/planner_agent.py`): Two-call planner. Call 1 (`llama-3.3-70b-versatile`) decides routing (agents + task_type). Call 2 (`llama-3.1-8b-instant`) classifies complexity (low/medium/high). Complexity is capped at `medium` when `row_count < 500` — not enough data to justify the high complexity model.
- **PythonAgent** (`src/agents/python_agent.py`): Generates and executes pandas code. Captures stdout. On failure, sends the error back to the LLM to fix and retries (3 attempts). Accepts `complexity` param — picks model via `get_model_for_complexity()`.
- **SQLAgent** (`src/agents/sql_agent.py`): Converts CSV to SQLite via `database_service`, generates SQL, executes queries. Same retry logic and complexity-based model routing.
- **ChartAgent** (`src/agents/chart_agent.py`): Generates matplotlib code, saves charts to `data/charts/`. Receives prior analysis result as context. Uses same complexity-based model as the preceding agent.

### Key Services

- **`src/services/analyst_service.py`**: Main orchestration. Loads CSV, extracts metadata, calls PlannerAgent (passing `row_count`), dispatches to agents with `complexity` and `session_id`, returns structured response including `model_used` and `session_id`.
- **`src/services/session_service.py`**: In-memory session store. Maps `session_id` → `{file_path, original_filename, created_at, last_accessed}`. TTL is 30 minutes. Background cleanup task runs every 5 minutes, deletes expired CSV and DB files.
- **`src/services/rag_service.py`**: Builds a FAISS index on startup from `docs/` (business_context.txt, data_dictionary.txt, routing_rules.txt). Every agent call retrieves relevant context via sentence-transformer embeddings.
- **`src/services/llm_service.py`**: Shared module with Groq client, `DEFAULT_MODEL`, `MODEL_ROUTING` dict, and `get_model_for_complexity(complexity)`. Referenced by all agents.
- **`src/services/database_service.py`**: On-demand CSV → SQLite conversion. When `session_id` provided, DB saved as `data/{session_id}_{table_name}.db`. Falls back to `data/{table_name}.db` for `/ask`.

### Response Schema (`src/utils/schemas.py`)

`AnalysisResponse` includes: `question`, `result`, `status`, `attempts`, `time_taken`, `model_used`, `row_count`, `column_count`, `file_name`, `timestamp`, `agents_used`, `task_type`, `reasoning`, `chart_path`, `session_id`.

### Configuration

- Dynamic model routing via `MODEL_ROUTING` in `llm_service.py`:
  - `low` → `llama-3.1-8b-instant` (count, total, simple lookups)
  - `medium` → `llama-3.3-70b-versatile` (group by, filter+aggregate, charts)
  - `high` → `meta-llama/llama-4-scout-17b-16e-instruct` (multi-step, trend, correlation) — only used when `row_count >= 500`
- Complexity classifier uses `llama-3.1-8b-instant` at `temperature=0.0` for determinism
- Embeddings: `all-MiniLM-L6-v2` via sentence-transformers
- FAISS index built at startup in `src/main.py` lifespan handler
- Environment: `GROQ_API_KEY` required in `.env`

### Data

- Sample data: `sample_data.csv` — TechMart Electronics sales (date, revenue, region, product), 12 rows
- Large test data: `tests/data/large_sales.csv` — 1000 rows, used for high complexity testing
- Business context for RAG: `docs/business_context.txt`, `docs/data_dictionary.txt`, `docs/routing_rules.txt`
- Generated databases: `data/{session_id}_{table_name}.db` (upload) or `data/{table_name}.db` (/ask)
- Generated charts: `data/charts/{session_id}.png`
- Uploaded files: `data/uploads/{session_id}.csv` — persisted for session duration, cleaned up on TTL expiry

### Current State (V5 File Upload Complete — V5.1 Auth Up Next)

V5 file upload is complete. A new `POST /upload` endpoint accepts CSV files via multipart/form-data. Uploaded files are saved to `data/uploads/{session_id}.csv`. Session service manages file retention with a 30-minute TTL — users upload once and ask multiple follow-up questions using the returned `session_id`. Background cleanup task runs every 5 minutes to delete expired session files. Chart filenames are now UUID-based (`data/charts/{session_id}.png`), fixing the hardcoded `chart.png` collision bug. SQLite DB filenames are prefixed with `session_id` to prevent collisions. `original_filename` is threaded through the stack so `file_name` in responses shows the real filename. The existing `POST /ask` endpoint is unchanged (backward compat). `python-multipart` added to requirements. 15/15 tests passing. V5.1 plans JWT auth and user accounts.
