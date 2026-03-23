"""Database connection management with lazy initialization."""

import os
import uuid
from datetime import datetime, timezone

import aiosqlite

from .schema import DEFAULT_CASH_BALANCE, DEFAULT_TICKERS, DEFAULT_USER_ID, SCHEMA_SQL

_DB_PATH: str | None = None


def get_db_path() -> str:
    """Return the configured database path."""
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = os.environ.get(
            "FINALLY_DB_PATH",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "db", "finally.db"),
        )
    return _DB_PATH


def set_db_path(path: str) -> None:
    """Override the database path (for testing)."""
    global _DB_PATH
    _DB_PATH = path


async def get_connection() -> aiosqlite.Connection:
    """Open a connection to the database."""
    db = await aiosqlite.connect(get_db_path())
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    """Create tables, seed default data if needed, and clean up anomalous snapshots."""
    db = await get_connection()
    try:
        await db.executescript(SCHEMA_SQL)

        # Check if default user exists
        cursor = await db.execute(
            "SELECT id FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
        )
        user = await cursor.fetchone()

        if user is None:
            now = datetime.now(timezone.utc).isoformat()

            # Create default user
            await db.execute(
                "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
                (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
            )

            # Seed default watchlist
            for ticker in DEFAULT_TICKERS:
                await db.execute(
                    "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now),
                )

            await db.commit()

        # Remove cash-only startup snapshots (a past bug recorded cash alone, not cash+positions).
        # Delete snapshots below 80% of median when we have enough history to judge.
        await db.execute("""
            DELETE FROM portfolio_snapshots
            WHERE (SELECT COUNT(*) FROM portfolio_snapshots) > 5
              AND total_value < 0.80 * (
                  SELECT total_value FROM portfolio_snapshots
                  ORDER BY total_value
                  LIMIT 1 OFFSET (SELECT COUNT(*) / 2 FROM portfolio_snapshots)
              )
        """)
        await db.commit()
    finally:
        await db.close()
