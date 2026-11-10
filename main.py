"""Emilia Frost startup module.

With DISCORD_TOKEN set, run the legacy Emilia bot (whose commands are
registered by emilia_frost.py and emilia_extra.py). If those modules are not
shipped, run the modular cogs bot instead. Without a token, expose a small
health endpoint for deployment diagnostics.
"""
from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import discord
    from discord.ext import commands
except ImportError:
    discord = None
    commands = None

try:
    from database import Database
except ImportError:
    Database = None


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_error(404, "Not found")
            return
        body = b"Emilia is running\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_health_server() -> None:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Emilia health server listening on port {port}", flush=True)
    server.serve_forever()


if commands is not None:
    class EmiliaBot(commands.Bot):
        def __init__(self, db_path: str | None = None, **kwargs):
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            owners = {
                int(value.strip())
                for value in os.getenv("OWNER_IDS", "").split(",")
                if value.strip().isdigit()
            }
            super().__init__(
                command_prefix=commands.when_mentioned_or("!", "+", "w."),
                intents=intents,
                help_command=None,
                owner_ids=owners,
                **kwargs,
            )
            self.db = (
                Database(db_path or os.getenv("DATABASE_PATH", "data/emilia_frost.db"))
                if Database is not None else None
            )

        async def initialize_runtime(self):
            if self.db is not None:
                await self.db.initialize()
            for extension in ("cogs.general", "cogs.economy", "cogs.moderation", "cogs.owner"):
                await self.load_extension(extension)

        async def setup_hook(self) -> None:
            await self.initialize_runtime()
            if self.tree is not None:
                await self.tree.sync()
else:
    class EmiliaBot:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("discord.py est nécessaire pour démarrer le bot.")


def _run_modular_bot(token: str) -> None:
    if commands is None:
        raise RuntimeError("discord.py est nécessaire pour démarrer le bot.")
    bot = EmiliaBot()
    bot.run(token)


def main() -> None:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        start_health_server()
        return

    try:
        import emilia_frost  # noqa: F401
        import emilia_extra
    except ModuleNotFoundError as error:
        if error.name not in {"emilia_frost", "emilia_extra"}:
            raise
        _run_modular_bot(token)
        return

    emilia_extra.main()


if __name__ == "__main__":
    main()
