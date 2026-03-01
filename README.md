# Autonomous Data Analyst AI Agent

An AI-powered system that accepts CSV data, understands its structure, and answers business questions by generating and executing Python code — with built-in retry logic and error handling.

## What it does
- Accepts CSV file input
- Understands data schema automatically
- Answers business questions in natural language
- Generates Python code using an LLM to produce answers
- Executes generated code safely in a sandboxed environment
- Retries automatically if generated code fails
- Returns structured responses with metadata

## Tech Stack
- Python
- FastAPI
- Groq (LLM provider)
- Llama 3.1 8B (AI model)
- Pandas

## Project Phases
- V1 — LLM + FastAPI ✅
- V2 — Code Execution Layer ✅
- V3 — RAG Integration
- V4 — Multi Agent Orchestration
- V5 — Deployment + Observability

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

### POST /ask
Ask a business question about your CSV data

Request body:
```json
{
    "question": "what is total revenue by month?",
    "file_path": "sample_data.csv"
}
```

Response:
```json
{
    "question": "what is total revenue by month?",
    "result": "...",
    "status": "success",
    "attempts": 1,
    "time_taken": "1.23s",
    "model_used": "llama-3.1-8b-instant",
    "row_count": 12,
    "column_count": 4,
    "file_name": "sample_data.csv",
    "timestamp": "2026-03-01 10:23:45"
}
```

## Architecture
```
Request → FastAPI (ask.py) → Analyst Service → LLM Service (Groq) → Execution Service → Response
                                     ↑                                      |
                                     └──────── Retry if failed ─────────────┘
```