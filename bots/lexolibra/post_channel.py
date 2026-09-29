#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created by Erion Nezha — © 2026 All rights reserved
"""
Postim automatik ditor në kanalin Telegram "Lexo Libra" 📢

Ekzekutohet një herë në ditë nga planifikuesi i supervisor.py (brenda
shërbimit Render — jo si cron i veçantë, që të përdorë të njëjtat env vars).

Çdo ekzekutim zgjedh "librin e ditës" në mënyrë DETERMINISTE
(data Tirane: dita e vitit mod numri i librave — i njëjti libër për
ripërsëritje të së njëjtës ditë) dhe e poston në kanal:
  • foto kopertine (nëse ka URL valide), ose vetëm tekst
  • titull, autor, përshkrim i shkurtër
  • buton "📖 Hap në bot" me deep-link t.me/lexolibra_bot?start=book_<idx>

Indeksi <idx> është pozicioni në books_clean.json — i njëjti file që lexon
edhe bot.py, ndaj deep-link hap librin e saktë.

Sekretet merren VETËM nga variablat e ambientit:
  TELEGRAM_TOKEN — token-i i @lexolibra_bot (i njëjti si te bot.py)
  CHANNEL_ID     — kanali (default: @lexolibra)
Kurrë mos shkruaj token-in në kod apo file.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.request import HTTPXRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lexolibra-channel")
logging.getLogger("httpx").setLevel(logging.WARNING)

BASE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@lexolibra").strip()

with open(os.path.join(BASE, "books_clean.json"), encoding="utf-8") as f:
    BOOKS = json.load(f)


def tirana_today():
    """Data e sotme sipas orës së Tiranës (përzgjedhje deterministe)."""
    try:
        now = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Tirane"))
    except Exception:
        now = datetime.now(timezone.utc)
    return now


def cover_ok(url: str) -> bool:
    """Kopertinë valide = URL http(s) absolute, jo bosh/placeholder."""
    if not url or not url.startswith("http"):
        return False
    u = url.lower()
    return "placeholder" not in u and "noimage" not in u and "no_image" not in u


def book_of_the_day():
    """Deterministe: dita e vitit (Tiranë) mod numri i librave."""
    doy = tirana_today().timetuple().tm_yday
    idx = doy % len(BOOKS)
    return idx, BOOKS[idx]


def caption_for(idx: int, b: dict) -> str:
    titulli = b.get("t", "Pa titull")
    autori = b.get("a", "")
    pershkrimi = (b.get("s", "") or "").strip()
    if len(pershkrimi) > 600:
        pershkrimi = pershkrimi[:600].rsplit(" ", 1)[0] + "…"
    teksti = f"📚 <b>Libri i ditës</b>\n\n📖 <b>{titulli}</b>"
    if autori:
        teksti += f"\n✍️ {autori}"
    if pershkrimi:
        teksti += f"\n\n{pershkrimi}"
    teksti += "\n\n<i>përmes @lexolibra_bot 📚</i>"
    return teksti


async def main():
    if not TOKEN:
        raise SystemExit("Mungon TELEGRAM_TOKEN — vendose si variabël ambienti.")
    if not CHANNEL_ID:
        raise SystemExit("Mungon CHANNEL_ID — vendose si variabël ambienti.")

    idx, book = book_of_the_day()
    teksti = caption_for(idx, book)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 Hap në bot",
                            url=f"https://t.me/lexolibra_bot?start=book_{idx}")
    ]])
    kopertina = book.get("v") or ""

    req = HTTPXRequest(connect_timeout=25.0, read_timeout=40.0,
                       write_timeout=40.0, pool_timeout=10.0)
    from telegram import Bot
    bot = Bot(token=TOKEN, request=req)
    try:
        if cover_ok(kopertina):
            await bot.send_photo(chat_id=CHANNEL_ID, photo=kopertina,
                                 caption=teksti, parse_mode="HTML",
                                 reply_markup=kb)
        else:
            await bot.send_message(chat_id=CHANNEL_ID, text=teksti,
                                   parse_mode="HTML", reply_markup=kb,
                                   disable_web_page_preview=True)
        log.info("U postua libri i ditës: #%d %s", idx, book.get("t"))
    except Exception:
        # Mos loggo kurrë token-in apo përmbajtje sensitive
        log.error("Postimi dështoi")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
