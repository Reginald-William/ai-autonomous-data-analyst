# Project Plan — Autonomous Data Analyst AI Agent

## Project Vision
Build an autonomous AI Data Analyst system that:
- Accepts structured data
- Understands schema
- Answers analytical questions
- Generates insights
- Produces visualizations
- Evolves into multi-agent architecture

## Current Status
V4 — In Progress

## Milestones

### V1 — LLM + FastAPI (Weeks 1-2)
- [x] Project structure setup
- [x] FastAPI server running
- [x] Health endpoint
- [x] LLM integration with Groq
- [x] /ask endpoint working
- [x] Code execution layer

### V2 — Code Execution Layer (Weeks 3-5)
- [x] Execute LLM generated Python code
- [x] Capture output
- [x] Error handling
- [x] Retry logic
- [x] Fix code function
- [x] Analyst service orchestration
- [x] Structured outputs with AnalysisResponse
- [x] Logging improvements
- [x] Temperature tuning
- [x] Global exception handler

### V3 — RAG Integration (Weeks 6-8)
- [x] Business context documents created
- [x] Data dictionary created
- [x] Sentence transformer embedding model integrated
- [x] Document loading and chunk splitting
- [x] FAISS index built on startup
- [x] Context retrieval with distance threshold
- [x] RAG context injected into LLM prompt

### V4 — Multi Agent Orchestration (Weeks 9-12)
- [ ] Planner agent
- [ ] SQL generator agent
- [ ] Python executor agent
- [ ] Chart generator agent

### Refactoring (after V4)
- [ ] Move ask_llm, fix_code into PythonAgent as methods
- [ ] Move execute_code, clean_code into PythonAgent as methods
- [ ] Keep llm_service.py for shared client and model only
- [ ] Delete execution_service.py

### V5 — Deployment + Observability
- [ ] Docker
- [ ] AWS/GCP deployment
- [ ] Monitoring
- [ ] Logging pipeline

## Tech Stack
- Python
- FastAPI
- Groq (LLM provider)
- Llama 3.1 8B (AI model)
- Pandas
- FAISS
- PostgreSQL (coming in V4)
- Docker (coming in V5)