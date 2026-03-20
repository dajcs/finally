"""CRUD helpers for FinAlly database."""

import uuid
from datetime import datetime, timezone

import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: aiosqlite.Row) -> dict:
    return dict(row)


# --- Users / Cash ---

async def get_cash_balance(db: aiosqlite.Connection, user_id: str = "default") -> float:
    cursor = await db.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return row["cash_balance"] if row else 0.0


async def update_cash_balance(
    db: aiosqlite.Connection, user_id: str, amount_delta: float
) -> float:
    """Atomically add/subtract from cash balance. Returns new balance."""
    await db.execute(
        "UPDATE users_profile SET cash_balance = cash_balance + ? WHERE id = ?",
        (amount_delta, user_id),
    )
    await db.commit()
    return await get_cash_balance(db, user_id)


# --- Watchlist ---

async def get_watchlist(
    db: aiosqlite.Connection, user_id: str = "default"
) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM watchlist WHERE user_id = ? ORDER BY added_at, ticker",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def add_to_watchlist(
    db: aiosqlite.Connection, user_id: str, ticker: str
) -> dict:
    entry = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "ticker": ticker.upper(),
        "added_at": _now(),
    }
    await db.execute(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        (entry["id"], entry["user_id"], entry["ticker"], entry["added_at"]),
    )
    await db.commit()
    return entry


async def remove_from_watchlist(
    db: aiosqlite.Connection, user_id: str, ticker: str
):
    await db.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker.upper()),
    )
    await db.commit()


# --- Positions ---

async def get_positions(
    db: aiosqlite.Connection, user_id: str = "default"
) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM positions WHERE user_id = ?", (user_id,)
    )
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def upsert_position(
    db: aiosqlite.Connection,
    user_id: str,
    ticker: str,
    quantity: float,
    avg_cost: float,
):
    """Insert or update a position. Deletes if quantity is 0."""
    ticker = ticker.upper()
    if quantity == 0:
        await delete_position(db, user_id, ticker)
        return

    now = _now()
    await db.execute(
        """INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id, ticker)
           DO UPDATE SET quantity = ?, avg_cost = ?, updated_at = ?""",
        (str(uuid.uuid4()), user_id, ticker, quantity, avg_cost, now,
         quantity, avg_cost, now),
    )
    await db.commit()


async def delete_position(
    db: aiosqlite.Connection, user_id: str, ticker: str
):
    await db.execute(
        "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker.upper()),
    )
    await db.commit()


# --- Trades ---

async def insert_trade(
    db: aiosqlite.Connection,
    user_id: str,
    ticker: str,
    side: str,
    quantity: float,
    price: float,
) -> dict:
    trade = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "ticker": ticker.upper(),
        "side": side,
        "quantity": quantity,
        "price": price,
        "executed_at": _now(),
    }
    await db.execute(
        """INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (trade["id"], trade["user_id"], trade["ticker"], trade["side"],
         trade["quantity"], trade["price"], trade["executed_at"]),
    )
    await db.commit()
    return trade


# --- Portfolio Snapshots ---

async def insert_portfolio_snapshot(
    db: aiosqlite.Connection, user_id: str, total_value: float
) -> dict:
    snapshot = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "total_value": total_value,
        "recorded_at": _now(),
    }
    await db.execute(
        """INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)
           VALUES (?, ?, ?, ?)""",
        (snapshot["id"], snapshot["user_id"], snapshot["total_value"], snapshot["recorded_at"]),
    )
    await db.commit()
    return snapshot


async def get_portfolio_snapshots(
    db: aiosqlite.Connection, user_id: str = "default", limit: int = 500
) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


# --- Chat Messages ---

async def insert_chat_message(
    db: aiosqlite.Connection,
    user_id: str,
    role: str,
    content: str,
    actions: str | None = None,
) -> dict:
    msg = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "role": role,
        "content": content,
        "actions": actions,
        "created_at": _now(),
    }
    await db.execute(
        """INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (msg["id"], msg["user_id"], msg["role"], msg["content"], msg["actions"], msg["created_at"]),
    )
    await db.commit()
    return msg


async def get_chat_messages(
    db: aiosqlite.Connection, user_id: str = "default", limit: int = 20
) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cursor.fetchall()
    return list(reversed([_row_to_dict(r) for r in rows]))
