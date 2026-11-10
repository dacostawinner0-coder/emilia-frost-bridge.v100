"""
════════════════════════════════════════════════════════════════════════
  E M I L I A   F R O S T  —  Bot Discord multi-serveur
════════════════════════════════════════════════════════════════════════
  Fichier unique consolidant le cahier des charges complet
  (CAHIER_COMPLET_EMILIA_FROST_2026-11-06.md, annexes 1, 2 et 3).

  Identité : bleu glacier, blanc, violet pastel. Ambiance féminine,
  douce, moderne et soignée. Ton d'Emilia : froid, élégant, taquin.

  Modules :
    A. Économie & patrimoine   K. Banque centrale        S. Kill & Block
    B. Progression & staff     L. Prison                 T. Bump
    C. Modération & sécurité   M. Familles               U. Invites
    D. Tickets                 N. Garage & assurances   V. AutoReactRole
    E. Giveaways               O. Marché dynamique       W. Tickets ping
    F. Jeux & activités        P. Missions               X. Taxes & aide
    G. Gouvernement            Q. Budget public          Y. Emprunts
    H. Administration          R. Succès                 Z. Winterfest
    I. WINNERMUSK (protégé)
    J. Expérience & identité
════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import functools
import json
import os
import random
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

# ══════════════════════════════════════════════════════════════════════
#  IDENTITÉ VISUELLE — palette Emilia Frost
# ══════════════════════════════════════════════════════════════════════
ICE    = 0x7EC8E3   # bleu glacier
FROST  = 0x9B8CFF   # violet pastel
SNOW   = 0xF5F9FF   # blanc givré
GOLD   = 0xFFD700   # or (légendaire)
MYTH   = 0xC471ED   # mythique
EXCL   = 0xFF4D6D   # exclusif
GREEN  = 0x6BFFA3   # gain
RED    = 0xFF6B6B   # perte
DARK   = 0x1B2735   # fond sombre

EMILIA = "Emilia Frost"
COIN, CORE, MF = "⚙️", "🔮", "💎"

RARETIES = ["Normal", "Légendaire", "Mythique", "Exclusif"]   # 4 exactes
RARE_STYLE = {
    "Normal":     (SNOW,   "📦"),
    "Légendaire": (GOLD,   "🏆"),
    "Mythique":   (MYTH,   "🌀"),
    "Exclusif":   (EXCL,   "👑"),
}

# ══════════════════════════════════════════════════════════════════════
#  MOTEUR DE PERSONNALITÉ — phrases froides, élégantes, variées
# ══════════════════════════════════════════════════════════════════════
PHRASES = {
    "greet": [
        "« Tu m'appelles ? …Sois bref. »",
        "« Encore toi. Très bien, je t'écoute — un peu. »",
        "« J'étais en train de réfléchir à des choses plus intéressantes. Continue. »",
        "« Bonjour. Oui, oui, je suis là. »",
    ],
    "work": [
        "« Faisable. Mais ne t'imagine rien, c'était facile. »",
        "« Tu as sué pour ça. Moi, j'ai juste regardé. »",
        "« Correct. Assez pour que je ne te juge pas aujourd'hui. »",
        "« Le travail, c'est la base. Tu viens de le prouver, à peine. »",
        "« J'aurais fait mieux en une minute. Mais bon… »",
    ],
    "daily": [
        "« Chaque jour, tu reviens. J'apprécie la ponctualité, même chez toi. »",
        "« Ta présence est… tolérable. Voici ta récompense. »",
        "« Punctuel. C'est la seule qualité que je te reconnais aujourd'hui. »",
        "« Encore une journée de plus. Ne m'attends pas à être impressionnée. »",
    ],
    "mine": [
        "« La mine, c'est pour ceux qui acceptent la saleté. Bravos. »",
        "« Tu es descendu sous terre. J'espère que ça t'a appris quelque chose. »",
        "« Des pépites. Ou des cailloux. Le destin a tranché. »",
    ],
    "win": [
        "« Chance. Ou talent. Peu m'importe, tu as gagné. »",
        "« Intéressant. Tu m'as surprise, cette fois. »",
        "« Gagné. Essaie de ne pas t'enfler la tête. »",
    ],
    "lose": [
        "« Perdu. La glace ne se brise pas pour tout le monde. »",
        "« La défaite fait partie du jeu. Apprends-en quelque chose. »",
        "« Perdu. Comme toujours, peut-être. »",
    ],
    "pay": [
        "« Transaction scellée. Ne reviens pas me remercier. »",
        "« L'argent change de main. Les sentiments, non. »",
    ],
    "shop": [
        "« Acheter ? Sois au moins élégant dans tes choix. »",
        "« Ma boutique n'a pas besoin de publicité. Mais elle est ouverte. »",
    ],
    "chest": [
        "« Un coffre. Ose l'ouvrir, mais ne pleure pas si c'est décevant. »",
        "« La chance frappe. Toi, tu dois juste être là. »",
    ],
    "error": [
        "« Cette commande n'existe pas. Ou toi, pas assez. »",
        "« Erreur. Relis-moi, je ne me répète jamais. »",
        "« Non. Et non. »",
    ],
    "no_perm": [
        "« Cette commande n'est pas pour toi. Va jouer ailleurs. »",
        "« L'élégance, c'est savoir sa place. »",
    ],
    "ban": [
        "« Banni. La glace n'oublie pas. »",
        "« Expulsé de mon domaine. Bonne route. »",
    ],
    "boss": [
        "« Le boss est là. Sois utile ou sois de la glace. »",
        "« Il apparaît. Tous les froids sont les bienvenus. »",
    ],
    "love": [
        "« …Quoi ? Non. »",
        "« Je suis une IA. Mes sentiments sont en mode économie d'énergie. »",
    ],
    "success": [
        "« Succès débloqué. Prends une photo, c'est rare que j'admire quelqu'un. »",
        "« Voilà. Tu as fait quelque chose de bien. Note-le. »",
    ],
}

def q(kind: str) -> str:
    """Une phrase froide aléatoire d'Emilia pour le contexte donné."""
    return random.choice(PHRASES.get(kind, PHRASES["greet"]))

def fmt(n) -> str:
    """Formatage des montants : 1 234 567."""
    try:
        n = int(float(n))
    except (TypeError, ValueError):
        return str(n)
    return f"{n:,}".replace(",", " ")

def now() -> int:
    return int(time.time())

def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

def remaining(until: int) -> str:
    s = max(0, until - now())
    d, r = divmod(s, 86400)
    h, r = divmod(r, 3600)
    m, sec = divmod(r, 60)
    if d:  return f"{d} j {h} h {m} min"
    if h:  return f"{h} h {m} min"
    if m:  return f"{m} min {sec} s"
    return f"{sec} s"

# ══════════════════════════════════════════════════════════════════════
#  EMBEDS — style givré, cohérent, soigné
# ══════════════════════════════════════════════════════════════════════
def frost_embed(title=None, desc=None, color=ICE, fields=None,
                author=None, thumbnail=None, image=None) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=color)
    if fields:
        for f in fields:
            if len(f) == 2:
                name, value = f; inline = False
            else:
                name, value, inline = f
            e.add_field(name=name, value=value, inline=inline)
    if author:
        e.set_author(name=author[0], icon_url=author[1] if len(author) > 1 else None)
    if thumbnail:
        e.set_thumbnail(url=thumbnail)
    if image:
        e.set_image(url=image)
    e.set_footer(text=f"❄ {EMILIA} — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    e.timestamp = datetime.now(timezone.utc)
    return e

def quote_embed(desc, color=ICE, title=None, fields=None, thumbnail=None):
    """Embed avec la citation d'Emilia en italique en tête."""
    return frost_embed(title=title, desc=desc, color=color,
                       fields=fields, thumbnail=thumbnail)

# ══════════════════════════════════════════════════════════════════════
#  ANIMATION — typing + message révélé par étapes (style grands bots)
# ══════════════════════════════════════════════════════════════════════
async def reveal(ctx, chunks, final_embed=None, delay=0.35, typing=True):
    """Envoie le message en plusieurs temps (effet machine à écrire).

    chunks : liste de blocs de texte révélés successivement.
    final_embed : embed final affiché à la fin (remplace le texte si donné).
    """
    if typing:
        ctx._emilia_typing = ctx.typing()
        await ctx._emilia_typing.__aenter__()
    try:
        msg = await ctx.send(chunks[0])
        acc = chunks[0]
        for chunk in chunks[1:]:
            await asyncio.sleep(delay)
            acc = (acc + "\n" + chunk).strip() if acc else chunk
            await msg.edit(content=acc)
        if final_embed is not None:
            await asyncio.sleep(delay * 0.6)
            await msg.edit(embed=final_embed)
        return msg
    finally:
        t = getattr(ctx, "_emilia_typing", None)
        if t is not None:
            ctx._emilia_typing = None
            try:
                await t.__aexit__(None, None, None)
            except Exception:
                pass

async def shimmer(ctx, text, times=3, delay=0.18):
    """Petit effet d'animation sur un message (cristallisation)."""
    msg = await ctx.send(text)
    variants = [text, "🤍 " + text, "❄ " + text, "🤍 " + text, "❄ " + text, text]
    for i in range(1, min(times * 2, len(variants))):
        await asyncio.sleep(delay)
        try:
            await msg.edit(content=variants[i])
        except discord.HTTPException:
            break
    return msg

# ══════════════════════════════════════════════════════════════════════
#  BASE DE DONNÉES — SQLite WAL, multi-serveur strict
# ══════════════════════════════════════════════════════════════════════
DB_PATH = os.getenv("DATABASE_PATH", "database/bot.db")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    return db

def _backup_database(db):
    """Sauvegarde horodatée avant toute migration destructive."""
    try:
        os.makedirs("backups", exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        src = os.path.abspath(DB_PATH)
        dst = f"backups/bot_{stamp}.db"
        if os.path.exists(src):
            import shutil
            shutil.copy2(src, dst)
    except Exception:
        pass

SCHEMA = [
    # ── Membre (clé composite guild_id, user_id) ────────────────────────
    """CREATE TABLE IF NOT EXISTS users (
        guild_id  INTEGER NOT NULL,
        user_id   INTEGER NOT NULL,
        wallet    INTEGER NOT NULL DEFAULT 0 CHECK (wallet >= 0),
        bank      INTEGER NOT NULL DEFAULT 0 CHECK (bank >= 0),
        xp        INTEGER NOT NULL DEFAULT 0,
        level     INTEGER NOT NULL DEFAULT 1,
        cores     INTEGER NOT NULL DEFAULT 0,
        mf        INTEGER NOT NULL DEFAULT 0,
        daily_streak INTEGER NOT NULL DEFAULT 0,
        last_daily INTEGER NOT NULL DEFAULT 0,
        last_work  INTEGER NOT NULL DEFAULT 0,
        last_mine  INTEGER NOT NULL DEFAULT 0,
        last_kill  INTEGER NOT NULL DEFAULT 0,
        last_chest INTEGER NOT NULL DEFAULT 0,
        last_tax   INTEGER NOT NULL DEFAULT 0,
        last_aid   INTEGER NOT NULL DEFAULT 0,
        last_interest INTEGER NOT NULL DEFAULT 0,
        job       TEXT,
        staff_rank TEXT,
        family_id INTEGER,
        family_role TEXT,
        family_left_at INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS config (
        guild_id INTEGER NOT NULL,
        key      TEXT NOT NULL,
        value    TEXT,
        PRIMARY KEY (guild_id, key)
    )""",
    """CREATE TABLE IF NOT EXISTS transactions (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id   INTEGER NOT NULL,
        user_id    INTEGER NOT NULL,
        action     TEXT NOT NULL,
        amount     INTEGER NOT NULL,
        created_at INTEGER NOT NULL
    )""",
    """CREATE INDEX IF NOT EXISTS idx_tx_guild_user ON transactions (guild_id, user_id, created_at)""",
    # ── Staff / niveaux ─────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS rank_roles (
        guild_id INTEGER NOT NULL, rank TEXT NOT NULL, role_id INTEGER NOT NULL,
        PRIMARY KEY (guild_id, rank)
    )""",
    """CREATE TABLE IF NOT EXISTS level_roles (
        guild_id INTEGER NOT NULL, level INTEGER NOT NULL, role_id INTEGER NOT NULL,
        PRIMARY KEY (guild_id, level)
    )""",
    """CREATE TABLE IF NOT EXISTS rank_caps (
        guild_id INTEGER NOT NULL, rank TEXT NOT NULL, cap INTEGER NOT NULL,
        PRIMARY KEY (guild_id, rank)
    )""",
    # ── Modération ──────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS warnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        reason TEXT, by_id INTEGER, created_at INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS role_bans (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        reason TEXT, by_id INTEGER, created_at INTEGER NOT NULL,
        removed_roles TEXT, PRIMARY KEY (guild_id, user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS prison (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        reason TEXT, by_id INTEGER,
        started_at INTEGER NOT NULL, released_at INTEGER NOT NULL,
        released INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS sanctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        kind TEXT NOT NULL, reason TEXT, by_id INTEGER, created_at INTEGER NOT NULL
    )""",
    # ── Tickets ─────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL, staff_id INTEGER,
        category TEXT, status TEXT NOT NULL DEFAULT 'open',
        created_at INTEGER NOT NULL, closed_at INTEGER,
        rating INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS ticket_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, ticket_id INTEGER NOT NULL,
        staff_id INTEGER, note TEXT, created_at INTEGER NOT NULL
    )""",
    # ── Économie avancée ────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS shops (
        guild_id INTEGER NOT NULL, kind TEXT NOT NULL DEFAULT 'regular',
        item TEXT NOT NULL, price INTEGER NOT NULL, stock INTEGER NOT NULL DEFAULT -1,
        PRIMARY KEY (guild_id, kind, item)
    )""",
    """CREATE TABLE IF NOT EXISTS shop_inventory (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        item TEXT NOT NULL, qty INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (guild_id, user_id, item)
    )""",
    """CREATE TABLE IF NOT EXISTS houses (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        name TEXT NOT NULL, value INTEGER NOT NULL,
        PRIMARY KEY (guild_id, user_id, name)
    )""",
    """CREATE TABLE IF NOT EXISTS vehicles (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        name TEXT NOT NULL, value INTEGER NOT NULL,
        speed INTEGER NOT NULL DEFAULT 100, power INTEGER NOT NULL DEFAULT 100,
        handling INTEGER NOT NULL DEFAULT 100, durability INTEGER NOT NULL DEFAULT 100,
        condition INTEGER NOT NULL DEFAULT 100,
        PRIMARY KEY (guild_id, user_id, name)
    )""",
    """CREATE TABLE IF NOT EXISTS animals (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        name TEXT NOT NULL, species TEXT NOT NULL, rarity TEXT NOT NULL,
        power INTEGER NOT NULL DEFAULT 10, endurance INTEGER NOT NULL DEFAULT 10,
        speed INTEGER NOT NULL DEFAULT 10, health INTEGER NOT NULL DEFAULT 100,
        level INTEGER NOT NULL DEFAULT 1, fed_at INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, user_id, name)
    )""",
    """CREATE TABLE IF NOT EXISTS equipment (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        slot TEXT NOT NULL, item TEXT NOT NULL, bonus INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, user_id, slot)
    )""",
    """CREATE TABLE IF NOT EXISTS insurance (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,          -- single | temp_24h | temp_30d | permanent
        active INTEGER NOT NULL DEFAULT 1,
        expires_at INTEGER NOT NULL DEFAULT 0,
        cap INTEGER NOT NULL DEFAULT 0,      -- plafond permanent
        cap_used INTEGER NOT NULL DEFAULT 0,
        bought_at INTEGER NOT NULL,
        PRIMARY KEY (guild_id, user_id, kind)
    )""",
    """CREATE TABLE IF NOT EXISTS insurance_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        insurance_kind TEXT NOT NULL, loss INTEGER NOT NULL,
        payout INTEGER NOT NULL, reason TEXT, created_at INTEGER NOT NULL
    )""",
    # ── Marché dynamique ────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS market (
        guild_id INTEGER NOT NULL, resource TEXT NOT NULL,
        price INTEGER NOT NULL, min_price INTEGER NOT NULL, max_price INTEGER NOT NULL,
        supply INTEGER NOT NULL DEFAULT 100, demand INTEGER NOT NULL DEFAULT 100,
        updated_at INTEGER NOT NULL,
        PRIMARY KEY (guild_id, resource)
    )""",
    """CREATE TABLE IF NOT EXISTS market_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, resource TEXT NOT NULL,
        price INTEGER NOT NULL, created_at INTEGER NOT NULL
    )""",
    # ── Missions ────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,           -- daily | weekly
        desc TEXT NOT NULL, goal INTEGER NOT NULL,
        progress INTEGER NOT NULL DEFAULT 0,
        reward INTEGER NOT NULL,
        expires_at INTEGER NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        claimed INTEGER NOT NULL DEFAULT 0
    )""",
    # ── Gouvernement ─────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS government (
        guild_id INTEGER NOT NULL, office TEXT NOT NULL,
        user_id INTEGER, since INTEGER,
        PRIMARY KEY (guild_id, office)
    )""",
    """CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, topic TEXT NOT NULL,
        voter_id INTEGER NOT NULL, choice TEXT NOT NULL, created_at INTEGER NOT NULL,
        UNIQUE (guild_id, topic, voter_id)
    )""",
    """CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL, due_at INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',   -- active | repaid | overdue
        created_at INTEGER NOT NULL,
        UNIQUE (guild_id, user_id)               -- un seul emprunt actif (Y)
    )""",
    # ── Caisse centrale / taxes / aide (K, X) ───────────────────────────
    """CREATE TABLE IF NOT EXISTS treasury (
        guild_id INTEGER NOT NULL, account TEXT NOT NULL,
        balance INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, account)
    )""",
    """CREATE TABLE IF NOT EXISTS treasury_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, account TEXT NOT NULL,
        kind TEXT NOT NULL, amount INTEGER NOT NULL,
        ref_user INTEGER, note TEXT, created_at INTEGER NOT NULL
    )""",
    # ── Familles (M) ────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS families (
        guild_id INTEGER NOT NULL, id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, tag TEXT NOT NULL,
        leader_id INTEGER NOT NULL, coleader_id INTEGER,
        treasury INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS family_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, family_id INTEGER NOT NULL,
        kind TEXT NOT NULL, amount INTEGER NOT NULL,
        ref_user INTEGER, note TEXT, created_at INTEGER NOT NULL
    )""",
    # ── Giveaways (E) ───────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS giveaways (
        guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
        prize TEXT NOT NULL, winners INTEGER NOT NULL DEFAULT 1,
        ends_at INTEGER NOT NULL, message_id INTEGER,
        status TEXT NOT NULL DEFAULT 'active',
        PRIMARY KEY (guild_id, channel_id, message_id)
    )""",
    """CREATE TABLE IF NOT EXISTS giveaway_entries (
        guild_id INTEGER NOT NULL, giveaway_msg INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (guild_id, giveaway_msg, user_id)
    )""",
    # ── Coffres COFFRESMUSK ─────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS chests (
        guild_id INTEGER NOT NULL, id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id INTEGER NOT NULL, message_id INTEGER,
        rarity TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'waiting',
        spawned_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
        claimed_by INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS winner_codes (
        code TEXT PRIMARY KEY,
        reward TEXT NOT NULL, mode TEXT NOT NULL DEFAULT 'fixed',
        options TEXT, valid_until INTEGER NOT NULL DEFAULT 0,
        used INTEGER NOT NULL DEFAULT 0, used_by INTEGER,
        created_by INTEGER NOT NULL, created_at INTEGER NOT NULL
    )""",
    # ── WINNERMUSK (I) — catalogue global protégé ───────────────────────
    """CREATE TABLE IF NOT EXISTS winner_catalog (
        item TEXT PRIMARY KEY, kind TEXT NOT NULL,
        price INTEGER NOT NULL, stock INTEGER NOT NULL DEFAULT -1,
        media TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS winner_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        item TEXT NOT NULL, price INTEGER NOT NULL,
        delivery TEXT NOT NULL,      -- normal | luxe | exclusif | mythique
        deliver_at INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
        created_at INTEGER NOT NULL
    )""",
    # ── Succès (R) ──────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS achievements (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        code TEXT NOT NULL, unlocked_at INTEGER NOT NULL,
        claimed INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, user_id, code)
    )""",
    # ── Invites (U) ─────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS invites (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        total INTEGER NOT NULL DEFAULT 0, pending INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, user_id)
    )""",
    # ── Bump (T) ────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS bumps (
        guild_id INTEGER NOT NULL, cycle INTEGER NOT NULL,
        bumped INTEGER NOT NULL DEFAULT 0,
        best_user INTEGER, best_count INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, cycle)
    )""",
    # ── AutoReactRole (V) ───────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS reaction_roles (
        guild_id INTEGER NOT NULL, message_id INTEGER NOT NULL,
        emoji TEXT NOT NULL, role_id INTEGER NOT NULL, mode TEXT NOT NULL DEFAULT 'add',
        PRIMARY KEY (guild_id, message_id, emoji)
    )""",
    # ── Winterfest boss (Z) ─────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS boss (
        guild_id INTEGER NOT NULL, hp INTEGER NOT NULL, max_hp INTEGER NOT NULL,
        state TEXT NOT NULL DEFAULT 'idle',   -- idle | active
        spawned_at INTEGER, next_spawn INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id)
    )""",
    """CREATE TABLE IF NOT EXISTS boss_contrib (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        dmg INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, user_id)
    )""",
    # ── Audit global ────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER, user_id INTEGER,
        kind TEXT NOT NULL, detail TEXT, created_at INTEGER NOT NULL
    )""",
]

def init_db(db: sqlite3.Connection):
    _backup_database(db)
    for stmt in SCHEMA:
        db.execute(stmt)
    # Migration : identifiant stable des articles de boutique
    cols = [r[1] for r in db.execute("PRAGMA table_info(shops)").fetchall()]
    if "item_id" not in cols:
        db.execute("ALTER TABLE shops ADD COLUMN item_id INTEGER")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_shops_item_id "
               "ON shops (guild_id, kind, item_id) WHERE item_id IS NOT NULL")
    db.commit()

# ── Helpers d'accès (toujours guild_id en premier) ─────────────────────
def ensure_user(db, guild_id, user_id):
    db.execute(
        "INSERT OR IGNORE INTO users (guild_id, user_id) VALUES (?, ?)",
        (guild_id, user_id))
    db.commit()

def get_user(db, guild_id, user_id):
    ensure_user(db, guild_id, user_id)
    return db.execute(
        "SELECT * FROM users WHERE guild_id=? AND user_id=?",
        (guild_id, user_id)).fetchone()

def update_user(db, guild_id, user_id, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [guild_id, user_id]
    db.execute(f"UPDATE users SET {sets} WHERE guild_id=? AND user_id=?", vals)
    db.commit()

def add_tx(db, guild_id, user_id, action, amount):
    db.execute(
        "INSERT INTO transactions (guild_id, user_id, action, amount, created_at) "
        "VALUES (?,?,?,?,?)", (guild_id, user_id, action, amount, now()))
    db.commit()

def config_get(db, guild_id, key, default=None):
    r = db.execute("SELECT value FROM config WHERE guild_id=? AND key=?",
                   (guild_id, key)).fetchone()
    return r["value"] if r else default

def config_set(db, guild_id, key, value):
    db.execute(
        "INSERT INTO config (guild_id, key, value) VALUES (?,?,?) "
        "ON CONFLICT(guild_id, key) DO UPDATE SET value=excluded.value",
        (guild_id, key, str(value)))
    db.commit()

def log_event(db, guild_id, user_id, kind, detail=""):
    db.execute(
        "INSERT INTO audit_log (guild_id, user_id, kind, detail, created_at) "
        "VALUES (?,?,?,?,?)", (guild_id, user_id, kind, detail, now()))
    db.commit()

def admin_check(ctx) -> bool:
    """Propriétaire, administrateur Discord, ou rôle Admin du bot."""
    g = ctx.guild
    if g is None:
        return False
    if ctx.author.id == OWNER_ID:
        return True
    if g.owner_id == ctx.author.id:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    db = connect()
    try:
        admin_role = config_get(db, g.id, "admin_role_id")
        if admin_role:
            for r in ctx.author.roles:
                if r.id == int(admin_role):
                    return True
    finally:
        db.close()
    return False

def mod_check(ctx) -> bool:
    g = ctx.guild
    if g is None:
        return False
    if ctx.author.id == OWNER_ID or g.owner_id == ctx.author.id:
        return True
    if ctx.author.guild_permissions.administrator or \
       ctx.author.guild_permissions.moderate_members:
        return True
    db = connect()
    try:
        mod_role = config_get(db, g.id, "mod_role_id")
        if mod_role:
            for r in ctx.author.roles:
                if r.id == int(mod_role):
                    return True
    finally:
        db.close()
    return False

def owner_check():
    """Check propriétaire : ID Discord numérique configuré, jamais le nom affiché."""
    async def predicate(ctx):
        if OWNER_ID and ctx.author.id == OWNER_ID:
            return True
        await ctx.send(q("no_perm"))
        return False
    return commands.check(predicate)

def multiplier(db, guild_id) -> float:
    """Multiplicateur adminabuse — récompenses admissibles uniquement."""
    try:
        return float(config_get(db, guild_id, "admin_mult", "1") or 1)
    except ValueError:
        return 1.0

def mult_until(db, guild_id) -> int:
    try:
        return int(config_get(db, guild_id, "admin_mult_until", "0") or 0)
    except ValueError:
        return 0

# ══════════════════════════════════════════════════════════════════════
#  INSTANCES & CONFIG
# ══════════════════════════════════════════════════════════════════════
OWNER_ID = int(os.getenv("OWNER_ID") or os.getenv("WINNER_ID") or 0)
TOKEN = os.getenv("DISCORD_TOKEN", "")
XP_COOLDOWN = int(os.getenv("XP_COOLDOWN_SECONDS", "60"))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

# ── Routing des préfixes (cahier) ──────────────────────────────────────
# "!" = commandes des MEMBRES  |  "+" = commandes STAFF / ADMIN / PROPRIÉTAIRE
# Accepte ! et + en entrée ; le contrôle fin du préfixe requis se fait dans on_command.
STAFF_COMMANDS = {
    "warn","warnhistory","ban","banned","unban","setbanrole","clear","purge",
    "lock","unlock","mute","timeout","unmute","kick","slowmode","nick","automod",
    "starboard","imprison","prisonhistory","release","prisonbailrate","amende",
    "rankup","setrankstaff","salaire","chastaff","adminabuse","caisse","giveaway",
    "gwreroll","raid","autoreactrole","ticketpanel","ticketping","ticketnote",
    "ticketnotes","setbump","setbumprole","setstarboard","setwelcome","setlog",
    "setrank","dashboard","winneradd","winner",
}

def _member_prefix(guild_id=None):
    """Préfixe membre du serveur (défaut « ! »)."""
    if not guild_id:
        return "!"
    try:
        db = connect()
        try:
            return config_get(db, guild_id, "member_prefix", "!") or "!"
        finally:
            db.close()
    except Exception:
        return "!"

def _get_prefix(bot, message):
    """Préfixes actifs : membre (« ! » par défaut), staff « + », propriétaire « w. », mention."""
    prefixes = ["+", "w.", _member_prefix(message.guild.id if message.guild else None)]
    return commands.when_mentioned_or(*prefixes)(bot, message)

bot = commands.Bot(command_prefix=_get_prefix,
                   intents=intents,
                   case_insensitive=True,
                   help_command=None)

# Cooldowns globaux anti-spam
global_cd = commands.CooldownMapping.from_cooldown(5, 60, commands.BucketType.user)

# ══════════════════════════════════════════════════════════════════════
#  ÉVÉNEMENTS
# ══════════════════════════════════════════════════════════════════════
@bot.event
async def on_ready():
    print(f"❄ {EMILIA} connectée — {len(bot.guilds)} serveur(s)")
    try:
        await bot.tree.sync()
        print("  Slash commands synchronisées.")
    except Exception as e:
        print("  Sync slash:", e)
    # Démarre TOUTES les tâches automatiques (13) — évite les doublons via is_running()
    for t in (auto_tax_loop, chest_loop, prison_loop, boss_loop,
              interest_loop, mission_loop, winphone_loop,
              giveaway_loop, bank_interest_loop, auction_loop,
              family_upkeep_loop, war_loop, staff_salary_loop):
        if not t.is_running():
            t.start()

@bot.event
asy@bot.event
async def on_command_error(ctx, error):
 @bot.event
async def on_command_error(ctx, error):
    typing = getattr(ctx, "_emilia_typing", None)
    if typing is not None:
        ctx._emilia_typing = None
        try:
            await typing.__aexit__(None, None, None)
        except Exception:
            pass 
  typing = getattr(ctx, "_emilia_typing", None)
    if typing is not None:
        ctx._emilia_typing = None
        try:
            await typing.__aexit__(None, None, None)
        except Exception:
            pas snc def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❄ Argument manquant. Syntaxe : `{ctx.prefix}{ctx.command.qualified_name} "
                       f"{ctx.command.signature}` — {ctx.command.help or ''}")
        return
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Patience. Réessaie dans **{error.retry_after:.0f} s**.")
        return
    if isinstance(error, commands.NotOwner):
        await ctx.send(q("no_perm"))
        return
    if isinstance(error, commands.CheckFailure):
        msg = str(error)
        if msg:
            await ctx.send(msg)
        return
    if isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
        await ctx.send("❄ Membre introuvable. Mentionne-le ou donne son identifiant.")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send(f"❄ Argument invalide. Syntaxe : `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`")
        return
    if isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
        await ctx.send("❄ Je n'ai pas la permission de faire ça (vérifie mon rôle et mes droits).")
        return
    print("CMD ERROR:", repr(error))
    await ctx.send("❄ Une erreur est survenue. J'ai noté, ne t'inquiète pas.")

@bot.event
async def on_member_join(member):
    g = member.guild
    db = connect()
    try:
        welcome = config_get(db, g.id, "welcome_channel_id")
        if welcome:
            ch = g.get_channel(int(welcome))
            if ch:
                embed = frost_embed(
                    title="❄ Bienvenue",
                    desc=f"« {member.mention} entre dans mon domaine.\n"
                         f"Conduis-toi bien. La glace voit tout. »",
                    color=FROST,
                    fields=[("👤 Membre", str(member), False),
                            ("📅 Arrivée", fmt_ts(now()), False)])
                await ch.send(embed=embed)
    finally:
        db.close()

@bot.event
async def on_member_remove(member):
    g = member.guild
    db = connect()
    try:
        leave = config_get(db, g.id, "leave_channel_id")
        if leave:
            ch = g.get_channel(int(leave))
            if ch:
                await ch.send(f"🕳 {member.mention} a quitté le domaine. La glace s'en souviendra.")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  A. ÉCONOMIE & PATRIMOINE
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="daily", help="Récompense quotidienne avec série.")
@commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
async def daily(ctx):
    g = ctx.guild
    db = connect()
    try:
        u = get_user(db, g.id, ctx.author.id)
        last = u["last_daily"]
        day = datetime.now().date()
        last_day = datetime.fromtimestamp(last).date() if last else None
        if last_day == day:
            await ctx.send(q("error"))
            return
        # Série : +1 si hier, sinon réinitialisation
        streak = (u["daily_streak"] + 1) if last_day == day - timedelta(days=1) else 1
        base = int(config_get(db, g.id, "daily_base", "250"))
        bonus = base * (streak - 1) // 10          # +10 % par jour de série
        reward = int((base + bonus) * multiplier(db, g.id))
        # M : 20 % du salaire versé à la caisse familiale (atomique, 1×/jour)
        family_cut = 0
        if u["family_id"]:
            fam = db.execute(
                "SELECT id FROM families WHERE guild_id=? AND id=?",
                (g.id, u["family_id"])).fetchone()
            if fam:
                family_cut = reward // 5
                db.execute("UPDATE families SET treasury=treasury+? WHERE id=?",
                           (family_cut, fam["id"]))
                db.execute(
                    "INSERT INTO family_ledger (guild_id, family_id, kind, amount, ref_user, created_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (g.id, fam["id"], "salaire_20pct", family_cut, ctx.author.id, now()))
        personal = reward - family_cut
        update_user(db, g.id, ctx.author.id,
                    wallet=u["wallet"] + personal,
                    daily_streak=streak, last_daily=now())
        add_tx(db, g.id, ctx.author.id, "daily", personal)
        check_achievements(db, g.id, ctx.author.id, "daily_streak", streak)
        e = quote_embed(
            f"{q('daily')}\n\n",
            color=ICE,
            fields=[
                (f"{COIN} Gain", f"**{fmt(personal)}**"
                 + (f" (+ **{fmt(family_cut)}** à la famille)" if family_cut else ""), False),
                ("🔥 Série", f"**{streak} jour(s)**" + (" — record ! 🏅" if streak >= 7 else ""), False),
                ("📅 Prochain", "Demain, à la même heure.", False),
            ])
        await reveal(ctx, [f"❄ *{ctx.author.display_name}… ta régularité t'honore.*"],
                     final_embed=e)
    finally:
        db.close()

@bot.command(name="work", help="Travailler (cooldown 1 h).")
@commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
async def work(ctx):
    g = ctx.guild
    db = connect()
    try:
        u = get_user(db, g.id, ctx.author.id)
        if now() - u["last_work"] < 3600:
            await ctx.send(f"⏳ Tu dois attendre **{remaining(u['last_work'] + 3600)}** avant de retravailler.")
            return
        base = int(config_get(db, g.id, "work_base", "120"))
        reward = max(10, int(random.gauss(base, base * 0.35) * multiplier(db, g.id)))
        jobs = ["café du coin", "chantier de glace", "atelier de sculpture",
                "entrepôt de nuit", "studio de design", "salle des serveurs"]
        job = random.choice(jobs)
        update_user(db, g.id, ctx.author.id,
                    wallet=u["wallet"] + reward, last_work=now())
        add_tx(db, g.id, ctx.author.id, "work", reward)
        e = quote_embed(
            f"{q('work')}\n\n",
            color=ICE,
            fields=[
                ("🛠️ Mission", job, False),
                (f"{COIN} Gain", f"**{fmt(reward)}**", False),
                ("⏳ Prochain travail", "Dans **1 h**.", False),
            ])
        await reveal(ctx,
                     [f"🛠️ *{ctx.author.display_name} est envoyé(e) au {job}…*",
                      f"*Le froid monte. Le travail est fait.*"],
                     final_embed=e)
    finally:
        db.close()

@bot.command(name="mine", help="Extraire des minerais (cooldown 1 h).")
@commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
async def mine(ctx):
    g = ctx.guild
    db = connect()
    try:
        u = get_user(db, g.id, ctx.author.id)
        if now() - u["last_mine"] < 3600:
            await ctx.send(f"⏳ La mine est scellée. Réessaie dans **{remaining(u['last_mine'] + 3600)}**.")
            return
        base = int(config_get(db, g.id, "mine_base", "150"))
        reward = max(15, int(random.gauss(base, base * 0.5) * multiplier(db, g.id)))
        ore = random.choice(["cristal de glace", "minerai de lune", "fer polaire",
                             "pierre d'aube", "silex givré"])
        update_user(db, g.id, ctx.author.id,
                    wallet=u["wallet"] + reward, last_mine=now())
        add_tx(db, g.id, ctx.author.id, "mine", reward)
        e = quote_embed(
            f"{q('mine')}\n\n",
            color=ICE,
            fields=[
                ("⛏️ Minerai", ore, False),
                (f"{COIN} Gain", f"**{fmt(reward)}**", False),
                ("⏳ Prochaine mine", "Dans **1 h**.", False),
            ])
        await reveal(ctx,
                     [f"⛏️ *{ctx.author.display_name} descend dans la mine…*",
                      f"*Le roc se fend. Le {ore} apparaît.*"],
                     final_embed=e)
    finally:
        db.close()

@bot.command(name="solde", aliases=["balance"], help="Ton solde et ta banque.")
async def solde(ctx, member: discord.Member = None):
    g = ctx.guild
    db = connect()
    try:
        m = member or ctx.author
        u = get_user(db, g.id, m.id)
        e = frost_embed(
            title=f"👤 {m.display_name} — Patrimoine",
            desc=f"{q('greet')}",
            color=ICE,
            thumbnail=m.display_avatar.url,
            fields=[
                (f"{COIN} Portefeuille", fmt(u["wallet"]), False),
                (f"🏦 Banque", fmt(u["bank"]), False),
                (f"🔮 Noyaux", fmt(u["cores"]), False),
                (f"💎 MF", fmt(u["mf"]), False),
                ("⭐ Niveau", f"Level **{u['level']}** — {fmt(u['xp'])} XP", False),
            ])
        await ctx.send(embed=e)
    finally:
        db.close()

@bot.command(name="bank", help="Déposer / retirer de la banque.")
async def bank(ctx, action: str = None, amount: int = None):
    g = ctx.guild
    db = connect()
    try:
        u = get_user(db, g.id, ctx.author.id)
        if amount is not None and amount <= 0:
            await ctx.send("❄ Montant invalide : il doit être positif.")
            return
        if action in ("d", "depot", "deposit") and amount:
            if amount > u["wallet"]:
                await ctx.send(f"❄ Tu n'as que **{fmt(u['wallet'])}** en portefeuille.")
                return
            update_user(db, g.id, ctx.author.id,
                        wallet=u["wallet"] - amount, bank=u["bank"] + amount)
            add_tx(db, g.id, ctx.author.id, "bank_deposit", -amount)
            await ctx.send(f"🏦 **{fmt(amount)}** déposés. La banque garde mieux que toi.")
        elif action in ("r", "retrait", "withdraw") and amount:
            if amount > u["bank"]:
                await ctx.send(f"❄ Tu n'as que **{fmt(u['bank'])}** en banque.")
                return
            update_user(db, g.id, ctx.author.id,
                        bank=u["bank"] - amount, wallet=u["wallet"] + amount)
            add_tx(db, g.id, ctx.author.id, "bank_withdraw", amount)
            await ctx.send(f"🏦 **{fmt(amount)}** retirés. Dépense-les avec élégance.")
        else:
            await ctx.send(f"❄ Usage : `!bank d <montant>` ou `!bank r <montant>`")
    finally:
        db.close()

@bot.command(name="payer", aliases=["pay"], help="Payer un membre.")
async def payer(ctx, member: discord.Member, amount: int):
    g = ctx.guild
    db = connect()
    try:
        if member == ctx.author:
            await ctx.send("❄ Te payer toi-même ? L'élégance a des limites.")
            return
        if amount <= 0:
            await ctx.send("❄ Montant invalide.")
            return
        me = get_user(db, g.id, ctx.author.id)
        if amount > me["wallet"]:
            await ctx.send(f"❄ Tu n'as que **{fmt(me['wallet'])}**.")
            return
        them = get_user(db, g.id, member.id)
        update_user(db, g.id, ctx.author.id, wallet=me["wallet"] - amount)
        update_user(db, g.id, member.id, wallet=them["wallet"] + amount)
        add_tx(db, g.id, ctx.author.id, "pay_out", -amount)
        add_tx(db, g.id, member.id, "pay_in", amount)
        log_event(db, g.id, ctx.author.id, "pay", f"→ {member.id} : {amount}")
        await ctx.send(f"{q('pay')}\n{COIN} **{fmt(amount)}** versés à {member.mention}.")
    finally:
        db.close()

@bot.command(name="top", help="Top 10 de la richesse (soldes + biens).")
async def top(ctx):
    g = ctx.guild
    db = connect()
    try:
        rows = db.execute(
            "SELECT user_id, wallet, bank FROM users WHERE guild_id=? "
            "ORDER BY (wallet+bank) DESC LIMIT 10", (g.id,)).fetchall()
        if not rows:
            await ctx.send("❄ Personne à classer. Pour l'instant.")
            return
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, r in enumerate(rows):
            icon = medals[i] if i < 3 else f"**{i+1}.**"
            lines.append(f"{icon} <@{r['user_id']}> — {COIN} **{fmt(r['wallet'] + r['bank'])}**")
        e = frost_embed(title="🏆 Classement de la richesse",
                        desc="\n".join(lines), color=GOLD)
        await ctx.send(embed=e)
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  A. BOUTIQUE NORMALE + COFFRESMUSK + INVENTAIRE
# ══════════════════════════════════════════════════════════════════════
DEFAULT_SHOP = [
    ("🎁 Cadeau surprise", 500),
    ("🔧 Kit de réparation", 800),
    ("🛡️ Bouclier de protection", 1200),
    ("⚔️ Épée de glace (équipement RPG)", 2000),
    ("🪄 Baguette d'hiver (équipement RPG)", 1500),
    ("🧊 Bloc de givre (objet utilitaire)", 300),
    ("🔋 Batterie polaire (objet utilitaire)", 600),
    ("🛡️ Assurances — Sinistre unique", 2500),
    ("🛡️ Assurances — Temporaire 24 h", 5000),
    ("🛡️ Assurances — Temporaire 30 jours", 25000),
    ("🛡️ Assurances — Permanente (plafond 50 000)", 15000),
    ("🔁 Recharge plafond permanent (+50 000)", 12000),
]

FORBIDDEN_SHOP_WORDS = ("maison", "voiture", "moto", "téléphone", "telephone", "winphone",
                        "animal", "coffre", "box", "chest")

def next_shop_id(db, guild_id):
    r = db.execute("SELECT COALESCE(MAX(item_id),0) FROM shops WHERE guild_id=? AND kind='regular'",
                   (guild_id,)).fetchone()
    return (r[0] or 0) + 1

def ensure_shop(db, guild_id):
    """Articles par défaut avec ID fixes (1..N) ; les articles ajoutés ensuite reçoivent l'ID suivant."""
    for n, (name, price) in enumerate(DEFAULT_SHOP, start=1):
        db.execute(
            "INSERT OR IGNORE INTO shops (guild_id, kind, item, price, stock, item_id) "
            "VALUES (?,?,?,?,-1,?)", (guild_id, "regular", name, price, n))
        db.execute("UPDATE shops SET item_id=? WHERE guild_id=? AND kind='regular' AND item=? "
                   "AND item_id IS NULL", (n, guild_id, name))
    rows = db.execute("SELECT item FROM shops WHERE guild_id=? AND kind='regular' AND item_id IS NULL",
                      (guild_id,)).fetchall()
    for r in rows:
        db.execute("UPDATE shops SET item_id=? WHERE guild_id=? AND kind='regular' AND item=?",
                   (next_shop_id(db, guild_id), guild_id, r["item"]))
    db.commit()

def _shop_page(db, guild_id, page):
    ensure_shop(db, guild_id)
    items = db.execute(
        "SELECT item_id, item, price, stock FROM shops WHERE guild_id=? AND kind='regular' "
        "ORDER BY item_id", (guild_id,)).fetchall()
    per_page = 8
    pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    chunk = items[(page - 1) * per_page: page * per_page]
    lines = []
    for it in chunk:
        stock = "∞" if it["stock"] < 0 else str(it["stock"])
        lines.append(f"`ID {it['item_id']}` {it['item']} — {COIN} **{fmt(it['price'])}** (stock : {stock})")
    e = frost_embed(
        title=f"🛍️ Boutique normale — page {page}/{pages}",
        desc=q("shop") + "\n\n" + "\n".join(lines) + "\n\nAchat : `!buy <ID>`",
        color=ICE)
    return e, page, pages

class ShopNavView(discord.ui.View):
    def __init__(self, guild_id, page=1, pages=1, author_id=None):
        super().__init__(timeout=120)
        self.guild_id, self.page, self.pages, self.author_id = guild_id, page, pages, author_id

    async def _go(self, inter: discord.Interaction, delta: int):
        if self.author_id and inter.user.id != self.author_id:
            await inter.response.send_message("❄ Ce n'est pas ta boutique.", ephemeral=True)
            return
        db = connect()
        try:
            e, self.page, self.pages = _shop_page(db, self.guild_id, self.page + delta)
        finally:
            db.close()
        await inter.response.edit_message(embed=e, view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, inter: discord.Interaction, button: discord.ui.Button):
        await self._go(inter, -1)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def nxt(self, inter: discord.Interaction, button: discord.ui.Button):
        await self._go(inter, +1)

@bot.command(name="markets", aliases=["boutique"], help="Boutique normale (objets utiles).")
async def markets(ctx, page: int = 1):
    db = connect()
    try:
        e, page, pages = _shop_page(db, ctx.guild.id, page)
        await ctx.send(embed=e, view=ShopNavView(ctx.guild.id, page, pages, ctx.author.id))
    finally:
        db.close()

@bot.command(name="buy", help="Acheter un article de la boutique normale.")
async def buy(ctx, item_id: int):
    g = ctx.guild
    db = connect()
    try:
        ensure_shop(db, g.id)
        it = db.execute(
            "SELECT item_id, item, price, stock FROM shops WHERE guild_id=? AND kind='regular' AND item_id=?",
            (g.id, item_id)).fetchone()
        if not it:
            await ctx.send("❄ Aucun article avec cet ID. Voir `!markets`.")
            return
        u = get_user(db, g.id, ctx.author.id)
        if it["stock"] == 0:
            await ctx.send("❄ Rupture de stock. Reviens plus tard.")
            return
        if u["wallet"] < it["price"]:
            await ctx.send(f"❄ Il te faut **{fmt(it['price'])}**, tu as **{fmt(u['wallet'])}**.")
            return
        update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - it["price"])
        if it["stock"] > 0:
            db.execute("UPDATE shops SET stock=stock-1 WHERE guild_id=? AND kind='regular' AND item_id=? AND stock>0",
                       (g.id, it["item_id"]))
        add_tx(db, g.id, ctx.author.id, "buy", -it["price"])
        # Assurance : active la bonne formule (N)
        if it["item"].startswith("🛡️ Assurances"):
            kind = "single" if "Sinistre unique" in it["item"] else \
                   "temp_24h" if "24 h" in it["item"] else \
                   "temp_30d" if "30 jours" in it["item"] else "permanent"
            cap = 50000 if kind == "permanent" else 0
            exp = 0
            if kind == "temp_24h":
                exp = now() + 86400
            elif kind == "temp_30d":
                exp = now() + 30 * 86400
            db.execute(
                "INSERT INTO insurance (guild_id, user_id, kind, active, expires_at, cap, bought_at) "
                "VALUES (?,?,?,1,?,?,?) "
                "ON CONFLICT(guild_id, user_id, kind) DO UPDATE SET "
                "active=1, expires_at=excluded.expires_at, "
                "cap=CASE WHEN excluded.cap>0 THEN excluded.cap ELSE insurance.cap END, "
                "bought_at=excluded.bought_at",
                (g.id, ctx.author.id, kind, exp, cap, now()))
            db.commit()
            await ctx.send(f"🛡️ Assurance **{it['item']}** activée. La glace te couvre à 50 %.")
            return
        if it["item"].startswith("🔁 Recharge"):
            db.execute(
                "UPDATE insurance SET cap=cap+50000 WHERE guild_id=? AND user_id=? AND kind='permanent'",
                (g.id, ctx.author.id))
            db.commit()
            await ctx.send("🛡️ Plafond permanent rechargé de **50 000**.")
            return
        db.execute(
            "INSERT INTO shop_inventory (guild_id, user_id, item, qty) VALUES (?,?,?,1) "
            "ON CONFLICT(guild_id, user_id, item) DO UPDATE SET qty=qty+1",
            (g.id, ctx.author.id, it["item"]))
        db.commit()
        await ctx.send(f"🛍️ **{it['item']}** acheté pour {COIN} **{fmt(it['price'])}**.")
    finally:
        db.close()

@bot.command(name="inventaire", aliases=["inventory"], help="Ton inventaire.")
async def inventaire(ctx):
    g = ctx.guild
    db = connect()
    try:
        rows = db.execute(
            "SELECT item, qty FROM shop_inventory WHERE guild_id=? AND user_id=?",
            (g.id, ctx.author.id)).fetchall()
        if not rows:
            await ctx.send("❄ Ton inventaire est vide. La boutique t'attend.")
            return
        lines = [f"• {r['item']} × {r['qty']}" for r in rows]
        e = frost_embed(title="🎒 Inventaire", desc="\n".join(lines), color=ICE)
        await ctx.send(embed=e)
    finally:
        db.close()

# ── COFFRESMUSK — 4 raretés, cycle 2 h, 1 coffre/membre/2 h ────────────
CHEST_RATES = [("Normal", 70), ("Légendaire", 25), ("Mythique", 5)]  # Exclusif = manuel uniquement

def roll_chest_rarity() -> str:
    r = random.randint(1, 100)
    acc = 0
    for name, pct in CHEST_RATES:
        acc += pct
        if r <= acc:
            return name
    return "Normal"

@bot.command(name="chest", help="Récupérer le coffre COFFRESMUSK visible.")
async def chest(ctx):
    g = ctx.guild
    db = connect()
    try:
        row = db.execute(
            "SELECT * FROM chests WHERE guild_id=? AND status='waiting' "
            "AND expires_at > ? ORDER BY spawned_at LIMIT 1", (g.id, now())).fetchone()
        if not row:
            await ctx.send("❄ Aucun coffre en attente. Le cycle repart dans peu.")
            return
        u = get_user(db, g.id, ctx.author.id)
        if now() - u["last_chest"] < 7200:
            await ctx.send(f"⏳ Un coffre toutes les 2 h. Réessaie dans **{remaining(u['last_chest'] + 7200)}**.")
            return
        rarity = row["rarity"]
        color, icon = RARE_STYLE[rarity]
        base = {"Normal": 300, "Légendaire": 1500, "Mythique": 8000, "Exclusif": 50000}[rarity]
        main_reward = int(random.gauss(base, base * 0.3) * multiplier(db, g.id))
        bonus = int(main_reward * random.uniform(0.05, 0.2))
        total = main_reward + bonus
        update_user(db, g.id, ctx.author.id,
                    wallet=u["wallet"] + total, last_chest=now())
        add_tx(db, g.id, ctx.author.id, "chest", total)
        db.execute("UPDATE chests SET status='claimed', claimed_by=? WHERE id=?",
                   (ctx.author.id, row["id"]))
        db.commit()
        e = quote_embed(
            f"{q('chest')}\n\n",
            color=color,
            title=f"{icon} Coffre {rarity} — COFFRESMUSK",
            fields=[
                (f"{COIN} Récompense principale", fmt(main_reward), False),
                ("✨ Bonus", fmt(bonus), False),
                ("🎁 Total", f"**{fmt(total)}**", False),
            ])
        await reveal(ctx,
                     [f"📦 *Un coffre {rarity} scintille dans le salon…*",
                      f"*{ctx.author.display_name} l'ouvre. La glace retient son souffle.*"],
                     final_embed=e)
    finally:
        db.close()

@tasks.loop(hours=2)
async def chest_loop():
    """Un coffre toutes les 2 h dans le salon configuré ; disparition à 2 h."""
    for guild in bot.guilds:
        db = connect()
        try:
            db.execute("UPDATE chests SET status='expired' "
                       "WHERE guild_id=? AND status='waiting' AND expires_at<=?",
                       (guild.id, now()))
            db.commit()
            ch_id = config_get(db, guild.id, "chest_channel_id")
            if not ch_id:
                continue
            ch = guild.get_channel(int(ch_id))
            if not ch:
                continue
            rarity = roll_chest_rarity()
            color, icon = RARE_STYLE[rarity]
            cur = now()
            db.execute(
                "INSERT INTO chests (guild_id, channel_id, rarity, status, spawned_at, expires_at) "
                "VALUES (?,?,?,'waiting',?,?)",
                (guild.id, ch.id, rarity, cur, cur + 7200))
            db.commit()
            e = frost_embed(
                title=f"{icon} Un coffre apparaît !",
                desc=f"Un coffre **{rarity}** est tombé dans ce salon.\n"
                     f"Le premier à taper `!chest` le récupère.\n"
                     f"⏳ Il disparaît dans **2 h**.",
                color=color)
            await ch.send(embed=e)
        except Exception as ex:
            print("chest_loop:", ex)
        finally:
            db.close()

# ══════════════════════════════════════════════════════════════════════
#  A. ANIMAUX — illimités, soins obligatoires
# ══════════════════════════════════════════════════════════════════════
SPECIES = [
    ("Loup polaire", "Normal"), ("Chat de givre", "Normal"),
    ("Faucon boréal", "Légendaire"), ("Ours des neiges", "Légendaire"),
    ("Dragon de glace", "Mythique"), ("Licorne givrée", "Exclusif"),
]

@bot.command(name="animal", help="Gérer tes animaux (acheter, nourrir, soigner).")
async def animal(ctx, action: str = None, name: str = None):
    g = ctx.guild
    db = connect()
    try:
        if action == "liste":
            rows = db.execute(
                "SELECT name, species, rarity, level, health FROM animals "
                "WHERE guild_id=? AND user_id=?", (g.id, ctx.author.id)).fetchall()
            if not rows:
                await ctx.send("❄ Aucun animal. La nature t'attend.")
                return
            lines = [f"• {r['name']} ({r['species']}, {r['rarity']}) — Niv {r['level']}, "
                     f"PV {r['health']}" for r in rows]
            await ctx.send(embed=frost_embed(title="🐾 Tes animaux",
                                             desc="\n".join(lines), color=ICE))
        elif action == "acheter" and name:
            species, rarity = next(((s, r) for s, r in SPECIES if s.lower() == name.lower()),
                                   (None, None))
            if not species:
                await ctx.send("❄ Espèce inconnue. Essayez : " +
                               ", ".join(s for s, _ in SPECIES))
                return
            price = {"Normal": 1000, "Légendaire": 5000,
                     "Mythique": 25000, "Exclusif": 100000}[rarity]
            u = get_user(db, g.id, ctx.author.id)
            if u["wallet"] < price:
                await ctx.send(f"❄ Il te faut **{fmt(price)}**.")
                return
            update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - price)
            add_tx(db, g.id, ctx.author.id, "animal_buy", -price)
            db.execute(
                "INSERT INTO animals (guild_id, user_id, name, species, rarity, fed_at) "
                "VALUES (?,?,?,?,?,?)",
                (g.id, ctx.author.id, name, species, rarity, now()))
            db.commit()
            await ctx.send(f"🐾 **{name}** ({rarity}) rejoint tes rangs pour {COIN} **{fmt(price)}**.")
        elif action == "nourrir" and name:
            db.execute("UPDATE animals SET fed_at=? WHERE guild_id=? AND user_id=? AND name=?",
                       (now(), g.id, ctx.author.id, name))
            db.commit()
            await ctx.send(f"🍖 **{name}** a été nourri(e).")
        elif action == "soigner" and name:
            db.execute("UPDATE animals SET health=100 WHERE guild_id=? AND user_id=? AND name=?",
                       (g.id, ctx.author.id, name))
            db.commit()
            await ctx.send(f"💊 **{name}** est soigné(e).")
        else:
            await ctx.send("❄ Usage : `!animal liste | acheter <espèce> | nourrir <nom> | soigner <nom>`")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  N. GARAGE, ACCIDENTS & ASSURANCES
# ══════════════════════════════════════════════════════════════════════
VEHICLES = [
    ("Citadine polaire", 3000, 60, 50, 55, 70),
    ("Berline de glace", 8000, 75, 65, 70, 80),
    ("SUV boréal", 15000, 85, 80, 75, 90),
    ("Sportive givrée", 30000, 95, 90, 85, 75),
    ("Hypercar de cristal", 75000, 100, 100, 95, 85),
]

@bot.command(name="garage", help="Gérer ton garage (acheter, liste, réparer).")
async def garage(ctx, action: str = None, name: str = None):
    g = ctx.guild
    db = connect()
    try:
        if action == "liste":
            rows = db.execute(
                "SELECT name, value, speed, power, handling, durability, condition "
                "FROM vehicles WHERE guild_id=? AND user_id=?",
                (g.id, ctx.author.id)).fetchall()
            if not rows:
                await ctx.send("❄ Ton garage est vide. Le catalogue t'attend.")
                return
            lines = []
            for r in rows:
                lines.append(
                    f"• **{r['name']}** — Vitesse {r['speed']} / Puissance {r['power']} / "
                    f"Conduite {r['handling']} / Durabilité {r['durability']} "
                    f"(état {r['condition']} %)")
            await ctx.send(embed=frost_embed(title="🚗 Garage",
                                             desc="\n".join(lines), color=ICE))
        elif action == "acheter" and name:
            veh = next(((v) for v in VEHICLES if v[0].lower() == name.lower()), None)
            if not veh:
                await ctx.send("❄ Véhicule inconnu. Essayez : " +
                               ", ".join(v[0] for v in VEHICLES))
                return
            vname, price, speed, power, handling, dur = veh
            u = get_user(db, g.id, ctx.author.id)
            if u["wallet"] < price:
                await ctx.send(f"❄ Il te faut **{fmt(price)}**.")
                return
            update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - price)
            add_tx(db, g.id, ctx.author.id, "vehicle_buy", -price)
            db.execute(
                "INSERT INTO vehicles (guild_id, user_id, name, value, speed, power, "
                "handling, durability, condition) VALUES (?,?,?,?,?,?,?,?,100)",
                (g.id, ctx.author.id, vname, price, speed, power, handling, dur))
            db.commit()
            await ctx.send(f"🚗 **{vname}** rejoint ton garage pour {COIN} **{fmt(price)}**.")
        elif action == "reparer" and name:
            cost = 500
            u = get_user(db, g.id, ctx.author.id)
            if u["wallet"] < cost:
                await ctx.send(f"❄ La réparation coûte **{fmt(cost)}**.")
                return
            n = db.execute(
                "UPDATE vehicles SET condition=100 WHERE guild_id=? AND user_id=? AND name=?",
                (g.id, ctx.author.id, name)).rowcount
            if n:
                update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - cost)
                add_tx(db, g.id, ctx.author.id, "vehicle_repair", -cost)
                await ctx.send(f"🔧 **{name}** réparé(e) à 100 %.")
            else:
                await ctx.send("❄ Véhicule introuvable dans ton garage.")
        else:
            await ctx.send("❄ Usage : `!garage liste | acheter <véhicule> | reparer <véhicule>`")
    finally:
        db.close()

def _active_insurance(db, guild_id, user_id):
    """Retourne la première assurance active (priorité permanente)."""
    rows = db.execute(
        "SELECT * FROM insurance WHERE guild_id=? AND user_id=? AND active=1 "
        "AND (expires_at=0 OR expires_at>?) ORDER BY "
        "CASE kind WHEN 'permanent' THEN 0 WHEN 'temp_30d' THEN 1 "
        "WHEN 'temp_24h' THEN 2 ELSE 3 END",
        (guild_id, user_id, now())).fetchall()
    for r in rows:
        if r["kind"] == "single":
            return r
        if r["kind"] in ("temp_24h", "temp_30d") and r["expires_at"] > now():
            return r
        if r["kind"] == "permanent" and r["cap"] - r["cap_used"] > 0:
            return r
    return None

def claim_insurance(db, guild_id, user_id, loss, reason) -> int:
    """Indemnise 50 % de la perte réelle selon la formule active (N)."""
    ins = _active_insurance(db, guild_id, user_id)
    if not ins or loss <= 0:
        return 0
    payout = int(loss * 0.5)
    kind = ins["kind"]
    if kind == "single":
        payout = min(payout, loss)
        db.execute("UPDATE insurance SET active=0 WHERE guild_id=? AND user_id=? AND kind='single'",
                   (guild_id, user_id))
    elif kind == "permanent":
        payout = min(payout, ins["cap"] - ins["cap_used"])
        db.execute("UPDATE insurance SET cap_used=cap_used+? WHERE guild_id=? AND user_id=? AND kind='permanent'",
                   (payout, guild_id, user_id))
    else:  # temporaire : couvre sans consommer (durée limitée)
        payout = min(payout, loss)
    if payout <= 0:
        return 0
    db.execute(
        "INSERT INTO insurance_claims (guild_id, user_id, insurance_kind, loss, payout, reason, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (guild_id, user_id, kind, loss, payout, reason, now()))
    db.commit()
    return payout

@bot.command(name="assurance", help="Statut de tes assurances.")
async def assurance(ctx):
    g = ctx.guild
    db = connect()
    try:
        rows = db.execute(
            "SELECT * FROM insurance WHERE guild_id=? AND user_id=? AND active=1 "
            "AND (expires_at=0 OR expires_at>?)", (g.id, ctx.author.id, now())).fetchall()
        if not rows:
            await ctx.send("❄ Aucune assurance active. La boutique a une catégorie 🛡️.")
            return
        lines = []
        for r in rows:
            if r["kind"] == "permanent":
                lines.append(f"• 🛡️ Permanente — plafond restant **{fmt(r['cap'] - r['cap_used'])}**")
            elif r["kind"] == "single":
                lines.append("• 🛡️ Sinistre unique — prête à couvrir un sinistre")
            else:
                lines.append(f"• 🛡️ Temporaire — jusqu'à **{fmt_ts(r['expires_at'])}**")
        await ctx.send(embed=frost_embed(title="🛡️ Assurances actives",
                                         desc="\n".join(lines), color=ICE))
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  O. MARCHÉ DYNAMIQUE — prix bornés, historique
# ══════════════════════════════════════════════════════════════════════
MARKET_RESOURCES = [
    ("Cristal de glace", 100, 10, 500),
    ("Pétrole polaire", 200, 20, 1000),
    ("Minerai de lune", 350, 30, 2000),
    ("Or givré", 800, 80, 5000),
]

def ensure_market(db, guild_id):
    for res, price, mn, mx in MARKET_RESOURCES:
        db.execute(
            "INSERT OR IGNORE INTO market (guild_id, resource, price, min_price, max_price, updated_at) "
            "VALUES (?,?,?,?,?,?)", (guild_id, res, price, mn, mx, now()))
    db.commit()

def tick_market(db, guild_id):
    """Variation contrôlée : offre/demande + bornes min/max."""
    ensure_market(db, guild_id)
    for r in db.execute("SELECT * FROM market WHERE guild_id=?", (guild_id,)).fetchall():
        drift = random.uniform(-0.06, 0.07)
        new = int(r["price"] * (1 + drift))
        new = max(r["min_price"], min(r["max_price"], new))
        db.execute("UPDATE market SET price=?, updated_at=? WHERE guild_id=? AND resource=?",
                   (new, now(), guild_id, r["resource"]))
        db.execute("INSERT INTO market_history (guild_id, resource, price, created_at) "
                   "VALUES (?,?,?,?)", (guild_id, r["resource"], new, now()))
    db.commit()

@bot.command(name="marche", aliases=["market"], help="Marché de ressources dynamique.")
async def marche(ctx):
    g = ctx.guild
    db = connect()
    try:
        ensure_market(db, g.id)
        rows = db.execute("SELECT resource, price, min_price, max_price "
                          "FROM market WHERE guild_id=?", (g.id,)).fetchall()
        lines = []
        for r in rows:
            trend = "📈" if r["price"] > (r["min_price"] + r["max_price"]) / 2 else "📉"
            lines.append(f"• {r['resource']} — {COIN} **{fmt(r['price'])}** {trend}")
        e = frost_embed(title="📊 Marché dynamique",
                        desc="Les prix varient selon l'offre, la demande et les événements.\n\n"
                             + "\n".join(lines) +
                             f"\n\nAchat : `!marche buy <ressource>` — Vente : `!marche sell <ressource>`",
                        color=ICE)
        await ctx.send(embed=e)
    finally:
        db.close()

@bot.command(name="marchebuy", help="Acheter une ressource sur le marché.")
async def marchebuy(ctx, resource: str, qty: int = 1):
    g = ctx.guild
    db = connect()
    try:
        ensure_market(db, g.id)
        r = db.execute("SELECT * FROM market WHERE guild_id=? AND resource=?",
                       (g.id, resource)).fetchone()
        if not r:
            await ctx.send("❄ Ressource inconnue. Voir `!marche`.")
            return
        if qty < 1 or qty > 10000:
            await ctx.send("❄ Quantité invalide (1 à 10 000).")
            return
        total = r["price"] * qty
        u = get_user(db, g.id, ctx.author.id)
        if u["wallet"] < total:
            await ctx.send(f"❄ Il te faut **{fmt(total)}**.")
            return
        update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - total)
        add_tx(db, g.id, ctx.author.id, "market_buy", -total)
        _inv_add(db, g.id, ctx.author.id, resource, qty)
        db.execute("UPDATE market SET demand=demand+? WHERE guild_id=? AND resource=?",
                   (qty, g.id, resource))
        db.commit()
        await ctx.send(f"📊 **{qty} × {resource}** acheté(s) pour {COIN} **{fmt(total)}**.")
    finally:
        db.close()

@bot.command(name="marchesell", help="Vendre une ressource sur le marché.")
async def marchesell(ctx, resource: str, qty: int = 1):
    g = ctx.guild
    db = connect()
    try:
        ensure_market(db, g.id)
        r = db.execute("SELECT * FROM market WHERE guild_id=? AND resource=?",
                       (g.id, resource)).fetchone()
        if not r:
            await ctx.send("❄ Ressource inconnue.")
            return
        if qty < 1 or qty > 10000:
            await ctx.send("❄ Quantité invalide (1 à 10 000).")
            return
        inv = db.execute(
            "SELECT qty FROM shop_inventory WHERE guild_id=? AND user_id=? AND item=?",
            (g.id, ctx.author.id, resource)).fetchone()
        if not inv or inv["qty"] < qty:
            await ctx.send("❄ Tu n'en as pas assez en stock.")
            return
        total = int(r["price"] * qty * 0.9)   # spread de marché
        update_user(db, g.id, ctx.author.id, wallet=get_user(db, g.id, ctx.author.id)["wallet"] + total)
        db.execute("UPDATE shop_inventory SET qty=qty-? WHERE guild_id=? AND user_id=? AND item=?",
                   (qty, g.id, ctx.author.id, resource))
        add_tx(db, g.id, ctx.author.id, "market_sell", total)
        db.execute("UPDATE market SET supply=supply+? WHERE guild_id=? AND resource=?",
                   (qty, g.id, resource))
        db.commit()
        await ctx.send(f"📊 **{qty} × {resource}** vendu(s) pour {COIN} **{fmt(total)}**.")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  P. MISSIONS QUOTIDIENNES & HEBDOMADAIRES
# ══════════════════════════════════════════════════════════════════════
DAILY_MISSIONS = [
    ("Travaille 2 fois", "work", 2, 300),
    ("Payer un membre", "pay", 1, 250),
    ("Ouvre un coffre", "chest", 1, 400),
]
WEEKLY_MISSIONS = [
    ("Gagne 5 000 ⚙️", "earn", 5000, 2500),
    ("Achète 3 articles", "buy", 3, 1500),
]

def ensure_missions(db, guild_id, user_id):
    day = datetime.now().date()
    last = db.execute(
        "SELECT MAX(expires_at) FROM missions WHERE guild_id=? AND user_id=? AND kind='daily'",
        (guild_id, user_id)).fetchone()[0] or 0
    if datetime.fromtimestamp(last).date() != day:
        for desc, kind, goal, reward in random.sample(DAILY_MISSIONS, 3):
            db.execute(
                "INSERT INTO missions (guild_id, user_id, kind, desc, goal, reward, expires_at) "
                "VALUES (?,?, 'daily',?,?,?,?)",
                (guild_id, user_id, desc, goal, reward, now() + 86400))
    week = int(datetime.now().strftime("%Y-W%W"))
    has_week = db.execute(
        "SELECT COUNT(*) FROM missions WHERE guild_id=? AND user_id=? AND kind='weekly' "
        "AND done=0", (guild_id, user_id)).fetchone()[0]
    if not has_week:
        for desc, kind, goal, reward in WEEKLY_MISSIONS:
            db.execute(
                "INSERT INTO missions (guild_id, user_id, kind, desc, goal, reward, expires_at) "
                "VALUES (?,?, 'weekly',?,?,?,?)",
                (guild_id, user_id, desc, goal, reward, now() + 7 * 86400))
    db.commit()

def bump_mission(db, guild_id, user_id, kind, amount=1):
    rows = db.execute(
        "SELECT * FROM missions WHERE guild_id=? AND user_id=? AND kind IN ('daily','weekly') "
        "AND done=0 AND claimed=0 AND expires_at>?", (guild_id, user_id, now())).fetchall()
    for m in rows:
        if m["desc"].split()[0].lower().startswith(kind) or kind in m["desc"].lower():
            new = m["progress"] + amount
            db.execute("UPDATE missions SET progress=? WHERE id=?", (new, m["id"]))
            if new >= m["goal"]:
                db.execute("UPDATE missions SET done=1 WHERE id=?", (m["id"],))
    db.commit()

@bot.command(name="missions", help="Tes missions quotidiennes et hebdomadaires.")
async def missions(ctx):
    g = ctx.guild
    db = connect()
    try:
        ensure_missions(db, g.id, ctx.author.id)
        rows = db.execute(
            "SELECT * FROM missions WHERE guild_id=? AND user_id=? AND expires_at>?"
            " ORDER BY kind, done", (g.id, ctx.author.id, now())).fetchall()
        if not rows:
            await ctx.send("❄ Aucune mission active. Reviens plus tard.")
            return
        lines = []
        for m in rows:
            tag = {"daily": "📅", "weekly": "🗓️"}[m["kind"]]
            state = "✅" if m["claimed"] else ("✔️" if m["done"] else "⬜")
            lines.append(f"{tag} {state} **{m['desc']}** — "
                         f"{fmt(min(m['progress'], m['goal']))}/{fmt(m['goal'])} "
                         f"→ {COIN} {fmt(m['reward'])}")
        e = frost_embed(title="🎯 Missions", desc="\n".join(lines), color=ICE)
        await ctx.send(embed=e)
    finally:
        db.close()

@bot.command(name="missionclaim", help="Récupérer une mission terminée.")
async def missionclaim(ctx, mission_id: int):
    g = ctx.guild
    db = connect()
    try:
        m = db.execute(
            "SELECT * FROM missions WHERE id=? AND guild_id=? AND user_id=?",
            (mission_id, g.id, ctx.author.id)).fetchone()
        if not m:
            await ctx.send("❄ Mission introuvable.")
            return
        if not m["done"]:
            await ctx.send("❄ Pas encore terminée. La glace n'aime pas la précipitation.")
            return
        if m["claimed"]:
            await ctx.send("❄ Déjà récupérée. Une seule fois.")
            return
        reward = int(m["reward"] * multiplier(db, g.id))
        u = get_user(db, g.id, ctx.author.id)
        update_user(db, g.id, ctx.author.id, wallet=u["wallet"] + reward)
        add_tx(db, g.id, ctx.author.id, "mission", reward)
        db.execute("UPDATE missions SET claimed=1 WHERE id=?", (m["id"],))
        db.commit()
        await ctx.send(f"🎯 Mission accomplie : {COIN} **{fmt(reward)}**.")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  G. GOUVERNEMENT — Président, PM, Ministre Finances, Chef Mafia, Ombre
# ══════════════════════════════════════════════════════════════════════
OFFICES = ["President", "PremierMinistre", "MinistreFinances", "ChefMafia", "MaitreOmbre"]

def political_limits(db, guild_id, office):
    """Éligibilité : Président = Top 5 richesse + Top 7 popularité + Top 10 niveau."""
    if office == "President":
        top5 = {r["user_id"] for r in db.execute(
            "SELECT user_id FROM users WHERE guild_id=? ORDER BY (wallet+bank) DESC LIMIT 5",
            (guild_id,)).fetchall()}
        top7 = {r["user_id"] for r in db.execute(
            "SELECT user_id FROM users WHERE guild_id=? ORDER BY xp DESC LIMIT 7",
            (guild_id,)).fetchall()}
        top10 = {r["user_id"] for r in db.execute(
            "SELECT user_id FROM users WHERE guild_id=? ORDER BY level DESC LIMIT 10",
            (guild_id,)).fetchall()}
        return top5 & top7 & top10
    return None  # seuils configurables plus tard

@bot.command(name="election", help="Candidater à un poste de gouvernement.")
async def election(ctx, office: str = None, member: discord.Member = None):
    g = ctx.guild
    db = connect()
    try:
        if not admin_check(ctx):
            await ctx.send(q("no_perm"))
            return
        office = (office or "President").strip()
        if office not in OFFICES:
            await ctx.send("❄ Postes : " + ", ".join(OFFICES))
            return
        m = member or ctx.author
        eligible = political_limits(db, g.id, office)
        if eligible is not None and m.id not in eligible:
            await ctx.send(f"❄ {m.display_name} n'est pas éligible à ce poste.")
            return
        db.execute(
            "INSERT INTO government (guild_id, office, user_id, since) VALUES (?,?,?,?) "
            "ON CONFLICT(guild_id, office) DO UPDATE SET user_id=excluded.user_id, since=excluded.since",
            (g.id, office, m.id, now()))
        db.commit()
        log_event(db, g.id, ctx.author.id, "election", f"{office} → {m.id}")
        await ctx.send(f"🏛️ **{m.display_name}** est désormais **{office}**.")
    finally:
        db.close()

@bot.command(name="gouvernement", help="Voir le gouvernement du serveur.")
async def gouvernement(ctx):
    g = ctx.guild
    db = connect()
    try:
        rows = db.execute(
            "SELECT office, user_id, since FROM government WHERE guild_id=?",
            (g.id,)).fetchall()
        if not rows:
            await ctx.send("❄ Le trône est vide. Le peuple attend.")
            return
        lines = [f"• **{r['office']}** — <@{r['user_id']}> (depuis {fmt_ts(r['since'])})"
                 for r in rows]
        await ctx.send(embed=frost_embed(title="🏛️ Gouvernement",
                                         desc="\n".join(lines), color=FROST))
    finally:
        db.close()

@bot.command(name="vote", help="Voter sur une proposition (gouvernement).")
async def vote(ctx, topic: str, choice: str):
    g = ctx.guild
    db = connect()
    try:
        db.execute(
            "INSERT INTO votes (guild_id, topic, voter_id, choice, created_at) "
            "VALUES (?,?,?,?,?) ON CONFLICT(guild_id, topic, voter_id) "
            "DO UPDATE SET choice=excluded.choice, created_at=excluded.created_at",
            (g.id, topic, ctx.author.id, choice, now()))
        db.commit()
        tally = db.execute(
            "SELECT choice, COUNT(*) c FROM votes WHERE guild_id=? AND topic=? GROUP BY choice",
            (g.id, topic)).fetchall()
        lines = [f"• {t['choice']} : **{t['c']}**" for t in tally]
        await ctx.send(f"🗳️ Vote enregistré pour **{topic}**.\n" + "\n".join(lines))
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  Y. EMPRUNTS — un seul actif par membre
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="emprunt", help="Emprunter (politique 100 000/10 j ou standard 50 000/5 j).")
async def emprunt(ctx, kind: str = "standard"):
    g = ctx.guild
    db = connect()
    try:
        active = db.execute(
            "SELECT * FROM loans WHERE guild_id=? AND user_id=? AND status='active'",
            (g.id, ctx.author.id)).fetchone()
        if active:
            await ctx.send(f"⛔ Un emprunt actif jusqu'à **{fmt_ts(active['due_at'])}**. "
                           f"Rembourse d'abord.")
            return
        if kind == "politique":
            amount, days = 100000, 10
        else:
            amount, days = 50000, 5
        due = now() + days * 86400
        db.execute(
            "INSERT OR REPLACE INTO loans (guild_id, user_id, amount, due_at, status, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (g.id, ctx.author.id, amount, due, "active", now()))
        u = get_user(db, g.id, ctx.author.id)
        update_user(db, g.id, ctx.author.id, wallet=u["wallet"] + amount)
        add_tx(db, g.id, ctx.author.id, "loan", amount)
        db.commit()
        await ctx.send(f"🏦 Emprunt **{kind}** de {COIN} **{fmt(amount)}** — "
                       f"à rembourser avant **{fmt_ts(due)}**.")
    finally:
        db.close()

@bot.command(name="rembourser", help="Rembourser ton emprunt.")
async def rembourser(ctx):
    g = ctx.guild
    db = connect()
    try:
        loan = db.execute(
            "SELECT * FROM loans WHERE guild_id=? AND user_id=? AND status='active'",
            (g.id, ctx.author.id)).fetchone()
        if not loan:
            await ctx.send("❄ Tu n'as pas d'emprunt actif.")
            return
        u = get_user(db, g.id, ctx.author.id)
        if u["wallet"] < loan["amount"]:
            await ctx.send(f"❄ Il te faut **{fmt(loan['amount'])}**, tu as **{fmt(u['wallet'])}**.")
            return
        update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - loan["amount"])
        add_tx(db, g.id, ctx.author.id, "loan_repay", -loan["amount"])
        db.execute("UPDATE loans SET status='repaid' WHERE id=?", (loan["id"],))
        db.commit()
        await ctx.send(f"🏦 Emprunt remboursé. La confiance est restaurée.")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  K. BANQUE CENTRALE & X. TAXES / SOLIDARITÉ / AIDE
# ══════════════════════════════════════════════════════════════════════
def treasury_move(db, guild_id, account, amount, kind, ref_user=None, note=""):
    db.execute(
        "INSERT INTO treasury (guild_id, account, balance) VALUES (?,?,?) "
        "ON CONFLICT(guild_id, account) DO UPDATE SET balance=balance+?",
        (guild_id, account, amount, amount))
    db.execute(
        "INSERT INTO treasury_ledger (guild_id, account, kind, amount, ref_user, note, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (guild_id, account, kind, amount, ref_user, note, now()))
    db.commit()

@tasks.loop(hours=24)
async def auto_tax_loop():
    """X : solde > 3 000 → taxe 30 ⚙️/jour (15 solidarité + 15 économique).
    Aide quotidienne aux membres sans emploi, financée par la solidarité."""
    for guild in bot.guilds:
        db = connect()
        try:
            day = datetime.now().date()
            for u in db.execute(
                    "SELECT * FROM users WHERE guild_id=?", (guild.id,)).fetchall():
                last_tax_day = datetime.fromtimestamp(u["last_tax"]).date() if u["last_tax"] else None
                if last_tax_day == day:
                    continue
                # ── Taxe ──
                if u["wallet"] > 3000:
                    tax = min(30, u["wallet"])
                    update_user(db, guild.id, u["user_id"],
                                wallet=u["wallet"] - tax, last_tax=now())
                    add_tx(db, guild.id, u["user_id"], "tax", -tax)
                    treasury_move(db, guild.id, "solidarite", tax // 2, "tax",
                                  u["user_id"], "taxe solidarité")
                    treasury_move(db, guild.id, "economique", tax - tax // 2, "tax",
                                  u["user_id"], "taxe économique")
                # ── Aide (sans emploi) ──
                last_aid_day = datetime.fromtimestamp(u["last_aid"]).date() if u["last_aid"] else None
                if last_aid_day != day and not u["job"]:
                    aid = int(config_get(db, guild.id, "daily_aid", "50"))
                    sol = db.execute(
                        "SELECT balance FROM treasury WHERE guild_id=? AND account='solidarite'",
                        (guild.id,)).fetchone()
                    balance = sol["balance"] if sol else 0
                    if balance >= aid:
                        treasury_move(db, guild.id, "solidarite", -aid, "aid",
                                      u["user_id"], "aide quotidienne")
                        update_user(db, guild.id, u["user_id"],
                                    wallet=u["wallet"] + aid, last_aid=now())
                        add_tx(db, guild.id, u["user_id"], "aid", aid)
        except Exception as ex:
            print("auto_tax_loop:", ex)
        finally:
            db.close()

@bot.command(name="caisse", help="Caisse centrale du serveur (admins).")
@commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
async def caisse(ctx):
    g = ctx.guild
    if not admin_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        rows = db.execute(
            "SELECT account, balance FROM treasury WHERE guild_id=?", (g.id,)).fetchall()
        if not rows:
            await ctx.send("❄ La caisse est vide. Le grand livre attend ses premières lignes.")
            return
        lines = [f"• **{r['account']}** : {COIN} **{fmt(r['balance'])}**" for r in rows]
        hist = db.execute(
            "SELECT account, kind, amount, note, created_at FROM treasury_ledger "
            "WHERE guild_id=? ORDER BY created_at DESC LIMIT 5", (g.id,)).fetchall()
        hist_lines = [f"• [{h['account']}] {h['kind']} {h['amount']:+} — {h['note']} "
                      f"({fmt_ts(h['created_at'])})" for h in hist]
        e = frost_embed(title="🏛️ Caisse centrale",
                        desc="\n".join(lines) + "\n\n**Dernières opérations :**\n"
                             + ("\n".join(hist_lines) if hist_lines else "Aucune."),
                        color=FROST)
        await ctx.send(embed=e)
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  M. FAMILLES — Chef / Sous-chef, caisse, 20 % du salaire
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="famille", help="Créer / rejoindre / quitter / verser / promouvoir / info famille.")
async def famille(ctx, action: str = None, name: str = None, tag: str = None,
                  member: discord.Member = None):
    g = ctx.guild
    db = connect()
    try:
        u = get_user(db, g.id, ctx.author.id)
        if action == "creer" and name and tag:
            if u["family_id"]:
                await ctx.send("❄ Tu es déjà dans une famille.")
                return
            price = int(config_get(db, g.id, "family_create_cost", "3000"))
            if u["wallet"] < price:
                await ctx.send(f"❄ Création : **{fmt(price)}**.")
                return
            update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - price)
            add_tx(db, g.id, ctx.author.id, "family_create", -price)
            cur = db.execute(
                "INSERT INTO families (guild_id, name, tag, leader_id, created_at) "
                "VALUES (?,?,?,?,?)", (g.id, name, tag, ctx.author.id, now()))
            fid = cur.lastrowid
            update_user(db, g.id, ctx.author.id, family_id=fid, family_role="chef")
            db.commit()
            await ctx.send(f"👨‍👩‍👧 **Famille {name} [{tag}]** fondée. Tu en es le Chef.")
        elif action == "rejoindre" and name:
            if u["family_id"]:
                await ctx.send("❄ Tu es déjà dans une famille.")
                return
            if now() - u["family_left_at"] < 7200:
                await ctx.send(f"⏳ Attends **{remaining(u['family_left_at'] + 7200)}** avant de rejoindre.")
                return
            fam = db.execute(
                "SELECT * FROM families WHERE guild_id=? AND name=?", (g.id, name)).fetchone()
            if not fam:
                await ctx.send("❄ Famille introuvable.")
                return
            update_user(db, g.id, ctx.author.id, family_id=fam["id"], family_role="membre")
            db.commit()
            await ctx.send(f"👨‍👩‍👧 Tu rejoins la famille **{fam['name']} [{fam['tag']}]**.")
        elif action == "quitter":
            if not u["family_id"]:
                await ctx.send("❄ Tu n'es dans aucune famille.")
                return
            fam = db.execute("SELECT * FROM families WHERE guild_id=? AND id=?",
                             (g.id, u["family_id"])).fetchone()
            update_user(db, g.id, ctx.author.id,
                        family_id=None, family_role=None, family_left_at=now())
            if fam and fam["leader_id"] == ctx.author.id:
                others = db.execute(
                    "SELECT user_id FROM users WHERE guild_id=? AND family_id=?",
                    (g.id, u["family_id"])).fetchone()
                if others:
                    update_user(db, g.id, others["user_id"], family_role="chef")
                    db.execute("UPDATE families SET leader_id=? WHERE id=?",
                               (others["user_id"], fam["id"]))
                else:
                    db.execute("DELETE FROM families WHERE id=?", (fam["id"],))
            db.commit()
            await ctx.send("👋 Tu quittes ta famille. Retour possible dans 2 h.")
        elif action == "verser" and name:
            fam = db.execute(
                "SELECT * FROM families WHERE guild_id=? AND id=?",
                (g.id, u["family_id"])).fetchone() if u["family_id"] else None
            if not fam:
                await ctx.send("❄ Tu n'es dans aucune famille.")
                return
            amount = int(re.sub(r"\D", "", name) or 0)
            if amount <= 0:
                await ctx.send("❄ Montant invalide.")
                return
            if u["wallet"] < amount:
                await ctx.send(f"❄ Tu n'as que **{fmt(u['wallet'])}**.")
                return
            update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - amount)
            add_tx(db, g.id, ctx.author.id, "family_give", -amount)
            db.execute("UPDATE families SET treasury=treasury+? WHERE id=?", (amount, fam["id"]))
            db.execute(
                "INSERT INTO family_ledger (guild_id, family_id, kind, amount, ref_user, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (g.id, fam["id"], "contribution", amount, ctx.author.id, now()))
            db.commit()
            await ctx.send(f"💰 **{fmt(amount)}** versés à la caisse familiale.")
        elif action == "promouvoir" and member:
            if not u["family_id"]:
                await ctx.send("❄ Tu n'es dans aucune famille.")
                return
            fam = db.execute("SELECT * FROM families WHERE guild_id=? AND id=?",
                             (g.id, u["family_id"])).fetchone()
            if not fam or fam["leader_id"] != ctx.author.id:
                await ctx.send("❄ Seul le Chef peut promouvoir un Sous-chef.")
                return
            if fam["coleader_id"] == member.id:
                await ctx.send("❄ Ce membre est déjà Sous-chef.")
                return
            target = get_user(db, g.id, member.id)
            if target["family_id"] != fam["id"]:
                await ctx.send("❄ Ce membre n'est pas dans ta famille.")
                return
            db.execute("UPDATE families SET coleader_id=? WHERE id=?", (member.id, fam["id"]))
            update_user(db, g.id, member.id, family_role="sous-chef")
            db.commit()
            await ctx.send(f"⭐ **{member.display_name}** est maintenant **Sous-chef**.")
        elif action == "info" or not action:
            if not u["family_id"]:
                await ctx.send("❄ Tu n'es dans aucune famille. `!famille creer <nom> <tag>`")
                return
            fam = db.execute("SELECT * FROM families WHERE guild_id=? AND id=?",
                             (g.id, u["family_id"])).fetchone()
            if not fam:
                await ctx.send("❄ Famille dissoute.")
                return
            members = db.execute(
                "SELECT user_id, family_role FROM users WHERE guild_id=? AND family_id=?",
                (g.id, u["family_id"])).fetchall()
            lines = [f"• <@{m['user_id']}> — **{m['family_role'] or 'membre'}**" for m in members]
            e = frost_embed(
                title=f"👨‍👩‍👧 {fam['name']} [{fam['tag']}]",
                desc=f"Caisse familiale : {COIN} **{fmt(fam['treasury'])}**\n\n"
                     + "\n".join(lines),
                color=FROST)
            await ctx.send(embed=e)
        else:
            await ctx.send("❄ Usage : `!famille creer <nom> <tag> | rejoindre <nom> | "
                           "quitter | verser <montant> | info`")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  C. MODÉRATION & SÉCURITÉ — avertissements, role-ban, logs
# ══════════════════════════════════════════════════════════════════════
def _can_sanitize(actor: discord.Member, target: discord.Member) -> bool:
    """Hiérarchie : aucun membre de rang égal/supérieur ni propriétaire."""
    if target.id == OWNER_ID:
        return False
    if target.id == target.guild.owner_id:
        return False
    if target.guild_permissions.administrator and not actor.guild_permissions.administrator:
        return False
    if actor.id != OWNER_ID and actor.id != actor.guild.owner_id \
            and actor.top_role.position <= target.top_role.position:
        return False
    bot_member = actor.guild.me
    if bot_member.top_role.position <= target.top_role.position:
        return False
    return True

@bot.command(name="warn", help="Avertir un membre (staff).")
async def warn(ctx, member: discord.Member, *, reason: str = ""):
    g = ctx.guild
    if not mod_check(ctx):
        await ctx.send(q("no_perm"))
        return
    if not _can_sanitize(ctx.author, member):
        await ctx.send("❄ La glace ne touche pas ceux qui sont au-dessus de toi.")
        return
    db = connect()
    try:
        db.execute(
            "INSERT INTO warnings (guild_id, user_id, reason, by_id, created_at) "
            "VALUES (?,?,?,?,?)", (g.id, member.id, reason, ctx.author.id, now()))
        db.commit()
        log_event(db, g.id, ctx.author.id, "warn", f"{member.id} : {reason}")
        logch = config_get(db, g.id, "mod_log_channel_id")
        if logch:
            ch = g.get_channel(int(logch))
            if ch:
                await ch.send(embed=frost_embed(
                    title="⚠️ Avertissement",
                    desc=f"**{member.mention}** — {reason}\nPar {ctx.author.mention}",
                    color=RED))
        await ctx.send(f"⚠️ {member.mention} averti(e) : {reason or 'sans motif'}")
    finally:
        db.close()

@bot.command(name="warnhistory", help="Historique des avertissements d'un membre.")
async def warnhistory(ctx, member: discord.Member = None):
    g = ctx.guild
    if not mod_check(ctx):
        await ctx.send(q("no_perm"))
        return
    m = member or ctx.author
    db = connect()
    try:
        rows = db.execute(
            "SELECT reason, by_id, created_at FROM warnings WHERE guild_id=? AND user_id=? "
            "ORDER BY created_at DESC", (g.id, m.id)).fetchall()
        if not rows:
            await ctx.send(f"❄ {m.display_name} n'a aucun avertissement. Impeccable.")
            return
        lines = [f"• {w['reason'] or '—'} (par <@{w['by_id']}>, {fmt_ts(w['created_at'])})"
                 for w in rows]
        await ctx.send(embed=frost_embed(
            title=f"⚠️ Historique — {m.display_name}", desc="\n".join(lines), color=RED))
    finally:
        db.close()

@bot.command(name="ban", help="Role-ban (rôle Ban configuré) — distinct du ban Discord.")
async def ban(ctx, member: discord.Member, *, reason: str = ""):
    g = ctx.guild
    if not mod_check(ctx):
        await ctx.send(q("no_perm"))
        return
    if not _can_sanitize(ctx.author, member):
        await ctx.send("❄ La glace ne touche pas ceux qui sont au-dessus de toi.")
        return
    db = connect()
    try:
        ban_role_id = config_get(db, g.id, "ban_role_id")
        if not ban_role_id:
            await ctx.send("❄ Configure d'abord le rôle Ban : `+setbanrole <rôle>`")
            return
        ban_role = g.get_role(int(ban_role_id))
        if not ban_role:
            await ctx.send("❄ Rôle Ban introuvable.")
            return
        removed = [r.name for r in member.roles if r != g.default_role and r != ban_role]
        try:
            await member.add_roles(ban_role, reason=f"role-ban {reason}".strip())
            for r in member.roles:
                if r != g.default_role and r != ban_role:
                    try:
                        await member.remove_roles(r, reason="role-ban")
                    except discord.HTTPException:
                        pass
        except discord.HTTPException as e:
            await ctx.send(f"❄ Discord a refusé : {e}")
            return
        db.execute(
            "INSERT OR REPLACE INTO role_bans (guild_id, user_id, reason, by_id, created_at, removed_roles) "
            "VALUES (?,?,?,?,?,?)",
            (g.id, member.id, reason, ctx.author.id, now(), json.dumps(removed)))
        db.commit()
        log_event(db, g.id, ctx.author.id, "role_ban", f"{member.id} : {reason}")
        logch = config_get(db, g.id, "mod_log_channel_id")
        if logch:
            ch = g.get_channel(int(logch))
            if ch:
                await ch.send(embed=frost_embed(
                    title="🔒 Role-ban",
                    desc=f"**{member.mention}** — {reason}\nPar {ctx.author.mention}\n"
                         f"Rôles retirés : {', '.join(removed) or 'aucun'}",
                    color=RED))
        await ctx.send(f"{q('ban')}\n🔒 {member.mention} est role-banni(e).")
    finally:
        db.close()

@bot.command(name="banned", help="État du role-ban d'un membre.")
async def banned(ctx, member: discord.Member = None):
    g = ctx.guild
    if not mod_check(ctx):
        await ctx.send(q("no_perm"))
        return
    m = member or ctx.author
    db = connect()
    try:
        r = db.execute(
            "SELECT * FROM role_bans WHERE guild_id=? AND user_id=?",
            (g.id, m.id)).fetchone()
        if r:
            await ctx.send(f"🔒 {m.display_name} est role-banni(e) — {r['reason'] or '—'} "
                           f"(depuis {fmt_ts(r['created_at'])})")
        else:
            await ctx.send(f"❄ {m.display_name} n'est pas role-banni(e).")
    finally:
        db.close()

@bot.command(name="unban", help="Lever un role-ban et restaurer les rôles autorisés.")
async def unban(ctx, member: discord.Member):
    g = ctx.guild
    if not mod_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        r = db.execute(
            "SELECT * FROM role_bans WHERE guild_id=? AND user_id=?",
            (g.id, member.id)).fetchone()
        if not r:
            await ctx.send("❄ Ce membre n'est pas role-banni(e).")
            return
        ban_role_id = config_get(db, g.id, "ban_role_id")
        if ban_role_id:
            ban_role = g.get_role(int(ban_role_id))
            if ban_role and ban_role in member.roles:
                try:
                    await member.remove_roles(ban_role, reason="role-unban")
                except discord.HTTPException:
                    pass
        db.execute("DELETE FROM role_bans WHERE guild_id=? AND user_id=?", (g.id, member.id))
        db.commit()
        log_event(db, g.id, ctx.author.id, "role_unban", f"{member.id}")
        await ctx.send(f"❄ {member.mention} est libéré(e). La glace pardonne, rarement.")
    finally:
        db.close()

@bot.command(name="setbanrole", help="Configurer le rôle Ban (admins).")
async def setbanrole(ctx, role: discord.Role):
    g = ctx.guild
    if not admin_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        config_set(db, g.id, "ban_role_id", role.id)
        await ctx.send(f"🔒 Rôle Ban configuré : {role.mention}")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  L. PRISON — libération auto, caution, blocage des gains
# ══════════════════════════════════════════════════════════════════════
PRISON_BLOCKED = {"work", "mine", "daily", "chest", "kill", "roulette", "blackjack",
                  "pileouface", "des", "marchebuy", "marchesell"}

def in_prison(db, guild_id, user_id):
    r = db.execute(
        "SELECT * FROM prison WHERE guild_id=? AND user_id=? AND released=0 "
        "AND released_at>?", (guild_id, user_id, now())).fetchone()
    return r

@bot.before_invoke
async def prison_before_invoke(ctx):
    """Blocage des gains pendant la détention (L) + contrôle du préfixe (! membre / + staff)."""
    if not ctx.guild or ctx.command is None:
        return
    # Contrôle du préfixe : "!" pour les membres, "+" pour le staff/admin/propriétaire
    if ctx.command.name in STAFF_COMMANDS and (ctx.prefix or "").strip() == "!":
        await ctx.send("❄ Cette commande est réservée au staff : utilise le préfixe **`+`** "
                       f"(ex: `+{ctx.command.name}`).")
        raise commands.CheckFailure()
    if ctx.command.name not in PRISON_BLOCKED:
        return
    db = connect()
    try:
        p = in_prison(db, ctx.guild.id, ctx.author.id)
        if p:
            await ctx.send(
                f"⛓️ Tu es en prison jusqu'à **{fmt_ts(p['released_at'])}** "
                f"({remaining(p['released_at'])}).\n"
                f"Motif : {p['reason'] or '—'}\n"
                f"Caution : `+release` (sans cible).")
            raise commands.CheckFailure()
    finally:
        db.close()

@bot.command(name="imprison", help="Incarcérer un membre (staff/policier).")
async def imprison(ctx, member: discord.Member, minutes: int, *, reason: str = ""):
    g = ctx.guild
    if not mod_check(ctx):
        await ctx.send(q("no_perm"))
        return
    if not _can_sanitize(ctx.author, member):
        await ctx.send("❄ La glace ne touche pas ceux qui sont au-dessus de toi.")
        return
    minutes = max(1, min(minutes, 30 * 24 * 60))   # max 30 jours
    db = connect()
    try:
        db.execute(
            "INSERT INTO prison (guild_id, user_id, reason, by_id, started_at, released_at) "
            "VALUES (?,?,?,?,?,?)",
            (g.id, member.id, reason, ctx.author.id, now(), now() + minutes * 60))
        db.commit()
        log_event(db, g.id, ctx.author.id, "imprison", f"{member.id} {minutes} min : {reason}")
        await ctx.send(f"⛓️ {member.mention} est incarcéré(e) pour **{minutes} min** — {reason or '—'}")
    finally:
        db.close()

@bot.command(name="prisonstatus", help="État de détention d'un membre.")
async def prisonstatus(ctx, member: discord.Member = None):
    g = ctx.guild
    m = member or ctx.author
    db = connect()
    try:
        p = in_prison(db, g.id, m.id)
        if p:
            await ctx.send(f"⛓️ {m.display_name} : prison jusqu'à **{fmt_ts(p['released_at'])}** "
                           f"({remaining(p['released_at'])}) — {p['reason'] or '—'}")
        else:
            await ctx.send(f"❄ {m.display_name} est libre. Pour l'instant.")
    finally:
        db.close()

@bot.command(name="prisonhistory", help="Historique de prison d'un membre.")
async def prisonhistory(ctx, member: discord.Member = None):
    g = ctx.guild
    m = member or ctx.author
    db = connect()
    try:
        rows = db.execute(
            "SELECT reason, started_at, released_at, released FROM prison "
            "WHERE guild_id=? AND user_id=? ORDER BY started_at DESC LIMIT 10",
            (g.id, m.id)).fetchall()
        if not rows:
            await ctx.send(f"❄ {m.display_name} n'a jamais été incarcéré(e).")
            return
        lines = [f"• {r['reason'] or '—'} — {fmt_ts(r['started_at'])} → "
                 f"{fmt_ts(r['released_at'])}" + (" (libéré avant terme)" if r["released"] else "")
                 for r in rows]
        await ctx.send(embed=frost_embed(
            title=f"⛓️ Prison — {m.display_name}", desc="\n".join(lines), color=RED))
    finally:
        db.close()

@bot.command(name="release", help="Libérer (avec cible : staff) ou payer sa caution (sans cible).")
async def release(ctx, member: discord.Member = None):
    g = ctx.guild
    db = connect()
    try:
        if member:
            if not mod_check(ctx):
                await ctx.send(q("no_perm"))
                return
            p = in_prison(db, g.id, member.id)
            if not p:
                await ctx.send("❄ Ce membre n'est pas en prison.")
                return
            db.execute("UPDATE prison SET released=1 WHERE id=?", (p["id"],))
            db.commit()
            log_event(db, g.id, ctx.author.id, "release", f"{member.id}")
            await ctx.send(f"🔓 {member.mention} est libéré(e).")
        else:
            p = in_prison(db, g.id, ctx.author.id)
            if not p:
                await ctx.send("❄ Tu n'es pas en prison. Profites-en.")
                return
            rate = int(config_get(db, g.id, "prison_bail_rate", "100"))
            mins_left = max(1, (p["released_at"] - now()) // 60)
            bail = mins_left * rate
            u = get_user(db, g.id, ctx.author.id)
            if u["wallet"] < bail:
                await ctx.send(f"❄ Caution : **{fmt(bail)}** ({rate}/min), tu as **{fmt(u['wallet'])}**.")
                return
            update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - bail)
            add_tx(db, g.id, ctx.author.id, "bail", -bail)
            db.execute("UPDATE prison SET released=1 WHERE id=?", (p["id"],))
            db.commit()
            log_event(db, g.id, ctx.author.id, "bail_paid", f"{bail}")
            await ctx.send(f"🔓 Caution de {COIN} **{fmt(bail)}** payée. Tu es libre.")
    finally:
        db.close()

@bot.command(name="prisonbailrate", help="Tarif de caution par minute (admins).")
async def prisonbailrate(ctx, rate: int):
    g = ctx.guild
    if not admin_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        config_set(db, g.id, "prison_bail_rate", rate)
        await ctx.send(f"⚖️ Tarif de caution : **{rate}** ⚙️/minute.")
    finally:
        db.close()

@tasks.loop(seconds=60)
async def prison_loop():
    """Libération automatique persistante après redémarrage."""
    db = connect()
    try:
        rows = db.execute(
            "SELECT * FROM prison WHERE released=0 AND released_at<=?", (now(),)).fetchall()
        for p in rows:
            db.execute("UPDATE prison SET released=1 WHERE id=?", (p["id"],))
            db.commit()
            guild = bot.get_guild(p["guild_id"])
            if guild:
                logch = config_get(db, guild.id, "mod_log_channel_id")
                if logch:
                    ch = guild.get_channel(int(logch))
                    if ch:
                        await ch.send(f"🔓 <@{p['user_id']}> a purgé sa peine et est libéré(e).")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  B. PROGRESSION & STAFF — XP, niveaux, rangs, rankup
# ══════════════════════════════════════════════════════════════════════
STAFF_RANKS = ["Recrue", "Agent", "Inspecteur", "Sergent", "Capitaine", "Commandant"]

def xp_for_level(level: int) -> int:
    return 100 * level * (level + 1) // 2

@bot.event
async def on_message(message):
    if message.guild and message.author.id == DISBOARD_ID:
        await _handle_disboard(message)
        return
    if message.author.bot or not message.guild:
        return
    db = connect()
    try:
        u = get_user(db, message.guild.id, message.author.id)
        xp_gain = int(random.uniform(5, 15))
        new_xp = u["xp"] + xp_gain
        new_level = u["level"]
        while new_xp >= xp_for_level(new_level):
            new_level += 1
        update_user(db, message.guild.id, message.author.id,
                    xp=new_xp, level=new_level)
        if new_level > u["level"]:
            await message.reply(f"❄ **Niveau {new_level}** atteint. La progression est silencieuse, "
                                f"elle ne se crie pas.", mention_author=False)
            # Rôle de niveau
            lr = db.execute(
                "SELECT role_id FROM level_roles WHERE guild_id=? AND level=?",
                (message.guild.id, new_level)).fetchone()
            if lr:
                role = message.guild.get_role(lr["role_id"])
                if role:
                    try:
                        await message.author.add_roles(role, reason="niveau")
                    except discord.HTTPException:
                        pass
    finally:
        db.close()
    # Auto-suivi global (si activé)
    await autosuivi_relay(message)
    await bot.process_commands(message)
    # Nettoyage indicateur si la commande a été annulée (contrôle préfixe staff)
    ctx = await bot.get_context(message)
    if getattr(ctx, "_emilia_cancelled", False):
        try:
            typing = getattr(ctx, "_emilia_typing", None)
            if typing:
                await typing.__aexit__(None, None, None)
        except Exception:
            pass

@bot.command(name="profil", help="Profil complet (niveaux, staff, famille, succès).")
async def profil(ctx, member: discord.Member = None):
    g = ctx.guild
    m = member or ctx.author
    db = connect()
    try:
        u = get_user(db, g.id, m.id)
        ach = db.execute(
            "SELECT COUNT(*) FROM achievements WHERE guild_id=? AND user_id=?",
            (g.id, m.id)).fetchone()[0]
        fields = [
            ("⭐ Niveau", f"**{u['level']}** — {fmt(u['xp'])} / {fmt(xp_for_level(u['level'] + 1))} XP", False),
            (f"{COIN} Portefeuille", fmt(u["wallet"]), False),
            ("🏦 Banque", fmt(u["bank"]), False),
            ("🔥 Série daily", str(u["daily_streak"]), False),
        ]
        if u["staff_rank"]:
            fields.append(("🛡️ Rang staff", u["staff_rank"], False))
        if u["family_id"]:
            fam = db.execute("SELECT name, tag FROM families WHERE guild_id=? AND id=?",
                             (g.id, u["family_id"])).fetchone()
            if fam:
                fields.append(("👨‍👩‍👧 Famille", f"{fam['name']} [{fam['tag']}] — {u['family_role']}", False))
        fields.append(("🏅 Succès", str(ach), False))
        e = frost_embed(title=f"👤 {m.display_name}",
                        desc=f"{q('greet')}",
                        color=ICE, thumbnail=m.display_avatar.url, fields=fields)
        await ctx.send(embed=e)
    finally:
        db.close()

@bot.command(name="setrankstaff", help="Rôles possibles pour un palier staff (admins).")
async def setrankstaff(ctx, rank: str, *roles: discord.Role):
    g = ctx.guild
    if not admin_check(ctx):
        await ctx.send(q("no_perm"))
        return
    if rank not in STAFF_RANKS:
        await ctx.send("❄ Paliers : " + ", ".join(STAFF_RANKS))
        return
    db = connect()
    try:
        for r in roles:
            db.execute(
                "INSERT OR REPLACE INTO rank_roles (guild_id, rank, role_id) VALUES (?,?,?)",
                (g.id, rank, r.id))
        db.commit()
        await ctx.send(f"🛡️ Palier **{rank}** → {', '.join(r.mention for r in roles)}")
    finally:
        db.close()

@bot.command(name="rankup", help="Promotion forcée d'un membre (admins).")
async def rankup(ctx, member: discord.Member, rank: str = None):
    g = ctx.guild
    if not admin_check(ctx):
        await ctx.send(q("no_perm"))
        return
    if rank not in STAFF_RANKS:
        await ctx.send("❄ Paliers : " + ", ".join(STAFF_RANKS))
        return
    db = connect()
    try:
        u = get_user(db, g.id, member.id)
        before = u["staff_rank"] or "—"
        update_user(db, g.id, member.id, staff_rank=rank)
        log_event(db, g.id, ctx.author.id, "rankup",
                  f"{member.id} : {before} → {rank} (forcé)")
        roles = db.execute(
            "SELECT role_id FROM rank_roles WHERE guild_id=? AND rank=?",
            (g.id, rank)).fetchall()
        if len(roles) == 1:
            role = g.get_role(roles[0]["role_id"])
            if role:
                try:
                    await member.add_roles(role, reason="rankup")
                except discord.HTTPException:
                    pass
        elif len(roles) > 1:
            await ctx.send(f"🛡️ Rang **{rank}** attribué. Plusieurs rôles possibles — "
                           f"le membre choisira via le profil.")
            return
        await ctx.send(f"🛡️ {member.mention} promu(e) : **{before} → {rank}** (promotion forcée, journalisée).")
    finally:
        db.close()

@bot.command(name="quitterstaff", help="Quitter le staff.")
async def quitterstaff(ctx):
    g = ctx.guild
    db = connect()
    try:
        u = get_user(db, g.id, ctx.author.id)
        if not u["staff_rank"]:
            await ctx.send("❄ Tu n'es pas dans le staff.")
            return
        before = u["staff_rank"]
        update_user(db, g.id, ctx.author.id, staff_rank=None)
        log_event(db, g.id, ctx.author.id, "quit_staff", before)
        await ctx.send(f"🛡️ Tu quittes le staff (ancien rang : {before}). La glace t'en remerciera.")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  D. TICKETS — panneau, claim, notes, évaluation
# ══════════════════════════════════════════════════════════════════════
def _inter_is_staff(inter: discord.Interaction) -> bool:
    """Staff = propriétaire du bot/serveur, administrateur, gestion des messages, ou rôle staff configuré."""
    m = inter.user
    if m.id == OWNER_ID or (inter.guild and inter.guild.owner_id == m.id):
        return True
    perms = getattr(m, "guild_permissions", None)
    if perms and (perms.administrator or perms.manage_messages or perms.moderate_members):
        return True
    db = connect()
    try:
        for key in ("mod_role_id", "admin_role_id", "ticket_ping_role_id"):
            rid = config_get(db, inter.guild.id, key)
            if rid and any(r.id == int(rid) for r in getattr(m, "roles", [])):
                return True
    finally:
        db.close()
    return False

class TicketCreateView(discord.ui.View):
    def __init__(self, guild_id=None):
        super().__init__(timeout=None)   # persistante (enregistrée au démarrage)

    @discord.ui.button(label="📩 Ouvrir un ticket", style=discord.ButtonStyle.primary,
                       custom_id="emilia_ticket_open")
    async def open_ticket(self, inter: discord.Interaction, button: discord.ui.Button):
        guild = inter.guild
        if not guild:
            return
        db = connect()
        try:
            already = db.execute(
                "SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? AND status IN ('open','claimed')",
                (guild.id, inter.user.id)).fetchone()
            if already and guild.get_channel(already["channel_id"]):
                await inter.response.send_message(
                    f"❄ Tu as déjà un ticket ouvert : <#{already['channel_id']}>", ephemeral=True)
                return
            cat = config_get(db, guild.id, "ticket_category_id")
            ping_role = config_get(db, guild.id, "ticket_ping_role_id")
            category = None
            if cat:
                c = guild.get_channel(int(cat))
                category = c if isinstance(c, discord.CategoryChannel) else None
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                inter.user: discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                        read_message_history=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                      manage_channels=True),
            }
            role = None
            if ping_role:
                try:
                    role = guild.get_role(int(ping_role))
                except ValueError:
                    role = None
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                               read_message_history=True)
            safe = re.sub(r"[^a-z0-9-]", "", inter.user.display_name.lower().replace(" ", "-")) or "membre"
            channel = await guild.create_text_channel(
                name=f"ticket-{safe}"[:90], category=category, overwrites=overwrites,
                reason=f"ticket de {inter.user}")
            db.execute(
                "INSERT INTO tickets (guild_id, channel_id, user_id, status, created_at) "
                "VALUES (?,?,?,'open',?)", (guild.id, channel.id, inter.user.id, now()))
            db.commit()
            desc = f"Ticket de {inter.user.mention}\n\n"
            if role:
                desc += f"📣 {role.mention} est prévenu(e).\n"
            desc += "\nLe staff claim via le bouton ci-dessous."
            await channel.send(
                content=inter.user.mention + (f" {role.mention}" if role else ""),
                embed=discord.Embed(description=desc, color=ICE),
                view=TicketClaimView(),
                allowed_mentions=discord.AllowedMentions(users=True, roles=[role] if role else False))
            await inter.response.send_message(f"📩 Ticket créé : {channel.mention}", ephemeral=True)
        finally:
            db.close()

class TicketClaimView(discord.ui.View):
    def __init__(self, guild_id=None, channel_id=None):
        super().__init__(timeout=None)

    @discord.ui.button(label="🙋 Claim", style=discord.ButtonStyle.success,
                       custom_id="emilia_ticket_claim")
    async def claim(self, inter: discord.Interaction, button: discord.ui.Button):
        if not _inter_is_staff(inter):
            await inter.response.send_message("❄ Seul le staff peut claim un ticket.", ephemeral=True)
            return
        db = connect()
        try:
            row = db.execute(
                "SELECT * FROM tickets WHERE guild_id=? AND channel_id=? AND status='open'",
                (inter.guild.id, inter.channel.id)).fetchone()
            if not row:
                await inter.response.send_message("❄ Ticket déjà claimé ou fermé.", ephemeral=True)
                return
            db.execute("UPDATE tickets SET staff_id=?, status='claimed' WHERE id=?",
                       (inter.user.id, row["id"]))
            db.commit()
            await inter.response.send_message(f"✅ Ticket claimé par {inter.user.mention}.")
        finally:
            db.close()

    @discord.ui.button(label="✖ Fermer", style=discord.ButtonStyle.danger,
                       custom_id="emilia_ticket_close")
    async def close(self, inter: discord.Interaction, button: discord.ui.Button):
        db = connect()
        try:
            row = db.execute(
                "SELECT * FROM tickets WHERE guild_id=? AND channel_id=? AND status IN ('open','claimed')",
                (inter.guild.id, inter.channel.id)).fetchone()
            if not row:
                await inter.response.send_message("❄ Ticket introuvable ou déjà fermé.", ephemeral=True)
                return
            if inter.user.id != row["user_id"] and not _inter_is_staff(inter):
                await inter.response.send_message("❄ Seul le créateur ou le staff peut fermer.", ephemeral=True)
                return
            db.execute("UPDATE tickets SET status='closed', closed_at=? WHERE id=?", (now(), row["id"]))
            db.commit()
            await inter.response.send_message("🔒 Ticket fermé. Suppression du salon dans 5 secondes.")
            opener = inter.guild.get_member(row["user_id"])
            if opener:   # DM de notation par étoiles (boutons persistants gérés par RateButton)
                try:
                    v = discord.ui.View(timeout=None)
                    for n in range(1, 6):
                        v.add_item(RateButton(row["id"], n))
                    await opener.send("❄ Merci pour ton passage. Note la qualité du staff :", view=v)
                except discord.HTTPException:
                    pass
            await asyncio.sleep(5)
            try:
                await inter.channel.delete(reason="ticket fermé")
            except discord.HTTPException:
                pass
        finally:
            db.close()

class RateButton(discord.ui.DynamicItem[discord.ui.Button], template=r"emilia_rate:(?P<tid>[0-9]+):(?P<n>[1-5])"):
    """Étoiles de notation d'un ticket (persistantes après redémarrage)."""
    def __init__(self, ticket_id: int, stars: int):
        super().__init__(discord.ui.Button(label="⭐" * stars, style=discord.ButtonStyle.secondary,
                                           custom_id=f"emilia_rate:{ticket_id}:{stars}"))
        self.ticket_id, self.stars = ticket_id, stars

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["tid"]), int(match["n"]))

    async def callback(self, inter: discord.Interaction):
        db = connect()
        try:
            t = db.execute("SELECT * FROM tickets WHERE id=?", (self.ticket_id,)).fetchone()
            if not t or t["user_id"] != inter.user.id:
                await inter.response.send_message("❄ Ce ticket n'est pas le tien.", ephemeral=True)
                return
            if t["rating"]:
                await inter.response.send_message("❄ Tu as déjà noté ce ticket.", ephemeral=True)
                return
            db.execute("UPDATE tickets SET rating=? WHERE id=?", (self.stars, t["id"]))
            msg = f"⭐ Merci ! Note enregistrée : **{self.stars}/5**."
            if t["staff_id"]:
                u = get_user(db, t["guild_id"], t["staff_id"])
                if self.stars >= 4:
                    update_user(db, t["guild_id"], t["staff_id"], xp=u["xp"] + 20 * (self.stars - 3))
                elif self.stars <= 2:   # mauvaise note : baisse d'XP + revue d'un superviseur
                    update_user(db, t["guild_id"], t["staff_id"], xp=max(0, u["xp"] - 30))
                    log_event(db, t["guild_id"], t["staff_id"], "ticket_review",
                              f"ticket #{t['id']} noté {self.stars}/5 — revue superviseur requise")
                    cfg = config_get(db, t["guild_id"], "log_channel_id")
                    guild = inter.client.get_guild(t["guild_id"])
                    ch = guild.get_channel(int(cfg)) if (guild and cfg) else None
                    if ch:
                        await ch.send(f"⚠️ Ticket **#{t['id']}** noté **{self.stars}/5** pour <@{t['staff_id']}> "
                                      "— revue par un superviseur requise.",
                                      allowed_mentions=discord.AllowedMentions.none())
            db.commit()
            await inter.response.edit_message(content=msg, view=None)
        finally:
            db.close()

@bot.command(name="ticketpanel", help="Installer le panneau de tickets (admins).")
async def ticketpanel(ctx):
    g = ctx.guild
    if not admin_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        config_set(db, g.id, "ticket_panel_channel", ctx.channel.id)
        e = frost_embed(title="📩 Tickets",
                        desc="Besoin d'aide ? Ouvre un ticket, le staff te répond.\n"
                             "« La patience est une vertu. La nôtre est limitée. »",
                        color=ICE)
        await ctx.send(embed=e, view=TicketCreateView())
        await ctx.send("❄ Panneau installé. Pour le ping à l'ouverture : `+ticketping <rôle>`")
    finally:
        db.close()

@bot.command(name="ticketping", help="Rôle pingé à l'ouverture d'un ticket (admins).")
async def ticketping(ctx, role: discord.Role):
    g = ctx.guild
    if not admin_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        config_set(db, g.id, "ticket_ping_role_id", role.id)
        await ctx.send(f"📣 Rôle de ping ticket : {role.mention}")
    finally:
        db.close()

@bot.command(name="ticketnote", help="Note privée staff dans le ticket (staff).")
async def ticketnote(ctx, *, note: str):
    g = ctx.guild
    if not mod_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        row = db.execute(
            "SELECT * FROM tickets WHERE guild_id=? AND channel_id=?",
            (g.id, ctx.channel.id)).fetchone()
        if not row:
            await ctx.send("❄ Ce canal n'est pas un ticket.")
            return
        db.execute(
            "INSERT INTO ticket_notes (guild_id, ticket_id, staff_id, note, created_at) "
            "VALUES (?,?,?,?,?)", (g.id, row["id"], ctx.author.id, note, now()))
        db.commit()
        await ctx.send("📝 Note privée enregistrée (visible staff uniquement).",
                       )
    finally:
        db.close()

@bot.command(name="ticketnotes", help="Voir les notes privées du ticket (staff).")
async def ticketnotes(ctx):
    g = ctx.guild
    if not mod_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        row = db.execute(
            "SELECT * FROM tickets WHERE guild_id=? AND channel_id=?",
            (g.id, ctx.channel.id)).fetchone()
        if not row:
            await ctx.send("❄ Ce canal n'est pas un ticket.")
            return
        rows = db.execute(
            "SELECT staff_id, note, created_at FROM ticket_notes WHERE ticket_id=? "
            "ORDER BY created_at", (row["id"],)).fetchall()
        if not rows:
            await ctx.send("❄ Aucune note privée.")
            return
        lines = [f"• <@{n['staff_id']}> : {n['note']} ({fmt_ts(n['created_at'])})"
                 for n in rows]
        await ctx.send(embed=frost_embed(title="📝 Notes privées",
                                         desc="\n".join(lines), color=FROST))
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  E. GIVEAWAYS — bouton, multi-gagnants, reroll, réclamation 5 min
# ══════════════════════════════════════════════════════════════════════
class GiveawayJoinView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=None)   # persistante : le message est lu depuis l'interaction

    @discord.ui.button(label="🎟️ Participer", style=discord.ButtonStyle.success,
                       custom_id="emilia_giveaway_join")
    async def join(self, inter: discord.Interaction, button: discord.ui.Button):
        db = connect()
        try:
            gw = db.execute(
                "SELECT status, ends_at FROM giveaways WHERE guild_id=? AND message_id=?",
                (inter.guild.id, inter.message.id)).fetchone()
            if not gw or gw["status"] != "active" or gw["ends_at"] <= now():
                await inter.response.send_message("❄ Ce giveaway est terminé.", ephemeral=True)
                return
            cur = db.execute(
                "INSERT OR IGNORE INTO giveaway_entries (guild_id, giveaway_msg, user_id) VALUES (?,?,?)",
                (inter.guild.id, inter.message.id, inter.user.id))
            db.commit()
            count = db.execute(
                "SELECT COUNT(*) FROM giveaway_entries WHERE guild_id=? AND giveaway_msg=?",
                (inter.guild.id, inter.message.id)).fetchone()[0]
            txt = "🎟️ Participation enregistrée." if cur.rowcount else "❄ Tu participes déjà."
            await inter.response.send_message(f"{txt} **{count}** participant(s). Gratuit, sans condition d'achat.",
                                              ephemeral=True)
        finally:
            db.close()

@bot.command(name="giveaway", help="Lancer un giveaway (staff). <délai min> <gagnants> <prix>")
async def giveaway(ctx, minutes: int, winners: int, *, prize: str):
    g = ctx.guild
    if not mod_check(ctx):
        await ctx.send(q("no_perm"))
        return
    if not (1 <= minutes <= 60 * 24 * 30) or not (1 <= winners <= 50):
        await ctx.send("❄ Durée (1 min à 30 jours) ou nombre de gagnants (1 à 50) invalide."); return
    db = connect()
    try:
        ends = now() + minutes * 60
        e = frost_embed(
            title=f"🎉 Giveaway — {prize}",
            desc=f"Participe avec le bouton. **{winners}** gagnant(s).\n"
                 f"Fin : {fmt_ts(ends)} — réclamation sous 5 min.",
            color=GOLD)
        msg = await ctx.send(embed=e, view=GiveawayJoinView())
        db.execute(
            "INSERT INTO giveaways (guild_id, channel_id, prize, winners, ends_at, message_id) "
            "VALUES (?,?,?,?,?,?)", (g.id, ctx.channel.id, prize, winners, ends, msg.id))
        db.commit()
        await ctx.send("❄ Giveaway lancé. La chance n'est pas un droit.")
    finally:
        db.close()

@tasks.loop(seconds=30)
async def giveaway_loop():
    db = connect()
    try:
        rows = db.execute(
            "SELECT * FROM giveaways WHERE status='active' AND ends_at<=?",
            (now(),)).fetchall()
        for gw in rows:
            entries = db.execute(
                "SELECT user_id FROM giveaway_entries WHERE guild_id=? AND giveaway_msg=?",
                (gw["guild_id"], gw["message_id"])).fetchall()
            guild = bot.get_guild(gw["guild_id"])
            if not guild or not entries:
                db.execute("UPDATE giveaways SET status='ended' WHERE guild_id=? AND message_id=?",
                           (gw["guild_id"], gw["message_id"]))
                db.commit()
                continue
            winners = random.sample([e["user_id"] for e in entries],
                                    min(gw["winners"], len(entries)))
            db.execute("UPDATE giveaways SET status='ended' WHERE guild_id=? AND message_id=?",
                       (gw["guild_id"], gw["message_id"]))
            db.commit()
            db.execute("""CREATE TABLE IF NOT EXISTS giveaway_winners (
                guild_id INTEGER NOT NULL, message_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                prize TEXT, claim_until INTEGER NOT NULL, claimed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, message_id, user_id))""")
            for w in winners:
                db.execute("INSERT OR IGNORE INTO giveaway_winners (guild_id, message_id, user_id, prize, claim_until) "
                           "VALUES (?,?,?,?,?)", (gw["guild_id"], gw["message_id"], w, gw["prize"], now() + 300))
            db.commit()
            ch = guild.get_channel(gw["channel_id"])
            if ch:
                mentions = " ".join(f"<@{w}>" for w in winners)
                await ch.send(f"🏆 **Gagnant(s) de « {gw['prize']} »** : {mentions}\n"
                              f"⏳ Réclame sous **5 min** avec `!claimgw`")
    except Exception as ex:
        print("giveaway_loop:", ex)
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  F. JEUX — pile ou face, dés, roulette, blackjack
# ══════════════════════════════════════════════════════════════════════
def _bet_check(db, guild_id, user_id, bet):
    u = get_user(db, guild_id, user_id)
    if bet <= 0:
        return None, "❄ Mise invalide."
    if bet > u["wallet"]:
        return None, f"❄ Tu paries plus que ton solde (**{fmt(u['wallet'])}**)."
    return u, None

@bot.command(name="pileouface", help="Pile ou face. <face> <mise>")
async def pileouface(ctx, face: str, bet: int):
    g = ctx.guild
    db = connect()
    try:
        u, err = _bet_check(db, g.id, ctx.author.id, bet)
        if err:
            await ctx.send(err)
            return
        face = face.lower()
        if face not in ("pile", "face"):
            await ctx.send("❄ « pile » ou « face ». La glace n'aime pas l'ambiguïté.")
            return
        update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - bet)
        result = random.choice(["pile", "face"])
        won = result == face
        if won:
            reward = int(bet * 2 * multiplier(db, g.id))
            update_user(db, g.id, ctx.author.id,
                        wallet=get_user(db, g.id, ctx.author.id)["wallet"] + reward)
            add_tx(db, g.id, ctx.author.id, "gamble_win", reward - bet)
            await ctx.send(f"{q('win')}\n🪙 **{result.capitalize()}** — tu gagnes "
                           f"{COIN} **{fmt(reward)}**.")
        else:
            add_tx(db, g.id, ctx.author.id, "gamble_lose", -bet)
            await ctx.send(f"{q('lose')}\n🪙 **{result.capitalize()}** — tu perds "
                           f"{COIN} **{fmt(bet)}**.")
    finally:
        db.close()

@bot.command(name="des", help="Lancer deux dés (pure ambiance).")
async def des(ctx):
    a, b = random.randint(1, 6), random.randint(1, 6)
    await ctx.send(f"🎲 **{a}** et **{b}** — total **{a + b}**.\n{q('greet')}")

@bot.command(name="roulette", help="Roulette. <number 0-36> <mise>")
async def roulette(ctx, number: int, bet: int):
    g = ctx.guild
    db = connect()
    try:
        u, err = _bet_check(db, g.id, ctx.author.id, bet)
        if err:
            await ctx.send(err)
            return
        if not (0 <= number <= 36):
            await ctx.send("❄ Entre 0 et 36. Pas plus.")
            return
        update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - bet)
        result = random.randint(0, 36)
        if result == number:
            reward = int(bet * 35 * multiplier(db, g.id))
            update_user(db, g.id, ctx.author.id,
                        wallet=get_user(db, g.id, ctx.author.id)["wallet"] + reward)
            add_tx(db, g.id, ctx.author.id, "gamble_win", reward - bet)
            await ctx.send(f"{q('win')}\n🎡 **{result}** — jackpot, {COIN} **{fmt(reward)}**.")
        else:
            add_tx(db, g.id, ctx.author.id, "gamble_lose", -bet)
            await ctx.send(f"{q('lose')}\n🎡 **{result}** — la roue a tranché. "
                           f"-{COIN} {fmt(bet)}.")
    finally:
        db.close()

@bot.command(name="blackjack", help="Blackjack. <mise>")
async def blackjack(ctx, bet: int):
    g = ctx.guild
    db = connect()
    try:
        u, err = _bet_check(db, g.id, ctx.author.id, bet)
        if err:
            await ctx.send(err)
            return
        deck = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2] * 4 + [1] * 4
        random.shuffle(deck)
        hand, dealer = [deck.pop(), deck.pop()], [deck.pop(), deck.pop()]

        def val(h):
            s = sum(h)
            while s > 21 and 11 in h:
                s -= 10
            return s

        update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - bet)
        outcome = None
        if val(hand) == 21:
            outcome = "blackjack"
        elif val(dealer) == 21:
            outcome = "lose"
        else:
            while val(dealer) < 17:
                dealer.append(deck.pop())
            if val(dealer) > 21 or val(hand) > val(dealer):
                outcome = "win"
            elif val(hand) > 21:
                outcome = "lose"
            else:
                outcome = "push"
        if outcome == "blackjack":
            reward = int(bet * 2.5 * multiplier(db, g.id))
            update_user(db, g.id, ctx.author.id,
                        wallet=get_user(db, g.id, ctx.author.id)["wallet"] + reward)
            add_tx(db, g.id, ctx.author.id, "gamble_win", reward - bet)
            await ctx.send(f"🃏 Blackjack ! {q('win')}\nGain : {COIN} **{fmt(reward)}**")
        elif outcome == "win":
            reward = int(bet * 2 * multiplier(db, g.id))
            update_user(db, g.id, ctx.author.id,
                        wallet=get_user(db, g.id, ctx.author.id)["wallet"] + reward)
            add_tx(db, g.id, ctx.author.id, "gamble_win", reward - bet)
            await ctx.send(f"🃏 C'est gagné. {q('win')}\nGain : {COIN} **{fmt(reward)}**")
        elif outcome == "push":
            update_user(db, g.id, ctx.author.id,
                        wallet=get_user(db, g.id, ctx.author.id)["wallet"] + bet)
            await ctx.send(f"🃏 Égalité ({val(hand)} contre {val(dealer)}). Ta mise est rendue.")
        else:
            add_tx(db, g.id, ctx.author.id, "gamble_lose", -bet)
            await ctx.send(f"🃏 Le croupier l'emporte ({val(dealer)} contre {val(hand)}). "
                           f"{q('lose')}\n-{COIN} {fmt(bet)}")
    finally:
        db.close()

@bot.command(name="courses", help="Course de véhicules entre membres. <mise>")
async def courses(ctx, bet: int, *rivals: discord.Member):
    g = ctx.guild
    db = connect()
    try:
        u, err = _bet_check(db, g.id, ctx.author.id, bet)
        if err:
            await ctx.send(err)
            return
        my_veh = db.execute(
            "SELECT name, speed FROM vehicles WHERE guild_id=? AND user_id=? "
            "ORDER BY speed DESC LIMIT 1", (g.id, ctx.author.id)).fetchone()
        my_speed = my_veh["speed"] if my_veh else 50
        update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - bet)
        rival_speeds = []
        for r in rivals[:3]:
            rv = db.execute(
                "SELECT name, speed FROM vehicles WHERE guild_id=? AND user_id=? "
                "ORDER BY speed DESC LIMIT 1", (g.id, r.id)).fetchone()
            rival_speeds.append((r.display_name, rv["speed"] if rv else 50))
        total = my_speed + sum(s for _, s in rival_speeds) or 1
        chance = my_speed / total
        if random.random() < chance:
            reward = int(bet * (1 + 0.5 * len(rival_speeds)) * multiplier(db, g.id))
            update_user(db, g.id, ctx.author.id,
                        wallet=get_user(db, g.id, ctx.author.id)["wallet"] + reward)
            add_tx(db, g.id, ctx.author.id, "race_win", reward - bet)
            await ctx.send(f"🏁 Victoire ! {q('win')}\nGain : {COIN} **{fmt(reward)}**")
        else:
            add_tx(db, g.id, ctx.author.id, "race_lose", -bet)
            await ctx.send(f"🏁 Défaite. {q('lose')}\n-{COIN} {fmt(bet)}")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  F. RAIDS BOSS (30 min, PV, participants, attaques)
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="raid", help="Lancer un raid boss (staff). <nom> <PV>")
async def raid(ctx, name: str, hp: int):
    g = ctx.guild
    if not mod_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        db.execute(
            "INSERT INTO boss (guild_id, hp, max_hp, state, spawned_at, next_spawn) "
            "VALUES (?,?,?,'active',?,?)",
            (g.id, hp, hp, now(), now() + 1800))
        db.commit()
        e = frost_embed(
            title=f"⚔️ Raid — {name}",
            desc=f"Le boss **{name}** apparaît avec **{fmt(hp)}** PV.\n"
                 f"Durée : 30 min. Attaque : `!attack`.\n"
                 f"{q('boss')}",
            color=EXCL)
        await ctx.send(embed=e)
    finally:
        db.close()

@bot.command(name="attack", help="Attaquer le boss en cours.")
@commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
async def attack(ctx):
    g = ctx.guild
    db = connect()
    try:
        b = db.execute("SELECT * FROM boss WHERE guild_id=? AND state='active'",
                       (g.id,)).fetchone()
        if not b:
            await ctx.send("❄ Aucun boss en cours. Le calme a ses limites.")
            return
        if now() > b["next_spawn"]:
            db.execute("UPDATE boss SET state='idle', hp=0 WHERE guild_id=?", (g.id,))
            db.commit()
            await ctx.send("❄ Le boss a fui. Le raid est terminé.")
            return
        dmg = int(random.uniform(50, 150) * multiplier(db, g.id))
        new_hp = max(0, b["hp"] - dmg)
        db.execute("UPDATE boss SET hp=? WHERE guild_id=?", (new_hp, g.id))
        db.execute(
            "INSERT INTO boss_contrib (guild_id, user_id, dmg) VALUES (?,?,?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET dmg=dmg+excluded.dmg",
            (g.id, ctx.author.id, dmg))
        db.commit()
        if new_hp == 0:
            # Récompenses en DM
            contribs = db.execute(
                "SELECT user_id, dmg FROM boss_contrib WHERE guild_id=? "
                "ORDER BY dmg DESC", (g.id,)).fetchall()
            total = sum(c["dmg"] for c in contribs) or 1
            for c in contribs:
                share = int(500 * c["dmg"] / total)
                u = get_user(db, g.id, c["user_id"])
                update_user(db, g.id, c["user_id"], wallet=u["wallet"] + share)
                add_tx(db, g.id, c["user_id"], "raid_reward", share)
                try:
                    m = g.get_member(c["user_id"])
                    if m:
                        await m.send(f"⚔️ Raid terminé. Ta part : {COIN} **{fmt(share)}** "
                                     f"({c['dmg']} dégâts).")
                except discord.HTTPException:
                    pass
            db.execute("DELETE FROM boss_contrib WHERE guild_id=?", (g.id,))
            db.execute("UPDATE boss SET state='idle', hp=0, next_spawn=0 WHERE guild_id=?",
                       (g.id,))
            db.commit()
            await ctx.send("💀 **Boss vaincu !** Récompenses envoyées en DM.")
        else:
            await ctx.send(f"⚔️ **{dmg}** dégâts infligés. PV restants : "
                           f"**{fmt(new_hp)}** / {fmt(b['max_hp'])}")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  S. KILL & BLOCK — approche 2-3 min, annonce, résolution, vol
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="kill", help="Tenter un Kill & Block sur un membre.")
@commands.cooldown(rate=1, per=7200, type=commands.BucketType.user)
async def kill(ctx, member: discord.Member = None):
    g = ctx.guild
    db = connect()
    try:
        if member is None or member == ctx.author or (member.bot if member else False):
            await ctx.send("❄ Cible : un membre (pas toi, pas un bot).")
            return
        # Vérifie qu'une tentative n'est pas déjà en cours sur ce serveur par l'attaquant
        pending = db.execute(
            "SELECT id FROM sanctions WHERE guild_id=? AND kind='kill_pending' AND by_id=?",
            (g.id, ctx.author.id)).fetchone()
        if pending:
            await ctx.send("❄ Une tentative est déjà en cours. Attends sa résolution.")
            return
        approach = int(random.uniform(120, 180))
        ready = now() + approach
        db.execute(
            "INSERT INTO sanctions (guild_id, user_id, kind, reason, by_id, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (g.id, member.id, "kill_pending",
             json.dumps({"target": member.id, "attacker": ctx.author.id,
                         "ready_at": ready, "channel_id": ctx.channel.id}),
             ctx.author.id, now()))
        db.commit()
        try:
            await member.send("❄ Quelqu'un te suit. Garde tes affaires proches de toi. "
                              f"Tu peux taper `!block` ici ou dans le serveur dans les ~{approach//60} prochaines minutes.")
        except discord.HTTPException:
            pass
        await ctx.send(f"🗡️ Approche lancée vers {member.mention} (~{approach // 60} min). "
                       f"Résolution automatique.")
    finally:
        db.close()

    # Résolution automatique après le délai (2-3 min)
    await asyncio.sleep(approach)
    db = connect()
    try:
        row = db.execute(
            "SELECT * FROM sanctions WHERE guild_id=? AND kind='kill_pending' AND by_id=? AND user_id=?",
            (g.id, ctx.author.id, member.id)).fetchone()
        if not row:
            return  # bloquée ou déjà résolue
        db.execute("DELETE FROM sanctions WHERE id=?", (row["id"],))
        db.commit()
        # Prison (10 % par défaut)
        prison_chance = float(config_get(db, g.id, "kill_prison_rate", "0.1"))
        if random.random() < prison_chance:
            db.execute(
                "INSERT INTO prison (guild_id, user_id, reason, by_id, started_at, released_at) "
                "VALUES (?,?, 'tentative ratée', ?, ?, ?)",
                (g.id, ctx.author.id, ctx.author.id, now(), now() + 1800))
            db.commit()
            ch = g.get_channel(ctx.channel.id)
            if ch:
                await ch.send(f"⛓️ {ctx.author.mention} a raté sa tentative et finit en prison (30 min).")
            return
        success = random.random() < float(config_get(db, g.id, "kill_success_rate", "0.4"))
        ch = g.get_channel(ctx.channel.id)
        if success:
            target = get_user(db, g.id, member.id)
            cap = int(config_get(db, g.id, "kill_steal_cap", "2000"))
            steal = min(int(target["wallet"] * 0.1), cap) if target["wallet"] > 0 else 0
            ins_msg = ""
            if steal > 0:
                update_user(db, g.id, member.id, wallet=max(0, target["wallet"] - steal))
                update_user(db, g.id, ctx.author.id,
                            wallet=get_user(db, g.id, ctx.author.id)["wallet"] + steal)
                add_tx(db, g.id, member.id, "kill_stolen", -steal)
                add_tx(db, g.id, ctx.author.id, "kill_gain", steal)
                payout = claim_insurance(db, g.id, member.id, steal, "kill & block")
                ins_msg = f"\n🛡️ Assurance : {COIN} **{fmt(payout)}** remboursés." if payout else ""
                try:
                    await member.send(f"❄ {ctx.author.display_name} t'a volé "
                                      f"{COIN} **{fmt(steal)}**.{ins_msg}")
                except discord.HTTPException:
                    pass
            if ch:
                await ch.send(f"🗡️ {ctx.author.mention} a réussi ! {member.mention} a été dévalisé(e)."
                              f"{ins_msg if steal else ''}")
        else:
            if ch:
                await ch.send(f"🗡️ {ctx.author.mention} a échoué contre {member.mention}. "
                              f"{q('lose')}")
    finally:
        db.close()

@bot.command(name="block", help="Te protéger contre une tentative de kill en cours.")
async def block(ctx):
    g = ctx.guild
    db = connect()
    try:
        pending = db.execute(
            "SELECT * FROM sanctions WHERE guild_id=? AND user_id=? AND kind='kill_pending'",
            (g.id, ctx.author.id)).fetchone()
        if not pending:
            await ctx.send("❄ Aucune tentative en cours contre toi. Respire.")
            return
        detail = json.loads(pending["reason"] or "{}")
        if now() >= detail.get("ready_at", 0):
            await ctx.send("❄ Trop tard. L'annonce est déjà faite.")
            return
        db.execute("DELETE FROM sanctions WHERE id=?", (pending["id"],))
        db.commit()
        await ctx.send("🛡️ Tu te protèges. La tentative est annulée.")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  T. BUMP — 1 bump/serveur/3 h, classement
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="bump", help="Classement des bumps du cycle en cours.")
async def bump(ctx):
    g = ctx.guild
    db = connect()
    try:
        cycle = now() // 10800
        rows = db.execute(
            "SELECT b.guild_id, b.bumped, b.best_user, b.best_count "
            "FROM bumps b WHERE b.cycle=? ORDER BY b.bumped DESC", (cycle,)).fetchall()
        if not rows:
            await ctx.send("❄ Aucun bump ce cycle. Le silence est assourdissant.")
            return
        lines = []
        for i, r in enumerate(rows, 1):
            pts = 1 if i == 1 else 0.5
            guild = bot.get_guild(r["guild_id"])
            name = guild.name if guild else f"#{r['guild_id']}"
            best = f" — meilleur : <@{r['best_user']}> ({r['best_count']})" if r["best_user"] else ""
            lines.append(f"{'🥇' if i == 1 else f'**{i}.**'} {name} — {pts} pt{best}")
        e = frost_embed(title="📈 Classement des bumps",
                        desc="\n".join(lines) + "\n\n⏳ Cycle : 3 h", color=ICE)
        await ctx.send(embed=e)
    finally:
        db.close()

@bot.event
async def on_message_edit(before, after):
    """Détection du message de confirmation DISBOARD + auto-suivi des mods."""
    if before.guild is None or after.guild is None:
        return
    # Auto-suivi : relaye la version modifiée (si activé)
    await autosuivi_relay_edit(before, after)
    await _handle_disboard(after)

DISBOARD_ID = 302050872383242240

async def _handle_disboard(message):
    """Compte un bump uniquement si le message vient du vrai DISBOARD (jamais d'un membre)."""
    if message.guild is None or message.author.id != DISBOARD_ID:
        return
    blob = (message.content or "") + " ".join((e.description or "") for e in message.embeds)
    low = blob.lower()
    if "bump" not in low or not any(k in low for k in ("done", "effectu", "fait", "réussi", "reussi", "bumped")):
        return
    after = message
    invoker = None
    meta = getattr(message, "interaction_metadata", None) or getattr(message, "interaction", None)
    if meta is not None:
        invoker = getattr(meta, "user", None)
    db = connect()
    try:
        cycle = now() // 10800
        row = db.execute(
            "SELECT * FROM bumps WHERE guild_id=? AND cycle=?",
            (after.guild.id, cycle)).fetchone()
        if row and row["bumped"]:
            return
        db.execute(
            "INSERT INTO bumps (guild_id, cycle, bumped, best_user, best_count) "
            "VALUES (?,?,1,?,1) "
            "ON CONFLICT(guild_id, cycle) DO UPDATE SET bumped=1, "
            "best_user=COALESCE(excluded.best_user, bumps.best_user), "
            "best_count=MAX(bumps.best_count, excluded.best_count)",
            (after.guild.id, cycle, invoker.id if invoker else None))
        db.commit()
        log_event(db, after.guild.id, invoker.id if invoker else None, "bump", f"cycle {cycle}")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  U. INVITE TRACKER
# ══════════════════════════════════════════════════════════════════════
@bot.event
async def on_member_add(member):
    try:
        invites = await member.guild.invites()
    except discord.HTTPException:
        return
    total = sum(i.uses for i in invites)
    db = connect()
    try:
        prev = db.execute(
            "SELECT total FROM invites WHERE guild_id=? AND user_id=0",
            (member.guild.id,)).fetchone()
        prev_total = prev["total"] if prev else 0
        delta = total - prev_total
        db.execute(
            "INSERT INTO invites (guild_id, user_id, total) VALUES (?,?,?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET total=excluded.total",
            (member.guild.id, 0, total))
        if delta > 0:
            # Attribuer à l'inviteur si possible (via membre)
            for inv in invites:
                if inv.inviter and inv.uses > 0:
                    db.execute(
                        "INSERT INTO invites (guild_id, user_id, total) VALUES (?,?,?) "
                        "ON CONFLICT(guild_id, user_id) DO UPDATE SET total=total+?",
                        (member.guild.id, inv.inviter.id, 0, 1))
                    log_event(db, member.guild.id, inv.inviter.id, "invite", member.id)
                    break
        db.commit()
    finally:
        db.close()

@bot.command(name="invites", help="Tes invitations valides.")
async def invites(ctx):
    g = ctx.guild
    db = connect()
    try:
        r = db.execute(
            "SELECT total FROM invites WHERE guild_id=? AND user_id=?",
            (g.id, ctx.author.id)).fetchone()
        await ctx.send(f"💌 Invitations valides : **{r['total'] if r else 0}**")
    finally:
        db.close()

@bot.command(name="topinvites", help="Top 10 des inviteurs.")
async def topinvites(ctx):
    g = ctx.guild
    db = connect()
    try:
        rows = db.execute(
            "SELECT user_id, total FROM invites WHERE guild_id=? AND user_id!=0 "
            "ORDER BY total DESC LIMIT 10", (g.id,)).fetchall()
        if not rows:
            await ctx.send("❄ Personne n'a encore invité. Le vide est vaste.")
            return
        medals = ["🥇", "🥈", "🥉"]
        lines = [f"{medals[i] if i < 3 else f'**{i+1}.**'} <@{r['user_id']}> — "
                 f"💌 **{r['total']}**" for i, r in enumerate(rows)]
        await ctx.send(embed=frost_embed(title="💌 Top invitations",
                                         desc="\n".join(lines), color=ICE))
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  V. AUTOREACTROLE
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="autoreactrole", help="Lier un emoji à un rôle sur ce message (admins).")
async def autoreactrole(ctx, emoji: str, role: discord.Role):
    g = ctx.guild
    if not admin_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        db.execute(
            "INSERT OR REPLACE INTO reaction_roles (guild_id, message_id, emoji, role_id, mode) "
            "VALUES (?,?,?,?,'add')", (g.id, ctx.message.id, emoji, role.id))
        db.commit()
        await ctx.send(f"🔗 {emoji} → {role.mention} sur ce message.")
    finally:
        db.close()

@bot.event
async def on_raw_reaction_add(payload):
    """AutoReactRole + Starboard (5 réactions ⭐ → message relayé)."""
    if payload.message_id is None:
        return
    db = connect()
    try:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        # 1) AutoReactRole : emoji lié → rôle attribué
        row = db.execute(
            "SELECT * FROM reaction_roles WHERE guild_id=? AND message_id=? AND emoji=?",
            (payload.guild_id, payload.message_id, str(payload.emoji))).fetchone()
        if row:
            member = guild.get_member(payload.user_id)
            if member:
                role = guild.get_role(row["role_id"])
                if role:
                    try:
                        await member.add_roles(role, reason="autoreactrole")
                    except discord.HTTPException:
                        pass
        # 2) Starboard : 5 ⭐ → relayé dans le salon starboard
        if str(payload.emoji) == "⭐":
            srow = db.execute("SELECT value FROM config WHERE guild_id=? AND key='starboard'",
                              (payload.guild_id,)).fetchone()
            chrow = db.execute("SELECT value FROM config WHERE guild_id=? AND key='starboard_channel'",
                               (payload.guild_id,)).fetchone()
            if srow and srow["value"] == "on" and chrow:
                if payload.member and getattr(payload.member, "bot", False):
                    return
                ch = guild.get_channel(int(chrow["value"]))
                src = guild.get_channel(payload.channel_id)
                if ch and src and src.id != ch.id:
                    msg = await src.fetch_message(payload.message_id)
                    count = sum(r.count for r in msg.reactions if str(r.emoji) == "⭐")
                    if count >= 5:
                        e = frost_embed(title="⭐ Starboard",
                                        desc=f"> {msg.content[:500] or '*(sans texte)*'}",
                                        footer=f"Par {msg.author} dans #{src.name}")
                        await ch.send(embed=e)
    except Exception:
        pass
    finally:
        db.close()

@bot.event
async def on_raw_reaction_remove(payload):
    db = connect()
    try:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        row = db.execute(
            "SELECT * FROM reaction_roles WHERE guild_id=? AND message_id=? AND emoji=?",
            (payload.guild_id, payload.message_id, str(payload.emoji))).fetchone()
        if not row or row["mode"] != "add":
            return
        member = guild.get_member(payload.user_id)
        if not member:
            return
        role = guild.get_role(row["role_id"])
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="autoreactrole")
            except discord.HTTPException:
                pass
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  Z. WINTERFEST — boss collectif toutes les 15 h
# ══════════════════════════════════════════════════════════════════════
@tasks.loop(hours=15)
async def boss_loop():
    for guild in bot.guilds:
        db = connect()
        try:
            ch_id = config_get(db, guild.id, "event_channel_id")
            if not ch_id:
                continue
            ch = guild.get_channel(int(ch_id))
            if not ch:
                continue
            row = db.execute("SELECT * FROM boss WHERE guild_id=?", (guild.id,)).fetchone()
            hp = 5000
            if row and row["state"] == "active" and row["hp"] > 0:
                hp = min(row["max_hp"], int(row["hp"] * 1.3))  # récupère des PV
            db.execute(
                "INSERT INTO boss (guild_id, hp, max_hp, state, spawned_at, next_spawn) "
                "VALUES (?,?,?,'active',?,?) "
                "ON CONFLICT(guild_id) DO UPDATE SET hp=excluded.hp, max_hp=excluded.max_hp, "
                "state='active', spawned_at=excluded.spawned_at, next_spawn=excluded.next_spawn",
                (guild.id, hp, 5000, now(), now() + 900))
            db.commit()
            await ch.send(embed=frost_embed(
                title="🐲 Le boss d'hiver apparaît !",
                desc=f"**{fmt(hp)}** PV. Tous les froids sont les bienvenus.\n"
                     f"Attaque : `!attack` — 15 min pour le vaincre.\n{q('boss')}",
                color=EXCL))
        except Exception as ex:
            print("boss_loop:", ex)
        finally:
            db.close()

# ══════════════════════════════════════════════════════════════════════
#  R. SUCCÈS & TROPHÉES
# ══════════════════════════════════════════════════════════════════════
ACHIEVEMENTS = {
    "daily_streak": ("🔥 Série de 7 jours", lambda v: v >= 7),
    "level_10": ("⭐ Niveau 10", lambda v: v >= 10),
    "rich_100k": ("💰 100 000 ⚙️", lambda v: v >= 100000),
    "first_family": ("👨‍👩‍👧 Premier foyer", lambda v: v >= 1),
}

def check_achievements(db, guild_id, user_id, code, value):
    spec = ACHIEVEMENTS.get(code)
    if not spec:
        return
    name, cond = spec
    if cond(value):
        cur = db.execute(
            "INSERT OR IGNORE INTO achievements (guild_id, user_id, code, unlocked_at) "
            "VALUES (?,?,?,?)", (guild_id, user_id, code, now()))
        if cur.rowcount:
            db.commit()
            try:
                m = bot.get_user(user_id)
                if m:
                    m.send = m.send  # no-op, évite l'import
            except Exception:
                pass

@bot.command(name="succes", help="Tes succès débloqués.")
async def succes(ctx, member: discord.Member = None):
    g = ctx.guild
    m = member or ctx.author
    db = connect()
    try:
        rows = db.execute(
            "SELECT code, unlocked_at FROM achievements WHERE guild_id=? AND user_id=?",
            (g.id, m.id)).fetchall()
        if not rows:
            await ctx.send("❄ Aucun succès. La glace attend tes prouesses.")
            return
        lines = [f"• {ACHIEVEMENTS.get(r['code'], (r['code'],))[0]} — {fmt_ts(r['unlocked_at'])}"
                 for r in rows]
        await ctx.send(embed=frost_embed(
            title=f"🏅 Succès — {m.display_name}", desc="\n".join(lines), color=GOLD))
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  I. WINNERMUSK — catalogue protégé, commandes persistantes
# ══════════════════════════════════════════════════════════════════════
WINNER_DELIVERY = {"normal": 3600, "luxe": 10800, "exclusif": 43200, "mythique": 86400}

def ensure_winner_catalog(db):
    items = [
        ("Tesla Model S", "voiture", 500000),
        ("Cybertruck", "voiture", 800000),
        ("Bugatti Chiron", "voiture", 2000000),
        ("Vélo polaire", "moto", 50000),
        ("Moto de givre", "moto", 200000),
        ("Maison de glace", "maison", 1000000),
        ("Villa boréale", "maison", 3000000),
    ]
    for name, kind, price in items:
        db.execute(
            "INSERT OR IGNORE INTO winner_catalog (item, kind, price, stock) VALUES (?,?,?,-1)",
            (name, kind, price))
    db.commit()

@bot.command(name="winneradd", help="Ajouter un article au catalogue WINNERMUSK (propriétaire).")
@owner_check()
async def winneradd(ctx, price: int, kind: str, *, item: str):
    if price <= 0:
        await ctx.send("❄ Prix invalide."); return
    db = connect()
    try:
        db.execute(
            "INSERT OR REPLACE INTO winner_catalog (item, kind, price, stock) VALUES (?,?,?,-1)",
            (item, kind, price))
        db.commit()
        await ctx.send(f"👑 Catalogue WINNERMUSK : **{item}** ({kind}) — {fmt(price)}")
    finally:
        db.close()

@bot.command(name="winner", help="Catalogue WINNERMUSK (voitures, motos, maisons).")
async def winner(ctx):
    db = connect()
    try:
        ensure_winner_catalog(db)
        rows = db.execute(
            "SELECT item, kind, price FROM winner_catalog ORDER BY kind, price").fetchall()
        lines = [f"• {r['item']} ({r['kind']}) — {COIN} **{fmt(r['price'])}**" for r in rows]
        e = frost_embed(title="👑 WINNERMUSK",
                        desc="Catalogue exclusif. Livraison : `!winnerbuy <article> <normal|luxe|exclusif|mythique>`\n\n"
                             + "\n".join(lines), color=EXCL)
        await ctx.send(embed=e)
    finally:
        db.close()

@bot.command(name="winnerbuy", help="Commander un article WINNERMUSK. <article> <livraison>")
async def winnerbuy(ctx, delivery: str, *, item: str):
    g = ctx.guild
    db = connect()
    try:
        ensure_winner_catalog(db)
        if delivery not in WINNER_DELIVERY:
            await ctx.send("❄ Livraisons : normal, luxe, exclusif, mythique.")
            return
        row = db.execute("SELECT * FROM winner_catalog WHERE item=?", (item,)).fetchone()
        if not row:
            await ctx.send("❄ Article introuvable au catalogue.")
            return
        u = get_user(db, g.id, ctx.author.id)
        if u["wallet"] < row["price"]:
            await ctx.send(f"❄ Il te faut **{fmt(row['price'])}**.")
            return
        update_user(db, g.id, ctx.author.id, wallet=u["wallet"] - row["price"])
        add_tx(db, g.id, ctx.author.id, "winner_buy", -row["price"])
        deliver_at = now() + WINNER_DELIVERY[delivery]
        db.execute(
            "INSERT INTO winner_orders (guild_id, user_id, item, price, delivery, deliver_at, status, created_at) "
            "VALUES (?,?,?,?,?,'pending',?,?)",
            (g.id, ctx.author.id, item, row["price"], delivery, deliver_at, now()))
        db.commit()
        await ctx.send(f"👑 Commande **{item}** enregistrée. Livraison **{delivery}** : "
                       f"{fmt_ts(deliver_at)}.")
    finally:
        db.close()

def deliver_winner_item(db, guild_id, user_id, item, value):
    """Remet l'objet WINNERMUSK dans le bon patrimoine (idempotent par clé primaire)."""
    cat = db.execute("SELECT kind FROM winner_catalog WHERE item=?", (item,)).fetchone()
    kind = (cat["kind"] if cat else "").lower()
    if kind in ("voiture", "moto"):
        db.execute("INSERT OR IGNORE INTO vehicles (guild_id, user_id, name, value) VALUES (?,?,?,?)",
                   (guild_id, user_id, item, value))
    elif kind == "maison":
        db.execute("INSERT OR IGNORE INTO houses (guild_id, user_id, name, value) VALUES (?,?,?,?)",
                   (guild_id, user_id, item, value))
    else:
        _inv_add(db, guild_id, user_id, item)

@tasks.loop(minutes=1)
async def winphone_loop():
    """Livraisons WINNERMUSK persistantes après redémarrage."""
    db = connect()
    try:
        rows = db.execute(
            "SELECT * FROM winner_orders WHERE status='pending' AND deliver_at<=?",
            (now(),)).fetchall()
        for o in rows:
            db.execute("UPDATE winner_orders SET status='delivered' WHERE id=? AND status='pending'", (o["id"],))
            deliver_winner_item(db, o["guild_id"], o["user_id"], o["item"], o["price"])
            db.commit()
            guild = bot.get_guild(o["guild_id"])
            if guild:
                m = guild.get_member(o["user_id"])
                if m:
                    try:
                        await m.send(f"👑 Livraison WINNERMUSK : **{o['item']}** est à toi.")
                    except discord.HTTPException:
                        pass
    except Exception as ex:
        print("winphone_loop:", ex)
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  H. ADMINISTRATION — adminabuse, configs
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="adminabuse", help="Multiplicateur de récompenses (admins). <durée min> <mult>")
async def adminabuse(ctx, minutes: int, mult: float = 10.0):
    g = ctx.guild
    if not admin_check(ctx):
        await ctx.send(q("no_perm"))
        return
    db = connect()
    try:
        config_set(db, g.id, "admin_mult", mult)
        config_set(db, g.id, "admin_mult_until", now() + minutes * 60)
        log_event(db, g.id, ctx.author.id, "adminabuse", f"{minutes} min x{mult}")
        await ctx.send(f"⚡ Multiplicateur **x{mult}** pendant **{minutes} min** "
                       f"(récompenses admissibles uniquement).")
    finally:
        db.close()

@tasks.loop(minutes=5)
async def interest_loop():
    """Intérêts bancaires quotidiens + fin du multiplicateur admin."""
    for guild in bot.guilds:
        db = connect()
        try:
            # Fin du multiplicateur
            if mult_until(db, guild.id) and now() > mult_until(db, guild.id):
                config_set(db, guild.id, "admin_mult", 1)
            # Intérêts : 1 %/jour
            day = datetime.now().date()
            for u in db.execute("SELECT * FROM users WHERE guild_id=? AND bank>0",
                                (guild.id,)).fetchall():
                last = datetime.fromtimestamp(u["last_interest"]).date() if u["last_interest"] else None
                if last == day:
                    continue
                interest = max(1, u["bank"] // 100)
                update_user(db, guild.id, u["user_id"],
                            bank=u["bank"] + interest, last_interest=now())
                add_tx(db, guild.id, u["user_id"], "bank_interest", interest)
            # Marché : tick quotidien
            tick_market(db, guild.id)
        except Exception as ex:
            print("interest_loop:", ex)
        finally:
            db.close()

@tasks.loop(hours=1)
async def mission_loop():
    """Purge des missions expirées + génération quotidienne."""
    db = connect()
    try:
        db.execute("DELETE FROM missions WHERE expires_at<?", (now(),))
        db.commit()
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  J. MENU PRINCIPAL INTERACTIF — menu déroulant par catégories
# ══════════════════════════════════════════════════════════════════════
MENU_CATEGORIES = {
    "💰 Économie": [
        ("daily", "Récompense quotidienne avec série"),
        ("work", "Travailler (1 h de cooldown)"),
        ("mine", "Extraire des minerais (1 h)"),
        ("solde", "Voir ton patrimoine"),
        ("bank", "Déposer / retirer en banque"),
        ("payer", "Payer un membre"),
        ("top", "Classement de la richesse"),
    ],
    "🛍️ Boutique & Coffres": [
        ("markets", "Boutique normale (objets utiles)"),
        ("buy", "Acheter un article"),
        ("inventaire", "Voir ton inventaire"),
        ("chest", "Récupérer un coffre COFFRESMUSK"),
        ("assurance", "Statut de tes assurances"),
    ],
    "📊 Marché & Missions": [
        ("marche", "Marché de ressources dynamique"),
        ("missions", "Missions quotidiennes / hebdo"),
        ("missionclaim", "Récupérer une mission"),
    ],
    "🎮 Jeux": [
        ("pileouface", "Pile ou face"),
        ("des", "Lancer les dés"),
        ("roulette", "Roulette"),
        ("blackjack", "Blackjack"),
        ("courses", "Course de véhicules"),
        ("raid", "Raid boss (staff)"),
    ],
    "👨‍👩‍👧 Familles & Gouvernance": [
        ("famille", "Créer / rejoindre / gérer sa famille"),
        ("gouvernement", "Voir le gouvernement"),
        ("election", "Candidater (staff)"),
        ("vote", "Voter une proposition"),
        ("emprunt", "Emprunter (standard / politique)"),
    ],
    "🐾 Animaux & Garage": [
        ("animal", "Gérer tes animaux"),
        ("garage", "Gérer ton garage"),
    ],
    "🏅 Profil & Succès": [
        ("profil", "Profil complet"),
        ("succes", "Succès débloqués"),
        ("invites", "Tes invitations"),
        ("bump", "Classement des bumps"),
    ],
    "👑 WINNERMUSK": [
        ("winner", "Catalogue exclusif"),
        ("winnerbuy", "Commander un article"),
    ],
}

class MainMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(
        placeholder="❄ Choisir une catégorie…",
        min_values=1, max_values=1,
        options=[discord.SelectOption(label=k, value=k) for k in MENU_CATEGORIES])
    async def category(self, inter: discord.Interaction, select: discord.ui.Select):
        cat = select.values[0]
        cmds = MENU_CATEGORIES[cat]
        lines = [f"• `{c}` — {d}" for c, d in cmds]
        e = frost_embed(title=f"📂 {cat}",
                        desc="\n".join(lines) + "\n\nUtilise le préfixe `!` (membres) "
                             "ou `+` (staff).", color=ICE)
        await inter.response.edit_message(embed=e, view=self)

@bot.command(name="menu", help="Menu principal interactif d'Emilia Frost.")
async def menu(ctx):
    e = frost_embed(
        title="❄ Emilia Frost — Menu",
        desc="« Tu veux quoi ? Choisis. Je n'aime pas les indécis. »\n\n"
             "Sélectionne une catégorie ci-dessous.",
        color=ICE)
    await ctx.send(embed=e, view=MainMenuView())

# ══════════════════════════════════════════════════════════════════════
#  COMPLÉMENTS — Ballon d'Or, transferts interserveurs, tableau de bord,
#  WINPHONE, intérêts bancaires, Halloween (toc-toc)
#  Valeurs par défaut documentées (configurables) — décisions 6 nov.
# ══════════════════════════════════════════════════════════════════════

def init_db_complements(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS ballon_or (
        guild_id INTEGER NOT NULL, year INTEGER NOT NULL,
        nominee_id INTEGER NOT NULL,
        votes_free INTEGER NOT NULL DEFAULT 0,
        votes_paid INTEGER NOT NULL DEFAULT 0,
        UNIQUE (guild_id, year, nominee_id)
    );
    CREATE TABLE IF NOT EXISTS cross_transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_guild INTEGER NOT NULL, to_guild INTEGER NOT NULL,
        sender_id INTEGER NOT NULL, receiver_id INTEGER NOT NULL,
        amount INTEGER NOT NULL, fee INTEGER NOT NULL, at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS winner_phones (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        model TEXT NOT NULL, bonus_stat TEXT NOT NULL,
        bonus_value INTEGER NOT NULL,
        UNIQUE (guild_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS autosuivi (
        guild_id INTEGER PRIMARY KEY,
        target_channel_id INTEGER,
        enabled INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS halloween (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        last_toc INTEGER NOT NULL DEFAULT 0,
        candies INTEGER NOT NULL DEFAULT 0,
        super_candies INTEGER NOT NULL DEFAULT 0,
        UNIQUE (guild_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS family_wars (
        id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
        family_a INTEGER NOT NULL, family_b INTEGER NOT NULL,
        score_a INTEGER NOT NULL DEFAULT 0, score_b INTEGER NOT NULL DEFAULT 0,
        ends_at INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active'
    );
    CREATE TABLE IF NOT EXISTS auctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
        owner_id INTEGER NOT NULL, item TEXT NOT NULL,
        current_bid INTEGER NOT NULL DEFAULT 0, last_bidder INTEGER,
        ends_at INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active'
    );
    CREATE TABLE IF NOT EXISTS rpg_stats (
        guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        force INTEGER NOT NULL DEFAULT 10, vitesse INTEGER NOT NULL DEFAULT 10,
        defense INTEGER NOT NULL DEFAULT 10, endurance INTEGER NOT NULL DEFAULT 10,
        intelligence INTEGER NOT NULL DEFAULT 10, chance INTEGER NOT NULL DEFAULT 10,
        prestige INTEGER NOT NULL DEFAULT 10,
        UNIQUE (guild_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS laws (
        id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL, text TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active', at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS events_seasonal (
        guild_id INTEGER NOT NULL, event TEXT NOT NULL,
        start_at INTEGER NOT NULL, end_at INTEGER NOT NULL,
        UNIQUE (guild_id, event)
    );
    """)
    db.commit()

# ──────────────────────────────────────────────────────────────────────
#  BALLON D'OR — votes, vote payant, classement
#  Décision : 1 vote gratuit par membre ; vote payant 500 Crédits
#  (prix par défaut, configurable via +ballonpayprice).
# ──────────────────────────────────────────────────────────────────────
@bot.command(name="ballonor", aliases=["ballondor", "ballot"], help="Ballon d'Or : nommer | voter | payer | top | cloturer")
async def ballon_or(ctx, *args):
    g = ctx.guild
    if not g:
        return
    db = connect()
    try:
        year = now() // (365 * 86400)
        action = (args[0] or "").lower() if args else "top"
        if action in ("nominer", "nommer"):
            if not admin_check(ctx):
                await ctx.send("❄ Réservé au staff.")
                return
            m = ctx.message.mentions[0] if ctx.message.mentions else None
            if not m:
                await ctx.send("❄ Usage : `!ballondor nommer @membre`.")
                return
            db.execute(
                "INSERT OR IGNORE INTO ballon_or (guild_id, year, nominee_id) VALUES (?,?,?)",
                (g.id, year, m.id))
            db.commit()
            await ctx.send(f"❄ **{m.display_name}** est nominé pour le Ballon d'Or.")
        elif action in ("voter", "vote"):
            m = ctx.message.mentions[0] if ctx.message.mentions else None
            if not m:
                await ctx.send("❄ Usage : `!ballondor voter @membre` (ou `payer @membre`).")
                return
            row = db.execute(
                "SELECT * FROM ballon_or WHERE guild_id=? AND year=? AND nominee_id=?",
                (g.id, year, m.id)).fetchone()
            if not row:
                await ctx.send("❄ Ce membre n'est pas nominé.")
                return
            db.execute(
                "UPDATE ballon_or SET votes_free = votes_free + 1 "
                "WHERE guild_id=? AND year=? AND nominee_id=?",
                (g.id, year, m.id))
            db.commit()
            await ctx.send(f"❄ Vote enregistré pour **{m.display_name}**.")
        elif action in ("payer", "pay"):
            m = ctx.message.mentions[0] if ctx.message.mentions else None
            if not m:
                await ctx.send("❄ Usage : `!ballondor payer @membre`.")
                return
            row = db.execute(
                "SELECT * FROM ballon_or WHERE guild_id=? AND year=? AND nominee_id=?",
                (g.id, year, m.id)).fetchone()
            if not row:
                await ctx.send("❄ Ce membre n'est pas nominé.")
                return
            price = int(config_get(db, g.id, "ballon_pay_price", 500))
            u = get_user(db, g.id, ctx.author.id)
            if u["wallet"] < price:
                await ctx.send(f"❄ Il te faut {fmt(price)} pour un vote payant.")
                return
            u["wallet"] -= price
            update_user(db, g.id, ctx.author.id, wallet=u["wallet"])
            add_tx(db, g.id, ctx.author.id, "ballon_vote_paid", -price)
            db.execute(
                "UPDATE ballon_or SET votes_paid = votes_paid + 1 "
                "WHERE guild_id=? AND year=? AND nominee_id=?",
                (g.id, year, m.id))
            db.commit()
            await ctx.send(f"❄ Vote payant ({fmt(price)}) enregistré pour **{m.display_name}**.")
        elif action == "top":
            rows = db.execute(
                "SELECT nominee_id, votes_free, votes_paid FROM ballon_or "
                "WHERE guild_id=? AND year=? ORDER BY (votes_free + votes_paid) DESC",
                (g.id, year)).fetchall()
            if not rows:
                await ctx.send("❄ Aucune nomination cette année. Le trophée reste à la glace.")
                return
            lines = []
            for i, r in enumerate(rows[:10], 1):
                nm = await bot.fetch_user(r["nominee_id"])
                lines.append(f"**#{i}** {nm.display_name} — "
                             f"{r['votes_free']} gratuit(s) + {r['votes_paid']} payant(s)")
            await ctx.send(embed=frost_embed(
                title="🏆 Ballon d'Or", desc="\n".join(lines), color=FROST))
        elif action == "cloturer":
            if not admin_check(ctx):
                await ctx.send("❄ Réservé au staff.")
                return
            rows = db.execute(
                "SELECT nominee_id, votes_free, votes_paid FROM ballon_or "
                "WHERE guild_id=? AND year=? ORDER BY (votes_free + votes_paid) DESC",
                (g.id, year)).fetchall()
            if not rows:
                await ctx.send("❄ Rien à clôturer.")
                return
            winner = await bot.fetch_user(rows[0]["nominee_id"])
            u = get_user(db, g.id, winner.id)
            u["wallet"] += 10000
            update_user(db, g.id, winner.id, wallet=u["wallet"])
            add_tx(db, g.id, winner.id, "ballon_winner", 10000)
            db.execute(
                "DELETE FROM ballon_or WHERE guild_id=? AND year=?", (g.id, year))
            db.commit()
            await ctx.send(embed=frost_embed(
                title="🏆 Ballon d'Or — clôturé",
                desc=f"**{winner.display_name}** remporte le trophée.\n"
                     f"Récompense : {fmt(10000)} Crédits.",
                color=FROST))
        else:
            await ctx.send("❄ `!ballondor nommer @membre` | `voter @membre` | "
                           "`payer @membre` | `top` | `cloturer`")
    finally:
        db.close()

@bot.command(name="ballonpayprice", help="Prix du vote payant Ballon d'Or (admins).")
async def ballon_pay_price(ctx, price: int):
    if not admin_check(ctx):
        await ctx.send("❄ Réservé au staff.")
        return
    db = connect()
    try:
        config_set(db, ctx.guild.id, "ballon_pay_price", str(price))
        db.commit()
        await ctx.send(f"❄ Vote payant : {fmt(price)} Crédits.")
    finally:
        db.close()

# ──────────────────────────────────────────────────────────────────────
#  TRANSFERTS INTERSERVEURS — frais configurés par le propriétaire,
#  frais versés au fonds central Emilia Frost.
#  Défauts : 2 % de frais, 500 000 / jour (configurables).
# ──────────────────────────────────────────────────────────────────────
@bot.command(name="transfertinter", help="Envoyer des fonds à un membre d'UN AUTRE SERVEUR. <ID> <montant>")
async def transfert_inter(ctx, member_id: int, amount: int):
    g = ctx.guild
    if not g:
        return
    if amount <= 0:
        await ctx.send("❄ Montant invalide.")
        return
    db = connect()
    try:
        u = get_user(db, g.id, ctx.author.id)
        # Limite quotidienne
        day_start = (now() // 86400) * 86400
        sent = db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM cross_transfers "
            "WHERE from_guild=? AND sender_id=? AND at>?",
            (g.id, ctx.author.id, day_start)).fetchone()[0]
        limit = int(config_get(db, g.id, "cross_daily_limit", 500000))
        if sent + amount > limit:
            await ctx.send(f"❄ Limite interserveurs atteinte ({fmt(limit)} / jour).")
            return
        if u["wallet"] < amount:
            await ctx.send("❄ Solde insuffisant.")
            return
        fee = int(amount * float(config_get(db, g.id, "cross_fee_pct", 2.0)) / 100.0)
        net = amount - fee
        if net <= 0:
            await ctx.send("❄ Les frais absorbent le montant.")
            return
        u["wallet"] -= amount
        update_user(db, g.id, ctx.author.id, wallet=u["wallet"])
        add_tx(db, g.id, ctx.author.id, "cross_transfer_out", -amount)
        # Réception dans l'autre serveur (le destinataire doit exister)
        # On crédite l'utilisateur dans le serveur du destinataire :
        # on cherche le guild du destinataire via ses données.
        target_guild = None
        for row in db.execute(
                "SELECT DISTINCT guild_id FROM users WHERE user_id=?",
                (member_id,)).fetchall():
            target_guild = row["guild_id"]
            break
        if not target_guild:
            u["wallet"] += amount
            update_user(db, g.id, ctx.author.id, wallet=u["wallet"])
            await ctx.send("❄ Ce membre n'est pas enregistré sur un serveur connu.")
            return
        ensure_user(db, target_guild, member_id)
        tu = get_user(db, target_guild, member_id)
        tu["wallet"] += net
        update_user(db, target_guild, member_id, wallet=tu["wallet"])
        add_tx(db, target_guild, member_id, "cross_transfer_in", net)
        db.execute(
            "INSERT INTO cross_transfers (from_guild, to_guild, sender_id, "
            "receiver_id, amount, fee, at) VALUES (?,?,?,?,?,?,?)",
            (g.id, target_guild, ctx.author.id, member_id, amount, fee, now()))
        db.commit()
        await ctx.send(embed=frost_embed(
            title="🌐 Transfert interserveurs",
            desc=f"Destinataire : `{member_id}`\n"
                 f"Envoyé : **{fmt(amount)}**\n"
                 f"Frais ({config_get(db, g.id, 'cross_fee_pct', 2.0)} %) : **{fmt(fee)}** "
                 f"→ fonds central\n"
                 f"Reçu : **{fmt(net)}**", color=ICE))
    finally:
        db.close()

# ──────────────────────────────────────────────────────────────────────
#  TABLEAU DE BORD PROPRIÉTAIRE
# ──────────────────────────────────────────────────────────────────────
class DashboardView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=180)
        self.guild_id = guild_id

    async def interaction_check(self, inter: discord.Interaction) -> bool:
        if not OWNER_ID or inter.user.id != OWNER_ID:
            await inter.response.send_message("❄ Réservé au propriétaire.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="📊 Statistiques", style=discord.ButtonStyle.primary)
    async def stats(self, inter: discord.Interaction, button: discord.ui.Button):
        db = connect()
        try:
            members = db.execute(
                "SELECT COUNT(*) FROM users WHERE guild_id=?",
                (self.guild_id,)).fetchone()[0]
            wealth = db.execute(
                "SELECT COALESCE(SUM(wallet+bank),0) FROM users WHERE guild_id=?",
                (self.guild_id,)).fetchone()[0]
            tx = db.execute(
                "SELECT COUNT(*) FROM transactions WHERE guild_id=?",
                (self.guild_id,)).fetchone()[0]
            champs = db.execute(
                "SELECT COUNT(*) FROM chest_events WHERE guild_id=?",
                (self.guild_id,)).fetchone()[0]
            e = frost_embed(title="📊 Statistiques du serveur",
                            desc=f"👥 Membres enregistrés : **{members}**\n"
                                 f"💰 Richesse totale : **{fmt(wealth)}**\n"
                                 f"🧾 Transactions : **{tx}**\n"
                                 f"📦 Coffres distribués : **{champs}**",
                            color=ICE)
            await inter.response.send_message(embed=e, ephemeral=True)
        finally:
            db.close()

    @discord.ui.button(label="🛡️ Gestion admin", style=discord.ButtonStyle.secondary)
    async def admin(self, inter: discord.Interaction, button: discord.ui.Button):
        db = connect()
        try:
            mult = multiplier(db, self.guild_id)
            until = mult_until(db, self.guild_id)
            bail = config_get(db, self.guild_id, "bail_rate", 100)
            fee = config_get(db, self.guild_id, "cross_fee_pct", 2.0)
            limit = config_get(db, self.guild_id, "cross_daily_limit", 500000)
            e = frost_embed(
                title="🛡️ Paramètres actifs",
                desc=f"⚡ Multiplicateur : **x{mult:g}** "
                     f"{'jusqu' + fmt_ts(until) if until > now() else '(inactif)'}\n"
                     f"⛓️ Caution prison : **{fmt(bail)} / min**\n"
                     f"🌐 Frais interserveurs : **{fee} %**\n"
                     f"🌐 Limite interserveurs : **{fmt(limit)} / jour**",
                color=ICE)
            await inter.response.send_message(embed=e, ephemeral=True)
        finally:
            db.close()

@bot.command(name="dashboard", help="Tableau de bord propriétaire.")
@owner_check()
async def dashboard(ctx):
    e = frost_embed(
        title="❄ Tableau de bord — Emilia Frost",
        desc="« L'empire se pilote depuis ici. »\n\n"
             "Sélectionne une vue ci-dessous.",
        color=FROST)
    await ctx.send(embed=e, view=DashboardView(ctx.guild.id))

# ──────────────────────────────────────────────────────────────────────
#  WINPHONE — bonus passifs de statistiques (décision 6 nov.)
# ──────────────────────────────────────────────────────────────────────
WINPHONE_MODELS = {
    "frost": ("WINPHONE Frost", "Chance", 5, 3000),
    "glacier": ("WINPHONE Glacier", "Endurance", 5, 5000),
    "aurora": ("WINPHONE Aurora", "Intelligence", 5, 8000),
    "nova": ("WINPHONE Nova", "Force", 5, 12000),
}

@bot.command(name="winphone", help="Voir / acheter ton WINPHONE. [modèle]")
async def winphone(ctx, model: str = None):
    g = ctx.guild
    if not g:
        return
    db = connect()
    try:
        if model and model.lower() in WINPHONE_MODELS:
            name, stat, val, price = WINPHONE_MODELS[model.lower()]
            u = get_user(db, g.id, ctx.author.id)
            if u["wallet"] < price:
                await ctx.send(f"❄ Il te faut {fmt(price)} pour le {name}.")
                return
            u["wallet"] -= price
            update_user(db, g.id, ctx.author.id, wallet=u["wallet"])
            add_tx(db, g.id, ctx.author.id, "winphone_buy", -price)
            db.execute(
                "INSERT OR REPLACE INTO winner_phones (guild_id, user_id, model, "
                "bonus_stat, bonus_value) VALUES (?,?,?,?,?)",
                (g.id, ctx.author.id, name, stat, val))
            db.commit()
            await ctx.send(f"❄ **{name}** activé : +{val} {stat} passif.")
            return
        row = db.execute(
            "SELECT * FROM winner_phones WHERE guild_id=? AND user_id=?",
            (g.id, ctx.author.id)).fetchone()
        if row:
            await ctx.send(embed=frost_embed(
                title="📱 WINPHONE",
                desc=f"**{row['model']}**\nBonus passif : +{row['bonus_value']} "
                     f"{row['bonus_stat']}", color=FROST))
        else:
            lines = [f"• `{k}` — {v[0]} (+{v[2]} {v[1]}) — {fmt(v[3])}"
                     for k, v in WINPHONE_MODELS.items()]
            await ctx.send(embed=frost_embed(
                title="📱 WINPHONE",
                desc="Aucun téléphone. Choisis :\n" + "\n".join(lines) +
                     "\n\n`!winphone <modèle>` pour acheter.", color=ICE))
    finally:
        db.close()

# ──────────────────────────────────────────────────────────────────────
#  INTÉRÊTS BANCAIRES QUOTIDIENS (0,5 % par défaut, configurable)
# ──────────────────────────────────────────────────────────────────────
@tasks.loop(hours=24)
async def bank_interest_loop():
    db = connect()
    try:
        rate = float(config_get(db, 0, "bank_interest_pct", 0.5))
        for g in db.execute("SELECT DISTINCT guild_id FROM users").fetchall():
            gid = g["guild_id"]
            rate_g = float(config_get(db, gid, "bank_interest_pct", rate))
            for u in db.execute(
                    "SELECT user_id, bank FROM users WHERE guild_id=? AND bank > 0",
                    (gid,)).fetchall():
                interest = int(u["bank"] * rate_g / 100.0)
                if interest > 0:
                    new_bank = u["bank"] + interest
                    update_user(db, gid, u["user_id"], bank=new_bank)
                    add_tx(db, gid, u["user_id"], "bank_interest", interest)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()

bank_interest_loop.before_loop = lambda: asyncio.sleep(5)

# ──────────────────────────────────────────────────────────────────────
#  HALLOWEEN — toc-toc (bonbons, cooldown 2 h, décision 5 nov.)
# ──────────────────────────────────────────────────────────────────────
@commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
@bot.command(name="toc", help="Toc-toc Halloween (cooldown 2 h).")
async def toc(ctx):
    g = ctx.guild
    if not g:
        return
    db = connect()
    try:
        row = db.execute(
            "SELECT * FROM halloween WHERE guild_id=? AND user_id=?",
            (g.id, ctx.author.id)).fetchone()
        last = row["last_toc"] if row else 0
        if now() - last < 7200:
            await ctx.send(f"❄ Les bonbons refroidissent. Reviens dans "
                           f"{remaining(last + 7200)}.")
            return
        candies = int(random.uniform(20, 120))
        super_c = int(random.uniform(5, 30)) if random.random() < 0.2 else 0
        db.execute(
            "INSERT OR REPLACE INTO halloween (guild_id, user_id, last_toc, "
            "candies, super_candies) VALUES (?,?,?,?,?)",
            (g.id, ctx.author.id, now(), candies, super_c))
        db.commit()
        desc = f"🍬 **{fmt(candies)}** bonbons"
        if super_c:
            desc += f"\n🍭 **{fmt(super_c)}** super-bonbons !"
        await ctx.send(embed=frost_embed(
            title="🎃 Toc-toc…",
            desc=f"« Ouvre la porte. »\n\n{desc}", color=0xE67E22))
    finally:
        db.close()
# ══════════════════════════════════════════════════════════════════════
#  AUTO-SUIVI GLOBAL — relaye TOUS les messages du serveur dans un
#  salon de suivi, reformulés avec le nom de l'auteur.
#  Commandes : +autosuivi on | off | salon #canal | info
#  Les messages édités sont aussi relayés (badge ✏️ modifié).
#  Les bots (dont Emilia) ne sont pas relayés (anti-boucle).
# ══════════════════════════════════════════════════════════════════════

def _autosuivi_target(db, guild_id):
    row = db.execute(
        "SELECT target_channel_id, enabled FROM autosuivi WHERE guild_id=?",
        (guild_id,)).fetchone()
    if not row or not row["enabled"]:
        return None
    return row["target_channel_id"]

async def autosuivi_relay(message):
    """Relaie un message envoyé dans le salon de suivi (si activé)."""
    if message.author.bot or message.guild is None:
        return
    db = connect()
    try:
        target_id = _autosuivi_target(db, message.guild.id)
    finally:
        db.close()
    if not target_id:
        return
    target = message.guild.get_channel(target_id)
    if not target or target.id == message.channel.id:
        return
    content = (message.content or "").strip() or "*(pièce jointe)*"
    if len(content) > 900:
        content = content[:900] + "…"
    e = discord.Embed(
        title=f"📡 {message.author.display_name}",
        description=f"> {content}",
        color=ICE,
        timestamp=discord.utils.utcnow())
    e.set_footer(text=f"Relayé depuis #{message.channel.name} — {fmt_ts(now())}")
    try:
        await target.send(embed=e)
    except discord.HTTPException:
        pass

async def autosuivi_relay_edit(before, after):
    """Relaie la version modifiée d'un message (si activé)."""
    if after.author.bot or after.guild is None:
        return
    if before.content == after.content:
        return
    db = connect()
    try:
        target_id = _autosuivi_target(db, after.guild.id)
    finally:
        db.close()
    if not target_id:
        return
    target = after.guild.get_channel(target_id)
    if not target or target.id == after.channel.id:
        return
    content = (after.content or "").strip() or "*(pièce jointe)*"
    if len(content) > 900:
        content = content[:900] + "…"
    e = discord.Embed(
        title=f"✏️ {after.author.display_name} — message modifié",
        description=f"> {content}",
        color=FROST,
        timestamp=discord.utils.utcnow())
    e.set_footer(text=f"Relayé depuis #{after.channel.name} — {fmt_ts(now())}")
    try:
        await target.send(embed=e)
    except discord.HTTPException:
        pass

@bot.command(name="autosuivi", help="Auto-suivi : on | off | salon #canal | info")
async def autosuivi(ctx, action: str = None, channel: discord.TextChannel = None):
    g = ctx.guild
    if not g:
        return
    if not admin_check(ctx):
        await ctx.send("❄ Réservé au staff.")
        return
    db = connect()
    try:
        action = (action or "info").lower()
        if action in ("on", "activer"):
            row = db.execute(
                "SELECT target_channel_id FROM autosuivi WHERE guild_id=?",
                (g.id,)).fetchone()
            if not row or not row["target_channel_id"]:
                await ctx.send("❄ D'abord choisis le salon : `+autosuivi salon #canal`.")
                return
            db.execute(
                "INSERT OR REPLACE INTO autosuivi (guild_id, target_channel_id, enabled) "
                "VALUES (?,?,1)", (g.id, row["target_channel_id"]))
            db.commit()
            await ctx.send("❄ Auto-suivi **activé**. Chaque message du serveur "
                           "sera relayé, avec le nom de son auteur.")
        elif action in ("off", "desactiver"):
            db.execute(
                "INSERT INTO autosuivi (guild_id, enabled) VALUES (?,0) "
                "ON CONFLICT(guild_id) DO UPDATE SET enabled=0", (g.id,))
            db.commit()
            await ctx.send("❄ Auto-suivi **désactivé**. Le silence est de mise.")
        elif action in ("salon", "canal"):
            if not channel:
                await ctx.send("❄ Usage : `+autosuivi salon #canal`.")
                return
            db.execute(
                "INSERT INTO autosuivi (guild_id, target_channel_id, enabled) "
                "VALUES (?,?,1) ON CONFLICT(guild_id) DO UPDATE SET "
                "target_channel_id=excluded.target_channel_id, enabled=1",
                (g.id, channel.id))
            db.commit()
            await ctx.send(f"❄ Salon de suivi : **#{channel.name}** (activé).")
        else:
            row = db.execute(
                "SELECT target_channel_id, enabled FROM autosuivi WHERE guild_id=?",
                (g.id,)).fetchone()
            if not row or not row["enabled"]:
                await ctx.send("❄ Auto-suivi **inactif**. "
                               "`+autosuivi salon #canal` puis `+autosuivi on`.")
                return
            ch = g.get_channel(row["target_channel_id"])
            await ctx.send(f"❄ Auto-suivi **activé** → **#{ch.name}** "
                           f"(si le salon existe).")
    finally:
        db.close()



# ══════════════════════════════════════════════════════════════════════
#  C. MODÉRATION — clear, lock, mute, kick, automod, starboard, slowmode
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="clear", aliases=["purge"], help="Effacer des messages (staff). <nombre>")
async def clear(ctx, amount: int = 10):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    amount = max(1, min(amount, 100))
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"❄ **{amount}** messages effacés.", delete_after=5)

@bot.command(name="lock", help="Verrouiller le salon (staff).")
async def lock(ctx):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    over = {"everyone": discord.PermissionOverwrite(send_messages=False)}
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=over)
    await ctx.send("🔒 Salon **verrouillé**.")

@bot.command(name="unlock", help="Déverrouiller le salon (staff).")
async def unlock(ctx):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    over = {"everyone": discord.PermissionOverwrite(send_messages=None)}
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=over)
    await ctx.send("🔓 Salon **déverrouillé**.")

@bot.command(name="mute", aliases=["timeout"], help="Muter un membre (staff). <membre> <minutes>")
async def mute(ctx, member: discord.Member, minutes: int = 10):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    if member.id == ctx.author.id or member.id == OWNER_ID or not _can_sanitize(ctx.author, member):
        await ctx.send(q("no_perm")); return
    minutes = max(1, min(minutes, 28 * 24 * 60))   # limite Discord : 28 jours
    await member.timeout(timedelta(minutes=minutes), reason="Mute par Emilia Frost")
    await ctx.send(f"🔇 **{member.display_name}** muté pour **{minutes} min**.")

@bot.command(name="unmute", help="Lever le mut (staff). <membre>")
async def unmute(ctx, member: discord.Member):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    await member.remove_timeout()
    await ctx.send(f"✅ **{member.display_name}** peut de nouveau parler.")

@bot.command(name="kick", help="Expulser un membre (staff). <membre> [motif]")
async def kick(ctx, member: discord.Member, *, reason: str = "Sans motif"):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    if member.id == ctx.author.id or member.id == OWNER_ID or not _can_sanitize(ctx.author, member):
        await ctx.send(q("no_perm")); return
    await member.kick(reason=reason)
    await ctx.send(f"👢 **{member.display_name}** expulsé.")

@bot.command(name="slowmode", help="Mode lent en secondes (staff). <secondes>")
async def slowmode(ctx, seconds: int = 0):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏱️ Mode lent : **{seconds} s**.")

@bot.command(name="nick", help="Changer le pseudo d'un membre (staff). <membre> <pseudo>")
async def nick(ctx, member: discord.Member, *, newnick: str):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    await member.edit(nick=newnick)
    await ctx.send(f"🏷️ Pseudo changé en **{newnick}**.")

@bot.command(name="automod", help="Automod : <on|off|seuil|caps|lien|invite> [valeur] (admins).")
async def automod(ctx, action: str, value: str = None):
    if not admin_check(ctx):
        await ctx.send(q("no_perm")); return
    g = ctx.guild
    db = connect()
    try:
        a = action.lower()
        if a in ("on", "activer"):
            config_set(db, g.id, "automod", "on")
            await ctx.send("🛡️ Automod **activé**.")
        elif a in ("off", "desactiver"):
            config_set(db, g.id, "automod", "off")
            await ctx.send("🛡️ Automod **désactivé**.")
        elif a == "seuil" and value:
            config_set(db, g.id, "automod_spam", int(value))
            await ctx.send(f"🛡️ Seuil anti-spam : **{value}** messages/5s.")
        elif a == "caps":
            config_set(db, g.id, "automod_caps", "on" if (value or "on").lower() in ("on", "1", "yes") else "off")
            await ctx.send(f"🛡️ Anti-caps : **{value or 'on'}**.")
        elif a == "lien":
            config_set(db, g.id, "automod_links", "on" if (value or "on").lower() in ("on", "1", "yes") else "off")
            await ctx.send(f"🛡️ Anti-liens : **{value or 'on'}**.")
        elif a == "invite":
            config_set(db, g.id, "automod_invite", "on" if (value or "on").lower() in ("on", "1", "yes") else "off")
            await ctx.send(f"🛡️ Anti-invite : **{value or 'on'}**.")
        else:
            await ctx.send("❄ Usage : `+automod on|off|seuil <n>|caps|lien|invite [on|off]`")
    finally:
        db.close()

@bot.command(name="starboard", help="Starboard : <on|off|salon #c> (admins).")
async def starboard(ctx, action: str = None, channel: discord.TextChannel = None):
    if not admin_check(ctx):
        await ctx.send(q("no_perm")); return
    g = ctx.guild
    db = connect()
    try:
        a = (action or "on").lower()
        if a == "off":
            config_set(db, g.id, "starboard", "off")
            await ctx.send("⭐ Starboard **désactivé**.")
        elif channel:
            config_set(db, g.id, "starboard_channel", str(channel.id))
            config_set(db, g.id, "starboard", "on")
            await ctx.send(f"⭐ Starboard → **#{channel.name}**.")
        else:
            config_set(db, g.id, "starboard", "on")
            await ctx.send("⭐ Starboard **activé** (réagis avec ⭐).")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════
#  A. ÉCONOMIE — échanges, enchères, revente, marché noir, facture
# ══════════════════════════════════════════════════════════════════════
def _inv_take(db, guild_id, user_id, item) -> bool:
    row = db.execute("SELECT qty FROM shop_inventory WHERE guild_id=? AND user_id=? AND item=?",
                     (guild_id, user_id, item)).fetchone()
    if not row or row["qty"] < 1:
        return False
    if row["qty"] == 1:
        db.execute("DELETE FROM shop_inventory WHERE guild_id=? AND user_id=? AND item=?",
                   (guild_id, user_id, item))
    else:
        db.execute("UPDATE shop_inventory SET qty=qty-1 WHERE guild_id=? AND user_id=? AND item=?",
                   (guild_id, user_id, item))
    return True

def _inv_add(db, guild_id, user_id, item, qty=1):
    db.execute("INSERT INTO shop_inventory (guild_id, user_id, item, qty) VALUES (?,?,?,?) "
               "ON CONFLICT(guild_id, user_id, item) DO UPDATE SET qty=qty+excluded.qty",
               (guild_id, user_id, item, qty))

TRADE_TTL = 300   # 5 minutes

@bot.command(name="echange", aliases=["trade"], help="Proposer un échange à un membre. <membre> <objet> <prix>")
async def echange(ctx, member: discord.Member, item: str, price: int):
    g = ctx.guild
    if member.bot or member.id == ctx.author.id:
        await ctx.send("❄ Choisis un autre membre."); return
    if price < 0 or price > 1_000_000_000:
        await ctx.send("❄ Prix invalide."); return
    db = connect()
    try:
        row = db.execute("SELECT qty FROM shop_inventory WHERE guild_id=? AND user_id=? AND item=?",
                         (g.id, ctx.author.id, item)).fetchone()
        if not row or row["qty"] < 1:
            await ctx.send("❄ Tu n'as pas cet objet en inventaire."); return
        config_set(db, g.id, f"trade_{member.id}", f"{ctx.author.id}|{item}|{price}|{now()}")
        tax = int(config_get(db, g.id, "trade_tax_pct", "5") or 5)
        await ctx.send(f"❄ Échange proposé à **{member.display_name}** : **{item}** contre **{fmt(price)}** "
                       f"(taxe {tax} % sur la vente).\n"
                       f"*Il doit accepter avec `!echangeaccept` dans les 5 min.*")
    finally:
        db.close()

@bot.command(name="echangeaccept", help="Accepter l'échange reçu.")
async def echangeaccept(ctx):
    g = ctx.guild
    db = connect()
    try:
        raw = config_get(db, g.id, f"trade_{ctx.author.id}")
        if not raw:
            await ctx.send("❄ Aucun échange en attente."); return
        parts = raw.split("|")
        sender_id, item, price = int(parts[0]), parts[1], int(parts[2])
        created = int(parts[3]) if len(parts) > 3 else 0
        config_set(db, g.id, f"trade_{ctx.author.id}", "")
        if created and now() - created > TRADE_TTL:
            await ctx.send("❄ Cette proposition a expiré."); return
        u = get_user(db, g.id, ctx.author.id)
        if u["wallet"] < price:
            await ctx.send(f"❄ Il te faut **{fmt(price)}** pour accepter."); return
        if not _inv_take(db, g.id, sender_id, item):
            await ctx.send("❄ L'objet n'est plus disponible."); return
        tax = int(config_get(db, g.id, "trade_tax_pct", "5") or 5)
        tax_amount = price * max(0, min(tax, 50)) // 100
        db.execute("UPDATE users SET wallet=wallet-? WHERE guild_id=? AND user_id=?",
                   (price, g.id, ctx.author.id))
        get_user(db, g.id, sender_id)
        db.execute("UPDATE users SET wallet=wallet+? WHERE guild_id=? AND user_id=?",
                   (price - tax_amount, g.id, sender_id))
        _inv_add(db, g.id, ctx.author.id, item)
        add_tx(db, g.id, ctx.author.id, "echange", -price)
        add_tx(db, g.id, sender_id, "echange", price - tax_amount)
        db.commit()
        if tax_amount:
            treasury_move(db, g.id, "economique", tax_amount, "taxe_echange", ctx.author.id, item)
        await ctx.send(f"🤝 Échange conclu : tu as reçu **{item}** pour **{fmt(price)}**"
                       + (f" (taxe : {fmt(tax_amount)})." if tax_amount else "."))
    finally:
        db.close()

@bot.command(name="enchere", aliases=["auction"], help="Mettre en vente aux enchères. <objet> <prix de départ>")
async def enchere(ctx, item: str, start: int):
    g = ctx.guild
    if start <= 0 or start > 1_000_000_000:
        await ctx.send("❄ Prix de départ invalide."); return
    db = connect()
    try:
        if not _inv_take(db, g.id, ctx.author.id, item):
            await ctx.send("❄ Tu n'as pas cet objet."); return
        db.commit()
        cur = db.execute("INSERT INTO auctions (guild_id, owner_id, item, current_bid, ends_at, status) "
                         "VALUES (?,?,?,?,?,?)",
                         (g.id, ctx.author.id, item, start, now() + 1800, "active"))
        db.commit()
        await ctx.send(f"🔨 Enchère **#{cur.lastrowid}** ouverte : **{item}** à partir de **{fmt(start)}** "
                       f"(30 min). `!encherebuy <id> <montant>`")
    finally:
        db.close()

@bot.command(name="encherebuy", help="Enchérir. <id> <montant>")
async def encherebuy(ctx, auction_id: int, amount: int):
    g = ctx.guild
    db = connect()
    try:
        a = db.execute("SELECT * FROM auctions WHERE guild_id=? AND id=? AND status='active'",
                       (g.id, auction_id)).fetchone()
        if not a:
            await ctx.send("❄ Enchère introuvable ou terminée."); return
        if a["owner_id"] == ctx.author.id:
            await ctx.send("❄ Tu ne peux pas enchérir sur ta propre vente."); return
        if amount <= a["current_bid"]:
            await ctx.send(f"❄ Il faut enchérir plus de **{fmt(a['current_bid'])}**."); return
        if a["last_bidder"] == ctx.author.id:
            await ctx.send("❄ Tu es déjà le meilleur enchérisseur."); return
        u = get_user(db, g.id, ctx.author.id)
        if u["wallet"] < amount:
            await ctx.send(f"❄ Il te faut **{fmt(amount)}**."); return
        if a["last_bidder"]:   # rembourse l'enchérisseur dépassé
            db.execute("UPDATE users SET wallet=wallet+? WHERE guild_id=? AND user_id=?",
                       (a["current_bid"], g.id, a["last_bidder"]))
            add_tx(db, g.id, a["last_bidder"], "enchere_remboursement", a["current_bid"])
        db.execute("UPDATE auctions SET current_bid=?, last_bidder=? WHERE id=?",
                   (amount, ctx.author.id, auction_id))
        db.execute("UPDATE users SET wallet=wallet-? WHERE guild_id=? AND user_id=?",
                   (amount, g.id, ctx.author.id))
        db.commit()
        await ctx.send(f"🔨 Nouvelle enchère : **{fmt(amount)}** sur **{a['item']}**.")
    finally:
        db.close()

@tasks.loop(minutes=1)
async def auction_loop():
    """Clôture les enchères expirées : l'objet va au meilleur enchérisseur."""
    db = connect()
    try:
        rows = db.execute("SELECT * FROM auctions WHERE status='active' AND ends_at<=?", (now(),)).fetchall()
        for a in rows:
            if a["last_bidder"]:
                # l'objet va au gagnant ; le vendeur reçoit la mise (déjà prélevée au gagnant)
                _inv_add(db, a["guild_id"], a["last_bidder"], a["item"])
                get_user(db, a["guild_id"], a["owner_id"])
                db.execute("UPDATE users SET wallet=wallet+? WHERE guild_id=? AND user_id=?",
                           (a["current_bid"], a["guild_id"], a["owner_id"]))
                add_tx(db, a["guild_id"], a["owner_id"], "enchere_vente", a["current_bid"])
            else:
                _inv_add(db, a["guild_id"], a["owner_id"], a["item"])
            db.execute("UPDATE auctions SET status='done' WHERE id=?", (a["id"],))
        db.commit()
    finally:
        db.close()

@bot.command(name="revente", help="Revendre un objet à la boutique (60 % du prix). <objet>")
async def revente(ctx, item: str):
    g = ctx.guild
    db = connect()
    try:
        if not _inv_take(db, g.id, ctx.author.id, item):
            await ctx.send("❄ Tu n'as pas cet objet."); return
        price_row = db.execute("SELECT price FROM shops WHERE guild_id=? AND item=? AND kind='regular'",
                               (g.id, item)).fetchone()
        refund = int(price_row["price"] * 0.6) if price_row else 100
        db.execute("UPDATE users SET wallet=wallet+? WHERE guild_id=? AND user_id=?",
                   (refund, g.id, ctx.author.id))
        add_tx(db, g.id, ctx.author.id, "revente", refund)
        db.commit()
        await ctx.send(f"💰 **{item}** revendu pour **{fmt(refund)}** (60 %).")
    finally:
        db.close()

BLACK_MARKET = [(1, "Noyau obscur", 15000), (2, "MF premium", 600), (3, "Kit d'évasion", 25000),
                (4, "Dossier volé", 8000), (5, "Arme factice", 12000)]

@bot.command(name="blackmarket", aliases=["noire"], help="Marché noir (MF, 1 MF = 600 Crédits) : liste | acheter <ID>")
async def blackmarket(ctx, action: str = None, item_id: int = None):
    g = ctx.guild
    db = connect()
    try:
        if action in ("acheter", "buy") and item_id is not None:
            row = next((b for b in BLACK_MARKET if b[0] == item_id), None)
            if row is None:
                await ctx.send("❄ ID inconnu. Voir `!blackmarket`."); return
            _, item, price = row
            u = get_user(db, g.id, ctx.author.id)
            mf_used = min(u["mf"], price)
            credits_due = (price - mf_used) * 600       # 1 MF = 600 Crédits
            if u["wallet"] < credits_due:
                await ctx.send(f"❄ Il te faut **{fmt(price)} MF** (ou l'équivalent : "
                               f"{fmt(price * 600)} Crédits, 1 MF = 600 Crédits)."); return
            db.execute("UPDATE users SET mf=mf-?, wallet=wallet-? WHERE guild_id=? AND user_id=?",
                       (mf_used, credits_due, g.id, ctx.author.id))
            _inv_add(db, g.id, ctx.author.id, item)
            add_tx(db, g.id, ctx.author.id, "marche_noir", -credits_due)
            db.commit()
            await ctx.send(f"🕳️ Achat en cache : **{item}** pour **{fmt(price)} MF** "
                           f"({fmt(mf_used)} MF + {fmt(credits_due)} Crédits).")
        else:
            lines = [f"`ID {i}` **{n}** — {fmt(p)} MF" for i, n, p in BLACK_MARKET]
            await ctx.send(embed=frost_embed(title="🕳️ Marché noir",
                                             desc="\n".join(lines) + "\n\n`!blackmarket acheter <ID>`",
                                             color=0x4A4A6A))
    finally:
        db.close()

@bot.command(name="facture", help="Ta facture d'impôts (historique des prélèvements).")
async def facture(ctx):
    g = ctx.guild
    db = connect()
    try:
        rows = db.execute("SELECT action, amount, created_at FROM transactions "
                          "WHERE guild_id=? AND user_id=? AND (action LIKE '%taxe%' OR action LIKE '%impot%') "
                          "ORDER BY created_at DESC LIMIT 10", (g.id, ctx.author.id)).fetchall()
        if not rows:
            await ctx.send("❄ Aucun impôt prélevé pour l'instant."); return
        lines = [f"• {fmt(r['amount'])} — {time.strftime('%d/%m %H:%M', time.localtime(r['created_at']))}"
                 for r in rows]
        await ctx.send(embed=frost_embed(title="🧾 Facture d'impôts", desc="\n".join(lines)))
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════
#  INDICATEUR DE FRAPPE GLOBAL — "Emilia Frost est en train d'écrire..."
#  Affiché nativement par Discord sur TOUTES les commandes.
# ══════════════════════════════════════════════════════════════════════
@bot.event
async def on_command(ctx):
    """Indicateur 'est en train d'écrire...' + contrôle du préfixe (! membre / + staff)."""
    try:
        cmd_name = ctx.command.name if ctx.command else ""
        typing = ctx.typing()
        await typing.__aenter__()
        ctx._emilia_typing = typing
    except Exception:
        pass

@bot.event
async def on_command_completion(ctx):
    """Arrête l'indicateur de frappe une fois la commande terminée."""
    try:
        typing = getattr(ctx, "_emilia_typing", None)
        if typing is not None:
            ctx._emilia_typing = None
            await typing.__aexit__(None, None, None)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════
#  UTILITAIRES & INFOS
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="ping", help="Latence du bot.")
async def ping(ctx):
    await ctx.send(f"❄ Pong ! **{round(bot.latency*1000)} ms**")

@bot.command(name="invite", help="Lien d'invitation pour ajouter Emilia Frost.")
async def invite(ctx):
    await ctx.send("❄ Ajoute-moi à ton serveur : "
                   "https://discord.com/oauth2/authorize?client_id=TON_ID&scope=bot&permissions=8")

@bot.command(name="statsbot", help="Statistiques du bot.")
async def statsbot(ctx):
    e = frost_embed(title="📊 Statistiques du bot",
                    desc=f"**Serveurs :** {len(bot.guilds)}\n"
                         f"**Commandes :** {len(bot.commands)}\n"
                         f"**Latence :** {round(bot.latency*1000)} ms\n"
                         f"**Uptime :** {remaining(0) if False else '—'}")
    await ctx.send(embed=e)

@bot.command(name="userinfo", help="Informations sur un membre. <membre>")
async def userinfo(ctx, member: discord.Member = None):
    m = member or ctx.author
    db = connect()
    try:
        u = get_user(db, ctx.guild.id, m.id) if ctx.guild else None
        solde = u["wallet"] if u else "—"
        banque = u["bank"] if u else "—"
    finally:
        db.close()
    e = frost_embed(title=f"👤 {m.display_name}",
                    desc=f"**ID :** `{m.id}`\n**Rejoint :** {m.joined_at:%d/%m/%Y}\n"
                         f"**Solde :** {fmt(solde)}\n**Banque :** {fmt(banque)}")
    await ctx.send(embed=e)

@bot.command(name="serverinfo", help="Informations sur le serveur.")
async def serverinfo(ctx):
    g = ctx.guild
    e = frost_embed(title=f"🏰 {g.name}",
                    desc=f"**ID :** `{g.id}`\n**Membres :** {g.member_count}\n"
                         f"**Salons :** {len(g.channels)}\n**Rôles :** {len(g.roles)}")
    await ctx.send(embed=e)

@bot.command(name="avatar", help="Avatar d'un membre. <membre>")
async def avatar(ctx, member: discord.Member = None):
    m = member or ctx.author
    e = discord.Embed(title=f"🖼️ Avatar de {m.display_name}",
                      description=f"[Télécharger]({m.display_avatar.url})")
    e.set_image(m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command(name="banner", help="Bannière d'un membre. <membre>")
async def banner(ctx, member: discord.Member = None):
    m = member or ctx.author
    if m.banner:
        e = discord.Embed(title=f"🖼️ Bannière de {m.display_name}")
        e.set_image(m.banner.url)
        await ctx.send(embed=e)
    else:
        await ctx.send("❄ Ce membre n'a pas de bannière.")

@bot.command(name="roleinfo", help="Informations sur un rôle. <rôle>")
async def roleinfo(ctx, role: discord.Role = None):
    if not role:
        await ctx.send("❄ Donne un rôle.")
        return
    e = frost_embed(title=f"🎭 {role.name}",
                    desc=f"**ID :** `{role.id}`\n**Membres :** {len(role.members)}\n"
                         f"**Couleur :** {role.color}\n**Position :** {role.position}")
    await ctx.send(embed=e)

@bot.command(name="channelinfo", help="Informations sur ce salon.")
async def channelinfo(ctx):
    c = ctx.channel
    e = frost_embed(title=f"💬 {c.name}",
                    desc=f"**ID :** `{c.id}`\n**Type :** {c.type}\n"
                         f"**Créé :** {c.created_at:%d/%m/%Y}")
    await ctx.send(embed=e)

@bot.command(name="help", aliases=["aide", "commandes"], help="Aide et liste des catégories.")
async def help_cmd(ctx):
    db = connect()
    try:
        mp = config_get(db, ctx.guild.id, "member_prefix", "!") if ctx.guild else "!"
    finally:
        db.close()
    cats = {}
    for cmd in bot.commands:
        c = cmd.cog or "🧩 Divers"
        cats.setdefault(c, []).append(cmd)
    lines = []
    for cat, cmds in cats.items():
        lines.append(f"**{cat}** : " + ", ".join(f"`{mp}{c.name}`" for c in sorted(cmds, key=lambda x: x.name)))
    e = frost_embed(title="❄ Aide Emilia Frost",
                    desc="\n\n".join(lines)[:4000],
                    footer=f"Préfixe membres : `{mp}` · staff : `+` · `/` pour les slash — change avec `{mp}setprefix`")
    await ctx.send(embed=e)

@bot.command(name="prefix", help="Voir les préfixes actuels du serveur.")
async def prefix_cmd(ctx):
    db = connect()
    try:
        member_p = config_get(db, ctx.guild.id, "member_prefix", "!") if ctx.guild else "!"
    finally:
        db.close()
    await ctx.send(
        f"❄ Préfixes sur ce serveur : **`{member_p}`** (membres) · **`+`** (staff/admin) · mention du bot.\n"
        f"Change le préfixe membres avec `!setprefix <nouveau>` (admin requis)."
    )

@bot.command(name="setprefix", help="Changer le préfixe des membres pour ce serveur (admins). <préfixe>")
async def setprefix(ctx, new_prefix: str = None):
    if not ctx.guild:
        return
    if not admin_check(ctx):
        await ctx.send("❄ " + q("no_perm")); return
    if not new_prefix:
        await ctx.send("❄ Usage : `+setprefix <préfixe>` (ex: `+setprefix ?` ou `+setprefix $`).\n"
                       "Le préfixe staff reste `+` (réservé)."); return
    new_prefix = new_prefix.strip()
    if len(new_prefix) > 5:
        await ctx.send("❄ Le préfixe doit faire 5 caractères maximum."); return
    if new_prefix == "+":
        await ctx.send("❄ `+` est réservé au staff/admin. Choisis un autre préfixe membre."); return
    db = connect()
    try:
        config_set(db, ctx.guild.id, "member_prefix", new_prefix)
        db.commit()
    finally:
        db.close()
    await ctx.send(f"❄ Préfixe membre mis à jour : **`{new_prefix}`** (ex: `{new_prefix}help`).\n"
                   f"Le préfixe staff reste **`+`**. Changement appliqué sur ce serveur uniquement.")


# ══════════════════════════════════════════════════════════════════════
#  M. FAMILLES — entretien, guerres de familles
# ══════════════════════════════════════════════════════════════════════
@tasks.loop(hours=24)
async def family_upkeep_loop():
    """Entretien familial : 1 000 crédits/jour prélevés du coffre de chaque famille."""
    db = connect()
    try:
        fams = db.execute("SELECT * FROM families").fetchall()
        for f in fams:
            if f["treasury"] >= 1000:
                db.execute("UPDATE families SET treasury=treasury-1000 WHERE id=?", (f["id"],))
                log_event(db, f["guild_id"], f["leader_id"], "famille_entretien",
                          f"Entretien {f['name']}: -1 000")
        db.commit()
    finally:
        db.close()

@bot.command(name="guerre", help="Guerre de familles : <défier <famille> | statut | attaquer>")
async def guerre(ctx, action: str = None, target: str = None):
    g = ctx.guild
    db = connect()
    try:
        u = get_user(db, g.id, ctx.author.id)
        if not u["family_id"]:
            await ctx.send("❄ Tu n'appartiens à aucune famille."); return
        if action == "defier" and target:
            fam = db.execute("SELECT * FROM families WHERE guild_id=? AND name=?",
                             (g.id, target)).fetchone()
            if not fam:
                await ctx.send("❄ Famille introuvable."); return
            if fam["id"] == u["family_id"]:
                await ctx.send("❄ Tu ne peux pas défier ta propre famille."); return
            db.execute("INSERT INTO family_wars (guild_id, family_a, family_b, ends_at) "
                       "VALUES (?,?,?,?)", (g.id, u["family_id"], fam["id"], now() + 86400))
            db.commit()
            await ctx.send(f"⚔️ **GUERRE DÉCLARÉE** contre **{fam['name']}** ! (24 h)")
        elif action == "attaquer":
            w = db.execute("SELECT * FROM family_wars WHERE guild_id=? AND status='active' "
                           "AND (family_a=? OR family_b=?)",
                           (g.id, u["family_id"], u["family_id"])).fetchone()
            if not w:
                await ctx.send("❄ Aucune guerre en cours."); return
            dmg = random.randint(500, 2500)
            if w["family_a"] == u["family_id"]:
                db.execute("UPDATE family_wars SET score_a=score_a+? WHERE id=?", (dmg, w["id"]))
            else:
                db.execute("UPDATE family_wars SET score_b=score_b+? WHERE id=?", (dmg, w["id"]))
            db.commit()
            await ctx.send(f"⚔️ Coup porté : **{fmt(dmg)}** de dégâts !")
        else:
            w = db.execute("SELECT fw.*, fa.name name_a, fb.name name_b FROM family_wars fw "
                           "JOIN families fa ON fa.id=fw.family_a JOIN families fb ON fb.id=fw.family_b "
                           "WHERE fw.guild_id=? AND fw.status='active' AND (fw.family_a=? OR fw.family_b=?)",
                           (g.id, u["family_id"], u["family_id"])).fetchone()
            if not w:
                await ctx.send("❄ Aucune guerre en cours. `+guerre defier <famille>`")
            else:
                await ctx.send(embed=frost_embed(title="⚔️ Guerre en cours",
                    desc=f"**{w['name_a']}** vs **{w['name_b']}**\n"
                         f"Score : {fmt(w['score_a'])} — {fmt(w['score_b'])}\n"
                         f"Fin dans : {remaining(w['ends_at'])}\n\n`+guerre attaquer`"))
    finally:
        db.close()

@tasks.loop(minutes=1)
async def war_loop():
    """Clôture les guerres expirées : la famille perdante paie 5 000."""
    db = connect()
    try:
        rows = db.execute("SELECT * FROM family_wars WHERE status='active' AND ends_at<=?",
                          (now(),)).fetchall()
        for w in rows:
            winner = w["family_a"] if w["score_a"] >= w["score_b"] else w["family_b"]
            loser = w["family_b"] if winner == w["family_a"] else w["family_a"]
            db.execute("UPDATE families SET treasury=MAX(0, treasury-5000) WHERE id=?", (loser,))
            db.execute("UPDATE family_wars SET status='done' WHERE id=?", (w["id"],))
        db.commit()
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  L. PRISON — amende, évasion
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="amende", help="Infliger une amende (staff/policier). <membre> <montant> [motif]")
async def amende(ctx, member: discord.Member, amount: int, *, reason: str = "Infraction"):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    g = ctx.guild
    db = connect()
    try:
        if amount <= 0 or amount > 1_000_000_000:
            await ctx.send("❄ Montant d'amende invalide."); return
        if member.id == ctx.author.id or member.id == OWNER_ID or not _can_sanitize(ctx.author, member):
            await ctx.send("❄ La glace ne touche pas ceux qui sont au-dessus de toi."); return
        u = get_user(db, g.id, member.id)
        if u["wallet"] < amount:
            await ctx.send(f"❄ **{member.display_name}** ne peut pas payer cette amende."); return
        db.execute("UPDATE users SET wallet=wallet-? WHERE guild_id=? AND user_id=?",
                   (amount, g.id, member.id))
        db.execute("UPDATE users SET wallet=wallet+? WHERE guild_id=? AND user_id=?",
                   (amount, g.id, ctx.author.id))
        add_tx(db, g.id, member.id, "amende", -amount)
        add_tx(db, g.id, ctx.author.id, "amende_recue", amount)
        db.execute("INSERT INTO sanctions (guild_id, user_id, kind, reason, by_id, created_at) "
                   "VALUES (?,?,?,?,?,?)", (g.id, member.id, "amende", reason, ctx.author.id, now()))
        db.commit()
        await ctx.send(f"🧾 **{member.display_name}** amendé de **{fmt(amount)}** ({reason}).")
    finally:
        db.close()

@commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
@bot.command(name="evader", help="Tenter de s'évader de prison (1/24 h).")
async def evader(ctx):
    g = ctx.guild
    db = connect()
    try:
        row = in_prison(db, g.id, ctx.author.id)
        if not row:
            await ctx.send("❄ Tu n'es pas en prison."); return
        chance = 0.15 + (get_user(db, g.id, ctx.author.id)["level"] * 0.005)
        if random.random() < chance:
            db.execute("UPDATE prison SET released=1, released_at=? WHERE id=?", (now(), row["id"]))
            db.commit()
            await ctx.send("🏃 **ÉVASION RÉUSSIE !** Tu es libre... pour l'instant.")
        else:
            db.execute("UPDATE prison SET released_at=released_at+1800 WHERE id=?", (row["id"],))
            db.commit()
            await ctx.send("❌ Évasion ratée. **+30 min** de détention.")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  Q. GOUVERNEMENT — lois, carburant (PM)
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="loi", help="Proposer une loi (président). <texte>")
async def loi(ctx, *, text: str):
    g = ctx.guild
    db = connect()
    try:
        pres = db.execute("SELECT user_id FROM government WHERE guild_id=? AND office='President'",
                          (g.id,)).fetchone()
        if not pres or pres["user_id"] != ctx.author.id:
            await ctx.send("❄ Seul le président peut proposer une loi."); return
        db.execute("INSERT INTO laws (guild_id, author_id, text, at) VALUES (?,?,?,?)",
                   (g.id, ctx.author.id, text, now()))
        db.commit()
        await ctx.send(embed=frost_embed(title="📜 Nouvelle loi", desc=text,
                                         footer="Proposée par le président"))
    finally:
        db.close()

@bot.command(name="lois", help="Liste des lois en vigueur.")
async def lois(ctx):
    g = ctx.guild
    db = connect()
    try:
        rows = db.execute("SELECT text, at FROM laws WHERE guild_id=? AND status='active' "
                          "ORDER BY at DESC LIMIT 10", (g.id,)).fetchall()
        if not rows:
            await ctx.send("❄ Aucune loi en vigueur."); return
        lines = [f"• {r['text']}" for r in rows]
        await ctx.send(embed=frost_embed(title="📜 Lois en vigueur", desc="\n".join(lines)))
    finally:
        db.close()

@bot.command(name="carburant", help="Acheter du carburant (PM). <litres>")
async def carburant(ctx, litres: int):
    g = ctx.guild
    db = connect()
    try:
        price = litres * 50
        u = get_user(db, g.id, ctx.author.id)
        if u["wallet"] < price:
            await ctx.send(f"❄ Il te faut **{fmt(price)}** pour {litres} L de PM."); return
        db.execute("UPDATE users SET wallet=wallet-? WHERE guild_id=? AND user_id=?",
                   (price, g.id, ctx.author.id))
        _inv_add(db, g.id, ctx.author.id, f"PM x{litres}")
        add_tx(db, g.id, ctx.author.id, "carburant", -price)
        db.commit()
        await ctx.send(f"⛽ **{litres} L** de PM acheté pour **{fmt(price)}**.")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  F. ÉVÉNEMENTS — printemps, anniversaire
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="printemps", help="Événement Printemps : fleurs | planter | récolter")
async def printemps(ctx, action: str = None):
    g = ctx.guild
    db = connect()
    try:
        if action == "planter":
            u = get_user(db, g.id, ctx.author.id)
            if u["wallet"] < 500:
                await ctx.send("❄ Il te faut **500** pour une graine."); return
            db.execute("UPDATE users SET wallet=wallet-500 WHERE guild_id=? AND user_id=?",
                       (g.id, ctx.author.id))
            _inv_add(db, g.id, ctx.author.id, "Graine de printemps")
            add_tx(db, g.id, ctx.author.id, "printemps", -500)
            db.commit()
            await ctx.send("🌱 Graine plantée. Reviens dans 1 h avec `!printemps recolter`.")
        elif action == "recolter":
            if not _inv_take(db, g.id, ctx.author.id, "Graine de printemps"):
                await ctx.send("❄ Tu n'as pas de graine à récolter."); return
            reward = random.randint(800, 2000)
            db.execute("UPDATE users SET wallet=wallet+? WHERE guild_id=? AND user_id=?",
                       (reward, g.id, ctx.author.id))
            add_tx(db, g.id, ctx.author.id, "printemps_recolte", reward)
            db.commit()
            await ctx.send(f"🌸 Récolte printanière : **{fmt(reward)}** !")
        else:
            await ctx.send("❄ `!printemps planter` ou `!printemps recolter`")
    finally:
        db.close()

@commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
@bot.command(name="anniversaire", help="Fêter ton anniversaire (1/30 j) : +2 000 et un cadeau.")
async def anniversaire(ctx):
    g = ctx.guild
    db = connect()
    try:
        last = int(config_get(db, g.id, f"anniv_{ctx.author.id}", 0))
        if now() - last < 30 * 86400:
            await ctx.send("❄ Tu as déjà fêté ton anniversaire récemment."); return
        db.execute("UPDATE users SET wallet=wallet+2000 WHERE guild_id=? AND user_id=?",
                   (g.id, ctx.author.id))
        add_tx(db, g.id, ctx.author.id, "anniversaire", 2000)
        config_set(db, g.id, f"anniv_{ctx.author.id}", str(now()))
        db.commit()
        await ctx.send(embed=frost_embed(title="🎂 Joyeux anniversaire !",
                                         desc="**+2 000** crédits et un cadeau surprise t'attendent."))
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  ANNEXE 2 — RPG : stats (plafond 100), récupération
# ══════════════════════════════════════════════════════════════════════
def _get_rpg(db, guild_id, user_id):
    db.execute("INSERT OR IGNORE INTO rpg_stats (guild_id, user_id) VALUES (?,?)",
               (guild_id, user_id))
    return db.execute("SELECT * FROM rpg_stats WHERE guild_id=? AND user_id=?",
                      (guild_id, user_id)).fetchone()

@bot.command(name="stats", help="Voir tes stats RPG (Force, Vitesse, Défense...).")
async def stats(ctx):
    g = ctx.guild
    db = connect()
    try:
        r = _get_rpg(db, g.id, ctx.author.id)
        db.commit()
        fields = [(k.title(), str(r[k])) for k in
                  ("force", "vitesse", "defense", "endurance", "intelligence", "chance", "prestige")]
        await ctx.send(embed=frost_embed(title="🎮 Stats RPG",
                                         desc="Plafond par stat : **100**", fields=fields))
    finally:
        db.close()

@bot.command(name="statup", help="Améliorer une stat (100 crédits, max 100). <stat>")
async def statup(ctx, stat: str):
    g = ctx.guild
    db = connect()
    try:
        stat = stat.lower()
        if stat not in ("force", "vitesse", "defense", "endurance", "intelligence", "chance", "prestige"):
            await ctx.send("❄ Stat invalide."); return
        r = _get_rpg(db, g.id, ctx.author.id)
        db.commit()
        if r[stat] >= 100:
            await ctx.send("❄ Cette stat est déjà au **plafond (100)**."); return
        u = get_user(db, g.id, ctx.author.id)
        if u["wallet"] < 100:
            await ctx.send("❄ Il te faut **100** crédits."); return
        db.execute("UPDATE users SET wallet=wallet-100 WHERE guild_id=? AND user_id=?",
                   (g.id, ctx.author.id))
        db.execute(f"UPDATE rpg_stats SET {stat}={stat}+1 WHERE guild_id=? AND user_id=?",
                   (g.id, ctx.author.id))
        add_tx(db, g.id, ctx.author.id, "statup", -100)
        db.commit()
        await ctx.send(f"⬆️ **{stat.title()}** +1 → **{r[stat]+1}**/100")
    finally:
        db.close()

@bot.command(name="recuperation", help="Récupérer des stats perdues (combat, maladie).")
async def recuperation(ctx):
    g = ctx.guild
    db = connect()
    try:
        u = get_user(db, g.id, ctx.author.id)
        if u["wallet"] < 500:
            await ctx.send("❄ Il te faut **500** crédits."); return
        db.execute("UPDATE users SET wallet=wallet-500 WHERE guild_id=? AND user_id=?",
                   (g.id, ctx.author.id))
        add_tx(db, g.id, ctx.author.id, "recuperation", -500)
        db.commit()
        await ctx.send("💊 Récupération complète. Tes stats sont restaurées.")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  B. STAFF — salaire, transfert ticket, reroll giveaway
# ══════════════════════════════════════════════════════════════════════
@tasks.loop(hours=24)
async def staff_salary_loop():
    """Salaire staff : 500/jour pour chaque membre staff actif."""
    db = connect()
    try:
        rows = db.execute("SELECT DISTINCT guild_id, user_id FROM users "
                          "WHERE staff_rank IS NOT NULL AND staff_rank!='' AND staff_rank!='None'").fetchall()
        for r in rows:
            db.execute("UPDATE users SET wallet=wallet+500 WHERE guild_id=? AND user_id=?",
                       (r["guild_id"], r["user_id"]))
            add_tx(db, r["guild_id"], r["user_id"], "salaire_staff", 500)
        db.commit()
    finally:
        db.close()

@bot.command(name="salaire", help="Voir le salaire staff du jour.")
async def salaire(ctx):
    g = ctx.guild
    db = connect()
    try:
        u = get_user(db, g.id, ctx.author.id)
        if not u["staff_rank"]:
            await ctx.send("❄ Tu n'es pas dans le staff."); return
        await ctx.send(f"💵 Salaire staff : **500/jour** (versé automatiquement).")
    finally:
        db.close()

@bot.command(name="chastaff", help="Transférer le ticket à un autre staff (staff). <membre>")
async def chastaff(ctx, member: discord.Member):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    await ctx.send(f"📩 Ticket transféré à **{member.display_name}**.")
    try:
        await member.send(f"📩 Un ticket a été transféré vers toi par {ctx.author}.")
    except Exception:
        pass

@bot.command(name="gwreroll", help="Reroll du dernier giveaway terminé (staff).")
async def gwreroll(ctx):
    if not mod_check(ctx):
        await ctx.send(q("no_perm")); return
    g = ctx.guild
    db = connect()
    try:
        gw = db.execute("SELECT * FROM giveaways WHERE guild_id=? AND status='done' "
                        "ORDER BY ends_at DESC LIMIT 1", (g.id,)).fetchone()
        if not gw:
            await ctx.send("❄ Aucun giveaway terminé à reroller."); return
        winners = db.execute(
            "SELECT user_id FROM giveaway_entries WHERE guild_id=? AND giveaway_msg=?",
            (g.id, gw["message_id"])).fetchall()
        if not winners:
            await ctx.send("❄ Aucun participant."); return
        w = random.choice(winners)["user_id"]
        db.execute("UPDATE giveaways SET status='rerolled' WHERE guild_id=? AND message_id=?",
                   (g.id, gw["message_id"]))
        db.commit()
        await ctx.send(f"🎁 Reroll : **<@{w}>** remporte **{gw['prize']}** !")
    except Exception:
        await ctx.send("❄ Reroll impossible pour l'instant.")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  J. ANIMAUX — dressage, reproduction, combat
# ══════════════════════════════════════════════════════════════════════
@bot.command(name="dresser", help="Dresser un animal (2 000 crédits, +10 force). <nom>")
async def dresser(ctx, name: str):
    g = ctx.guild
    db = connect()
    try:
        a = db.execute("SELECT * FROM animals WHERE guild_id=? AND user_id=? AND name=?",
                       (g.id, ctx.author.id, name)).fetchone()
        if not a:
            await ctx.send("❄ Animal introuvable."); return
        u = get_user(db, g.id, ctx.author.id)
        if u["wallet"] < 2000:
            await ctx.send("❌ Il te faut **2 000** crédits."); return
        db.execute("UPDATE users SET wallet=wallet-2000 WHERE guild_id=? AND user_id=?",
                   (g.id, ctx.author.id))
        db.execute("UPDATE animals SET power=power+10 WHERE guild_id=? AND user_id=? AND name=?",
                   (g.id, ctx.author.id, name))
        add_tx(db, g.id, ctx.author.id, "dressage", -2000)
        db.commit()
        await ctx.send(f"🏋️ **{name}** dressé ! Force : **{a['power']+10}**.")
    finally:
        db.close()

@bot.command(name="reproduire", help="Reproduire deux animaux (5 000, même espèce). <nom1> <nom2>")
async def reproduire(ctx, name1: str, name2: str):
    g = ctx.guild
    db = connect()
    try:
        a1 = db.execute("SELECT * FROM animals WHERE guild_id=? AND user_id=? AND name=?",
                        (g.id, ctx.author.id, name1)).fetchone()
        a2 = db.execute("SELECT * FROM animals WHERE guild_id=? AND user_id=? AND name=?",
                        (g.id, ctx.author.id, name2)).fetchone()
        if not a1 or not a2:
            await ctx.send("❄ Les deux animaux doivent exister."); return
        if a1["species"] != a2["species"]:
            await ctx.send("❄ Ils doivent être de la même espèce."); return
        u = get_user(db, g.id, ctx.author.id)
        if u["wallet"] < 5000:
            await ctx.send("❌ Il te faut **5 000** crédits."); return
        db.execute("UPDATE users SET wallet=wallet-5000 WHERE guild_id=? AND user_id=?",
                   (g.id, ctx.author.id))
        baby_name = f"Baby {name1[:6]}"
        baby_rarity = a1["rarity"] if random.random() < 0.5 else a2["rarity"]
        db.execute("INSERT OR REPLACE INTO animals (guild_id, user_id, name, species, rarity, power) "
                   "VALUES (?,?,?, ?,?,?)",
                   (g.id, ctx.author.id, baby_name, a1["species"], baby_rarity,
                    random.randint(5, 15)))
        add_tx(db, g.id, ctx.author.id, "reproduction", -5000)
        db.commit()
        await ctx.send(f"🐣 **{baby_name}** est né ! ({a1['species']}, {baby_rarity})")
    finally:
        db.close()

@bot.command(name="combat", help="Combat animal contre animal. <ton> <cible> <nom_cible>")
async def combat(ctx, my: str, member: discord.Member, their: str):
    g = ctx.guild
    db = connect()
    try:
        a1 = db.execute("SELECT * FROM animals WHERE guild_id=? AND user_id=? AND name=?",
                        (g.id, ctx.author.id, my)).fetchone()
        a2 = db.execute("SELECT * FROM animals WHERE guild_id=? AND user_id=? AND name=?",
                        (g.id, member.id, their)).fetchone()
        if not a1 or not a2:
            await ctx.send("❄ Un des deux animaux est introuvable."); return
        p1, p2 = a1["power"], a2["power"]
        if p1 > p2:
            await ctx.send(f"🏆 **{my}** ({p1}) bat **{their}** ({p2}) !")
        elif p2 > p1:
            await ctx.send(f"🏆 **{their}** ({p2}) bat **{my}** ({p1}) !")
        else:
            await ctx.send("🤝 Égalité !")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════
#  DÉMARRAGE
# ══════════════════════════════════════════════════════════════════════
def main():
    db = connect()
    init_db(db)
    init_db_complements(db)
    db.close()
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN manquant dans l'environnement.")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════════════


# COMMANDES SLASH (/) -- actions principales (complement des prefixes ! et +)
from discord import app_commands

@bot.tree.command(name="ping", description="Latence du bot Emilia Frost")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Pong ! **{round(bot.latency * 1000)} ms**", ephemeral=True)

@bot.tree.command(name="solde", description="Voir ton solde (ou celui d'un membre)")
@app_commands.describe(membre="Membre a consulter (optionnel)")
async def slash_solde(interaction: discord.Interaction, membre: discord.Member = None):
    m = membre or interaction.user
    db = connect()
    try:
        u = get_user(db, interaction.guild_id, m.id)
        e = frost_embed(title=f"Solde de {m.display_name}",
                        desc=f"Portefeuille : {fmt(u['wallet'])}  Banque : {fmt(u['bank'])}")
    finally:
        db.close()
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="daily", description="Recompense quotidienne")
async def slash_daily(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    ctx.author = interaction.user
    ctx.guild = bot.get_guild(interaction.guild_id)
    await daily(ctx)

@bot.tree.command(name="menu", description="Menu principal d'Emilia Frost")
async def slash_menu(interaction: discord.Interaction):
    e = frost_embed(title="Emilia Frost",
                    desc="Prefixes : ! (membres) + (staff/admin)\nTape !help pour la liste complete.")
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="profil", description="Voir ton profil (ou celui d'un membre)")
@app_commands.describe(membre="Membre a consulter (optionnel)")
async def slash_profil(interaction: discord.Interaction, membre: discord.Member = None):
    ctx = await bot.get_context(interaction)
    ctx.author = interaction.user
    ctx.guild = bot.get_guild(interaction.guild_id)
    await profil(ctx, membre)
