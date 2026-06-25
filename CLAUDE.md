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
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is total revenue?", "file_path": "sample_data.csv"}'
```

There are no automated tests currently.

## Architecture

This is a **FastAPI multi-agent data analysis system** that answers natural language questions about CSV data using LLM-generated code execution.

### Request Flow

```
POST /ask → analyst_service.analyse()
              ↓
         PlannerAgent (routes to one or more agents)
              ↓
    PythonAgent | SQLAgent | ChartAgent
         (code generation + retry loop, max 3 attempts)
              ↓
         AnalysisResponse (Pydantic)
```

### Agent Responsibilities

- **PlannerAgent** (`src/agents/planner_agent.py`): Two-call planner. Call 1 (`llama-3.3-70b-versatile`) decides routing (agents + task_type). Call 2 (`llama-3.1-8b-instant`) classifies complexity (low/medium/high). Complexity is capped at `medium` when `row_count < 500` — not enough data to justify the high complexity model.
- **PythonAgent** (`src/agents/python_agent.py`): Generates and executes pandas code. Captures stdout. On failure, sends the error back to the LLM to fix and retries (3 attempts). Accepts `complexity` param — picks model via `get_model_for_complexity()`.
- **SQLAgent** (`src/agents/sql_agent.py`): Converts CSV to SQLite via `database_service`, generates SQL, executes queries. Same retry logic and complexity-based model routing.
- **ChartAgent** (`src/agents/chart_agent.py`): Generates matplotlib code, saves charts to `data/charts/`. Receives prior analysis result as context. Uses same complexity-based model as the preceding agent.

### Key Services

- **`src/services/analyst_service.py`**: Main orchestration. Loads CSV, extracts metadata, calls PlannerAgent (passing `row_count`), dispatches to agents with `complexity`, returns structured response including `model_used`.
- **`src/services/rag_service.py`**: Builds a FAISS index on startup from `docs/` (business_context.txt, data_dictionary.txt, routing_rules.txt). Every agent call retrieves relevant context via sentence-transformer embeddings.
- **`src/services/llm_service.py`**: Shared module with Groq client, `DEFAULT_MODEL`, `MODEL_ROUTING` dict, and `get_model_for_complexity(complexity)`. Referenced by all agents.
- **`src/services/database_service.py`**: On-demand CSV → SQLite conversion. Database files land in `data/`.

### Response Schema (`src/utils/schemas.py`)

`AnalysisResponse` includes: `answer`, `agent_used`, `code_executed`, `chart_path`, `rows_analyzed`, `columns_analyzed`, `execution_time`.

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
- Generated databases: `data/*.db`; generated charts: `data/charts/`

### Current State (V4.2 Complete — V5 Up Next)

V4.2 is fully complete. Dynamic model routing implemented — PlannerAgent now uses a two-call design: Call 1 handles routing (agents + task_type), Call 2 is a dedicated complexity classifier on `llama-3.1-8b-instant`. Complexity drives model selection via `get_model_for_complexity()` in `llm_service.py`. High complexity is capped at `medium` for datasets under 500 rows. Complexity rules live in `docs/routing_rules.txt` (RAG-retrieved). All 9 test scenarios passing across low/medium/high complexity and edge cases. Large test dataset (`tests/data/large_sales.csv`, 1000 rows) added for high complexity testing. V5 plans file upload endpoint, auth, and Docker deployment.
