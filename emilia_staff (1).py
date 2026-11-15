"""
Rangs du staff (niveaux 1 à 10) + recrutement automatique.

Rangs :
  • +rolestaff <niveau 1-10> <@rôle> — associe un rôle Discord à un niveau.
  • Les points s'accumulent en parlant, en traitant des tickets, en vocal.
  • !staffstats — voir ses points, son niveau, et un bouton pour monter de
    grade si (et seulement si) les conditions du niveau suivant sont remplies.
  • +rankup / +derank <@membre> [niveau] — un admin peut monter ou descendre
    un membre du staff même sans avoir le niveau requis.
  • Les paliers montent vite en difficulté (progression quadratique) : ce
    n'est volontairement pas facile d'atteindre les niveaux élevés.

Recrutement :
  • +recrutsetup #salon — poste le panneau de candidature (bouton persistant).
  • +recrutlog #salon — salon où les réponses sont publiées (ping du staff).
  • +recrutrole <@role> — rôle staff général donné à l'acceptation.
  • +recrutquestion add|liste|del ... — gère les questions posées en DM.
  • Un membre clique "Candidater" → reçoit les questions en DM, une par une.
  • Une fois terminé → les réponses sont publiées dans le salon de logs,
    avec deux boutons : Tester (admin uniquement) / Refuser.
  • Tester ouvre un ticket avec le candidat et le staff qui a cliqué ;
    dans ce ticket, deux boutons : Accepter (ajoute le rôle staff + niveau 1)
    / Refuser (ferme le ticket).
"""
import json
import time

import discord
from discord.ext import commands, tasks

import emilia_frost as ef
from emilia_frost import bot, connect, frost_embed, q, ICE, FROST, EXCL

MAX_LEVEL = 10
# Progression quadratique : difficile d'atteindre les niveaux élevés.
LEVEL_BASE = 300


def level_threshold(level: int) -> int:
    return level * level * LEVEL_BASE


def score_of(row) -> int:
    return row["messages"] * 1 + row["tickets"] * 25 + row["voice_minutes"] * 2


def now() -> int:
    return int(time.time())


# ══════════════════════════════════════════════════════════════════════
#  BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════════════
def init_staff_db(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS staff_rank_roles (
        guild_id INTEGER NOT NULL, level INTEGER NOT NULL,
        role_id INTEGER NOT NULL, label TEXT,
        PRIMARY KEY (guild_id, level)
    );
    CREATE TABLE IF NOT EXISTS staff_points (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        messages INTEGER NOT NULL DEFAULT 0,
        tickets INTEGER NOT NULL DEFAULT 0,
        voice_minutes INTEGER NOT NULL DEFAULT 0,
        level INTEGER NOT NULL DEFAULT 0,
        last_change_at INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS staff_voice_sessions (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, joined_at INTEGER NOT NULL,
        PRIMARY KEY (guild_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS recruit_config (
        guild_id INTEGER PRIMARY KEY,
        panel_channel_id INTEGER, log_channel_id INTEGER,
        staff_role_id INTEGER, first_level_role_id INTEGER
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
        created_at INTEGER NOT NULL
    );
    """)
    db.commit()


def get_points(db, guild_id, user_id):
    db.execute("INSERT OR IGNORE INTO staff_points (guild_id, user_id, last_change_at) VALUES (?,?,?)",
               (guild_id, user_id, now()))
    db.commit()
    return db.execute("SELECT * FROM staff_points WHERE guild_id=? AND user_id=?",
                      (guild_id, user_id)).fetchone()


def rank_role(db, guild_id, level):
    return db.execute("SELECT * FROM staff_rank_roles WHERE guild_id=? AND level=?",
                      (guild_id, level)).fetchone()


def recruit_cfg(db, guild_id):
    return db.execute("SELECT * FROM recruit_config WHERE guild_id=?", (guild_id,)).fetchone()


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


def is_staff_member(db, guild_id, member: discord.Member) -> bool:
    cfg = recruit_cfg(db, guild_id)
    if cfg and cfg["staff_role_id"]:
        role = member.guild.get_role(cfg["staff_role_id"])
        if role and role in member.roles:
            return True
    ranks = db.execute("SELECT role_id FROM staff_rank_roles WHERE guild_id=?", (guild_id,)).fetchall()
    held = {r.id for r in member.roles}
    return any(r["role_id"] in held for r in ranks)


async def _swap_rank_role(db, member: discord.Member, old_level: int, new_level: int):
    guild_id = member.guild.id
    old_r = rank_role(db, guild_id, old_level) if old_level else None
    new_r = rank_role(db, guild_id, new_level) if new_level else None
    try:
        if old_r:
            role = member.guild.get_role(old_r["role_id"])
            if role and role in member.roles:
                await member.remove_roles(role, reason="Changement de niveau staff")
        if new_r:
            role = member.guild.get_role(new_r["role_id"])
            if role and role not in member.roles:
                await member.add_roles(role, reason="Changement de niveau staff")
    except discord.HTTPException:
        pass


# ══════════════════════════════════════════════════════════════════════
#  GAIN DE POINTS — messages, tickets, vocal
# ══════════════════════════════════════════════════════════════════════
@bot.listen("on_message")
async def _staff_points_on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return
    db = connect()
    try:
        init_staff_db(db)
        if not is_staff_member(db, message.guild.id, message.author):
            return
        db.execute("INSERT INTO staff_points (guild_id, user_id, messages, last_change_at) VALUES (?,?,1,?) "
                   "ON CONFLICT(guild_id, user_id) DO UPDATE SET messages=messages+1, last_change_at=excluded.last_change_at",
                   (message.guild.id, message.author.id, now()))
        db.commit()
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
            if row and is_staff_member(db, member.guild.id, member):
                minutes = max(0, (now() - row["joined_at"]) // 60)
                if minutes:
                    db.execute("INSERT INTO staff_points (guild_id, user_id, voice_minutes, last_change_at) "
                              "VALUES (?,?,?,?) ON CONFLICT(guild_id, user_id) DO UPDATE SET "
                              "voice_minutes=voice_minutes+excluded.voice_minutes, last_change_at=excluded.last_change_at",
                              (member.guild.id, member.id, minutes, now()))
            db.commit()
    finally:
        db.close()


@bot.listen("on_emilia_ticket_closed")
async def _staff_points_on_ticket(guild_id, staff_id):
    if not staff_id:
        return
    db = connect()
    try:
        init_staff_db(db)
        db.execute("INSERT INTO staff_points (guild_id, user_id, tickets, last_change_at) VALUES (?,?,1,?) "
                   "ON CONFLICT(guild_id, user_id) DO UPDATE SET tickets=tickets+1, last_change_at=excluded.last_change_at",
                   (guild_id, staff_id, now()))
        db.commit()
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════
#  COMMANDES — configuration et actions des rangs
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="rolestaff", help="Associer un rôle à un niveau de staff 1-10 (admins). <niveau> <@rôle>")
async def rolestaff(ctx, level: int, role: discord.Role):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    if not (1 <= level <= MAX_LEVEL):
        await ctx.send(f"❄ Le niveau doit être entre 1 et {MAX_LEVEL}."); return
    db = connect()
    try:
        init_staff_db(db)
        db.execute("INSERT INTO staff_rank_roles (guild_id, level, role_id, label) VALUES (?,?,?,?) "
                   "ON CONFLICT(guild_id, level) DO UPDATE SET role_id=excluded.role_id, label=excluded.label",
                   (ctx.guild.id, level, role.id, role.name))
        db.commit()
    finally:
        db.close()
    await ctx.send(f"✅ Niveau **{level}** → {role.mention} (seuil : **{level_threshold(level)}** points).",
                   allowed_mentions=discord.AllowedMentions.none())


async def _do_rank_change(ctx, member: discord.Member, target_level: int, forced: bool):
    db = connect()
    try:
        init_staff_db(db)
        row = get_points(db, ctx.guild.id, member.id)
        target_level = max(0, min(MAX_LEVEL, target_level))
        await _swap_rank_role(db, member, row["level"], target_level)
        db.execute("UPDATE staff_points SET level=?, last_change_at=? WHERE guild_id=? AND user_id=?",
                  (target_level, now(), ctx.guild.id, member.id))
        ef.log_event(db, ctx.guild.id, ctx.author.id,
                    "staff_rankup" if target_level > row["level"] else "staff_derank",
                    f"{member.id} : {row['level']} → {target_level}" + (" (forcé)" if forced else ""))
        db.commit()
    finally:
        db.close()
    verb = "monte au" if target_level > row["level"] else "descend au"
    await ctx.send(f"✅ {member.mention} {verb} niveau **{target_level}**.",
                   allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="staffup", help="Monter un membre du staff (niveaux numériques), même sans le niveau requis (admins). <@membre> [niveau]")
async def staffup(ctx, member: discord.Member, level: int = None):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        cur = get_points(db, ctx.guild.id, member.id)["level"]
    finally:
        db.close()
    await _do_rank_change(ctx, member, level if level is not None else cur + 1, forced=True)


@bot.command(name="staffdown", help="Descendre un membre du staff d'un niveau, ou à un niveau précis (admins). <@membre> [niveau]")
async def staffdown(ctx, member: discord.Member, level: int = None):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        cur = get_points(db, ctx.guild.id, member.id)["level"]
    finally:
        db.close()
    await _do_rank_change(ctx, member, level if level is not None else cur - 1, forced=True)


class RankupView(discord.ui.View):
    def __init__(self, author_id, eligible):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.up.disabled = not eligible

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
            if nxt > MAX_LEVEL or score_of(row) < level_threshold(nxt) or not rank_role(db, inter.guild.id, nxt):
                await inter.response.send_message("❄ Les conditions ne sont plus remplies.", ephemeral=True)
                return
            await _swap_rank_role(db, member, row["level"], nxt)
            db.execute("UPDATE staff_points SET level=?, last_change_at=? WHERE guild_id=? AND user_id=?",
                      (nxt, now(), inter.guild.id, member.id))
            ef.log_event(db, inter.guild.id, member.id, "staff_rankup", f"{row['level']} → {nxt} (mérité)")
            db.commit()
        finally:
            db.close()
        button.disabled = True
        await inter.response.edit_message(content=f"🎉 Félicitations, tu es maintenant **niveau {nxt}** !",
                                          embed=None, view=self)
        self.stop()


@bot.command(name="staffstats", aliases=["rankstaff"], help="Tes statistiques de staff et ton niveau.")
async def staffstats(ctx, member: discord.Member = None):
    m = member or ctx.author
    db = connect()
    try:
        init_staff_db(db)
        if not is_staff_member(db, ctx.guild.id, m) and member is None:
            await ctx.send("❄ Tu ne fais pas partie du staff pour l'instant."); return
        row = get_points(db, ctx.guild.id, m.id)
        score = score_of(row)
        nxt = row["level"] + 1
        nxt_role = rank_role(db, ctx.guild.id, nxt) if nxt <= MAX_LEVEL else None
        eligible = nxt <= MAX_LEVEL and nxt_role and score >= level_threshold(nxt)
    finally:
        db.close()
    fields = [
        ("💬 Messages", str(row["messages"]), True),
        ("🎫 Tickets", str(row["tickets"]), True),
        ("🎙️ Vocal", f"{row['voice_minutes']} min", True),
        ("✨ Score total", str(score), True),
        ("🏅 Niveau actuel", str(row["level"]), True),
    ]
    if nxt <= MAX_LEVEL:
        need = level_threshold(nxt)
        fields.append(("🎯 Niveau suivant", f"{score}/{need}" + ("" if nxt_role else " *(rôle non configuré)*"), False))
    else:
        fields.append(("🎯 Niveau suivant", "Niveau maximum atteint !", False))
    e = frost_embed(title=f"🏅 Statistiques staff — {m.display_name}", color=FROST, fields=fields)
    view = RankupView(ctx.author.id, bool(eligible)) if m.id == ctx.author.id and nxt <= MAX_LEVEL else None
    await ctx.send(embed=e, view=view)


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
    finally:
        db.close()
    await ctx.send(f"✅ Rôle staff général → {role.mention}.", allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="recrutlog", help="Salon des réponses de candidature (admins). <#salon>")
async def recrutlog(ctx, channel: discord.TextChannel):
    if not ef.admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        init_staff_db(db); _ensure_recruit_cfg(db, ctx.guild.id)
        db.execute("UPDATE recruit_config SET log_channel_id=? WHERE guild_id=?", (channel.id, ctx.guild.id))
        db.commit()
    finally:
        db.close()
    await ctx.send(f"✅ Salon des candidatures → {channel.mention}.")


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
    if guild is None or cfg is None or not cfg["log_channel_id"]:
        return
    channel = guild.get_channel(cfg["log_channel_id"])
    if channel is None:
        return
    applicant = guild.get_member(app["user_id"])
    lines = [f"**{q['question']}**\n{a}" for q, a in zip(questions, answers_list)]
    e = frost_embed(title=f"📋 Candidature de {applicant.display_name if applicant else app['user_id']}",
                    desc="\n\n".join(lines)[:3900], color=EXCL)
    role = guild.get_role(cfg["staff_role_id"]) if cfg["staff_role_id"] else None
    msg = await channel.send(content=role.mention if role else None, embed=e,
                             view=RecruitLogView(app["id"]),
                             allowed_mentions=discord.AllowedMentions(roles=[role] if role else False))
    db = connect()
    try:
        db.execute("UPDATE recruit_applications SET log_message_id=?, log_channel_id=? WHERE id=?",
                  (msg.id, channel.id, app["id"]))
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
            db.execute("UPDATE recruit_applications SET status='refused' WHERE id=?", (app["id"],))
            db.commit()
        finally:
            db.close()
        guild = inter.guild
        applicant = guild.get_member(app["user_id"])
        if applicant:
            try:
                await applicant.send(f"❄ Ta candidature pour **{guild.name}** n'a pas été retenue cette fois-ci.")
            except discord.HTTPException:
                pass
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
            db.execute("UPDATE recruit_applications SET status='accepted' WHERE id=?", (app["id"],))
            get_points(db, guild.id, applicant.id)
            lvl1 = rank_role(db, guild.id, 1)
            db.execute("UPDATE staff_points SET level=1, last_change_at=? WHERE guild_id=? AND user_id=?",
                      (now(), guild.id, applicant.id))
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
        try:
            await applicant.send(f"🎉 Bienvenue dans le staff de **{guild.name}** !")
        except discord.HTTPException:
            pass
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
                db.execute("UPDATE recruit_applications SET status='refused' WHERE id=?", (app["id"],))
                db.commit()
            finally:
                db.close()
            guild = inter.guild
            applicant = guild.get_member(app["user_id"])
            if applicant:
                try:
                    await applicant.send(f"❄ Ta candidature pour **{guild.name}** n'a pas été retenue.")
                except discord.HTTPException:
                    pass
        await inter.response.send_message("🔒 Fermeture du salon dans 5 secondes.")
        import asyncio
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
    await channel.send(embed=e, view=RecruitPanelView())
    await ctx.send(f"✅ Panneau de candidature posté dans {channel.mention}.")


def register_persistent_views():
    bot.add_view(RecruitPanelView())
    bot.add_view(RecruitLogView())
    bot.add_view(RecruitTicketView())
