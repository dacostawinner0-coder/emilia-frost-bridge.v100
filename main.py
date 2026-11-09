"""Emilia Frost startup module.

Supports the bot branch and the starter Railway health-check behavior: with a
DISCORD_TOKEN it boots the bot; without one it serves the lightweight health endpoint.
"""
from __future__ import annotations

import asyncio
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import discord
    from discord.ext import commands
except ImportError:  # Optional for the health-check-only deployment.
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

    def log_message(self, format, *args):
        super().log_message(format, *args)


if commands is not None:
    class EmiliaBot(commands.Bot):
        """Bot bootstrap used by startup tests and deployments."""

        def __init__(self, db_path: str | None = None, **kwargs):
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            super().__init__(command_prefix="!", intents=intents, help_command=None, **kwargs)
            if Database is None:
                self.db = None
            else:
                self.db = Database(db_path or os.getenv("DATABASE_PATH", "data/emilia_frost.db"))

        async def initialize_runtime(self):
            if self.db is not None and hasattr(self.db, "initialize"):
                await self.db.initialize()
            for extension in ("cogs.general", "cogs.economy", "cogs.moderation", "cogs.owner"):
                try:
                    await self.load_extension(extension)
                except Exception:
                    # Keep startup resilient when optional cogs aren't included.
                    continue
else:
    class EmiliaBot:  # pragma: no cover - used only without discord.py installed
        def __init__(self, *args, **kwargs):
            raise RuntimeError("discord.py est nécessaire pour démarrer le bot.")


def start_health_server() -> None:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Emilia health server listening on port {port}", flush=True)
    server.serve_forever()


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        start_health_server()
        return

    if commands is None:
        raise RuntimeError("discord.py est nécessaire pour démarrer le bot.")

    # Keep historical cogs/listeners that register on import when they exist.
    try:
        import emilia_frost  # noqa: F401
        import emilia_extra  # noqa: F401
    except ModuleNotFoundError:
        pass

    bot = EmiliaBot()

    async def bootstrap() -> None:
        await bot.initialize_runtime()

    asyncio.run(bootstrap())
    bot.run(token)


if __name__ == "__main__":
    main()
