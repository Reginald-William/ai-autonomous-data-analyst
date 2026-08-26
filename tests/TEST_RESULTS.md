# Test Results

**Historical record — superseded by the automated suite.** Everything below was run by hand
against a live server, version by version. The models these results were produced with
(`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `meta-llama/llama-4-scout-17b-16e-instruct`)
were later removed from the Groq API entirely, so none of these results are reproducible today
— see `PHASES.md` Phase 1a. The 78 automated tests added in Phase 1c (`pytest -v`) are the
current source of truth for what's verified to work; this file is kept as a record of what was
manually checked at each version, not as a live test report.

Manual test results for each version. All tests run against the live API (`POST /ask`) with the server running locally.

---

## V5 — File Upload & Session Management

**Date:** 2026-06-26
**Branch:** `claude/v5-file-upload`
**Goal:** Verify `/upload` endpoint, file validation, session-based follow-ups, artifact collision fixes, and backward compat.

| # | Scenario | Method | Expected | Status | Notes |
|---|----------|--------|----------|--------|-------|
| 1 | First upload, simple question | `POST /upload` + `file=@sample_data.csv` | 200, answer, `session_id` in response | ✅ Pass | `file_name` shows `sample_data.csv` not UUID |
| 2 | Follow-up question using `session_id` | `POST /upload` + `session_id`, no file | 200, same `session_id` returned | ✅ Pass | File reused from session, no re-upload needed |
| 3 | Chart question via upload | `POST /upload` + chart question | 200, `chart_path` has UUID filename | ✅ Pass | `data/charts/{uuid}.png` not `chart.png` |
| 4 | SQL routing via upload | Covered in Test 2 | `agents_used: ["sql"]` | ✅ Pass | |
| 5 | Non-CSV file upload | Upload `README.md` | 400: "Only CSV files are supported" | ✅ Pass | |
| 6 | Empty CSV upload | Upload `tests/data/empty.csv` | 400: "no data rows" | ✅ Pass | Caught by analyst_service empty guard |
| 7 | Corrupt binary with `.csv` extension | Upload PNG bytes as `.csv` | 400: "File is not a valid CSV" | ✅ Pass | |
| 8 | Invalid `session_id` | Send fake UUID as `session_id` | 404: "Session not found or expired" | ✅ Pass | |
| 9 | No file, no `session_id` | Question only | 400: "No file uploaded" | ✅ Pass | |
| 10 | Both `session_id` + file sent | Send both | Session takes priority, file ignored | ✅ Pass | |
| 11 | `/ask` backward compat | `POST /ask` JSON with `file_path` | 200, works as before | ✅ Pass | |
| 12 | `/ask` returns `session_id` | Same as Test 11 | `session_id` auto-generated in response | ✅ Pass | |
| 13 | Chart filename is UUID | Check `data/charts/` after Test 3 | `{uuid}.png` not `chart.png` | ✅ Pass | |
| 14 | DB filename has session prefix | Check `data/` after SQL routing | `{session_id}_sample_data.db` | ✅ Pass | Fixed mid-test: was doubling UUID as table name |
| 15 | Uploaded files persist during session | Check `data/uploads/` after requests | Files present while sessions active | ✅ Pass | |
| 16 | TTL cleanup deletes files after expiry | Set TTL=0, sleep=5s, upload file, wait 10s | File deleted from `data/uploads/` | ✅ Pass | Tested with temporary TTL override |
| 17 | Startup orphan sweep clears leftover files | Restart server, check logs + directories | All files in uploads + charts deleted on startup | ✅ Pass | Logs: `Startup cleanup: removed X orphaned file(s)` |

**Result: 17/17 passing**

### Key Decisions Made During Testing

- **DB filename doubling bug:** `database_service` was deriving the table name from the UUID-named upload path, producing `{uuid}_{uuid}.db`. Fixed by passing `original_filename` through the route → `analyse()` → `sql_agent` → `database_service`, so the table name comes from the real filename (`sample_data`).
- **`file_name` in response showed UUID:** Same root cause — `analyst_service` was extracting filename from the saved path. Fixed by accepting `original_filename` param and using it for display.
- **Table name sanitization added:** Hyphens in UUIDs are invalid SQLite identifiers. Added `.replace("-", "_")` in `database_service` as a safety measure for edge cases.

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
