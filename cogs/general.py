from __future__ import annotations

import discord
from discord.ext import commands

from ui import GLACIER, LAVENDER, make_embed


def public_prefix(ctx: commands.Context) -> bool:
    return ctx.interaction is not None or ctx.prefix == "!"


class GeneralCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Vérifier si Emilia Frost répond")
    @commands.guild_only()
    @commands.check(public_prefix)
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        await ctx.send(embed=make_embed("Emilia est là ❄️", f"Latence Gateway : **{latency} ms**\nLe bot répond correctement dans **{ctx.guild.name}**.", GLACIER), ephemeral=bool(ctx.interaction))

    @commands.hybrid_command(name="help", description="Afficher l’aide des commandes disponibles")
    @commands.guild_only()
    @commands.check(public_prefix)
    async def help(self, ctx: commands.Context):
        embed = make_embed("Aide Emilia Frost", "Commandes actuellement disponibles dans cette version.", LAVENDER)
        embed.add_field(name="💰 Économie", value="`/balance` · `!balance` · `!daily` · `!work` · `!pay` · `!bank` · `!deposit` · `!withdraw` · `!leaderboard`", inline=False)
        embed.add_field(name="🧭 Général", value="`/ping` · `!ping` · `/help` · `!help`", inline=False)
        embed.add_field(name="🛡️ Staff", value="`+warn` · `+warnings` · `+timeout` · `+kick` · `+ban` (role-ban interne) · `+unban` · `+discordban` · `+setbanrole` · `+setlog` · `+clear`", inline=False)
        embed.add_field(name="ℹ️ À venir", value="Les autres modules du cahier maître ne sont pas encore implémentés. L’aide ne les annonce pas comme actifs.", inline=False)
        await ctx.send(embed=embed, ephemeral=bool(ctx.interaction))

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.db.ensure_guild(guild.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCog(bot))
