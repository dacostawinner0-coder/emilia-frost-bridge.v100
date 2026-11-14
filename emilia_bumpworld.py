"""
BumpWorld — réseau de serveurs partenaires avec calendrier de bump commun.

Remplace entièrement l'ancien système (points 1 / 0.5, classement par points).
Règles (spécification BumpWorld dédiée) :
  • +bumpset #salon @role — configure le salon et le rôle à mentionner.
  • Affiche les règles avec deux boutons : Accepter / Refuser.
  • Accepté → le serveur rejoint BumpWorld. Refusé → pas d'inscription.
  • Calendrier commun à tous les serveurs (même période pour tout le monde).
  • À chaque période, le bot mentionne automatiquement le rôle configuré
    dans chaque serveur participant.
  • !bump enregistre le bump du serveur pour la période en cours.
  • Après chaque bump, classement des 10 serveurs les plus rapides.
  • Un bouton unique « Afficher les serveurs » → menu déroulant (jusqu'à 10),
    qui envoie le lien d'invitation du serveur choisi en DM.
  • Un seul bump autorisé par serveur et par période.
  • Tout est sauvegardé en base (volume persistant) et restauré au redémarrage.
"""
import time

import discord
from discord.ext import commands, tasks

import emilia_frost as ef
from emilia_frost import bot, connect, frost_embed, fmt_ts, ICE, FROST

PERIOD_SECONDS = 2 * 60 * 60   # 2 heures : calendrier commun à tout BumpWorld
MAX_LISTED_SERVERS = 10
MAX_LEADERBOARD = 10


def now() -> int:
    return int(time.time())


def current_cycle(ts: int = None) -> int:
    return (ts if ts is not None else now()) // PERIOD_SECONDS


def cycle_start(cycle: int) -> int:
    return cycle * PERIOD_SECONDS


def cycle_end(cycle: int) -> int:
    return cycle_start(cycle) + PERIOD_SECONDS


# ══════════════════════════════════════════════════════════════════════
#  BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════════════
def init_bumpworld_db(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS bumpworld_servers (
        guild_id INTEGER PRIMARY KEY,
        guild_name TEXT NOT NULL,
        channel_id INTEGER NOT NULL,
        role_id INTEGER NOT NULL,
        invite_url TEXT,
        invite_channel_id INTEGER,
        active INTEGER NOT NULL DEFAULT 0,
        joined_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bumpworld_bumps (
        cycle INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        bumped_at INTEGER NOT NULL,
        PRIMARY KEY (cycle, guild_id)
    );
    CREATE TABLE IF NOT EXISTS bumpworld_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)
    db.commit()


def _meta_get(db, key, default=None):
    r = db.execute("SELECT value FROM bumpworld_meta WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def _meta_set(db, key, value):
    db.execute("INSERT INTO bumpworld_meta (key, value) VALUES (?,?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
    db.commit()


def is_active(db, guild_id) -> bool:
    r = db.execute("SELECT active FROM bumpworld_servers WHERE guild_id=?", (guild_id,)).fetchone()
    return bool(r and r["active"])


# ══════════════════════════════════════════════════════════════════════
#  INVITATION — créée/validée à l'inscription, régénérée si besoin
# ══════════════════════════════════════════════════════════════════════
async def _ensure_invite(guild: discord.Guild, channel: discord.abc.GuildChannel):
    """Retourne une invitation permanente valide pour ce salon, ou None si impossible."""
    try:
        existing = await channel.invites()
        for inv in existing:
            if inv.max_age == 0 and inv.max_uses == 0 and not inv.temporary:
                return inv.url
        inv = await channel.create_invite(
            max_age=0, max_uses=0, temporary=False, unique=False,
            reason="BumpWorld — lien partagé avec les membres d'autres serveurs")
        return inv.url
    except discord.HTTPException:
        return None


# ══════════════════════════════════════════════════════════════════════
#  INSCRIPTION — +bumpset puis Accepter / Refuser
# ══════════════════════════════════════════════════════════════════════
RULES_TEXT = (
    "**Règles du partenariat BumpWorld**\n\n"
    "• Ton serveur rejoint un réseau commun de serveurs partenaires.\n"
    "• Toutes les **2 heures**, Emilia Frost mentionne ton rôle choisi dans le salon "
    "choisi pour rappeler de faire `!bump`.\n"
    "• Un seul bump compte par serveur et par période.\n"
    "• Après chaque bump, un classement des 10 serveurs les plus rapides est affiché.\n"
    "• Les membres d'autres serveurs pourront voir le tien dans la liste BumpWorld "
    "et recevoir ton lien d'invitation en message privé s'ils le demandent.\n"
    "• Tu peux quitter à tout moment avec `+bumpleave`.\n\n"
    "Acceptes-tu ces règles pour ton serveur ?")


class BumpAcceptView(discord.ui.View):
    def __init__(self, guild_id: int, channel_id: int, role_id: int, author_id: int):
        super().__init__(timeout=300)
        self.guild_id, self.channel_id, self.role_id, self.author_id = (
            guild_id, channel_id, role_id, author_id)

    async def interaction_check(self, inter: discord.Interaction) -> bool:
        if inter.user.id != self.author_id:
            await inter.response.send_message("❄ Seule la personne qui a lancé `+bumpset` peut répondre.",
                                               ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.success)
    async def accept(self, inter: discord.Interaction, button: discord.ui.Button):
        guild = inter.guild
        channel = guild.get_channel(self.channel_id)
        if channel is None:
            await inter.response.edit_message(content="❄ Le salon choisi n'existe plus. Relance `+bumpset`.",
                                              embed=None, view=None)
            return
        invite_url = await _ensure_invite(guild, channel)
        db = connect()
        try:
            db.execute(
                "INSERT INTO bumpworld_servers "
                "(guild_id, guild_name, channel_id, role_id, invite_url, invite_channel_id, active, joined_at) "
                "VALUES (?,?,?,?,?,?,1,?) "
                "ON CONFLICT(guild_id) DO UPDATE SET guild_name=excluded.guild_name, "
                "channel_id=excluded.channel_id, role_id=excluded.role_id, "
                "invite_url=COALESCE(excluded.invite_url, bumpworld_servers.invite_url), "
                "invite_channel_id=excluded.invite_channel_id, active=1",
                (guild.id, guild.name, self.channel_id, self.role_id, invite_url, self.channel_id, now()))
            db.commit()
        finally:
            db.close()
        note = "" if invite_url else ("\n⚠️ Je n'ai pas pu créer de lien d'invitation (vérifie mes permissions "
                                      "sur ce salon) — les autres membres ne pourront pas encore être invités.")
        for child in self.children:
            child.disabled = True
        await inter.response.edit_message(
            content=f"🌍 **{guild.name}** a rejoint BumpWorld !{note}",
            embed=None, view=self)
        self.stop()

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger)
    async def decline(self, inter: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await inter.response.edit_message(content="❄ Inscription annulée. Ton serveur ne rejoint pas BumpWorld.",
                                          embed=None, view=self)
        self.stop()


@bot.command(name="bumpset", help="Configurer et proposer l'inscription à BumpWorld (admins). <#salon> <@rôle>")
async def bumpset(ctx, channel: discord.TextChannel, role: discord.Role):
    if not ef.admin_check(ctx):
        await ctx.send(ef.q("no_perm")); return
    perms = channel.permissions_for(ctx.guild.me)
    if not (perms.send_messages and perms.create_instant_invite):
        await ctx.send("❄ Il me faut la permission d'envoyer des messages et de créer des invitations "
                       f"dans {channel.mention}."); return
    e = frost_embed(title="🌍 Rejoindre BumpWorld ?", desc=RULES_TEXT, color=ICE)
    await ctx.send(embed=e, view=BumpAcceptView(ctx.guild.id, channel.id, role.id, ctx.author.id))


@bot.command(name="bumpleave", help="Quitter BumpWorld (admins).")
async def bumpleave(ctx):
    if not ef.admin_check(ctx):
        await ctx.send(ef.q("no_perm")); return
    db = connect()
    try:
        cur = db.execute("UPDATE bumpworld_servers SET active=0 WHERE guild_id=?", (ctx.guild.id,))
        db.commit()
    finally:
        db.close()
    await ctx.send("👋 Ton serveur a quitté BumpWorld." if cur.rowcount else
                   "❄ Ton serveur n'était pas inscrit à BumpWorld.")


# ══════════════════════════════════════════════════════════════════════
#  !bump — enregistrement + classement de vitesse
# ══════════════════════════════════════════════════════════════════════
async def _leaderboard_embed(db, cycle: int) -> discord.Embed:
    rows = db.execute(
        "SELECT b.guild_id AS guild_id, s.guild_name AS guild_name, b.bumped_at AS bumped_at "
        "FROM bumpworld_bumps b JOIN bumpworld_servers s ON s.guild_id = b.guild_id "
        "WHERE b.cycle=? ORDER BY b.bumped_at ASC LIMIT ?", (cycle, MAX_LEADERBOARD)).fetchall()
    start = cycle_start(cycle)
    if not rows:
        desc = "Personne n'a encore bumpé pour cette période."
    else:
        medal = ["🥇", "🥈", "🥉"]
        lines = []
        for i, r in enumerate(rows):
            tag = medal[i] if i < 3 else f"`{i + 1}.`"
            delay = r["bumped_at"] - start
            lines.append(f"{tag} **{r['guild_name']}** — +{delay // 60} min {delay % 60} s")
        desc = "\n".join(lines)
    return frost_embed(title="🏆 Classement BumpWorld — période en cours", desc=desc, color=FROST)


@bot.command(name="bump", help="Enregistrer le bump de ton serveur pour cette période BumpWorld.")
async def bump_cmd(ctx):
    db = connect()
    try:
        init_bumpworld_db(db)
        if not is_active(db, ctx.guild.id):
            await ctx.send("❄ Ce serveur n'est pas inscrit à BumpWorld. Un admin peut lancer `+bumpset`.")
            return
        cycle = current_cycle()
        ts = now()
        db.execute("UPDATE bumpworld_servers SET guild_name=? WHERE guild_id=?", (ctx.guild.name, ctx.guild.id))
        try:
            db.execute("INSERT INTO bumpworld_bumps (cycle, guild_id, user_id, bumped_at) VALUES (?,?,?,?)",
                       (cycle, ctx.guild.id, ctx.author.id, ts))
            db.commit()
        except Exception:
            db.rollback()
            remaining = cycle_end(cycle) - ts
            await ctx.send(f"❄ Ce serveur a déjà bumpé pour cette période. Prochaine période dans "
                           f"**{remaining // 60} min**.")
            return
        ef.bump_mission(db, ctx.guild.id, ctx.author.id, "bump")
        await ctx.send(f"🚀 Bump enregistré par {ctx.author.mention} — merci !",
                       allowed_mentions=discord.AllowedMentions.none())
        await ctx.send(embed=await _leaderboard_embed(db, cycle))
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════
#  RAPPEL AUTOMATIQUE — même période pour tous les serveurs participants
# ══════════════════════════════════════════════════════════════════════
@tasks.loop(seconds=60)
async def bumpworld_reminder_loop():
    cycle = current_cycle()
    db = connect()
    try:
        init_bumpworld_db(db)
        last = int(_meta_get(db, "last_announced_cycle", "-1"))
        if cycle <= last:
            return
        _meta_set(db, "last_announced_cycle", cycle)
        servers = db.execute("SELECT * FROM bumpworld_servers WHERE active=1").fetchall()
    finally:
        db.close()
    for s in servers:
        guild = bot.get_guild(s["guild_id"])
        if guild is None:
            continue
        channel = guild.get_channel(s["channel_id"])
        role = guild.get_role(s["role_id"])
        if channel is None:
            continue
        try:
            await channel.send(
                content=role.mention if role else None,
                embed=frost_embed(title="⏰ C'est l'heure du bump !",
                                  desc="Tape `!bump` pour faire grimper ton serveur dans BumpWorld.",
                                  color=ICE),
                allowed_mentions=discord.AllowedMentions(roles=[role] if role else False))
        except discord.HTTPException:
            continue


@bumpworld_reminder_loop.before_loop
async def _before_bumpworld_loop():
    await bot.wait_until_ready()


# ══════════════════════════════════════════════════════════════════════
#  « Afficher les serveurs » — menu déroulant, envoie l'invitation en DM
# ══════════════════════════════════════════════════════════════════════
class BumpWorldServerSelect(discord.ui.Select):
    def __init__(self, options_data):
        options = [discord.SelectOption(label=name[:100], value=str(gid))
                   for gid, name in options_data]
        super().__init__(placeholder="Choisis un serveur…", options=options,
                         custom_id="bumpworld_pick_server")

    async def callback(self, inter: discord.Interaction):
        guild_id = int(self.values[0])
        db = connect()
        try:
            row = db.execute("SELECT * FROM bumpworld_servers WHERE guild_id=? AND active=1",
                             (guild_id,)).fetchone()
        finally:
            db.close()
        if not row:
            await inter.response.send_message("❄ Ce serveur n'est plus dans BumpWorld.", ephemeral=True)
            return
        invite_url = row["invite_url"]
        guild = bot.get_guild(guild_id)
        channel = guild.get_channel(row["invite_channel_id"]) if guild else None
        if guild and channel:
            fresh = await _ensure_invite(guild, channel)
            if fresh:
                invite_url = fresh
                db = connect()
                try:
                    db.execute("UPDATE bumpworld_servers SET invite_url=? WHERE guild_id=?",
                              (fresh, guild_id))
                    db.commit()
                finally:
                    db.close()
        if not invite_url:
            await inter.response.send_message("❄ Aucune invitation valide pour ce serveur pour l'instant.",
                                              ephemeral=True)
            return
        try:
            await inter.user.send(f"🌍 Invitation pour **{row['guild_name']}** : {invite_url}")
            await inter.response.send_message("📩 Invitation envoyée en message privé !", ephemeral=True)
        except discord.HTTPException:
            await inter.response.send_message(f"❄ Tes DM sont fermés. Voici le lien : {invite_url}",
                                              ephemeral=True)


class BumpWorldShowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🌍 Afficher les serveurs", style=discord.ButtonStyle.primary,
                       custom_id="bumpworld_show_servers")
    async def show(self, inter: discord.Interaction, button: discord.ui.Button):
        db = connect()
        try:
            init_bumpworld_db(db)
            rows = db.execute(
                "SELECT guild_id, guild_name FROM bumpworld_servers WHERE active=1 "
                "ORDER BY joined_at DESC LIMIT ?", (MAX_LISTED_SERVERS,)).fetchall()
        finally:
            db.close()
        if not rows:
            await inter.response.send_message("❄ Aucun serveur n'est encore inscrit à BumpWorld.",
                                              ephemeral=True)
            return
        view = discord.ui.View(timeout=180)
        view.add_item(BumpWorldServerSelect([(r["guild_id"], r["guild_name"]) for r in rows]))
        await inter.response.send_message(
            f"🌍 **{len(rows)}** serveur(s) dans BumpWorld — choisis-en un pour recevoir son invitation :",
            view=view, ephemeral=True)


@bot.command(name="bumpworld", help="Statut de BumpWorld et liste des serveurs participants.")
async def bumpworld_cmd(ctx):
    db = connect()
    try:
        init_bumpworld_db(db)
        total = db.execute("SELECT COUNT(*) FROM bumpworld_servers WHERE active=1").fetchone()[0]
        mine = is_active(db, ctx.guild.id)
        cycle = current_cycle()
        remaining = cycle_end(cycle) - now()
        already = db.execute("SELECT 1 FROM bumpworld_bumps WHERE cycle=? AND guild_id=?",
                             (cycle, ctx.guild.id)).fetchone()
    finally:
        db.close()
    lines = [f"🌍 **{total}** serveur(s) participent à BumpWorld.",
             f"⏳ Prochaine période dans **{remaining // 60} min**.",
             f"Ce serveur : {'✅ inscrit' if mine else '❄ non inscrit (`+bumpset`)'}"]
    if mine:
        lines.append("Bump de cette période : " + ("✅ déjà fait" if already else "⏳ pas encore, tape `!bump`"))
    e = frost_embed(title="🌍 BumpWorld", desc="\n".join(lines), color=ICE)
    await ctx.send(embed=e, view=BumpWorldShowView())


def register_persistent_views():
    bot.add_view(BumpWorldShowView())


def start_loop():
    if not bumpworld_reminder_loop.is_running():
        bumpworld_reminder_loop.start()
