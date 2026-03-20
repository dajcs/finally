# Market Data Backend — Implementation Design

Complete, implementation-ready design for `backend/app/market/`. This document reflects the **as-built** system — all code review fixes are incorporated.

---

## Table of Contents

1. [Architecture & File Structure](#1-architecture--file-structure)
2. [Data Model — `models.py`](#2-data-model)
3. [Price Cache — `cache.py`](#3-price-cache)
4. [Abstract Interface — `interface.py`](#4-abstract-interface)
5. [Seed Prices & Parameters — `seed_prices.py`](#5-seed-prices--parameters)
6. [GBM Simulator — `simulator.py`](#6-gbm-simulator)
7. [Massive API Client — `massive_client.py`](#7-massive-api-client)
8. [Factory — `factory.py`](#8-factory)
9. [SSE Streaming Endpoint — `stream.py`](#9-sse-streaming-endpoint)
10. [FastAPI Lifecycle Integration](#10-fastapi-lifecycle-integration)
11. [Watchlist Coordination](#11-watchlist-coordination)
12. [Testing Strategy](#12-testing-strategy)
13. [Error Handling & Edge Cases](#13-error-handling--edge-cases)
14. [Configuration Reference](#14-configuration-reference)

---

## 1. Architecture & File Structure

```
MarketDataSource (ABC)
├── SimulatorDataSource  →  GBM simulator (default, no API key needed)
└── MassiveDataSource    →  Polygon.io REST poller (when MASSIVE_API_KEY set)
        │
        ▼  writes PriceUpdate objects
   PriceCache (thread-safe, in-memory)
        │
        ├──→ SSE stream endpoint (/api/stream/prices)
        ├──→ Portfolio valuation
        └──→ Trade execution
```

```
backend/app/market/
├── __init__.py        # Re-exports: PriceUpdate, PriceCache, MarketDataSource,
│                      #             create_market_data_source, create_stream_router
├── models.py          # PriceUpdate frozen dataclass
├── interface.py       # MarketDataSource abstract base class
├── cache.py           # PriceCache (thread-safe)
├── seed_prices.py     # SEED_PRICES, TICKER_PARAMS, correlation constants
├── simulator.py       # GBMSimulator + SimulatorDataSource
├── massive_client.py  # MassiveDataSource
├── factory.py         # create_market_data_source()
└── stream.py          # FastAPI SSE router factory
```

**Key design principles:**
- **Strategy pattern** — both data sources implement the same ABC; downstream code is source-agnostic
- **PriceCache as single point of truth** — producers write, consumers read; no direct coupling
- **Push model** — data sources write to cache on their own schedule; SSE reads at 500ms cadence

---

## 2. Data Model

**`backend/app/market/models.py`**

`PriceUpdate` is the only data structure that leaves the market data layer.

```python
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Immutable snapshot of a single ticker's price at a point in time."""

    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)  # Unix seconds

    @property
    def change(self) -> float:
        """Absolute price change from previous update."""
        return round(self.price - self.previous_price, 4)

    @property
    def change_percent(self) -> float:
        """Percentage change from previous update."""
        if self.previous_price == 0:
            return 0.0
        return round((self.price - self.previous_price) / self.previous_price * 100, 4)

    @property
    def direction(self) -> str:
        """'up', 'down', or 'flat'."""
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "flat"

    def to_dict(self) -> dict:
        """Serialize for JSON / SSE transmission."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "timestamp": self.timestamp,
            "change": self.change,
            "change_percent": self.change_percent,
            "direction": self.direction,
        }
```

**Design decisions:**
- `frozen=True` + `slots=True` — immutable value object, safe to share across async tasks
- Computed properties derived from `price`/`previous_price` — can never be inconsistent
- `to_dict()` is the single serialization point for both SSE and REST responses

---

## 3. Price Cache

**`backend/app/market/cache.py`**

Central data hub. Data sources write; SSE and portfolio valuation read.

```python
from __future__ import annotations

import time
from threading import Lock

from .models import PriceUpdate


class PriceCache:
    """Thread-safe in-memory cache of the latest price per ticker.

    Writers: one MarketDataSource background task.
    Readers: SSE streaming endpoint, portfolio valuation, trade execution.
    """

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version: int = 0  # Bumped on every update

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Record a new price. First update: previous_price == price, direction == 'flat'."""
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price
            update = PriceUpdate(
                ticker=ticker,
                price=round(price, 2),
                previous_price=round(previous_price, 2),
                timestamp=ts,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        with self._lock:
            return self._prices.get(ticker)

    def get_price(self, ticker: str) -> float | None:
        update = self.get(ticker)
        return update.price if update else None

    def get_all(self) -> dict[str, PriceUpdate]:
        """Shallow copy — safe for the SSE loop to iterate."""
        with self._lock:
            return dict(self._prices)

    def remove(self, ticker: str) -> None:
        with self._lock:
            self._prices.pop(ticker, None)

    @property
    def version(self) -> int:
        """Monotonically increasing. Bumped on every update.
        SSE uses this for change detection — no event sent if version unchanged."""
        return self._version

    def __len__(self) -> int:
        with self._lock:
            return len(self._prices)

    def __contains__(self, ticker: str) -> bool:
        with self._lock:
            return ticker in self._prices
```

**Why `threading.Lock` and not `asyncio.Lock`:**
The Massive client runs synchronous code in `asyncio.to_thread()` (a real OS thread). `asyncio.Lock` only protects against concurrent coroutines on the event loop — it does not protect against threads. `threading.Lock` protects both.

**Why a version counter:**
The SSE loop runs every 500ms. With Massive polling every 15s, most SSE ticks would send unchanged data without the version check. The counter lets the loop skip sends when nothing changed.

---

## 4. Abstract Interface

**`backend/app/market/interface.py`**

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their own
    schedule. Downstream code never reads prices from the source directly.

    Lifecycle:
        source = create_market_data_source(cache)
        await source.start(["AAPL", "GOOGL", ...])
        await source.add_ticker("TSLA")
        await source.remove_ticker("GOOGL")
        await source.stop()
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates. Starts a background task.
        Must be called exactly once."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task. Safe to call multiple times."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set. No-op if already present."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker. Also removes it from the PriceCache."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of tracked tickers (synchronous)."""
```

`start/stop/add_ticker/remove_ticker` are async so implementations can do async I/O. `get_tickers` is sync — reads in-memory state only.

---

## 5. Seed Prices & Parameters

**`backend/app/market/seed_prices.py`**

Constants only — no logic. Shared by the simulator; no runtime dependency.

```python
"""Seed prices and per-ticker GBM parameters."""

SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT":  420.00,
    "AMZN":  185.00,
    "TSLA":  250.00,
    "NVDA":  800.00,
    "META":  500.00,
    "JPM":   195.00,
    "V":     280.00,
    "NFLX":  600.00,
}

# sigma: annualized volatility  |  mu: annualized drift
TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL":  {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT":  {"sigma": 0.20, "mu": 0.05},
    "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA":  {"sigma": 0.50, "mu": 0.03},  # High volatility
    "NVDA":  {"sigma": 0.40, "mu": 0.08},  # High vol, strong drift
    "META":  {"sigma": 0.30, "mu": 0.05},
    "JPM":   {"sigma": 0.18, "mu": 0.04},  # Low vol (bank)
    "V":     {"sigma": 0.17, "mu": 0.04},  # Low vol (payments)
    "NFLX":  {"sigma": 0.35, "mu": 0.05},
}

DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}

CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech":    {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

INTRA_TECH_CORR    = 0.6   # Tech stocks move together
INTRA_FINANCE_CORR = 0.5   # Finance stocks move together
CROSS_GROUP_CORR   = 0.3   # Between sectors, and for unknown tickers
TSLA_CORR          = 0.3   # TSLA does its own thing
```

Tickers not in `SEED_PRICES` (dynamically added) start at `random.uniform(50, 300)` with `DEFAULT_PARAMS`.

---

## 6. GBM Simulator

**`backend/app/market/simulator.py`**

Two classes in one file: `GBMSimulator` (pure math) and `SimulatorDataSource` (async wrapper).

### GBM Math

```
S(t+dt) = S(t) × exp((μ - σ²/2) × dt + σ × √dt × Z)

TRADING_SECONDS_PER_YEAR = 252 × 6.5 × 3600 = 5,896,800
dt = 0.5 / 5,896,800 ≈ 8.48e-8   (500ms as fraction of a trading year)
```

The tiny `dt` produces sub-cent moves per tick that accumulate naturally into realistic daily ranges.

### GBMSimulator

```python
import math
import random
import numpy as np
from .cache import PriceCache
from .interface import MarketDataSource
from .seed_prices import (
    CORRELATION_GROUPS, CROSS_GROUP_CORR, DEFAULT_PARAMS,
    INTRA_FINANCE_CORR, INTRA_TECH_CORR, SEED_PRICES,
    TICKER_PARAMS, TSLA_CORR,
)


class GBMSimulator:
    """Geometric Brownian Motion simulator with correlated sector moves."""

    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR   # ~8.48e-8

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability
        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None

        for ticker in tickers:
            self._add_ticker_internal(ticker)   # Batch add without rebuilding
        self._rebuild_cholesky()                # One rebuild at the end

    def step(self) -> dict[str, float]:
        """Advance all tickers one time step. Returns {ticker: new_price}."""
        n = len(self._tickers)
        if n == 0:
            return {}

        z_ind = np.random.standard_normal(n)
        z = self._cholesky @ z_ind if self._cholesky is not None else z_ind

        result: dict[str, float] = {}
        for i, ticker in enumerate(self._tickers):
            mu = self._params[ticker]["mu"]
            sigma = self._params[ticker]["sigma"]
            drift     = (mu - 0.5 * sigma ** 2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            # ~0.1% chance per tick per ticker of a 2-5% shock event
            # With 10 tickers at 2 ticks/sec → ~1 event every 50 seconds
            if random.random() < self._event_prob:
                shock = random.uniform(0.02, 0.05) * random.choice([-1, 1])
                self._prices[ticker] *= 1 + shock

            result[ticker] = round(self._prices[ticker], 2)

        return result

    def add_ticker(self, ticker: str) -> None:
        if ticker in self._prices:
            return
        self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    def _add_ticker_internal(self, ticker: str) -> None:
        self._tickers.append(ticker)
        self._prices[ticker] = SEED_PRICES.get(ticker, random.uniform(50.0, 300.0))
        self._params[ticker] = TICKER_PARAMS.get(ticker, dict(DEFAULT_PARAMS))

    def _rebuild_cholesky(self) -> None:
        """Rebuild Cholesky decomposition. O(n²), n < 50 in practice."""
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return
        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                rho = self._pairwise_correlation(self._tickers[i], self._tickers[j])
                corr[i, j] = corr[j, i] = rho
        self._cholesky = np.linalg.cholesky(corr)

    @staticmethod
    def _pairwise_correlation(t1: str, t2: str) -> float:
        if t1 == "TSLA" or t2 == "TSLA":
            return TSLA_CORR
        tech = CORRELATION_GROUPS["tech"]
        finance = CORRELATION_GROUPS["finance"]
        if t1 in tech and t2 in tech:
            return INTRA_TECH_CORR
        if t1 in finance and t2 in finance:
            return INTRA_FINANCE_CORR
        return CROSS_GROUP_CORR
```

**Correlated moves — Cholesky decomposition:**
1. Build n×n correlation matrix `C` from sector rules
2. Compute `L = cholesky(C)` so `L @ L.T = C`
3. Each tick: draw `n` independent normals `z_ind`
4. Apply: `z = L @ z_ind` — now `z[i]` has the desired sector correlations

### SimulatorDataSource

```python
import asyncio
import logging

logger = logging.getLogger(__name__)


class SimulatorDataSource(MarketDataSource):
    """MarketDataSource backed by GBMSimulator. Runs a 500ms asyncio loop."""

    def __init__(
        self,
        price_cache: PriceCache,
        update_interval: float = 0.5,
        event_probability: float = 0.001,
    ) -> None:
        self._cache = price_cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(tickers=tickers, event_probability=self._event_prob)
        # Seed cache immediately — SSE has data before first loop tick
        for ticker in tickers:
            if (price := self._sim.get_price(ticker)) is not None:
                self._cache.update(ticker=ticker, price=price)
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")
        logger.info("Simulator started with %d tickers", len(tickers))

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Simulator stopped")

    async def add_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.add_ticker(ticker)
            # Seed immediately — ticker has a price before the next loop tick
            if (price := self._sim.get_price(ticker)) is not None:
                self._cache.update(ticker=ticker, price=price)

    async def remove_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.get_tickers() if self._sim else []

    async def _run_loop(self) -> None:
        while True:
            try:
                if self._sim:
                    prices = self._sim.step()
                    for ticker, price in prices.items():
                        self._cache.update(ticker=ticker, price=price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```

**Key behaviors:**
- `step()` is synchronous pure NumPy — no `to_thread()` needed (< 0.1ms per step)
- Cache seeded in `start()` and `add_ticker()` so there is never a blank-screen delay
- Exception in `_run_loop` is caught per-tick — a bad step never kills the stream
- `stop()` cancels and awaits the task — clean shutdown during FastAPI lifespan teardown

---

## 7. Massive API Client

**`backend/app/market/massive_client.py`**

Polls the Massive (formerly Polygon.io) REST API on a configurable interval.

```python
from __future__ import annotations

import asyncio
import logging

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class MassiveDataSource(MarketDataSource):
    """MarketDataSource backed by the Massive (Polygon.io) REST API.

    One API call fetches all watched tickers. Rate limits:
      Free tier:  5 req/min → poll every 15s (default)
      Paid tiers: higher limits → poll every 2-5s
    """

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client = None

    async def start(self, tickers: list[str]) -> None:
        from massive import RESTClient

        self._client = RESTClient(api_key=self._api_key)
        self._tickers = list(tickers)
        await self._poll_once()  # Immediate first poll — cache has data right away
        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")
        logger.info("Massive poller started: %d tickers, %.1fs interval", len(tickers), self._interval)

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None
        logger.info("Massive poller stopped")

    async def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            # Takes effect on next poll cycle

    async def remove_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _poll_loop(self) -> None:
        """Sleep then poll, forever. First poll already happened in start()."""
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        if not self._tickers or not self._client:
            return
        try:
            # RESTClient is synchronous — run in thread to avoid blocking event loop
            snapshots = await asyncio.to_thread(self._fetch_snapshots)
            for snap in snapshots:
                try:
                    self._cache.update(
                        ticker=snap.ticker,
                        price=snap.last_trade.price,
                        timestamp=snap.last_trade.timestamp / 1000.0,  # ms → seconds
                    )
                except (AttributeError, TypeError) as e:
                    logger.warning("Skipping snapshot for %s: %s", getattr(snap, "ticker", "?"), e)
        except Exception as e:
            logger.error("Massive poll failed: %s", e)
            # Don't re-raise — loop retries on next interval; stale prices remain visible

    def _fetch_snapshots(self) -> list:
        """Synchronous Massive API call. Runs in a thread via asyncio.to_thread()."""
        return list(self._client.list_universal_snapshots(
            type="stocks",
            ticker_any_of=self._tickers,
        ))
```

**Key design decisions:**
- `asyncio.to_thread()` wraps the synchronous client — event loop never blocked
- Immediate first poll in `start()` — cache has real data before first SSE connect
- Poll errors logged and swallowed — stale prices remain visible rather than crashing
- `add_ticker` takes effect on the next poll (no special handling needed)

**Error handling:**

| Error | Behavior |
|-------|----------|
| 401 Unauthorized | Logged as error. Loop keeps retrying. |
| 429 Rate Limited | Logged as error. Retries after `poll_interval`. |
| Network timeout | Logged as error. Retries automatically. |
| Malformed snapshot | Individual ticker skipped. Others still processed. |

---

## 8. Factory

**`backend/app/market/factory.py`**

```python
from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Select simulator or Massive based on MASSIVE_API_KEY env var.

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        from .massive_client import MassiveDataSource
        logger.info("Market data source: Massive API (real data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        from .simulator import SimulatorDataSource
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
```

---

## 9. SSE Streaming Endpoint

**`backend/app/market/stream.py`**

```python
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stream", tags=["streaming"])


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Factory — injects PriceCache without globals."""

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        """SSE endpoint: streams all tracked ticker prices every ~500ms.

        Client connects with EventSource('/api/stream/prices') and receives:
            data: {"AAPL": {"ticker": "AAPL", "price": 190.50, ...}, ...}
        """
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering if proxied
            },
        )

    return router


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
) -> AsyncGenerator[str, None]:
    """Yield SSE events while the client is connected."""
    yield "retry: 1000\n\n"  # Browser reconnects after 1s if dropped

    last_version = -1
    client_ip = request.client.host if request.client else "unknown"
    logger.info("SSE client connected: %s", client_ip)

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected: %s", client_ip)
                break

            current_version = price_cache.version
            if current_version != last_version:
                last_version = current_version
                prices = price_cache.get_all()
                if prices:
                    data = {ticker: update.to_dict() for ticker, update in prices.items()}
                    yield f"data: {json.dumps(data)}\n\n"

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client_ip)
```

**Wire format — one SSE event:**
```
data: {"AAPL":{"ticker":"AAPL","price":190.50,"previous_price":190.42,
       "timestamp":1707580800.5,"change":0.08,"change_percent":0.042,"direction":"up"},
       "GOOGL":{...}, ...}

```

**Frontend consumption:**
```javascript
const es = new EventSource('/api/stream/prices');
es.onmessage = (event) => {
    const prices = JSON.parse(event.data);
    // prices: { "AAPL": { ticker, price, previous_price, change, change_percent, direction }, ... }
};
```

**Why poll-and-push instead of event-driven:**
Regular 500ms intervals produce evenly-spaced updates that the frontend accumulates into sparkline charts. Irregular event-driven pushes would cause uneven sparklines.

---

## 10. FastAPI Lifecycle Integration

**`backend/app/main.py`** — skeleton showing market data integration:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from app.market import PriceCache, MarketDataSource, create_market_data_source, create_stream_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    cache = PriceCache()
    app.state.price_cache = cache

    source = create_market_data_source(cache)
    app.state.market_source = source

    initial_tickers = await load_watchlist_from_db()  # reads from SQLite
    await source.start(initial_tickers)

    app.include_router(create_stream_router(cache))

    yield  # App is running

    # SHUTDOWN
    await source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)


# Dependency injection for route handlers
def get_price_cache() -> PriceCache:
    return app.state.price_cache

def get_market_source() -> MarketDataSource:
    return app.state.market_source
```

**Using in route handlers:**

```python
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api")

@router.post("/portfolio/trade")
async def execute_trade(
    trade: TradeRequest,
    cache: PriceCache = Depends(get_price_cache),
):
    price = cache.get_price(trade.ticker)
    if price is None:
        raise HTTPException(400, f"No price for {trade.ticker}. Wait and retry.")
    # execute trade at `price`


@router.post("/watchlist")
async def add_to_watchlist(
    payload: WatchlistAdd,
    source: MarketDataSource = Depends(get_market_source),
):
    await db.insert_watchlist(payload.ticker)
    await source.add_ticker(payload.ticker)


@router.delete("/watchlist/{ticker}")
async def remove_from_watchlist(
    ticker: str,
    source: MarketDataSource = Depends(get_market_source),
):
    await db.delete_watchlist(ticker)
    position = await db.get_position(ticker)
    # Only stop tracking if no open position — portfolio valuation still needs the price
    if not position or position.quantity == 0:
        await source.remove_ticker(ticker)
```

---

## 11. Watchlist Coordination

### Adding a ticker

```
POST /api/watchlist {ticker: "PYPL"}
  → INSERT INTO watchlist (user_id, ticker, ...)
  → await source.add_ticker("PYPL")
      Simulator: adds to GBMSimulator, rebuilds Cholesky, seeds cache immediately
      Massive:   appends to ticker list; appears on next poll cycle (~15s)
  → Return {ticker: "PYPL", price: <current or null>}
```

### Removing a ticker

```
DELETE /api/watchlist/PYPL
  → DELETE FROM watchlist WHERE ticker = 'PYPL'
  → Check: does user hold shares of PYPL?
      If no open position:  await source.remove_ticker("PYPL")  → removes from cache
      If open position:     keep tracking for portfolio valuation
  → Return {status: "ok"}
```

---

## 12. Testing Strategy

Tests live in `backend/tests/market/`. Run with:

```bash
cd backend
uv run pytest tests/market/ -v
```

### test_models.py

```python
from app.market.models import PriceUpdate

def test_direction_up():
    u = PriceUpdate(ticker="AAPL", price=191.0, previous_price=190.0)
    assert u.direction == "up"
    assert u.change == 1.0
    assert u.change_percent == pytest.approx(0.5263, rel=1e-3)

def test_direction_flat():
    u = PriceUpdate(ticker="AAPL", price=190.0, previous_price=190.0)
    assert u.direction == "flat"

def test_to_dict_keys():
    u = PriceUpdate(ticker="AAPL", price=190.0, previous_price=189.0)
    d = u.to_dict()
    assert set(d) == {"ticker", "price", "previous_price", "timestamp", "change", "change_percent", "direction"}
```

### test_cache.py

```python
from app.market.cache import PriceCache

def test_first_update_is_flat():
    cache = PriceCache()
    u = cache.update("AAPL", 190.0)
    assert u.direction == "flat"
    assert u.previous_price == 190.0

def test_direction_tracks_change():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    u = cache.update("AAPL", 191.0)
    assert u.direction == "up"

def test_version_increments():
    cache = PriceCache()
    v = cache.version
    cache.update("AAPL", 190.0)
    assert cache.version == v + 1

def test_remove():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    cache.remove("AAPL")
    assert cache.get("AAPL") is None
```

### test_simulator.py

```python
from app.market.simulator import GBMSimulator
from app.market.seed_prices import SEED_PRICES

def test_initial_price_matches_seed():
    sim = GBMSimulator(tickers=["AAPL"])
    assert sim.get_price("AAPL") == SEED_PRICES["AAPL"]

def test_prices_always_positive():
    sim = GBMSimulator(tickers=["AAPL"])
    for _ in range(10_000):
        prices = sim.step()
        assert prices["AAPL"] > 0

def test_add_remove_ticker():
    sim = GBMSimulator(tickers=["AAPL"])
    sim.add_ticker("TSLA")
    assert "TSLA" in sim.step()
    sim.remove_ticker("TSLA")
    assert "TSLA" not in sim.step()

def test_unknown_ticker_random_seed():
    sim = GBMSimulator(tickers=["ZZZZ"])
    assert 50.0 <= sim.get_price("ZZZZ") <= 300.0

def test_cholesky_none_for_single_ticker():
    sim = GBMSimulator(tickers=["AAPL"])
    assert sim._cholesky is None
    sim.add_ticker("GOOGL")
    assert sim._cholesky is not None
```

### test_simulator_source.py (async integration)

```python
import asyncio
import pytest
from app.market.cache import PriceCache
from app.market.simulator import SimulatorDataSource

@pytest.mark.asyncio
async def test_start_seeds_cache():
    cache = PriceCache()
    source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
    await source.start(["AAPL", "GOOGL"])
    assert cache.get("AAPL") is not None
    assert cache.get("GOOGL") is not None
    await source.stop()

@pytest.mark.asyncio
async def test_add_ticker_seeded_immediately():
    cache = PriceCache()
    source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
    await source.start(["AAPL"])
    await source.add_ticker("TSLA")
    assert cache.get("TSLA") is not None  # No need to wait for next loop tick
    await source.stop()

@pytest.mark.asyncio
async def test_stop_is_idempotent():
    cache = PriceCache()
    source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
    await source.start(["AAPL"])
    await source.stop()
    await source.stop()  # Should not raise
```

### test_massive.py (mocked)

```python
from unittest.mock import MagicMock, patch
import pytest
from app.market.cache import PriceCache
from app.market.massive_client import MassiveDataSource


def _snap(ticker: str, price: float, ts_ms: int = 1707580800000) -> MagicMock:
    snap = MagicMock()
    snap.ticker = ticker
    snap.last_trade.price = price
    snap.last_trade.timestamp = ts_ms
    return snap


@pytest.mark.asyncio
async def test_poll_updates_cache():
    cache = PriceCache()
    source = MassiveDataSource(api_key="test", price_cache=cache, poll_interval=60.0)
    source._tickers = ["AAPL"]
    source._client = MagicMock()

    with patch.object(source, "_fetch_snapshots", return_value=[_snap("AAPL", 190.5)]):
        await source._poll_once()

    assert cache.get_price("AAPL") == 190.5


@pytest.mark.asyncio
async def test_malformed_snapshot_skipped():
    cache = PriceCache()
    source = MassiveDataSource(api_key="test", price_cache=cache, poll_interval=60.0)
    source._tickers = ["AAPL", "BAD"]
    source._client = MagicMock()

    bad = MagicMock()
    bad.ticker = "BAD"
    bad.last_trade = None  # AttributeError on access

    with patch.object(source, "_fetch_snapshots", return_value=[_snap("AAPL", 190.5), bad]):
        await source._poll_once()

    assert cache.get_price("AAPL") == 190.5
    assert cache.get_price("BAD") is None


@pytest.mark.asyncio
async def test_api_error_does_not_crash():
    cache = PriceCache()
    source = MassiveDataSource(api_key="test", price_cache=cache, poll_interval=60.0)
    source._tickers = ["AAPL"]
    source._client = MagicMock()

    with patch.object(source, "_fetch_snapshots", side_effect=Exception("network error")):
        await source._poll_once()  # Must not raise
```

### test_factory.py

```python
import pytest
from app.market.cache import PriceCache
from app.market.factory import create_market_data_source
from app.market.simulator import SimulatorDataSource
from app.market.massive_client import MassiveDataSource


def test_no_key_returns_simulator(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    cache = PriceCache()
    source = create_market_data_source(cache)
    assert isinstance(source, SimulatorDataSource)


def test_key_set_returns_massive(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key-123")
    cache = PriceCache()
    source = create_market_data_source(cache)
    assert isinstance(source, MassiveDataSource)


def test_empty_key_returns_simulator(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "   ")
    cache = PriceCache()
    source = create_market_data_source(cache)
    assert isinstance(source, SimulatorDataSource)
```

---

## 13. Error Handling & Edge Cases

### Empty watchlist on startup

`start([])` is valid for both implementations. The simulator produces no prices; the Massive poller skips its API call. When the user adds a ticker, it begins tracking immediately.

### Price cache miss during trade

```python
price = cache.get_price(ticker)
if price is None:
    raise HTTPException(
        status_code=400,
        detail=f"Price not yet available for {ticker}. Please wait and retry.",
    )
```

The simulator avoids this by seeding in `add_ticker()`. Massive may have a brief gap on new tickers — the 400 with a clear message is correct.

### Massive API key invalid (401)

The poller logs the error, keeps retrying. The cache retains last-known prices. Users see stale data but the app doesn't crash. Fix: correct the key, restart the container.

### Removing a ticker with an open position

The watchlist route must check for open positions before calling `source.remove_ticker()`. If shares are held, the ticker stays in the data source for accurate portfolio valuation — it just disappears from the watchlist UI.

---

## 14. Configuration Reference

| Parameter | Location | Default | Notes |
|-----------|----------|---------|-------|
| `MASSIVE_API_KEY` | Env var | `""` | Empty → simulator; non-empty → Massive API |
| `update_interval` | `SimulatorDataSource.__init__` | `0.5s` | Simulator tick rate |
| `poll_interval` | `MassiveDataSource.__init__` | `15.0s` | Massive API poll rate (free tier) |
| `event_probability` | `GBMSimulator.__init__` | `0.001` | Shock event probability per ticker per tick |
| `dt` | `GBMSimulator.__init__` | `~8.5e-8` | GBM time step (fraction of trading year) |
| SSE push interval | `_generate_events()` | `0.5s` | How often SSE checks for new prices |
| SSE retry | `_generate_events()` | `1000ms` | Browser reconnect delay |

### Public API (`backend/app/market/__init__.py`)

```python
"""Market data subsystem for FinAlly."""

from .cache import PriceCache
from .factory import create_market_data_source
from .interface import MarketDataSource
from .models import PriceUpdate
from .stream import create_stream_router

__all__ = [
    "PriceUpdate",
    "PriceCache",
    "MarketDataSource",
    "create_market_data_source",
    "create_stream_router",
]
```

### Typical usage (outside the market module)

```python
from app.market import PriceCache, create_market_data_source

# Startup
cache = PriceCache()
source = create_market_data_source(cache)
await source.start(["AAPL", "GOOGL", "MSFT", ...])

# Read prices
update = cache.get("AAPL")          # PriceUpdate | None
price  = cache.get_price("AAPL")    # float | None
all_p  = cache.get_all()            # dict[str, PriceUpdate]

# Dynamic watchlist
await source.add_ticker("TSLA")
await source.remove_ticker("GOOGL")

# Shutdown
await source.stop()
```
