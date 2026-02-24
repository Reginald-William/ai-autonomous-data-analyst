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
V1 — In Progress

## Milestones

### V1 — LLM + FastAPI (Weeks 1-2)
- [x] Project structure setup
- [x] FastAPI server running
- [x] Health endpoint
- [x] LLM integration with Groq
- [x] /ask endpoint working
- [ ] Code execution layer

### V2 — Code Execution Layer (Weeks 3-5)
- [ ] Execute LLM generated Python code
- [ ] Capture output
- [ ] Error handling
- [ ] Retry logic
- [ ] Structured outputs
- [ ] Logging improvements

### V3 — RAG Integration (Weeks 6-8)
- [ ] Add embeddings
- [ ] Store schema and docs in vector DB
- [ ] Retrieval pipeline
- [ ] Chunking strategy

### V4 — Multi Agent Orchestration (Weeks 9-12)
- [ ] Planner agent
- [ ] SQL generator agent
- [ ] Python executor agent
- [ ] Chart generator agent

### V5 — Deployment + Observability
- [ ] Docker
- [ ] AWS/GCP deployment
- [ ] Monitoring
- [ ] Logging pipeline

## Tech Stack
- Python
- FastAPI
- Groq (LLM provider)
- Llama 3.1 8B
- Pandas
- FAISS (coming in V3)
- PostgreSQL (coming in V4)
- Docker (coming in V5)

## Architecture

### V1 Architecture
User → FastAPI → LLM Service → Groq API → Generated Code → Response