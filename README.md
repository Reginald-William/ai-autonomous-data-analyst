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
- Llama 3.1 8B (AI model)
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
- V4.1 — Refactoring & Testing 🔄
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
    "question": "what is total revenue by region?",
    "file_path": "sample_data.csv"
}
```

Response:
```json
{
    "question": "what is total revenue by region?",
    "result": "...",
    "status": "success",
    "attempts": 1,
    "time_taken": "2.1s",
    "model_used": "llama-3.1-8b-instant",
    "row_count": 12,
    "column_count": 4,
    "file_name": "sample_data.csv",
    "timestamp": "2026-03-30 10:10:10",
    "agents_used": ["python"],
    "task_type": "analysis",
    "reasoning": "question asks for calculation so python agent is used",
    "chart_path": null
}
```

## Architecture
```
Request → FastAPI (ask.py) → Analyst Service
                                    │
                                    ↓
                              RAG Service (FAISS)
                          retrieves business context
                                    │
                                    ↓
                              Planner Agent
                          (LLM decides routing)
                                    │
                          ┌─────────┼──────────┐
                          ↓         ↓          ↓
                    Python Agent  SQL Agent  Chart Agent
                    LLM+Pandas  LLM+SQLite  LLM+Matplotlib
                          │         │          │
                          └─────────┴──────────┘
                                    │
                        Retry Logic (max 3 attempts)
                                    │
                                    ↓
                                  Result
                            Structured Response
                            (AnalysisResponse)
```