"""
Emilia Frost — extensions (commandes manquantes du cahier des charges).

Ce module s'ajoute à emilia_frost.py sans le remplacer :
  • routage des préfixes  : « ! » membres · « + » staff · « w. » propriétaire
  • configuration serveur : +config / +showconfig / +setlog / +setrole …
  • boutique              : +shopadd / +shopstock / +shopprice / +shopremove
  • tickets               : +claim / +close / +ticketadd / +ticketremove
  • giveaways             : !claimgw
  • WINNERMUSK            : codes (w.gencode, !code), !winnerassets, !winnersell
  • cycle de vie          : message d'installation, départ/retour, vérification
  • aide filtrée par préfixe, activité Discord (rotation + contrôle propriétaire)
"""
import asyncio
import json
import re
import secrets
import string
import time

import discord
from discord.ext import commands, tasks

import emilia_frost as ef
from emilia_frost import (
    bot, connect, config_get, config_set, get_user, update_user, add_tx, log_event,
    frost_embed, fmt, now, fmt_ts, q, admin_check, mod_check, owner_check,
    COIN, ICE, FROST, EXCL, treasury_move,
)

# ══════════════════════════════════════════════════════════════════════
#  TABLES SUPPLÉMENTAIRES
# ══════════════════════════════════════════════════════════════════════
def init_extra_db(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS giveaway_winners (
        guild_id INTEGER NOT NULL, message_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        prize TEXT, claim_until INTEGER NOT NULL, claimed INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, message_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS member_roles (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        role_ids TEXT NOT NULL, left_at INTEGER NOT NULL,
        PRIMARY KEY (guild_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS verif_pending (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        answer INTEGER NOT NULL, tries INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL,
        PRIMARY KEY (guild_id, user_id)
    );
    """)
    db.commit()


# ══════════════════════════════════════════════════════════════════════
#  ROUTAGE DES PRÉFIXES  (!  membres · +  staff · w.  propriétaire)
# ══════════════════════════════════════════════════════════════════════
OWNER_COMMANDS = {"winneradd", "dashboard", "gencode", "activity", "journal",
                  "servers", "setfee", "setcrosslimit"}

STAFF_COMMANDS = (set(ef.STAFF_COMMANDS) - {"winneradd", "winner", "dashboard"}) | {
    "setprefix", "autosuivi", "claim", "ticketadd", "ticketremove",
    "config", "showconfig", "setlog", "setwelcome", "setleave", "setchest", "setevent",
    "setrole", "ticketcategory", "givemoney", "setmoney", "givemf", "setmf",
    "shopadd", "shopstock", "shopprice", "shopremove", "verify", "verifsetup",
}
ef.STAFF_COMMANDS.clear()
ef.STAFF_COMMANDS.update(STAFF_COMMANDS)

NO_GUILD_OK = {"help", "ping", "invite"}


class WrongPrefix(commands.CheckFailure):
    pass


def kind_of(cmd) -> str:
    root = cmd.root_parent or cmd
    if root.name in OWNER_COMMANDS:
        return "owner"
    if root.name in STAFF_COMMANDS:
        return "staff"
    return "member"


@bot.check
async def prefix_router(ctx):
    """Le préfixe ne donne aucun droit : il sert seulement à ranger les commandes."""
    cmd = ctx.command
    if cmd is None:
        return True
    root = cmd.root_parent or cmd
    if ctx.guild is None and root.name not in NO_GUILD_OK:
        raise commands.NoPrivateMessage("❄ Cette commande fonctionne seulement dans un serveur.")
    if root.name in ("help", "aide", "commandes", "close"):
        return True   # s'adaptent elles-mêmes (aide) ou s'autorisent en interne (fermeture de ticket)
    used = (ctx.prefix or "").strip().lower()
    if not used or used.startswith("<@"):
        return True
    kind = kind_of(cmd)
    member_prefix = ef._member_prefix(ctx.guild.id if ctx.guild else None).lower()
    expected = {"owner": "w.", "staff": "+", "member": member_prefix}[kind]
    if used == expected:
        return True
    names = {"owner": "propriétaire", "staff": "staff", "member": "membres"}
    raise WrongPrefix(f"❄ Cette commande est de type **{names[kind]}** : utilise "
                      f"`{expected}{root.name}`.")


# ══════════════════════════════════════════════════════════════════════
#  OUTILS
# ══════════════════════════════════════════════════════════════════════
def _extract_id(raw: str):
    m = re.search(r"\d{15,21}", raw or "")
    return int(m.group()) if m else None


def add_alias(command_name: str, alias: str):
    cmd = bot.get_command(command_name)
    if cmd is not None and alias not in bot.all_commands:
        cmd.aliases = list(cmd.aliases) + [alias]
        bot.all_commands[alias] = cmd


MAX_AMOUNT = 1_000_000_000_000

# ══════════════════════════════════════════════════════════════════════
#  H. CONFIGURATION DU SERVEUR
# ══════════════════════════════════════════════════════════════════════
# clé : (type, description)
CONFIG_KEYS = {
    "mod_log_channel_id":   ("channel",  "Salon unique des logs de modération"),
    "log_channel_id":       ("channel",  "Salon des journaux (tickets, revues staff…)"),
    "journal_channel_id":   ("channel",  "Salon 📖・journal (annonces du propriétaire)"),
    "welcome_channel_id":   ("channel",  "Salon d'accueil"),
    "leave_channel_id":     ("channel",  "Salon des départs"),
    "chest_channel_id":     ("channel",  "Salon d'apparition des coffres (toutes les 2 h)"),
    "event_channel_id":     ("channel",  "Salon des événements / boss"),
    "ticket_category_id":   ("category", "Catégorie où créer les tickets"),
    "ticket_ping_role_id":  ("role",     "Rôle pingé à l'ouverture d'un ticket"),
    "admin_role_id":        ("role",     "Rôle administrateur du bot"),
    "mod_role_id":          ("role",     "Rôle modérateur du bot"),
    "ban_role_id":          ("role",     "Rôle du role-ban (+ban)"),
    "bump_role_id":         ("role",     "Rôle pingé au rappel de bump"),
    "verif_role_unverified": ("role",    "Rôle « 🔒・Non vérifié »"),
    "verif_role_member":    ("role",     "Rôle membre donné après vérification"),
    "verif_enabled":        ("bool",     "Vérification à l'arrivée (on/off)"),
    "daily_base":           ("int",      "Gain de base du !daily"),
    "work_base":            ("int",      "Gain de base du !work"),
    "mine_base":            ("int",      "Gain de base du !mine"),
    "daily_aid":            ("int",      "Aide quotidienne aux sans-emploi"),
    "bank_interest_pct":    ("number",   "Intérêt bancaire quotidien (%)"),
    "trade_tax_pct":        ("pct",      "Taxe sur les ventes entre membres (%)"),
    "family_create_cost":   ("int",      "Coût de création d'une famille"),
    "prison_bail_rate":     ("int",      "Caution de prison (Crédits/minute)"),
    "kill_success_rate":    ("pct",      "Kill & Block : chances de réussite (%)"),
    "kill_prison_rate":     ("pct",      "Kill & Block : risque de prison (%)"),
    "kill_steal_cap":       ("int",      "Kill & Block : plafond de vol"),
    "ballon_pay_price":     ("int",      "Prix du second vote Ballon d'Or"),
}
OWNER_KEYS = {
    "cross_fee_pct":     ("number", "Frais des transferts interserveurs (%)"),
    "cross_daily_limit": ("int",    "Limite quotidienne des transferts interserveurs"),
}


def _parse_config_value(guild, kind, raw):
    """Retourne (valeur_stockée, affichage) ou lève ValueError avec un message clair."""
    raw = (raw or "").strip()
    if kind in ("channel", "category", "role"):
        _id = _extract_id(raw)
        if _id is None:
            raise ValueError("Mentionne l'élément (#salon / @rôle) ou donne son identifiant.")
        if kind == "role":
            obj = guild.get_role(_id)
            if obj is None or obj.is_default():
                raise ValueError("Rôle introuvable sur ce serveur.")
            return str(_id), obj.mention
        obj = guild.get_channel(_id)
        if obj is None:
            raise ValueError("Salon introuvable sur ce serveur.")
        if kind == "category" and not isinstance(obj, discord.CategoryChannel):
            raise ValueError("Ce n'est pas une catégorie.")
        if kind == "channel" and isinstance(obj, discord.CategoryChannel):
            raise ValueError("Donne un salon, pas une catégorie.")
        return str(_id), obj.mention
    if kind == "bool":
        v = raw.lower()
        if v in ("on", "oui", "1", "true", "actif"):
            return "1", "activé"
        if v in ("off", "non", "0", "false", "inactif"):
            return "0", "désactivé"
        raise ValueError("Valeur attendue : on ou off.")
    if kind in ("int", "pct", "number"):
        try:
            num = float(raw.replace(",", ".").replace(" ", ""))
        except ValueError:
            raise ValueError("Valeur numérique attendue.")
        if num < 0 or num > MAX_AMOUNT:
            raise ValueError("Valeur hors limites.")
        if kind == "pct" and num > 100:
            raise ValueError("Un pourcentage doit être entre 0 et 100.")
        if kind in ("int", "pct"):
            num = int(num)
        return str(num), f"{num:g}" if kind == "number" else fmt(num)
    raise ValueError("Type de réglage inconnu.")


async def _set_config(ctx, key, raw, table=CONFIG_KEYS):
    if key not in table:
        await ctx.send("❄ Réglage inconnu. Liste : `+showconfig`.")
        return
    kind, label = table[key]
    try:
        stored, shown = _parse_config_value(ctx.guild, kind, raw)
    except ValueError as e:
        await ctx.send(f"❄ {e}")
        return
    db = connect()
    try:
        config_set(db, ctx.guild.id, key, stored)
        log_event(db, ctx.guild.id, ctx.author.id, "config", f"{key}={stored}")
    finally:
        db.close()
    await ctx.send(f"✅ **{label}** → {shown}", allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="config", help="Régler un paramètre du serveur (admins). <clé> <valeur>")
async def config_cmd(ctx, key: str, *, value: str):
    if not admin_check(ctx):
        await ctx.send(q("no_perm")); return
    await _set_config(ctx, key.lower(), value)


@bot.command(name="showconfig", help="Voir la configuration du serveur (admins).")
async def showconfig(ctx):
    if not admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        lines, missing = [], []
        for key, (kind, label) in CONFIG_KEYS.items():
            v = config_get(db, ctx.guild.id, key)
            if v in (None, ""):
                missing.append(key)
                continue
            if kind in ("channel", "category"):
                v = f"<#{v}>"
            elif kind == "role":
                v = f"<@&{v}>"
            elif kind == "bool":
                v = "activé" if v == "1" else "désactivé"
            lines.append(f"• `{key}` — {label} : **{v}**")
        text = "\n".join(lines) or "Aucun réglage défini pour l'instant."
        e = frost_embed(title="⚙️ Configuration du serveur", desc=text[:3800], color=ICE)
        if missing:
            e.add_field(name="Non définis (valeurs par défaut)", value=", ".join(f"`{m}`" for m in missing)[:1000],
                        inline=False)
        e.set_footer(text="Modifier : +config <clé> <valeur>")
        await ctx.send(embed=e)
    finally:
        db.close()


def _shortcut(name, key, helptext):
    @bot.command(name=name, help=helptext)
    async def _cmd(ctx, *, value: str):
        if not admin_check(ctx):
            await ctx.send(q("no_perm")); return
        await _set_config(ctx, key, value)
    _cmd.__name__ = f"cmd_{name}"
    return _cmd


_shortcut("setlog", "mod_log_channel_id", "Définir le salon unique des logs de modération (admins). <#salon>")
_shortcut("setwelcome", "welcome_channel_id", "Définir le salon d'accueil (admins). <#salon>")
_shortcut("setleave", "leave_channel_id", "Définir le salon des départs (admins). <#salon>")
_shortcut("setchest", "chest_channel_id", "Définir le salon des coffres COFFRESMUSK (admins). <#salon>")
_shortcut("setevent", "event_channel_id", "Définir le salon des événements et du boss (admins). <#salon>")
_shortcut("ticketcategory", "ticket_category_id", "Définir la catégorie des tickets (admins). <catégorie>")

ROLE_KEYS = {"admin": "admin_role_id", "mod": "mod_role_id", "ban": "ban_role_id",
             "ticket": "ticket_ping_role_id", "bump": "bump_role_id"}


@bot.command(name="setrole", help="Définir un rôle du bot (admins). <admin|mod|ban|ticket|bump> <@rôle>")
async def setrole(ctx, kind: str, *, role: str):
    if not admin_check(ctx):
        await ctx.send(q("no_perm")); return
    key = ROLE_KEYS.get(kind.lower())
    if not key:
        await ctx.send("❄ Types : " + ", ".join(f"`{k}`" for k in ROLE_KEYS)); return
    await _set_config(ctx, key, role)


# ── Réglages réservés au propriétaire (w.) ───────────────────────────
@bot.command(name="setfee", help="Frais interserveurs en % (propriétaire). <pourcentage>")
@owner_check()
async def setfee(ctx, pct: float):
    await _set_config(ctx, "cross_fee_pct", str(pct), table=OWNER_KEYS)


@bot.command(name="setcrosslimit", help="Limite quotidienne interserveurs (propriétaire). <montant>")
@owner_check()
async def setcrosslimit(ctx, amount: int):
    await _set_config(ctx, "cross_daily_limit", str(amount), table=OWNER_KEYS)


# ══════════════════════════════════════════════════════════════════════
#  A. ÉCONOMIE — commandes staff d'ajustement
# ══════════════════════════════════════════════════════════════════════
async def _money_admin(ctx, member, amount, column, mode):
    if not admin_check(ctx):
        await ctx.send(q("no_perm")); return
    if member.bot:
        await ctx.send("❄ Les bots n'ont pas de compte."); return
    if amount < (0 if mode == "set" else 1) or amount > MAX_AMOUNT:
        await ctx.send("❄ Montant invalide."); return
    db = connect()
    try:
        get_user(db, ctx.guild.id, member.id)
        if mode == "give":
            db.execute(f"UPDATE users SET {column}={column}+? WHERE guild_id=? AND user_id=?",
                       (amount, ctx.guild.id, member.id))
        else:
            db.execute(f"UPDATE users SET {column}=? WHERE guild_id=? AND user_id=?",
                       (amount, ctx.guild.id, member.id))
        add_tx(db, ctx.guild.id, member.id, f"admin_{mode}_{column}", amount)
        log_event(db, ctx.guild.id, ctx.author.id, f"admin_{mode}_{column}", f"{member.id} {amount}")
        db.commit()
    finally:
        db.close()
    unit = COIN if column == "wallet" else ef.MF
    verb = "reçoit" if mode == "give" else "est fixé(e) à"
    await ctx.send(f"✅ {member.mention} {verb} {unit} **{fmt(amount)}**.",
                   allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="givemoney", help="Donner des Crédits (admins). <@membre> <montant>")
async def givemoney(ctx, member: discord.Member, amount: int):
    await _money_admin(ctx, member, amount, "wallet", "give")


@bot.command(name="setmoney", help="Fixer le portefeuille d'un membre (admins). <@membre> <montant>")
async def setmoney(ctx, member: discord.Member, amount: int):
    await _money_admin(ctx, member, amount, "wallet", "set")


@bot.command(name="givemf", help="Donner des MF (admins). <@membre> <montant>")
async def givemf(ctx, member: discord.Member, amount: int):
    await _money_admin(ctx, member, amount, "mf", "give")


@bot.command(name="setmf", help="Fixer les MF d'un membre (admins). <@membre> <montant>")
async def setmf(ctx, member: discord.Member, amount: int):
    await _money_admin(ctx, member, amount, "mf", "set")


@bot.command(name="patrimoine", aliases=["assetvalue", "myassets"],
             help="Valeur de ton patrimoine : soldes + maisons + véhicules. [@membre]")
async def patrimoine(ctx, member: discord.Member = None):
    m = member or ctx.author
    db = connect()
    try:
        u = get_user(db, ctx.guild.id, m.id)
        houses = db.execute("SELECT COALESCE(SUM(value),0) FROM houses WHERE guild_id=? AND user_id=?",
                            (ctx.guild.id, m.id)).fetchone()[0]
        vehicles = db.execute("SELECT COALESCE(SUM(value),0) FROM vehicles WHERE guild_id=? AND user_id=?",
                              (ctx.guild.id, m.id)).fetchone()[0]
        total = u["wallet"] + u["bank"] + houses + vehicles
        e = frost_embed(title=f"🏛️ Patrimoine de {m.display_name}", color=ICE, fields=[
            (f"{COIN} Portefeuille + 🏦 Banque", fmt(u["wallet"] + u["bank"]), False),
            ("🏠 Maisons", fmt(houses), False),
            ("🚗 Véhicules", fmt(vehicles), False),
            ("✨ Total (chaque bien compté une seule fois)", f"**{fmt(total)}**", False)])
        await ctx.send(embed=e)
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════
#  BOUTIQUE NORMALE — administration (stock par article, ID stables)
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="shopadd", help="Ajouter un article à la boutique (admins). <prix> <nom>")
async def shopadd(ctx, price: int, *, name: str):
    if not admin_check(ctx):
        await ctx.send(q("no_perm")); return
    name = name.strip()
    if not (1 <= len(name) <= 80) or not (1 <= price <= 1_000_000_000):
        await ctx.send("❄ Nom (1–80 caractères) ou prix invalide."); return
    if any(w in name.lower() for w in ef.FORBIDDEN_SHOP_WORDS):
        await ctx.send("❄ Maisons, véhicules, téléphones, animaux et coffres n'ont pas leur place "
                       "dans la boutique normale (WINNERMUSK, Animalerie, COFFRESMUSK)."); return
    db = connect()
    try:
        ef.ensure_shop(db, ctx.guild.id)
        if db.execute("SELECT 1 FROM shops WHERE guild_id=? AND kind='regular' AND item=?",
                      (ctx.guild.id, name)).fetchone():
            await ctx.send("❄ Un article porte déjà ce nom."); return
        new_id = ef.next_shop_id(db, ctx.guild.id)
        db.execute("INSERT INTO shops (guild_id, kind, item, price, stock, item_id) VALUES (?,?,?,?,-1,?)",
                   (ctx.guild.id, "regular", name, price, new_id))
        db.commit()
        await ctx.send(f"🛍️ Article ajouté : `ID {new_id}` **{name}** — {COIN} {fmt(price)}.")
    finally:
        db.close()


async def _shop_edit(ctx, item_id, column, value, label):
    if not admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        ef.ensure_shop(db, ctx.guild.id)
        cur = db.execute(f"UPDATE shops SET {column}=? WHERE guild_id=? AND kind='regular' AND item_id=?",
                         (value, ctx.guild.id, item_id))
        db.commit()
        await ctx.send(f"✅ Article `ID {item_id}` : {label}." if cur.rowcount
                       else "❄ Aucun article avec cet ID.")
    finally:
        db.close()


@bot.command(name="shopstock", help="Régler le stock d'un article, -1 = illimité (admins). <ID> <stock>")
async def shopstock(ctx, item_id: int, stock: int):
    if stock < -1 or stock > 1_000_000:
        await ctx.send("❄ Stock invalide (-1 = illimité)."); return
    await _shop_edit(ctx, item_id, "stock", stock, f"stock = {'∞' if stock < 0 else stock}")


@bot.command(name="shopprice", help="Changer le prix d'un article (admins). <ID> <prix>")
async def shopprice(ctx, item_id: int, price: int):
    if not (1 <= price <= 1_000_000_000):
        await ctx.send("❄ Prix invalide."); return
    await _shop_edit(ctx, item_id, "price", price, f"prix = {fmt(price)}")


@bot.command(name="shopremove", help="Retirer un article de la boutique (admins). <ID>")
async def shopremove(ctx, item_id: int):
    if not admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        cur = db.execute("DELETE FROM shops WHERE guild_id=? AND kind='regular' AND item_id=?",
                         (ctx.guild.id, item_id))
        db.commit()
        await ctx.send(f"🗑️ Article `ID {item_id}` retiré." if cur.rowcount else "❄ Aucun article avec cet ID.")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════
#  D. TICKETS — commandes (en plus des boutons)
# ══════════════════════════════════════════════════════════════════════
def _open_ticket(db, ctx):
    return db.execute(
        "SELECT * FROM tickets WHERE guild_id=? AND channel_id=? AND status IN ('open','claimed')",
        (ctx.guild.id, ctx.channel.id)).fetchone()


@bot.command(name="claim", help="Prendre en charge le ticket du salon (staff).")
async def claim(ctx):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        t = _open_ticket(db, ctx)
        if not t:
            await ctx.send("❄ Ce salon n'est pas un ticket ouvert."); return
        if t["staff_id"]:
            await ctx.send(f"❄ Ticket déjà claimé par <@{t['staff_id']}> (claim exclusif). "
                           "Utilise `+chastaff` pour le réattribuer.",
                           allowed_mentions=discord.AllowedMentions.none()); return
        db.execute("UPDATE tickets SET staff_id=?, status='claimed' WHERE id=?", (ctx.author.id, t["id"]))
        db.commit()
        await ctx.send(f"✅ Ticket claimé par {ctx.author.mention}.")
    finally:
        db.close()


@bot.command(name="close", help="Fermer le ticket du salon (créateur ou staff). [raison]")
async def close(ctx, *, reason: str = ""):
    db = connect()
    try:
        t = _open_ticket(db, ctx)
        if not t:
            await ctx.send("❄ Ce salon n'est pas un ticket ouvert."); return
        if ctx.author.id != t["user_id"] and not mod_check(ctx):
            await ctx.send(q("no_perm")); return
        db.execute("UPDATE tickets SET status='closed', closed_at=? WHERE id=?", (now(), t["id"]))
        log_event(db, ctx.guild.id, ctx.author.id, "ticket_close", f"#{t['id']} {reason}".strip())
        db.commit()
        await ctx.send("🔒 Ticket fermé. Suppression du salon dans 5 secondes.")
        opener = ctx.guild.get_member(t["user_id"])
        if opener:
            try:
                v = discord.ui.View(timeout=None)
                for n in range(1, 6):
                    v.add_item(ef.RateButton(t["id"], n))
                await opener.send("❄ Merci pour ton passage. Note la qualité du staff :", view=v)
            except discord.HTTPException:
                pass
        await asyncio.sleep(5)
        try:
            await ctx.channel.delete(reason="ticket fermé")
        except discord.HTTPException:
            pass
    finally:
        db.close()


@bot.command(name="ticketadd", help="Ajouter un membre au ticket (staff). <@membre>")
async def ticketadd(ctx, member: discord.Member):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        if not _open_ticket(db, ctx):
            await ctx.send("❄ Ce salon n'est pas un ticket ouvert."); return
    finally:
        db.close()
    await ctx.channel.set_permissions(member, view_channel=True, send_messages=True,
                                      read_message_history=True)
    await ctx.send(f"➕ {member.mention} a été ajouté au ticket.")


@bot.command(name="ticketremove", help="Retirer un membre du ticket (staff). <@membre>")
async def ticketremove(ctx, member: discord.Member):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        t = _open_ticket(db, ctx)
        if not t:
            await ctx.send("❄ Ce salon n'est pas un ticket ouvert."); return
        if member.id == t["user_id"]:
            await ctx.send("❄ On ne retire pas le créateur du ticket : ferme-le avec `+close`."); return
    finally:
        db.close()
    await ctx.channel.set_permissions(member, overwrite=None)
    await ctx.send(f"➖ {member.mention} a été retiré du ticket.")


# ══════════════════════════════════════════════════════════════════════
#  E. GIVEAWAYS — réclamation sous 5 minutes
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="claimgw", help="Réclamer ton gain de giveaway (sous 5 min).")
async def claimgw(ctx):
    db = connect()
    try:
        init_extra_db(db)
        rows = db.execute(
            "SELECT * FROM giveaway_winners WHERE guild_id=? AND user_id=? AND claimed=0 "
            "ORDER BY claim_until DESC", (ctx.guild.id, ctx.author.id)).fetchall()
        if not rows:
            await ctx.send("❄ Aucun gain à réclamer."); return
        live = [r for r in rows if r["claim_until"] >= now()]
        if not live:
            await ctx.send("⏳ Trop tard : le délai de réclamation de 5 minutes est dépassé. "
                           "Le staff peut relancer avec `+gwreroll`."); return
        r = live[0]
        db.execute("UPDATE giveaway_winners SET claimed=1 WHERE guild_id=? AND message_id=? AND user_id=?",
                   (r["guild_id"], r["message_id"], r["user_id"]))
        log_event(db, ctx.guild.id, ctx.author.id, "giveaway_claim", r["prize"] or "")
        db.commit()
        await ctx.send(f"🎁 {ctx.author.mention} réclame **{r['prize']}** ! Le staff va te le remettre.")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════
#  I. WINNERMUSK — codes, patrimoine, revente
# ══════════════════════════════════════════════════════════════════════
def _new_code():
    alphabet = string.ascii_uppercase + string.digits
    return "WM-" + "".join(secrets.choice(alphabet) for _ in range(4)) + "-" + \
           "".join(secrets.choice(alphabet) for _ in range(4))


@bot.command(name="gencode", help="Créer un code WINNERMUSK à usage unique (propriétaire). "
                                  "<fixed|select> <objet>  ou  select <obj1> | <obj2> …")
@owner_check()
async def gencode(ctx, mode: str, *, items: str):
    mode = mode.lower()
    if mode not in ("fixed", "select"):
        await ctx.send("❄ Mode : `fixed` (objet précis) ou `select` (choix parmi plusieurs, séparés par `|`)."); return
    options = [i.strip() for i in items.split("|") if i.strip()]
    if not options or (mode == "fixed" and len(options) != 1) or (mode == "select" and len(options) < 2):
        await ctx.send("❄ `fixed` : un seul objet. `select` : au moins deux objets séparés par `|`."); return
    db = connect()
    try:
        for _ in range(10):
            code = _new_code()
            try:
                db.execute(
                    "INSERT INTO winner_codes (code, reward, mode, options, valid_until, used, created_by, created_at) "
                    "VALUES (?,?,?,?,0,0,?,?)",
                    (code, options[0] if mode == "fixed" else "", mode,
                     json.dumps(options, ensure_ascii=False), ctx.author.id, now()))
                db.commit()
                break
            except Exception:
                continue
        else:
            await ctx.send("❄ Impossible de générer un code unique, réessaie."); return
        log_event(db, ctx.guild.id if ctx.guild else None, ctx.author.id, "winner_code_created", mode)
    finally:
        db.close()
    text = f"🔑 Code **{code}** ({mode}) : " + " | ".join(options) + "\nUsage unique, sans expiration."
    try:   # jamais dans un salon public
        await ctx.author.send(text)
        await ctx.send("🔑 Code créé. Je te l'ai envoyé en message privé.")
    except discord.HTTPException:
        await ctx.send("❄ Je ne peux pas t'écrire en MP : ouvre tes messages privés puis recommence.")


@bot.command(name="code", help="Utiliser un code WINNERMUSK. <CODE> [choix]")
async def code_cmd(ctx, code: str, *, choice: str = ""):
    code = code.strip().upper()
    db = connect()
    try:
        row = db.execute("SELECT * FROM winner_codes WHERE code=?", (code,)).fetchone()
        if not row or row["used"]:
            await ctx.send("❄ Code invalide ou déjà utilisé."); return
        reward = row["reward"]
        if row["mode"] == "select":
            options = json.loads(row["options"] or "[]")
            if not choice.strip():
                await ctx.send("🔑 Ce code te laisse choisir : " + " | ".join(f"**{o}**" for o in options) +
                               f"\nExemple : `!code {code} {options[0]}`"); return
            match = next((o for o in options if o.lower() == choice.strip().lower()), None)
            if match is None:
                await ctx.send("❄ Choix invalide. Options : " + " | ".join(options)); return
            reward = match
        cur = db.execute("UPDATE winner_codes SET used=1, used_by=? WHERE code=? AND used=0",
                         (ctx.author.id, code))
        if cur.rowcount == 0:   # double utilisation simultanée
            db.rollback()
            await ctx.send("❄ Code invalide ou déjà utilisé."); return
        cat = db.execute("SELECT price FROM winner_catalog WHERE item=?", (reward,)).fetchone()
        value = cat["price"] if cat else 0
        db.execute("INSERT INTO winner_orders (guild_id, user_id, item, price, delivery, deliver_at, status, created_at) "
                   "VALUES (?,?,?,?,?,?,?,?)",
                   (ctx.guild.id, ctx.author.id, reward, 0, "code", now(), "delivered", now()))
        ef.deliver_winner_item(db, ctx.guild.id, ctx.author.id, reward, value)
        log_event(db, ctx.guild.id, ctx.author.id, "winner_code_used", code)
        db.commit()
        await ctx.send(f"👑 Code accepté ! **{reward}** est ajouté à ton patrimoine.")
    finally:
        db.close()


@bot.command(name="winnerassets", help="Tes biens et commandes WINNERMUSK.")
async def winnerassets(ctx, member: discord.Member = None):
    m = member or ctx.author
    db = connect()
    try:
        v = db.execute("SELECT name, value FROM vehicles WHERE guild_id=? AND user_id=?",
                       (ctx.guild.id, m.id)).fetchall()
        h = db.execute("SELECT name, value FROM houses WHERE guild_id=? AND user_id=?",
                       (ctx.guild.id, m.id)).fetchall()
        o = db.execute("SELECT item, deliver_at FROM winner_orders WHERE guild_id=? AND user_id=? "
                       "AND status='pending' ORDER BY deliver_at", (ctx.guild.id, m.id)).fetchall()
        lines = [f"🚗 **{r['name']}** — {fmt(r['value'])}" for r in v] + \
                [f"🏠 **{r['name']}** — {fmt(r['value'])}" for r in h] + \
                [f"📦 {r['item']} — livraison {fmt_ts(r['deliver_at'])}" for r in o]
        await ctx.send(embed=frost_embed(title=f"👑 Biens WINNERMUSK de {m.display_name}",
                                         desc="\n".join(lines) or "Aucun bien pour l'instant.", color=EXCL))
    finally:
        db.close()


@bot.command(name="winnersell", help="Revendre un bien WINNERMUSK à 60 % de sa valeur. <nom du bien>")
async def winnersell(ctx, *, item: str):
    db = connect()
    try:
        for table in ("vehicles", "houses"):
            row = db.execute(f"SELECT name, value FROM {table} WHERE guild_id=? AND user_id=? "
                             "AND lower(name)=lower(?)", (ctx.guild.id, ctx.author.id, item.strip())).fetchone()
            if row:
                cur = db.execute(f"DELETE FROM {table} WHERE guild_id=? AND user_id=? AND name=?",
                                 (ctx.guild.id, ctx.author.id, row["name"]))
                if cur.rowcount == 0:
                    break
                refund = int(row["value"] * 0.6)
                get_user(db, ctx.guild.id, ctx.author.id)
                db.execute("UPDATE users SET wallet=wallet+? WHERE guild_id=? AND user_id=?",
                           (refund, ctx.guild.id, ctx.author.id))
                add_tx(db, ctx.guild.id, ctx.author.id, "winner_sell", refund)
                db.commit()
                await ctx.send(f"💰 **{row['name']}** revendu pour {COIN} **{fmt(refund)}** (60 %).")
                return
        await ctx.send("❄ Tu ne possèdes pas ce bien. Voir `!winnerassets`.")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════
#  PROPRIÉTAIRE — activité, journal, serveurs
# ══════════════════════════════════════════════════════════════════════
ACTIVITIES = ["code", "Emilia Frost ❄️", "WINNERMUSK 👑"]
_activity_idx = {"i": 0}


async def apply_activity():
    db = connect()
    try:
        manual = config_get(db, 0, "activity_manual", "") or ""
    finally:
        db.close()
    if manual:
        text = manual
    else:
        text = ACTIVITIES[_activity_idx["i"] % len(ACTIVITIES)]
        _activity_idx["i"] += 1
    await bot.change_presence(activity=discord.Game(name=text[:120]))


@tasks.loop(minutes=10)
async def activity_loop():
    try:
        await apply_activity()
    except Exception as ex:
        print("activity_loop:", ex)


@activity_loop.before_loop
async def _before_activity():
    await bot.wait_until_ready()


@bot.command(name="activity", help="Activité du bot (propriétaire). <texte> | auto")
@owner_check()
async def activity(ctx, *, text: str = ""):
    db = connect()
    try:
        if not text.strip():
            cur = config_get(db, 0, "activity_manual", "") or "auto (rotation)"
            await ctx.send(f"🎭 Activité actuelle : **{cur}**. `w.activity <texte>` ou `w.activity auto`."); return
        if text.strip().lower() == "auto":
            config_set(db, 0, "activity_manual", "")
            msg = "🎭 Rotation automatique rétablie."
        else:
            config_set(db, 0, "activity_manual", text.strip()[:120])
            msg = f"🎭 Activité fixée : **{text.strip()[:120]}** (conservée après redémarrage)."
    finally:
        db.close()
    await apply_activity()
    await ctx.send(msg)


def _journal_channel(guild):
    db = connect()
    try:
        cid = config_get(db, guild.id, "journal_channel_id")
    finally:
        db.close()
    if cid:
        ch = guild.get_channel(int(cid))
        if ch:
            return ch
    return next((c for c in guild.text_channels if "journal" in c.name.lower()), None)


@bot.command(name="journal", help="Publier un message dans le journal de chaque serveur (propriétaire). <message>")
@owner_check()
async def journal(ctx, *, message: str):
    sent, failed = 0, 0
    for g in bot.guilds:
        ch = _journal_channel(g)
        if ch is None:
            failed += 1
            continue
        try:
            await ch.send(embed=frost_embed(title="📖 Journal d'Emilia Frost", desc=message[:3500], color=FROST),
                          allowed_mentions=discord.AllowedMentions.none())
            sent += 1
        except discord.HTTPException:
            failed += 1
    await ctx.send(f"📖 Publié dans **{sent}** serveur(s) ; indisponible dans **{failed}**.")


@bot.command(name="servers", help="Liste des serveurs d'Emilia Frost (propriétaire).")
@owner_check()
async def servers(ctx):
    lines = [f"• **{g.name}** — {g.member_count} membres" for g in sorted(bot.guilds, key=lambda x: -x.member_count)]
    await ctx.send(embed=frost_embed(title=f"🌍 {len(bot.guilds)} serveur(s)",
                                     desc="\n".join(lines)[:3800] or "Aucun.", color=ICE))


# ══════════════════════════════════════════════════════════════════════
#  CYCLE DE VIE — installation, départ / retour, vérification
# ══════════════════════════════════════════════════════════════════════
INTRO_TEXT = (
    "« Je suis **Emilia Frost**. Économie, progression, familles, tickets, événements… tout ce qu'il faut "
    "pour faire vivre un serveur — avec un peu de froid et beaucoup de style. »\n\n"
    "**Préfixes** : `!` commandes des membres · `+` staff & modération · `/` commandes slash.\n"
    "**Aide** : `!help` (membres) · `+help` (staff).\n"
    "**Pour commencer (admins)** : `+showconfig` puis `+setlog`, `+setwelcome`, `+setchest`…")


async def _send_intro(guild):
    db = connect()
    try:
        if config_get(db, guild.id, "intro_sent"):
            return
        target = guild.system_channel
        if target is None or not target.permissions_for(guild.me).send_messages:
            target = next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
        # le marqueur est posé même sans salon : on ne réessaie pas à chaque redémarrage
        config_set(db, guild.id, "intro_sent", str(now()))
    finally:
        db.close()
    if target:
        try:
            await target.send(embed=frost_embed(title="❄ Emilia Frost est arrivée", desc=INTRO_TEXT, color=ICE))
        except discord.HTTPException:
            pass


_recent_bans = {}


@bot.listen("on_member_ban")
async def _on_ban(guild, user):
    _recent_bans[(guild.id, user.id)] = time.time()


def _is_dangerous(role: discord.Role) -> bool:
    p = role.permissions
    return bool(p.administrator or p.manage_guild or p.manage_roles or p.ban_members or p.kick_members
                or p.manage_channels or p.manage_webhooks)


@bot.listen("on_member_remove")
async def _on_leave(member):
    if member.bot:
        return
    g = member.guild
    role_ids = [r.id for r in member.roles if not r.is_default() and not r.managed]
    db = connect()
    try:
        init_extra_db(db)
        if role_ids:
            db.execute("INSERT INTO member_roles (guild_id, user_id, role_ids, left_at) VALUES (?,?,?,?) "
                       "ON CONFLICT(guild_id, user_id) DO UPDATE SET role_ids=excluded.role_ids, left_at=excluded.left_at",
                       (g.id, member.id, json.dumps(role_ids), now()))
            db.commit()
    finally:
        db.close()
    await asyncio.sleep(2)   # laisse arriver l'événement de bannissement
    banned_at = _recent_bans.pop((g.id, member.id), 0)
    if time.time() - banned_at < 30:
        return   # un bannissement ne déclenche pas le message de départ ordinaire
    try:
        await member.send(f"❄ Tu as quitté **{g.name}**. Ton économie, ta progression et tes participations "
                          "sont conservées : si tu reviens, tout sera restauré.")
    except (discord.HTTPException, AttributeError):
        db = connect()
        try:
            log_event(db, g.id, member.id, "leave_dm_failed", "")
        finally:
            db.close()


def _verif_question():
    a, b = secrets.randbelow(8) + 2, secrets.randbelow(8) + 2
    return f"{a} + {b}", a + b


@bot.listen("on_member_join")
async def _on_join(member):
    if member.bot:
        return
    g = member.guild
    db = connect()
    try:
        init_extra_db(db)
        banned = db.execute("SELECT 1 FROM role_bans WHERE guild_id=? AND user_id=?", (g.id, member.id)).fetchone()
        saved = db.execute("SELECT role_ids FROM member_roles WHERE guild_id=? AND user_id=?",
                           (g.id, member.id)).fetchone()
        known = db.execute("SELECT 1 FROM users WHERE guild_id=? AND user_id=?", (g.id, member.id)).fetchone()
        unverified_id = config_get(db, g.id, "verif_role_unverified")
        member_id = config_get(db, g.id, "verif_role_member")
        verif_on = config_get(db, g.id, "verif_enabled") == "1" and unverified_id and member_id
    finally:
        db.close()
    # retour : restauration sans doublon des rôles encore valides (jamais les rôles dangereux, ni si role-ban)
    restored = []
    if saved and not banned:
        for rid in json.loads(saved["role_ids"]):
            role = g.get_role(rid)
            if (role and not role.managed and role < g.me.top_role and not _is_dangerous(role)
                    and role not in member.roles and str(rid) != str(unverified_id)):
                restored.append(role)
        if restored:
            try:
                await member.add_roles(*restored, reason="Restauration au retour")
            except discord.HTTPException:
                restored = []
    if known:
        try:
            await member.send(f"❄ Bon retour sur **{g.name}** ! Tes données ont été restaurées"
                              + (f" ({len(restored)} rôle(s) rendu(s))." if restored else "."))
        except discord.HTTPException:
            pass
    # vérification
    if not verif_on:
        return
    mrole = g.get_role(int(member_id))
    if mrole and mrole in member.roles:
        return   # déjà vérifié avant son départ
    urole = g.get_role(int(unverified_id))
    if urole:
        try:
            await member.add_roles(urole, reason="Vérification à l'arrivée")
        except discord.HTTPException:
            return
    text, answer = _verif_question()
    db = connect()
    try:
        db.execute("INSERT INTO verif_pending (guild_id, user_id, answer, tries, created_at) VALUES (?,?,?,0,?) "
                   "ON CONFLICT(guild_id, user_id) DO UPDATE SET answer=excluded.answer, tries=0, created_at=excluded.created_at",
                   (g.id, member.id, answer, now()))
        db.commit()
    finally:
        db.close()
    try:
        await member.send(f"🔒 Bienvenue sur **{g.name}** ! Pour entrer, réponds par un nombre : "
                          f"**combien font {text} ?** (3 essais)")
    except discord.HTTPException:
        db = connect()
        try:
            log_event(db, g.id, member.id, "verif_dm_closed", "DM fermés : validation manuelle (+verify)")
        finally:
            db.close()


async def _grant_member(guild, member, db):
    urole = guild.get_role(int(config_get(db, guild.id, "verif_role_unverified") or 0))
    mrole = guild.get_role(int(config_get(db, guild.id, "verif_role_member") or 0))
    if urole and urole in member.roles:
        await member.remove_roles(urole, reason="Vérifié")
    if mrole:
        await member.add_roles(mrole, reason="Vérifié")
    db.execute("DELETE FROM verif_pending WHERE guild_id=? AND user_id=?", (guild.id, member.id))
    db.commit()


@bot.listen("on_message")
async def _verif_dm_answer(message):
    if message.author.bot or message.guild is not None:
        return
    m = re.fullmatch(r"\s*(\d{1,3})\s*", message.content or "")
    if not m:
        return
    db = connect()
    try:
        init_extra_db(db)
        row = db.execute("SELECT * FROM verif_pending WHERE user_id=? AND tries<3 ORDER BY created_at DESC LIMIT 1",
                         (message.author.id,)).fetchone()
        if not row:
            return
        guild = bot.get_guild(row["guild_id"])
        member = guild.get_member(message.author.id) if guild else None
        if not member:
            return
        if int(m.group(1)) == row["answer"]:
            await _grant_member(guild, member, db)
            log_event(db, guild.id, member.id, "verif_ok", "")
            await message.channel.send(f"✅ Bien joué ! Bienvenue sur **{guild.name}**.")
        else:
            tries = row["tries"] + 1
            db.execute("UPDATE verif_pending SET tries=? WHERE guild_id=? AND user_id=?",
                       (tries, row["guild_id"], row["user_id"]))
            db.commit()
            if tries >= 3:
                log_event(db, guild.id, member.id, "verif_failed", "3 essais ratés")
                await message.channel.send("❄ Trop d'erreurs. Contacte le staff pour être validé manuellement.")
            else:
                await message.channel.send(f"❄ Mauvaise réponse. Il te reste **{3 - tries}** essai(s).")
    finally:
        db.close()


@bot.command(name="verify", help="Valider manuellement un membre non vérifié (staff). <@membre>")
async def verify(ctx, member: discord.Member):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        if not config_get(db, ctx.guild.id, "verif_role_member"):
            await ctx.send("❄ La vérification n'est pas configurée (`+verifsetup`)."); return
        await _grant_member(ctx.guild, member, db)
        log_event(db, ctx.guild.id, ctx.author.id, "verif_manual", str(member.id))
    finally:
        db.close()
    await ctx.send(f"✅ {member.mention} est validé(e).", allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="verifsetup", help="Activer la vérification (admins). <@Non vérifié> <@Membre>  |  off")
async def verifsetup(ctx, first: str, second: str = ""):
    if not admin_check(ctx):
        await ctx.send(q("no_perm")); return
    db = connect()
    try:
        if first.lower() == "off":
            config_set(db, ctx.guild.id, "verif_enabled", "0")
            await ctx.send("🔓 Vérification désactivée."); return
        try:
            u, _ = _parse_config_value(ctx.guild, "role", first)
            m, _ = _parse_config_value(ctx.guild, "role", second)
        except ValueError as e:
            await ctx.send(f"❄ {e} Syntaxe : `+verifsetup @NonVérifié @Membre`."); return
        config_set(db, ctx.guild.id, "verif_role_unverified", u)
        config_set(db, ctx.guild.id, "verif_role_member", m)
        config_set(db, ctx.guild.id, "verif_enabled", "1")
        await ctx.send("🔒 Vérification activée : les nouveaux reçoivent une question simple en MP.\n"
                       "*Bloque l'accès aux salons pour le rôle non vérifié dans les permissions Discord.*")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════
#  AIDE — générée depuis le registre réel des commandes, filtrée par préfixe
# ══════════════════════════════════════════════════════════════════════
CATEGORIES = {
    "💰 Économie": {"daily", "work", "mine", "solde", "bank", "payer", "top", "markets", "buy", "inventaire",
                    "marche", "marchebuy", "marchesell", "echange", "echangeaccept", "enchere", "encherebuy",
                    "revente", "blackmarket", "facture", "patrimoine", "transfertinter", "emprunt", "rembourser",
                    "assurance", "caisse"},
    "📈 Progression": {"profil", "succes", "missions", "missionclaim", "rankup", "quitterstaff", "setrankstaff",
                       "salaire", "statup", "stats", "anniversaire"},
    "🎮 Jeux & activités": {"pileouface", "des", "roulette", "blackjack", "courses", "raid", "attack", "kill",
                            "block", "chest", "toc", "printemps", "carburant", "ballonor", "ballonpayprice"},
    "🐾 Animaux & garage": {"animal", "garage", "reproduire", "combat", "dresser", "recuperation", "winphone"},
    "👑 WINNERMUSK": {"winner", "winnerbuy", "winnerassets", "winnersell", "code", "winneradd", "gencode"},
    "👪 Familles & gouvernement": {"famille", "guerre", "election", "gouvernement", "vote", "loi", "lois"},
    "🛡️ Modération": {"warn", "warnhistory", "ban", "banned", "unban", "setbanrole", "clear", "lock", "unlock",
                      "mute", "unmute", "kick", "slowmode", "nick", "automod", "starboard", "amende"},
    "⛓️ Prison": {"imprison", "prisonstatus", "prisonhistory", "release", "prisonbailrate", "evader"},
    "📩 Tickets & giveaways": {"ticketpanel", "ticketping", "ticketnote", "ticketnotes", "claim", "close",
                               "ticketadd", "ticketremove", "chastaff", "giveaway", "gwreroll", "claimgw"},
    "⚙️ Administration": {"config", "showconfig", "setlog", "setwelcome", "setleave", "setchest", "setevent",
                          "setrole", "ticketcategory", "givemoney", "setmoney", "givemf", "setmf", "shopadd",
                          "shopstock", "shopprice", "shopremove", "adminabuse", "setprefix", "autosuivi",
                          "autoreactrole", "verify", "verifsetup", "setfee", "setcrosslimit", "dashboard",
                          "activity", "journal", "servers"},
    "📡 Serveur & infos": {"bump", "invites", "topinvites", "userinfo", "serverinfo", "avatar", "banner",
                           "roleinfo", "channelinfo", "ping", "statsbot", "invite", "prefix", "menu", "help"},
}


def _category_of(name):
    for cat, names in CATEGORIES.items():
        if name in names:
            return cat
    return "✨ Divers"


def _prefix_for(kind, guild_id):
    return {"owner": "w.", "staff": "+", "member": ef._member_prefix(guild_id)}[kind]


def _syntax(cmd, prefix):
    return f"{prefix}{cmd.qualified_name} {cmd.signature}".strip()


def _example(cmd, prefix):
    parts = []
    for p in cmd.clean_params.values():
        ann = p.annotation
        name = getattr(ann, "__name__", "")
        parts.append("@membre" if name == "Member" else "@rôle" if name == "Role" else
                     "#salon" if "Channel" in name else "10" if name in ("int", "float") else p.name)
    return f"{prefix}{cmd.qualified_name} " + " ".join(parts)


PERM_LABEL = {"owner": "Propriétaire du bot uniquement (ID Discord configuré)",
              "staff": "Staff / modérateurs / administrateurs (permissions Discord et hiérarchie vérifiées)",
              "member": "Tous les membres"}


def _visible_commands(kind):
    return sorted((c for c in bot.commands if kind_of(c) == kind and not c.hidden), key=lambda c: c.name)


async def _send_chunks(ctx, title, lines, color=ICE):
    chunk, pages = "", []
    for line in lines:
        if len(chunk) + len(line) + 1 > 3800:
            pages.append(chunk)
            chunk = ""
        chunk += line + "\n"
    if chunk:
        pages.append(chunk)
    for i, page in enumerate(pages or ["Aucune commande."], 1):
        suffix = f" ({i}/{len(pages)})" if len(pages) > 1 else ""
        await ctx.send(embed=frost_embed(title=title + suffix, desc=page, color=color))


for _n in ("help", "aide", "commandes"):
    bot.remove_command(_n)   # remplace l'ancienne aide par celle filtrée par préfixe

@bot.command(name="help", aliases=["aide", "commandes"],
             help="Aide : liste par catégorie ou détail d'une commande. [catégorie|commande]")
async def help_cmd(ctx, *, topic: str = ""):
    used = (ctx.prefix or "").strip().lower()
    kind = "owner" if used == "w." else "staff" if used == "+" else "member"
    prefix = _prefix_for(kind, ctx.guild.id if ctx.guild else None)
    cmds = _visible_commands(kind)
    topic = topic.strip().lower().lstrip("+!/").removeprefix("w.")
    if topic:
        cmd = next((c for c in cmds if c.name == topic or topic in c.aliases), None)
        if cmd:
            e = frost_embed(title=f"❄ {prefix}{cmd.name}", desc=cmd.help or "—", color=ICE, fields=[
                ("Syntaxe", f"`{_syntax(cmd, prefix)}`", False),
                ("Exemple", f"`{_example(cmd, prefix)}`", False),
                ("Alias", ", ".join(f"`{a}`" for a in cmd.aliases) or "—", True),
                ("Permissions", PERM_LABEL[kind], False)])
            await ctx.send(embed=e)
            return
        matching = [c for c in cmds if topic in _category_of(c.name).lower()]
        if matching:
            lines = [f"`{prefix}{c.name}` — {(c.help or '').split('.')[0]}" for c in matching]
            await _send_chunks(ctx, f"❄ {_category_of(matching[0].name)}", lines)
            return
        await ctx.send(f"❄ Rien trouvé pour « {topic} ». Essaie `{prefix}help` pour la liste.")
        return
    by_cat = {}
    for c in cmds:
        by_cat.setdefault(_category_of(c.name), []).append(c)
    titles = {"member": "Commandes membres", "staff": "Commandes staff", "owner": "Commandes propriétaire"}
    lines = [f"**{cat}** — {len(items)} commande(s)\n" + " ".join(f"`{c.name}`" for c in items)
             for cat, items in sorted(by_cat.items())]
    lines.append(f"\nDétail : `{prefix}help <commande>` · catégorie : `{prefix}help <mot de la catégorie>`")
    await _send_chunks(ctx, f"❄ {titles[kind]} ({len(cmds)}) — préfixe `{prefix}`", lines)


# ══════════════════════════════════════════════════════════════════════
#  DÉMARRAGE
# ══════════════════════════════════════════════════════════════════════
async def _setup_hook():
    # vues persistantes : fonctionnent après redémarrage, pour tous les serveurs
    bot.add_view(ef.TicketCreateView())
    bot.add_view(ef.TicketClaimView())
    bot.add_view(ef.GiveawayJoinView())
    bot.add_dynamic_items(ef.RateButton)
    if not activity_loop.is_running():
        activity_loop.start()


bot.setup_hook = _setup_hook


@bot.listen("on_ready")
async def _on_ready_extra():
    for guild in bot.guilds:
        try:
            await _send_intro(guild)
        except Exception as ex:
            print("intro:", ex)


for _alias, _target in (("level", "profil"), ("bail", "release"), ("winnerstore", "winner"),
                        ("ballondor", "ballonor")):
    add_alias(_target, _alias)


def main():
    db = connect()
    ef.init_db(db)
    ef.init_db_complements(db)
    init_extra_db(db)
    db.close()
    if not ef.TOKEN:
        raise SystemExit("DISCORD_TOKEN manquant : ajoute la variable DISCORD_TOKEN dans Railway.")
    bot.run(ef.TOKEN)


if __name__ == "__main__":
    main()
