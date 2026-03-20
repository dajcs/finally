"""Watchlist CRUD endpoints."""

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from app.db import add_to_watchlist, get_db, get_watchlist, remove_from_watchlist

router = APIRouter(tags=["watchlist"])


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("/watchlist")
async def list_watchlist(request: Request):
    cache = request.app.state.cache
    db = await get_db(request.app.state.db_path)
    try:
        items = await get_watchlist(db)
    finally:
        await db.close()

    result = []
    for item in items:
        ticker = item["ticker"]
        update = cache.get(ticker)
        result.append({
            "ticker": ticker,
            "price": update.price if update else None,
            "previous_price": update.previous_price if update else None,
            "change_percent": update.change_percent if update else 0.0,
            "direction": update.direction if update else "flat",
        })
    return result


@router.post("/watchlist")
async def add_ticker(body: AddTickerRequest, request: Request):
    ticker = body.ticker.upper().strip()
    db = await get_db(request.app.state.db_path)
    try:
        await add_to_watchlist(db, "default", ticker)
    finally:
        await db.close()

    market_source = request.app.state.market_source
    await market_source.add_ticker(ticker)

    return await list_watchlist(request)


@router.delete("/watchlist/{ticker}", status_code=204)
async def remove_ticker(ticker: str, request: Request):
    ticker = ticker.upper().strip()
    db = await get_db(request.app.state.db_path)
    try:
        await remove_from_watchlist(db, "default", ticker)
    finally:
        await db.close()

    market_source = request.app.state.market_source
    await market_source.remove_ticker(ticker)

    return Response(status_code=204)
