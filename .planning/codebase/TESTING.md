# Testing Patterns

**Analysis Date:** 2026-03-23

## Test Framework

**Runner:**
- Backend: pytest 8.3.0+
- Frontend: Jest 30.2.0+
- Config: `backend/pyproject.toml` (pytest section), `frontend/jest.config.ts`

**Assertion Library:**
- Backend: pytest assertions (assert statement)
- Frontend: React Testing Library with `@testing-library/jest-dom` matchers

**Run Commands:**
```bash
# Backend
uv run --extra dev pytest -v              # Run all tests
uv run --extra dev pytest --cov=app       # With coverage report
uv run --extra dev ruff check app/ tests/ # Lint check

# Frontend
npm test                                  # Run all Jest tests
npm test -- --watch                       # Watch mode
npm test -- --coverage                    # Coverage report
```

## Test File Organization

**Location:**
- Backend: `backend/tests/` — mirrors `backend/app/` structure
  - `tests/api/` for API endpoint tests
  - `tests/db/` for database tests
  - `tests/llm/` for LLM service tests
  - `tests/market/` for market data tests
  - `tests/routes/` for route-specific tests
- Frontend: `frontend/__tests__/` — flat directory for utility/component tests

**Naming:**
- Backend: `test_*.py` (e.g., `test_portfolio.py`, `test_service.py`)
- Frontend: `*.test.ts` or `*.test.tsx` (e.g., `Header.test.tsx`, `format.test.ts`)

**Structure:**
```
backend/tests/
├── conftest.py                # Root pytest configuration
├── api/
│   ├── conftest.py           # API-specific fixtures (client, cache, app)
│   ├── test_portfolio.py
│   └── test_watchlist.py
├── db/
│   └── test_db.py
├── llm/
│   ├── test_service.py
│   └── test_models.py
└── market/
    └── test_simulator.py

frontend/__tests__/
├── Header.test.tsx
├── format.test.ts
└── PortfolioHeatmap.test.tsx
```

## Test Structure

**Suite Organization (Python):**
```python
"""Tests for portfolio endpoints."""

async def test_get_portfolio_initial_state(client):
    """Docstring describes test behavior."""
    resp = await client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cash"] == 10000.0

class TestBuildContext:
    """Logical grouping of related tests via class."""
    async def test_builds_context_with_defaults(self, test_db, price_cache):
        # Test implementation
        pass
```

**Suite Organization (TypeScript/React):**
```typescript
describe("Header", () => {
  it("renders portfolio value and cash balance", () => {
    render(<Header totalValue={12345.67} cashBalance={5000} status="connected" />);
    expect(screen.getByText("$12,345.67")).toBeInTheDocument();
    expect(screen.getByText("$5,000.00")).toBeInTheDocument();
  });
});
```

**Patterns:**
- Backend: Setup via fixtures (see Fixtures section), test body is function body
- Frontend: Render component, query via Testing Library, assert expectations
- Async handling: `pytest-asyncio` with `asyncio_mode = "auto"` (no manual async wrapping)

## Mocking

**Framework:**
- Backend: pytest fixtures for object injection; `FakeMarketSource` class for dependency stubbing
- Frontend: Jest mocks (no external mocking library needed)

**Patterns (Python):**
```python
# Fixture-based dependency injection
@pytest.fixture
def cache():
    return PriceCache()

@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

# Stub class for interface compliance
class FakeMarketSource:
    async def add_ticker(self, ticker: str):
        pass
    async def start(self, tickers: list[str]):
        pass
```

**Patterns (TypeScript):**
```typescript
// Component rendering with props (all data passed in)
render(<Header totalValue={12345.67} cashBalance={5000} status="connected" />);

// Query via Testing Library
const element = screen.getByText("FinAlly");
expect(element).toBeInTheDocument();
```

**What to Mock:**
- External API calls: Stub with fixture returning canned data
- Market data source: Use `FakeMarketSource` in app setup
- HTTP client: Use `httpx.AsyncClient` with `ASGITransport` for FastAPI testing
- Database: Use temporary SQLite file via `tempfile`, cleaned up after test

**What NOT to Mock:**
- Database schema/tables: Initialize real SQLite for integration tests
- Pydantic models: Instantiate real models; validation is part of contract
- Core business logic: Test actual implementation, not mocks
- Price cache: Use real `PriceCache` instance; it's thread-safe and simple

## Fixtures and Factories

**Test Data (Python):**
```python
@pytest.fixture
def price_cache():
    """Seeded cache with realistic prices."""
    cache = PriceCache()
    cache.update("AAPL", 190.50)
    cache.update("GOOGL", 175.25)
    # ... etc
    return cache

@pytest.fixture
async def test_db(tmp_path):
    """Isolated temporary database."""
    db_path = str(tmp_path / "test.db")
    set_db_path(db_path)
    await init_db()
    yield db_path
    set_db_path(str(tmp_path / "unused.db"))
```

**Location:**
- Backend: `tests/conftest.py` (root fixtures), `tests/api/conftest.py` (API-specific), nested `conftest.py` per test module as needed
- Frontend: Fixtures defined inline in test files or via Jest setup

## Coverage

**Requirements:** Not enforced; goal is realistic coverage of business logic and error paths

**View Coverage (Backend):**
```bash
uv run --extra dev pytest --cov=app --cov-report=html
# Opens coverage/index.html
```

**View Coverage (Frontend):**
```bash
npm test -- --coverage
# Displays summary in console
```

**Excluded from Coverage (Python):**
```python
# pyproject.toml [tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Test Types

**Unit Tests (Backend):**
- Scope: Single function or class
- Approach: Isolate via fixtures; test one code path at a time
- Example: `test_buy_shares()` in `test_portfolio.py` — tests trade execution logic with fixed cache data
- No database in pure unit tests; mock via fixtures

**Integration Tests (Backend):**
- Scope: Multiple modules interacting (e.g., API route + database + cache)
- Approach: Real SQLite database, real `PriceCache`, test full request flow
- Example: `test_get_portfolio_initial_state()` — tests API response with initialized database
- Location: `tests/api/` for route-level integration

**Component Tests (Frontend):**
- Scope: React component rendering and user interaction
- Approach: Render with props; query via Testing Library; verify DOM output
- Example: `Header.test.tsx` — tests that portfolio value and connection status display correctly
- No API mocking; tests focus on visual output

**E2E Tests (Frontend):**
- Framework: Not yet implemented (planned for `test/` directory with Playwright)
- Scope: Full application flow (watchlist → trade → portfolio update)

## Common Patterns

**Async Testing (Python):**
```python
async def test_buy_shares(client, cache):
    cache.update("AAPL", 100.0)
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    assert resp.status_code == 200
```
- Fixtures are automatically awaited if async
- `pytest-asyncio` with `asyncio_mode = "auto"` handles event loop

**Error Testing (Python):**
```python
async def test_buy_insufficient_cash(client, cache):
    cache.update("AAPL", 100.0)
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 200, "side": "buy"},
    )
    assert resp.status_code == 400
    assert "Insufficient cash" in resp.json()["detail"]
```
- Verify HTTP status code
- Parse response JSON and check error message

**Error Testing (TypeScript):**
```typescript
it("renders error message on failed trade", () => {
  // Component would catch error from API call
  // and display status message
  expect(screen.getByText(/Trade failed/)).toBeInTheDocument();
});
```
- Render component with error state props
- Verify error UI elements display

**Assertion Patterns:**
- Python: `assert expr` for simple checks, `assert X in Y` for containment
- TypeScript: `expect(X).toBeInTheDocument()`, `expect(X).toBe(Y)`, `expect(X).toMatch(/pattern/)`

## Mock LLM Mode

When `LLM_MOCK=true` (environment variable):
- Backend's `app/llm/mock.py` returns deterministic responses
- Used in E2E tests for reproducibility and speed
- Enables testing without OpenRouter API key

---

*Testing analysis: 2026-03-23*
