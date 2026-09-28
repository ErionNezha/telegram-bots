#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created by Erion Nezha — © 2026 All rights reserved
"""
Dertli Bot — versioni Telegram 💬
Thin client mbi funksionin Netlify: dërgon mesazhin e përdoruesit me POST
në https://dertlibot.netlify.app/.netlify/functions/chat dhe kthen përgjigjen.

RREGULLA:
  - Kurrë mos i zbulo përdoruesit provider-in (CodeCraft/Gemini) —
    boti sillet thjesht si Dertli Bot.
  - Funksioni ka rate limit 30 kërkesa/orë për IP dhe të gjithë userët e
    Telegramit ndajnë IP-në e serverit. Prandaj zbatohet:
      • cooldown 25 sekonda për çdo përdorues
      • maksimum ~25 mesazhe/orë për çdo përdorues
    me mesazh miqësor në shqip kur kufiri kapet.

Sekreti merret VETËM nga variabla e ambientit:
  DERTLI_TG_TOKEN — token-i nga @BotFather (i detyrueshëm)
Kurrë mos shkruaj token-in në kod apo file.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone

import httpx
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dertli-tg")
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

TOKEN = os.environ.get("DERTLI_TG_TOKEN", "").strip()
CHAT_URL = "https://dertlibot.netlify.app/.netlify/functions/chat"

# Kufijtë tanë (më striktë se 30/orë e funksionit, sepse IP-ja ndahet):
COOLDOWN_S = 25          # sekonda midis dy mesazheve të të njëjtit user
HOURLY_MAX = 25          # mesazhe maksimum për user brenda 1 ore
HISTORY_MAX = 10         # ruajmë max 10 mesazhe histori për kontekst
MSG_MAX_LEN = 1500       # funksioni pret mesazhe deri ~2000 karaktere

HIST_FILE = os.path.join(DATA_DIR, "history.json")
LIMITS_FILE = os.path.join(DATA_DIR, "limits.json")

SYSTEM_PROMPT = (
    "Je Dertli Bot, një asistent virtual miqësor dhe i dobishëm. "
    "Përgjigju gjithmonë në gjuhën shqipe, qartë dhe shkurt. "
    "Nëse nuk e di diçka, thuaje sinqerisht. "
    "Kurrë mos përmend se cili shërbim AI po përgjigjet pas skenave."
)


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


def check_limits(user_id: int):
    """Kthen (ok: bool, arsye: str|None). Përditëson gjurmimin e dërgimeve."""
    now = time.time()
    limits = _load(LIMITS_FILE, {})
    u = str(user_id)
    rec = limits.get(u, {"last": 0, "times": []})
    # Pastro dërgimet më të vjetra se 1 orë
    rec["times"] = [t for t in rec.get("times", []) if now - t < 3600]
    if now - rec.get("last", 0) < COOLDOWN_S:
        wait = int(COOLDOWN_S - (now - rec["last"]))
        return False, f"⏳ Prit {wait} sekonda para mesazhit tjetër, të lutem."
    if len(rec["times"]) >= HOURLY_MAX:
        return False, (
            "⏳ Ke arritur kufirin e mesazheve për këtë orë. "
            "Pusho pak dhe provo përsëri më vonë."
        )
    rec["last"] = now
    rec["times"].append(now)
    limits[u] = rec
    _save(LIMITS_FILE, limits)
    return True, None


def get_history(user_id: int):
    return _load(HIST_FILE, {}).get(str(user_id), [])


def push_history(user_id: int, role: str, content: str):
    hist = _load(HIST_FILE, {})
    h = hist.get(str(user_id), [])
    h.append({"role": role, "content": content[:MSG_MAX_LEN]})
    hist[str(user_id)] = h[-HISTORY_MAX:]
    _save(HIST_FILE, hist)


def clear_history(user_id: int):
    hist = _load(HIST_FILE, {})
    hist.pop(str(user_id), None)
    _save(HIST_FILE, hist)


async def ask_dertli(history: list) -> tuple:
    """Thërret funksionin Netlify. Kthen (reply | None, error_msg | None)."""
    payload = {"messages": history, "systemPrompt": SYSTEM_PROMPT}
    try:
        async with httpx.AsyncClient(timeout=60.0,
                                     verify=_HTTPX_KWARGS.get("verify", True)) as cli:
            r = await cli.post(CHAT_URL, json=payload)
    except Exception as e:
        log.warning("POST dështoi: %s", type(e).__name__)
        return None, "lidhja"
    try:
        data = r.json()
    except Exception:
        data = {}
    if r.status_code == 429:
        return None, "shume"
    if r.status_code != 200:
        log.warning("chat.js ktheu %s", r.status_code)
        return None, "gabim"
    reply = (data.get("reply") or "").strip()
    if not reply:
        return None, "bosh"
    return reply, None


FRIENDLY_ERRORS = {
    "lidhja": "😕 S'munda të lidhem dot tani. Provo përsëri pas pak.",
    "shume": "⏳ Shumë kërkesa në këtë moment — pusho pak dhe provo përsëri.",
    "gabim": "😕 Ndodhi një problem i përkohshëm. Provo përsëri pas pak.",
    "bosh": "😕 S'mora përgjigje. Provo ta riformulosh pyetjen.",
}


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Përshëndetje! Unë jam <b>Dertli Bot</b> — asistenti yt virtual.\n\n"
        "Më shkruaj çfarë të duash dhe do të përgjigjem në shqip. 🇦🇱\n\n"
        "Komandat:\n"
        "• /ndihme — si të më përdorësh\n"
        "• /pastro — fshin historinë e bisedës sonë",
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💡 <b>Si të më përdorësh</b>\n\n"
        "Thjesht më dërgo një mesazh — pyetje, kërkesë apo bisedë — "
        "dhe unë të përgjigjem.\n\n"
        "• Mbaj mend kontekstin e bisedës (10 mesazhet e fundit).\n"
        "• /pastro — fillon bisedë të re (harroj çfarë folëm).\n"
        "• Ka një kufi të vogël shpejtësie që të mos mbingarkohet "
        "shërbimi — nëse të del ⏳, prit pak dhe provo sërish.",
        parse_mode="HTML",
    )


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_user.id)
    await update.message.reply_text("🧹 Historia u fshi — fillojmë nga e para! Çfarë të ndihmoj?")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()
    if not text:
        return
    if len(text) > MSG_MAX_LEN:
        await update.message.reply_text(
            "✂️ Mesazhi yt është pak i gjatë — provo ta shkurtosh (max ~1500 karaktere)."
        )
        return

    ok, reason = check_limits(user.id)
    if not ok:
        await update.message.reply_text(reason)
        return

    history = get_history(user.id) + [{"role": "user", "content": text}]
    history = history[-HISTORY_MAX:]

    await update.message.chat.send_action(ChatAction.TYPING)
    reply, err = await ask_dertli(history)
    if err:
        await update.message.reply_text(FRIENDLY_ERRORS[err])
        return

    push_history(user.id, "user", text)
    push_history(user.id, "assistant", reply)
    # Telegram-i pret max 4096 karaktere për mesazh — ndajmë nëse duhet
    for i in range(0, len(reply), 4000):
        await update.message.reply_text(reply[i:i + 4000])


def main():
    if not TOKEN:
        raise SystemExit("Mungon DERTLI_TG_TOKEN — vendose si variabël ambienti.")
    req = HTTPXRequest(connect_timeout=25.0, read_timeout=40.0,
                       write_timeout=40.0, pool_timeout=10.0,
                       httpx_kwargs=_HTTPX_KWARGS)
    app = Application.builder().token(TOKEN).request(req).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ndihme", cmd_help))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("pastro", cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    log.info("Dertli Bot (Telegram) u ndez.")
    app.run_polling(bootstrap_retries=100, poll_interval=2.0)


if __name__ == "__main__":
    main()
