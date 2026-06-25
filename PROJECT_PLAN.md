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
V4 — Completed ✅ | V4.1 — Completed ✅ | V4.2 — Completed ✅ | V5 — Up Next

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
- [x] Test with different CSV files and schemas
- [x] Test edge cases - empty CSV, missing values, special characters
- [x] Test all agent routing with various question types
- [x] Test retry logic under failure conditions
- [x] Test RAG with questions that have no relevant context
- [x] Add routing_rules.txt to docs for RAG

### V4.2 — Dynamic Model Routing ✅
- [x] Two-call PlannerAgent: Call 1 routing (llama-3.3-70b-versatile), Call 2 complexity classifier (llama-3.1-8b-instant)
- [x] MODEL_ROUTING dict + get_model_for_complexity() in llm_service.py
- [x] All agents accept complexity param and return (result, attempts, model) tuple
- [x] High complexity capped at medium for datasets under 500 rows
- [x] Complexity rules added to docs/routing_rules.txt (RAG-retrieved)
- [x] Pandas freq='ME' fix in python agent prompt
- [x] Large test dataset added (tests/data/large_sales.csv, 1000 rows)
- [x] All 9 test scenarios passing — documented in tests/TEST_RESULTS.md

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
- Llama 3.1 8B Instant / Llama 3.3 70B Versatile / Llama 4 Scout 17B (dynamic model routing)
- Pandas
- FAISS
- Sentence Transformers
- SQLite
- Matplotlib
- Tabulate
- Docker (coming in V5)
- PostgreSQL (coming in V5)