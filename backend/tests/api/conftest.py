"""Shared fixtures for API tests."""

import os
import tempfile

import httpx
import pytest
from fastapi import FastAPI

from app.db import init_db
from app.db.connection import reset_init_flag
from app.market import PriceCache
from app.routers import health, portfolio, watchlist


class FakeMarketSource:
    """Minimal fake market data source for tests."""

    async def add_ticker(self, ticker: str):
        pass

    async def remove_ticker(self, ticker: str):
        pass

    async def start(self, tickers: list[str]):
        pass

    async def stop(self):
        pass

    def get_tickers(self) -> list[str]:
        return []


@pytest.fixture
async def db_path():
    """Create a temporary SQLite file, initialize it, and clean up after."""
    reset_init_flag()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    await init_db(path)
    yield path
    reset_init_flag()
    os.unlink(path)


@pytest.fixture
def cache():
    return PriceCache()


@pytest.fixture
def app(db_path, cache):
    test_app = FastAPI()
    test_app.state.db_path = db_path
    test_app.state.cache = cache
    test_app.state.market_source = FakeMarketSource()
    test_app.include_router(health.router, prefix="/api")
    test_app.include_router(portfolio.router, prefix="/api")
    test_app.include_router(watchlist.router, prefix="/api")
    return test_app


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
