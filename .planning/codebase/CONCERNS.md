# Codebase Concerns

**Analysis Date:** 2026-03-23

## Tech Debt

**Duplicate Route Modules (Critical):**
- Issue: Two parallel implementations of routes exist: `app/routes/` and `app/routers/`. Main.py imports from `app/routes` but newer, more robust versions exist in `app/routers/`.
- Files: `backend/app/routes/` vs `backend/app/routers/` (portfolio.py, chat.py, watchlist.py differ significantly)
- Impact: Code maintenance complexity, confusion about which version is canonical, divergent implementations can cause bugs if changes are made to one but not the other.
- Fix approach: Audit which directory main.py should import from, delete the unused one, ensure all imports in main.py point to the single source of truth.

**Duplicate Frontend Component Directories:**
- Issue: Both `frontend/app/components/` and `frontend/components/` exist with similar but different components.
- Files: `frontend/app/components/` vs `frontend/components/`
- Impact: Component duplication, tsconfig.json paths alias `@/components` to root, but `app/page.tsx` might be importing from wrong location. Risk of editing wrong version.
- Fix approach: Consolidate into single canonical location. Check tsconfig.json path resolution and ensure all imports reference only one directory.

**Database Layer Inconsistency:**
- Issue: Repository wrapper layer (`app/db/repository.py`) opens/closes connections for every operation, but newer routers expect CRUD functions to accept a database connection parameter (e.g., `get_db(request.app.state.db_path)`). Two incompatible APIs.
- Files: `backend/app/db/__init__.py` exports repository functions, but `backend/app/routers/chat.py` tries to call `get_db()` which is not exported.
- Impact: Routers can't compile if imported; routes vs routers inconsistency breaks routing.
- Fix approach: Either update all routers to use the repository pattern from __init__.py, or refactor repository to support pass-through connections. Choose single approach.

**Stale Chat History Function:**
- Issue: `app/db/__init__.py` exports `get_chat_history` but the actual function in repository.py is `get_chat_messages`. Routes import `get_chat_history` (wrong name).
- Files: `backend/app/db/__init__.py` line 34, `backend/app/routes/chat.py` line 8, `backend/app/db/repository.py` (renamed)
- Impact: Imports break; routes/chat.py will fail with ImportError.
- Fix approach: Rename exports or function consistently. Use `get_chat_messages` everywhere.

## Known Bugs

**Race Condition in Portfolio Snapshot Recording:**
- Symptoms: Portfolio snapshot value may be calculated from stale position data if market data updates and snapshot task fire simultaneously without transaction isolation.
- Files: `backend/app/main.py` lines 21-36 (_snapshot_loop), `backend/app/llm/service.py` lines 192-199
- Trigger: Frequent snapshot recording (every 30s) while trades execute; high concurrent price updates.
- Workaround: None. Snapshots may occasionally show out-of-sync values.
- Fix approach: Wrap snapshot recording in a database transaction that reads cash + positions atomically, or add mutex around portfolio state reads.

**Inconsistent Cash Balance Update in LLM Service:**
- Symptoms: In `app/llm/service.py` line 178, cash balance is updated by reading old cash, then updating with delta. But between lines 146 (read cash) and 178 (update), other market changes or trades could have modified cash.
- Files: `backend/app/llm/service.py` lines 146-178
- Trigger: Concurrent LLM trade execution and manual trades.
- Workaround: Sequence trades serially or accept small race windows.
- Fix approach: Use atomic update_cash_balance() or transaction-based approach that reads/writes cash as single operation.

**Type Mismatch in Frontend API Expectations:**
- Symptoms: Frontend `lib/api.ts` expects portfolio response with `cash` field (line 28), but backend routes/portfolio.py returns `cash_balance`. Data mapping may fail.
- Files: `frontend/lib/api.ts` line 28-29, `backend/app/routes/portfolio.py` (if used)
- Trigger: Calling getPortfolio() after backend refactored to use `cash_balance` naming.
- Workaround: Frontend currently parses `cash` → `cash_balance` but may be brittle.
- Fix approach: Standardize on single field name in backend response. Document API contract clearly.

## Security Considerations

**API Key Exposure Risk:**
- Risk: OpenRouter API key stored in `.env` file (standard practice but vulnerable to accidental commit or container leakage).
- Files: `.env` (not committed, but mounted into Docker container)
- Current mitigation: `.env` in .gitignore; Docker build uses --env-file flag.
- Recommendations: (1) Use Docker secrets or environment variables injected at runtime, never baked into image. (2) Add pre-commit hook to catch .env commits. (3) Rotate API key if ever exposed.

**No Input Validation on Ticker Symbols:**
- Risk: Frontend and routes accept any ticker string. Malformed tickers could cause LLM confusion, Massive API errors, or injection attacks if ticker used in SQL (though parameterized queries protect against this).
- Files: `backend/app/routes/watchlist.py` line 40, `backend/app/routes/portfolio.py` (trade endpoint)
- Current mitigation: Parameterized SQL queries prevent injection. Massive API will reject invalid tickers.
- Recommendations: Add regex validation for ticker format (1-5 uppercase letters + optional numbers). Reject before database write.

**No Authentication / Multi-User Safety Issues:**
- Risk: Hardcoded `user_id="default"` means all users share same portfolio. If this ever becomes multi-user, state corruption is possible.
- Files: `backend/app/db/schema.py` (DEFAULT_USER_ID="default"), all CRUD functions default to user_id="default"
- Current mitigation: Single-user design acceptable for simulation. Code is documented as single-user.
- Recommendations: For future multi-user: (1) Extract user_id from request context (JWT or session), never default. (2) Add test covering user isolation.

## Performance Bottlenecks

**N+1 Query Pattern in LLM Service:**
- Problem: `app/llm/service.py` lines 51-53 call get_cash_balance(), get_positions(), get_watchlist() separately. Each opens its own DB connection (repository pattern). For every chat message, 3 connections spawned.
- Files: `backend/app/llm/service.py` _build_context()
- Cause: Repository pattern opens connection per function call. No connection pooling or batching.
- Improvement path: Batch reads into single transaction. Or migrate to routers pattern that accepts pre-opened connection.

**Inefficient Snapshot Query:**
- Problem: `_snapshot_loop` in main.py re-fetches all positions every 30 seconds, even if they haven't changed. With 100+ users (future scale), this becomes O(users * positions * 30Hz).
- Files: `backend/app/main.py` lines 26-31
- Cause: No caching or dirty-flag tracking. Always recalculates total value from scratch.
- Improvement path: Cache last snapshot value and market prices, only recalculate if cache version changed. Skip snapshot if no price updates.

**Frontend Price Update Flooding:**
- Problem: `frontend/app/page.tsx` line 59-62 refreshes entire portfolio and watchlist every 5 seconds, even if only one ticker price changed. Also calls getPortfolio() which re-fetches all positions and cash, even though prices alone drive the UI updates.
- Files: `frontend/app/page.tsx` lines 56-64
- Cause: Polling at fixed interval regardless of SSE activity.
- Improvement path: Trigger portfolio refresh only on trade execution, not on price updates. Use SSE events to drive UI updates, not interval polling.

## Fragile Areas

**Market Data Source Initialization Order Dependency:**
- Files: `backend/app/main.py` lines 40-60
- Why fragile: If init_db() completes but get_watchlist() fails, market source won't start with correct tickers. If market source crashes after startup, no recovery attempted.
- Safe modification: Add error handling around market source startup. Add retry loop or health check endpoint that re-initializes if source is dead.
- Test coverage: No integration test for lifespan startup/shutdown failures.

**SSE Client Disconnect Detection Gap:**
- Files: `backend/app/market/stream.py` lines 68-71
- Why fragile: `request.is_disconnected()` checks only at loop iteration. If client disconnects between sleep intervals, it takes up to 0.5s to detect and clean up. Multiple disconnects could accumulate.
- Safe modification: Use asyncio.wait_for() with timeout, or event-based notification instead of polling.
- Test coverage: No test for SSE reconnection under network jitter.

**LLM Response Parsing Failure Handling:**
- Files: `backend/app/llm/service.py` lines 238-254
- Why fragile: If LLM returns non-JSON or malformed structured output, the except block swallows all exceptions and returns generic error. User doesn't know what went wrong. No logging of actual response content (security consideration, but makes debugging hard).
- Safe modification: Log the raw response body before catching. Differentiate between JSON parse errors and validation errors. Return slightly more specific error message if safe.
- Test coverage: No test for malformed LLM responses.

## Scaling Limits

**Single Database File Bottleneck:**
- Current capacity: SQLite handles ~100-1000 concurrent connections depending on query load.
- Limit: Breaks around 100+ active users with frequent snapshots.
- Scaling path: Migrate to PostgreSQL with connection pooling. Or implement read replicas for snapshot queries.

**Memory Price Cache Unbounded:**
- Current capacity: In-memory PriceCache stores all tickers ever added; no eviction.
- Limit: With 1000+ tickers, memory usage grows indefinitely.
- Scaling path: Implement LRU eviction (keep only recent N tickers). Or use Redis for distributed cache.

**SSE Broadcast to All Clients:**
- Current capacity: Every client receives all price updates every 500ms. With 100 clients, 200 events/sec on broadcast.
- Limit: Network bandwidth saturates around 1000 concurrent users.
- Scaling path: Implement client-side filtering (only stream prices for user's watchlist). Or use WebSocket with per-client subscriptions.

## Dependencies at Risk

**LiteLLM with OpenRouter Dependency:**
- Risk: LiteLLM is a thin wrapper around OpenRouter API. If OpenRouter goes down or changes API, chat breaks. No fallback LLM provider.
- Impact: Chat functionality completely unavailable if OpenRouter is down. Cost can spike if usage scales.
- Migration plan: Add fallback to local LLM (e.g., Ollama) or secondary provider (Claude, Grok). Implement circuit breaker to fall back gracefully.

**Massive API Optional but Undocumented:**
- Risk: MASSIVE_API_KEY environment variable is optional, but if set to invalid key, simulator silently uses fallback. Ambiguous behavior.
- Impact: User thinks they're using real data but are actually using simulator.
- Migration plan: Fail loudly if MASSIVE_API_KEY is set but invalid. Provide clear documentation of when simulator vs Massive is used.

## Missing Critical Features

**No Position Cost Basis Tracking on Partial Sells:**
- Problem: When user sells part of a position, avg_cost is preserved correctly. But if user bought at $100, it's now $150, and they sell half, the cost basis calculation assumes they sold the cheaper half first (FIFO). No way to specify cost basis method (FIFO/LIFO/average).
- Blocks: Accurate tax reporting, portfolio analysis tools.

**No Error Boundary for Component Crashes:**
- Problem: Frontend has no error boundary. If any component throws, entire app blank-screens.
- Blocks: Graceful error recovery, user can't trade even if one chart fails.

**No Watchlist Persistence Across Frontend Reloads:**
- Problem: Frontend state is in React useState. On page reload, watchlist and portfolio re-fetch from API, but selected ticker resets to first in list. UX is jarring.
- Blocks: Better UX, "remember my last selected ticker" feature.

## Test Coverage Gaps

**No Integration Tests for Database Transactions:**
- What's not tested: Whether snapshot + trade execution maintains data consistency under concurrent access.
- Files: `backend/tests/` (unit tests only, no integration tests)
- Risk: Race conditions in production that unit tests don't catch.
- Priority: High — affects financial data integrity.

**No E2E Tests for SSE Reconnection:**
- What's not tested: Does frontend reconnect correctly after network interruption? Are prices streamed consistently?
- Files: No E2E test coverage in `test/` directory.
- Risk: Silent data staleness — user sees cached prices, doesn't know they're stale.
- Priority: High — core feature.

**No Stress Test for Concurrent Trades + Snapshots:**
- What's not tested: Race condition between LLM auto-trade execution and 30-second snapshot recording.
- Files: `backend/tests/` (no load tests)
- Risk: Portfolio value misreporting under high load.
- Priority: Medium — only manifests at scale.

**Frontend Component Rendering Tests:**
- What's not tested: PnLChart, PortfolioHeatmap rendering with edge cases (empty portfolio, single position, high P&L).
- Files: `frontend/__tests__/` (minimal or missing)
- Risk: Visual bugs only discovered in production.
- Priority: Medium — nice-to-have, not critical functionality.

---

*Concerns audit: 2026-03-23*
