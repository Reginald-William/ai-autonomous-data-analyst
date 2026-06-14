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
V4 — Completed | V4.1 Refactoring & Testing — In Progress (routing tests done, model upgraded to llama-3.3-70b-versatile)

## Milestones

### V1 — LLM + FastAPI (Weeks 1-2) ✅
- [x] Project structure setup
- [x] FastAPI server running
- [x] Health endpoint
- [x] LLM integration with Groq
- [x] /ask endpoint working
- [x] Code execution layer

### V2 — Code Execution Layer (Weeks 3-5) ✅
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

### V3 — RAG Integration (Weeks 6-8) ✅
- [x] Business context documents created
- [x] Data dictionary created
- [x] Sentence transformer embedding model integrated
- [x] Document loading and chunk splitting
- [x] FAISS index built on startup
- [x] Context retrieval with distance threshold
- [x] RAG context injected into LLM prompt

### V4 — Multi Agent Orchestration (Weeks 9-12) ✅
- [x] Planner agent with LLM based routing
- [x] Python agent for data analysis
- [x] SQL agent with SQLite integration
- [x] Chart agent with matplotlib
- [x] Agent orchestration in analyst service
- [x] Structured response with agent metadata
- [x] RAG assisted planner routing rules

### V4.1 — Refactoring & Testing
- [x] Move ask_llm and fix_code into PythonAgent
- [x] Move execute_code and clean_code into PythonAgent
- [x] Keep llm_service.py for shared client and model only
- [x] Delete execution_service.py
- [x] Fix attempts field to reflect actual agent attempts
- [ ] Test with different CSV files and schemas
- [ ] Test edge cases - empty CSV, missing values, special characters
- [x] Test all agent routing with various question types
- [ ] Test retry logic under failure conditions
- [ ] Test RAG with questions that have no relevant context
- [x] Add routing_rules.txt to docs for RAG

### V4.2 — Dynamic Model Routing
- [ ] Extend PlannerAgent to output complexity level (low/medium/high) alongside task_type
- [ ] Add ModelRouter that maps complexity to model (low → llama-3.1-8b-instant, medium → llama-3.3-70b-versatile, high → qwen/qwen3-32b)
- [ ] Pass selected model dynamically to each agent instead of using global MODEL_NAME constant
- [ ] Test cost vs quality tradeoff across all complexity levels

### V5 — Deployment + Observability
- [ ] Docker containerization
- [ ] AWS/GCP deployment
- [ ] Monitoring
- [ ] Logging pipeline
- [ ] Authentication
- [ ] File upload endpoint (replace file_path with multipart/form-data)
- [ ] Per-user rate limiting (protect Groq API quota)
- [ ] HTTPS

### V5.1 — Frontend + Monetization
- [ ] Simple frontend (Streamlit or Next.js) for non-technical users
- [ ] Usage tracking per user (enforce free/pro tiers)
- [ ] SaaS subscription tiers (free: limited questions/month, pro: $19-49/mo unlimited)
- [ ] API key access for developers (per 1000 questions billing)

### Future Considerations
- Multi-file and multi-database support (PostgreSQL, MySQL)
- Conversation memory (follow-up questions within a session)
- White-label offering for companies embedding in internal tools

## Tech Stack
- Python
- FastAPI
- Groq (LLM provider)
- Llama 3.3 70B Versatile (upgraded from 3.1 8B for better code generation accuracy)
- Pandas
- FAISS
- Sentence Transformers
- SQLite
- Matplotlib
- Tabulate
- Docker (coming in V5)
- PostgreSQL (coming in V5)