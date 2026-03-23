"""Tests for portfolio endpoints."""


async def test_get_portfolio_initial_state(client):
    resp = await client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cash"] == 10000.0
    assert data["positions"] == []
    assert data["total_value"] == 10000.0


async def test_buy_shares(client, cache):
    cache.update("AAPL", 100.0)
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cash"] == 9000.0
    assert len(data["positions"]) == 1
    pos = data["positions"][0]
    assert pos["ticker"] == "AAPL"
    assert pos["quantity"] == 10
    assert pos["avg_cost"] == 100.0
    assert pos["current_price"] == 100.0


async def test_sell_shares(client, cache):
    cache.update("AAPL", 100.0)
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    cache.update("AAPL", 110.0)
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cash"] == 9550.0  # 9000 + 5*110
    pos = data["positions"][0]
    assert pos["quantity"] == 5
    assert pos["avg_cost"] == 100.0


async def test_sell_all_removes_position(client, cache):
    cache.update("AAPL", 100.0)
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "sell"},
    )
    data = resp.json()
    assert data["cash"] == 10000.0
    assert len(data["positions"]) == 0


async def test_buy_insufficient_cash(client, cache):
    cache.update("AAPL", 100.0)
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 200, "side": "buy"},
    )
    assert resp.status_code == 400
    assert "Insufficient cash" in resp.json()["detail"]


async def test_sell_no_position(client, cache):
    cache.update("AAPL", 100.0)
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
    )
    assert resp.status_code == 400
    assert "No position" in resp.json()["detail"]


async def test_sell_more_than_held(client, cache):
    cache.update("AAPL", 100.0)
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
    )
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "sell"},
    )
    assert resp.status_code == 400
    assert "Cannot sell" in resp.json()["detail"]


async def test_buy_no_price(client):
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "ZZZZ", "quantity": 5, "side": "buy"},
    )
    assert resp.status_code == 400
    assert "No price" in resp.json()["detail"]


async def test_invalid_side(client):
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "short"},
    )
    assert resp.status_code == 400


async def test_negative_quantity(client):
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": -1, "side": "buy"},
    )
    assert resp.status_code == 400


async def test_portfolio_history(client, cache):
    # Execute a trade to generate a snapshot
    cache.update("AAPL", 100.0)
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1, "side": "buy"},
    )
    resp = await client.get("/api/portfolio/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "total_value" in data[0]
    assert "recorded_at" in data[0]


async def test_weighted_average_cost(client, cache):
    cache.update("AAPL", 100.0)
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    cache.update("AAPL", 200.0)
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    data = resp.json()
    pos = data["positions"][0]
    assert pos["quantity"] == 20
    assert pos["avg_cost"] == 150.0  # (10*100 + 10*200) / 20
