from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from core.config import Settings
from database import Database
from ui import ERROR, make_embed

SETTINGS = Settings.from_env()
logging.basicConfig(level=SETTINGS.log_level,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("emilia_frost")


class EmiliaBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned_or("!", "+", "w."),
                         intents=intents, help_command=None, case_insensitive=True)
        self.db = Database(SETTINGS.database_path)
        self.owner_ids = set(SETTINGS.owner_ids)

    async def setup_hook(self) -> None:
        await self.db.initialize()
        for extension in ("cogs.general", "cogs.economy", "cogs.moderation", "cogs.owner"):
            await self.load_extension(extension)
            log.info("Extension chargée : %s", extension)
        if SETTINGS.sync_guild_id:
            guild = discord.Object(id=SETTINGS.sync_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("%d commandes synchronisées sur le serveur de test %s", len(synced), SETTINGS.sync_guild_id)
        else:
            synced = await self.tree.sync()
            log.info("%d commandes slash synchronisées globalement", len(synced))

    async def on_ready(self) -> None:
        log.info("Emilia Frost connectée : %s (%s), %s serveur(s)", self.user, self.user.id, len(self.guilds))
        await self.change_presence(activity=discord.Game(name="❄️ Emilia Frost • /help"))

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CheckFailure):
            await ctx.send(embed=make_embed("Accès refusé", "Cette commande n’est pas disponible avec ce préfixe ou tes permissions.", ERROR), ephemeral=bool(ctx.interaction))
            return
        if isinstance(error, commands.MissingRequiredArgument):
            syntax = f"{ctx.clean_prefix}{ctx.command.qualified_name} {ctx.command.signature}"
            await ctx.send(embed=make_embed("Paramètre manquant", f"Syntaxe : `{syntax}`", ERROR), ephemeral=bool(ctx.interaction))
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send(embed=make_embed("Paramètre invalide", "Vérifie les mentions, nombres et valeurs fournis.", ERROR), ephemeral=bool(ctx.interaction))
            return
        log.error("Erreur de commande", exc_info=(type(error), error, error.__traceback__))
        await ctx.send(embed=make_embed("Petit incident", "La commande n’a pas abouti. Réessaie dans un instant.", ERROR), ephemeral=bool(ctx.interaction))


bot = EmiliaBot()


async def main() -> None:
    SETTINGS.validate_for_startup()
    async with bot:
        await bot.start(SETTINGS.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
