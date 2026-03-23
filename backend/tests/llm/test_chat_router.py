"""Tests for the chat router with mocked LLM and DB."""

import os
from unittest.mock import AsyncMock, patch

import pytest

from app.db import get_db, init_db
from app.db.connection import reset_init_flag
from app.main import app

try:
    from httpx import ASGITransport, AsyncClient
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@pytest.fixture
async def db():
    reset_init_flag()
    await init_db(":memory:")
    conn = await get_db(":memory:")
    yield conn
    await conn.close()


@pytest.fixture
def mock_cache():
    """A mock PriceCache."""
    from app.market import PriceCache
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    cache.update("GOOGL", 175.0)
    cache.update("MSFT", 420.0)
    return cache


@pytest.mark.skipif(not HAS_HTTPX, reason="httpx not installed")
class TestChatRouter:
    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        monkeypatch.setenv("DB_PATH", ":memory:")

    async def test_chat_basic(self, mock_cache):
        """Test basic chat returns a response."""
        reset_init_flag()
        app.state.cache = mock_cache
        app.state.db_path = ":memory:"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "trades_executed" in data
        assert "watchlist_changes" in data
        assert "errors" in data

    async def test_chat_with_buy_trigger(self, mock_cache):
        """Test that 'buy' keyword triggers a trade in mock mode."""
        reset_init_flag()
        app.state.cache = mock_cache
        app.state.db_path = ":memory:"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/chat", json={"message": "buy AAPL"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trades_executed"]) == 1
        assert data["trades_executed"][0]["ticker"] == "AAPL"
        assert data["trades_executed"][0]["side"] == "buy"

    async def test_chat_llm_error_graceful(self, mock_cache):
        """Test that LLM errors are handled gracefully."""
        reset_init_flag()
        app.state.cache = mock_cache
        app.state.db_path = ":memory:"

        with patch.dict(os.environ, {"LLM_MOCK": "false"}):
            with patch("app.routers.chat.get_llm_response", side_effect=Exception("API down")):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data["message"].lower()
        assert len(data["errors"]) > 0
