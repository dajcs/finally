"""Chat endpoint: LLM-powered trading assistant."""

import json
import logging
import os

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.db import (
    add_to_watchlist,
    delete_position,
    get_cash_balance,
    get_chat_messages,
    get_db,
    get_positions,
    get_watchlist,
    insert_chat_message,
    insert_portfolio_snapshot,
    insert_trade,
    remove_from_watchlist,
    update_cash_balance,
    upsert_position,
)
from app.llm import LLMResponse, get_llm_response
from app.llm.mock import get_mock_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    cache = request.app.state.cache
    db = await get_db(request.app.state.db_path)
    try:
        return await _handle_chat(db, cache, request, body.message)
    finally:
        await db.close()


async def _handle_chat(db, cache, request, user_message: str) -> dict:
    """Process a chat message: call LLM, execute actions, store history."""
    # Build portfolio context
    cash = await get_cash_balance(db)
    positions = await get_positions(db)
    watchlist_items = await get_watchlist(db)

    enriched_positions = []
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
        enriched_positions.append({
            "ticker": ticker,
            "quantity": pos["quantity"],
            "avg_cost": pos["avg_cost"],
            "current_price": round(current_price, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })

    watchlist_with_prices = []
    for w in watchlist_items:
        ticker = w["ticker"]
        update = cache.get(ticker)
        price = update.price if update else 0.0
        change_pct = update.change_percent if update else 0.0
        watchlist_with_prices.append({
            "ticker": ticker,
            "price": price,
            "change_percent": change_pct,
        })

    context = {
        "cash": round(cash, 2),
        "positions": enriched_positions,
        "watchlist": watchlist_with_prices,
        "total_value": round(cash + total_positions_value, 2),
    }

    # Load conversation history
    history_rows = await get_chat_messages(db)
    history = [{"role": row["role"], "content": row["content"]} for row in history_rows]
    history.append({"role": "user", "content": user_message})

    # Call LLM or mock
    use_mock = os.environ.get("LLM_MOCK", "").lower() == "true"
    try:
        if use_mock:
            llm_resp = await get_mock_response(history, context)
        else:
            llm_resp = await get_llm_response(history, context)
    except Exception as e:
        logger.exception("LLM call failed")
        await insert_chat_message(db, "default", "user", user_message)
        await insert_chat_message(
            db, "default", "assistant",
            "I encountered an error processing your request. Please try again.",
        )
        return {
            "message": "I encountered an error processing your request. Please try again.",
            "trades_executed": [],
            "watchlist_changes": [],
            "errors": [str(e)],
        }

    # Auto-execute trades
    trades_executed = []
    errors = []
    for trade in llm_resp.trades:
        result = await _execute_trade(db, cache, trade.ticker, trade.side, trade.quantity)
        if result.get("error"):
            errors.append(result["error"])
        else:
            trades_executed.append(result)

    # Auto-execute watchlist changes
    watchlist_changes_done = []
    for change in llm_resp.watchlist_changes:
        try:
            ticker = change.ticker.upper()
            if change.action == "add":
                await add_to_watchlist(db, "default", ticker)
                if hasattr(request.app.state, "market_source"):
                    await request.app.state.market_source.add_ticker(ticker)
            else:
                await remove_from_watchlist(db, "default", ticker)
                if hasattr(request.app.state, "market_source"):
                    await request.app.state.market_source.remove_ticker(ticker)
            watchlist_changes_done.append({"ticker": ticker, "action": change.action})
        except Exception as e:
            errors.append(f"Watchlist {change.action} {change.ticker}: {e}")

    # Store messages
    actions = {
        "trades": [t for t in trades_executed],
        "watchlist_changes": watchlist_changes_done,
        "errors": errors,
    }
    await insert_chat_message(db, "default", "user", user_message)
    await insert_chat_message(
        db, "default", "assistant", llm_resp.message,
        actions=json.dumps(actions) if (trades_executed or watchlist_changes_done or errors) else None,
    )

    return {
        "message": llm_resp.message,
        "trades_executed": trades_executed,
        "watchlist_changes": watchlist_changes_done,
        "errors": errors,
    }


async def _execute_trade(db, cache, ticker: str, side: str, quantity: float) -> dict:
    """Execute a single trade. Returns trade dict or error dict."""
    ticker = ticker.upper()
    current_price = cache.get_price(ticker)
    if current_price is None:
        return {"error": f"No price available for {ticker}"}

    cash = await get_cash_balance(db)

    if side == "buy":
        cost = quantity * current_price
        if cash < cost:
            return {"error": f"Insufficient cash for {ticker}. Need ${cost:.2f}, have ${cash:.2f}"}
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
            return {"error": f"No position in {ticker}"}
        if quantity > existing["quantity"]:
            return {"error": f"Cannot sell {quantity} of {ticker}, only hold {existing['quantity']}"}

        proceeds = quantity * current_price
        await update_cash_balance(db, "default", proceeds)
        remaining = existing["quantity"] - quantity
        if remaining <= 0:
            await delete_position(db, "default", ticker)
        else:
            await upsert_position(db, "default", ticker, remaining, existing["avg_cost"])

    trade = await insert_trade(db, "default", ticker, side, quantity, current_price)

    # Snapshot after trade
    new_cash = await get_cash_balance(db)
    new_positions = await get_positions(db)
    total = new_cash
    for pos in new_positions:
        p = cache.get_price(pos["ticker"])
        total += pos["quantity"] * (p if p is not None else pos["avg_cost"])
    await insert_portfolio_snapshot(db, "default", round(total, 2))

    return {
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": current_price,
    }
