# Autonomous Data Analyst AI Agent

An AI-powered system that accepts CSV data, understands its structure, and answers business questions by generating and executing Python code.

## What it does
- Accepts CSV file input
- Understands data schema automatically
- Answers business questions in natural language
- Generates Python code using an LLM to produce answers
- Returns computed results

## Tech Stack
- Python
- FastAPI
- Groq (LLM provider)
- Llama 3.1 8B (AI model)
- Pandas

## Project Phases
- V1 — LLM + FastAPI (current)
- V2 — Code Execution Layer
- V3 — RAG Integration
- V4 — Multi Agent Orchestration
- V5 — Deployment + Observability

## Setup

1. Clone the repository

2. Create a virtual environment and activate it

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
- `GET /` — Welcome message
- `GET /health` — Health check
- `POST /ask` — Ask a question about your CSV data