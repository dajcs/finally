"""Pydantic models for LLM structured output."""

from pydantic import BaseModel, Field


class TradeAction(BaseModel):
    ticker: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(gt=0)


class WatchlistChange(BaseModel):
    ticker: str
    action: str = Field(pattern="^(add|remove)$")


class LLMResponse(BaseModel):
    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistChange] = []
