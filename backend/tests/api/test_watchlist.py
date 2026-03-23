"""Tests for watchlist endpoints."""


async def test_get_watchlist_returns_default_tickers(client):
    resp = await client.get("/api/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10
    tickers = [item["ticker"] for item in data]
    assert "AAPL" in tickers
    assert "GOOGL" in tickers


async def test_get_watchlist_includes_prices(client, cache):
    cache.update("AAPL", 190.0)
    resp = await client.get("/api/watchlist")
    data = resp.json()
    aapl = next(item for item in data if item["ticker"] == "AAPL")
    assert aapl["price"] == 190.0


async def test_add_ticker(client):
    resp = await client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert resp.status_code == 200
    data = resp.json()
    tickers = [item["ticker"] for item in data]
    assert "PYPL" in tickers


async def test_add_ticker_uppercases(client):
    resp = await client.post("/api/watchlist", json={"ticker": "pypl"})
    assert resp.status_code == 200
    data = resp.json()
    tickers = [item["ticker"] for item in data]
    assert "PYPL" in tickers


async def test_delete_ticker(client):
    resp = await client.delete("/api/watchlist/AAPL")
    assert resp.status_code == 204

    resp = await client.get("/api/watchlist")
    tickers = [item["ticker"] for item in resp.json()]
    assert "AAPL" not in tickers


async def test_delete_nonexistent_ticker(client):
    # Should not error, just no-op
    resp = await client.delete("/api/watchlist/ZZZZ")
    assert resp.status_code == 204
