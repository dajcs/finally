# Market Data Backend — Code Review

**Date:** 2026-03-19
**Scope:** `backend/app/market/` (8 source files, ~350 LOC) and `backend/tests/market/` (6 test files, 73 tests)
**Reviewer:** Claude Sonnet 4.6

---

## 1. Test & Lint Results

| Check | Result |
|-------|--------|
| Tests | **73 passed, 0 failed** |
| Ruff lint | **0 warnings** |
| Overall coverage | **91%** |

**Per-module coverage:**

| Module | Coverage | Uncovered lines |
|--------|----------|-----------------|
| `__init__.py` | 100% | — |
| `models.py` | 100% | — |
| `cache.py` | 100% | — |
| `interface.py` | 100% | — |
| `seed_prices.py` | 100% | — |
| `factory.py` | 100% | — |
| `simulator.py` | 98% | L149 (duplicate-add guard), L268–269 (exception log path) |
| `massive_client.py` | 94% | L85–87 (`_poll_loop` body), L125 (`_fetch_snapshots` return) |
| `stream.py` | **33%** | L26–48 (route handler), L62–87 (`_generate_events` body) |

The low coverage on `stream.py` is expected — testing an SSE generator requires a running ASGI server. This is the single largest gap in the test suite.

---

## 2. Prior Review

A previous code review (archived at `planning/archive/MARKET_DATA_REVIEW.md`, dated 2026-02-10) identified 7 issues. All 7 have been resolved in the current code:

| Prior issue | Status |
|-------------|--------|
| Missing `[tool.hatch.build.targets.wheel]` in pyproject.toml | Fixed |
| Lazy imports of `massive` broke test patches | Fixed — imports now at module level |
| `_generate_events` annotated `-> None` instead of `-> AsyncGenerator[str, None]` | Fixed |
| `SimulatorDataSource.get_tickers()` accessed private `_sim._tickers` | Fixed — `GBMSimulator.get_tickers()` added |
| Duplicate `DEFAULT_CORR` constant shadowed by `CROSS_GROUP_CORR` | Fixed — `DEFAULT_CORR` removed |
| Unused imports in test files caused ruff warnings | Fixed |
| Massive test mocks failed when `massive` package was absent | Fixed — now passes with package installed |

---

## 3. Architecture Assessment

The design is clean and correct. The strategy pattern is well-applied: `SimulatorDataSource` and `MassiveDataSource` both implement `MarketDataSource` and write to `PriceCache` independently of each other, while all downstream consumers (SSE, portfolio, trading) read exclusively from the cache. Responsibilities are clearly separated across focused modules.

**Strengths:**
- GBM with Cholesky-correlated sector moves is mathematically rigorous and produces realistic-looking price action
- `PriceUpdate` as a frozen dataclass prevents accidental mutation; computed properties (`change`, `direction`) can never be stale
- All background tasks cancel cleanly and `stop()` is idempotent on both implementations
- Version-based change detection in the SSE loop avoids sending redundant payloads (important when Massive polls at 15s intervals)
- Thread-safe cache uses `threading.Lock` correctly — the Massive client calls `asyncio.to_thread()`, which uses a real OS thread, so `asyncio.Lock` would be insufficient

---

## 4. Issues Found

### 4.1 Falsy Timestamp Check — `cache.py:30` (Medium)

```python
ts = timestamp or time.time()
```

If `timestamp=0.0` is passed, this evaluates as falsy and silently falls back to the current time instead of using the provided timestamp. The correct guard is:

```python
ts = timestamp if timestamp is not None else time.time()
```

**In practice:** The Massive API provides timestamps in Unix milliseconds (around 1.7 trillion ms, which divides to ~1.7 billion seconds). A zero timestamp cannot come from the API, and the simulator never passes a timestamp at all. This is a latent bug that won't trigger in normal operation, but could bite future callers who pass `0.0` to explicitly set an epoch timestamp or use it in tests.

---

### 4.2 Deprecated API in `massive_client.py:123–128` (Medium)

```python
def _fetch_snapshots(self) -> list:
    """Synchronous call to the Massive REST API. Runs in a thread."""
    return self._client.get_snapshot_all(
        market_type=SnapshotMarketType.STOCKS,
        tickers=self._tickers,
    )
```

`MASSIVE_API.md` explicitly documents this deprecation:

> The older `get_snapshot_all(market_type=SnapshotMarketType.STOCKS, tickers=[...])` method still works but is deprecated. Prefer `list_universal_snapshots(type="stocks", ticker_any_of=[...])`.

The preferred replacement, with the necessary `list()` call to exhaust the paginated iterator:

```python
def _fetch_snapshots(self) -> list:
    return list(self._client.list_universal_snapshots(
        type="stocks",
        ticker_any_of=self._tickers,
    ))
```

Note: `list_universal_snapshots` returns a lazy iterator (it paginates), so `list()` is required to force evaluation inside the thread. The current `get_snapshot_all` returns a concrete list, so no wrapping is needed there. When switching to `list_universal_snapshots`, the `list()` call is essential — omitting it would cause the iteration (and HTTP I/O) to happen on the async event loop thread after `asyncio.to_thread` returns, blocking it.

---

### 4.3 `version` Property Reads Without Lock — `cache.py:64–67` (Low)

```python
@property
def version(self) -> int:
    return self._version
```

All writes to `_version` are protected by `self._lock`, but this read is not. On CPython (the GIL guarantees atomic reads of Python integers), this is safe in practice. However, Python 3.13 introduced an experimental free-threaded build (PEP 703) that removes the GIL. On that build, an unprotected concurrent read could observe a torn write.

The fix is trivial:

```python
@property
def version(self) -> int:
    with self._lock:
        return self._version
```

This project targets Python 3.12, so the risk is theoretical for now. Worth fixing proactively for correctness.

---

### 4.4 Module-Level Router Singleton — `stream.py:17–48` (Low)

```python
router = APIRouter(prefix="/api/stream", tags=["streaming"])

def create_stream_router(price_cache: PriceCache) -> APIRouter:
    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        ...
    return router
```

`router` is a module-level singleton. `create_stream_router()` is named as a factory, implying it creates a new router each call, but it mutates and returns the shared singleton. Calling it twice (e.g., across tests) would register `/prices` twice on the same router. FastAPI silently allows duplicate routes but only the first registration wins.

In production this is harmless (called once in app startup). In tests it is a latent issue if any test ever calls `create_stream_router()`. The fix is to move router creation inside the factory:

```python
def create_stream_router(price_cache: PriceCache) -> APIRouter:
    router = APIRouter(prefix="/api/stream", tags=["streaming"])
    @router.get("/prices")
    ...
    return router
```

---

## 5. Test Coverage Gaps

### 5.1 No SSE Endpoint Tests — `stream.py` at 33%

`_generate_events` and the `stream_prices` route handler are entirely untested. SSE testing requires an ASGI test client; `httpx.AsyncClient` with `app` supports streaming responses:

```python
async def test_sse_emits_events():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("GET", "/api/stream/prices") as r:
            lines = []
            async for line in r.aiter_lines():
                if line.startswith("data:"):
                    lines.append(json.loads(line[5:]))
                    break
    assert len(lines) == 1
    assert "AAPL" in lines[0]
```

Even a basic test that verifies the endpoint returns `200` with `text/event-stream` and at least one event would add meaningful confidence.

### 5.2 No Full 10-Ticker Cholesky Test

The Cholesky decomposition is only tested with 1–2 tickers. A test with all 10 default tickers (the production configuration) would verify the full correlation matrix is positive-definite and the decomposition succeeds:

```python
def test_cholesky_with_all_default_tickers():
    from app.market.seed_prices import SEED_PRICES
    sim = GBMSimulator(tickers=list(SEED_PRICES.keys()))
    assert sim._cholesky is not None
    assert sim._cholesky.shape == (10, 10)
    result = sim.step()
    assert len(result) == 10
```

### 5.3 No Concurrent Write Test for PriceCache

The thread-safety claims of `PriceCache` are untested. A test that fires concurrent writes from multiple threads and verifies the version counter increments correctly would add empirical confidence to the lock implementation.

---

## 6. Minor Observations

**`math.sqrt(self._dt)` in `step()` hot path (`simulator.py:100`)**
`self._dt` is set once in `__init__` and never changes. `math.sqrt(self._dt)` could be precomputed in `__init__` as `self._sqrt_dt`. With 2 ticks/second, the saving is trivial, but it's a free micro-optimization for the code that runs most frequently.

**`massive_client.py` docstring references old endpoint (`_poll_once`, L90)**
The docstring says "Polls GET /v2/snapshot/locale/us/markets/stocks/tickers" but the actual call uses `get_snapshot_all`. This should be updated alongside the API migration in issue 4.2.

**`SimulatorDataSource.add_ticker` logs at INFO but `remove_ticker` also logs at INFO (`simulator.py:249, 255`)**
Consistent and fine. `MassiveDataSource.add_ticker` logs at INFO as well. No issue.

**`_add_ticker_internal` duplicate-add guard at `simulator.py:148`**
```python
def _add_ticker_internal(self, ticker: str) -> None:
    if ticker in self._prices:  # L148 — never reached; public add_ticker checks first
        return
```
This guard is unreachable because all callers (`add_ticker` and `__init__` via the batch loop) check before calling. It's defensive code that adds no runtime value. The 98% coverage reflects this uncovered branch. Not a bug — just dead code.

---

## 7. Verdict

The market data subsystem is well-implemented and production-ready for this project. All prior review issues are resolved, tests are comprehensive and passing, and the code is clean.

**Should fix:**
1. `timestamp or time.time()` → `timestamp if timestamp is not None else time.time()` in `cache.py:30`
2. Replace deprecated `get_snapshot_all` with `list_universal_snapshots` in `massive_client.py:125` — remembering the `list()` wrapper

**Worth fixing:**
3. `version` property reads without lock in `cache.py:66`
4. Move router instantiation inside `create_stream_router()` in `stream.py`

**Nice to have:**
5. At least one SSE integration test
6. Full 10-ticker Cholesky test
7. Concurrent write test for `PriceCache`
