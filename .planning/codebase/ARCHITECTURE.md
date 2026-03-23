# Architecture

**Analysis Date:** 2026-03-23

## Pattern Overview

**Overall:** Microservices-inspired single-container monolith with clear separation of concerns across frontend, backend, and data layers.

**Key Characteristics:**
- Single Docker container housing both FastAPI backend and static-exported Next.js frontend
- Async/await throughout Python backend; React hooks and EventSource on frontend
- Market data abstraction via pluggable `MarketDataSource` interface (simulator vs. real API)
- SSE streaming for one-way price push; REST APIs for request/response endpoints
- LLM integration via structured output with auto-execution of trades and watchlist changes
- SQLite for persistence; in-memory cache for live price state

## Layers

**Presentation (Frontend):**
- Purpose: Interactive trading UI rendered as static HTML/JS/CSS
- Location: `frontend/app/` and `frontend/components/`
- Contains: React components (watchlist, charts, trade bar, chat panel), hooks (`usePrices`), API client (`lib/api.ts`)
- Depends on: `/api/*` REST endpoints, `/api/stream/prices` SSE, types from `lib/types.ts`
- Used by: Browser (end user)

**API Gateway (FastAPI):**
- Purpose: Route HTTP requests, coordinate backend services, serve static frontend files
- Location: `backend/app/main.py`
- Contains: FastAPI app setup, lifespan hooks, route registration, static file mount
- Depends on: Router modules (`app/routes/`), market data source, database layer
- Used by: Frontend via HTTP, browser via SSE

**Market Data (In-Memory + Stream):**
- Purpose: Generate or fetch live prices, push updates to connected clients via SSE
- Location: `backend/app/market/`
- Contains: `PriceCache` (thread-safe store), `SimulatorDataSource` (GBM), `MassiveDataSource` (REST polling), `MarketDataSource` interface, SSE router
- Depends on: Database (watchlist), external APIs (Massive), asyncio for background tasks
- Used by: Portfolio calculations, chat context, SSE streaming, LLM service

**LLM Service:**
- Purpose: Process user chat messages, call OpenRouter/Cerebras, auto-execute trades/watchlist changes
- Location: `backend/app/llm/`
- Contains: `chat_with_llm()` service function, structured output models, mock mode, prompt builders
- Depends on: Market data (price cache, current prices), database (portfolio, chat history, positions), LiteLLM client
- Used by: Chat router (`app/routes/chat.py`)

**Database (SQLite + CRUD):**
- Purpose: Persist user state, positions, trades, watchlist, chat history, portfolio snapshots
- Location: `backend/app/db/`
- Contains: Schema definitions (`schema.py`), connection pooling (`connection.py`), CRUD operations (`crud.py`), initialization (`seed.py`)
- Depends on: aiosqlite for async SQLite access
- Used by: All backend services (portfolio, watchlist, chat, market data initialization)

**Portfolio Logic:**
- Purpose: Calculate P&L, track positions, execute trades, manage cash balance
- Location: `backend/app/routes/portfolio.py` (API layer), database CRUD
- Contains: Trade execution with validation (cash checks, share availability), position averaging, snapshot recording
- Depends on: Market data (current prices), database (positions, cash), balance updates
- Used by: Chat service (auto-execute trades), trade API endpoint, portfolio snapshots

## Data Flow

**Price Stream (Server → Client):**

1. Backend market data source (Simulator or Massive) generates prices on ~500ms interval
2. Prices written to in-memory `PriceCache` with `PriceUpdate` objects
3. SSE router reads cache, serializes all tickers as JSON, sends to connected clients
4. Frontend `usePrices` hook receives SSE event, parses JSON, updates state
5. Components re-render with new prices; flash animation triggered via CSS
6. Sparkline history accumulated on frontend (`historyRef` in hook, max 120 points per ticker)

**Trade Execution (Client → Server):**

1. User clicks buy/sell button with ticker and quantity
2. Frontend POST to `/api/portfolio/trade` with `{ticker, side, quantity}`
3. Backend validates: checks current price from cache, verifies cash (buy) or shares (sell)
4. On success: updates position (upsert with cost averaging), deducts/adds cash, records trade in database
5. Portfolio snapshot recorded immediately after trade
6. Response returned with new cash and portfolio value
7. Frontend calls `onTradeExecuted()` to refresh portfolio state and watchlist

**Chat with LLM (Request → Response → Auto-Execution):**

1. User sends message to chat panel
2. Frontend POST to `/api/chat` with `{message}`
3. Backend builds portfolio context (cash, positions with P&L, watchlist with live prices)
4. Loads conversation history (last 20 messages)
5. Constructs prompt with system message, context, history, user message
6. Calls LiteLLM → OpenRouter with structured output schema
7. LLM returns JSON matching `LlmResponse` schema (message, trades array, watchlist_changes array)
8. Backend executes each trade in the trades array (same validation as manual trades)
9. Backend executes each watchlist change (add/remove ticker)
10. Records all results (success/error per action) and stores assistant message with actions JSON
11. Returns complete response with message and action results to frontend
12. Frontend displays message and shows action confirmations inline
13. Frontend refreshes portfolio and watchlist on action execution

**Portfolio Snapshot Loop:**

1. Background task runs every 30 seconds
2. Fetches current cash from database
3. Fetches all positions
4. For each position: gets latest price from cache (or fallback to avg_cost)
5. Calculates total portfolio value = cash + sum(position market values)
6. Inserts snapshot into `portfolio_snapshots` table
7. Frontend fetches this history and renders P&L chart

**State Management:**

- **Backend state:** SQLite database (persistent), in-memory PriceCache (ephemeral, rebuilt on restart), FastAPI app state (price_cache, market_source)
- **Frontend state:** React hooks (prices, portfolio, watchlist), EventSource connection (auto-manages reconnection)
- **Shared context:** Price cache is the source of truth for live prices; all downstream calculations read from it

## Key Abstractions

**MarketDataSource Interface:**
- Purpose: Abstract different price sources (simulator vs. real API)
- Examples: `app/market/simulator.py`, `app/market/massive_client.py`
- Pattern: Factory pattern via `create_market_data_source()` in `app/market/factory.py` based on `MASSIVE_API_KEY` env var
- Lifecycle: `await source.start(tickers)` → add/remove tickers → `await source.stop()`
- Both implementations push updates to shared `PriceCache` on their own schedule

**PriceCache:**
- Purpose: Thread-safe, in-memory cache of latest prices and previous prices
- Key methods: `update(ticker, price)` → returns `PriceUpdate`, `get(ticker)`, `get_price(ticker)`, `get_all()`, `version` (for change detection)
- Populated by: Market data source background task
- Consumed by: SSE stream, portfolio calculations, LLM context, trade execution validation

**PriceUpdate:**
- Purpose: Immutable dataclass representing a single price tick
- Fields: `ticker`, `price`, `previous_price`, `timestamp`, plus computed `change`, `change_percent`, `direction`
- Method: `to_dict()` for JSON serialization to SSE clients

**LlmResponse:**
- Purpose: Structured output schema for LLM response
- Fields: `message` (str), `trades` (list of Trade), `watchlist_changes` (list of WatchlistChange)
- Validation: Pydantic model used by `completion()` with structured output and validated via `model_validate_json()`

**Trade/Position/Snapshot Models:**
- Purpose: Represent domain entities consistently across API, database, cache
- Frontend types in `lib/types.ts` mirror backend Pydantic models
- Database CRUD functions return dicts; frontend API layer transforms to TypeScript interfaces

## Entry Points

**FastAPI Application:**
- Location: `backend/app/main.py`
- Triggers: Docker container startup; uvicorn ASGI server
- Responsibilities: Initialize database, start market data source, start snapshot loop, register routers, mount static files

**Frontend Page Component:**
- Location: `frontend/app/page.tsx` (Next.js root route)
- Triggers: Browser request to `/` (served as static HTML after build)
- Responsibilities: Connect to SSE stream via `usePrices` hook, fetch portfolio/watchlist on interval (5s), render layout, coordinate child components

**Market Data Lifecycle:**
- Startup: `await source.start(tickers)` with initial watchlist tickers
- Dynamic: `await source.add_ticker()` / `remove_ticker()` called when watchlist changes
- Shutdown: `await source.stop()` in FastAPI shutdown lifespan hook

**API Endpoints (Entry Points for Frontend):**
- `GET /api/stream/prices` — SSE long-lived connection; initiated by `usePrices` hook on component mount
- `GET /api/portfolio` — Periodic fetch every 5s, triggered by main page `useEffect`
- `POST /api/portfolio/trade` — User clicks buy/sell in TradeBar component
- `GET /api/watchlist` — Periodic fetch every 5s, triggered by main page `useEffect`
- `POST /api/watchlist` — User clicks add button or LLM executes add
- `DELETE /api/watchlist/{ticker}` — User clicks remove or LLM executes remove
- `POST /api/chat` — ChatPanel sends user message
- `GET /api/health` — Docker health checks

## Error Handling

**Strategy:** Fail gracefully; return user-friendly errors; avoid 5xx responses for expected failures.

**Patterns:**

**Backend API Errors:**
- Validation failures (invalid trade params, insufficient cash/shares) → 400 HTTPException with detail message
- LLM call failures → Caught, logged, return 200 with error message in response body (not 500)
- Database errors → Logged, propagate as 500 (unexpected)
- Missing prices → 400 with message "No price available for {ticker}"

**Frontend API Errors:**
- HTTP error responses parsed from response body text and thrown as Error
- Chat errors caught and displayed as assistant message ("Failed to get response")
- Portfolio/watchlist fetch errors caught silently in `useEffect`, retry on next interval (no interruption)

**Price Cache Missing:**
- If price not in cache, fallback to position's `avg_cost` for P&L calculations
- If price not in cache for trade, reject with 400 error (user sees "no price available")

**SSE Connection Errors:**
- EventSource native auto-retry on error
- Frontend manual retry logic: reconnect after 2s on error
- Status indicator shows "disconnected" until reconnected

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module with app logger in each module
- Backend: INFO for lifecycle events (DB init, market source start), DEBUG for price updates, ERROR for exceptions
- Frontend: Browser console only; no structured logging

**Validation:**
- Backend: Pydantic models for request bodies, manual validation for business logic (cash/shares checks)
- Frontend: Type safety via TypeScript; no runtime validation
- LLM: Structured output validation via Pydantic `model_validate_json()`

**Authentication:**
- Single-user hardcoded: all operations use `user_id="default"`
- No login, no secrets per user, no isolation
- Future: multi-user would add user context to all CRUD functions, API auth middleware

**Async/Await:**
- Backend: All DB operations async via aiosqlite; all routes async
- Market source background task: async loop with `asyncio.sleep()`, cancellation-safe
- Snapshot loop: async loop with `asyncio.sleep()`, graceful shutdown on `CancelledError`
- Frontend: async/await only for API calls; hooks and rendering synchronous

---

*Architecture analysis: 2026-03-23*
