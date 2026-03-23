"""Tests for prompt building."""

from app.llm.prompts import SYSTEM_PROMPT, build_context_message


class TestPrompts:
    def test_system_prompt_exists(self):
        assert "FinAlly" in SYSTEM_PROMPT
        assert "trading assistant" in SYSTEM_PROMPT

    def test_build_context_empty_portfolio(self):
        ctx = {"cash": 10000, "total_value": 10000, "positions": [], "watchlist": []}
        result = build_context_message(ctx)
        assert "$10,000.00" in result
        assert "No open positions" in result

    def test_build_context_with_positions(self):
        ctx = {
            "cash": 5000,
            "total_value": 7500,
            "positions": [
                {
                    "ticker": "AAPL",
                    "quantity": 10,
                    "avg_cost": 150.0,
                    "current_price": 160.0,
                    "unrealized_pnl": 100.0,
                    "pnl_pct": 6.7,
                }
            ],
            "watchlist": [{"ticker": "AAPL", "price": 160.0, "change_percent": 1.5}],
        }
        result = build_context_message(ctx)
        assert "AAPL" in result
        assert "10 shares" in result
        assert "$5,000.00" in result

    def test_build_context_with_watchlist(self):
        ctx = {
            "cash": 10000,
            "total_value": 10000,
            "positions": [],
            "watchlist": [
                {"ticker": "GOOGL", "price": 175.50, "change_percent": -0.5},
            ],
        }
        result = build_context_message(ctx)
        assert "GOOGL" in result
        assert "$175.50" in result
