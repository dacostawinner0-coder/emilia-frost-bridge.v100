from __future__ import annotations

import json
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from ui import ERROR, LAVENDER, SUCCESS, make_embed


def staff_prefix(ctx: commands.Context) -> bool:
    return ctx.interaction is not None or ctx.prefix == "+"


class ModerationCog(commands.Cog):
    """Guild-scoped moderation; +ban is the project's role-ban, not Discord ban."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _target_check(self, ctx: commands.Context, target: discord.Member) -> bool:
        guild = ctx.guild
        if target.id == guild.owner_id or target.id == self.bot.user.id:
            await ctx.send(embed=make_embed("Cible protégée", "Le propriétaire du serveur et Emilia ne peuvent pas être sanctionnés.", ERROR), ephemeral=bool(ctx.interaction))
            return False
        if ctx.author.id != guild.owner_id and ctx.author.top_role <= target.top_role:
            await ctx.send(embed=make_embed("Hiérarchie insuffisante", "Tu ne peux pas intervenir sur un membre de rang égal ou supérieur au tien.", ERROR), ephemeral=bool(ctx.interaction))
            return False
        if guild.me is None or guild.me.top_role <= target.top_role:
            await ctx.send(embed=make_embed("Rôle du bot trop bas", "Place le rôle d’Emilia au-dessus du membre cible.", ERROR), ephemeral=bool(ctx.interaction))
            return False
        return True

    async def _can_moderate(self, ctx: commands.Context, permission: str) -> bool:
        if not getattr(ctx.author.guild_permissions, permission, False):
            await ctx.send(embed=make_embed("Accès staff requis", "La permission Discord adaptée est nécessaire.", ERROR), ephemeral=bool(ctx.interaction))
            return False
        return True

    async def _log(self, ctx: commands.Context, target: discord.Member, action: str, reason: str):
        case_id = await self.bot.db.add_case(ctx.guild.id, target.id, ctx.author.id, action, reason)
        settings = await self.bot.db.ensure_guild(ctx.guild.id)
        if settings["log_channel_id"]:
            channel = ctx.guild.get_channel(int(settings["log_channel_id"]))
            if channel and hasattr(channel, "send"):
                embed = make_embed(f"Modération · {action} · #{case_id}", f"**Membre :** {target.mention}\n**Staff :** {ctx.author.mention}\n**Motif :** {reason or 'Non précisé'}", ERROR)
                await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="warn", description="Enregistrer un avertissement")
    @commands.guild_only()
    @commands.check(staff_prefix)
    async def warn(self, ctx: commands.Context, membre: discord.Member, *, motif: str = "Non précisé"):
        if not await self._can_moderate(ctx, "moderate_members") or not await self._target_check(ctx, membre):
            return
        await self._log(ctx, membre, "Avertissement", motif)
        await ctx.send(embed=make_embed("Avertissement enregistré", f"{membre.mention} — **Motif :** {motif}", SUCCESS))

    @commands.hybrid_command(name="warnings", description="Consulter les avertissements récents")
    @commands.guild_only()
    @commands.check(staff_prefix)
    async def warnings(self, ctx: commands.Context, membre: discord.Member):
        if not await self._can_moderate(ctx, "moderate_members"):
            return
        rows = [row for row in await self.bot.db.cases(ctx.guild.id, membre.id) if row["action"] == "Avertissement"]
        lines = [f"• #{row['id']} — {row['reason'] or 'Sans motif'} (<t:{row['created_at']}:R>)" for row in rows]
        await ctx.send(embed=make_embed(f"Historique de {membre.display_name}", "\n".join(lines) or "Aucun avertissement enregistré.", LAVENDER), ephemeral=bool(ctx.interaction))

    @commands.hybrid_command(name="timeout", description="Appliquer un timeout Discord")
    @commands.guild_only()
    @commands.check(staff_prefix)
    async def timeout(self, ctx: commands.Context, membre: discord.Member, minutes: app_commands.Range[int, 1, 40320], *, motif: str = "Non précisé"):
        if not await self._can_moderate(ctx, "moderate_members") or not await self._target_check(ctx, membre):
            return
        await membre.timeout(timedelta(minutes=minutes), reason=motif)
        await self._log(ctx, membre, "Timeout", motif)
        await ctx.send(embed=make_embed("Timeout appliqué", f"{membre.mention} est en timeout pour **{minutes} min**.\n**Motif :** {motif}", SUCCESS))

    @commands.hybrid_command(name="kick", description="Expulser un membre du serveur")
    @commands.guild_only()
    @commands.check(staff_prefix)
    async def kick(self, ctx: commands.Context, membre: discord.Member, *, motif: str = "Non précisé"):
        if not await self._can_moderate(ctx, "kick_members") or not await self._target_check(ctx, membre):
            return
        await self._log(ctx, membre, "Expulsion", motif)
        await membre.kick(reason=motif)
        await ctx.send(embed=make_embed("Membre expulsé", f"{membre} a été expulsé. Motif : {motif}", SUCCESS))

    @commands.hybrid_command(name="ban", description="Appliquer le role-ban interne Emilia Frost")
    @commands.guild_only()
    @commands.check(staff_prefix)
    async def ban(self, ctx: commands.Context, membre: discord.Member, *, motif: str = "Non précisé"):
        if not await self._can_moderate(ctx, "manage_roles") or not await self._target_check(ctx, membre):
            return
        settings = await self.bot.db.ensure_guild(ctx.guild.id)
        if not settings["ban_role_id"]:
            return await ctx.send(embed=make_embed("Role-ban non configuré", "Un administrateur doit lancer `+setbanrole @rôle`.", LAVENDER), ephemeral=bool(ctx.interaction))
        role = ctx.guild.get_role(int(settings["ban_role_id"]))
        if role is None or role >= ctx.guild.me.top_role:
            return await ctx.send(embed=make_embed("Configuration invalide", "Le rôle de restriction doit exister sous le rôle du bot.", ERROR), ephemeral=bool(ctx.interaction))
        previous_roles = [str(item.id) for item in membre.roles if item != ctx.guild.default_role]
        async with await self.bot.db.connect() as db:
            await db.execute("BEGIN IMMEDIATE")
            await db.execute("INSERT INTO role_bans(guild_id,user_id,roles_json,moderator_id,reason) VALUES (?,?,?,?,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET roles_json=excluded.roles_json,moderator_id=excluded.moderator_id,reason=excluded.reason", (str(ctx.guild.id), str(membre.id), json.dumps(previous_roles), str(ctx.author.id), motif[:1000]))
            await db.commit()
        removable = [item for item in membre.roles if item != ctx.guild.default_role and item < ctx.guild.me.top_role]
        if removable:
            await membre.remove_roles(*removable, reason=f"Role-ban Emilia Frost: {motif}")
        await membre.add_roles(role, reason=f"Role-ban Emilia Frost: {motif}")
        await self._log(ctx, membre, "Role-ban interne", motif)
        await ctx.send(embed=make_embed("Role-ban appliqué", f"{membre.mention} reçoit le rôle de restriction configuré. Ce n’est pas un ban Discord natif.", SUCCESS))

    @commands.hybrid_command(name="unban", description="Retirer le role-ban interne")
    @commands.guild_only()
    @commands.check(staff_prefix)
    async def unban(self, ctx: commands.Context, membre: discord.Member):
        if not await self._can_moderate(ctx, "manage_roles"):
            return
        async with await self.bot.db.connect() as db:
            row = await (await db.execute("SELECT roles_json FROM role_bans WHERE guild_id=? AND user_id=?", (str(ctx.guild.id), str(membre.id)))).fetchone()
            if row is None:
                return await ctx.send(embed=make_embed("Aucun role-ban", "Ce membre n’a pas de role-ban interne actif.", LAVENDER), ephemeral=bool(ctx.interaction))
            await db.execute("DELETE FROM role_bans WHERE guild_id=? AND user_id=?", (str(ctx.guild.id), str(membre.id)))
            await db.commit()
        settings = await self.bot.db.ensure_guild(ctx.guild.id)
        ban_role = ctx.guild.get_role(int(settings["ban_role_id"])) if settings["ban_role_id"] else None
        if ban_role and ban_role in membre.roles:
            await membre.remove_roles(ban_role, reason="Fin du role-ban interne")
        restore = [ctx.guild.get_role(int(role_id)) for role_id in json.loads(row["roles_json"])]
        restore = [item for item in restore if item and item < ctx.guild.me.top_role]
        if restore:
            await membre.add_roles(*restore, reason="Restauration après role-ban Emilia Frost")
        await self._log(ctx, membre, "Fin du role-ban interne", "Rôles existants autorisés restaurés")
        await ctx.send(embed=make_embed("Role-ban levé", f"Les rôles existants et toujours autorisés de {membre.mention} ont été restaurés.", SUCCESS))

    @commands.hybrid_command(name="discordban", description="Appliquer un ban natif Discord")
    @commands.guild_only()
    @commands.check(staff_prefix)
    async def discordban(self, ctx: commands.Context, membre: discord.Member, *, motif: str = "Non précisé"):
        if not await self._can_moderate(ctx, "ban_members") or not await self._target_check(ctx, membre):
            return
        await self._log(ctx, membre, "Ban Discord natif", motif)
        await membre.ban(reason=motif)
        await ctx.send(embed=make_embed("Ban Discord appliqué", f"{membre} a été banni de Discord. Ce comportement est distinct de `+ban`.", SUCCESS))

    @commands.hybrid_command(name="setbanrole", description="Configurer le rôle de restriction du role-ban")
    @commands.guild_only()
    @commands.check(staff_prefix)
    async def setbanrole(self, ctx: commands.Context, role: discord.Role):
        if not await self._can_moderate(ctx, "manage_guild"):
            return
        if role >= ctx.guild.me.top_role or role == ctx.guild.default_role:
            return await ctx.send(embed=make_embed("Rôle inutilisable", "Le rôle doit rester sous celui d’Emilia et ne peut pas être @everyone.", ERROR), ephemeral=bool(ctx.interaction))
        async with await self.bot.db.connect() as db:
            await db.execute("INSERT INTO guild_settings(guild_id,ban_role_id) VALUES (?,?) ON CONFLICT(guild_id) DO UPDATE SET ban_role_id=excluded.ban_role_id,updated_at=unixepoch()", (str(ctx.guild.id), str(role.id)))
            await db.commit()
        await ctx.send(embed=make_embed("Rôle configuré", f"Le role-ban interne utilisera {role.mention}.", SUCCESS))

    @commands.hybrid_command(name="setlog", description="Configurer le salon des journaux de modération")
    @commands.guild_only()
    @commands.check(staff_prefix)
    async def setlog(self, ctx: commands.Context, salon: discord.TextChannel):
        if not await self._can_moderate(ctx, "manage_guild"):
            return
        async with await self.bot.db.connect() as db:
            await db.execute("INSERT INTO guild_settings(guild_id,log_channel_id) VALUES (?,?) ON CONFLICT(guild_id) DO UPDATE SET log_channel_id=excluded.log_channel_id,updated_at=unixepoch()", (str(ctx.guild.id), str(salon.id)))
            await db.commit()
        await ctx.send(embed=make_embed("Journal configuré", f"Les actions de modération seront consignées dans {salon.mention}.", SUCCESS))

    @commands.hybrid_command(name="clear", description="Supprimer des messages récents")
    @commands.guild_only()
    @commands.check(staff_prefix)
    async def clear(self, ctx: commands.Context, nombre: app_commands.Range[int, 1, 100]):
        if not await self._can_moderate(ctx, "manage_messages"):
            return
        if not isinstance(ctx.channel, discord.TextChannel):
            return await ctx.send(embed=make_embed("Salon incompatible", "Utilise cette commande dans un salon texte.", ERROR), ephemeral=bool(ctx.interaction))
        deleted = await ctx.channel.purge(limit=nombre + (0 if ctx.interaction else 1))
        count = max(len(deleted) - (0 if ctx.interaction else 1), 0)
        await ctx.send(embed=make_embed("Salon rafraîchi", f"**{count}** message(s) supprimé(s).", SUCCESS), ephemeral=bool(ctx.interaction), delete_after=None if ctx.interaction else 8)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
