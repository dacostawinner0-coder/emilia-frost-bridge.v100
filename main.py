from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import Database
from ui import ERROR, GLACIER, make_embed

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("emilia_frost")


def owner_ids() -> set[int]:
    return {int(value.strip()) for value in os.getenv("OWNER_IDS", "").split(",") if value.strip().isdigit()}


class EmiliaBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned_or("!", "+", "w."),
                         intents=intents, help_command=None, case_insensitive=True)
        self.db = Database()
        self.owner_ids = owner_ids()

    async def setup_hook(self) -> None:
        await self.db.initialize()
        await self.load_extension("cogs.economy")
        await self.load_extension("cogs.moderation")
        synced = await self.tree.sync()
        log.info("%d commandes slash synchronisées", len(synced))

    async def on_ready(self) -> None:
        log.info("Emilia Frost connectée : %s (%s), %s serveur(s)", self.user, self.user.id, len(self.guilds))
        await self.change_presence(activity=discord.Game(name="❄️ Emilia Frost • /aide"))

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CheckFailure):
            await ctx.send(embed=make_embed("Accès refusé", "Cette commande n’est pas disponible avec ce préfixe ou tes permissions.", ERROR), ephemeral=bool(ctx.interaction))
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=make_embed("Paramètre manquant", f"Syntaxe : `{ctx.clean_prefix}{ctx.command.qualified_name} {ctx.command.signature}`", ERROR), ephemeral=bool(ctx.interaction))
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send(embed=make_embed("Paramètre invalide", "Vérifie les mentions, nombres et valeurs fournis.", ERROR), ephemeral=bool(ctx.interaction))
            return
        log.error("Erreur de commande", exc_info=(type(error), error, error.__traceback__))
        await ctx.send(embed=make_embed("Petit incident", "La commande n’a pas abouti. Réessaie dans un instant.", ERROR), ephemeral=bool(ctx.interaction))


bot = EmiliaBot()


async def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN est absent. Configure-le dans les variables d’environnement de l’hébergeur.")
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
