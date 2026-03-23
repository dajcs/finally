# Codebase Structure

**Analysis Date:** 2026-03-23

## Directory Layout

```
finally/
├── frontend/                      # Next.js TypeScript project (static export)
│   ├── app/
│   │   ├── page.tsx               # Root page, layout orchestration
│   │   ├── layout.tsx             # Next.js layout wrapper
│   │   └── ...                    # Future nested routes (currently static export)
│   ├── components/                # React UI components
│   │   ├── Header.tsx             # Portfolio total, cash, connection status
│   │   ├── Watchlist.tsx          # Ticker grid with prices and sparklines
│   │   ├── PriceChart.tsx         # Selected ticker price chart
│   │   ├── PortfolioHeatmap.tsx   # Treemap of positions by weight
│   │   ├── PositionsTable.tsx     # Table of holdings
│   │   ├── PnlChart.tsx           # Line chart of portfolio value over time
│   │   ├── TradeBar.tsx           # Buy/sell input, buttons
│   │   ├── ChatPanel.tsx          # AI chat interface
│   │   └── Sparkline.tsx          # Mini price sparkline component
│   ├── lib/
│   │   ├── api.ts                 # Fetch wrappers for all /api/* endpoints
│   │   ├── types.ts               # TypeScript interfaces (Portfolio, Trade, etc.)
│   │   ├── use-prices.ts          # Hook for SSE price stream connection
│   │   └── format.ts              # Formatting helpers (price, percent, currency)
│   ├── __tests__/                 # Jest unit tests
│   │   ├── Sparkline.test.tsx
│   │   ├── format.test.ts
│   │   └── ...
│   ├── package.json               # npm dependencies (Next, React, Tailwind, Jest)
│   ├── tsconfig.json              # TypeScript config
│   ├── next.config.ts             # Static export output mode
│   ├── jest.config.ts             # Jest test config
│   └── .eslintrc.json             # ESLint rules
│
├── backend/                       # FastAPI uv project
│   ├── app/
│   │   ├── main.py                # FastAPI app, lifespan, route registration
│   │   ├── routes/
│   │   │   ├── portfolio.py       # GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history
│   │   │   ├── watchlist.py       # GET /api/watchlist, POST /api/watchlist, DELETE /api/watchlist/{ticker}
│   │   │   └── chat.py            # POST /api/chat, GET /api/chat/history
│   │   ├── routers/               # Legacy duplicate routes (prefer routes/)
│   │   ├── db/
│   │   │   ├── __init__.py        # Re-exports of CRUD functions for convenience
│   │   │   ├── connection.py      # aiosqlite connection pooling, DB_PATH initialization
│   │   │   ├── schema.py          # SQL CREATE TABLE statements, DEFAULT_USER_ID
│   │   │   ├── crud.py            # CRUD operation functions (get_positions, insert_trade, etc.)
│   │   │   └── seed.py            # Seed data (10 default tickers, $10k initial cash)
│   │   ├── market/
│   │   │   ├── __init__.py        # Re-exports (PriceCache, PriceUpdate, create_market_data_source)
│   │   │   ├── interface.py       # MarketDataSource abstract class
│   │   │   ├── cache.py           # PriceCache implementation
│   │   │   ├── simulator.py       # SimulatorDataSource with GBM
│   │   │   ├── massive_client.py  # MassiveDataSource (Polygon.io API polling)
│   │   │   ├── factory.py         # create_market_data_source() factory
│   │   │   ├── stream.py          # create_stream_router() for SSE /api/stream/prices
│   │   │   ├── models.py          # PriceUpdate, Trade dataclasses
│   │   │   └── seed_prices.py     # SEED_PRICES, TICKER_PARAMS, volatility/drift per ticker
│   │   ├── llm/
│   │   │   ├── __init__.py        # Re-export of chat_with_llm
│   │   │   ├── service.py         # chat_with_llm() orchestrator, _build_context(), _execute_actions()
│   │   │   ├── client.py          # LiteLLM wrapper (if future refactor needed)
│   │   │   ├── models.py          # LlmResponse, Trade, WatchlistChange Pydantic models
│   │   │   ├── schemas.py         # Structured output schema for LLM (mirrors models)
│   │   │   ├── prompts.py         # System prompt, message builders (if extracted)
│   │   │   └── mock.py            # Deterministic mock responses for testing
│   ├── tests/
│   │   ├── conftest.py            # Shared pytest fixtures (async event loop, test DB)
│   │   ├── api/
│   │   │   ├── conftest.py        # Test client fixtures
│   │   │   ├── test_health.py
│   │   │   ├── test_portfolio.py
│   │   │   └── test_watchlist.py
│   │   ├── routes/
│   │   │   ├── conftest.py        # Route-specific fixtures
│   │   │   ├── test_portfolio.py
│   │   │   ├── test_watchlist.py
│   │   │   └── test_chat.py
│   │   ├── db/
│   │   │   └── test_db.py         # CRUD function tests
│   │   ├── llm/
│   │   │   ├── test_service.py
│   │   │   ├── test_models.py
│   │   │   ├── test_schemas.py
│   │   │   └── test_mock.py
│   │   └── market/
│   │       ├── test_simulator.py
│   │       ├── test_massive.py
│   │       ├── test_cache.py
│   │       └── test_stream.py
│   ├── market_data_demo.py        # Rich terminal dashboard demo (run with uv run)
│   ├── pyproject.toml             # uv project config, dependencies, pytest/ruff config
│   └── uv.lock                    # Lockfile
│
├── planning/                      # Project documentation
│   ├── PLAN.md                    # Core project specification (vision, arch overview, APIs)
│   ├── MARKET_DATA_SUMMARY.md     # Completed market data component overview
│   └── archive/                   # Historical docs
│
├── .planning/codebase/            # GSD codebase analysis docs
│   ├── ARCHITECTURE.md            # Pattern, layers, data flow
│   ├── STRUCTURE.md               # This file
│   ├── CONVENTIONS.md             # Code style, naming, patterns (when written)
│   └── TESTING.md                 # Test frameworks and patterns (when written)
│
├── test/                          # E2E tests (Playwright)
│   ├── docker-compose.test.yml    # Test infrastructure
│   └── e2e/
│       └── (Playwright test files, TBD)
│
├── scripts/
│   ├── start_mac.sh               # macOS/Linux Docker run wrapper
│   ├── stop_mac.sh                # macOS/Linux Docker stop/rm
│   ├── start_windows.ps1          # Windows PowerShell Docker run
│   └── stop_windows.ps1           # Windows PowerShell Docker stop/rm
│
├── db/                            # Runtime SQLite location
│   └── .gitkeep                   # Directory exists; finally.db is .gitignored
│
├── Dockerfile                     # Multi-stage: Node 20 (build frontend) → Python 3.12 (serve both)
├── docker-compose.yml             # Optional convenience wrapper (calls docker run with volume/env)
├── .env                           # Environment variables (gitignored)
├── .env.example                   # Environment template (committed)
├── .gitignore                     # Excludes node_modules, .venv, db/finally.db, .env, etc.
└── README.md                      # Quick start guide
```

## Directory Purposes

**`frontend/`:**
- Purpose: Single-Page Application built with Next.js (TypeScript, React 19)
- Contains: Components, hooks, API client, types, tests, build config
- Key files: `app/page.tsx` (root), `components/*` (UI), `lib/*` (shared logic)
- Build output: Next.js exports to `out/` directory (static HTML/JS/CSS)
- After Docker build: copied into backend `static/` directory for serving

**`backend/app/`:**
- Purpose: FastAPI application code
- Core modules: `main.py` (entry point), `routes/` (API endpoints), `db/` (persistence), `market/` (prices), `llm/` (chat)
- Entry point: `main.py` initializes FastAPI, registers routes, starts background tasks
- Serving: Mounts frontend static files at `/` after all `/api/*` routes registered

**`backend/app/routes/`:**
- Purpose: FastAPI router modules
- `portfolio.py`: Trade execution, position queries, balance, history
- `watchlist.py`: Add/remove tickers, get watchlist with prices
- `chat.py`: Chat endpoint, LLM orchestration

**`backend/app/db/`:**
- Purpose: SQLite database abstraction
- `connection.py`: Async connection pool, DB path resolution, lazy schema initialization
- `schema.py`: SQL CREATE TABLE statements, schema version
- `crud.py`: CRUD functions (one async function per operation, e.g., `get_positions()`, `insert_trade()`)
- `seed.py`: Default data (10 tickers, $10k cash)
- Lazy init: On first DB operation, if tables don't exist, creates schema and seeds data

**`backend/app/market/`:**
- Purpose: Live price abstraction and SSE streaming
- `interface.py`: `MarketDataSource` abstract class (contract for all price sources)
- `cache.py`: `PriceCache` in-memory store, thread-safe, version tracking
- `simulator.py`: GBM-based price generator (default)
- `massive_client.py`: REST API client to Massive/Polygon.io (if `MASSIVE_API_KEY` set)
- `factory.py`: `create_market_data_source()` instantiates correct implementation
- `stream.py`: SSE router at `/api/stream/prices`
- `models.py`: `PriceUpdate`, `Trade` dataclasses
- `seed_prices.py`: SEED_PRICES dict, per-ticker volatility/drift params, correlation groups

**`backend/app/llm/`:**
- Purpose: LLM integration for chat
- `service.py`: `chat_with_llm()` main function; context building, message construction, action execution
- `models.py`: Pydantic models for LLM structured output (`LlmResponse`, `Trade`, `WatchlistChange`)
- `mock.py`: Deterministic mock responses for testing (returns fixed message/trades for test repeatability)
- `client.py`: LiteLLM wrapper (currently inline in service; could be extracted)
- `prompts.py`: System prompt, message builders (currently inline in service.py)

**`backend/tests/`:**
- Purpose: Unit and integration tests
- Structure mirrors `app/` structure: `tests/routes/`, `tests/db/`, `tests/market/`, `tests/llm/`
- Fixtures in `conftest.py`: test event loop, test database (in-memory or temp file), test client
- Async tests via pytest-asyncio

**`planning/`:**
- Purpose: Project documentation for agents
- `PLAN.md`: Full specification (vision, architecture, endpoints, environment, database, LLM, testing)
- `MARKET_DATA_SUMMARY.md`: Completed market data component overview
- `archive/`: Historical iterations

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis (architecture, structure, conventions, testing, concerns)
- Created by `/gsd:map-codebase` orchestrator
- Consumed by `/gsd:plan-phase` and `/gsd:execute-phase` to drive implementation

**`test/`:**
- Purpose: E2E tests (Playwright)
- Infrastructure: `docker-compose.test.yml` (spins up app + Playwright container)
- Scenarios: Fresh start, add/remove tickers, buy/sell, portfolio visualizations, chat with mocked LLM

**`scripts/`:**
- Purpose: Developer convenience scripts for Docker operations
- `start_mac.sh`, `start_windows.ps1`: Build Docker image if needed, run container with volume/env mount
- `stop_mac.sh`, `stop_windows.ps1`: Stop and remove container (volume persists)

**`db/`:**
- Purpose: Runtime SQLite location
- Volume-mounted into container at `/app/db`
- SQLite file `finally.db` created here by backend on first run
- Persists across container restarts via named volume

## Key File Locations

**Entry Points:**

- `backend/app/main.py` — FastAPI app initialization, lifespan, route registration, static file serving
- `frontend/app/page.tsx` — Root Next.js page, main layout orchestration
- `backend/app/routes/portfolio.py` — Portfolio API routes
- `backend/app/routes/watchlist.py` — Watchlist API routes
- `backend/app/routes/chat.py` — Chat API route

**Configuration:**

- `backend/pyproject.toml` — Python dependencies, pytest/ruff config
- `frontend/package.json` — npm dependencies, build scripts
- `frontend/next.config.ts` — Static export config
- `.env.example` — Environment variable template
- `Dockerfile` — Multi-stage build (Node → Python)

**Core Logic:**

- `backend/app/market/simulator.py` — GBM price generation
- `backend/app/market/cache.py` — In-memory price cache
- `backend/app/llm/service.py` — LLM chat orchestration and action execution
- `backend/app/db/crud.py` — All database operations
- `frontend/lib/use-prices.ts` — SSE price stream connection hook

**Testing:**

- `backend/tests/conftest.py` — Shared pytest fixtures
- `backend/tests/market/test_simulator.py` — Simulator tests
- `backend/tests/routes/test_portfolio.py` — Portfolio route tests
- `frontend/__tests__/Sparkline.test.tsx` — React component tests

## Naming Conventions

**Files:**

- Python modules: `snake_case.py` (e.g., `market_data_demo.py`, `simulator.py`)
- React components: `PascalCase.tsx` (e.g., `Header.tsx`, `TradeBar.tsx`)
- Tests: `test_*.py` (Python) or `*.test.tsx` (React)
- Config files: `lowercase.json`, `lowercase.toml`, `lowercase.ts` (e.g., `tsconfig.json`, `next.config.ts`)

**Functions:**

- Python: `snake_case()` for regular functions and async functions (e.g., `get_positions()`, `chat_with_llm()`)
- React hooks: `useCamelCase()` (e.g., `usePrices()`, `useCallback()`)
- Event handlers: `handle{Action}()` (e.g., `handleSend()`, `handleTrade()`)

**Variables & Constants:**

- Local variables: `camelCase` in both Python and TypeScript (e.g., `current_price`, `selectedTicker`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_HISTORY`, `SEED_PRICES`, `MODEL`)
- Database IDs: UUIDs, strings (e.g., `id`, `user_id`, `ticker`)

**Types:**

- TypeScript interfaces: `PascalCase` (e.g., `Portfolio`, `TradeRequest`, `PriceUpdate`)
- Pydantic models (Python): `PascalCase` (e.g., `LlmResponse`, `Trade`)
- Database dicts: Returned as plain dicts with `snake_case` keys matching SQL columns

## Where to Add New Code

**New Feature (e.g., Stop Orders):**
- Primary code: `backend/app/routes/portfolio.py` (new endpoint or extend existing trade endpoint logic)
- Database schema: `backend/app/db/schema.py` (new table if needed, e.g., `pending_orders`)
- CRUD: `backend/app/db/crud.py` (new functions like `insert_pending_order()`, `get_pending_orders()`)
- Tests: `backend/tests/routes/test_portfolio.py` (test new logic), `backend/tests/db/test_db.py` (test CRUD)
- Frontend: `frontend/components/TradeBar.tsx` or new component, `frontend/lib/api.ts` (new API call), `frontend/lib/types.ts` (new type)

**New Component (e.g., Risk Heatmap):**
- Implementation: `frontend/components/RiskHeatmap.tsx`
- Import in: `frontend/app/page.tsx` (add to layout)
- Types: Add interface to `frontend/lib/types.ts` if it needs new API response shape
- Tests: `frontend/__tests__/RiskHeatmap.test.tsx`
- API: If needs new data, add endpoint to backend routes, extend corresponding CRUD functions

**New Market Data Source (e.g., WebSocket stream):**
- Implementation: `backend/app/market/websocket_source.py`
- Interface: Already implements `MarketDataSource` from `backend/app/market/interface.py`
- Factory: Update `backend/app/market/factory.py` to conditionally instantiate new source
- Tests: `backend/tests/market/test_websocket.py`
- Documentation: Update `planning/PLAN.md` with new source type

**New LLM Feature (e.g., Portfolio Rebalance Suggestions):**
- Service logic: Update `backend/app/llm/service.py`, add new field to `LlmResponse` model
- Prompts: Update system prompt in `backend/app/llm/service.py`
- Execution: Add new executor function in `service.py` (similar to `_execute_actions()`)
- Tests: `backend/tests/llm/test_service.py` (test context building, action execution)
- Frontend: Update chat panel to display new action type (e.g., render rebalance suggestion)

**Utilities/Helpers:**
- Shared backend helpers: `backend/app/db/helpers.py` or similar (not yet created; use when needed)
- Shared frontend helpers: `frontend/lib/format.ts` (for formatting) or `frontend/lib/helpers.ts` (general utilities)

## Special Directories

**`backend/.venv/`:**
- Purpose: Python virtual environment (created by `uv sync`)
- Generated: Yes (by uv)
- Committed: No (.gitignored)
- Use: Activate with `source .venv/bin/activate` or use `uv run` to run scripts

**`frontend/node_modules/`:**
- Purpose: npm dependencies
- Generated: Yes (by `npm install` or `npm ci`)
- Committed: No (.gitignored)

**`frontend/.next/`:**
- Purpose: Next.js build cache and incremental output
- Generated: Yes (by `npm run build`)
- Committed: No (.gitignored)

**`frontend/out/`:**
- Purpose: Static export output (HTML, JS, CSS)
- Generated: Yes (by `npm run build`)
- Committed: No (.gitignored)
- After Docker build: Copied into backend's `static/` directory (which is not checked in)

**`db/`:**
- Purpose: SQLite database file location
- Generated: Yes (by backend on first run)
- Committed: No (finally.db .gitignored)
- Persistence: Docker named volume mounts this directory

---

*Structure analysis: 2026-03-23*
