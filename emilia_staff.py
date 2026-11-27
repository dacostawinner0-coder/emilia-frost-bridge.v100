"""
Rangs du staff (niveaux 1 à 10, avec branches multiples par niveau) + recrutement
automatique complet.

RANGS
  • +rolestaff <niveau> <branche> <@rôle> — associe un rôle à un niveau+branche
    (plusieurs branches possibles au même niveau, ex: 7 moderation / 7 animation).
  • +rolestaffremove <niveau> <branche> — retire une branche.
  • +rolestaffcap <niveau> <branche> <nombre> — limite de places (0 = illimité).
  • +rolestaffwaitrole <@rôle> — rôle de repli quand une branche est pleine.
  • +showstaffconfig — vue d'ensemble de toute la configuration.
  • +staffweights <message> <ticket> <vocal> <modération> — poids de chaque source de points.
  • +staffthreshold <niveau> <seuil> — seuil précis pour un niveau (sinon calcul automatique).
  • +staffactivitywindow <jours> — fenêtre d'activité récente jugée pour le derank auto.
  • +staffderank on|off — activer/couper le derank automatique hebdomadaire.
  • +staffprotect / +staffunprotect <@membre> — exempter du derank auto.
  • +staffup / +staffdown <@membre> [niveau] [branche] — forcer monter/descendre (admins).
  • +staffremove <@membre> — sortir complètement du staff (retire tous les rôles liés).
  • +staffinfo <@membre> — stats détaillées de n'importe quel membre du staff (admins).
  • +staffboard — tableau de tout le staff actuel.
  • !staffstats — ses propres stats, avec barre de progression ; bouton (ou menu si
    plusieurs branches possibles) pour monter de grade si les conditions sont remplies.

Points gagnés en : écrivant des messages, en vocal, en traitant des tickets, et en
modérant (mute/kick/ban/clear/lock/unlock/warn). Les poids sont configurables.

Chaque semaine, le bot vérifie l'activité RÉCENTE (fenêtre configurable) de chaque
membre du staff ; si elle ne suffit plus pour son niveau actuel, il redescend d'un
cran automatiquement (sauf s'il est protégé ou si le derank auto est coupé), avec un
MP expliquant pourquoi.

Quand un rôle staff général ou un rôle de niveau est lié, le bot synchronise les
membres qui l'ont déjà (DM avec leur XP / niveau assigné rétroactivement).

RECRUTEMENT
  • +recrutsetup #salon — panneau de candidature (bouton persistant, icône du serveur).
  • +recrutrole / +recrutquestion — configuration (le log passe par +setlogadmin, voir
    emilia_extra, pour éviter un salon dédié en plus).
  • +recrutcooldown <jours> — délai avant de pouvoir recandidater après un refus.
  • +recrutlist — candidatures en cours.
  • !recrutstatut — un candidat suit l'état de sa propre candidature.
  • Flux : Candidater → questions en DM → log avancé (ping staff) → Tester (admin) →
    ticket → Accepter (rôle staff + niveau 1, branche par défaut) / Refuser.
"""
import asyncio
import json
import time

import discord
from discord.ext import commands, tasks

import emilia_frost as ef
from emilia_frost import bot, connect, frost_embed, q, ICE, FROST, EXCL, RED

MAX_LEVEL = 10
LEVEL_BASE = 300          # progression quadratique par défaut : level*level*LEVEL_BASE
DEFAULT_BRANCH = "defaut"
DEFAULT_WEIGHTS = {"message": 1, "ticket": 25, "voice": 2, "moderation": 15}
DEFAULT_WINDOW_DAYS = 30
WEEK_SECONDS = 7 * 24 * 60 * 60


def now() -> int:
    return int(time.time())


# ══════════════════════════════════════════════════════════════════════
#  BASE DE DONNÉES — création + migrations douces (ne perdent aucune donnée)
# ══════════════════════════════════════════════════════════════════════
def init_staff_db(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS staff_rank_roles (
        guild_id INTEGER NOT NULL, level INTEGER NOT NULL, branch TEXT NOT NULL DEFAULT 'defaut',
        role_id INTEGER NOT NULL, label TEXT, cap INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, level, branch)
    );
    CREATE TABLE IF NOT EXISTS staff_points (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        messages INTEGER NOT NULL DEFAULT 0,
        tickets INTEGER NOT NULL DEFAULT 0,
        voice_minutes INTEGER NOT NULL DEFAULT 0,
        moderation INTEGER NOT NULL DEFAULT 0,
        level INTEGER NOT NULL DEFAULT 0,
        branch TEXT NOT NULL DEFAULT 'defaut',
        protected INTEGER NOT NULL DEFAULT 0,
        last_change_at INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS staff_activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        kind TEXT NOT NULL, points INTEGER NOT NULL, ts INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS staff_voice_sessions (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, joined_at INTEGER NOT NULL,
        PRIMARY KEY (guild_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS recruit_config (
        guild_id INTEGER PRIMARY KEY,
        panel_channel_id INTEGER, log_channel_id INTEGER,
        staff_role_id INTEGER, first_level_role_id INTEGER,
        cooldown_days INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS recruit_questions (
        guild_id INTEGER NOT NULL, position INTEGER NOT NULL, question TEXT NOT NULL,
        PRIMARY KEY (guild_id, position)
    );
    CREATE TABLE IF NOT EXISTS recruit_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'in_progress',
        answers TEXT NOT NULL DEFAULT '[]',
        current_question INTEGER NOT NULL DEFAULT 0,
        log_message_id INTEGER, log_channel_id INTEGER,
        ticket_channel_id INTEGER, tester_id INTEGER,
        created_at INTEGER NOT NULL, decided_at INTEGER
    );
    """)
    db.commit()
    # migrations douces sur des tables déjà existantes avant cette version
    _ensure_column(db, "staff_points", "moderation", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "staff_points", "branch", "TEXT NOT NULL DEFAULT 'defaut'")
    _ensure_column(db, "staff_points", "protected", "INTEGER NOT NULL DEFAULT 0")
    _migrate_staff_rank_roles(db)
    _ensure_column(db, "recruit_config", "cooldown_days", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "recruit_applications", "decided_at", "INTEGER")
    db.commit()


def _ensure_column(db, table, column, decl):
    cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _migrate_staff_rank_roles(db):
    """L'ancienne table avait PRIMARY KEY (guild_id, level) ; la nouvelle a besoin de
    (guild_id, level, branch) pour autoriser plusieurs branches au même niveau. Une simple
    colonne ajoutée ne change pas la clé primaire — il faut reconstruire la table."""
    cols = [r[1] for r in db.execute("PRAGMA table_info(staff_rank_roles)").fetchall()]
    if "branch" in cols and "cap" in cols:
        pk_cols = [r[1] for r in db.execute("PRAGMA table_info(staff_rank_roles)").fetchall() if r[5] > 0]
        if set(pk_cols) == {"guild_id", "level", "branch"}:
            return  # déjà la bonne structure
    db.execute("ALTER TABLE staff_rank_roles RENAME TO staff_rank_roles_old")
    db.execute("""CREATE TABLE staff_rank_roles (
        guild_id INTEGER NOT NULL, level INTEGER NOT NULL, branch TEXT NOT NULL DEFAULT 'defaut',
        role_id INTEGER NOT NULL, label TEXT, cap INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, level, branch)
    )""")
    old_cols = [r[1] for r in db.execute("PRAGMA table_info(staff_rank_roles_old)").fetchall()]
    branch_expr = "branch" if "branch" in old_cols else "'defaut'"
    cap_expr = "cap" if "cap" in old_cols else "0"
    db.execute(f"INSERT OR IGNORE INTO staff_rank_roles (guild_id, level, branch, role_id, label, cap) "
               f"SELECT guild_id, level, {branch_expr}, role_id, label, {cap_expr} FROM staff_rank_roles_old")
    db.execute("DROP TABLE staff_rank_roles_old")
    db.commit()


# ── réglages par serveur (réutilise la table config générique d'emilia_frost) ──
def _weights(db, guild_id):
    raw = ef.config_get(db, guild_id, "staff_weights")
    if raw:
        try:
            w = json.loads(raw)
            return {**DEFAULT_WEIGHTS, **w}
        except (TypeError, ValueError):
            pass
    return dict(DEFAULT_WEIGHTS)


def _window_days(db, guild_id):
    v = ef.config_get(db, guild_id, "staff_activity_window_days")
    try:
        return max(1, int(v)) if v else DEFAULT_WINDOW_DAYS
    except ValueError:
        return DEFAULT_WINDOW_DAYS


def _autoderank_enabled(db, guild_id):
    return (ef.config_get(db, guild_id, "staff_autoderank", "1") or "1") == "1"


def level_threshold(db, guild_id, level: int) -> int:
    override = ef.config_get(db, guild_id, f"staff_threshold_{level}")
    if override:
        try:
            return int(override)
        except ValueError:
            pass
    return level * level * LEVEL_BASE


def score_of(db, guild_id, row) -> int:
    w = _weights(db, guild_id)
    return (row["messages"] * w["message"] + row["tickets"] * w["ticket"] +
            row["voice_minutes"] * w["voice"] + row["moderation"] * w["moderation"])


def recent_score(db, guild_id, user_id, days: int) -> int:
    since = now() - days * 86400
    r = db.execute("SELECT COALESCE(SUM(points),0) FROM staff_activity_log "
                   "WHERE guild_id=? AND user_id=? AND ts>=?", (guild_id, user_id, since)).fetchone()
    return r[0] or 0


def get_points(db, guild_id, user_id):
    db.execute("INSERT OR IGNORE INTO staff_points (guild_id, user_id, last_change_at) VALUES (?,?,?)",
               (guild_id, user_id, now()))
    db.commit()
    return db.execute("SELECT * FROM staff_points WHERE guild_id=? AND user_id=?",
                      (guild_id, user_id)).fetchone()


def branches_at(db, guild_id, level):
    return db.execute("SELECT * FROM staff_rank_roles WHERE guild_id=? AND level=? ORDER BY branch",
                      (guild_id, level)).fetchall()


def rank_role(db, guild_id, level, branch=DEFAULT_BRANCH):
    return db.execute("SELECT * FROM staff_rank_roles WHERE guild_id=? AND level=? AND branch=?",
                      (guild_id, level, branch)).fetchone()


def recruit_cfg(db, guild_id):
    return db.execute("SELECT * FROM recruit_config WHERE guild_id=?", (guild_id,)).fetchone()


def is_staff_member(db, guild_id, member: discord.Member) -> bool:
    cfg = recruit_cfg(db, guild_id)
    if cfg and cfg["staff_role_id"]:
        role = member.guild.get_role(cfg["staff_role_id"])
        if role and role in member.roles:
            return True
    ranks = db.execute("SELECT role_id FROM staff_rank_roles WHERE guild_id=?", (guild_id,)).fetchall()
    held = {r.id for r in member.roles}
    return any(r["role_id"] in held for r in ranks)


def _is_admin_member(member: discord.Member) -> bool:
    """Équivalent de ef.admin_check(ctx) mais à partir d'un Member (boutons d'interaction)."""
    g = member.guild
    if member.id == ef.OWNER_ID or g.owner_id == member.id:
        return True
    if member.guild_permissions.administrator:
        return True
    db = connect()
    try:
        admin_role = ef.config_get(db, g.id, "admin_role_id")
    finally:
        db.close()
    if admin_role:
        return any(r.id == int(admin_role) for r in member.roles)
    return False


# ══════════════════════════════════════════════════════════════════════
#  QUOTAS — rôle plein → rôle de repli configurable
# ══════════════════════════════════════════════════════════════════════
def _branch_count(db, guild_id, level, branch, exclude_user_id=None):
    r = db.execute("SELECT COUNT(*) FROM staff_points WHERE guild_id=? AND level=? AND branch=? "
                   "AND user_id != COALESCE(?, -1)", (guild_id, level, branch, exclude_user_id)).fetchone()
    return r[0] or 0


def _wait_role(db, guild_id):
    rid = ef.config_get(db, guild_id, "staff_wait_role_id")
    return int(rid) if rid else None


async def _assign_branch_role(db, member: discord.Member, level, branch, old_level, old_branch):
    """Retire l'ancien rôle de niveau, pose le nouveau (ou le rôle d'attente si plein)."""
    guild_id = member.guild.id
    old_r = rank_role(db, guild_id, old_level, old_branch) if old_level else None
    new_r = rank_role(db, guild_id, level, branch) if level else None
    wait_id = _wait_role(db, guild_id)
    wait_role = member.guild.get_role(wait_id) if wait_id else None
    placed_on_wait = False
    try:
        if old_r:
            role = member.guild.get_role(old_r["role_id"])
            if role and role in member.roles:
                await member.remove_roles(role, reason="Changement de niveau staff")
        if wait_role and wait_role in member.roles:
            await member.remove_roles(wait_role, reason="Changement de niveau staff")
        if new_r:
            cap = new_r["cap"] or 0
            full = cap > 0 and _branch_count(db, guild_id, level, branch, exclude_user_id=member.id) >= cap
            if full and wait_role:
                await member.add_roles(wait_role, reason="Branche pleine : rôle d'attente")
                placed_on_wait = True
            else:
                role = member.guild.get_role(new_r["role_id"])
                if role and role not in member.roles:
                    await member.add_roles(role, reason="Changement de niveau staff")
    except discord.HTTPException:
        pass
    return placed_on_wait


# ══════════════════════════════════════════════════════════════════════
#  GAIN DE POINTS — messages, vocal, tickets, modération
# ══════════════════════════════════════════════════════════════════════
def _bump_points(db, guild_id, user_id, column, amount, kind):
    w = _weights(db, guild_id)
    db.execute(f"INSERT INTO staff_points (guild_id, user_id, {column}, last_change_at) VALUES (?,?,?,?) "
               f"ON CONFLICT(guild_id, user_id) DO UPDATE SET {column}={column}+excluded.{column}, "
               "last_change_at=excluded.last_change_at", (guild_id, user_id, amount, now()))
    db.execute("INSERT INTO staff_activity_log (guild_id, user_id, kind, points, ts) VALUES (?,?,?,?,?)",
              (guild_id, user_id, kind, amount * w.get(kind, 1), now()))
    db.commit()


@bot.listen("on_message")
async def _staff_points_on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return
    db = connect()
    try:
        init_staff_db(db)
        if not is_staff_member(db, message.guild.id, message.author):
            return
        _bump_points(db, message.guild.id, message.author.id, "messages", 1, "message")
    finally:
        db.close()


@bot.listen("on_voice_state_update")
async def _staff_points_on_voice(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot:
        return
    db = connect()
    try:
        init_staff_db(db)
        if before.channel is None and after.channel is not None:
            db.execute("INSERT INTO staff_voice_sessions (guild_id, user_id, joined_at) VALUES (?,?,?) "
                       "ON CONFLICT(guild_id, user_id) DO UPDATE SET joined_at=excluded.joined_at",
                       (member.guild.id, member.id, now()))
            db.commit()
        elif before.channel is not None and after.channel is None:
            row = db.execute("SELECT joined_at FROM staff_voice_sessions WHERE guild_id=? AND user_id=?",
                             (member.guild.id, member.id)).fetchone()
            db.execute("DELETE FROM staff_voice_sessions WHERE guild_id=? AND user_id=?",
                      (member.guild.id, member.id))
            db.commit()
            if row and is_staff_member(db, member.guild.id, member):
                minutes = max(0, (now() - row["joined_at"]) // 60)
                if minutes:
                    _bump_points(db, member.guild.id, member.id, "voice_minutes", minutes, "voice")
    finally:
        db.close()


@bot.listen("on_emilia_ticket_closed")
async def _staff_points_on_ticket(guild_id, staff_id):
    if not staff_id:
        return
    db = connect()
    try:
        init_staff_db(db)
        _bump_points(db, guild_id, staff_id, "tickets", 1, "ticket")
    finally:
        db.close()


@bot.listen("on_emilia_staff_action")
async def _staff_points_on_moderation(guild_id, staff_id):
    """Points de modération : déclenché par mute/kick/ban/clear/lock/unlock/warn (emilia_frost.py)."""
    if not staff_id:
        return
    db = connect()
    try:
        init_staff_db(db)
        _bump_points(db, guild_id, staff_id, "moderation", 1, "moderation")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════
#  COMMANDES — configuration des niveaux / branches / quotas
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="rolestaff",
             help="Associer un rôle à un niveau+branche de staff 1-10 (admins). <niveau> <branche> <@rôle>")
async def rolestaff(ctx, level: int, branch: str, role: discord.Role):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    if not (1 <= level <= MAX_LEVEL):
        await ctx.send(f"❄ Le niveau doit être entre 1 et {MAX_LEVEL}."); return
    branch = branch.lower().strip()[:50]
    db = connect()
    try:
        init_staff_db(db)
        db.execute("INSERT INTO staff_rank_roles (guild_id, level, branch, role_id, label) VALUES (?,?,?,?,?) "
                   "ON CONFLICT(guild_id, level, branch) DO UPDATE SET role_id=excluded.role_id, "
                   "label=excluded.label", (ctx.guild.id, level, branch, role.id, role.name))
        db.commit()
        # synchronisation rétroactive : qui a déjà ce rôle ?
        synced = 0
        for member in ctx.guild.members:
            if role in member.roles:
                row = get_points(db, ctx.guild.id, member.id)
                if row["level"] != level or row["branch"] != branch:
                    db.execute("UPDATE staff_points SET level=?, branch=? WHERE guild_id=? AND user_id=?",
                              (level, branch, ctx.guild.id, member.id))
                    db.commit()
                    synced += 1
        threshold = level_threshold(db, ctx.guild.id, level)
    finally:
        db.close()
    extra = f" **{synced}** membre(s) déjà en possession du rôle synchronisé(s)." if synced else ""
    await ctx.send(f"✅ Niveau **{level}** / branche **{branch}** → {role.mention} "
                   f"(seuil : **{threshold}** points).{extra}",
                   allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="rolestaffremove", help="Retirer une branche d'un niveau (admins). <niveau> <branche>")
async def rolestaffremove(ctx, level: int, branch: str):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        cur = db.execute("DELETE FROM staff_rank_roles WHERE guild_id=? AND level=? AND branch=?",
                        (ctx.guild.id, level, branch.lower().strip()))
        db.commit()
    finally:
        db.close()
    await ctx.send(f"🗑️ Branche retirée." if cur.rowcount else "❄ Introuvable.")


@bot.command(name="rolestaffcap", help="Limiter le nombre de places d'une branche, 0=illimité (admins). <niveau> <branche> <nombre>")
async def rolestaffcap(ctx, level: int, branch: str, cap: int):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    if cap < 0:
        await ctx.send("❄ Nombre invalide."); return
    db = connect()
    try:
        cur = db.execute("UPDATE staff_rank_roles SET cap=? WHERE guild_id=? AND level=? AND branch=?",
                        (cap, ctx.guild.id, level, branch.lower().strip()))
        db.commit()
    finally:
        db.close()
    if not cur.rowcount:
        await ctx.send("❄ Niveau/branche introuvable — crée-le d'abord avec `+rolestaff`."); return
    await ctx.send(f"✅ Limite : **{cap if cap else 'illimité'}** place(s).")


@bot.command(name="rolestaffwaitrole", help="Rôle de repli quand une branche est pleine (admins). <@rôle>")
async def rolestaffwaitrole(ctx, role: discord.Role):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        ef.config_set(db, ctx.guild.id, "staff_wait_role_id", role.id)
    finally:
        db.close()
    await ctx.send(f"✅ Rôle d'attente → {role.mention}.", allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="staffweights",
             help="Poids des sources de points (admins). <message> <ticket> <vocal> <modération>")
async def staffweights(ctx, message: int, ticket: int, voice: int, moderation: int):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    if min(message, ticket, voice, moderation) < 0:
        await ctx.send("❄ Les poids doivent être positifs."); return
    db = connect()
    try:
        ef.config_set(db, ctx.guild.id, "staff_weights",
                      json.dumps({"message": message, "ticket": ticket, "voice": voice, "moderation": moderation}))
    finally:
        db.close()
    await ctx.send(f"✅ Poids : message **{message}**, ticket **{ticket}**, vocal **{voice}**/min, "
                   f"modération **{moderation}**.")


@bot.command(name="staffthreshold", help="Seuil précis d'un niveau, vide = calcul automatique (admins). <niveau> [seuil]")
async def staffthreshold(ctx, level: int, threshold: int = None):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        if threshold is None:
            ef.config_set(db, ctx.guild.id, f"staff_threshold_{level}", "")
            msg = f"✅ Niveau **{level}** : retour au calcul automatique ({level * level * LEVEL_BASE} points)."
        else:
            ef.config_set(db, ctx.guild.id, f"staff_threshold_{level}", threshold)
            msg = f"✅ Niveau **{level}** : seuil fixé à **{threshold}** points."
    finally:
        db.close()
    await ctx.send(msg)


@bot.command(name="staffactivitywindow", help="Fenêtre d'activité récente jugée pour le derank auto, en jours (admins). <jours>")
async def staffactivitywindow(ctx, days: int):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    if days < 1:
        await ctx.send("❄ Au moins 1 jour."); return
    db = connect()
    try:
        ef.config_set(db, ctx.guild.id, "staff_activity_window_days", days)
    finally:
        db.close()
    await ctx.send(f"✅ Fenêtre d'activité : **{days} jour(s)**.")


@bot.command(name="staffderank", help="Activer/couper le derank automatique hebdomadaire (admins). on | off")
async def staffderank_toggle(ctx, state: str):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    state = state.lower().strip()
    if state not in ("on", "off"):
        await ctx.send("❄ Utilise `on` ou `off`."); return
    db = connect()
    try:
        ef.config_set(db, ctx.guild.id, "staff_autoderank", "1" if state == "on" else "0")
    finally:
        db.close()
    await ctx.send(f"✅ Derank automatique : **{'activé' if state == 'on' else 'coupé'}**.")


@bot.command(name="staffprotect", help="Exempter un membre du derank automatique (admins). <@membre>")
async def staffprotect(ctx, member: discord.Member):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        get_points(db, ctx.guild.id, member.id)
        db.execute("UPDATE staff_points SET protected=1 WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
        db.commit()
    finally:
        db.close()
    await ctx.send(f"🛡️ {member.mention} est protégé(e) du derank automatique.",
                   allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="staffunprotect", help="Retirer la protection contre le derank automatique (admins). <@membre>")
async def staffunprotect(ctx, member: discord.Member):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        db.execute("UPDATE staff_points SET protected=0 WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
        db.commit()
    finally:
        db.close()
    await ctx.send(f"✅ Protection retirée pour {member.mention}.", allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="showstaffconfig", help="Vue d'ensemble de la configuration du staff (admins).")
async def showstaffconfig(ctx):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        init_staff_db(db)
        rows = db.execute("SELECT * FROM staff_rank_roles WHERE guild_id=? ORDER BY level, branch",
                         (ctx.guild.id,)).fetchall()
        w = _weights(db, ctx.guild.id)
        window = _window_days(db, ctx.guild.id)
        derank_on = _autoderank_enabled(db, ctx.guild.id)
        wait_id = _wait_role(db, ctx.guild.id)
    finally:
        db.close()
    lines = []
    for r in rows:
        role = ctx.guild.get_role(r["role_id"])
        cap_txt = f"{r['cap']} place(s)" if r["cap"] else "illimité"
        lines.append(f"**Niv. {r['level']}** / {r['branch']} → {role.mention if role else '*(rôle supprimé)*'} "
                     f"({cap_txt})")
    wait_role = ctx.guild.get_role(wait_id) if wait_id else None
    e = frost_embed(title="🏅 Configuration du staff", color=FROST, fields=[
        ("Niveaux / branches", "\n".join(lines) or "Aucun configuré", False),
        ("Poids", f"message {w['message']} · ticket {w['ticket']} · vocal {w['voice']}/min · "
                  f"modération {w['moderation']}", False),
        ("Fenêtre d'activité (derank)", f"{window} jour(s)", True),
        ("Derank automatique", "✅ activé" if derank_on else "❌ coupé", True),
        ("Rôle d'attente", wait_role.mention if wait_role else "*(non défini)*", True),
    ])
    if ctx.guild.icon:
        e.set_thumbnail(url=ctx.guild.icon.url)
    await ctx.send(embed=e)


# ══════════════════════════════════════════════════════════════════════
#  GESTION INDIVIDUELLE
# ══════════════════════════════════════════════════════════════════════
async def _notify(member, text):
    try:
        await member.send(text)
    except discord.HTTPException:
        pass


async def _do_rank_change(ctx_or_guild, actor, member: discord.Member, target_level: int,
                          target_branch: str, forced: bool, reply):
    db = connect()
    try:
        init_staff_db(db)
        row = get_points(db, member.guild.id, member.id)
        target_level = max(0, min(MAX_LEVEL, target_level))
        on_wait = await _assign_branch_role(db, member, target_level, target_branch, row["level"], row["branch"])
        db.execute("UPDATE staff_points SET level=?, branch=?, last_change_at=? WHERE guild_id=? AND user_id=?",
                  (target_level, target_branch, now(), member.guild.id, member.id))
        ef.log_event(db, member.guild.id, actor.id,
                    "staff_rankup" if target_level > row["level"] else "staff_derank",
                    f"{member.id} : {row['level']}/{row['branch']} → {target_level}/{target_branch}"
                    + (" (forcé)" if forced else ""))
        db.commit()
    finally:
        db.close()
    verb = "monte au" if target_level > row["level"] else "descend au"
    wait_note = " (branche pleine : rôle d'attente posé)" if on_wait else ""
    await ef._log_general(member.guild, "🏅 Changement de niveau staff",
                          f"{member.mention} : {row['level']}/{row['branch']} → **{target_level}/{target_branch}** "
                          f"— Par {actor.mention}" + (" (forcé)" if forced else "") + wait_note)
    await _notify(member, f"❄ Ton niveau de staff sur **{member.guild.name}** change : "
                         f"tu {verb} **niveau {target_level}** (branche {target_branch}).{wait_note}")
    await reply(f"✅ {member.mention} {verb} niveau **{target_level}** (branche **{target_branch}**).{wait_note}")


@bot.command(name="staffup", help="Monter un membre du staff, même sans le niveau requis (admins). <@membre> <niveau> [branche]")
async def staffup(ctx, member: discord.Member, level: int, branch: str = DEFAULT_BRANCH):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        init_staff_db(db)
        opts = branches_at(db, ctx.guild.id, level)
    finally:
        db.close()
    if len(opts) > 1 and branch == DEFAULT_BRANCH and not any(o["branch"] == DEFAULT_BRANCH for o in opts):
        names = ", ".join(f"`{o['branch']}`" for o in opts)
        await ctx.send(f"❄ Plusieurs branches existent au niveau {level} : {names}. "
                       f"Précise : `+staffup {member.mention} {level} <branche>`")
        return
    await _do_rank_change(ctx, ctx.author, member, level, branch.lower().strip(), forced=True,
                          reply=ctx.send)


@bot.command(name="staffdown", help="Descendre un membre du staff, ou à un niveau précis (admins). <@membre> [niveau] [branche]")
async def staffdown(ctx, member: discord.Member, level: int = None, branch: str = DEFAULT_BRANCH):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        cur = get_points(db, ctx.guild.id, member.id)
    finally:
        db.close()
    target = level if level is not None else cur["level"] - 1
    await _do_rank_change(ctx, ctx.author, member, target, branch.lower().strip(), forced=True, reply=ctx.send)


@bot.command(name="staffremove", help="Sortir complètement un membre du staff — retire tous les rôles liés (admins). <@membre>")
async def staffremove(ctx, member: discord.Member):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        init_staff_db(db)
        row = get_points(db, ctx.guild.id, member.id)
        cfg = recruit_cfg(db, ctx.guild.id)
        await _assign_branch_role(db, member, 0, DEFAULT_BRANCH, row["level"], row["branch"])
        db.execute("UPDATE staff_points SET level=0, branch=?, last_change_at=? WHERE guild_id=? AND user_id=?",
                  (DEFAULT_BRANCH, now(), ctx.guild.id, member.id))
        if cfg and cfg["staff_role_id"]:
            role = ctx.guild.get_role(cfg["staff_role_id"])
            if role and role in member.roles:
                try:
                    await member.remove_roles(role, reason="Sortie du staff")
                except discord.HTTPException:
                    pass
        ef.log_event(db, ctx.guild.id, ctx.author.id, "staff_removed", str(member.id))
        db.commit()
    finally:
        db.close()
    await ef._log_general(ctx.guild, "🚪 Sortie du staff", f"{member.mention} — Par {ctx.author.mention}")
    await _notify(member, f"❄ Tu ne fais plus partie du staff de **{ctx.guild.name}**.")
    await ctx.send(f"✅ {member.mention} ne fait plus partie du staff.", allowed_mentions=discord.AllowedMentions.none())


def _progress_bar(score, need, length=14):
    if need <= 0:
        return "█" * length
    filled = max(0, min(length, round(length * score / need)))
    return "█" * filled + "░" * (length - filled)


async def _stats_embed(guild, member, viewer_is_self):
    db = connect()
    try:
        init_staff_db(db)
        row = get_points(db, guild.id, member.id)
        score = score_of(db, guild.id, row)
        nxt = row["level"] + 1
        opts = branches_at(db, guild.id, nxt) if nxt <= MAX_LEVEL else []
        need = level_threshold(db, guild.id, nxt) if nxt <= MAX_LEVEL else 0
        recent = recent_score(db, guild.id, member.id, _window_days(db, guild.id))
        cur_role_row = rank_role(db, guild.id, row["level"], row["branch"]) if row["level"] else None
    finally:
        db.close()
    role = guild.get_role(cur_role_row["role_id"]) if cur_role_row else None
    fields = [
        ("💬 Messages", str(row["messages"]), True),
        ("🎫 Tickets", str(row["tickets"]), True),
        ("🎙️ Vocal", f"{row['voice_minutes']} min", True),
        ("🛡️ Modération", str(row["moderation"]), True),
        ("✨ Score total", str(score), True),
        ("🏅 Niveau actuel", f"{row['level']} ({role.mention if role else row['branch']})", True),
        ("📈 Activité récente", str(recent), True),
    ]
    if row["protected"]:
        fields.append(("🛡️ Statut", "Protégé(e) du derank automatique", False))
    if nxt <= MAX_LEVEL:
        branch_txt = " / ".join(f"`{o['branch']}`" for o in opts) if opts else "*(aucun rôle configuré)*"
        fields.append((f"🎯 Niveau {nxt}", f"{_progress_bar(score, need)}  {score}/{need}\nBranches : {branch_txt}",
                      False))
    else:
        fields.append(("🎯 Niveau suivant", "Niveau maximum atteint !", False))
    e = frost_embed(title=f"🏅 Statistiques staff — {member.display_name}", color=FROST, fields=fields)
    e.set_thumbnail(url=member.display_avatar.url)
    return e, nxt, opts, score, need


@bot.command(name="staffinfo", help="Stats détaillées d'un membre du staff, pour les admins. <@membre>")
async def staffinfo(ctx, member: discord.Member):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    e, *_ = await _stats_embed(ctx.guild, member, viewer_is_self=False)
    await ctx.send(embed=e)


@bot.command(name="staffboard", help="Tableau de tout le staff actuel.")
async def staffboard(ctx):
    if not ef.mod_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        init_staff_db(db)
        rows = db.execute("SELECT * FROM staff_points WHERE guild_id=? AND level>0 ORDER BY level DESC, "
                         "(messages+tickets*10+voice_minutes+moderation*5) DESC", (ctx.guild.id,)).fetchall()
        window = _window_days(db, ctx.guild.id)
        lines = []
        for r in rows[:25]:
            m = ctx.guild.get_member(r["user_id"])
            name = m.display_name if m else f"<@{r['user_id']}>"
            recent = recent_score(db, ctx.guild.id, r["user_id"], window)
            lines.append(f"**Niv. {r['level']}** ({r['branch']}) — {name} — récent : {recent}")
    finally:
        db.close()
    e = frost_embed(title=f"🏅 Tableau du staff ({len(rows)})", desc="\n".join(lines) or "Aucun membre du staff.",
                    color=ICE)
    await ctx.send(embed=e)


class BranchSelect(discord.ui.Select):
    def __init__(self, options, author_id):
        self.author_id = author_id
        super().__init__(placeholder="Choisis ta branche…",
                         options=[discord.SelectOption(label=o["branch"][:100], value=o["branch"])
                                 for o in options][:25])

    async def callback(self, inter: discord.Interaction):
        if inter.user.id != self.author_id:
            await inter.response.send_message("❄ Ce menu n'est pas pour toi.", ephemeral=True)
            return
        member = inter.user
        db = connect()
        try:
            row = get_points(db, inter.guild.id, member.id)
            nxt = row["level"] + 1
            need = level_threshold(db, inter.guild.id, nxt)
            if score_of(db, inter.guild.id, row) < need or not rank_role(db, inter.guild.id, nxt, self.values[0]):
                await inter.response.send_message("❄ Les conditions ne sont plus remplies.", ephemeral=True)
                return
            on_wait = await _assign_branch_role(db, member, nxt, self.values[0], row["level"], row["branch"])
            db.execute("UPDATE staff_points SET level=?, branch=?, last_change_at=? WHERE guild_id=? AND user_id=?",
                      (nxt, self.values[0], now(), inter.guild.id, member.id))
            ef.log_event(db, inter.guild.id, member.id, "staff_rankup",
                        f"{row['level']} → {nxt}/{self.values[0]} (mérité)")
            db.commit()
        finally:
            db.close()
        await ef._log_general(inter.guild, "🏅 Niveau staff mérité",
                              f"{member.mention} : niveau {row['level']} → **{nxt}/{self.values[0]}**")
        note = " (branche pleine : rôle d'attente posé)" if on_wait else ""
        await inter.response.edit_message(
            content=f"🎉 Félicitations, tu es maintenant **niveau {nxt}** (branche {self.values[0]}) !{note}",
            embed=None, view=None)


class RankupView(discord.ui.View):
    def __init__(self, author_id, eligible, opts):
        super().__init__(timeout=120)
        self.author_id = author_id
        if len(opts) > 1:
            self.remove_item(self.up)
            self.add_item(BranchSelect(opts, author_id))
            self.children[0].disabled = not eligible
        else:
            self.up.disabled = not eligible
            if not opts:
                self.remove_item(self.up)
            else:
                self._branch = opts[0]["branch"]

    async def interaction_check(self, inter: discord.Interaction) -> bool:
        if inter.user.id != self.author_id:
            await inter.response.send_message("❄ Ce bouton n'est pas pour toi.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⬆️ Monter de grade", style=discord.ButtonStyle.success)
    async def up(self, inter: discord.Interaction, button: discord.ui.Button):
        member = inter.user
        db = connect()
        try:
            row = get_points(db, inter.guild.id, member.id)
            nxt = row["level"] + 1
            branch = getattr(self, "_branch", DEFAULT_BRANCH)
            if nxt > MAX_LEVEL or score_of(db, inter.guild.id, row) < level_threshold(db, inter.guild.id, nxt) \
                    or not rank_role(db, inter.guild.id, nxt, branch):
                await inter.response.send_message("❄ Les conditions ne sont plus remplies.", ephemeral=True)
                return
            on_wait = await _assign_branch_role(db, member, nxt, branch, row["level"], row["branch"])
            db.execute("UPDATE staff_points SET level=?, branch=?, last_change_at=? WHERE guild_id=? AND user_id=?",
                      (nxt, branch, now(), inter.guild.id, member.id))
            ef.log_event(db, inter.guild.id, member.id, "staff_rankup", f"{row['level']} → {nxt} (mérité)")
            db.commit()
        finally:
            db.close()
        await ef._log_general(inter.guild, "🏅 Niveau staff mérité",
                              f"{member.mention} : niveau {row['level']} → **{nxt}**")
        note = " (branche pleine : rôle d'attente posé)" if on_wait else ""
        button.disabled = True
        await inter.response.edit_message(content=f"🎉 Félicitations, tu es maintenant **niveau {nxt}** !{note}",
                                          embed=None, view=self)
        self.stop()


@bot.command(name="staffstats", aliases=["rankstaff"], help="Tes statistiques de staff et ton niveau. [@membre]")
async def staffstats(ctx, member: discord.Member = None):
    m = member or ctx.author
    db = connect()
    try:
        init_staff_db(db)
        if member is None and not is_staff_member(db, ctx.guild.id, m):
            await ctx.send("❄ Tu ne fais pas partie du staff pour l'instant."); return
        row = get_points(db, ctx.guild.id, m.id)
        score = score_of(db, ctx.guild.id, row)
        nxt = row["level"] + 1
        need = level_threshold(db, ctx.guild.id, nxt) if nxt <= MAX_LEVEL else 0
        eligible = nxt <= MAX_LEVEL and score >= need
    finally:
        db.close()
    e, nxt, opts, score, need = await _stats_embed(ctx.guild, m, viewer_is_self=(m.id == ctx.author.id))
    view = RankupView(ctx.author.id, eligible and bool(opts), opts) if m.id == ctx.author.id and nxt <= MAX_LEVEL and opts else None
    await ctx.send(embed=e, view=view)


# ══════════════════════════════════════════════════════════════════════
#  DERANK AUTOMATIQUE HEBDOMADAIRE
# ══════════════════════════════════════════════════════════════════════
@tasks.loop(hours=24)
async def staff_derank_loop():
    """Tourne tous les jours mais ne traite chaque serveur qu'une fois par semaine
    (persistant : la date du dernier passage est stockée en base)."""
    db = connect()
    try:
        init_staff_db(db)
        guild_ids = {r["guild_id"] for r in db.execute("SELECT DISTINCT guild_id FROM staff_points").fetchall()}
    finally:
        db.close()
    for guild_id in guild_ids:
        guild = bot.get_guild(guild_id)
        if guild is None:
            continue
        db = connect()
        try:
            if not _autoderank_enabled(db, guild_id):
                continue
            last_raw = ef.config_get(db, guild_id, "staff_derank_last_run")
            if last_raw is None:
                # Premier passage pour ce serveur : on amorce l'horloge maintenant plutôt que
                # de pénaliser aussitôt un staff qui vient d'être promu (0 activité "récente").
                ef.config_set(db, guild_id, "staff_derank_last_run", now())
                continue
            last = int(last_raw or 0)
            if now() - last < WEEK_SECONDS:
                continue
            ef.config_set(db, guild_id, "staff_derank_last_run", now())
            window = _window_days(db, guild_id)
            rows = db.execute("SELECT * FROM staff_points WHERE guild_id=? AND level>0 AND protected=0",
                             (guild_id,)).fetchall()
        finally:
            db.close()
        for row in rows:
            member = guild.get_member(row["user_id"])
            if member is None:
                continue
            db = connect()
            try:
                recent = recent_score(db, guild_id, row["user_id"], window)
                need = level_threshold(db, guild_id, row["level"])
            finally:
                db.close()
            if recent < need:
                new_level = max(0, row["level"] - 1)
                await _do_rank_change(
                    None, guild.me, member, new_level, row["branch"], forced=False,
                    reply=lambda *_: asyncio.sleep(0))
                await _notify(member,
                             f"❄ Derank automatique sur **{guild.name}** : ton activité récente "
                             f"({recent} pts sur {window} j) ne suffit plus pour le niveau {row['level']} "
                             f"(il fallait {need}). Tu passes au niveau {new_level}.")


@staff_derank_loop.before_loop
async def _before_derank_loop():
    await bot.wait_until_ready()


# ══════════════════════════════════════════════════════════════════════
#  RECRUTEMENT — configuration
# ══════════════════════════════════════════════════════════════════════
def _ensure_recruit_cfg(db, guild_id):
    db.execute("INSERT OR IGNORE INTO recruit_config (guild_id) VALUES (?)", (guild_id,))
    db.commit()


@bot.command(name="recrutrole", help="Rôle staff général donné à l'acceptation (admins). <@rôle>")
async def recrutrole(ctx, role: discord.Role):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        init_staff_db(db); _ensure_recruit_cfg(db, ctx.guild.id)
        db.execute("UPDATE recruit_config SET staff_role_id=? WHERE guild_id=?", (role.id, ctx.guild.id))
        db.commit()
        synced = [m for m in ctx.guild.members if role in m.roles]
    finally:
        db.close()
    await ctx.send(f"✅ Rôle staff général → {role.mention}. Synchronisation de **{len(synced)}** membre(s)…",
                   allowed_mentions=discord.AllowedMentions.none())
    for m in synced:
        db = connect()
        try:
            row = get_points(db, ctx.guild.id, m.id)
            xp = score_of(db, ctx.guild.id, row)
        finally:
            db.close()
        await _notify(m, f"❄ Tu fais partie du staff de **{ctx.guild.name}**. "
                        f"Ton XP actuel : **{xp}** points (niveau {row['level']}). "
                        "Vois `!staffstats` pour le détail.")


@bot.command(name="recrutquestion", help="Gérer les questions. add <texte> | liste | del <numéro>")
async def recrutquestion(ctx, action: str, *, rest: str = ""):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        init_staff_db(db)
        if action == "add":
            if not rest.strip():
                await ctx.send("❄ Donne le texte de la question."); return
            pos = (db.execute("SELECT COALESCE(MAX(position),0) FROM recruit_questions WHERE guild_id=?",
                              (ctx.guild.id,)).fetchone()[0] or 0) + 1
            db.execute("INSERT INTO recruit_questions (guild_id, position, question) VALUES (?,?,?)",
                      (ctx.guild.id, pos, rest.strip()))
            db.commit()
            await ctx.send(f"✅ Question **#{pos}** ajoutée.")
        elif action in ("liste", "list"):
            rows = db.execute("SELECT * FROM recruit_questions WHERE guild_id=? ORDER BY position",
                             (ctx.guild.id,)).fetchall()
            if not rows:
                await ctx.send("❄ Aucune question configurée."); return
            lines = [f"**{r['position']}.** {r['question']}" for r in rows]
            await ctx.send(embed=frost_embed(title="📋 Questions de candidature", desc="\n".join(lines)[:3900],
                                             color=ICE))
        elif action in ("del", "remove", "supprimer"):
            try:
                pos = int(rest.strip())
            except ValueError:
                await ctx.send("❄ Donne le numéro de la question à retirer."); return
            cur = db.execute("DELETE FROM recruit_questions WHERE guild_id=? AND position=?",
                            (ctx.guild.id, pos))
            db.commit()
            await ctx.send(f"🗑️ Question **#{pos}** retirée." if cur.rowcount else "❄ Numéro inconnu.")
        else:
            await ctx.send("❄ Utilise `add <texte>`, `liste` ou `del <numéro>`.")
    finally:
        db.close()


@bot.command(name="recrutcooldown", help="Délai avant de pouvoir recandidater après un refus, en jours (admins). <jours>")
async def recrutcooldown(ctx, days: int):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    if days < 0:
        await ctx.send("❄ Valeur invalide."); return
    db = connect()
    try:
        init_staff_db(db); _ensure_recruit_cfg(db, ctx.guild.id)
        db.execute("UPDATE recruit_config SET cooldown_days=? WHERE guild_id=?", (days, ctx.guild.id))
        db.commit()
    finally:
        db.close()
    await ctx.send(f"✅ Délai avant de recandidater : **{days} jour(s)**." if days else
                   "✅ Aucun délai avant de recandidater.")


@bot.command(name="recrutlist", help="Candidatures en cours (staff).")
async def recrutlist(ctx):
    if not ef.mod_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        init_staff_db(db)
        rows = db.execute("SELECT * FROM recruit_applications WHERE guild_id=? "
                         "AND status IN ('in_progress','submitted','testing') "
                         "ORDER BY created_at DESC", (ctx.guild.id,)).fetchall()
    finally:
        db.close()
    if not rows:
        await ctx.send("❄ Aucune candidature en cours."); return
    lines = []
    for r in rows:
        m = ctx.guild.get_member(r["user_id"])
        name = m.display_name if m else f"<@{r['user_id']}>"
        lines.append(f"**{name}** — {r['status']} (depuis {ef.fmt_ts(r['created_at'])})")
    await ctx.send(embed=frost_embed(title=f"📋 Candidatures en cours ({len(rows)})",
                                     desc="\n".join(lines), color=ICE))


@bot.command(name="recrutstatut", help="Suivre l'état de ta propre candidature.")
async def recrutstatut(ctx):
    db = connect()
    try:
        init_staff_db(db)
        row = db.execute("SELECT * FROM recruit_applications WHERE guild_id=? AND user_id=? "
                         "ORDER BY created_at DESC LIMIT 1", (ctx.guild.id, ctx.author.id)).fetchone()
    finally:
        db.close()
    if not row:
        await ctx.send("❄ Tu n'as pas de candidature sur ce serveur."); return
    labels = {"in_progress": "⏳ En cours de réponse aux questions", "submitted": "📨 Envoyée, en attente de revue",
             "testing": "🧪 En entretien", "accepted": "✅ Acceptée", "refused": "❌ Refusée"}
    await ctx.send(f"❄ Ta candidature : **{labels.get(row['status'], row['status'])}**")


# ══════════════════════════════════════════════════════════════════════
#  RECRUTEMENT — panneau, DM, log, ticket
# ══════════════════════════════════════════════════════════════════════
class RecruitPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Candidater", style=discord.ButtonStyle.success,
                       custom_id="emilia_recruit_apply")
    async def apply(self, inter: discord.Interaction, button: discord.ui.Button):
        db = connect()
        try:
            init_staff_db(db)
            questions = db.execute("SELECT * FROM recruit_questions WHERE guild_id=? ORDER BY position",
                                   (inter.guild.id,)).fetchall()
            if not questions:
                await inter.response.send_message("❄ Le recrutement n'est pas encore configuré.", ephemeral=True)
                return
            pending = db.execute(
                "SELECT 1 FROM recruit_applications WHERE guild_id=? AND user_id=? AND status='in_progress'",
                (inter.guild.id, inter.user.id)).fetchone()
            if pending:
                await inter.response.send_message("❄ Tu as déjà une candidature en cours, regarde tes DM.",
                                                  ephemeral=True)
                return
            cfg = recruit_cfg(db, inter.guild.id)
            cooldown = cfg["cooldown_days"] if cfg else 0
            if cooldown:
                last_refused = db.execute(
                    "SELECT decided_at FROM recruit_applications WHERE guild_id=? AND user_id=? "
                    "AND status='refused' ORDER BY decided_at DESC LIMIT 1",
                    (inter.guild.id, inter.user.id)).fetchone()
                if last_refused and last_refused["decided_at"]:
                    remaining = cooldown * 86400 - (now() - last_refused["decided_at"])
                    if remaining > 0:
                        await inter.response.send_message(
                            f"❄ Tu pourras recandidater dans **{remaining // 86400 + 1} jour(s)**.", ephemeral=True)
                        return
            db.execute("INSERT INTO recruit_applications (guild_id, user_id, status, created_at) "
                      "VALUES (?,?,'in_progress',?)", (inter.guild.id, inter.user.id, now()))
            db.commit()
            app_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        finally:
            db.close()
        try:
            await inter.user.send(f"📋 Candidature pour **{inter.guild.name}** — question 1/{len(questions)} :\n\n"
                                  f"**{questions[0]['question']}**\n\n*Réponds directement ici, en DM.*")
        except discord.HTTPException:
            db = connect()
            try:
                db.execute("UPDATE recruit_applications SET status='refused' WHERE id=?", (app_id,))
                db.commit()
            finally:
                db.close()
            await inter.response.send_message("❄ Je n'arrive pas à t'envoyer de message privé. "
                                              "Ouvre tes DM puis retente.", ephemeral=True)
            return
        await inter.response.send_message("📩 Les questions arrivent dans tes messages privés !", ephemeral=True)


async def _submit_application(app, answers_list, questions):
    db = connect()
    try:
        cfg = recruit_cfg(db, app["guild_id"])
        db.execute("UPDATE recruit_applications SET status='submitted', answers=? WHERE id=?",
                  (json.dumps(answers_list, ensure_ascii=False), app["id"]))
        db.commit()
    finally:
        db.close()
    guild = bot.get_guild(app["guild_id"])
    if guild is None:
        return
    applicant = guild.get_member(app["user_id"])
    lines = [f"**{q['question']}**\n{a}" for q, a in zip(questions, answers_list)]
    role = guild.get_role(cfg["staff_role_id"]) if (cfg and cfg["staff_role_id"]) else None
    msg = await ef._log_admin(
        guild, f"📋 Candidature de {applicant.display_name if applicant else app['user_id']}",
        "\n\n".join(lines)[:3900],
        view=RecruitLogView(app["id"]),
        content=role.mention if role else None,
        allowed_mentions=discord.AllowedMentions(roles=[role] if role else False))
    if msg is None:
        return  # log_admin_id pas encore configuré (+setlogadmin #salon)
    db = connect()
    try:
        db.execute("UPDATE recruit_applications SET log_message_id=?, log_channel_id=? WHERE id=?",
                  (msg.id, msg.channel.id, app["id"]))
        db.commit()
    finally:
        db.close()


@bot.listen("on_message")
async def _recruit_dm_flow(message: discord.Message):
    if message.author.bot or message.guild is not None:
        return
    db = connect()
    try:
        init_staff_db(db)
        app = db.execute("SELECT * FROM recruit_applications WHERE user_id=? AND status='in_progress' "
                         "ORDER BY created_at DESC LIMIT 1", (message.author.id,)).fetchone()
        if not app:
            return
        questions = db.execute("SELECT * FROM recruit_questions WHERE guild_id=? ORDER BY position",
                               (app["guild_id"],)).fetchall()
        answers = json.loads(app["answers"] or "[]")
        answers.append(message.content or "*(réponse vide)*")
        idx = app["current_question"] + 1
        if idx < len(questions):
            db.execute("UPDATE recruit_applications SET answers=?, current_question=? WHERE id=?",
                      (json.dumps(answers, ensure_ascii=False), idx, app["id"]))
            db.commit()
        db.close()
        if idx < len(questions):
            await message.channel.send(f"Question {idx + 1}/{len(questions)} :\n\n**{questions[idx]['question']}**")
        else:
            await message.channel.send("✅ Merci, ta candidature a bien été envoyée. On revient vers toi !")
            await _submit_application(app, answers, questions)
        return
    finally:
        try:
            db.close()
        except Exception:
            pass


class RecruitLogView(discord.ui.View):
    def __init__(self, app_id=None):
        super().__init__(timeout=None)
        self.app_id = app_id

    async def _get_app(self, inter):
        app_id = self.app_id
        if app_id is None and inter.message:
            db = connect()
            try:
                row = db.execute("SELECT id FROM recruit_applications WHERE log_message_id=?",
                                 (inter.message.id,)).fetchone()
            finally:
                db.close()
            app_id = row["id"] if row else None
        db = connect()
        try:
            return db.execute("SELECT * FROM recruit_applications WHERE id=?", (app_id,)).fetchone()
        finally:
            db.close()

    @discord.ui.button(label="🧪 Tester", style=discord.ButtonStyle.primary, custom_id="emilia_recruit_test")
    async def test(self, inter: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_member(inter.user):
            await inter.response.send_message("❄ Seul un admin peut lancer un test.", ephemeral=True)
            return
        app = await self._get_app(inter)
        if not app or app["status"] != "submitted":
            await inter.response.send_message("❄ Candidature introuvable ou déjà traitée.", ephemeral=True)
            return
        guild = inter.guild
        applicant = guild.get_member(app["user_id"])
        if applicant is None:
            await inter.response.send_message("❄ Le candidat a quitté le serveur.", ephemeral=True)
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            applicant: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            inter.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        safe = "".join(c for c in applicant.display_name.lower().replace(" ", "-") if c.isalnum() or c == "-") or "candidat"
        channel = await guild.create_text_channel(name=f"recrut-{safe}"[:90], overwrites=overwrites,
                                                  reason=f"Test de recrutement — {applicant}")
        db = connect()
        try:
            db.execute("UPDATE recruit_applications SET status='testing', ticket_channel_id=?, tester_id=? WHERE id=?",
                      (channel.id, inter.user.id, app["id"]))
            db.commit()
        finally:
            db.close()
        await channel.send(
            content=f"{inter.user.mention} {applicant.mention}",
            embed=frost_embed(title="🧪 Entretien de recrutement",
                              desc=f"Testeur : {inter.user.mention}\nCandidat : {applicant.mention}\n\n"
                                   "Décision finale avec les boutons ci-dessous.", color=ICE),
            view=RecruitTicketView(app["id"]),
            allowed_mentions=discord.AllowedMentions(users=True))
        for child in self.children:
            child.disabled = True
        await inter.response.edit_message(view=self)
        await inter.followup.send(f"🧪 Entretien ouvert : {channel.mention}", ephemeral=True)

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger, custom_id="emilia_recruit_refuse")
    async def refuse(self, inter: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_member(inter.user):
            await inter.response.send_message("❄ Seul un admin peut refuser.", ephemeral=True)
            return
        app = await self._get_app(inter)
        if not app or app["status"] != "submitted":
            await inter.response.send_message("❄ Candidature introuvable ou déjà traitée.", ephemeral=True)
            return
        db = connect()
        try:
            db.execute("UPDATE recruit_applications SET status='refused', decided_at=? WHERE id=?",
                      (now(), app["id"]))
            db.commit()
        finally:
            db.close()
        guild = inter.guild
        applicant = guild.get_member(app["user_id"])
        if applicant:
            await _notify(applicant, f"❄ Ta candidature pour **{guild.name}** n'a pas été retenue cette fois-ci.")
        for child in self.children:
            child.disabled = True
        await inter.response.edit_message(view=self)
        await inter.followup.send("❌ Candidature refusée.", ephemeral=True)


class RecruitTicketView(discord.ui.View):
    def __init__(self, app_id=None):
        super().__init__(timeout=None)
        self.app_id = app_id

    async def _get_app(self, inter):
        app_id = self.app_id
        if app_id is None:
            db = connect()
            try:
                row = db.execute("SELECT id FROM recruit_applications WHERE ticket_channel_id=?",
                                 (inter.channel.id,)).fetchone()
            finally:
                db.close()
            app_id = row["id"] if row else None
        db = connect()
        try:
            return db.execute("SELECT * FROM recruit_applications WHERE id=?", (app_id,)).fetchone()
        finally:
            db.close()

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.success, custom_id="emilia_recruit_accept")
    async def accept(self, inter: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_member(inter.user):
            await inter.response.send_message("❄ Seul un admin peut accepter.", ephemeral=True)
            return
        app = await self._get_app(inter)
        if not app:
            await inter.response.send_message("❄ Candidature introuvable.", ephemeral=True)
            return
        guild = inter.guild
        applicant = guild.get_member(app["user_id"])
        if applicant is None:
            await inter.response.send_message("❄ Le candidat a quitté le serveur.", ephemeral=True)
            return
        db = connect()
        try:
            init_staff_db(db)
            cfg = recruit_cfg(db, guild.id)
            db.execute("UPDATE recruit_applications SET status='accepted', decided_at=? WHERE id=?",
                      (now(), app["id"]))
            get_points(db, guild.id, applicant.id)
            lvl1_opts = branches_at(db, guild.id, 1)
            lvl1 = lvl1_opts[0] if lvl1_opts else None
            db.execute("UPDATE staff_points SET level=1, branch=?, last_change_at=? WHERE guild_id=? AND user_id=?",
                      (lvl1["branch"] if lvl1 else DEFAULT_BRANCH, now(), guild.id, applicant.id))
            db.commit()
        finally:
            db.close()
        roles_to_add = []
        if cfg and cfg["staff_role_id"]:
            r = guild.get_role(cfg["staff_role_id"])
            if r:
                roles_to_add.append(r)
        if lvl1:
            r = guild.get_role(lvl1["role_id"])
            if r:
                roles_to_add.append(r)
        if roles_to_add:
            try:
                await applicant.add_roles(*roles_to_add, reason="Recrutement accepté")
            except discord.HTTPException:
                pass
        await _notify(applicant, f"🎉 Bienvenue dans le staff de **{guild.name}** !")
        for child in self.children:
            child.disabled = True
        await inter.response.edit_message(view=self)
        await inter.followup.send(f"✅ {applicant.mention} rejoint le staff.",
                                  allowed_mentions=discord.AllowedMentions.none())

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger, custom_id="emilia_recruit_ticket_refuse")
    async def refuse(self, inter: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_member(inter.user):
            await inter.response.send_message("❄ Seul un admin peut refuser.", ephemeral=True)
            return
        app = await self._get_app(inter)
        if app:
            db = connect()
            try:
                db.execute("UPDATE recruit_applications SET status='refused', decided_at=? WHERE id=?",
                          (now(), app["id"]))
                db.commit()
            finally:
                db.close()
            guild = inter.guild
            applicant = guild.get_member(app["user_id"])
            if applicant:
                await _notify(applicant, f"❄ Ta candidature pour **{guild.name}** n'a pas été retenue.")
        await inter.response.send_message("🔒 Fermeture du salon dans 5 secondes.")
        await asyncio.sleep(5)
        try:
            await inter.channel.delete(reason="Candidature refusée")
        except discord.HTTPException:
            pass


@bot.command(name="recrutsetup", help="Poster le panneau de candidature (admins). <#salon>")
async def recrutsetup(ctx, channel: discord.TextChannel):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        init_staff_db(db); _ensure_recruit_cfg(db, ctx.guild.id)
        db.execute("UPDATE recruit_config SET panel_channel_id=? WHERE guild_id=?", (channel.id, ctx.guild.id))
        db.commit()
    finally:
        db.close()
    e = frost_embed(title="📋 Rejoindre le staff",
                    desc="Clique sur le bouton ci-dessous pour candidater. Tu recevras les questions en "
                         "message privé.", color=ICE)
    if ctx.guild.icon:
        e.set_thumbnail(url=ctx.guild.icon.url)
    await channel.send(embed=e, view=RecruitPanelView())
    await ctx.send(f"✅ Panneau de candidature posté dans {channel.mention}.")


def register_persistent_views():
    bot.add_view(RecruitPanelView())
    bot.add_view(RecruitLogView())
    bot.add_view(RecruitTicketView())


def start_loops():
    if not staff_derank_loop.is_running():
        staff_derank_loop.start()
