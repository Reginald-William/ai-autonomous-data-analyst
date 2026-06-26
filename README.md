# Autonomous Data Analyst AI Agent

An AI-powered autonomous data analyst that accepts CSV data, understands its structure, retrieves relevant business context using RAG, and answers business questions through a multi-agent architecture — with built-in retry logic, SQL querying, chart generation, and structured responses.

## What it does
- Accepts CSV file input
- Understands data schema automatically
- Retrieves relevant business context using RAG
- Routes questions to specialized agents using an LLM powered planner
- Answers analytical questions using a Python agent with pandas
- Queries data using a SQL agent with SQLite
- Generates charts and visualizations using a Chart agent
- Retries automatically if generated code fails
- Returns structured responses with full metadata

## Tech Stack
- Python
- FastAPI
- Groq (LLM provider)
- Llama 3.1 8B Instant / Llama 3.3 70B Versatile / Llama 4 Scout 17B (dynamic model routing)
- Pandas
- FAISS
- Sentence Transformers
- SQLite
- Matplotlib
- Tabulate

## Project Phases
- V1 — LLM + FastAPI ✅
- V2 — Code Execution Layer ✅
- V3 — RAG Integration ✅
- V4 — Multi Agent Orchestration ✅
- V4.1 — Refactoring & Testing ✅
- V4.2 — Dynamic Model Routing ✅
- V5 — File Upload & Session Management ✅
- V5.1 — Auth (up next)

## Setup

1. Clone the repository

2. Create a virtual environment and activate it
```
source venv/Scripts/activate
```

3. Install dependencies
```
pip install -r requirements.txt
```

4. Create a `.env` file and add your Groq API key
```
GROQ_API_KEY=your_api_key_here
```

5. Run the server
```
uvicorn src.main:app --reload
```

## API Endpoints

### GET /
Welcome message

### GET /health
Health check endpoint

### POST /upload
Upload a CSV file and ask a question. Returns a `session_id` for follow-up questions.

**First request (upload file):**
```bash
curl -X POST http://localhost:8000/upload \
  -F "question=What is total revenue by region?" \
  -F "file=@sample_data.csv"
```

**Follow-up request (reuse session, no re-upload needed):**
```bash
curl -X POST http://localhost:8000/upload \
  -F "question=Show me a bar chart of that" \
  -F "session_id=<session_id_from_response>"
```

Sessions expire after 30 minutes of inactivity.

### POST /ask
Ask a question using a local file path. Kept for development and local testing.

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "what is total revenue by region?", "file_path": "sample_data.csv"}'
```

**Response (both endpoints):**
```json
{
    "question": "what is total revenue by region?",
    "result": "...",
    "status": "success",
    "attempts": 1,
    "time_taken": "2.1s",
    "model_used": "llama-3.3-70b-versatile",
    "row_count": 12,
    "column_count": 4,
    "file_name": "sample_data.csv",
    "timestamp": "2026-03-30 10:10:10",
    "agents_used": ["python"],
    "task_type": "analysis",
    "reasoning": "question asks for calculation so python agent is used",
    "chart_path": null,
    "session_id": "7455452f-f6be-4770-93d9-f24186779432"
}
```

## Architecture (High Level)
```
POST /upload (multipart: file + question)
  │
  ├─ Validate file (CSV, ≤10MB, non-empty, parseable) → 400 on failure
  ├─ Save to data/uploads/{session_id}.csv
  ├─ Register session (30-min TTL, background cleanup every 5 min)
  │
POST /upload (multipart: session_id + question)  ← follow-up, no re-upload
  │
  └─ Lookup session → reuse saved file path
  │
POST /ask (JSON: file_path + question)  ← local dev/testing only
  │
  └─────────────────────────────────────┐
                                        ↓
                                 Analyst Service
                                        │
                                        ├─ Empty CSV? → 400 Bad Request
                                        │
                                        ↓
                                  RAG Service (FAISS)
                              retrieves business context
                                        │
                                        ↓
                                Planner Agent (Two-Call)
                         Call 1: routing → agents + task_type
                         Call 2: complexity → low/medium/high
                          (capped at medium if row_count < 500)
                                        │
                        ┌───────────────┼──────────┬─────────────┐
                        ↓               ↓          ↓             ↓
                   Python Agent     SQL Agent  Chart Agent  Out of Scope
                   LLM+Pandas     LLM+SQLite  LLM+Matplotlib → clear message
                        │               │          │
                        └───────────────┴──────────┘
                  Dynamic Model per Complexity:
                  low  → llama-3.1-8b-instant
                  med  → llama-3.3-70b-versatile
                  high → llama-4-scout-17b
                  Retry Logic (max 3 attempts per agent)
                  Artifacts named with session_id (charts + DBs)
                                        │
                                        ↓
                                 AnalysisResponse
                          (result, status, attempts, model_used,
                           agents_used, chart_path, session_id, ...)
```