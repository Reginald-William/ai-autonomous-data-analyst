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

- **PlannerAgent** (`src/agents/planner_agent.py`): Uses Groq LLM with RAG context to decide which agents handle the question. Returns a routing plan.
- **PythonAgent** (`src/agents/python_agent.py`): Generates and executes pandas code. Captures stdout. On failure, sends the error back to the LLM to fix and retries (3 attempts).
- **SQLAgent** (`src/agents/sql_agent.py`): Converts CSV to SQLite via `database_service`, generates SQL, executes queries. Same retry logic.
- **ChartAgent** (`src/agents/chart_agent.py`): Generates matplotlib code, saves charts to `data/charts/`. Receives prior analysis result as context.

### Key Services

- **`src/services/analyst_service.py`**: Main orchestration. Loads CSV, extracts metadata, calls PlannerAgent, dispatches to agents, returns structured response.
- **`src/services/rag_service.py`**: Builds a FAISS index on startup from `docs/` (business_context.txt, data_dictionary.txt). Every agent call retrieves relevant context via sentence-transformer embeddings.
- **`src/services/llm_service.py`**: Shared module holding Groq client init (`get_llm_client()`) and `MODEL_NAME` constant. Referenced by all agents.
- **`src/services/database_service.py`**: On-demand CSV → SQLite conversion. Database files land in `data/`.

### Response Schema (`src/utils/schemas.py`)

`AnalysisResponse` includes: `answer`, `agent_used`, `code_executed`, `chart_path`, `rows_analyzed`, `columns_analyzed`, `execution_time`.

### Configuration

- LLM: Groq with `llama-3.3-70b-versatile`, temperature `0.1` for determinism
- Embeddings: `all-MiniLM-L6-v2` via sentence-transformers
- FAISS index built at startup in `src/main.py` lifespan handler
- Environment: `GROQ_API_KEY` required in `.env`

### Data

- Sample data: `sample_data.csv` — TechMart Electronics sales (date, revenue, region, product)
- Business context for RAG: `docs/business_context.txt`, `docs/data_dictionary.txt`, `docs/routing_rules.txt`
- Generated databases: `data/*.db`; generated charts: `data/charts/`

### Current State (V4.1)

V4.1 refactoring is complete. `ask_llm`, `fix_code`, `execute_code`, `clean_code` have been migrated into `PythonAgent`. `src/services/llm_service.py` is now a clean shared module (client + model constant only). `src/services/execution_service.py` has been deleted. Model upgraded to `llama-3.3-70b-versatile` for better code generation accuracy. Routing tests passing. Remaining: edge case testing, retry logic testing, RAG testing. V4.2 plans dynamic model routing based on task complexity. V5 plans Docker deployment and observability.
