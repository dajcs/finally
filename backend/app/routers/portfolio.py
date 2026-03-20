"""Portfolio endpoints: positions, trading, history."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.db import (
    delete_position,
    get_cash_balance,
    get_db,
    get_portfolio_snapshots,
    get_positions,
    insert_portfolio_snapshot,
    insert_trade,
    update_cash_balance,
    upsert_position,
)

router = APIRouter(tags=["portfolio"])


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: str  # "buy" or "sell"


async def _build_portfolio(db, cache):
    """Build the full portfolio response dict."""
    cash = await get_cash_balance(db)
    positions = await get_positions(db)

    enriched = []
    total_positions_value = 0.0
    for pos in positions:
        ticker = pos["ticker"]
        current_price = cache.get_price(ticker)
        if current_price is None:
            current_price = pos["avg_cost"]
        market_value = pos["quantity"] * current_price
        cost_basis = pos["quantity"] * pos["avg_cost"]
        unrealized_pnl = market_value - cost_basis
        pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis != 0 else 0.0
        total_positions_value += market_value
        enriched.append({
            "ticker": ticker,
            "quantity": pos["quantity"],
            "avg_cost": round(pos["avg_cost"], 2),
            "current_price": round(current_price, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })

    return {
        "cash": round(cash, 2),
        "positions": enriched,
        "total_value": round(cash + total_positions_value, 2),
    }


@router.get("/portfolio")
async def get_portfolio(request: Request):
    cache = request.app.state.cache
    db = await get_db(request.app.state.db_path)
    try:
        return await _build_portfolio(db, cache)
    finally:
        await db.close()


@router.post("/portfolio/trade")
async def execute_trade(body: TradeRequest, request: Request):
    ticker = body.ticker.upper().strip()
    quantity = body.quantity
    side = body.side.lower()

    if side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="side must be 'buy' or 'sell'")
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be positive")

    cache = request.app.state.cache
    current_price = cache.get_price(ticker)
    if current_price is None:
        raise HTTPException(status_code=400, detail=f"No price available for {ticker}")

    db = await get_db(request.app.state.db_path)
    try:
        cash = await get_cash_balance(db)

        if side == "buy":
            cost = quantity * current_price
            if cash < cost:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient cash. Need ${cost:.2f}, have ${cash:.2f}",
                )
            await update_cash_balance(db, "default", -cost)

            positions = await get_positions(db)
            existing = next((p for p in positions if p["ticker"] == ticker), None)
            if existing:
                old_qty = existing["quantity"]
                old_cost = existing["avg_cost"]
                new_qty = old_qty + quantity
                new_avg = (old_qty * old_cost + quantity * current_price) / new_qty
                await upsert_position(db, "default", ticker, new_qty, new_avg)
            else:
                await upsert_position(db, "default", ticker, quantity, current_price)

        else:  # sell
            positions = await get_positions(db)
            existing = next((p for p in positions if p["ticker"] == ticker), None)
            if not existing:
                raise HTTPException(status_code=400, detail=f"No position in {ticker}")
            if quantity > existing["quantity"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot sell {quantity} shares of {ticker}, only hold {existing['quantity']}",
                )

            proceeds = quantity * current_price
            await update_cash_balance(db, "default", proceeds)

            remaining = existing["quantity"] - quantity
            if remaining <= 0:
                await delete_position(db, "default", ticker)
            else:
                await upsert_position(db, "default", ticker, remaining, existing["avg_cost"])

        await insert_trade(db, "default", ticker, side, quantity, current_price)

        portfolio = await _build_portfolio(db, cache)
        await insert_portfolio_snapshot(db, "default", portfolio["total_value"])

        return portfolio
    finally:
        await db.close()


@router.get("/portfolio/history")
async def portfolio_history(request: Request):
    db = await get_db(request.app.state.db_path)
    try:
        snapshots = await get_portfolio_snapshots(db)
    finally:
        await db.close()
    return [{"total_value": s["total_value"], "recorded_at": s["recorded_at"]} for s in snapshots]
