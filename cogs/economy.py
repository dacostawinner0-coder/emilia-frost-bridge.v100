from __future__ import annotations

import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from ui import GLACIER, LAVENDER, SUCCESS, make_embed


def prefix_is(prefix: str):
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.interaction is not None or ctx.prefix == prefix
    return commands.check(predicate)


class EconomyCog(commands.Cog):
    """Guild-isolated economy starter commands, available as slash and ! prefix."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def settings(self, guild_id: int):
        return await self.bot.db.ensure_guild(guild_id)

    @commands.hybrid_command(name="aide", description="Découvrir les commandes Emilia Frost")
    @commands.guild_only()
    @prefix_is("!")
    async def aide(self, ctx: commands.Context):
        embed = make_embed("Bienvenue dans Emilia Frost", "Une expérience communautaire douce et claire, pensée pour rester agréable sur mobile comme sur ordinateur.", LAVENDER)
        embed.add_field(name="💰 Économie", value="`/balance` · `!balance` · `!daily` · `!work` · `!pay` · `!bank` · `!deposit` · `!withdraw` · `!leaderboard`", inline=False)
        embed.add_field(name="🛡️ Modération", value="Les commandes staff utilisent `+` : `+warn`, `+warnings`, `+timeout`, `+kick`, `+ban` (role-ban interne), `+discordban` (ban Discord).", inline=False)
        embed.add_field(name="ℹ️ État du projet", value="Les modules non listés ici ne sont pas encore implémentés. Les comptes sont séparés par serveur.", inline=False)
        await ctx.send(embed=embed, ephemeral=bool(ctx.interaction))

    @commands.hybrid_command(name="balance", aliases=["solde"], description="Consulter un solde sur ce serveur")
    @commands.guild_only()
    @prefix_is("!")
    async def balance(self, ctx: commands.Context, membre: discord.Member | None = None):
        target = membre or ctx.author
        account = await self.bot.db.account(ctx.guild.id, target.id)
        settings = await self.settings(ctx.guild.id)
        embed = make_embed(f"Portefeuille de {target.display_name}", "Voici l’aperçu économique de ce serveur.")
        embed.add_field(name="⚙️ Portefeuille", value=f"**{account['wallet']:,}** {settings['currency_name']}")
        embed.add_field(name="🏦 Banque", value=f"**{account['bank']:,}** {settings['currency_name']}")
        embed.add_field(name="💎 MF", value=f"**{account['mf']:,}**")
        embed.add_field(name="Patrimoine liquide", value=f"**{account['wallet'] + account['bank']:,}** {settings['currency_name']}", inline=False)
        await ctx.send(embed=embed, ephemeral=bool(ctx.interaction and target.id != ctx.author.id))

    @commands.hybrid_command(name="daily", description="Récupérer ta récompense quotidienne")
    @commands.guild_only()
    @prefix_is("!")
    async def daily(self, ctx: commands.Context):
        settings = await self.settings(ctx.guild.id)
        success, value = await self.bot.db.claim_reward(ctx.guild.id, ctx.author.id, "daily", settings["daily_reward"], 86400, int(time.time()))
        if not success:
            return await ctx.send(embed=make_embed("Ta récompense se prépare", f"Reviens dans **{self.format_time(value)}**.", LAVENDER), ephemeral=bool(ctx.interaction))
        await ctx.send(embed=make_embed("Cadeau quotidien récupéré", f"Ton portefeuille reçoit **{value:,} {settings['currency_name']}**. À demain !", SUCCESS))

    @commands.hybrid_command(name="work", description="Travailler pour gagner des Crédits")
    @commands.guild_only()
    @prefix_is("!")
    async def work(self, ctx: commands.Context):
        settings = await self.settings(ctx.guild.id)
        reward = random.randint(settings["work_min"], settings["work_max"])
        success, value = await self.bot.db.claim_reward(ctx.guild.id, ctx.author.id, "work", reward, 3600, int(time.time()))
        if not success:
            return await ctx.send(embed=make_embed("Pause bien méritée", f"Tu pourras retravailler dans **{self.format_time(value)}**.", LAVENDER), ephemeral=bool(ctx.interaction))
        await ctx.send(embed=make_embed("Journée productive", f"Tu as gagné **{value:,} {settings['currency_name']}**. Beau travail !", SUCCESS))

    @commands.hybrid_command(name="pay", description="Envoyer des Crédits à un membre du serveur")
    @commands.guild_only()
    @prefix_is("!")
    async def pay(self, ctx: commands.Context, membre: discord.Member, montant: app_commands.Range[int, 1, 1_000_000_000]):
        if membre.bot or membre.id == ctx.author.id:
            return await ctx.send(embed=make_embed("Transfert impossible", "Choisis un autre membre humain du serveur."), ephemeral=bool(ctx.interaction))
        success = await self.bot.db.transfer(ctx.guild.id, ctx.author.id, membre.id, montant)
        if not success:
            return await ctx.send(embed=make_embed("Solde insuffisant", "Le transfert n’a pas été effectué ; vérifie ton portefeuille."), ephemeral=bool(ctx.interaction))
        settings = await self.settings(ctx.guild.id)
        await ctx.send(embed=make_embed("Transfert envoyé", f"{ctx.author.mention} a envoyé **{montant:,} {settings['currency_name']}** à {membre.mention}.", SUCCESS))

    @commands.hybrid_command(name="bank", description="Consulter ton portefeuille et ta banque")
    @commands.guild_only()
    @prefix_is("!")
    async def bank(self, ctx: commands.Context):
        account = await self.bot.db.account(ctx.guild.id, ctx.author.id)
        settings = await self.settings(ctx.guild.id)
        await ctx.send(embed=make_embed("Ta banque", f"⚙️ Portefeuille : **{account['wallet']:,}** {settings['currency_name']}\n🏦 Épargne : **{account['bank']:,}** {settings['currency_name']}\n\nLes intérêts automatiques ne sont pas encore activés.", GLACIER))

    @commands.hybrid_command(name="deposit", description="Déposer des Crédits à la banque")
    @commands.guild_only()
    @prefix_is("!")
    async def deposit(self, ctx: commands.Context, montant: app_commands.Range[int, 1, 1_000_000_000]):
        success = await self.bot.db.bank_move(ctx.guild.id, ctx.author.id, montant, True)
        await ctx.send(embed=make_embed("Dépôt effectué" if success else "Dépôt impossible", f"{montant:,} Crédits ont été déposés." if success else "Vérifie que ton portefeuille contient ce montant.", SUCCESS), ephemeral=(not success or bool(ctx.interaction)))

    @commands.hybrid_command(name="withdraw", description="Retirer des Crédits de la banque")
    @commands.guild_only()
    @prefix_is("!")
    async def withdraw(self, ctx: commands.Context, montant: app_commands.Range[int, 1, 1_000_000_000]):
        success = await self.bot.db.bank_move(ctx.guild.id, ctx.author.id, montant, False)
        await ctx.send(embed=make_embed("Retrait effectué" if success else "Retrait impossible", f"{montant:,} Crédits ont été retirés." if success else "Vérifie que ton compte bancaire contient ce montant.", SUCCESS), ephemeral=(not success or bool(ctx.interaction)))

    @commands.hybrid_command(name="leaderboard", aliases=["top"], description="Voir les dix fortunes liquides du serveur")
    @commands.guild_only()
    @prefix_is("!")
    async def leaderboard(self, ctx: commands.Context):
        rows = await self.bot.db.top_accounts(ctx.guild.id)
        if not rows:
            return await ctx.send(embed=make_embed("Classement", "Les premières fortunes apparaîtront ici bientôt.", LAVENDER))
        lines = [f"**{index}.** <@{row['user_id']}> — **{row['wallet'] + row['bank']:,}** Crédits" for index, row in enumerate(rows, 1)]
        await ctx.send(embed=make_embed("Top 10 des fortunes liquides", "\n".join(lines), LAVENDER))

    @staticmethod
    def format_time(seconds: int) -> str:
        hours, remainder = divmod(max(seconds, 0), 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours} h {minutes} min" if hours else (f"{minutes} min {secs} s" if minutes else f"{secs} s")


async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
