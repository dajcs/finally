"""Tests for LLM structured output parsing."""

import pytest
from pydantic import ValidationError

from app.llm.schemas import LLMResponse, TradeAction, WatchlistChange


class TestLLMResponse:
    def test_parse_full_response(self):
        raw = '{"message": "Done!", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}], "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]}'
        resp = LLMResponse.model_validate_json(raw)
        assert resp.message == "Done!"
        assert len(resp.trades) == 1
        assert resp.trades[0].ticker == "AAPL"
        assert resp.trades[0].side == "buy"
        assert resp.trades[0].quantity == 10
        assert len(resp.watchlist_changes) == 1
        assert resp.watchlist_changes[0].ticker == "PYPL"
        assert resp.watchlist_changes[0].action == "add"

    def test_parse_message_only(self):
        raw = '{"message": "Hello!"}'
        resp = LLMResponse.model_validate_json(raw)
        assert resp.message == "Hello!"
        assert resp.trades == []
        assert resp.watchlist_changes == []

    def test_missing_message_fails(self):
        raw = '{"trades": []}'
        with pytest.raises(ValidationError):
            LLMResponse.model_validate_json(raw)

    def test_invalid_side_fails(self):
        raw = '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "short", "quantity": 1}]}'
        with pytest.raises(ValidationError):
            LLMResponse.model_validate_json(raw)

    def test_negative_quantity_fails(self):
        raw = '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": -5}]}'
        with pytest.raises(ValidationError):
            LLMResponse.model_validate_json(raw)

    def test_invalid_watchlist_action_fails(self):
        raw = '{"message": "ok", "watchlist_changes": [{"ticker": "X", "action": "update"}]}'
        with pytest.raises(ValidationError):
            LLMResponse.model_validate_json(raw)

    def test_malformed_json_fails(self):
        with pytest.raises(Exception):
            LLMResponse.model_validate_json("not json at all")

    def test_multiple_trades(self):
        raw = '{"message": "Trading!", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}, {"ticker": "TSLA", "side": "sell", "quantity": 3}]}'
        resp = LLMResponse.model_validate_json(raw)
        assert len(resp.trades) == 2
        assert resp.trades[1].side == "sell"
