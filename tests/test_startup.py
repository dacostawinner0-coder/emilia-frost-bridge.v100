from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from database import Database
from main import EmiliaBot


class StartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_extensions_load_and_commands_register_without_discord_login(self):
        temp = tempfile.TemporaryDirectory()
        bot = EmiliaBot()
        bot.db = Database(Path(temp.name) / "startup.db")
        try:
            await bot.db.initialize()
            for extension in ("cogs.general", "cogs.economy", "cogs.moderation", "cogs.owner"):
                await bot.load_extension(extension)
            expected = {
                "ping", "help", "aide", "balance", "daily", "work", "pay", "bank",
                "deposit", "withdraw", "leaderboard", "warn", "warnings", "timeout",
                "kick", "ban", "unban", "discordban", "setbanrole", "setlog", "clear",
                "ownerstatus",
            }
            self.assertTrue(expected.issubset(set(bot.all_commands)))
            slash_names = {command.name for command in bot.tree.get_commands()}
            self.assertTrue(expected.issubset(slash_names))
        finally:
            await bot.close()
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
