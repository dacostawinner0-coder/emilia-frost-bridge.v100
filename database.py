from __future__ import annotations

import os
from pathlib import Path

import aiosqlite


DEFAULT_DATABASE = Path(__file__).resolve().parent / "data" / "emilia_frost.db"


class Database:
    """Async SQLite store. Every community-owned record is keyed by guild_id."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE)))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def connect(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self.path, timeout=30)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("PRAGMA busy_timeout = 30000")
        return db

    async def initialize(self) -> None:
        async with await self.connect() as db:
            await db.execute("PRAGMA journal_mode = WAL")
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id TEXT PRIMARY KEY,
                    currency_name TEXT NOT NULL DEFAULT 'Crédits ⚙️',
                    daily_reward INTEGER NOT NULL DEFAULT 200 CHECK (daily_reward >= 0),
                    work_min INTEGER NOT NULL DEFAULT 25 CHECK (work_min >= 0),
                    work_max INTEGER NOT NULL DEFAULT 100 CHECK (work_max >= work_min),
                    log_channel_id TEXT,
                    ban_role_id TEXT,
                    updated_at INTEGER NOT NULL DEFAULT (unixepoch())
                );
                CREATE TABLE IF NOT EXISTS economy_accounts (
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    wallet INTEGER NOT NULL DEFAULT 0 CHECK (wallet >= 0),
                    bank INTEGER NOT NULL DEFAULT 0 CHECK (bank >= 0),
                    mf INTEGER NOT NULL DEFAULT 0 CHECK (mf >= 0),
                    daily_at INTEGER NOT NULL DEFAULT 0,
                    work_at INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    updated_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    PRIMARY KEY (guild_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL DEFAULT (unixepoch())
                );
                CREATE INDEX IF NOT EXISTS ix_transactions_guild_user
                    ON transactions(guild_id, user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS moderation_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    moderator_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL DEFAULT (unixepoch())
                );
                CREATE INDEX IF NOT EXISTS ix_cases_guild_target
                    ON moderation_cases(guild_id, target_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS role_bans (
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    roles_json TEXT NOT NULL DEFAULT '[]',
                    moderator_id TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    PRIMARY KEY (guild_id, user_id)
                );
                """
            )
            await db.commit()

    async def ensure_guild(self, guild_id: int | str) -> aiosqlite.Row:
        async with await self.connect() as db:
            await db.execute(
                "INSERT INTO guild_settings(guild_id) VALUES (?) ON CONFLICT(guild_id) DO NOTHING",
                (str(guild_id),),
            )
            row = await (await db.execute(
                "SELECT * FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
            )).fetchone()
            await db.commit()
            return row

    async def account(self, guild_id: int | str, user_id: int | str) -> aiosqlite.Row:
        async with await self.connect() as db:
            await db.execute(
                "INSERT INTO economy_accounts(guild_id,user_id) VALUES (?,?) "
                "ON CONFLICT(guild_id,user_id) DO NOTHING",
                (str(guild_id), str(user_id)),
            )
            row = await (await db.execute(
                "SELECT * FROM economy_accounts WHERE guild_id = ? AND user_id = ?",
                (str(guild_id), str(user_id)),
            )).fetchone()
            await db.commit()
            return row

    async def claim_reward(self, guild_id: int, user_id: int, kind: str, amount: int,
                           cooldown: int, now: int) -> tuple[bool, int]:
        column = {"daily": "daily_at", "work": "work_at"}.get(kind)
        if column is None or amount < 0:
            raise ValueError("Récompense ou type invalide")
        async with await self.connect() as db:
            await db.execute("BEGIN IMMEDIATE")
            await db.execute(
                "INSERT INTO economy_accounts(guild_id,user_id) VALUES (?,?) "
                "ON CONFLICT(guild_id,user_id) DO NOTHING", (str(guild_id), str(user_id))
            )
            row = await (await db.execute(
                f"SELECT {column} AS last_at FROM economy_accounts WHERE guild_id=? AND user_id=?",
                (str(guild_id), str(user_id)),
            )).fetchone()
            remaining = int(row["last_at"]) + cooldown - now
            if remaining > 0:
                await db.rollback()
                return False, remaining
            await db.execute(
                f"UPDATE economy_accounts SET wallet=wallet+?, {column}=?, updated_at=? "
                "WHERE guild_id=? AND user_id=?",
                (amount, now, now, str(guild_id), str(user_id)),
            )
            await db.execute(
                "INSERT INTO transactions(guild_id,user_id,kind,amount,details,created_at) VALUES (?,?,?,?,?,?)",
                (str(guild_id), str(user_id), kind, amount, "Récompense Emilia Frost", now),
            )
            await db.commit()
            return True, amount

    async def transfer(self, guild_id: int, sender_id: int, recipient_id: int, amount: int) -> bool:
        if amount <= 0 or sender_id == recipient_id:
            return False
        async with await self.connect() as db:
            await db.execute("BEGIN IMMEDIATE")
            for uid in (sender_id, recipient_id):
                await db.execute(
                    "INSERT INTO economy_accounts(guild_id,user_id) VALUES (?,?) "
                    "ON CONFLICT(guild_id,user_id) DO NOTHING", (str(guild_id), str(uid))
                )
            cursor = await db.execute(
                "UPDATE economy_accounts SET wallet=wallet-?,updated_at=unixepoch() "
                "WHERE guild_id=? AND user_id=? AND wallet>=?",
                (amount, str(guild_id), str(sender_id), amount),
            )
            if cursor.rowcount != 1:
                await db.rollback()
                return False
            await db.execute(
                "UPDATE economy_accounts SET wallet=wallet+?,updated_at=unixepoch() WHERE guild_id=? AND user_id=?",
                (amount, str(guild_id), str(recipient_id)),
            )
            for uid, kind, delta, other in (
                (sender_id, "transfer_out", -amount, recipient_id),
                (recipient_id, "transfer_in", amount, sender_id),
            ):
                await db.execute(
                    "INSERT INTO transactions(guild_id,user_id,kind,amount,details) VALUES (?,?,?,?,?)",
                    (str(guild_id), str(uid), kind, delta, f"Membre {other}"),
                )
            await db.commit()
            return True

    async def bank_move(self, guild_id: int, user_id: int, amount: int, deposit: bool) -> bool:
        if amount <= 0:
            return False
        source, destination = ("wallet", "bank") if deposit else ("bank", "wallet")
        async with await self.connect() as db:
            await db.execute("BEGIN IMMEDIATE")
            await db.execute(
                "INSERT INTO economy_accounts(guild_id,user_id) VALUES (?,?) "
                "ON CONFLICT(guild_id,user_id) DO NOTHING", (str(guild_id), str(user_id))
            )
            cursor = await db.execute(
                f"UPDATE economy_accounts SET {source}={source}-?,{destination}={destination}+?,updated_at=unixepoch() "
                f"WHERE guild_id=? AND user_id=? AND {source}>=?",
                (amount, amount, str(guild_id), str(user_id), amount),
            )
            if cursor.rowcount != 1:
                await db.rollback()
                return False
            await db.execute(
                "INSERT INTO transactions(guild_id,user_id,kind,amount,details) VALUES (?,?,?,?,'Virement bancaire')",
                (str(guild_id), str(user_id), "deposit" if deposit else "withdraw", amount),
            )
            await db.commit()
            return True

    async def top_accounts(self, guild_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        async with await self.connect() as db:
            return await (await db.execute(
                "SELECT user_id,wallet,bank,mf FROM economy_accounts WHERE guild_id=? "
                "ORDER BY (wallet+bank) DESC LIMIT ?", (str(guild_id), limit)
            )).fetchall()

    async def add_case(self, guild_id: int, target_id: int, moderator_id: int,
                       action: str, reason: str) -> int:
        async with await self.connect() as db:
            cursor = await db.execute(
                "INSERT INTO moderation_cases(guild_id,target_id,moderator_id,action,reason) VALUES (?,?,?,?,?)",
                (str(guild_id), str(target_id), str(moderator_id), action, reason[:1000]),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def cases(self, guild_id: int, target_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        async with await self.connect() as db:
            return await (await db.execute(
                "SELECT * FROM moderation_cases WHERE guild_id=? AND target_id=? ORDER BY created_at DESC LIMIT ?",
                (str(guild_id), str(target_id), limit),
            )).fetchall()
