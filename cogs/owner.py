from __future__ import annotations

import discord
from discord.ext import commands

from ui import LAVENDER, make_embed


def owner_prefix(ctx: commands.Context) -> bool:
    return ctx.interaction is not None or ctx.prefix == "w."


class OwnerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def owner_check(self, ctx: commands.Context) -> bool:
        return ctx.author.id in self.bot.owner_ids

    @commands.hybrid_command(name="ownerstatus", description="Voir le statut du bot (propriétaire uniquement)")
    @commands.check(owner_prefix)
    async def ownerstatus(self, ctx: commands.Context):
        if not await self.owner_check(ctx):
            return await ctx.send(embed=make_embed("Accès refusé", "Cette commande est réservée au propriétaire configuré par ID Discord."), ephemeral=bool(ctx.interaction))
        text = f"Connecté : **{self.bot.is_ready()}**\nServeurs : **{len(self.bot.guilds)}**\nCommandes : **{len(self.bot.commands)}**\nBase : `{self.bot.db.path}`"
        await ctx.send(embed=make_embed("Console propriétaire", text, LAVENDER), ephemeral=bool(ctx.interaction))


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCog(bot))
