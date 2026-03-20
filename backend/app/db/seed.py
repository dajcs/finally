"""Seed data for FinAlly database."""

import uuid
from datetime import datetime, timezone


DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]


async def seed_db(db):
    """Insert default user and watchlist if not present."""
    now = datetime.now(timezone.utc).isoformat()

    # Seed default user
    await db.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        ("default", 10000.0, now),
    )

    # Seed default watchlist
    for ticker in DEFAULT_TICKERS:
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "default", ticker, now),
        )

    await db.commit()
