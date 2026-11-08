from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    discord_token: str
    owner_ids: frozenset[int]
    database_path: Path
    log_level: str
    sync_guild_id: int | None

    @classmethod
    def from_env(cls) -> "Settings":
        owners = frozenset(
            int(value.strip()) for value in os.getenv("OWNER_IDS", "").split(",")
            if value.strip().isdigit()
        )
        sync_guild = os.getenv("SYNC_GUILD_ID", "").strip()
        return cls(
            discord_token=os.getenv("DISCORD_TOKEN", "").strip(),
            owner_ids=owners,
            database_path=Path(os.getenv("DATABASE_PATH", str(ROOT / "data" / "emilia_frost.db"))),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            sync_guild_id=int(sync_guild) if sync_guild.isdigit() else None,
        )

    def validate_for_startup(self) -> None:
        if not self.discord_token:
            raise RuntimeError("DISCORD_TOKEN est absent. Configure-le dans les variables d’environnement.")
        if not self.owner_ids:
            raise RuntimeError("OWNER_IDS doit contenir au moins l’ID Discord numérique du propriétaire.")
