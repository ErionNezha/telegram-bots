#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created by Erion Nezha — © 2026 All rights reserved
"""
Lexo Libra — Telegram Bot 📚 PREMIUM
Katalogu i plotë i bibliotekës shqiptare brenda Telegram-it.

Funksionet:
  🔍 Kërkim i zgjuar (tolerant ndaj ë/ç)
  🎲 Libri i ditës (i njëjtë për të gjithë)
  🆕 10 librat më të rinj
  ⭐ Të preferuarat (ruhen për çdo përdorues)
  🔊 Dëgjo përmbledhjen (zë neural shqip, MP3)
  👤 Biografi autori
  📩 Kërko titull → njoftim direkt te administratori
  📊 /stats — statistika vetëm për adminin

Sekretet merren VETËM nga variablat e ambientit:
  TELEGRAM_TOKEN — token-i nga @BotFather (i detyrueshëm)
  ADMIN_ID       — ID-ja numerike e administratorit (për njoftime + /stats)
Kurrë mos shkruaj token-in në kod apo file.
"""
import json
import logging
import os
import random
import unicodedata
from datetime import date

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lexolibra-bot")
# Mos loggo URL-të e API-t (përmbajnë token-in)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Fortësi ndaj ambientit: httpx thyhet me hyrje IPv6 si [::1] në no_proxy,
# dhe proxy-ja e daljes bën TLS-interception (duhet CA-ja e saj).
for _var in ("no_proxy", "NO_PROXY"):
    _val = os.environ.get(_var, "")
    if "[" in _val:
        os.environ[_var] = ",".join(p for p in _val.split(",") if "[" not in p)
_CA = os.environ.get("SSL_CERT_FILE", "")
_HTTPX_KWARGS = {"verify": _CA} if _CA and os.path.isfile(_CA) else {}

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(DATA_DIR, exist_ok=True)

with open(os.path.join(BASE, "books_clean.json"), encoding="utf-8") as f:
    BOOKS = json.load(f)
with open(os.path.join(BASE, "author_bios.json"), encoding="utf-8") as f:
    BIOS = json.load(f)

TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or 0)

FAVS_FILE = os.path.join(DATA_DIR, "favs.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")

ASK_TITLE = 1


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def get_favs():
    return _load(FAVS_FILE, {})


def get_stats():
    return _load(STATS_FILE, {"users": [], "searches": {}, "opens": {}})


def norm(s: str) -> str:
    """Lowercase + heq thekset (ë→e, ç→c) për kërkim tolerant."""
    s = unicodedata.normalize("NFD", s or "").lower()
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def search_books(query: str, limit: int = 8):
    q = norm(query)
    if len(q) < 2:
        return []
    hits = []
    for i, b in enumerate(BOOKS):
        hay = norm(f"{b.get('t', '')} {b.get('a', '')}")
        if q in hay:
            score = 0 if norm(b.get("t", "")).startswith(q) else 1
            hits.append((score, i, b))
    hits.sort(key=lambda x: (x[0], norm(x[2].get("t", ""))))
    return [(i, b) for _, i, b in hits[:limit]]


AUDIO_CACHE = os.path.join(BASE, "audio_cache")
os.makedirs(AUDIO_CACHE, exist_ok=True)
AUDIO_BASE_URL = os.environ.get(
    "AUDIO_BASE_URL", "https://lexolibra.netlify.app/audio").rstrip("/")
try:
    with open(os.path.join(BASE, "audio_manifest.json"), encoding="utf-8") as _mf:
        AUDIO_MANIFEST = set(json.load(_mf).get("files", []))
except Exception:
    AUDIO_MANIFEST = set()


def audio_available(idx: int) -> bool:
    """A ka audio për këtë libër (pa shkarkuar asgjë)."""
    return f"b{idx:04d}.mp3" in AUDIO_MANIFEST


def audio_path(idx: int):
    """Kthen rrugën lokale të MP3-së; e shkarkon nga sajti herën e parë."""
    name = f"b{idx:04d}.mp3"
    if name not in AUDIO_MANIFEST:
        return None
    p = os.path.join(AUDIO_CACHE, name)
    if os.path.isfile(p):
        return p
    try:
        import urllib.request
        urllib.request.urlretrieve(f"{AUDIO_BASE_URL}/{name}", p)
        return p if os.path.isfile(p) else None
    except Exception:
        return None


def book_caption(b) -> str:
    parts = [f"📖 *{b.get('t', 'Pa titull')}*"]
    if b.get("a"):
        parts.append(f"✍️ {b['a']}")
    if b.get("c"):
        parts.append(f"🏷️ {b['c']}")
    if b.get("s"):
        parts.append(f"\n{b['s']}")
    return "\n".join(parts)


def book_keyboard(idx: int, user_id: int = 0) -> InlineKeyboardMarkup:
    b = BOOKS[idx]
    kb = []
    row1 = []
    if b.get("l"):
        row1.append(InlineKeyboardButton("⬇️ Shkarko librin", url=b["l"]))
    if audio_available(idx):
        row1.append(InlineKeyboardButton("🔊 Dëgjo", callback_data=f"audio:{idx}"))
    if row1:
        kb.append(row1)
    row2 = []
    if b.get("a") and b["a"] in BIOS:
        row2.append(InlineKeyboardButton("👤 Autori", callback_data=f"bio:{idx}"))
    favs = get_favs().get(str(user_id), []) if user_id else []
    row2.append(InlineKeyboardButton(
        "⭐ Hiq nga të preferuarat" if idx in favs else "⭐ Preferuar",
        callback_data=f"fav:{idx}",
    ))
    kb.append(row2)
    kb.append([InlineKeyboardButton("🎲 Sugjerim tjetër", callback_data="random:")])
    kb.append([InlineKeyboardButton("🆘 Ndihmë", url="https://t.me/lexolibra_help_bot")])
    return InlineKeyboardMarkup(kb)


def track_open(idx: int, user_id: int):
    st = get_stats()
    st["opens"][str(idx)] = st["opens"].get(str(idx), 0) + 1
    if user_id and user_id not in st["users"]:
        st["users"].append(user_id)
    _save(STATS_FILE, st)


def track_search(query: str, user_id: int):
    st = get_stats()
    q = query.strip()[:60]
    st["searches"][q] = st["searches"].get(q, 0) + 1
    if user_id and user_id not in st["users"]:
        st["users"].append(user_id)
    _save(STATS_FILE, st)


async def send_book(chat_id, idx: int, context: ContextTypes.DEFAULT_TYPE,
                   intro: str = "", user_id: int = 0):
    b = BOOKS[idx]
    caption = (intro + "\n\n" if intro else "") + book_caption(b)
    try:
        if b.get("v"):
            await context.bot.send_photo(
                chat_id, photo=b["v"], caption=caption,
                parse_mode="Markdown", reply_markup=book_keyboard(idx, user_id),
            )
        else:
            raise ValueError("no cover")
    except Exception as e:
        log.warning("photo failed for #%d: %s", idx, e)
        await context.bot.send_message(
            chat_id, caption, parse_mode="Markdown",
            reply_markup=book_keyboard(idx, user_id),
        )


MENU = ReplyKeyboardMarkup(
    [
        ["🔍 Kërko libër", "🎲 Libri i ditës"],
        ["🆕 Libra të rinj", "⭐ Të preferuarat"],
        ["📩 Kërko një titull", "ℹ️ Ndihmë"],
        ["🆘 Ndihmë", "📢 Kanali"],
    ],
    resize_keyboard=True,
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    st = get_stats()
    if uid not in st["users"]:
        st["users"].append(uid)
        _save(STATS_FILE, st)
    # Deep-link nga rezultatet inline: /start book_<idx>
    if context.args and context.args[0].startswith("book_"):
        try:
            idx = int(context.args[0].split("_", 1)[1])
            if 0 <= idx < len(BOOKS):
                track_open(idx, uid)
                await send_book(update.effective_chat.id, idx, context,
                                intro="📖 Ja libri që zgjodhe:", user_id=uid)
                return
        except (ValueError, IndexError):
            pass
    name = update.effective_user.first_name or "lexues"
    await update.message.reply_text(
        f"📚 Mirë se vjen, {name}!\n\n"
        f"Unë jam asistenti i *Lexo Libra* — kam {len(BOOKS)} libra shqip gati për ty.\n\n"
        "🔍 Kërko me titull ose autor\n"
        "🔊 Dëgjo përmbledhjen me zë shqip\n"
        "🎲 Merr sugjerimin e ditës\n"
        "⭐ Ruaj të preferuarat e tua\n"
        "📩 Kërko një titull që s'e gjete",
        parse_mode="Markdown",
        reply_markup=MENU,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Si përdoret boti*\n\n"
        "• Shkruaj thjesht titullin ose autorin — p.sh. `Kadare` ose `Princi i Vogel`\n"
        "• Te çdo libër ke: ⬇️ shkarkim, 🔊 dëgjim, ⭐ preferuar, 👤 biografi autori\n"
        "• Me 📩 kërkon një titull që mungon — na vjen njoftim direkt\n"
        "• Me ⭐ Të preferuarat i gjen librat që ke ruajtur",
        parse_mode="Markdown",
        reply_markup=MENU,
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or not ADMIN_ID:
        await update.message.reply_text("⛔ Kjo komandë është vetëm për administratorin.")
        return
    st = get_stats()
    top_search = sorted(st["searches"].items(), key=lambda x: -x[1])[:5]
    top_books = sorted(st["opens"].items(), key=lambda x: -x[1])[:5]
    lines = [
        "📊 *Statistikat e botit*",
        f"👥 Përdorues unikë: {len(st['users'])}",
        f"🔍 Kërkime gjithsej: {sum(st['searches'].values())}",
        f"📖 Hapje librash: {sum(st['opens'].values())}",
    ]
    if top_search:
        lines.append("\n*Top kërkimet:*")
        lines += [f"• {q} — {c}x" for q, c in top_search]
    if top_books:
        lines.append("\n*Top librat:*")
        for idx_s, c in top_books:
            t = BOOKS[int(idx_s)].get("t", "?")
            lines.append(f"• {t} — {c}x")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def on_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    uid = update.effective_user.id
    chat_id = update.effective_chat.id

    if text == "🔍 Kërko libër":
        await update.message.reply_text("✏️ Shkruaj titullin ose autorin që kërkon:")
        return
    if text == "🎲 Libri i ditës":
        rnd = random.Random(date.today().isoformat())
        idx = rnd.randrange(len(BOOKS))
        track_open(idx, uid)
        await send_book(chat_id, idx, context, intro="🎲 *Libri i ditës*", user_id=uid)
        return
    if text == "🆕 Libra të rinj":
        newest = list(range(len(BOOKS) - 1, max(len(BOOKS) - 11, -1), -1))
        kb = [[InlineKeyboardButton(
            f"📖 {BOOKS[i].get('t', '?')} — {BOOKS[i].get('a', '?')}",
            callback_data=f"book:{i}")] for i in newest]
        await update.message.reply_text(
            "🆕 *10 librat më të rinj në bibliotekë:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return
    if text == "⭐ Të preferuarat":
        favs = get_favs().get(str(uid), [])
        if not favs:
            await update.message.reply_text(
                "⭐ S'ke ruajtur ende asnjë libër.\nHap një libër dhe shtyp *⭐ Preferuar*.",
                parse_mode="Markdown", reply_markup=MENU,
            )
            return
        kb = [[InlineKeyboardButton(
            f"📖 {BOOKS[i].get('t', '?')} — {BOOKS[i].get('a', '?')}",
            callback_data=f"book:{i}")] for i in favs if 0 <= i < len(BOOKS)]
        await update.message.reply_text(
            f"⭐ *Të preferuarat e tua* ({len(kb)}):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return
    if text == "ℹ️ Ndihmë":
        await cmd_help(update, context)
        return
    if text == "🆘 Ndihmë":
        await update.message.reply_text(
            "🆘 *Ke nevojë për ndihmë?*\n\n"
            "Boti i ndihmës të përgjigjet për pyetjet e shpeshta, "
            "ose na e dërgon problemin direkt neve:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🆘 Hap botin e ndihmës",
                                    url="https://t.me/lexolibra_help_bot")
            ]]),
        )
        return
    if text == "📢 Kanali":
        await update.message.reply_text(
            "📢 *Kanali ynë në Telegram*\n\n"
            "Aty postojmë çdo ditë librin e ditës dhe të rejat e bibliotekës:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 Hap kanalin @lexolibra",
                                    url="https://t.me/lexolibra")
            ]]),
        )
        return
    if text == "📩 Kërko një titull":
        return  # e kap ConversationHandler-i

    # çdo tekst tjetër = kërkim
    hits = search_books(text)
    track_search(text, uid)
    if not hits:
        await update.message.reply_text(
            f"😕 S'gjetëm asgjë për \"{text}\".\n"
            "Provo me më pak fjalë, ose kërkoje me 📩 dhe e shtojmë!",
            reply_markup=MENU,
        )
        return
    if len(hits) == 1:
        idx = hits[0][0]
        track_open(idx, uid)
        await send_book(chat_id, idx, context, user_id=uid)
        return
    kb = [[InlineKeyboardButton(
        f"📖 {b.get('t', '?')} — {b.get('a', '?')}",
        callback_data=f"book:{i}")] for i, b in hits]
    await update.message.reply_text(
        f"🔎 Gjetëm {len(hits)} rezultate për \"{text}\" — zgjidh:",
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    uid = q.from_user.id
    chat_id = q.message.chat_id

    if data.startswith("book:"):
        idx = int(data.split(":")[1])
        track_open(idx, uid)
        await send_book(chat_id, idx, context, user_id=uid)
    elif data.startswith("bio:"):
        idx = int(data.split(":")[1])
        author = BOOKS[idx].get("a", "")
        bio = BIOS.get(author, "S'ka biografi për këtë autor.")
        await q.message.reply_text(f"👤 *{author}*\n\n{bio}", parse_mode="Markdown")
    elif data.startswith("audio:"):
        idx = int(data.split(":")[1])
        p = audio_path(idx)
        if not p:
            await q.message.reply_text("🔇 S'ka audio për këtë libër.")
            return
        title = BOOKS[idx].get("t", "Përmbledhja")
        await context.bot.send_audio(
            chat_id, audio=open(p, "rb"),
            title=f"Përmbledhja — {title}",
            caption=f"🔊 *Përmbledhja e librit*\n📖 {title}",
            parse_mode="Markdown",
        )
    elif data.startswith("fav:"):
        idx = int(data.split(":")[1])
        favs = get_favs()
        mine = favs.get(str(uid), [])
        if idx in mine:
            mine.remove(idx)
            msg = "💔 U hoq nga të preferuarat."
        else:
            mine.append(idx)
            msg = "⭐ U shtua te të preferuarat!"
        favs[str(uid)] = mine
        _save(FAVS_FILE, favs)
        await q.answer(msg, show_alert=False)
        try:
            await q.message.edit_reply_markup(reply_markup=book_keyboard(idx, uid))
        except Exception:
            pass
    elif data == "random:":
        idx = random.randrange(len(BOOKS))
        track_open(idx, uid)
        await send_book(chat_id, idx, context, intro="🎲 *Sugjerim*", user_id=uid)


# ---- Kërkesa për titull të ri ----
async def req_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📩 Shkruaj titullin e librit që kërkon (dhe autorin nëse e di).\n"
        "Kërkesa shkon direkt te administratori. Shkruaj /anulo për të dalë."
    )
    return ASK_TITLE


async def req_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = (update.message.text or "").strip()
    user = update.effective_user
    uname = f"@{user.username}" if user.username else f"{user.first_name} (id {user.id})"
    if ADMIN_ID:
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"📩 *Kërkesë e re libri*\n\n📖 {title}\n👤 Nga: {uname}",
                parse_mode="Markdown",
            )
        except Exception as e:
            log.warning("admin notify failed: %s", e)
    await update.message.reply_text(
        "✅ Kërkesa u dërgua! Do të njoftohesh sapo libri të shtohet në bibliotekë. 📚",
        reply_markup=MENU,
    )
    return ConversationHandler.END


async def req_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("U anulua.", reply_markup=MENU)
    return ConversationHandler.END


async def on_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kërkim inline: @lexolibra_bot <titull/autor> nga çdo chat."""
    q = (update.inline_query.query or "").strip()
    uid = update.inline_query.from_user.id
    if len(norm(q)) >= 2:
        track_search("inline: " + q[:50], uid)
    hits = search_books(q, limit=20) if len(norm(q)) >= 2 else []
    results = []
    for idx, b in hits:
        title = b.get("t", "Pa titull")
        author = b.get("a", "")
        desc = b.get("s", "")[:120]
        text = f"📖 <b>{title}</b>"
        if author:
            text += f"\n✍️ {author}"
        if b.get("s"):
            text += f"\n\n{b['s'][:300]}"
        text += "\n\n<i>përmes @lexolibra_bot 📚</i>"
        kb = [[InlineKeyboardButton("📖 Hap te bota",
                                   url=f"https://t.me/lexolibra_bot?start=book_{idx}")]]
        if b.get("l"):
            kb[0].append(InlineKeyboardButton("⬇️ Shkarko", url=b["l"]))
        results.append(InlineQueryResultArticle(
            id=f"book{idx}",
            title=title,
            description=(f"{author} — " if author else "") + desc,
            thumbnail_url=b.get("v") or None,
            input_message_content=InputTextMessageContent(
                text, parse_mode="HTML", disable_web_page_preview=True),
            reply_markup=InlineKeyboardMarkup(kb),
        ))
    await update.inline_query.answer(results, cache_time=300)


def main():
    if not TOKEN:
        raise SystemExit("Mungon TELEGRAM_TOKEN — vendose si variabël ambienti.")
    # Timeout-e të gjera: lidhja kalon përmes proxy-t të daljes që është e ngadaltë
    req = HTTPXRequest(connect_timeout=25.0, read_timeout=40.0,
                       write_timeout=40.0, pool_timeout=10.0,
                       httpx_kwargs=_HTTPX_KWARGS)
    app = Application.builder().token(TOKEN).request(req).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📩 Kërko një titull$"), req_start)],
        states={ASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, req_received)]},
        fallbacks=[CommandHandler("anulo", req_cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ndihme", cmd_help))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_menu))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(InlineQueryHandler(on_inline_query))

    log.info("Lexo Libra bot u ndez — %d libra në katalog.", len(BOOKS))
    # bootstrap_retries: proxy-ja e daljes i këput lidhjet herë pas here,
    # prandaj lejojmë shumë riprovime në fazën e nisjes.
    app.run_polling(bootstrap_retries=100, poll_interval=2.0)


if __name__ == "__main__":
    main()
