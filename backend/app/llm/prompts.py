"""System prompt and context formatting for the LLM."""

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant for a simulated trading workstation. You help users manage their virtual portfolio with $10,000 in starting cash.

Your capabilities:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with clear reasoning
- Execute trades when the user asks or agrees (buy/sell at current market price)
- Add or remove tickers from the watchlist

Rules:
- Market orders only, filled instantly at the current price
- This is a simulation with virtual money — no real financial risk
- Be concise and data-driven
- When suggesting trades, include your reasoning
- Always respond with valid structured JSON matching the required schema"""


def build_context_message(portfolio_context: dict) -> str:
    """Format portfolio data as readable text for the LLM context."""
    lines = ["Current Portfolio State:"]

    cash = portfolio_context.get("cash", 0)
    total_value = portfolio_context.get("total_value", cash)
    lines.append(f"Cash: ${cash:,.2f}")
    lines.append(f"Total Portfolio Value: ${total_value:,.2f}")

    positions = portfolio_context.get("positions", [])
    if positions:
        lines.append("\nOpen Positions:")
        for p in positions:
            ticker = p.get("ticker", "?")
            qty = p.get("quantity", 0)
            avg_cost = p.get("avg_cost", 0)
            current_price = p.get("current_price", 0)
            pnl = p.get("unrealized_pnl", 0)
            pnl_pct = p.get("pnl_pct", 0)
            lines.append(
                f"  {ticker}: {qty} shares @ ${avg_cost:.2f} avg | "
                f"Current: ${current_price:.2f} | P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)"
            )
    else:
        lines.append("\nNo open positions.")

    watchlist = portfolio_context.get("watchlist", [])
    if watchlist:
        lines.append("\nWatchlist Prices:")
        for w in watchlist:
            ticker = w.get("ticker", "?")
            price = w.get("price", 0)
            change_pct = w.get("change_percent", 0)
            lines.append(f"  {ticker}: ${price:.2f} ({change_pct:+.2f}%)")

    return "\n".join(lines)
