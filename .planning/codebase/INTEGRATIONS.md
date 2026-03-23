# External Integrations

**Analysis Date:** 2026-03-23

## APIs & External Services

**LLM / AI Assistant:**
- **OpenRouter** - Unified LLM API gateway
  - Model: `openrouter/openai/gpt-oss-120b` (Cerebras inference provider)
  - SDK/Client: LiteLLM (`litellm` package)
  - Auth: `OPENROUTER_API_KEY` environment variable
  - Implementation: `app/llm/client.py` → async call via `acompletion()`
  - Structured Output: Pydantic `LLMResponse` model for JSON validation
  - Response Schema: `message` (string), `trades[]`, `watchlist_changes[]`
  - File: `backend/app/llm/client.py`

**Market Data:**
- **Massive (Polygon.io)** - Optional real-time stock market data API
  - API Type: REST polling (not WebSocket)
  - SDK/Client: `massive` package (v2.2.0)
  - Auth: `MASSIVE_API_KEY` environment variable
  - Rate Limits: Free tier 5 req/min → 15s poll interval; paid tiers faster
  - Endpoint: `GET /v2/snapshot/locale/us/markets/stocks/tickers`
  - Data: Last trade price and timestamp for equity snapshots
  - Activation: Only used if `MASSIVE_API_KEY` is set and non-empty
  - Implementation: `app/market/massive_client.py` → `MassiveDataSource` class
  - Fallback: Built-in simulator used if key is absent (no external dependency)

## Data Storage

**Databases:**
- **SQLite 3**
  - Connection: `aiosqlite` async client
  - File location: `/app/db/finally.db` (Docker volume mount)
  - Initialization: Lazy schema creation on first request (`app/db/connection.py`)
  - Pragma flags: WAL mode (journal_mode=WAL), foreign keys enabled
  - Tables:
    - `users_profile` - User account state (cash balance)
    - `watchlist` - Tracked tickers
    - `positions` - Current holdings
    - `trades` - Trade history log (append-only)
    - `portfolio_snapshots` - Portfolio value time series (recorded every 30s)
    - `chat_messages` - LLM conversation history with executed actions

**File Storage:**
- **Local filesystem only** - Frontend static files served from `backend/static/` directory

**Caching:**
- **In-memory PriceCache** - Thread-safe price store (no external service)
  - Location: `app/market/cache.py`
  - Holds: Latest price, previous price, timestamp per ticker
  - Used by: SSE stream, portfolio calculations, LLM context
  - Versioning: Monotonic counter for change detection

## Authentication & Identity

**Auth Provider:**
- **None / Single-user hardcoded** - No authentication required
  - Implementation: All operations use `user_id="default"` hardcoded
  - Design: Simulated environment, course demonstration (no multi-user)
  - Schema ready: `user_id` column in all tables enables future multi-user migration

## Monitoring & Observability

**Error Tracking:**
- **None** - Errors logged to stdout/stderr only

**Logs:**
- **Python logging module** - Backend logs to console (file location determined by container runtime)
- **Console output** - Frontend errors logged to browser console
- Log level: INFO by default; exceptions include full tracebacks

**Health Check:**
- `GET /api/health` endpoint returns `{"status": "ok"}`

## CI/CD & Deployment

**Hosting:**
- **Docker container** - Standalone image, self-contained
- **Port:** 8000 (HTTP only, no SSL termination in container)
- **Runtime:** Uvicorn ASGI server (`uv run uvicorn app.main:app`)

**CI Pipeline:**
- **None configured** - Project structure ready for GitHub Actions, Render, AWS App Runner but not yet integrated

**Deployment Platforms (Ready):**
- Docker-based: AWS App Runner, Render, DigitalOcean App Platform, Heroku
- Requirements: Container registry push capability, environment variable injection

## Environment Configuration

**Required env vars:**
- `OPENROUTER_API_KEY` - Must be set for LLM chat to work (fatal if missing on first `/api/chat` call)

**Optional env vars:**
- `MASSIVE_API_KEY` - If empty/unset, simulator provides market data instead
- `LLM_MOCK=true` - If set to "true" (case-insensitive string), use deterministic mock responses (for testing/development)
- `FINALLY_DB_PATH` - Override SQLite file location (defaults to `db/finally.db`)

**Secrets location:**
- `.env` file at project root (gitignored, not committed)
- `.env.example` serves as template documentation
- Docker: Passed via `--env-file .env` flag in container startup

## Webhooks & Callbacks

**Incoming:**
- None - Trading workstation is request-response only

**Outgoing:**
- None - No external callbacks or event forwarding

**Server-Sent Events (SSE):**
- **Endpoint:** `GET /api/stream/prices`
- **Format:** Server-Sent Events (MIME: `text/event-stream`)
- **Client:** Native browser `EventSource` API
- **Data:** Price updates for all tickers in user's watchlist
- **Cadence:** ~500ms per push (configurable in `app/market/stream.py`)
- **Direction:** Server→Client (one-way push, no client→server messages)
- **Resilience:** Browser EventSource handles reconnection automatically

## API Endpoints

**Market Data:**
- `GET /api/stream/prices` - SSE price updates (long-lived connection)

**Portfolio Operations:**
- `GET /api/portfolio` - Current positions, cash, total value, P&L
- `POST /api/portfolio/trade` - Execute market order (buy/sell)
- `GET /api/portfolio/history` - Portfolio snapshots for P&L chart

**Watchlist Management:**
- `GET /api/watchlist` - Current watchlist with live prices
- `POST /api/watchlist` - Add ticker
- `DELETE /api/watchlist/{ticker}` - Remove ticker

**Chat (LLM):**
- `POST /api/chat` - Send user message, receive LLM response + auto-executed trades/watchlist changes
  - Request: `{"message": "user query"}`
  - Response: `{"message": "...", "trades_executed": [...], "watchlist_changes": [...], "errors": [...]}`

**System:**
- `GET /api/health` - Health check (for Docker/load balancer)

**Static Files:**
- `GET /`, `GET /index.html`, `GET /**/*.js`, `GET /**/*.css` - Frontend served from `/static/` mount

## LLM Integration Details

**Flow:**
1. User sends message to `POST /api/chat`
2. Backend loads portfolio context (positions, cash, watchlist with live prices)
3. Loads recent chat history from `chat_messages` table
4. Constructs prompt: system message + context + conversation history + user message
5. Calls OpenRouter via LiteLLM with structured output format
6. Parses JSON response into `LLMResponse` Pydantic model
7. Auto-executes trades and watchlist changes (no confirmation dialog)
8. Stores message + executed actions in `chat_messages` table
9. Returns complete response to frontend

**Structured Output Schema:**
```python
{
    "message": "Conversational response to user",
    "trades": [
        {"ticker": "AAPL", "side": "buy", "quantity": 10}
    ],
    "watchlist_changes": [
        {"ticker": "PYPL", "action": "add"}
    ]
}
```

**Mock Mode:**
- Enabled via `LLM_MOCK=true` environment variable
- File: `backend/app/llm/mock.py`
- Pattern matching for keywords: "buy", "sell", "watch", "portfolio", etc.
- Returns deterministic responses (useful for E2E tests and development)
- No API calls made in mock mode

**Error Handling:**
- If LLM returns malformed JSON: Backend catches parsing error, logs it, returns 200 with user-friendly message
- If trade validation fails (insufficient cash, no position): Error included in response for LLM to explain to user
- If OpenRouter API is unavailable: Exception caught, fallback message returned to user

## Third-Party Libraries by Purpose

| Library | Purpose | Used By |
|---------|---------|---------|
| `litellm` | LLM API abstraction | Backend chat endpoint |
| `massive` | Market data API client | Market data source (optional) |
| `aiosqlite` | Async database access | All DB operations |
| `numpy` | Numerical computation | Market simulator (GBM math) |
| `rich` | Terminal formatting | CLI tools, logging |
| `fastapi` | Web framework | Backend API routes |
| `uvicorn` | ASGI server | Backend runtime |
| `pydantic` | Data validation | LLM response schemas, API request/response validation |
| `next` | React framework | Frontend build/routing/static export |
| `recharts` | Chart library | Portfolio heatmap, P&L visualization |
| `lightweight-charts` | Financial charting | Ticker detail chart |
| `tailwindcss` | CSS framework | Frontend styling |

---

*Integration audit: 2026-03-23*
