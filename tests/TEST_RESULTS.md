# Test Results

Manual test results for each version. All tests run against the live API (`POST /ask`) with the server running locally.

---

## V4.2 — Dynamic Model Routing

**Date:** 2026-06-25
**Branch:** `claude/v4.2-dynamic-model-routing`
**Goal:** Verify correct model is selected based on complexity, row count threshold works, and all routing scenarios pass.

| # | Question | File | Expected Complexity | Expected Model | Status | Notes |
|---|----------|------|--------------------:|---------------|--------|-------|
| 1 | How many rows are in the data? | `sample_data.csv` | low | `llama-3.1-8b-instant` | ✅ Pass | |
| 2 | What is the total revenue? | `sample_data.csv` | low | `llama-3.1-8b-instant` | ✅ Pass | |
| 3 | What is the total revenue by region? | `sample_data.csv` | medium | `llama-3.3-70b-versatile` | ✅ Pass | |
| 4 | Show me a bar chart of revenue by product | `sample_data.csv` | medium | `llama-3.3-70b-versatile` | ✅ Pass | python + chart agents both fired |
| 5 | Show me all sales where revenue is greater than 5000 | `sample_data.csv` | low | `llama-3.1-8b-instant` | ✅ Pass | SQL agent routed correctly |
| 6 | What is the revenue trend over time and which region is growing fastest? | `sample_data.csv` | high → medium (12 rows < 500 threshold) | `llama-3.3-70b-versatile` | ✅ Pass | Complexity downgraded correctly |
| 7 | What is the revenue trend over time and which region is growing fastest? | `large_sales.csv` | high | `llama-4-scout-17b` | ✅ Pass | 1000 rows, full high complexity model used |
| 8 | What is the capital of France? | `sample_data.csv` | out_of_scope | — | ✅ Pass | No agent dispatched, clear message returned |
| 9 | How many rows are in the data? | `empty.csv` | — | — | ✅ Pass | 400 error returned before planner runs |

**Result: 9/9 passing**

### Key Decisions Made During Testing
- `qwen/qwen3-32b` was initially chosen for high complexity but rejected — rate limited on Groq free tier. Replaced with `meta-llama/llama-4-scout-17b-16e-instruct`.
- Single-call planner consistently returned `medium` for high complexity questions — root cause: model anchors on routing and treats complexity as afterthought. Fixed with two-call design.
- Pandas `freq='M'` deprecation error (pandas >= 2.2 requires `freq='ME'`) — fixed by adding instruction directly to python agent prompt.
- Row count threshold set at 500 — below this, high complexity is downgraded to medium since small datasets don't have enough signal for multi-step analysis.

---

## V4.1 — Refactoring & Testing

**Date:** 2026-06-14
**Branch:** `claude-code-v4.1-refactoring`
**Goal:** Verify all routing, edge cases, retry logic, and RAG after refactoring agents.

| # | Scenario | Status |
|---|----------|--------|
| 1 | Python agent routing — calculation question | ✅ Pass |
| 2 | SQL agent routing — filter/retrieval question | ✅ Pass |
| 3 | Chart agent routing — visualization question | ✅ Pass |
| 4 | Out-of-scope routing — unrelated question | ✅ Pass |
| 5 | Empty CSV guard — 400 error | ✅ Pass |

**Result: 5/5 passing**
