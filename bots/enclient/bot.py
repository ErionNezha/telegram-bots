#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created by Erion Nezha — © 2026 All rights reserved
"""
ERION NEZHA — PRIVATE CLIENTS 🔐
Bot privat Telegram për klientë, me akses VETËM me kod unik personal.

Rrjedha:
- Linku në bio të Instagramit (@erjonixx) mund të hapet nga kushdo, por
  brenda shfaqet vetëm ekrani i kyçjes — asnjë shërbim, çmim apo kontakt.
- KOD UNIK: admini krijon kod për klientin (/krijo_kod) dhe ia jep në DM.
  Kodi lidhet me llogarinë Telegram të klientit në përdorimin e parë;
  përcjellja te dikush tjetër nuk punon. Afati default 30 ditë.
- PA KOD: vizitori zgjedh "Kërkoj shërbim", plotëson 3 hapa dhe kërkesa
  i vjen adminit me ✅/❌. Miratimi e aktivizon klientin drejtpërdrejt.
- 3 kode të gabuara brenda 15 min → kyçje 60 min + njoftim te admini.

Pas zhbllokimit (klient): shërbimet, shembuj pune me kategori, FAQ,
vlerësime, CV-ja si dokument, formulari i projektit (brief), gjurmimi
i projektit ("Projekti im"), rezervimi i konsultave, bisedë direkte
me Erionin (relay dykahësh me tekst + media), kartvizita (+ imazh me
QR), /akses. E GJITHA kjo mbetet në zonën private — vizitori i kyçur
sheh vetëm ekranin e derës.

Një detyrë në sfond (post_init, çdo ~30 min) dërgon kujtesat: për
konsultat e miratuara që nisin brenda 3 orëve dhe për klientët, afati
i të cilëve skadon brenda 3 ditëve (klientin + përmbledhje te admini).

Paketa 1–6 (2026-10-22):
  F1 vlerësime automatike pas dorëzimit (yje + koment opsional,
     miratim i adminit para publikimit) — /vleresime
  F2 miratimi i konsultës dërgon file .ics + buton Google Calendar
  F3 ndërfaqe dygjuhëshe (SQ/EN): zgjedhja te dera (🇦🇱/🇬🇧) dhe te
     menyja (🌍 Gjuha / Language); ruhet për përdorues, kalon në
     regjistrin e klientit pas aktivizimit
  F4 propozim paraprak PDF pas brief-it (stdlib, pa çmime/shuma)
  F5 mesazh zanor mirëseardhjeje pas çdo aktivizimi të ri
  F6 raport javor automatik (të hënën) + /raport sipas kërkesës

Komandat e adminit (vetëm ADMIN_ID):
  /krijo_kod [ditë] [shënim]   /kodet   /klientet
  /revoko <user_id>            /zgjat <user_id> [ditë]   /panel
  /backup                      (vetëm admin; NUK është në menunë publike)
  /statusi [teksti]            (statusi i disponueshmërisë për klientët)
  /projekt <user_id> <titulli> /faza <user_id> <faza>
  /shenim_projekti <user_id> <teksti>   /projekt_fund <user_id>
  /slot <YYYY-MM-DD> <HH:MM>   /slotet   /slot_fshi <slot_id>
  /njoftim <teksti>            (broadcast te klientët aktivë)
  /pergjigju <user_id>         (përgjigja tjetër i shkon klientit)
  /vleresime                   (vlerësimet në pritje — publiko/refuzo)
  /mireseardhje                /hiq_mireseardhjen   (zëri i mirëseardhjes)
  /raport                      (raporti javor sipas kërkesës)
  /marreveshje <user_id>       (paketa 3: marrëveshja dixhitale)
  /orari <HH:MM-HH:MM>         (paketa 3: orari i punës)
  /orari_fundjave on|off       (paketa 3: fundjava në orar pune)

Paketa 4 (2026-10-23):
  roja javore e linkeve (WORKS/WORKS_EN + Web App — hesht kur
  gjithçka punon), veprimet një-prekje të adminit mbi njoftimin e
  brief-it (krijo projekt / dërgo marrëveshje / përgjigju; brief-et
  ruhen me id), dosja e klientit /dosja + shënimet private
  /shenim_klienti, turi udhëzues i klientit të ri (🧭 Udhëzuesi),
  anulimi i rezervimit nga vetë klienti, butoni 🏠 Kreu te
  "Më shumë" dhe kujtesa e mëngjesit për pikat në pritje > 24 orë.

Paketa 3 (2026-10-22):
  menu e thjeshtuar (kryesore + "☰ Më shumë"), galeria vizuale e
  punëve (album me pamje reale nga assets/gallery/), butoni i Mini
  Web App-it te faqja kryesore e klientit, marrëveshja dixhitale e
  bashkëpunimit (pranim me buton + PDF për të dyja palët) dhe orari
  i punës me përgjigje automatike jashtë orarit (maks. 1/ditë).

Sekretet VETËM nga ambienti / .env (kurë në kod):
  CLIENT_BOT_TOKEN  — token-i nga @BotFather (i detyrueshëm)
  ADMIN_ID          — ID-ja numerike e Erionit (default: 1318275745)
  ENCLIENT_DATA     — rruga e data.json (opsionale)
"""
import asyncio
import html
import io
import logging
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    TIRANA = ZoneInfo("Europe/Tirane")
except Exception:  # pa tzdata — përafërsi fikse (si te supervisor-i)
    TIRANA = timezone(timedelta(hours=2))

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

# .env loader (Botkeep nuk injekton variabla; i lexojmë vetë, stdlib).
# Variablat reale të ambientit kanë gjithmonë përparësi (setdefault).
_envf = os.path.join(BASE, ".env")
if os.path.isfile(_envf):
    try:
        with open(_envf, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
    except OSError:
        pass

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from store import PROJECT_STAGES, Store, normalize_code, parse_iso

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("en-private-clients")
logging.getLogger("httpx").setLevel(logging.WARNING)

# Fortësi ndaj ambientit (si te botët e tjerë): proxy/IPv6 + CA e saj.
for _var in ("no_proxy", "NO_PROXY"):
    _val = os.environ.get(_var, "")
    if "[" in _val:
        os.environ[_var] = ",".join(p for p in _val.split(",") if "[" not in p)
_CA = os.environ.get("SSL_CERT_FILE", "")
_HTTPX_KWARGS = {"verify": _CA} if _CA and os.path.isfile(_CA) else {}

TOKEN = os.environ.get("CLIENT_BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1318275745") or 1318275745)
DATA_PATH = os.environ.get("ENCLIENT_DATA", os.path.join(BASE, "data.json"))
store = Store(DATA_PATH)

DEFAULT_DAYS = 30


# ---------------------------------------------------------------- auditi 360°
def _esc(s) -> str:
    """Shpëtim HTML për përmbajtjen e kontrolluar nga përdoruesi që
    futet në mesazhe parse_mode='HTML' (emra, përshkrime, tituj...).
    Pa këtë, një '<3' ose '<b>' i klientit e rrëzonte dërgimin me
    BadRequest ose injektonte formatim (D19)."""
    if s is None:
        return ""
    return html.escape(str(s), quote=False)


def _safe_int(v, default: int = 0) -> int:
    """int() i sigurt: vlera të korruptuara ('five', '²', vargje me
    mijëra shifra) kthejnë default-in në vend që të rrëzojnë pamjen
    (D8/D11)."""
    try:
        return int(v)
    except (TypeError, ValueError, OverflowError):
        return default


def _trunc(s, n: int) -> str:
    """Shkurton tekstin e gjatë të përdoruesit për njoftimet e adminit,
    që mesazhi të mos kalojë kufirin 4096 të Telegramit dhe të mos
    humbasë bashkë me butonat e veprimit (D12)."""
    s = str(s or "")
    return s[:n].rstrip() + "…" if len(s) > n else s

SERVICES = [
    ("web", "🌐 Faqe interneti & e-commerce"),
    ("app", "📱 Aplikacion Android"),
    ("bot", "🤖 Bot Telegram & automatizim"),
    ("design", "🎨 Dizajn grafik & video"),
    ("marketing", "📣 Marketing dixhital"),
    ("other", "✨ Tjetër"),
]
SERVICE_NAMES = dict(SERVICES)

SERVICE_DETAILS = {
    "web": "🌐 <b>Faqe interneti & e-commerce</b>\nFaqe prezantuese, dyqan online, faqe rezervimesh apo platformë me porosi — dizajn premium, e shpejtë, e optimizuar për Google dhe për telefon.",
    "app": "📱 <b>Aplikacion Android</b>\nNga ideja te publikimi në Google Play: dizajn, zhvillim, testime dhe dorëzim i plotë i aplikacionit tënd.",
    "bot": "🤖 <b>Bot Telegram & automatizim</b>\nBotë për biznesin tënd (porosi, njoftime, mbështetje klientësh) dhe automatizime që të kursejnë orë pune çdo javë.",
    "design": "🎨 <b>Dizajn grafik & video</b>\nLogo dhe identitet vizual, grafika për rrjete sociale e dyqane aplikacionesh, editim videoje me titra të animuara.",
    "marketing": "📣 <b>Marketing dixhital</b>\nStrategji përmbajtjeje, menaxhim prezence online dhe fushata që sjellin klientë realë, jo thjesht shikime.",
    "other": "✨ <b>Tjetër</b>\nKe një ide tjetër në mendje? Tregoje me formularin e projektit dhe e diskutojmë bashkë.",
}

# Buxhetet: vetëm cilësore, PA shifra (urdhër i përdoruesit: "mos vendos shifra").
BUDGETS = ["Modest", "Mesatar", "Serioz", "Ende nuk e di"]

# Shembujt e punës — me kategori (vetëm zonë private e klientit).
WORK_CATEGORIES = [
    ("apps", "📱 Aplikacione mobile"),
    ("web", "🌐 Platforma web"),
    ("ai", "🤖 Botë & AI"),
]
WORKS = {
    "apps": [
        ("📺 ERION TV — aplikacioni IPTV", "https://play.google.com/store/apps/details?id=com.streamvision.app"),
        ("📡 Dream TV AL — TV live e filma në telefon", "https://play.google.com/store/apps/details?id=blackmaster.ex"),
        ("🎵 Radio Shqip — radiot shqiptare live", "https://play.google.com/store/apps/details?id=com.erionxx.radioshqip"),
        ("📷 QR Code Scanner — skanim i shpejtë QR & barcode", "https://play.google.com/store/apps/details?id=com.erionxx.qrscanner"),
        ("📶 Speedtest Pro — matja e shpejtësisë së internetit", "https://play.google.com/store/apps/details?id=com.erionxx.speedtestpro"),
    ],
    "web": [
        ("📚 Lexo Libra — biblioteka dixhitale shqipe", "https://lexolibra.netlify.app"),
        ("📉 ÇmimRadar — krahasuesi i çmimeve", "https://cmimradar.netlify.app"),
        ("🛒 MarketRadar — çmimet e supermarketeve në Tiranë", "https://marketradar-tirana.netlify.app"),
        ("💊 FarmaciRadar — krahasuesi i farmacive online", "https://farmaciradar.netlify.app"),
        ("🎬 FilmaHD — katalog filmash e serialesh", "https://filma12hd.vercel.app"),
        ("🛍 KlikoBli — dyqani online", "https://klikobli.vercel.app/"),
        ("✨ VELTRIX — prezantim vizual kreativ", "https://veltrix-visuals.netlify.app"),
        ("🌐 Portfolio e plotë e Erion Nezhës", "https://erionxx1.netlify.app"),
        ("🎴 Kartvizita dixhitale", "https://erionnezha.github.io/erionxx-business-card/"),
    ],
    "ai": [
        ("💬 Dertli Bot — asistenti AI shqip", "https://dertlibot.netlify.app"),
        ("🤖 JARVIS PC — asistenti zanor për kompjuterin", "https://github.com/ErionNezha/jarvis-pc"),
    ],
}
WORKS_HEADER = "🗂 <b>Shembuj pune reale</b> — projekte të përfunduara dhe live.\nZgjidh një kategori:"

# Vlerësime REALE (përmbledhje të ndershme, jo citate të sajuara):
# dy vlerësime me yje maksimale në Google Play për ERION TV.
# PA shifra (urdhri "mos vendos shifra") — as në atribucion.
REVIEWS_HEADER = "⭐ <b>Vlerësime nga përdorues realë</b>"
REVIEWS_PLAY = (
    "⭐⭐⭐⭐⭐\n"
    "Dizajn shumë i pëlqyer dhe navigim i lehtë nëpër aplikacion.\n"
    "<i>— vlerësim në Google Play (ERION TV)</i>\n\n"
    "⭐⭐⭐⭐⭐\n"
    "Kanale të shumta dhe funksionim i qëndrueshëm, pa ndërprerje.\n"
    "<i>— vlerësim në Google Play (ERION TV)</i>"
)
REVIEWS_TEXT = REVIEWS_HEADER + "\n\n" + REVIEWS_PLAY

# FAQ — TEPËR cilësore: PA asnjë shifër (urdhri "mos vendos shifra"):
# jo %, jo shuma, jo afate me ditë/orë, jo premtime të numëruara.
FAQ_TEXT = (
    "❓ <b>Pyetje të shpeshta</b>\n\n"
    "<b>Sa zgjat një projekt?</b>\n"
    "Varet nga madhësia dhe funksionet që kërkon projekti. Pasi plotëson "
    "brief-in, afati përcaktohet bashkë dhe fiksohet në marrëveshje para "
    "se të nisë puna.\n\n"
    "<b>Si bëhet pagesa?</b>\n"
    "Pagesa bëhet me faza, sipas marrëveshjes: një parapagim për të nisur "
    "punën dhe pjesa tjetër sipas ecurisë, deri në dorëzimin final.\n\n"
    "<b>Çfarë duhet të jap unë si klient?</b>\n"
    "Përgjigjet e brief-it dhe materialet e tua — logo, tekste, foto dhe "
    "akseset e nevojshme. Për gjithçka tjetër kujdesem unë.\n\n"
    "<b>A ka mbështetje dhe mirëmbajtje pas dorëzimit?</b>\n"
    "Po — pas dorëzimit mbështetja është e përfshirë për çdo problem që "
    "lind nga puna e dorëzuar. Nëse do qetësi afatgjatë, ka edhe paketa "
    "mirëmbajtjeje opsionale.\n\n"
    "<b>A mund të kërkoj korrigjime?</b>\n"
    "Po — korrigjimet brenda fushës së rënë dakord janë të përfshira. "
    "Ndryshimet më të mëdha, jashtë fushës fillestare, i diskutojmë "
    "bashkë para se të bëhen."
)

CV_PATH = os.path.join(BASE, "assets", "CV-Erion-Nezha.pdf")
CV_CAPTION = ("📄 CV-ja e Erion Nezhës — Software Developer\n"
              "Përvojë, aftësi dhe projekte — në një dokument.")

WELCOME_VOICE_PATH = os.path.join(BASE, "assets", "welcome.ogg")

# ---------- paketa 3: galeria vizuale + Mini Web App ----------
GALLERY_DIR = os.path.join(BASE, "assets", "gallery")
# Rendi i qëndrueshëm i galerisë; file-t që mungojnë kapërcehen.
GALLERY_ORDER = ["lexolibra", "cmimradar", "marketradar", "farmaciradar",
                 "filmahd", "klikobli", "veltrix", "portfolio", "dertli",
                 "radioshqip"]
# Emrat shfaqës për caption-et e albumit (pa shifra).
GALLERY_NAMES = {
    "lexolibra": "📚 Lexo Libra — biblioteka dixhitale shqipe",
    "cmimradar": "📉 ÇmimRadar — krahasuesi i çmimeve",
    "marketradar": "🛒 MarketRadar — çmimet e supermarketeve",
    "farmaciradar": "💊 FarmaciRadar — krahasuesi i farmacive",
    "filmahd": "🎬 FilmaHD — katalog filmash e serialesh",
    "klikobli": "🛍 KlikoBli — dyqani online",
    "veltrix": "✨ VELTRIX — prezantim vizual kreativ",
    "portfolio": "🌐 Portfolio — Erion Nezha",
    "dertli": "💬 Dertli Bot — asistenti AI shqip",
    "radioshqip": "🎵 Radio Shqip — radiot shqiptare live",
}

# Mini Web App-i (portali vizual) — GitHub Pages; vetëm përmbajtje
# publike, pa të dhëna private (ato jetojnë në bisedën e botit).
WEBAPP_URL = "https://erionnezha.github.io/client-portal-app/"

CARD_PATH = os.path.join(BASE, "assets", "card.png")
CARD_IMG_CAPTION = (
    "🎴 Kartvizita e Erion Nezhës — ruaje ose përcille te dikush që "
    "kërkon shërbimet e mia.\n"
    "Skanimi i kodit QR të çon te portali privat i klientëve."
)

# ---------- F1: gjurmimi i projektit (vetëm zonë private, pa shifra) ----------
PROJECTS_HEADER = "🚧 <b>Projekti im</b> — ecuria e punës:"
PROJECTS_EMPTY = (
    "🚧 <b>Projekti im</b>\n\n"
    "Nuk ke ende një projekt aktiv.\n\n"
    "Kur të nisësh një projekt me 📝 <b>Nis një projekt</b>, këtu do të "
    "shohësh ecurinë e tij fazë pas faze, deri në dorëzim."
)
CLIENT_FINISH_TEXT = (
    "🎉 <b>Projekti yt përfundoi!</b>\n\n"
    "🚧 <b>{title}</b>\n\n"
    "Puna u dorëzua me sukses. Faleminderit për besimin — për çdo gjë "
    "tjetër, dera ime këtu është gjithmonë e hapur. ✨"
)

# ---------- F2: rezervimi i konsultave (tekstet statike pa shifra;
# datat/oraret janë të dhëna funksionale dhe lejohen) ----------
BOOK_START_TEXT = "🗓 <b>Rezervo konsultë</b>\n\nZgjidh shërbimin për të cilin do të flasim:"
BOOK_PICK_SLOT_TEXT = "🗓 <b>Zgjidh orarin</b> që të përshtatet:"
BOOK_NO_SLOTS_TEXT = (
    "🗓 <b>Rezervo konsultë</b>\n\n"
    "Për momentin s'ka orare të lira.\n\n"
    "Provo më vonë, ose shkruaj direkt me 💬 <b>Fol me Erionin</b> — "
    "gjejmë bashkë një orar."
)
BOOK_PENDING_TEXT = (
    "⏳ <b>Ke tashmë një kërkesë konsulte në pritje.</b>\n\n"
    "Kur Erioni ta shqyrtojë, do të njoftohesh këtu. Për diçka urgjente "
    "përdor 💬 <b>Fol me Erionin</b>."
)
BOOK_SENT_TEXT = (
    "✅ <b>Kërkesa për konsultë u dërgua.</b>\n\n"
    "Erioni e shqyrton dhe të konfirmon këtu orarin. Faleminderit!"
)
BOOK_TAKEN_TEXT = (
    "⚠️ Ky orar sapo u rezervua nga dikush tjetër.\n\n"
    "Zgjidh një orar tjetër:"
)
BOOK_APPROVED_TEXT = (
    "✅ <b>Konsulta u konfirmua!</b>\n\n"
    "💼 Shërbimi: {service}\n"
    "🗓 Orari: <b>{slot}</b>\n\n"
    "Do të marrësh një kujtesë para takimit. Nëse orari s'të përshtatet "
    "më, njofto Erionin me 💬 <b>Fol me Erionin</b>."
)
BOOK_REJECTED_TEXT = (
    "🗓 <b>Për konsultën e kërkuar</b>\n\n"
    "Na vjen keq — orari <b>{slot}</b> për {service} s'është më i mundur.\n\n"
    "Provo një orar tjetër nga 🗓 <b>Rezervo konsultë</b>, ose shkruaj "
    "Erionit me 💬 <b>Fol me Erionin</b> dhe e gjejmë bashkë."
)

# ---------- kujtesat automatike (F2/F3) ----------
BOOKING_REMIND_WITHIN = timedelta(hours=3)
EXPIRY_REMIND_WITHIN = timedelta(days=3)
REMINDER_BOOKING_CLIENT = (
    "⏰ <b>Kujtesë për konsultën tënde</b>\n\n"
    "💼 Shërbimi: {service}\n"
    "🗓 Orari: <b>{slot}</b>\n\n"
    "Erioni të pret këtu në bisedë — ji gati pak para orarit. Nëse "
    "s'mundesh, njoftoje me 💬 <b>Fol me Erionin</b>."
)
REMINDER_BOOKING_ADMIN = (
    "⏰ <b>Kujtesë konsulte</b>\n\n"
    "👤 {name} (@{username}, id {client_id})\n"
    "💼 Shërbimi: {service}\n"
    "🗓 Orari: <b>{slot}</b>"
)
EXPIRY_CLIENT_TEXT = (
    "⏰ <b>Aksesi yt po i afrohet fundit</b>\n\n"
    "Portali yt privat skadon më <b>{date}</b>.\n\n"
    "Nëse do ta zgjatësh, ose ke një projekt të ri në mendje, shkruaj "
    "Erionit me 💬 <b>Fol me Erionin</b>.\n\n"
    "Faleminderit që je pjesë e klientëve të mi! ✨"
)

# Emrat e ditëve/muajve për shfaqjen e orareve të konsultave (F3: dy gjuhë).
AL_WEEKDAYS = ["e hënë", "e martë", "e mërkurë", "e enjte",
               "e premte", "e shtunë", "e diel"]
AL_MONTHS = ["janar", "shkurt", "mars", "prill", "maj", "qershor",
             "korrik", "gusht", "shtator", "tetor", "nëntor", "dhjetor"]
EN_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
               "Friday", "Saturday", "Sunday"]
EN_MONTHS = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November",
             "December"]


def fmt_slot(dt, lang: str = "sq") -> str:
    """'e premte, 24 tetor — 18:00' / 'Friday, October 24 — 18:00'
    (data/ora = të dhëna funksionale, përjashtohen nga 'pa shifra')."""
    if dt is None:
        return "—"
    if lang == "en":
        return (f"{EN_WEEKDAYS[dt.weekday()]}, {EN_MONTHS[dt.month - 1]} "
                f"{dt.day} — {dt:%H:%M}")
    return (f"{AL_WEEKDAYS[dt.weekday()]}, {dt.day} "
            f"{AL_MONTHS[dt.month - 1]} — {dt:%H:%M}")

# Rrjedhat shumë-hapëshe mbahen në user_data["flow"] = {"kind": ..., "step": ...}
# dhe drejtohen nga dispatch-i i tekstit/callback-eve (pa ConversationHandler:
# më e thjeshtë, pa paralajmërime PTB dhe plotësisht e testueshme lokalisht).

# Paketa 3 (F4): menuja e klientit u THJESHTUA — katër veprimet
# kryesore + "☰ Më shumë"; pjesa tjetër jeton në tastierën e dytë.
CLIENT_KB = ReplyKeyboardMarkup(
    [["💼 Shërbimet", "🗂 Shembuj pune"],
     ["🚧 Projekti im", "💬 Fol me Erionin"],
     ["📝 Nis një projekt", "☰ Më shumë"]],
    resize_keyboard=True,
)
CLIENT_KB_EN = ReplyKeyboardMarkup(
    [["💼 Services", "🗂 Work samples"],
     ["🚧 My project", "💬 Talk to Erion"],
     ["📝 Start a project", "☰ More"]],
    resize_keyboard=True,
)
CLIENT_KB_MORE = ReplyKeyboardMarkup(
    [["🏠 Kreu", "🧭 Udhëzuesi"],
     ["🗓 Rezervo konsultë", "❓ FAQ"],
     ["📄 CV-ja ime", "🎴 Kartvizita ime"],
     ["🔐 Aksesi im", "🌍 Gjuha"],
     ["⬅ Mbrapa"]],
    resize_keyboard=True,
)
CLIENT_KB_MORE_EN = ReplyKeyboardMarkup(
    [["🏠 Home", "🧭 Guide"],
     ["🗓 Book a consultation", "❓ FAQ"],
     ["📄 My CV", "🎴 My card"],
     ["🔐 My access", "🌍 Language"],
     ["⬅ Back"]],
    resize_keyboard=True,
)


def client_kb(lang: str = "sq", more: bool = False):
    """Tastiera e klientit sipas gjuhës (kryesore ose 'Më shumë')."""
    if more:
        return CLIENT_KB_MORE_EN if lang == "en" else CLIENT_KB_MORE
    return CLIENT_KB_EN if lang == "en" else CLIENT_KB


# Etiketat e menusë në të dyja gjuhët → veprimi (F3). Emrat e duhur të
# projekteve/shërbimeve nuk ndryshojnë; përkthehen vetëm fjalët përshkruese.
MENU_ROUTES = {
    "💼 Shërbimet": "services", "💼 Services": "services",
    "🗂 Shembuj pune": "works", "🗂 Work samples": "works",
    "🎴 Kartvizita ime": "card", "🎴 Kartvizita": "card",
    "🎴 My card": "card",
    "🔐 Aksesi im": "access", "🔐 My access": "access",
    "💬 Fol me Erionin": "talk", "💬 Talk to Erion": "talk",
    "📝 Nis një projekt": "brief", "📝 Start a project": "brief",
    "🚧 Projekti im": "projects", "🚧 My project": "projects",
    "🗓 Rezervo konsultë": "booking", "🗓 Book a consultation": "booking",
    "❓ FAQ": "faq",
    "📄 CV-ja ime": "cv", "📄 My CV": "cv",
    "🌍 Gjuha": "lang", "🌍 Language": "lang",
    "☰ Më shumë": "more", "☰ More": "more",
    "⬅ Mbrapa": "back_home", "⬅ Back": "back_home",
    # paketa 4: Kreu (rreshti i parë i "Më shumë") + Udhëzuesi (turi)
    "🏠 Kreu": "home", "🏠 Home": "home",
    "🧭 Udhëzuesi": "guide", "🧭 Guide": "guide",
}

LOCK_TEXT = (
    "🔐 <b>ERION NEZHA — PRIVATE ACCESS</b>\n"
    "━━━━━━━━━━━━━━━\n"
    "Ky është portali privat i klientëve të <b>Erion Nezhës</b>.\n\n"
    "Aksesi bëhet <b>vetëm me kod personal</b>, i cili jepet pas "
    "kontaktit të parë për një shërbim.\n\n"
    "Nëse s'ke kod ende, kërko shërbimin tënd këtu — kërkesa shqyrtohet "
    "personalisht nga Erioni."
)

# Fiks 3 (siguri): te dera, TË GJITHA dështimet marrin TË NJËJTIN mesazh
# gjenerik — vizitori s'mëson dot nëse kodi ekziston, ka skaduar, është
# revokuar apo i përket dikujt tjetër. Arsyeja e saktë i shkon vetëm adminit.
GATE_FAIL_TEXT = (
    "❌ <b>Kodi nuk u pranua.</b>\n\n"
    "Kontrollo që e ke shkruar saktë (formati: EN-XXXX-XXXX) dhe provo "
    "sërish. Nëse kodi të është dhënë nga Erioni dhe prapë s'pranohet, "
    "shkruaji atij në Instagram: @erjonixx"
)

FAIL_STATUS_LABELS = {
    "invalid": "kod i pasaktë / i panjohur",
    "expired": "kod i skaduar",
    "revoked": "kod i revokuar",
    "bound_other": "kod i lidhur me një llogari tjetër",
}

# Fiks 2 (anti-spam): kufijtë ditorë për vizitorë/klientë
REQ_PENDING_TEXT = (
    "⏳ <b>Ke tashmë një kërkesë në pritje.</b>\n\n"
    "Kërkesa jote e mëparshme është dërguar dhe po pret përgjigjen e "
    "Erionit — s'mund të dërgosh një tjetër ndërkohë. Kur të shqyrtohet, "
    "do të njoftohesh këtu."
)
REQ_DAILY_TEXT = (
    "⏳ <b>Ke arritur limitin ditor të kërkesave.</b>\n\n"
    "Kërkesat për shërbim kanë limit ditor. Provo sërish nesër — "
    "ose shkruaji Erionit në Instagram: @erjonixx"
)
BRIEF_DAILY_TEXT = (
    "⏳ <b>Ke arritur limitin ditor të brief-eve.</b>\n\n"
    "Brief-et e projekteve kanë limit ditor. Brief-i i ri mund të "
    "niset nesër — për diçka urgjente përdor 💬 <b>Fol me Erionin</b>."
)

WELCOME_CLIENT = (
    "✨ <b>Mirë se erdhe në portalin tënd privat, {name}.</b>\n\n"
    "Këtu gjen shërbimet, shembujt e punës dhe formularin për të nisur "
    "projektin tënd. Mesazhet e tua vijnë direkt tek unë.\n\n"
    "{status}\n\n"
    "— <i>Erion Nezha</i>"
)


# ================================================================
# F3 — NDËRFAQJA DY GJUHËSH (sq / en)
# Çdo tekst statik që sheh klienti/vizitori kalon nga STR + t().
# Tekstet e adminit mbeten shqip; përmbajtja e të dhënave (shënimet,
# broadcast-i, titujt e projekteve, statusi) mbetet siç u shkrua.
# ================================================================
SERVICES_EN = [
    ("web", "🌐 Website & e-commerce"),
    ("app", "📱 Android app"),
    ("bot", "🤖 Telegram bot & automation"),
    ("design", "🎨 Graphic design & video"),
    ("marketing", "📣 Digital marketing"),
    ("other", "✨ Something else"),
]
SERVICE_DETAILS_EN = {
    "web": "🌐 <b>Websites & e-commerce</b>\nShowcase sites, online shops, booking pages or a custom platform — premium design, fast, optimized for Google and for phones.",
    "app": "📱 <b>Android app</b>\nFrom the idea to publishing on Google Play: design, development, testing and complete delivery of your app.",
    "bot": "🤖 <b>Telegram bots & automation</b>\nBots for your business (orders, notifications, customer support) and automations that save you hours of work every week.",
    "design": "🎨 <b>Graphic design & video</b>\nLogo and visual identity, graphics for social media and app stores, video editing with animated captions.",
    "marketing": "📣 <b>Digital marketing</b>\nContent strategy, online presence management and campaigns that bring real clients, not just views.",
    "other": "✨ <b>Something else</b>\nHave another idea in mind? Tell me through the project form and we'll discuss it together.",
}
BUDGETS_EN = ["Modest", "Moderate", "Serious", "Not sure yet"]

WORK_CATEGORIES_EN = [
    ("apps", "📱 Mobile apps"),
    ("web", "🌐 Web platforms"),
    ("ai", "🤖 Bots & AI"),
]
WORKS_EN = {
    "apps": [
        ("📺 ERION TV — the IPTV app", "https://play.google.com/store/apps/details?id=com.streamvision.app"),
        ("📡 Dream TV AL — live TV and movies on your phone", "https://play.google.com/store/apps/details?id=blackmaster.ex"),
        ("🎵 Radio Shqip — Albanian radio stations live", "https://play.google.com/store/apps/details?id=com.erionxx.radioshqip"),
        ("📷 QR Code Scanner — fast QR & barcode scanning", "https://play.google.com/store/apps/details?id=com.erionxx.qrscanner"),
        ("📶 Speedtest Pro — internet speed testing", "https://play.google.com/store/apps/details?id=com.erionxx.speedtestpro"),
    ],
    "web": [
        ("📚 Lexo Libra — the Albanian digital library", "https://lexolibra.netlify.app"),
        ("📉 ÇmimRadar — the price comparison tool", "https://cmimradar.netlify.app"),
        ("🛒 MarketRadar — supermarket prices in Tirana", "https://marketradar-tirana.netlify.app"),
        ("💊 FarmaciRadar — the online pharmacy comparison", "https://farmaciradar.netlify.app"),
        ("🎬 FilmaHD — movie and series catalogue", "https://filma12hd.vercel.app"),
        ("🛍 KlikoBli — the online store", "https://klikobli.vercel.app/"),
        ("✨ VELTRIX — creative visual showcase", "https://veltrix-visuals.netlify.app"),
        ("🌐 Erion Nezha's full portfolio", "https://erionxx1.netlify.app"),
        ("🎴 Digital business card", "https://erionnezha.github.io/erionxx-business-card/"),
    ],
    "ai": [
        ("💬 Dertli Bot — the Albanian AI assistant", "https://dertlibot.netlify.app"),
        ("🤖 JARVIS PC — the voice assistant for your computer", "https://github.com/ErionNezha/jarvis-pc"),
    ],
}

FAQ_TEXT_EN = (
    "❓ <b>Frequently asked questions</b>\n\n"
    "<b>How long does a project take?</b>\n"
    "It depends on the project's size and the features you need. Once "
    "you complete the brief, the deadline is agreed together and fixed "
    "in the agreement before work starts.\n\n"
    "<b>How does payment work?</b>\n"
    "Payment is made in stages, as agreed: an advance to start the "
    "work, and the rest along the way, up to the final delivery.\n\n"
    "<b>What do I need to provide as a client?</b>\n"
    "The brief answers and your materials — logo, texts, photos and "
    "the necessary access. I take care of everything else.\n\n"
    "<b>Is there support and maintenance after delivery?</b>\n"
    "Yes — after delivery, support is included for any issue arising "
    "from the delivered work. If you'd like long-term peace of mind, "
    "there are optional maintenance packages too.\n\n"
    "<b>Can I ask for revisions?</b>\n"
    "Yes — revisions within the agreed scope are included. Bigger "
    "changes, outside the initial scope, are discussed together "
    "before they're made."
)

REVIEWS_HEADER_EN = "⭐ <b>Reviews from real users</b>"
REVIEWS_PLAY_EN = (
    "⭐⭐⭐⭐⭐\n"
    "Loved the design and how easy the app is to navigate.\n"
    "<i>— Google Play review (ERION TV)</i>\n\n"
    "⭐⭐⭐⭐⭐\n"
    "Plenty of channels and stable playback, without interruptions.\n"
    "<i>— Google Play review (ERION TV)</i>"
)

PROJECT_STAGES_EN = ["Brief", "Design", "Development", "Testing", "Delivery"]

STR = {
    "sq": {
        "lock_text": LOCK_TEXT,
        "lock_note_need_code": "🔒 Së pari nevojitet kodi i aksesit.",
        "lock_note_private": "🔒 Ky bot është privat. Hyrja bëhet vetëm me kod personal.",
        "locked_alert": "Aksesi është i kyçur.",
        "lock_btn_code": "🔑 Kam kod aksesi",
        "lock_btn_req": "📝 Kërkoj shërbim",
        "code_prompt": "🔑 Shkruaj kodin tënd të aksesit (formati: <code>EN-XXXX-XXXX</code>):",
        "locked_temp_code": "⏳ Llogaria jote është e kyçur përkohësisht nga tentativat e gabura. Provo më vonë.",
        "locked_temp": "⏳ Llogaria jote është e kyçur përkohësisht. Provo më vonë.",
        "code_accepted": "✅ <b>Kodi u pranua.</b> Aksesi yt është aktiv deri më <b>{date}</b>.",
        "gate_fail": GATE_FAIL_TEXT,
        "too_many": "🔒 Shumë tentativa të gabuara — llogaria u kyç për një orë.",
        "code_retry": "Shkruaj sërish kodin, ose /anulo për t'u kthyer.",
        "req_title": "📝 <b>Kërkesë për shërbim</b>\n\nÇfarë shërbimi kërkon?",
        "req_name": "Si e ke <b>emrin</b> (emër mbiemër)?",
        "req_desc": "Përshkruaje shkurtimisht <b>çfarë të duhet</b>:",
        "req_contact": "Një <b>kontakt</b> ku mund të të shkruaj Erioni (numër telefoni ose email). Mund ta kapërcesh — biseda vazhdon këtu.",
        "skip": "⏭ Kapërce",
        "req_sent": "✅ <b>Kërkesa jote u dërgua.</b>\n\nErioni e shqyrton personalisht. Kur të miratohet, boti hapet automatikisht për ty dhe merr njoftim këtu.\n\nPërgjigjja zakonisht vjen brenda ditës.",
        "req_pending": REQ_PENDING_TEXT,
        "req_daily": REQ_DAILY_TEXT,
        "welcome": WELCOME_CLIENT,
        "approved_welcome": "🎉 <b>Kërkesa jote u MIRATUA!</b>\n\nPortali yt privat është aktiv deri më <b>{date}</b>.\n\n",
        "services_header": "💼 <b>Shërbimet</b> — zgjidh për detaje:",
        "service_start_btn": "📝 Nis projekt të këtij lloji",
        "works_header": WORKS_HEADER,
        "works_cat_title": "🗂 <b>{title}</b> — projekte live:",
        "back": "⬅ Kthehu",
        "reviews_btn": "⭐ Vlerësime",
        "faq": FAQ_TEXT,
        "cv_caption": CV_CAPTION,
        "cv_missing": "📄 CV-ja për momentin s'është e disponueshme këtu — kërkoja Erionit me 💬 <b>Fol me Erionin</b>.",
        "cv_failed": "📄 CV-ja s'u dërgua dot tani — kërkoja Erionit me 💬 <b>Fol me Erionin</b>.",
        "card_text": "🎴 <b>Erion Nezha</b> — Software Developer\nTiranë, Shqipëri\n\nRuaji kontaktet e mia:",
        "card_img_btn": "🖼 Karta si imazh",
        "card_img_caption": CARD_IMG_CAPTION,
        "card_img_missing": "🖼 Karta si imazh për momentin s'është e disponueshme — përdor lidhjet e kartvizitës më sipër.",
        "card_img_failed": "🖼 Karta s'u dërgua dot tani — përdor lidhjet e kartvizitës më sipër.",
        "access_admin": "🔐 Je admini — akses i pakufizuar.",
        "access_text": "🔐 <b>Aksesi yt</b>\n\n• Statusi: ✅ Aktiv\n• Skadon më: <b>{date}</b> (edhe {days} ditë)\n• Shërbimi: {service}\n\nPër zgjatje, shkruaj Erionit me 💬 <b>Fol me Erionin</b>.",
        "brief_title": "📝 <b>Projekt i ri</b>\n\nÇfarë lloj projekti është?",
        "brief_desc_q": "Përshkruaje projektin: çfarë duhet të bëjë, për kë është, çfarë faqesh/funksionesh mendon?",
        "brief_budget_q": "Buxheti i përafërt?",
        "brief_deadline_q": "Kur të duhet gati? (p.sh. brenda muajit / kam një datë)",
        "brief_contact_q": "Kontakti yt (telefon ose email):",
        "brief_sent": "✅ <b>Brief-i u dërgua!</b>\n\nErioni e lexon dhe të përgjigjet këtu me hapat e radhës dhe preventivin. Faleminderit për besimin!",
        "brief_daily": BRIEF_DAILY_TEXT,
        "projects_header": PROJECTS_HEADER,
        "projects_empty": PROJECTS_EMPTY,
        "project_updated": "🕒 Përditësuar më: {date}",
        "project_update_title": "🚧 <b>Përditësim projekti</b>",
        "project_finish": CLIENT_FINISH_TEXT,
        "book_start": BOOK_START_TEXT,
        "book_pick_slot": BOOK_PICK_SLOT_TEXT,
        "book_no_slots": BOOK_NO_SLOTS_TEXT,
        "book_pending": BOOK_PENDING_TEXT,
        "book_sent": BOOK_SENT_TEXT,
        "book_taken": BOOK_TAKEN_TEXT,
        "book_approved": BOOK_APPROVED_TEXT,
        "book_rejected": BOOK_REJECTED_TEXT,
        "reminder_booking_client": REMINDER_BOOKING_CLIENT,
        "expiry_client": EXPIRY_CLIENT_TEXT,
        "talk_start": "💬 <b>Je në bisedë direkte me Erionin.</b>\nShkruaj mesazhin tënd — i vjen atij menjëherë dhe përgjigjja të kthehet këtu.\nPër t'u kthyer te menuja: /ndalo",
        "talk_stop": "U ktheve te menuja 👇",
        "talk_sent": "✔️ U dërgua te Erioni.",
        "talk_send_fail": "⚠️ Dërgimi dështoi — provo sërish.",
        "talk_media_hint": "Për të dërguar foto, zë ose dokumente, aktivizo më parë 💬 <b>Fol me Erionin</b> nga menuja.",
        "flow_needs_text": "Kjo rrjedhë pret tekst — shkruaj përgjigjen, ose /anulo për t'u kthyer.",
        "menu_prompt": "Zgjidh nga menuja më poshtë 👇",
        "admin_says": "💬 <b>Erioni:</b>\n{text}",
        "cancelled": "U anulua.",
        "lang_choose": "🌍 <b>Gjuha / Language</b>\n\nZgjidh gjuhën e ndërfaqes:",
        "review_ask": "⭐ <b>Si e vlerëson punën për projektin «{title}»?</b>\n\nPrek yjet më poshtë — vlerësimi yt më ndihmon të përmirësohem dhe, me miratimin tim, shfaqet te vlerësimet e klientëve.",
        "review_skipped": "👍 Në rregull — faleminderit gjithsesi!",
        "review_skip": "Kapërce",
        "review_comment_q": "⭐ Faleminderit! Nëse do, shto një koment të shkurtër (ose kapërce):",
        "review_thanks": "⭐ <b>Faleminderit për vlerësimin!</b>\n\nVlerësimi yt u ruajt dhe, pas shqyrtimit, mund të shfaqet te vlerësimet e klientëve.",
        "ics_caption": "📅 Shtoje konsultën në kalendarin tënd me një prekje — hape këtë file nga telefoni yt.",
        "pdf_caption": "🧾 Propozimi paraprak i projektit tënd — përmbledhje pa angazhim. Oferta përfundimtare vjen pas diskutimit tonë.",
        "gcal_btn": "📅 Google Calendar",
        # paketa 3: menu e thjeshtuar, galeria, web app, marrëveshja, orari
        "menu_more": "☰ Më shumë",
        "menu_back": "⬅ Mbrapa",
        "works_gallery": "📸 Galeria",
        "works_gallery_empty": "Galeria po përgatitet — së shpejti këtu do të shohësh pamje reale të punëve të mia.",
        "home_webapp": "🖥 Portali vizual",
        "home_webapp_text": "🖥 <b>Portali vizual</b>\nShërbimet, punët dhe faqja ime — në një pamje të vetme, pa dalë nga Telegrami:",
        "agreement_subject_default": "shërbimet e rëna dakord",
        "agreement_intro": "✍ <b>Marrëveshje bashkëpunimi</b>\n\nErioni të propozon një marrëveshje bashkëpunimi për «{title}».\n\nLexo kushtet më poshtë dhe, nëse je dakord, prek butonin e pranimit.",
        "agreement_terms": (
            "<b>Kushtet e bashkëpunimit</b>\n"
            "• Objekti: puna e përshkruar në brief-in dhe propozimin tënd, e konfirmuar në bisedë.\n"
            "• Ecuria: puna zhvillohet me faza dhe ecuria ndiqet te «Projekti im» në këtë portal.\n"
            "• Pagesa: sipas kushteve të rëna dakord në bisedë mes nesh.\n"
            "• Korrigjimet: korrigjimet e arsyeshme brenda fushës së rënë dakord janë të përfshira.\n"
            "• Dorëzimi: sipas planit të projektit që ndiqet në portal.\n"
            "• Pas dorëzimit: një periudhë mbështetjeje për rregullimin e defekteve, siç është rënë dakord.\n"
            "• Komunikimi: të dyja palët komunikojnë përmes këtij portali."
        ),
        "agreement_accept": "✅ I pranoj kushtet",
        "agreement_decline": "❌ Refuzoj",
        "agreement_accepted_msg": "✅ <b>Marrëveshja u pranua.</b>\n\nDokumenti i marrëveshjes të vjen më poshtë — ruaje për vete. Faleminderit për besimin!",
        "agreement_declined_msg": "Në rregull — marrëveshja nuk u pranua dhe Erioni u njoftua. Për çdo sqarim, shkruaj me 💬 <b>Fol me Erionin</b>.",
        "agreement_done": "Kjo marrëveshje është vendosur tashmë.",
        "agreement_pdf_caption": "✍ Marrëveshja jote e bashkëpunimit — e pranuar dixhitalisht në këtë portal.",
        "after_hours": "Faleminderit për mesazhin — u mor dhe iu përcoll Erionit. Orari i tij i punës është gjatë ditëve të javës; përgjigjja vjen sapo të nisë orari i punës. Për gjëra urgjente, lëre mesazhin këtu — e sheh gjithçka me radhë.",
        # paketa 4: Kreu/Udhëzuesi, anulimi i rezervimit, turi, nisja e projektit
        "menu_home": "🏠 Kreu",
        "menu_guide": "🧭 Udhëzuesi",
        "book_cancel_btn": "❌ Anulo rezervimin",
        "book_cancelled": "🗓 <b>Kërkesa për konsultë u anulua.</b>\n\nErioni u njoftua. Nëse do një orar tjetër, nis sërish nga 🗓 <b>Rezervo konsultë</b>.",
        "book_cancel_done": "Ky rezervim është vendosur tashmë.",
        "project_started": "🚧 <b>Projekti yt nisi!</b>\n\nErioni e hapi projektin tënd — ecuria ndiqet këtu, fazë pas faze.",
        "tour_s1": "🧭 <b>Mirë se erdhe në turin e portalit tënd</b>\n\n💼 <b>Shërbimet</b>\nKëtu gjen gjithçka që ndërtoj: faqe interneti, aplikacione, botë Telegram, dizajn dhe marketing — me detaje për secilin shërbim.",
        "tour_s2": "🗂 <b>Shembuj pune</b> dhe 📸 <b>Galeria</b>\nShiko punë reale, të përfunduara dhe live — me pamje të vërteta të projekteve, jo vetëm përshkrime.",
        "tour_s3": "📝 <b>Nis një projekt</b>\nKur të jesh gati, plotëso brief-in e shkurtër: lloji, përshkrimi, buxheti dhe afati. E lexoj dhe të përgjigjem me hapat e radhës.",
        "tour_s4": "🗓 <b>Rezervo konsultë</b> dhe 💬 <b>Fol me Erionin</b>\nZgjidh një orar të lirë për konsultë, ose shkruaj direkt në bisedë — mesazhet e tua më vijnë drejtpërdrejt.",
        "tour_next": "➡ Vazhdo",
        "tour_done_btn": "✅ E kuptova",
        "tour_closing": "🧭 <b>Gati je!</b>\n\nTani e njeh portalin tënd. Për çdo gjë, jam një mesazh larg — 💬 <b>Fol me Erionin</b>.",
        # rregullimi UX: etiketat e menusë ndërpresin çdo rrjedhë aktive
        "flow_interrupted": "U ndërpre rrjedha ku ishe — ja ku je tani.",
        "brief_pick_hint": "Zgjidh njërin nga butonat më lart — ose shkruaj /anulo për ta lënë.",
    },
    "en": {
        "lock_text": (
            "🔐 <b>ERION NEZHA — PRIVATE ACCESS</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "This is the private client portal of <b>Erion Nezha</b>.\n\n"
            "Access is granted <b>only with a personal code</b>, which is "
            "given after the first contact about a service.\n\n"
            "If you don't have a code yet, request your service here — "
            "every request is reviewed personally by Erion."
        ),
        "lock_note_need_code": "🔒 First, your access code is needed.",
        "lock_note_private": "🔒 This bot is private. Entry is only possible with a personal code.",
        "locked_alert": "Access is locked.",
        "lock_btn_code": "🔑 I have an access code",
        "lock_btn_req": "📝 Request a service",
        "code_prompt": "🔑 Type your access code (format: <code>EN-XXXX-XXXX</code>):",
        "locked_temp_code": "⏳ Your account is temporarily locked because of wrong attempts. Please try again later.",
        "locked_temp": "⏳ Your account is temporarily locked. Please try again later.",
        "code_accepted": "✅ <b>Code accepted.</b> Your access is active until <b>{date}</b>.",
        "gate_fail": (
            "❌ <b>The code was not accepted.</b>\n\n"
            "Check that you typed it correctly (format: EN-XXXX-XXXX) "
            "and try again. If Erion gave you the code and it still "
            "isn't accepted, message him on Instagram: @erjonixx"
        ),
        "too_many": "🔒 Too many wrong attempts — the account is locked for a while.",
        "code_retry": "Type the code again, or /anulo to go back.",
        "req_title": "📝 <b>Service request</b>\n\nWhat service are you looking for?",
        "req_name": "What is your <b>full name</b>?",
        "req_desc": "Briefly describe <b>what you need</b>:",
        "req_contact": "A <b>contact</b> where Erion can reach you (phone number or email). You can skip this — the conversation continues here.",
        "skip": "⏭ Skip",
        "req_sent": "✅ <b>Your request has been sent.</b>\n\nErion reviews every request personally. When approved, the bot opens for you automatically and you'll be notified here.\n\nReplies usually arrive within the day.",
        "req_pending": "⏳ <b>You already have a request pending.</b>\n\nYour earlier request was sent and is waiting for Erion's reply — you can't send another one in the meantime. When it's reviewed, you'll be notified here.",
        "req_daily": "⏳ <b>You've reached the daily request limit.</b>\n\nService requests have a daily limit. Please try again tomorrow — or message Erion on Instagram: @erjonixx",
        "welcome": "✨ <b>Welcome to your private portal, {name}.</b>\n\nHere you'll find the services, work samples and the form to start your project. Your messages come straight to me.\n\n{status}\n\n— <i>Erion Nezha</i>",
        "approved_welcome": "🎉 <b>Your request was APPROVED!</b>\n\nYour private portal is active until <b>{date}</b>.\n\n",
        "services_header": "💼 <b>Services</b> — pick one for details:",
        "service_start_btn": "📝 Start a project of this kind",
        "works_header": "🗂 <b>Real work samples</b> — finished, live projects.\nPick a category:",
        "works_cat_title": "🗂 <b>{title}</b> — live projects:",
        "back": "⬅ Back",
        "reviews_btn": "⭐ Reviews",
        "faq": FAQ_TEXT_EN,
        "cv_caption": "📄 Erion Nezha's CV — Software Developer\nExperience, skills and projects — in one document.",
        "cv_missing": "📄 The CV isn't available here right now — ask Erion via 💬 <b>Talk to Erion</b>.",
        "cv_failed": "📄 The CV couldn't be sent right now — ask Erion via 💬 <b>Talk to Erion</b>.",
        "card_text": "🎴 <b>Erion Nezha</b> — Software Developer\nTirana, Albania\n\nSave my contacts:",
        "card_img_btn": "🖼 Card as image",
        "card_img_caption": "🎴 Erion Nezha's business card — save it or forward it to someone looking for my services.\nScanning the QR code leads to the private client portal.",
        "card_img_missing": "🖼 The card image isn't available right now — please use the card links above.",
        "card_img_failed": "🖼 The card couldn't be sent right now — please use the card links above.",
        "access_admin": "🔐 You are the admin — unlimited access.",
        "access_text": "🔐 <b>Your access</b>\n\n• Status: ✅ Active\n• Expires on: <b>{date}</b> ({days} days left)\n• Service: {service}\n\nTo extend it, message Erion via 💬 <b>Talk to Erion</b>.",
        "brief_title": "📝 <b>New project</b>\n\nWhat kind of project is it?",
        "brief_desc_q": "Describe the project: what should it do, who is it for, which pages or features do you have in mind?",
        "brief_budget_q": "Roughly, what is your budget?",
        "brief_deadline_q": "When do you need it ready? (e.g. within the month / I have a date)",
        "brief_contact_q": "Your contact (phone or email):",
        "brief_sent": "✅ <b>Your brief has been sent!</b>\n\nErion will read it and reply here with the next steps and the quote. Thank you for your trust!",
        "brief_daily": "⏳ <b>You've reached the daily brief limit.</b>\n\nProject briefs have a daily limit. A new brief can be started tomorrow — for anything urgent use 💬 <b>Talk to Erion</b>.",
        "projects_header": "🚧 <b>My project</b> — work progress:",
        "projects_empty": "🚧 <b>My project</b>\n\nYou don't have an active project yet.\n\nWhen you start a project with 📝 <b>Start a project</b>, you'll see its progress here, stage by stage, all the way to delivery.",
        "project_updated": "🕒 Updated on: {date}",
        "project_update_title": "🚧 <b>Project update</b>",
        "project_finish": "🎉 <b>Your project is finished!</b>\n\n🚧 <b>{title}</b>\n\nThe work has been delivered successfully. Thank you for your trust — for anything else, my door here is always open. ✨",
        "book_start": "🗓 <b>Book a consultation</b>\n\nPick the service you'd like to talk about:",
        "book_pick_slot": "🗓 <b>Pick a time slot</b> that suits you:",
        "book_no_slots": "🗓 <b>Book a consultation</b>\n\nThere are no free slots at the moment.\n\nTry again later, or write directly via 💬 <b>Talk to Erion</b> — we'll find a time together.",
        "book_pending": "⏳ <b>You already have a consultation request pending.</b>\n\nWhen Erion reviews it, you'll be notified here. For anything urgent use 💬 <b>Talk to Erion</b>.",
        "book_sent": "✅ <b>Your consultation request has been sent.</b>\n\nErion will review it and confirm the time here. Thank you!",
        "book_taken": "⚠️ That slot was just taken by someone else.\n\nPlease pick another slot:",
        "book_approved": "✅ <b>Consultation confirmed!</b>\n\n💼 Service: {service}\n🗓 Time: <b>{slot}</b>\n\nYou'll receive a reminder before the meeting. If the time no longer suits you, let Erion know via 💬 <b>Talk to Erion</b>.",
        "book_rejected": "🗓 <b>About your consultation request</b>\n\nSorry — the slot <b>{slot}</b> for {service} is no longer possible.\n\nTry another slot under 🗓 <b>Book a consultation</b>, or write to Erion via 💬 <b>Talk to Erion</b> and we'll find one together.",
        "reminder_booking_client": "⏰ <b>Reminder about your consultation</b>\n\n💼 Service: {service}\n🗓 Time: <b>{slot}</b>\n\nErion is expecting you here in this chat — be ready a little before the time. If you can't make it, let him know via 💬 <b>Talk to Erion</b>.",
        "expiry_client": "⏰ <b>Your access is coming to an end</b>\n\nYour private portal expires on <b>{date}</b>.\n\nIf you'd like to extend it, or you have a new project in mind, message Erion via 💬 <b>Talk to Erion</b>.\n\nThank you for being one of my clients! ✨",
        "talk_start": "💬 <b>You are in a direct chat with Erion.</b>\nWrite your message — it reaches him right away and his reply comes back here.\nTo return to the menu: /ndalo",
        "talk_stop": "You're back at the menu 👇",
        "talk_sent": "✔️ Sent to Erion.",
        "talk_send_fail": "⚠️ Sending failed — please try again.",
        "talk_media_hint": "To send photos, voice or documents, first turn on 💬 <b>Talk to Erion</b> from the menu.",
        "flow_needs_text": "This flow expects text — type your answer, or /anulo to go back.",
        "menu_prompt": "Pick from the menu below 👇",
        "admin_says": "💬 <b>Erion:</b>\n{text}",
        "cancelled": "Cancelled.",
        "lang_choose": "🌍 <b>Gjuha / Language</b>\n\nChoose the interface language:",
        "review_ask": "⭐ <b>How would you rate the work on the project “{title}”?</b>\n\nTap the stars below — your review helps me improve and, with my approval, it may appear among the client reviews.",
        "review_skipped": "👍 No problem — thank you anyway!",
        "review_skip": "Skip",
        "review_comment_q": "⭐ Thank you! If you'd like, add a short comment (or skip):",
        "review_thanks": "⭐ <b>Thank you for your review!</b>\n\nYour review was saved and, after a quick check, it may appear among the client reviews.",
        "ics_caption": "📅 Add the consultation to your calendar with one tap — open this file on your phone.",
        "pdf_caption": "🧾 The preliminary proposal for your project — a non-binding summary. The final offer follows our discussion.",
        "gcal_btn": "📅 Google Calendar",
        # pack 3: simple menu, gallery, web app, agreement, work hours
        "menu_more": "☰ More",
        "menu_back": "⬅ Back",
        "works_gallery": "📸 Gallery",
        "works_gallery_empty": "The gallery is being prepared — soon you'll see real screenshots of my work here.",
        "home_webapp": "🖥 Visual portal",
        "home_webapp_text": "🖥 <b>Visual portal</b>\nMy services, work and page — in a single view, without leaving Telegram:",
        "agreement_subject_default": "the agreed services",
        "agreement_intro": "✍ <b>Cooperation agreement</b>\n\nErion proposes a cooperation agreement for “{title}”.\n\nPlease read the terms below and, if you agree, tap the acceptance button.",
        "agreement_terms": (
            "<b>Terms of cooperation</b>\n"
            "• Scope: the work described in your brief and proposal, as confirmed in our conversation.\n"
            "• Process: the work proceeds in phases and progress is tracked under “My project” in this portal.\n"
            "• Payment: under the terms agreed between us in conversation.\n"
            "• Revisions: reasonable revisions within the agreed scope are included.\n"
            "• Delivery: according to the project plan tracked in the portal.\n"
            "• After delivery: a support period for fixing defects, as agreed.\n"
            "• Communication: both sides communicate through this portal."
        ),
        "agreement_accept": "✅ I accept the terms",
        "agreement_decline": "❌ Decline",
        "agreement_accepted_msg": "✅ <b>The agreement was accepted.</b>\n\nYour agreement document follows below — keep it for your records. Thank you for your trust!",
        "agreement_declined_msg": "No problem — the agreement was not accepted and Erion has been notified. For any clarification, write via 💬 <b>Talk to Erion</b>.",
        "agreement_done": "This agreement has already been decided.",
        "agreement_pdf_caption": "✍ Your cooperation agreement — accepted digitally in this portal.",
        "after_hours": "Thank you for your message — it was received and forwarded to Erion. His working hours are on weekdays; he'll reply as soon as working hours start. For anything urgent, leave your message here — he sees everything in order.",
        # pack 4: Home/Guide, booking cancel, tour, project start
        "menu_home": "🏠 Home",
        "menu_guide": "🧭 Guide",
        "book_cancel_btn": "❌ Cancel booking",
        "book_cancelled": "🗓 <b>Your consultation request was cancelled.</b>\n\nErion has been notified. If you'd like another time, start again from 🗓 <b>Book a consultation</b>.",
        "book_cancel_done": "This booking has already been decided.",
        "project_started": "🚧 <b>Your project has started!</b>\n\nErion has opened your project — its progress is tracked here, stage by stage.",
        "tour_s1": "🧭 <b>Welcome to your portal tour</b>\n\n💼 <b>Services</b>\nHere you'll find everything I build: websites, apps, Telegram bots, design and marketing — with details for each service.",
        "tour_s2": "🗂 <b>Work samples</b> and 📸 <b>the Gallery</b>\nSee real work — finished and live — with actual screenshots of the projects, not just descriptions.",
        "tour_s3": "📝 <b>Start a project</b>\nWhen you're ready, fill in the short brief: type, description, budget and deadline. I'll read it and reply with the next steps.",
        "tour_s4": "🗓 <b>Book a consultation</b> and 💬 <b>Talk to Erion</b>\nPick a free slot for a consultation, or write directly in the chat — your messages reach me straight away.",
        "tour_next": "➡ Next",
        "tour_done_btn": "✅ Got it",
        "tour_closing": "🧭 <b>You're all set!</b>\n\nNow you know your portal. For anything at all, I'm one message away — 💬 <b>Talk to Erion</b>.",
        # UX fix: menu labels interrupt any active flow
        "flow_interrupted": "I left the flow you were in — here you are now.",
        "brief_pick_hint": "Pick one of the buttons above — or type /anulo to leave it.",
    },
}


def t(lang: str, key: str, **kw) -> str:
    """Teksti statik sipas gjuhës; 'sq' është gjithmonë fallback-u."""
    table = STR.get(lang) or STR["sq"]
    s = table.get(key)
    if s is None:
        s = STR["sq"][key]
    return s.format(**kw) if kw else s


def ulang(user) -> str:
    """Gjuha e ndërfaqes për përdoruesin (admini gjithmonë shqip)."""
    if user is None or is_admin(user):
        return "sq"
    return store.get_lang(user.id)


def services_for(lang: str):
    return SERVICES_EN if lang == "en" else SERVICES


def svc_name(sid: str, lang: str = "sq") -> str:
    return dict(services_for(lang)).get(sid, sid)


def svc_details(sid: str, lang: str = "sq") -> str:
    table = SERVICE_DETAILS_EN if lang == "en" else SERVICE_DETAILS
    return table.get(sid, "")


def budgets_for(lang: str):
    return BUDGETS_EN if lang == "en" else BUDGETS


def work_categories_for(lang: str):
    return WORK_CATEGORIES_EN if lang == "en" else WORK_CATEGORIES


def works_for(lang: str):
    return WORKS_EN if lang == "en" else WORKS


def stages_for(lang: str):
    return PROJECT_STAGES_EN if lang == "en" else PROJECT_STAGES


def reviews_text(lang: str = "sq") -> str:
    """Ekrani i vlerësimeve: vlerësimet e miratuara të botit (më të
    rejat sipër) + përmbledhjet e Google Play që mbeten gjithmonë."""
    if lang == "en":
        header, play = REVIEWS_HEADER_EN, REVIEWS_PLAY_EN
    else:
        header, play = REVIEWS_HEADER, REVIEWS_PLAY
    parts = [header]
    for r in store.list_reviews(status="approved")[:5]:
        entry = "⭐" * max(0, min(5, _safe_int(r.get("stars"), 5)))
        if r.get("text"):
            entry += "\n" + _esc(r["text"])
        first = (r.get("name") or "").split()[0] if r.get("name") else ""
        if first:
            entry += f"\n<i>— {_esc(first)}</i>"
        parts.append(entry)
    parts.append(play)
    return "\n\n".join(parts)


# ---------------------------------------------------------------- ndihmës
def is_admin(user) -> bool:
    return bool(user) and user.id == ADMIN_ID


def client_rec(user):
    if is_admin(user):
        return {"name": "Erion (admin)", "expires_at": None}
    return store.get_client(user.id)


def has_access(user) -> bool:
    return client_rec(user) is not None


def fmt_date(iso_s):
    dt = parse_iso(iso_s)
    return dt.strftime("%d.%m.%Y") if dt else "—"


def lock_kb(lang: str = "sq"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "lock_btn_code"), callback_data="gate:code")],
        [InlineKeyboardButton(t(lang, "lock_btn_req"), callback_data="gate:req")],
        [InlineKeyboardButton("🇦🇱 Shqip", callback_data="lang:sq"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
    ])


def lang_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇦🇱 Shqip", callback_data="lang:sq"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
    ]])


async def show_lock(update: Update, context: ContextTypes.DEFAULT_TYPE, note: str = ""):
    lang = ulang(update.effective_user)
    body = t(lang, "lock_text")
    text = (note + "\n\n" + body) if note else body
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text, parse_mode="HTML", reply_markup=lock_kb(lang))
    else:
        await update.effective_message.reply_text(
            text, parse_mode="HTML", reply_markup=lock_kb(lang))


async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = ulang(user)
    name = _esc((user.first_name or "klient").strip())
    msg = update.effective_message
    await msg.reply_text(
        t(lang, "welcome", name=name, status=store.get_status()),
        parse_mode="HTML", reply_markup=client_kb(lang))
    if not is_admin(user):
        # paketa 3 (F2): butoni i Mini Web App-it — vetëm te faqja
        # kryesore e klientit (vizitori sheh vetëm derën, admini panelin)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            t(lang, "home_webapp"), web_app=WebAppInfo(url=WEBAPP_URL))]])
        await msg.reply_text(t(lang, "home_webapp_text"), parse_mode="HTML",
                             reply_markup=kb)
    if is_admin(user):
        await msg.reply_text(
            "🛠 <b>Panel admini</b>\n"
            "/krijo_kod — kod i ri unik (opsione: /krijo_kod 30 emri-klientit)\n"
            "/kodet — kodet e krijuara dhe statusi i tyre\n"
            "/klientet — klientët aktivë\n"
            "/revoko &lt;user_id&gt; — hiq aksesin menjëherë\n"
            "/zgjat &lt;user_id&gt; [ditë] — zgjat aksesin (default 30)\n"
            "/backup — merr kopjen aktuale të të dhënave (data.json)\n"
            "/statusi [teksti] — statusi i disponueshmërisë që shohin klientët\n"
            "/projekt &lt;user_id&gt; &lt;titulli&gt; — krijon projekt për klientin\n"
            "/faza &lt;user_id&gt; &lt;faza&gt; — ndërron fazën (Briefi, Dizajni, "
            "Zhvillimi, Testimi, Dorëzimi)\n"
            "/shenim_projekti &lt;user_id&gt; &lt;teksti&gt; — shënim te «Projekti im»\n"
            "/projekt_fund &lt;user_id&gt; — mbyll projektin aktiv të klientit\n"
            "/slot &lt;YYYY-MM-DD&gt; &lt;HH:MM&gt; — shton orar konsulte\n"
            "/slotet — oraret e konsultave dhe gjendja e tyre\n"
            "/slot_fshi &lt;slot_id&gt; — fshin një orar të lirë\n"
            "/njoftim &lt;teksti&gt; — broadcast te të gjithë klientët aktivë\n"
            "/pergjigju &lt;user_id&gt; — mesazhi yt tjetër i shkon atij klienti\n"
            "/vleresime — vlerësimet e klientëve në pritje (publiko/refuzo)\n"
            "/mireseardhje — vendos/ndryshon mesazhin zanor të mirëseardhjes "
            "(klientët e rinj e marrin automatikisht pas aktivizimit)\n"
            "/hiq_mireseardhjen — heq mesazhin zanor të mirëseardhjes\n"
            "/marreveshje &lt;user_id&gt; — dërgo marrëveshjen dixhitale "
            "të bashkëpunimit për projektin e fundit të klientit\n"
            f"/orari &lt;HH:MM-HH:MM&gt; — orari i punës (aktual: "
            f"{store.get_work_settings()['start']}–"
            f"{store.get_work_settings()['end']}, fundjava "
            f"{'e hapur' if store.get_work_settings()['weekend'] else 'e mbyllur'}); "
            "jashtë tij klienti merr përgjigjen automatike\n"
            "/orari_fundjave on|off — hap/mbyll fundjavën si orar pune\n"
            "/raport — raporti javor (këtë javë) + pikat në pritje\n"
            "/dosja &lt;user_id&gt; — dosja e plotë e klientit (paketa 4): "
            "aksesi, projektet, rezervimet, marrëveshja, vlerësimet, "
            "shënimet e tua private\n"
            "/shenim_klienti &lt;user_id&gt; &lt;teksti&gt; — shënim "
            "privat te dosja e klientit (paketa 4)",
            parse_mode="HTML")


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str, markup=None):
    try:
        await context.bot.send_message(ADMIN_ID, text, parse_mode="HTML",
                                       reply_markup=markup)
    except Exception as e:  # admini s'e ka hapur botin ende etj.
        log.warning("notify_admin dështoi: %s", e)


async def send_backup(context: ContextTypes.DEFAULT_TYPE, caption: str):
    """Fiks 4: dërgon data.json aktual te admini si dokument (backup)."""
    try:
        if not os.path.exists(store.path):
            store._save()  # file-i krijohet në mutacionin e parë; materializoje
        with open(store.path, "rb") as f:
            await context.bot.send_document(
                ADMIN_ID, document=f, filename="enclient-data.json",
                caption=caption)
    except Exception as e:
        log.warning("backup dështoi: %s", e)


# ---------------------------------------------------------------- F3: gjuha
async def show_lang_chooser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🌍 Gjuha / Language — zgjedhja e gjuhës nga zona e klientit."""
    if not await guard_client(update):
        return
    lang = ulang(update.effective_user)
    await update.effective_message.reply_text(
        t(lang, "lang_choose"), parse_mode="HTML", reply_markup=lang_kb())


async def lang_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ndërrimi i gjuhës (dera + zona e klientit): zgjedhja ruhet te
    përdoruesi dhe kalon në regjistrin e klientit pas aktivizimit."""
    q = update.callback_query
    await q.answer()
    code = (q.data or "").split(":", 1)[1] if ":" in (q.data or "") else "sq"
    store.set_lang(q.from_user.id, code)
    if has_access(q.from_user):
        await show_home(update, context)
    else:
        await show_lock(update, context)


# ---------------------------------------------------------------- F5: zëri i mirëseardhjes
async def send_welcome_voice(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Dërgon mesazhin zanor të mirëseardhjes. Përparësia:
    1) file_id i regjistruar nga admini (/mireseardhje);
    2) zëri i paketës assets/welcome.ogg (Azure Ilir) — pas dërgimit
       të parë, file_id që kthen Telegrami ruhet në settings dhe
       dërgimet e tjera bëhen me të.
    Dështimi (file_id i vjetër etj.) kapet në heshtje —
    aktivizimi s'prishet kurrë prej tij."""
    fid = store.get_welcome_voice()
    if fid:
        try:
            await context.bot.send_voice(user_id, voice=fid)
        except Exception as e:
            log.warning("zëri i mirëseardhjes s'u dërgua te %s: %s",
                        user_id, e)
        return
    if not os.path.isfile(WELCOME_VOICE_PATH):
        return
    try:
        with open(WELCOME_VOICE_PATH, "rb") as f:
            msg = await context.bot.send_voice(user_id, voice=f)
        new_fid = getattr(getattr(msg, "voice", None), "file_id", None)
        if new_fid:
            store.set_welcome_voice(new_fid)
    except Exception as e:
        log.warning("zëri i paketës s'u dërgua te %s: %s", user_id, e)


async def adm_voice_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F5: /mireseardhje — tregon gjendjen dhe kap zërin e radhës
    të adminit si mesazh mirëseardhjeje për klientët e rinj."""
    if not is_admin(update.effective_user):
        return
    fid = store.get_welcome_voice()
    has_asset = os.path.isfile(WELCOME_VOICE_PATH)
    if fid:
        state = ("✅ <b>Aktiv (zëri yt i regjistruar)</b> — klientët e "
                 "rinj e marrin automatikisht pas aktivizimit.")
    elif has_asset:
        state = ("✅ <b>Aktiv (zëri Ilir nga paketa)</b> — klientët e "
                 "rinj marrin zërin e paketës, derisa të regjistrosh "
                 "zërin tënd.")
    else:
        state = "ℹ️ <b>Joaktiv</b> — s'ka mesazh zanor mirëseardhjeje."
    pkg_line = ("\nZëri i paketës (Ilir) është i përfshirë si "
                "parazgjedhje." if has_asset else "")
    context.user_data["capture_voice"] = True
    await update.message.reply_text(
        "🎙 <b>Mesazhi zanor i mirëseardhjes</b>\n\n"
        f"{state}{pkg_line}\n\n"
        "Dërgo tani një <b>mesazh zanor</b> — ai do të ruhet dhe "
        "klientët e rinj do ta marrin pas aktivizimit.\n"
        "/anulo për ta lënë siç është.", parse_mode="HTML")


async def adm_voice_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F5: /hiq_mireseardhjen — pastron zërin e mirëseardhjes."""
    if not is_admin(update.effective_user):
        return
    if store.get_welcome_voice():
        store.set_welcome_voice(None)
        if os.path.isfile(WELCOME_VOICE_PATH):
            await update.message.reply_text(
                "🎙 Zëri yt u hoq — klientët e rinj tani marrin "
                "zërin e paketës (Ilir).")
        else:
            await update.message.reply_text(
                "🎙 Mesazhi zanor i mirëseardhjes u hoq — klientët "
                "e rinj s'e marrin më.")
    else:
        await update.message.reply_text(
            "🎙 S'ka mesazh zanor mirëseardhjeje të vendosur.")


# ---------------------------------------------------------------- paketa 4: turi udhëzues i klientit të ri
TOUR_STEP_KEYS = ("tour_s1", "tour_s2", "tour_s3", "tour_s4")


def _tour_text(lang: str, step: int) -> str:
    """Teksti i hapit të turit + treguesi i progresit VETËM me
    simbole (●/○) — pa shifra (urdhri 'mos vendos shifra')."""
    step = max(1, min(len(TOUR_STEP_KEYS), int(step)))
    dots = "●" * step + "○" * (len(TOUR_STEP_KEYS) - step)
    return dots + "\n\n" + t(lang, TOUR_STEP_KEYS[step - 1])


def _tour_kb(lang: str, step: int):
    step = max(1, min(len(TOUR_STEP_KEYS), int(step)))
    if step < len(TOUR_STEP_KEYS):
        return InlineKeyboardMarkup([[InlineKeyboardButton(
            t(lang, "tour_next"), callback_data=f"tour:next:{step + 1}")]])
    return InlineKeyboardMarkup([[InlineKeyboardButton(
        t(lang, "tour_done_btn"), callback_data="tour:done")]])


async def start_tour(context: ContextTypes.DEFAULT_TYPE, user_id: int,
                     lang: str = None):
    """Nis turin udhëzues (hapi i parë) si mesazh i ri — pas
    aktivizimit të klientit të ri dhe nga butoni 🧭 Udhëzuesi."""
    lang = lang or store.get_lang(user_id)
    try:
        await context.bot.send_message(
            user_id, _tour_text(lang, 1), parse_mode="HTML",
            reply_markup=_tour_kb(lang, 1))
    except Exception as e:
        log.warning("turi s'u nis për %s: %s", user_id, e)


async def _maybe_start_tour(context: ContextTypes.DEFAULT_TYPE,
                            user_id: int):
    """Pas aktivizimit: turi nis VETËM nëse klienti s'e ka përfunduar
    ndonjëherë (tour_done). Dështimet kapen në heshtje."""
    try:
        rec = store.get_client_any(user_id) or {}
        if not rec.get("tour_done"):
            await start_tour(context, user_id, store.get_lang(user_id))
    except Exception as e:
        log.warning("kontrolli i turit dështoi për %s: %s", user_id, e)


async def tour_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hapat e turit (tour:next:<n>) + mbyllja (tour:done): mesazhi
    i turit EDITOHET hap pas hapi; në fund shënohet tour_done."""
    q = update.callback_query
    user = q.from_user
    lang = ulang(user)
    if not has_access(user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    data = q.data or ""
    if data == "tour:done":
        store.set_tour_done(user.id, True)
        try:
            await q.edit_message_text(t(lang, "tour_closing"),
                                      parse_mode="HTML")
        except Exception:
            pass
        return
    try:
        step = int(data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        return
    if not (1 <= step <= len(TOUR_STEP_KEYS)):
        return
    try:
        await q.edit_message_text(_tour_text(lang, step),
                                  parse_mode="HTML",
                                  reply_markup=_tour_kb(lang, step))
    except Exception:
        pass


# ---------------------------------------------------------------- /start
# Payload-et e rrjedhës nga Mini Web App-i (addendum): fjalët e
# veprimit kontrollohen PARA kodit dhe trajtohen si kod VETËM kur
# payload-i ka formatin e saktë të kodit (EN + 8 shenja të alfabetit).
FLOW_PAYLOADS = ("brief", "book", "talk", "works", "services")
_CODE_FORMAT = re.compile(r"EN[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{8}")


async def _start_flow_payload(update: Update,
                              context: ContextTypes.DEFAULT_TYPE,
                              payload: str):
    """Hap rrjedhën përkatëse për klientin aktiv (ose adminin) nga
    payload-i i deep-link-ut të Web App-it."""
    if payload == "brief":
        await brief_menu_start(update, context)
    elif payload == "book":
        await booking_menu_start(update, context)
    elif payload == "talk":
        await talk_start(update, context)
    elif payload == "works":
        await show_works(update, context)
    elif payload == "services":
        await show_services(update, context)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.pop("talk", None)
    context.user_data.pop("reply_to", None)
    context.user_data.pop("flow", None)
    payload = ((context.args[0] if context.args else "") or "").strip()
    low = payload.lower()
    if low in FLOW_PAYLOADS:
        # Fjalë rrjedhe, JO kod: për vizitorin shfaqet vetëm kyçja dhe
        # tentativat e kodit NUK preken; për klientin hapet rrjedha.
        if has_access(user):
            await _start_flow_payload(update, context, low)
        else:
            await show_lock(update, context)
        return
    # Deep-link nga bio/DM: t.me/<bot>?start=EN-XXXX-XXXX → zhbllokim direkt
    if payload and not has_access(user) \
            and _CODE_FORMAT.fullmatch(normalize_code(payload)):
        await try_redeem(update, context, payload)
        return
    if has_access(user):
        await show_home(update, context)
    else:
        await show_lock(update, context)


# ---------------------------------------------------------------- kodi
async def gate_code_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ulang(q.from_user)
    if has_access(q.from_user):
        await show_home(update, context)
        return
    if store.is_locked(q.from_user.id):
        await q.message.reply_text(t(lang, "locked_temp_code"))
        return
    context.user_data["flow"] = {"kind": "code"}
    await q.message.reply_text(t(lang, "code_prompt"), parse_mode="HTML")


async def try_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    user = update.effective_user
    lang = ulang(user)
    if store.is_locked(user.id):
        await update.effective_message.reply_text(t(lang, "locked_temp"))
        return
    status, rec = store.redeem_code(code, user.id)
    if status == "ok":
        store.clear_fails(user.id)
        store.activate_client(user.id, user.first_name or "", user.username or "",
                              "", DEFAULT_DAYS, via="code",
                              expires_at=parse_iso(rec["expires_at"]))
        lang = ulang(user)  # regjistri i ri mund ta ketë gjuhën të ruajtur
        await update.effective_message.reply_text(
            t(lang, "code_accepted", date=fmt_date(rec["expires_at"])),
            parse_mode="HTML")
        await notify_admin(context,
                           f"🔓 <b>Klient i ri u zhbllokua me kod</b>\n"
                           f"👤 {_esc(user.first_name)} (@{_esc(user.username) or '—'}, id {user.id})\n"
                           f"📝 Shënimi i kodit: {_esc(rec.get('note')) or '—'}")
        await show_home(update, context)
        await send_welcome_voice(context, user.id)  # F5
        await _maybe_start_tour(context, user.id)  # paketa 4: turi
    else:
        await _gate_fail(update, context, status)


async def _gate_fail(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str):
    """Dështim te dera: vizitori sheh VETËM mesazhin gjenerik (Fiks 3);
    arsyeja e saktë ruhet dhe i raportohet vetëm adminit."""
    user = update.effective_user
    lang = ulang(user)
    who = f"{_esc(user.first_name)} (@{_esc(user.username) or '—'}, id {user.id})"
    locked = store.register_fail(user.id, status=status)
    await update.effective_message.reply_text(t(lang, "gate_fail"), parse_mode="HTML")
    if status == "bound_other":
        # sinjali i vjedhjes/përcjelljes së kodit — njoftim i menjëhershëm
        await notify_admin(
            context,
            "🚨 <b>Tentativë me kodin e një klienti tjetër</b>\n"
            f"👤 {who}\n"
            "Kodi i përdorur është i lidhur me një llogari tjetër — sinjal "
            "i mundshëm përcjelljeje ose vjedhjeje të kodit. Vizitorit iu "
            "tregua vetëm mesazhi gjenerik.")
    if locked:
        await update.effective_message.reply_text(t(lang, "too_many"))
        last = store.last_fail_status(user.id) or status
        label = FAIL_STATUS_LABELS.get(last, last or "—")
        await notify_admin(
            context,
            f"🚨 <b>Kyçje pas 3 tentativave të dështuara</b>\n"
            f"👤 {who}\n"
            f"ℹ️ Arsyeja e tentativës së fundit: <b>{label}</b>")


async def code_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await try_redeem(update, context, (update.message.text or "").strip())
    if has_access(update.effective_user) or store.is_locked(update.effective_user.id):
        context.user_data.pop("flow", None)
        return
    await update.message.reply_text(t(ulang(update.effective_user), "code_retry"))


# ---------------------------------------------------------------- kërkesa për shërbim
def service_kb(prefix: str, lang: str = "sq"):
    rows = [[InlineKeyboardButton(label, callback_data=f"{prefix}:{sid}")]
            for sid, label in services_for(lang)]
    return InlineKeyboardMarkup(rows)


async def gate_req_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ulang(q.from_user)
    if has_access(q.from_user):
        await show_home(update, context)
        return
    block = store.request_block(q.from_user.id)  # anti-spam (Fiks 2)
    if block == "pending":
        await q.message.reply_text(t(lang, "req_pending"), parse_mode="HTML")
        return
    if block == "daily":
        await q.message.reply_text(t(lang, "req_daily"), parse_mode="HTML")
        return
    context.user_data["flow"] = {"kind": "req", "step": "service"}
    context.user_data["req"] = {}
    await q.message.reply_text(
        t(lang, "req_title"), parse_mode="HTML",
        reply_markup=service_kb("svc", lang))


async def req_service_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    flow = context.user_data.get("flow") or {}
    if flow.get("kind") != "req":
        return
    sid = q.data.split(":", 1)[1]
    context.user_data.setdefault("req", {})["service"] = SERVICE_NAMES.get(sid, sid)
    flow["step"] = "name"
    await q.message.reply_text(
        t(ulang(q.from_user), "req_name"), parse_mode="HTML")


async def req_text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = context.user_data["flow"]
    step = flow.get("step")
    lang = ulang(update.effective_user)
    text = (update.message.text or "").strip()
    if step == "service":
        # Hapi pret buton inline (svc:); teksti i lirë → ri-pyetje + hint,
        # jo heshtje (auditi i rrugëve pa përgjigje).
        await update.message.reply_text(
            t(lang, "req_title") + "\n\n" + t(lang, "brief_pick_hint"),
            parse_mode="HTML", reply_markup=service_kb("svc", lang))
    elif step == "name":
        context.user_data["req"]["name"] = text
        flow["step"] = "desc"
        await update.message.reply_text(t(lang, "req_desc"), parse_mode="HTML")
    elif step == "desc":
        context.user_data["req"]["desc"] = text
        flow["step"] = "contact"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            t(lang, "skip"), callback_data="req:nocontact")]])
        await update.message.reply_text(
            t(lang, "req_contact"), parse_mode="HTML", reply_markup=kb)
    elif step == "contact":
        context.user_data["req"]["contact"] = text
        await req_finish(update, context)


async def req_contact_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    flow = context.user_data.get("flow") or {}
    if flow.get("kind") != "req" or flow.get("step") != "contact":
        return
    context.user_data.setdefault("req", {})["contact"] = ""
    await req_finish(update, context)


async def req_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = ulang(user)
    d = context.user_data.get("req", {})
    block = store.request_block(user.id)  # kontroll i dytë, në krijim (Fiks 2)
    if block:
        await update.effective_message.reply_text(
            t(lang, "req_pending" if block == "pending" else "req_daily"),
            parse_mode="HTML")
        context.user_data.pop("req", None)
        context.user_data.pop("flow", None)
        return
    req_id = store.create_request(
        user.id, d.get("name") or user.first_name or "", user.username or "",
        d.get("service", ""), d.get("contact", ""), d.get("desc", ""))
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Mirato", callback_data=f"adm:ok:{req_id}"),
        InlineKeyboardButton("❌ Refuzo", callback_data=f"adm:no:{req_id}"),
    ]])
    await notify_admin(
        context,
        "📩 <b>KËRKESË E RE PËR SHËRBIM</b>\n"
        f"👤 {_esc(d.get('name') or user.first_name)} (@{_esc(user.username) or '—'}, id {user.id})\n"
        f"💼 Shërbimi: {_esc(d.get('service')) or '—'}\n"
        f"📝 Nevoja: {_esc(_trunc(d.get('desc'), 900)) or '—'}\n"
        f"📞 Kontakti: {_esc(d.get('contact')) or '—'}",
        markup=kb)
    await update.effective_message.reply_text(
        t(lang, "req_sent"), parse_mode="HTML")
    context.user_data.pop("req", None)
    context.user_data.pop("flow", None)


# ---------------------------------------------------------------- vendimet e adminit
async def admin_decision_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user):
        await q.answer("Vetëm admini.", show_alert=True)
        return
    parts = (q.data or "").split(":", 2)
    if len(parts) != 3 or parts[1] not in ("ok", "no") or not parts[2]:
        await q.answer("Të dhëna të pavlefshme.", show_alert=True)
        return
    _, action, req_id = parts
    req = store.get_request(req_id)
    if not req or req["status"] != "pending":
        await q.answer("Kërkesa është trajtuar tashmë.")
        return
    await q.answer()
    if action == "no":
        store.set_request_status(req_id, "rejected")
        try:
            await q.edit_message_text(q.message.text + "\n\n❌ <b>REFUZUAR</b>",
                                      parse_mode="HTML")
        except Exception:
            pass
        try:
            await context.bot.send_message(
                req["user_id"],
                "Të faleminderit për kërkesën. Për momentin nuk mund ta marr "
                "përsipër këtë projekt — të uroj suksese! Nëse ndryshon "
                "nevoja, më shkruaj në Instagram: @erjonixx")
        except Exception as e:
            log.warning("refuzimi s'u dërgua: %s", e)
        return
    # miratim → aktivizim i drejtpërdrejtë i klientit (+30 ditë)
    store.set_request_status(req_id, "approved")
    client = store.activate_client(req["user_id"], req["name"], req["username"],
                                   req["service"], DEFAULT_DAYS, via="approval")
    try:
        await q.edit_message_text(q.message.text + "\n\n✅ <b>MIRATUAR</b> — klienti u aktivizua.",
                                  parse_mode="HTML")
    except Exception:
        pass
    clang = store.get_lang(req["user_id"])
    try:
        await context.bot.send_message(
            req["user_id"],
            t(clang, "approved_welcome", date=fmt_date(client['expires_at']))
            + t(clang, "welcome",
                name=_esc((req["name"] or "klient").split()[0]),
                status=store.get_status()),
            parse_mode="HTML", reply_markup=client_kb(clang))
        await send_welcome_voice(context, req["user_id"])  # F5
        await _maybe_start_tour(context, req["user_id"])  # paketa 4: turi
    except Exception as e:
        log.warning("miratimi s'u dërgua: %s", e)
    # Fiks 4: backup automatik pas aktivizimit të klientit të ri
    await send_backup(
        context,
        "💾 Backup automatik — u aktivizua klienti i ri: "
        f"{req['name'] or '—'} (@{req['username'] or '—'}). "
        f"Klientë gjithsej: {len(store.list_clients())}.")


# ---------------------------------------------------------------- menuja e klientit
async def guard_client(update: Update) -> bool:
    if has_access(update.effective_user):
        return True
    lang = ulang(update.effective_user)
    await show_lock(update, None, t(lang, "lock_note_need_code"))
    return False


async def show_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    lang = ulang(update.effective_user)
    await update.effective_message.reply_text(
        t(lang, "services_header"),
        parse_mode="HTML", reply_markup=service_kb("det", lang))


async def service_detail_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    sid = q.data.split(":", 1)[1]
    details = svc_details(sid, lang)
    if not details:
        # id shërbimi i panjohur (buton i vjetër/i modifikuar): teksti
        # bosh do ta rrëzonte dërgimin — ri-pyet me listën e shërbimeve
        await q.message.reply_text(
            t(lang, "services_header"), parse_mode="HTML",
            reply_markup=service_kb("det", lang))
        return
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        t(lang, "service_start_btn"), callback_data="cli:brief")]])
    await q.message.reply_text(details, parse_mode="HTML",
                               reply_markup=kb)


def works_categories_kb(lang: str = "sq"):
    rows = [[InlineKeyboardButton(label, callback_data=f"works:{cid}")]
            for cid, label in work_categories_for(lang)]
    rows.append([InlineKeyboardButton(t(lang, "works_gallery"),
                                      callback_data="works:gallery")])
    rows.append([InlineKeyboardButton(t(lang, "reviews_btn"),
                                      callback_data="works:reviews")])
    return InlineKeyboardMarkup(rows)


def gallery_files():
    """File-t e galerisë që ekzistojnë realisht në disk, në rendin
    e qëndrueshëm GALLERY_ORDER (mungesat kapërcehen në heshtje)."""
    out = []
    for key in GALLERY_ORDER:
        path = os.path.join(GALLERY_DIR, key + ".jpg")
        if os.path.isfile(path):
            out.append((key, path))
    return out


async def _send_gallery(context, user_id: int, lang: str,
                        reply_to_msg=None):
    """Paketa 3 (F3): albumi vizual i punëve — NJË media group me
    pamjet reale të sajteve (caption = emri shfaqës i projektit)."""
    files = gallery_files()[:10]
    if not files:
        if reply_to_msg is not None:
            await reply_to_msg.reply_text(t(lang, "works_gallery_empty"))
        return
    opened = []
    try:
        media = []
        for key, path in files:
            f = open(path, "rb")
            opened.append(f)
            media.append(InputMediaPhoto(
                f, caption=GALLERY_NAMES.get(key, key)))
        await context.bot.send_media_group(user_id, media=media)
    except Exception as e:
        log.warning("galeria s'u dërgua te %s: %s", user_id, e)
        if reply_to_msg is not None:
            await reply_to_msg.reply_text(t(lang, "works_gallery_empty"))
    finally:
        for f in opened:
            try:
                f.close()
            except Exception:
                pass


def works_category_kb(cid, lang: str = "sq"):
    rows = [[InlineKeyboardButton(lbl, url=u)]
            for lbl, u in works_for(lang)[cid]]
    rows.append([InlineKeyboardButton(t(lang, "back"),
                                      callback_data="works:cat")])
    return InlineKeyboardMarkup(rows)


async def show_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    lang = ulang(update.effective_user)
    await update.effective_message.reply_text(
        t(lang, "works_header"), parse_mode="HTML",
        reply_markup=works_categories_kb(lang))


async def works_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback-et e shembujve të punës: kategori / vlerësime / mbrapa.
    Vetëm klientë të zhbllokuar — vizitori merr vetëm sinjalin e kyçjes."""
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    data = (q.data or "").split(":", 1)[1] if ":" in (q.data or "") else "cat"
    if data == "gallery":
        await _send_gallery(context, q.from_user.id, lang,
                            reply_to_msg=q.message)
    elif data == "reviews":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            t(lang, "back"), callback_data="works:cat")]])
        await q.message.reply_text(reviews_text(lang), parse_mode="HTML",
                                   reply_markup=kb)
    elif data in WORKS:
        title = dict(work_categories_for(lang))[data]
        await q.message.reply_text(
            t(lang, "works_cat_title", title=title),
            parse_mode="HTML", reply_markup=works_category_kb(data, lang))
    else:  # "cat" → kthehu te kategoritë
        await q.message.reply_text(
            t(lang, "works_header"), parse_mode="HTML",
            reply_markup=works_categories_kb(lang))


async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    lang = ulang(update.effective_user)
    await update.effective_message.reply_text(t(lang, "faq"), parse_mode="HTML")


async def show_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📄 CV-ja ime: dërgon PDF-në e paketuar (assets/CV-Erion-Nezha.pdf).
    Vetëm klientë — vizitori s'merr as dokumentin, as përmbajtjen."""
    if not await guard_client(update):
        return
    lang = ulang(update.effective_user)
    if not os.path.isfile(CV_PATH):
        await update.effective_message.reply_text(
            t(lang, "cv_missing"), parse_mode="HTML")
        return
    try:
        with open(CV_PATH, "rb") as f:
            await context.bot.send_document(
                update.effective_user.id, document=f,
                filename="CV-Erion-Nezha.pdf", caption=t(lang, "cv_caption"))
    except Exception as e:
        log.warning("dërgimi i CV-së dështoi: %s", e)
        await update.effective_message.reply_text(
            t(lang, "cv_failed"), parse_mode="HTML")


async def show_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    lang = ulang(update.effective_user)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "card_img_btn"), callback_data="cli:cardimg")],
        [InlineKeyboardButton("🎴 Kartvizita dixhitale", url="https://erionnezha.github.io/erionxx-business-card/")],
        [InlineKeyboardButton("🌐 Portfolio", url="https://erionnezha.netlify.app")],
        [InlineKeyboardButton("💼 LinkedIn", url="https://www.linkedin.com/in/erion-nezha")],
        [InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/erjonixx/")],
    ])
    await update.effective_message.reply_text(
        t(lang, "card_text"), parse_mode="HTML", reply_markup=kb)


async def card_image_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🖼 Karta si imazh: dërgon assets/card.png (me QR te boti) si foto.
    Vetëm klientë; nëse file-i mungon, mesazh i sjellshëm (si te CV-ja)."""
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    if not os.path.isfile(CARD_PATH):
        await q.message.reply_text(t(lang, "card_img_missing"))
        return
    try:
        with open(CARD_PATH, "rb") as f:
            await context.bot.send_photo(
                q.from_user.id, photo=f, caption=t(lang, "card_img_caption"))
    except Exception as e:
        log.warning("dërgimi i kartës si imazh dështoi: %s", e)
        await q.message.reply_text(t(lang, "card_img_failed"))


async def show_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = ulang(user)
    if is_admin(user):
        await update.effective_message.reply_text(t(lang, "access_admin"))
        return
    rec = store.get_client(user.id)
    if not rec:
        await show_lock(update, context)
        return
    exp = parse_iso(rec.get("expires_at"))
    days = max(0, (exp - datetime.now(timezone.utc)).days) if exp else "—"
    await update.effective_message.reply_text(
        t(lang, "access_text", date=fmt_date(rec.get("expires_at")),
          days=days, service=_esc(rec.get("service")) or "—"),
        parse_mode="HTML")


# ---------------------------------------------------------------- brief-i i projektit
async def brief_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    if store.brief_block(q.from_user.id):  # anti-spam (Fiks 2)
        await q.message.reply_text(t(lang, "brief_daily"), parse_mode="HTML")
        return
    context.user_data["flow"] = {"kind": "brief", "step": "service"}
    context.user_data["brief"] = {}
    await q.message.reply_text(
        t(lang, "brief_title"), parse_mode="HTML",
        reply_markup=service_kb("briefsvc", lang))


async def brief_menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    lang = ulang(update.effective_user)
    if store.brief_block(update.effective_user.id):  # anti-spam (Fiks 2)
        await update.effective_message.reply_text(t(lang, "brief_daily"), parse_mode="HTML")
        return
    context.user_data["flow"] = {"kind": "brief", "step": "service"}
    context.user_data["brief"] = {}
    await update.effective_message.reply_text(
        t(lang, "brief_title"), parse_mode="HTML",
        reply_markup=service_kb("briefsvc", lang))


async def brief_service_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    flow = context.user_data.get("flow") or {}
    if flow.get("kind") != "brief":
        return
    sid = q.data.split(":", 1)[1]
    brief = context.user_data.setdefault("brief", {})
    brief["service"] = SERVICE_NAMES.get(sid, sid)   # etiketa shqip (admini)
    brief["service_key"] = sid
    flow["step"] = "desc"
    await q.message.reply_text(
        t(ulang(q.from_user), "brief_desc_q"), parse_mode="HTML")


async def brief_text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = context.user_data["flow"]
    step = flow.get("step")
    lang = ulang(update.effective_user)
    text = (update.message.text or "").strip()
    if step == "service":
        # Hapi pret buton inline (briefsvc:); teksti i lirë s'gëlltitet
        # më në heshtje — ri-dërgohet pyetja me një hint të butë.
        await update.message.reply_text(
            t(lang, "brief_title") + "\n\n" + t(lang, "brief_pick_hint"),
            parse_mode="HTML", reply_markup=service_kb("briefsvc", lang))
    elif step == "budget":
        # Edhe hapi i buxhetit pret buton (briefbud:) — njësoj si më lart.
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(b, callback_data=f"briefbud:{i}")]
                                    for i, b in enumerate(budgets_for(lang))])
        await update.message.reply_text(
            t(lang, "brief_budget_q") + "\n\n" + t(lang, "brief_pick_hint"),
            reply_markup=kb)
    elif step == "desc":
        context.user_data["brief"]["desc"] = text
        flow["step"] = "budget"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(b, callback_data=f"briefbud:{i}")]
                                    for i, b in enumerate(budgets_for(lang))])
        await update.message.reply_text(
            t(lang, "brief_budget_q"), reply_markup=kb)
    elif step == "deadline":
        context.user_data["brief"]["deadline"] = text
        flow["step"] = "contact"
        await update.message.reply_text(t(lang, "brief_contact_q"))
    elif step == "contact":
        context.user_data["brief"]["contact"] = text
        await brief_finish(update, context)


async def brief_budget_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        # aksesi mund të ketë skaduar/revokuar në mes të brief-it —
        # butoni stale merr alert-in e kyçjes, jo vazhdimin e rrjedhës
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    flow = context.user_data.get("flow") or {}
    if flow.get("kind") != "brief":
        return
    try:
        idx = int(q.data.split(":", 1)[1])
    except (ValueError, IndexError):
        return
    budgets = budgets_for(lang)
    if not (0 <= idx < len(budgets)):
        idx = 0
    context.user_data.setdefault("brief", {})["budget"] = budgets[idx]
    flow["step"] = "deadline"
    await q.message.reply_text(t(lang, "brief_deadline_q"))


# ---------------------------------------------------------------- F4: PDF-ja e propozimit
def _pdf_bytes(s: str) -> bytes:
    """Tekst → bytes WinAnsi (cp1252): ë/ç/Ë/Ç dalin saktë me fontet
    bazë-14; shenjat jashtë hartës (p.sh. emoji) hiqen pa gabim."""
    return (s or "").encode("cp1252", "ignore")


def _pdf_escape_b(b: bytes) -> bytes:
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _pdf_wrap(text: str, width: int):
    """Mbështjellje e thjeshtë e fjalëve sipas gjatësisë së rreshtit."""
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        if len(cur) + (1 if cur else 0) + len(w) > width:
            if cur:
                lines.append(cur)
            cur = w
            while len(cur) > width:  # fjalë shumë e gjatë → pritet
                lines.append(cur[:width])
                cur = cur[width:]
        else:
            cur = (cur + " " + w) if cur else w
    if cur:
        lines.append(cur)
    return lines or [""]


def build_proposal_pdf(brief: dict, client_name: str, lang: str = "sq") -> bytes:
    """PROPOZIM PARAPRAK — një faqe A4, e ndërtuar me kod të pastër
    stdlib (pa asnjë varësi): sfond i zi, vija ari, font Helvetica
    (bazë-14, WinAnsi). KURRË çmime/shuma — vetëm të dhënat e vetë
    klientit + tekstet statike të shabllonit (pa shifra)."""
    en = (lang == "en")
    L = {
        "title": "PRELIMINARY PROPOSAL" if en else "PROPOZIM PARAPRAK",
        "client": "Client" if en else "Klienti",
        "service": "Service" if en else "Shërbimi",
        "desc": "Description" if en else "Përshkrimi",
        "budget": "Budget" if en else "Buxheti",
        "deadline": "Desired timeline" if en else "Afati i dëshiruar",
        "contact": "Contact" if en else "Kontakti",
        "next_h": "Next steps" if en else "Hapat e radhës",
        "next": ("Discussion and clarifications - Final offer - "
                 "Agreement - Work begins" if en else
                 "Diskutim dhe sqarime - Oferta përfundimtare - "
                 "Marrëveshja - Nisja e punës"),
        "note": ("This is a preliminary, non-binding summary. The "
                 "final offer follows our discussion." if en else
                 "Ky është një përmbledhje paraprake, pa angazhim. "
                 "Oferta përfundimtare vjen pas diskutimit tonë."),
    }
    sid = brief.get("service_key") or ""
    service_label = (svc_name(sid, lang) if sid
                     else (brief.get("service") or "—"))
    desc = (brief.get("desc") or "—").strip()
    if len(desc) > 700:
        desc = desc[:700].rstrip() + "…"
    rows = [
        (L["client"], client_name or "—"),
        (L["service"], service_label),
        (L["desc"], desc),
        (L["budget"], brief.get("budget") or "—"),
        (L["deadline"], brief.get("deadline") or "—"),
        (L["contact"], brief.get("contact") or "—"),
    ]
    ops = []  # operatori i rrjedhës së përmbajtjes (bytes)
    ops.append(b"0 0 0 rg 0 0 595 842 re f")              # sfondi i zi
    ops.append(b"0.85 0.65 0.13 RG 3 w 40 786 m 555 786 l S")  # vija ari lart
    y = [806.0]

    def line(text, size=11, font=b"F1", color=b"1 1 1", dy=16, x=40):
        text = " ".join((text or "").split())
        ops.append(b"BT /" + font + b" " + str(size).encode() + b" Tf "
                   + color + b" rg 1 0 0 1 " + str(x).encode() + b" "
                   + f"{y[0]:.0f}".encode() + b" Tm (" +
                   _pdf_escape_b(_pdf_bytes(text)) + b") Tj ET")
        y[0] -= dy

    gold, white = b"0.85 0.65 0.13", b"1 1 1"
    line("ERION NEZHA - PRIVATE CLIENTS", 17, b"F2", gold, dy=30)
    line(L["title"], 13, b"F2", white, dy=26)
    ops.append(b"0.85 0.65 0.13 RG 1.5 w 40 " + f"{y[0] + 8:.0f}".encode()
               + b" m 555 " + f"{y[0] + 8:.0f}".encode() + b" l S")
    y[0] -= 14
    for label, value in rows:
        line(label.upper(), 9.5, b"F2", gold, dy=13)
        for ln in _pdf_wrap(value, 88)[:9]:
            line(ln, 11, b"F1", white, dy=15)
        y[0] -= 7
    line(L["next_h"].upper(), 9.5, b"F2", gold, dy=13)
    for ln in _pdf_wrap(L["next"], 88):
        line(ln, 11, b"F1", white, dy=15)
    # footer-i (pozicion fiks, poshtë)
    y[0] = 74.0
    ops.append(b"0.85 0.65 0.13 RG 1.5 w 40 88 m 555 88 l S")
    line("MR ERJONIXX", 11, b"F2", gold, dy=15)
    for ln in _pdf_wrap(L["note"], 100):
        line(ln, 8.5, b"F1", white, dy=11)
    stream = b"\n".join(ops)

    def obj(n, body):
        return str(n).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    objects = [
        obj(1, b"<< /Type /Catalog /Pages 2 0 R >>"),
        obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
        obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
               b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> "
               b"/Contents 6 0 R >>"),
        obj(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
               b"/Encoding /WinAnsiEncoding >>"),
        obj(5, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
               b"/Encoding /WinAnsiEncoding >>"),
        obj(6, b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
               + stream + b"\nendstream"),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for o in objects:
        offsets.append(len(out))
        out += o
    xref_at = len(out)
    out += b"xref\n0 7\n0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (b"trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n"
            + str(xref_at).encode() + b"\n%%EOF")
    return bytes(out)


# ================================================================
# Paketa 3 (F5) — MARRËVESHJA DIXHITALE E BASHKËPUNIMIT
# Admini: /marreveshje <user_id> → klienti merr kushtet me butonat
# ✅/❌; pranimi regjistrohet (me datë/orë) dhe të dyja palët marrin
# PDF-në e marrëveshjes (i njëjti ndërtues stdlib si propozimi).
# ================================================================
def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "")


def build_agreement_pdf(agr: dict, client_name: str, decided_local: str,
                        lang: str = "sq") -> bytes:
    """MARRËVESHJE BASHKËPUNIMI — një faqe A4 me të njëjtën estetikë
    (sfond i zi, vija ari, Helvetica/WinAnsi) si propozimi paraprak.
    Shifrat këtu janë TË DHËNA (id, data/ora e pranimit) — të lejuara."""
    en = (lang == "en")
    L = {
        "title": "COOPERATION AGREEMENT" if en else "MARRËVESHJE BASHKËPUNIMI",
        "parties": "Parties" if en else "Palët",
        "provider": ("Service provider" if en else "Ofruesi i shërbimit"),
        "client": "Client" if en else "Klienti",
        "subject": "Subject" if en else "Objekti",
        "terms_h": "Terms" if en else "Kushtet",
        "accept_h": "Digital acceptance" if en else "Pranimi dixhital",
        "accepted_by": "Accepted by" if en else "Pranuar nga",
        "when": "Date and time" if en else "Data dhe ora",
        "note": ("Accepted digitally inside the Telegram portal" if en
                 else "Pranuar dixhitalisht brenda portalit Telegram"),
    }
    terms_plain = _strip_tags(t(lang, "agreement_terms"))
    terms_lines = []
    for para in terms_plain.splitlines():
        para = para.strip()
        if not para or para == _strip_tags("Kushtet e bashkëpunimit") \
                or para == "Terms of cooperation":
            continue
        terms_lines.extend(_pdf_wrap(para, 92))
    ops = []
    ops.append(b"0 0 0 rg 0 0 595 842 re f")
    ops.append(b"0.85 0.65 0.13 RG 3 w 40 786 m 555 786 l S")
    y = [806.0]

    def line(text, size=11, font=b"F1", color=b"1 1 1", dy=16, x=40):
        text = " ".join((text or "").split())
        ops.append(b"BT /" + font + b" " + str(size).encode() + b" Tf "
                   + color + b" rg 1 0 0 1 " + str(x).encode() + b" "
                   + f"{y[0]:.0f}".encode() + b" Tm (" +
                   _pdf_escape_b(_pdf_bytes(text)) + b") Tj ET")
        y[0] -= dy

    gold, white = b"0.85 0.65 0.13", b"1 1 1"
    line("ERION NEZHA - PRIVATE CLIENTS", 17, b"F2", gold, dy=30)
    line(L["title"], 13, b"F2", white, dy=26)
    ops.append(b"0.85 0.65 0.13 RG 1.5 w 40 " + f"{y[0] + 8:.0f}".encode()
               + b" m 555 " + f"{y[0] + 8:.0f}".encode() + b" l S")
    y[0] -= 14
    line(L["parties"].upper(), 9.5, b"F2", gold, dy=13)
    line(f"{L['provider']}: Erion Nezha", 11, b"F1", white, dy=15)
    line(f"{L['client']}: {client_name or '—'}", 11, b"F1", white, dy=15)
    y[0] -= 7
    line(L["subject"].upper(), 9.5, b"F2", gold, dy=13)
    for ln in _pdf_wrap(agr.get("title") or "—", 88)[:3]:
        line(ln, 11, b"F1", white, dy=15)
    y[0] -= 7
    line(L["terms_h"].upper(), 9.5, b"F2", gold, dy=13)
    for ln in terms_lines[:22]:
        line(ln, 10, b"F1", white, dy=13.5)
    y[0] -= 9
    line(L["accept_h"].upper(), 9.5, b"F2", gold, dy=13)
    line(f"{L['accepted_by']}: {client_name or '—'} "
         f"(Telegram ID: {agr.get('client_id')})", 10.5, b"F1", white, dy=14)
    line(f"{L['when']}: {decided_local}", 10.5, b"F1", white, dy=14)
    line(L["note"], 10.5, b"F1", white, dy=14)
    # footer-i (pozicion fiks, poshtë)
    y[0] = 74.0
    ops.append(b"0.85 0.65 0.13 RG 1.5 w 40 88 m 555 88 l S")
    line("MR ERJONIXX", 11, b"F2", gold, dy=15)
    stream = b"\n".join(ops)

    def obj(n, body):
        return str(n).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    objects = [
        obj(1, b"<< /Type /Catalog /Pages 2 0 R >>"),
        obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
        obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
               b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> "
               b"/Contents 6 0 R >>"),
        obj(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
               b"/Encoding /WinAnsiEncoding >>"),
        obj(5, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
               b"/Encoding /WinAnsiEncoding >>"),
        obj(6, b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
               + stream + b"\nendstream"),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for o in objects:
        offsets.append(len(out))
        out += o
    xref_at = len(out)
    out += b"xref\n0 7\n0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (b"trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n"
            + str(xref_at).encode() + b"\n%%EOF")
    return bytes(out)


async def _send_agreement(context: ContextTypes.DEFAULT_TYPE, uid: int):
    """Bërthama e dërgimit të marrëveshjes dixhitale — përdoret nga
    /marreveshje dhe nga butoni brief:agr (paketa 4). Objekti është
    projekti më i fundit i klientit (çdo status); pa projekt →
    objekti i përgjithshëm i lokalizuar. Maks. një në pritje.
    Kthen (status, title): 'no_client' | 'pending' | 'failed' | 'sent'."""
    rec = store.get_client_any(uid)
    if not rec:
        return "no_client", ""
    if store.pending_agreement_for(uid):
        return "pending", ""
    projects = store.list_projects(uid)
    proj = projects[-1] if projects else None
    lang_c = store.get_lang(uid)
    title = (proj or {}).get("title") or t(lang_c,
                                           "agreement_subject_default")
    agr = store.create_agreement(uid, (proj or {}).get("id"), title)
    if agr is None:  # garë e rrallë: sapo u krijua një tjetër
        return "pending", title
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang_c, "agreement_accept"),
                             callback_data=f"agr:accept:{agr['id']}"),
        InlineKeyboardButton(t(lang_c, "agreement_decline"),
                             callback_data=f"agr:decline:{agr['id']}"),
    ]])
    text = (t(lang_c, "agreement_intro", title=_esc(title)) + "\n\n"
            + t(lang_c, "agreement_terms"))
    try:
        await context.bot.send_message(uid, text, parse_mode="HTML",
                                       reply_markup=kb)
    except Exception as e:
        log.warning("marrëveshja s'u dërgua te %s: %s", uid, e)
        return "failed", title
    return "sent", title


async def adm_agreement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/marreveshje <user_id> — i dërgon klientit marrëveshjen dixhitale
    për projektin e tij më të fundit (çdo status); pa projekt → objekti
    i përgjithshëm i lokalizuar. Maks. një në pritje për klient."""
    if not is_admin(update.effective_user):
        return
    uid, _ = _parse_uid_arg(context)
    if uid is None:
        await update.message.reply_text(
            "Përdorimi: /marreveshje <user_id> — i dërgon klientit "
            "marrëveshjen e bashkëpunimit për projektin e tij të fundit.")
        return
    rec = store.get_client_any(uid)
    if not rec:
        await update.message.reply_text("Ky user_id nuk u gjet te klientët.")
        return
    if store.pending_agreement_for(uid):
        await update.message.reply_text(
            "✍ Klienti ka tashmë një marrëveshje në pritje — prit "
            "vendimin e tij para se të dërgosh tjetër.")
        return
    status, title = await _send_agreement(context, uid)
    if status == "pending":  # garë e rrallë: sapo u krijua një tjetër
        await update.message.reply_text(
            "✍ Klienti ka tashmë një marrëveshje në pritje.")
        return
    if status == "failed":
        await update.message.reply_text(
            "⚠️ Marrëveshja u regjistrua, por dërgimi te klienti "
            "dështoi (ndoshta s'e ka hapur botin).")
        return
    await update.message.reply_text(
        f"✍ Marrëveshja iu dërgua <b>{_esc(rec.get('name')) or 'klientit'}</b> "
        f"(id {uid}) për «{_esc(title)}». Do të njoftohesh kur të vendosë.",
        parse_mode="HTML")


async def agreement_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vendimi i klientit mbi marrëveshjen (agr:accept[:<id>] /
    agr:decline[:<id>]). Butonat e rinj mbajnë id-në e marrëveshjes:
    një buton STALE (i mesazhit të vjetër) s'mund të vendosë një
    marrëveshje më të re në pritje (auditi 360°, D6). Formati legacy
    pa id (mesazhet e dërguara para rregullimit) vendos ende
    marrëveshjen në pritje. Vetëm klienti i adresuar vendos."""
    q = update.callback_query
    user = q.from_user
    lang = ulang(user)
    if not has_access(user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    parts = (q.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    aid = parts[2] if len(parts) > 2 else None
    if aid:
        agr = store.get_agreement(aid)
        if not agr or agr.get("client_id") != user.id \
                or agr.get("status") != "pending":
            await q.answer(t(lang, "agreement_done"), show_alert=True)
            return
    else:
        agr = store.pending_agreement_for(user.id)
        if not agr:
            await q.answer(t(lang, "agreement_done"), show_alert=True)
            return
    await q.answer()
    rec = store.get_client_any(user.id) or {}
    client_name = rec.get("name") or user.first_name or ""
    if action == "decline":
        store.set_agreement_status(agr["id"], "declined")
        await q.message.reply_text(t(lang, "agreement_declined_msg"),
                                   parse_mode="HTML")
        await notify_admin(
            context,
            f"✍ <b>Marrëveshja u refuzua</b>\n\n"
            f"👤 {_esc(client_name)} (@{_esc(user.username) or '—'}, id {user.id})\n"
            f"📄 Objekti: «{_esc(agr.get('title')) or '—'}»")
        return
    updated = store.set_agreement_status(agr["id"], "accepted")
    decided_dt = parse_iso((updated or {}).get("decided_at"))
    decided_local = (decided_dt.astimezone(TIRANA).strftime("%d.%m.%Y %H:%M")
                      if decided_dt else "—")
    await q.message.reply_text(t(lang, "agreement_accepted_msg"),
                               parse_mode="HTML")
    try:
        pdf = build_agreement_pdf(updated or agr, client_name,
                                  decided_local, lang)
        caption = t(lang, "agreement_pdf_caption")
        await context.bot.send_document(
            user.id, document=io.BytesIO(pdf),
            filename="marreveshje-bashkepunimi.pdf", caption=caption)
        await context.bot.send_document(
            ADMIN_ID, document=io.BytesIO(pdf),
            filename="marreveshje-bashkepunimi.pdf",
            caption=(f"✍ Marrëveshje e pranuar — {client_name} "
                     f"(id {user.id}), objekti: «{agr.get('title') or '—'}», "
                     f"pranuar më {decided_local}"))
    except Exception as e:
        log.warning("PDF-ja e marrëveshjes dështoi: %s", e)
    await notify_admin(
        context,
        f"✍ <b>Marrëveshja u pranua</b>\n\n"
        f"👤 {_esc(client_name)} (@{_esc(user.username) or '—'}, id {user.id})\n"
        f"📄 Objekti: «{_esc(agr.get('title')) or '—'}»\n"
        f"🕒 Pranuar më: {decided_local}")


def _brief_admin_kb(brief_id: str, with_project: bool = True):
    """Butonat një-prekje të adminit mbi njoftimin e brief-it
    (paketa 4): krijo projektin / dërgo marrëveshjen / përgjigju."""
    top = []
    if with_project:
        top.append(InlineKeyboardButton(
            "🚧 Krijo projektin", callback_data=f"brief:proj:{brief_id}"))
    top.append(InlineKeyboardButton(
        "✍ Dërgo marrëveshjen", callback_data=f"brief:agr:{brief_id}"))
    return InlineKeyboardMarkup([
        top,
        [InlineKeyboardButton(
            "💬 Përgjigju", callback_data=f"brief:reply:{brief_id}")],
    ])


def _brief_project_title(brief: dict) -> str:
    """Titulli i projektit nga brief-i: përshkrimi i klientit është
    'emri' praktik i projektit (pastrohet + shkurtohet); pa
    përshkrim përdoret etiketa e shërbimit."""
    desc = " ".join((brief.get("desc") or "").split())
    if desc:
        return desc[:70].rstrip() + ("…" if len(desc) > 70 else "")
    return brief.get("service") or "Projekt"


async def brief_action_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paketa 4: veprimet një-prekje të adminit mbi njoftimin e
    brief-it (brief:proj:<id> / brief:agr:<id> / brief:reply:<id>).
    Vetëm admini; 'proj' është idempotent (brief.project_id)."""
    q = update.callback_query
    if not is_admin(q.from_user):
        await q.answer("Vetëm admini.", show_alert=True)
        return
    parts = (q.data or "").split(":")
    if len(parts) != 3:
        await q.answer("Të dhëna të pavlefshme.", show_alert=True)
        return
    _, action, bid = parts
    brief = store.get_brief(bid)
    if not brief:
        await q.answer("Brief-i nuk u gjet.", show_alert=True)
        return
    uid = brief["client_id"]
    crec = store.get_client_any(uid) or {}
    cname = brief.get("name") or crec.get("name") or "klientit"
    if action == "reply":
        # e njëjta gjendje si /pergjigju <id>: mesazhi tjetër i
        # adminit i shkon këtij klienti
        await q.answer()
        context.user_data["reply_to"] = uid
        await q.message.reply_text(
            f"✍️ Po i përgjigjesh <b>{_esc(cname)}</b> (id {uid}).\n"
            "Mesazhi yt i radhës — tekst ose media — i dërgohet "
            "atij direkt. /anulo për anulim.", parse_mode="HTML")
        return
    if action == "agr":
        status, title = await _send_agreement(context, uid)
        if status == "sent":
            await q.answer(f"✍ Marrëveshja iu dërgua klientit — «{title}»")
        elif status == "pending":
            await q.answer(
                "✍ Klienti ka tashmë një marrëveshje në pritje.",
                show_alert=True)
        elif status == "no_client":
            await q.answer("Klienti nuk u gjet më te regjistri.",
                           show_alert=True)
        else:
            await q.answer("⚠️ Dërgimi te klienti dështoi.",
                           show_alert=True)
        return
    # action == "proj"
    if brief.get("project_id"):
        await q.answer("🚧 Projekti i këtij brief-i është krijuar tashmë.")
        return
    await q.answer()
    title = _brief_project_title(brief)
    rec = store.create_project(uid, title)
    store.set_brief_project(bid, rec["id"])
    clang = store.get_lang(uid)
    try:
        await context.bot.send_message(
            uid, t(clang, "project_started") + "\n\n"
            + project_view_text(rec, clang), parse_mode="HTML")
    except Exception as e:
        log.warning("njoftimi i nisjes së projektit s'u dërgua: %s", e)
    try:
        await q.edit_message_text(
            (q.message.text or "")
            + f"\n\n✅ <b>Projekti u krijua</b> — «{_esc(title)}»",
            parse_mode="HTML",
            reply_markup=_brief_admin_kb(bid, with_project=False))
    except Exception:
        pass


async def brief_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = ulang(user)
    d = context.user_data.get("brief", {})
    if store.brief_block(user.id):  # kontroll përfundimtar (Fiks 2)
        await update.message.reply_text(t(lang, "brief_daily"), parse_mode="HTML")
        context.user_data.pop("brief", None)
        context.user_data.pop("flow", None)
        return
    # paketa 4: brief-i ruhet si regjistër me id — admini vepron
    # mbi njoftimin me butonat një-prekje (brief_action_cb)
    brief = store.create_brief(user.id, user.first_name or "",
                               user.username or "", d)
    await notify_admin(
        context,
        "🚀 <b>BRIEF I RI PROJEKTI</b>\n"
        f"👤 {_esc(user.first_name)} (@{_esc(user.username) or '—'}, id {user.id})\n"
        f"💼 Lloji: {_esc(d.get('service')) or '—'}\n"
        f"📝 Përshkrimi: {_esc(_trunc(d.get('desc'), 900)) or '—'}\n"
        f"💰 Buxheti: {_esc(d.get('budget')) or '—'}\n"
        f"⏰ Afati: {_esc(_trunc(d.get('deadline'), 200)) or '—'}\n"
        f"📞 Kontakti: {_esc(_trunc(d.get('contact'), 200)) or '—'}\n\n"
        f"💡 <b>Gjurmim:</b> për ta ndjekur projektin te klienti, kopjo: "
        f"<code>/projekt {user.id} Titulli i projektit</code>",
        markup=_brief_admin_kb(brief["id"]))
    # F4: propozimi paraprak PDF për adminin + klientin (në heshtje
    # nëse gjenerimi dështon — rrjedha e brief-it s'prishet kurrë)
    try:
        pdf = build_proposal_pdf(d, user.first_name or "", lang)
        for chat_id, cap in (
                (ADMIN_ID, "🧾 Propozimi paraprak për brief-in e "
                           f"{user.first_name or 'klientit'} — "
                           "përmbledhje pa angazhim."),
                (user.id, t(lang, "pdf_caption"))):
            try:
                await context.bot.send_document(
                    chat_id, document=io.BytesIO(pdf),
                    filename="propozim-paraprak.pdf", caption=cap)
            except Exception as e:
                log.warning("PDF-ja s'u dërgua te %s: %s", chat_id, e)
    except Exception as e:
        log.warning("gjenerimi i PDF-së dështoi: %s", e)
    store.bump_today(user.id, "briefs")
    await update.message.reply_text(
        t(lang, "brief_sent"), parse_mode="HTML",
        reply_markup=client_kb(lang))
    context.user_data.pop("brief", None)
    context.user_data.pop("flow", None)


# ---------------------------------------------------------------- F1: Projekti im
def project_view_text(rec, lang: str = "sq") -> str:
    """Pamja e projektit për klientin: fazat me simbole + shiriti i
    progresit VETËM me simbole (✅/🔄/⚪ dhe ▰/▱) — kurrë përqindje
    apo numra fazash (urdhri 'mos vendos shifra'). Etiketat e fazave
    përkthehen sipas gjuhës; titulli/shënimi janë përmbajtje admini."""
    stages = stages_for(lang)
    stage = max(0, min(len(stages) - 1, _safe_int(rec.get("stage"), 0)))
    done = bool(rec.get("done"))
    lines = [f"🚧 <b>{_esc(rec.get('title')) or 'Projekt'}</b>"]
    for i, label in enumerate(stages):
        if done or i < stage:
            mark = "✅"
        elif i == stage:
            mark = "🔄"
        else:
            mark = "⚪"
        lines.append(f"{mark} {label}")
    filled = len(stages) if done else stage + 1
    lines.append("▰" * filled + "▱" * (len(stages) - filled))
    if rec.get("note"):
        lines.append(f"📝 <i>{_esc(rec['note'])}</i>")
    lines.append(t(lang, "project_updated",
                   date=fmt_date(rec.get('updated_at'))))
    return "\n".join(lines)


async def show_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚧 Projekti im — vetëm klientë të zhbllokuar (portieri)."""
    if not await guard_client(update):
        return
    user = update.effective_user
    lang = ulang(user)
    projects = store.list_projects(user.id) if not is_admin(user) else []
    active = [p for p in projects if not p.get("done")]
    finished = [p for p in projects if p.get("done")]
    ordered = active + finished
    if not ordered:
        await update.effective_message.reply_text(
            t(lang, "projects_empty"), parse_mode="HTML")
        return
    parts = [t(lang, "projects_header")] + [project_view_text(p, lang)
                                           for p in ordered]
    await update.effective_message.reply_text(
        "\n\n".join(parts), parse_mode="HTML")


_UID_ARG = re.compile(r"-?[0-9]{1,18}")


def _parse_uid_arg(context):
    """user_id nga args[0] (ose None nëse formati është gabim).
    Regex ASCII strikte: '.isdigit()' pranon edhe shifra Unicode
    ('²') që int() pastaj i rrëzon, dhe vargjet me mijëra shifra e
    kalojnë kufirin e int()-it — të dyja jepnin traceback (D8)."""
    args = context.args or []
    if not args or not _UID_ARG.fullmatch(args[0] or ""):
        return None, []
    return int(args[0]), args[1:]


async def adm_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F1: /projekt <user_id> <titulli...> — krijon projekt për klientin."""
    if not is_admin(update.effective_user):
        return
    uid, rest = _parse_uid_arg(context)
    if uid is None or not rest:
        await update.message.reply_text(
            "Përdorimi: /projekt <user_id> <titulli i projektit>")
        return
    if not store.get_client_any(uid):
        await update.message.reply_text("Ky user_id nuk u gjet te klientët.")
        return
    rec = store.create_project(uid, " ".join(rest))
    await update.message.reply_text(
        "🚧 <b>Projekti u krijua</b> — klienti e sheh te «Projekti im»:\n\n"
        + project_view_text(rec), parse_mode="HTML")


async def adm_project_stage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F1: /faza <user_id> <emri i fazës> — ndërron fazën e projektit
    aktiv më të ri të klientit dhe e njofton atë automatikisht."""
    if not is_admin(update.effective_user):
        return
    uid, rest = _parse_uid_arg(context)
    if uid is None or not rest:
        await update.message.reply_text(
            "Përdorimi: /faza <user_id> <emri i fazës>\n"
            "Fazat: " + ", ".join(PROJECT_STAGES))
        return
    proj = store.latest_project(uid)
    if not proj:
        await update.message.reply_text(
            "Klienti s'ka projekt aktiv (jo të përfunduar). "
            "Krijoje me /projekt <user_id> <titulli>.")
        return
    label = " ".join(rest).strip()
    match = next((i for i, l in enumerate(PROJECT_STAGES)
                  if l.lower() == label.lower()), None)
    if match is None:
        await update.message.reply_text(
            f"⚠️ Fazë e panjohur: «{label}».\n"
            "Fazat e vlefshme: " + ", ".join(PROJECT_STAGES))
        return
    rec = store.set_stage(proj["id"], match)
    await update.message.reply_text(
        f"✅ Faza u ndryshua në <b>{PROJECT_STAGES[match]}</b> për "
        f"projektin e klientit {uid} — klienti u njoftua.",
        parse_mode="HTML")
    clang = store.get_lang(uid)
    try:
        await context.bot.send_message(
            uid,
            t(clang, "project_update_title") + "\n\n"
            + project_view_text(rec, clang),
            parse_mode="HTML")
    except Exception as e:
        log.warning("njoftimi i fazës s'u dërgua: %s", e)
    if match == len(PROJECT_STAGES) - 1:  # faza e fundit → F1
        await ask_review(context, uid, rec)


async def adm_project_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F1: /shenim_projekti <user_id> <teksti...> — shënim i dukshëm
    për klientin te pamja e projektit."""
    if not is_admin(update.effective_user):
        return
    uid, rest = _parse_uid_arg(context)
    if uid is None or not rest:
        await update.message.reply_text(
            "Përdorimi: /shenim_projekti <user_id> <teksti i shënimit>")
        return
    proj = store.latest_project(uid)
    if not proj:
        await update.message.reply_text(
            "Klienti s'ka projekt aktiv (jo të përfunduar).")
        return
    store.set_note(proj["id"], " ".join(rest))
    await update.message.reply_text(
        "📝 Shënimi u ruajt — klienti e sheh te «Projekti im».")


async def adm_project_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F1: /projekt_fund <user_id> — mbyll projektin aktiv dhe e
    njofton klientin me mesazhin e ngrohtë të përfundimit."""
    if not is_admin(update.effective_user):
        return
    uid, _ = _parse_uid_arg(context)
    if uid is None:
        await update.message.reply_text("Përdorimi: /projekt_fund <user_id>")
        return
    proj = store.latest_project(uid)
    if not proj:
        await update.message.reply_text(
            "Klienti s'ka projekt aktiv (jo të përfunduar).")
        return
    rec = store.finish_project(proj["id"])
    await update.message.reply_text(
        "🎉 Projekti i klientit "
        f"{uid} u shënua i përfunduar — klienti u njoftua.")
    clang = store.get_lang(uid)
    try:
        await context.bot.send_message(
            uid, t(clang, "project_finish",
                   title=_esc(rec.get("title")) or "Projekt"),
            parse_mode="HTML")
    except Exception as e:
        log.warning("njoftimi i përfundimit s'u dërgua: %s", e)
    await ask_review(context, uid, rec)  # F1: kërkesa për vlerësim


# ---------------------------------------------------------------- F1: vlerësimet automatike
def _review_admin_kb(rid: str):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Publiko", callback_data=f"revadm:ok:{rid}"),
        InlineKeyboardButton("❌ Mos e publiko", callback_data=f"revadm:no:{rid}"),
    ]])


def _review_admin_text(rec, project_title: str = "") -> str:
    stars = "⭐" * max(0, min(5, _safe_int(rec.get("stars"), 0)))
    lines = ["⭐ <b>VLERËSIM I RI</b>",
             f"👤 {_esc(rec.get('name')) or '—'} (id {rec.get('client_id')})"]
    if project_title:
        lines.append(f"🚧 Projekti: {_esc(project_title)}")
    lines.append(stars)
    if rec.get("text"):
        lines.append(f"💬 {_esc(rec['text'])}")
    return "\n".join(lines)


async def ask_review(context: ContextTypes.DEFAULT_TYPE, uid: int, project: dict):
    """F1: pas përfundimit të projektit, klienti ftohet të vlerësojë
    (yje me simbole + kapërce). Një vlerësim për projekt — nëse
    ekziston tashmë (çdo status), s'pyetet më."""
    if store.review_for_project(project["id"]) is not None:
        return
    lang = store.get_lang(uid)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐" * n,
                              callback_data=f"rev:s:{project['id']}:{n}")
         for n in (1, 2, 3)],
        [InlineKeyboardButton("⭐" * n,
                              callback_data=f"rev:s:{project['id']}:{n}")
         for n in (4, 5)],
        [InlineKeyboardButton(t(lang, "review_skip"),
                              callback_data=f"rev:skip:{project['id']}")],
    ])
    try:
        await context.bot.send_message(
            uid, t(lang, "review_ask",
                   title=_esc(project.get("title")) or "Projekt"),
            parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        log.warning("ftesa për vlerësim s'u dërgua: %s", e)


async def review_stars_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hapi i yjeve: ruan zgjedhjen dhe kërkon komentin opsional."""
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    parts = (q.data or "").split(":")  # rev:s:<pid>:<n>
    if len(parts) != 4:
        return
    try:
        n = int(parts[3])
    except ValueError:
        return  # numër yjesh i shtrembëruar — pa rrjedhë, pa crash (D1)
    if not (1 <= n <= 5):
        return  # jashtë diapazonit 1–5 — refuzohet në heshtje pas answer-it
    pid = parts[2]
    proj = store.get_project(pid)
    if not proj or int(proj.get("client_id") or 0) != q.from_user.id:
        return
    if store.review_for_project(pid) is not None:
        return  # një vlerësim për projekt
    context.user_data["flow"] = {"kind": "review", "project_id": pid,
                                 "stars": n}
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        t(lang, "skip"), callback_data="rev:tskip")]])
    await q.message.reply_text(t(lang, "review_comment_q"),
                               parse_mode="HTML", reply_markup=kb)


async def review_skip_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kapërcimi te hapi i yjeve: asnjë vlerësim s'krijohet."""
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    await q.message.reply_text(t(lang, "review_skipped"))


async def review_tskip_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kapërcimi i komentit: vlerësimi ruhet vetëm me yjet."""
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        context.user_data.pop("flow", None)
        return
    await q.answer()
    flow = context.user_data.get("flow") or {}
    if flow.get("kind") != "review":
        return
    context.user_data.pop("flow", None)
    await _finalize_review(update, context, flow, "")


async def review_text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Komenti i vlerësimit (hapi i dytë i rrjedhës 'review')."""
    flow = context.user_data["flow"]
    text = (update.message.text or "").strip()
    context.user_data.pop("flow", None)
    await _finalize_review(update, context, flow, text)


async def _finalize_review(update, context, flow: dict, text: str):
    user = update.effective_user
    lang = ulang(user)
    pid = flow.get("project_id")
    proj = store.get_project(pid) if pid else None
    if not proj:
        return
    client_name = user.first_name or ""
    rec_client = store.get_client(user.id)
    if rec_client and rec_client.get("name"):
        client_name = rec_client["name"]
    rec, created = store.create_review(
        user.id, client_name, pid, _safe_int(flow.get("stars"), 5), text)
    if created:
        await notify_admin(
            context, _review_admin_text(rec, proj.get("title") or ""),
            markup=_review_admin_kb(rec["id"]))
    await update.effective_message.reply_text(
        t(lang, "review_thanks"), parse_mode="HTML")


async def review_admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vendimi i adminit mbi vlerësimin (publiko/refuzo) — vetëm
    admini; jo-admini merr alert (jo heshtje), veprimi i panjohur
    s'ndryshon asgjë dhe vendimi i marrë s'kthehet nga klikimi stale
    (auditi 360°, D2)."""
    q = update.callback_query
    if not is_admin(q.from_user):
        await q.answer("Vetëm admini.", show_alert=True)
        return
    parts = (q.data or "").split(":")  # revadm:ok|no:<rid>
    if len(parts) != 3 or parts[1] not in ("ok", "no"):
        await q.answer("Veprim i panjohur.", show_alert=True)
        return
    action, rid = parts[1], parts[2]
    rec = store.get_review(rid)
    if not rec:
        await q.answer("Vlerësimi nuk u gjet.", show_alert=True)
        return
    if rec.get("status") != "pending":
        await q.answer("Vlerësimi është vendosur tashmë.")
        return
    await q.answer()
    store.set_review_status(rid, "approved" if action == "ok" else "rejected")
    verdict = ("✅ <b>U PUBLIKUA</b> — shfaqet te ⭐ Vlerësimet."
               if action == "ok" else "❌ <b>U REFUZUA</b> — s'shfaqet.")
    try:
        await q.edit_message_text((q.message.text or "") + "\n\n" + verdict,
                                  parse_mode="HTML")
    except Exception:
        await q.message.reply_text(verdict, parse_mode="HTML")


async def adm_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F1: /vleresime — vlerësimet në pritje, me butonat e vendimit."""
    if not is_admin(update.effective_user):
        return
    pending = store.list_reviews(status="pending")
    if not pending:
        await update.message.reply_text(
            "⭐ S'ka vlerësime në pritje për momentin.")
        return
    await update.message.reply_text(
        f"⭐ <b>{len(pending)} vlerësim(e) në pritje:</b>", parse_mode="HTML")
    for rec in pending[:10]:
        proj = store.get_project(rec.get("project_id") or "")
        await update.message.reply_text(
            _review_admin_text(rec, (proj or {}).get("title") or ""),
            parse_mode="HTML", reply_markup=_review_admin_kb(rec["id"]))


# ---------------------------------------------------------------- F2: Rezervo konsultë
async def booking_menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🗓 Rezervo konsultë — pika e hyrjes nga menuja e klientit."""
    if not await guard_client(update):
        return
    user = update.effective_user
    lang = ulang(user)
    pend = store.pending_booking_for(user.id)
    if pend:
        # paketa 4: edhe nga këtu, klienti mund ta anulojë vetë
        # kërkesën në pritje me një prekje
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            t(lang, "book_cancel_btn"),
            callback_data=f"book:cancel:{pend['id']}")]])
        await update.effective_message.reply_text(
            t(lang, "book_pending"), parse_mode="HTML", reply_markup=kb)
        return
    context.user_data["flow"] = {"kind": "booking", "step": "service"}
    context.user_data["booking"] = {}
    await update.effective_message.reply_text(
        t(lang, "book_start"), parse_mode="HTML",
        reply_markup=service_kb("booksvc", lang))


def _slot_rows(slots, lang: str = "sq"):
    return [[InlineKeyboardButton(fmt_slot(parse_iso(s["dt_iso"]), lang),
                                  callback_data=f"bookslot:{s['id']}")]
            for s in slots]


async def book_service_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    flow = context.user_data.get("flow") or {}
    if flow.get("kind") != "booking":
        return
    sid = q.data.split(":", 1)[1]
    context.user_data.setdefault("booking", {})["service_key"] = sid
    slots = store.open_slots()
    if not slots:
        context.user_data.pop("flow", None)
        context.user_data.pop("booking", None)
        await q.message.reply_text(t(lang, "book_no_slots"), parse_mode="HTML")
        return
    flow["step"] = "slot"
    await q.message.reply_text(
        t(lang, "book_pick_slot"), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(_slot_rows(slots, lang)))


async def book_slot_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = ulang(q.from_user)
    if not has_access(q.from_user):
        await q.answer(t(lang, "locked_alert"), show_alert=True)
        return
    await q.answer()
    flow = context.user_data.get("flow") or {}
    booking = context.user_data.get("booking") or {}
    if flow.get("kind") != "booking" or "service_key" not in booking:
        return
    user = q.from_user
    slot_id = q.data.split(":", 1)[1]
    if store.pending_booking_for(user.id):
        context.user_data.pop("flow", None)
        context.user_data.pop("booking", None)
        await q.message.reply_text(t(lang, "book_pending"), parse_mode="HTML")
        return
    slot = store.get_slot(slot_id)
    slot_dt0 = parse_iso(slot["dt_iso"]) if slot else None
    if slot is None or slot.get("booked_by") is not None \
            or (slot_dt0 is not None
                and slot_dt0 <= datetime.now(timezone.utc)):
        # orari s'ekziston / u rezervua / KA KALUAR tashmë (buton stale
        # për orar të kaluar — auditi 360°, D7): e njëjta rrugë ri-pyetjeje
        slots = store.open_slots()
        context.user_data.pop("flow", None)
        context.user_data.pop("booking", None)
        if slots:
            context.user_data["flow"] = {"kind": "booking", "step": "slot"}
            context.user_data["booking"] = {"service_key": booking["service_key"]}
            await q.message.reply_text(
                t(lang, "book_taken"), parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(_slot_rows(slots, lang)))
        else:
            await q.message.reply_text(t(lang, "book_no_slots"), parse_mode="HTML")
        return
    rec = store.create_booking(user.id, slot_id, booking["service_key"])
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Konfirmo", callback_data=f"bookadm:ok:{rec['id']}"),
        InlineKeyboardButton("❌ Refuzo", callback_data=f"bookadm:no:{rec['id']}"),
    ]])
    await notify_admin(
        context,
        "🗓 <b>KËRKESË E RE KONSULTE</b>\n"
        f"👤 {_esc(user.first_name)} (@{_esc(user.username) or '—'}, id {user.id})\n"
        f"💼 Shërbimi: {SERVICE_NAMES.get(booking['service_key'], booking['service_key'])}\n"
        f"🗓 Orari: <b>{fmt_slot(parse_iso(slot['dt_iso']))}</b>",
        markup=kb)
    # paketa 4: klienti mund ta anulojë vetë kërkesën në pritje
    cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        t(lang, "book_cancel_btn"),
        callback_data=f"book:cancel:{rec['id']}")]])
    await q.message.reply_text(t(lang, "book_sent"), parse_mode="HTML",
                               reply_markup=cancel_kb)
    context.user_data.pop("flow", None)
    context.user_data.pop("booking", None)


async def booking_text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Teksti gjatë rrjedhës së rezervimit: të dy hapat (shërbimi,
    orari) presin butona inline — teksti i lirë ri-dërgon hapin aktual
    me hint, pa e prishur dhe pa e lënë pa përgjigje rrjedhën."""
    flow = context.user_data["flow"]
    lang = ulang(update.effective_user)
    hint = "\n\n" + t(lang, "brief_pick_hint")
    if flow.get("step") == "slot":
        slots = store.open_slots()
        if slots:
            await update.message.reply_text(
                t(lang, "book_pick_slot") + hint, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(_slot_rows(slots, lang)))
            return
        context.user_data.pop("flow", None)
        context.user_data.pop("booking", None)
        await update.message.reply_text(
            t(lang, "book_no_slots"), parse_mode="HTML")
        return
    await update.message.reply_text(
        t(lang, "book_start") + hint, parse_mode="HTML",
        reply_markup=service_kb("booksvc", lang))


async def booking_cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paketa 4 (3c): klienti anulon vetë kërkesën e tij të konsultës
    në pritje (book:cancel:<id>). Rezervimi 'pending' s'e ka konsumuar
    orarin — konsumimi ndodh vetëm në miratim — prandaj anulimi
    thjesht e shënon 'cancelled' dhe njofton adminin. Vendimet e
    marra tashmë dhe rezervimet e të tjerëve nuk preken."""
    q = update.callback_query
    user = q.from_user
    lang = ulang(user)
    bid = (q.data or "").rsplit(":", 1)[-1]
    b = store.get_booking(bid)
    if (not b or b.get("client_id") != user.id
            or b.get("status") != "pending"):
        await q.answer(t(lang, "book_cancel_done"), show_alert=True)
        return
    await q.answer()
    store.set_booking_status(bid, "cancelled")
    try:
        await q.edit_message_text(t(lang, "book_cancelled"),
                                  parse_mode="HTML")
    except Exception:
        pass
    slot = store.get_slot(b["slot_id"])
    slot_dt = parse_iso(slot["dt_iso"]) if slot else None
    client = store.get_client_any(user.id) or {}
    await notify_admin(
        context,
        "🗓 <b>Rezervimi u anulua nga klienti</b>\n"
        f"👤 {_esc(client.get('name') or user.first_name)} "
        f"(@{_esc(user.username) or '—'}, id {user.id})\n"
        f"💼 Shërbimi: {SERVICE_NAMES.get(b['service_key'], b['service_key'])}\n"
        f"🗓 Orari: <b>{fmt_slot(slot_dt) if slot_dt else '—'}</b>")


# ---------------------------------------------------------------- F2: kalendari (ICS + Google)
BOOKING_DURATION_MIN = 45


def _ics_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;") \
                    .replace(",", "\\,").replace("\n", "\\n")


def _ics_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_booking_ics(booking: dict, slot_dt: datetime, service_label: str,
                      client_name: str) -> bytes:
    """File .ics (stdlib, RFC 5545 bazë): DTSTART/DTEND në UTC nga
    orari i Tiranës, kohëzgjatje standarde, UID nga id-ja e
    rezervimit. Përmbajtja është TË DHËNA funksionale — shifrat
    brenda file-it lejohen (nuk janë tekst ndërfaqeje)."""
    end = slot_dt + timedelta(minutes=BOOKING_DURATION_MIN)
    summary = f"Konsultë me Erion Nezha — {service_label}"
    if client_name:
        summary += f" ({client_name})"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ErionNezhaBot//EN//",
        "BEGIN:VEVENT",
        f"UID:{booking['id']}@enclient",
        f"DTSTAMP:{_ics_utc(datetime.now(timezone.utc))}",
        f"DTSTART:{_ics_utc(slot_dt)}",
        f"DTEND:{_ics_utc(end)}",
        f"SUMMARY:{_ics_escape(summary)}",
        "DESCRIPTION:" + _ics_escape(
            "Konsultë private me Erion Nezha — biseda zhvillohet "
            "në chat-in e botit @ErionNezhaBot."),
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def gcal_url(slot_dt: datetime, service_label: str, client_name: str) -> str:
    """Lidhje 'template' e Google Calendar (e paraplotësuar) — pa
    asnjë kredencial; përdoruesi e hap dhe e ruan vetë ngjarjen."""
    end = slot_dt + timedelta(minutes=BOOKING_DURATION_MIN)
    summary = f"Konsultë me Erion Nezha — {service_label}"
    if client_name:
        summary += f" ({client_name})"
    params = {
        "action": "TEMPLATE",
        "text": summary,
        "dates": f"{_ics_utc(slot_dt)}/{_ics_utc(end)}",
        "details": "Konsultë private me Erion Nezha — biseda "
                   "zhvillohet në chat-in e botit @ErionNezhaBot.",
    }
    return ("https://calendar.google.com/calendar/render?"
            + urllib.parse.urlencode(params))


async def booking_decision_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vendimi i adminit mbi kërkesën e konsultës (si te kërkesat)."""
    q = update.callback_query
    if not is_admin(q.from_user):
        await q.answer("Vetëm admini.", show_alert=True)
        return
    parts = (q.data or "").split(":", 2)
    if len(parts) != 3 or parts[1] not in ("ok", "no") or not parts[2]:
        await q.answer("Të dhëna të pavlefshme.", show_alert=True)
        return
    _, action, bid = parts
    b = store.get_booking(bid)
    if not b or b["status"] != "pending":
        await q.answer("Rezervimi është trajtuar tashmë.")
        return
    slot = store.get_slot(b["slot_id"])
    if action == "ok" and slot is not None \
            and slot.get("booked_by") is not None \
            and slot.get("booking_id") != bid:
        await q.answer(
            "⚠️ Ky orar u rezervua ndërkohë nga një rezervim tjetër.",
            show_alert=True)
        return
    await q.answer()
    slot_dt = parse_iso(slot["dt_iso"]) if slot else None
    clang = store.get_lang(b["client_id"])
    client_rec_b = store.get_client_any(b["client_id"]) or {}
    client_name = client_rec_b.get("name") or ""
    if action == "no":
        store.set_booking_status(bid, "rejected")
        try:
            await q.edit_message_text(
                q.message.text + "\n\n❌ <b>REFUZUAR</b>", parse_mode="HTML")
        except Exception:
            pass
        try:
            await context.bot.send_message(
                b["client_id"],
                t(clang, "book_rejected",
                  service=svc_name(b["service_key"], clang),
                  slot=fmt_slot(slot_dt, clang) if slot_dt else "—"),
                parse_mode="HTML")
        except Exception as e:
            log.warning("refuzimi i konsultës s'u dërgua: %s", e)
        return
    if not store.set_booking_status(bid, "approved"):
        # roja atomike e store-it (D13): orari u zë ndërkohë nga një
        # rezervim tjetër — konflikti i raportohet adminit, klienti
        # s'merr konfirmim të rremë
        await q.message.reply_text(
            "⚠️ Ky orar u rezervua ndërkohë nga një rezervim tjetër — "
            "rezervimi mbetet në pritje.")
        return
    try:
        await q.edit_message_text(
            q.message.text + "\n\n✅ <b>KONFIRMUAR</b>", parse_mode="HTML")
    except Exception:
        pass
    # F2: butoni Google Calendar në të dy mesazhet e miratimit
    gcal_kb = None
    if slot_dt is not None:
        gcal_kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            t(clang, "gcal_btn"),
            url=gcal_url(slot_dt, svc_name(b["service_key"], "sq"),
                         client_name))]])
    try:
        await q.message.reply_text(
            "📅 Konsulta u konfirmua — klienti mori edhe file-in e "
            "kalendarit (.ics) dhe butonin Google Calendar.",
            reply_markup=gcal_kb)
    except Exception:
        pass
    try:
        await context.bot.send_message(
            b["client_id"],
            t(clang, "book_approved",
              service=svc_name(b["service_key"], clang),
              slot=fmt_slot(slot_dt, clang) if slot_dt else "—"),
            parse_mode="HTML", reply_markup=gcal_kb)
    except Exception as e:
        log.warning("konfirmimi i konsultës s'u dërgua: %s", e)
    # F2: file-i .ics si dokument për klientin DHE adminin
    if slot_dt is not None:
        try:
            ics = build_booking_ics(b, slot_dt,
                                    svc_name(b["service_key"], "sq"),
                                    client_name)
            for chat_id, cap in (
                    (b["client_id"], t(clang, "ics_caption")),
                    (ADMIN_ID, "📅 File-i i kalendarit për konsultën e "
                               f"{client_name or 'klientit'}.")):
                try:
                    await context.bot.send_document(
                        chat_id, document=io.BytesIO(ics),
                        filename="konsulte.ics", caption=cap)
                except Exception as e:
                    log.warning("ICS s'u dërgua te %s: %s", chat_id, e)
        except Exception as e:
            log.warning("gjenerimi i ICS dështoi: %s", e)


def _parse_slot_dt(date_s: str, time_s: str):
    """'2026-10-24' + '18:00' → datetime me zonën e Tiranës (ose None)."""
    try:
        d = datetime.strptime(f"{date_s} {time_s}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return None
    return d.replace(tzinfo=TIRANA)


async def adm_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F2: /slot <YYYY-MM-DD> <HH:MM> — shton orar konsulte të lirë."""
    if not is_admin(update.effective_user):
        return
    args = context.args or []
    dt = _parse_slot_dt(args[0], args[1]) if len(args) >= 2 else None
    if dt is None:
        await update.message.reply_text(
            "Përdorimi: /slot <YYYY-MM-DD> <HH:MM> — p.sh. /slot 2026-10-24 18:00")
        return
    if dt <= datetime.now(TIRANA):
        await update.message.reply_text(
            "⚠️ Ky orar është në të kaluarën — zgjidh një orar të ardhshëm.")
        return
    rec = store.add_slot(dt.isoformat(timespec="minutes"))
    await update.message.reply_text(
        f"✅ Orari u shtua: <b>{fmt_slot(dt)}</b>\n"
        f"id: <code>{rec['id']}</code> (fshihet me /slot_fshi)",
        parse_mode="HTML")


async def adm_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F2: /slotet — oraret e konsultave me gjendjen e tyre."""
    if not is_admin(update.effective_user):
        return
    slots = store.list_slots()
    if not slots:
        await update.message.reply_text(
            "S'ka orare të shtuara. Shto me /slot <YYYY-MM-DD> <HH:MM>.")
        return
    lines = ["🗓 <b>Oraret e konsultave</b>:\n"]
    for s in slots:
        if s.get("booked_by") is not None:
            c = store.get_client_any(s["booked_by"]) or {}
            st = f"🔒 i rezervuar nga {_esc(c.get('name')) or s['booked_by']}"
        else:
            st = "🟢 i lirë"
        lines.append(
            f"• {fmt_slot(parse_iso(s['dt_iso']))} — {st} · "
            f"id <code>{s['id']}</code>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def adm_slot_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F2: /slot_fshi <slot_id> — fshin vetëm orar të lirë."""
    if not is_admin(update.effective_user):
        return
    if not context.args:
        await update.message.reply_text("Përdorimi: /slot_fshi <slot_id> (id nga /slotet)")
        return
    if store.delete_slot(context.args[0]):
        await update.message.reply_text("✅ Orari u fshi.")
    else:
        await update.message.reply_text(
            "Ky orar s'u gjet, ose është i rezervuar dhe s'fshihet.")


# ---------------------------------------------------------------- kujtesat (F2/F3)
def plan_reminders(at: datetime = None):
    """Funksion i pastër/testueshëm: llogarit veprimet e kujtesave për
    momentin `at` dhe shënon flamujt në ruajtje (kujtesa nuk dërgohet
    dy herë). Kthen listë {'kind', 'chat_id', 'text'} — ekzekutimi i
    dërgimit bëhet nga _reminder_loop. Datat/oraret në tekste janë të
    dhëna funksionale (të lejuara); tekstet statike pa shifra."""
    at = at or datetime.now(timezone.utc)
    actions = []
    # (a) kujtesa për konsultat e miratuara që nisin brenda 3 orëve
    for bid, b in store.list_bookings().items():
        if b.get("status") != "approved" or b.get("reminded"):
            continue
        slot = store.get_slot(b["slot_id"])
        dt = parse_iso(slot["dt_iso"]) if slot else None
        if dt is None or not (timedelta(0) <= dt - at <= BOOKING_REMIND_WITHIN):
            continue
        svc = SERVICE_NAMES.get(b["service_key"], b["service_key"])
        clang = store.get_lang(b["client_id"])
        client = store.get_client_any(b["client_id"]) or {}
        actions.append({
            "kind": "booking_client", "chat_id": b["client_id"],
            "text": t(clang, "reminder_booking_client",
                      service=svc_name(b["service_key"], clang),
                      slot=fmt_slot(dt, clang))})
        slot_label = fmt_slot(dt)
        actions.append({
            "kind": "booking_admin", "chat_id": ADMIN_ID,
            "text": REMINDER_BOOKING_ADMIN.format(
                name=_esc(client.get("name")), username=_esc(client.get("username")) or "—",
                client_id=b["client_id"], service=svc, slot=slot_label)})
        store.set_booking_reminded(bid, True)
    # (b) kujtesa e skadimit të aksesit (brenda 3 ditëve)
    reminded_names = []
    for uid_s, rec in store.list_clients().items():
        if rec.get("revoked"):
            continue
        exp = parse_iso(rec.get("expires_at"))
        if exp is None or not (timedelta(0) < exp - at <= EXPIRY_REMIND_WITHIN):
            continue
        if rec.get("expiry_reminded_for") == rec.get("expires_at"):
            continue
        uid = int(uid_s)
        actions.append({
            "kind": "expiry_client", "chat_id": uid,
            "text": t(store.get_lang(uid), "expiry_client",
                      date=fmt_date(rec["expires_at"]))})
        store.mark_expiry_reminded(uid)
        reminded_names.append(
            f"{_esc(rec.get('name'))} (@{_esc(rec.get('username')) or '—'}, id {uid})")
    if reminded_names:
        actions.append({
            "kind": "expiry_admin_summary", "chat_id": ADMIN_ID,
            "text": "⏰ <b>Kujtesë skadimi — klientët që u njoftuan</b>\n"
                    + "\n".join(f"• {n}" for n in reminded_names)
                    + "\n\nAfati i tyre skadon brenda pak ditësh — "
                      "zgjatje me /zgjat <user_id>."})
    return actions


# ---------------------------------------------------------------- F6: raporti javor
def build_digest_text(week: str, counters: dict, at: datetime = None) -> str:
    """Teksti i raportit javor (vetëm admin — shifrat lejohen këtu):
    numëruesit e javës + klientët aktivë tani + ata që skadojnë
    brenda pak ditësh (me emra) + pikat në pritje të veprimit."""
    at = at or datetime.now(timezone.utc)
    c = counters or {}
    active, expiring = 0, []
    for uid_s, rec in store.list_clients().items():
        if rec.get("revoked"):
            continue
        exp = parse_iso(rec.get("expires_at"))
        if exp is None or exp <= at:
            continue
        active += 1
        if exp - at <= EXPIRY_REMIND_WITHIN:
            expiring.append(_esc(rec.get("name")) or uid_s)
    pend_req = len(store.list_requests(status="pending"))
    pend_book = len([b for b in store.list_bookings().values()
                     if b.get("status") == "pending"])
    lines = [
        f"📊 <b>RAPORTI JAVOR — {week}</b>",
        "",
        f"👥 Klientë të rinj: <b>{c.get('clients', 0)}</b>",
        f"📝 Kërkesa shërbimi: <b>{c.get('requests', 0)}</b> "
        f"(miratuar: {c.get('requests_approved', 0)})",
        f"🚀 Brief-e projektesh: <b>{c.get('briefs', 0)}</b>",
        f"🗓 Konsulta të kërkuara: <b>{c.get('bookings', 0)}</b> "
        f"(miratuar: {c.get('bookings_approved', 0)})",
        f"⭐ Vlerësime të marra: <b>{c.get('reviews', 0)}</b>",
        "",
        f"👥 Klientë aktivë tani: <b>{active}</b>",
    ]
    if expiring:
        lines.append("⏰ Skadojnë brenda pak ditësh: "
                     + ", ".join(expiring))
    lines += [
        "",
        f"🔔 Në pritje të veprimit tënd: <b>{pend_req}</b> kërkesë(a), "
        f"<b>{pend_book}</b> konsultë(a).",
    ]
    return "\n".join(lines)


def plan_digest(at: datetime = None):
    """F6: planifikues i pastër — të hënën (ora e Tiranës) pas orës
    nëntë, një herë në javë, kthen veprimin e raportit për javën e
    kaluar (ose javën rrjedhëse në ekzekutimin e parë). Flamuri
    vendoset para kthimit — raporti s'dërgohet dy herë."""
    at = at or datetime.now(timezone.utc)
    local = at.astimezone(TIRANA)
    if local.weekday() != 0 or local.hour < 9:
        return []
    cur = Store.week_key(at)
    if store.get_last_digest_week() == cur:
        return []
    prev_local = local - timedelta(days=7)
    prev = Store.week_key(prev_local)
    counters = store.weekly_counters(prev)
    week_label = prev
    if not counters:
        counters = store.weekly_counters(cur)
        week_label = cur
    store.set_last_digest_week(cur)
    return [{"kind": "digest", "chat_id": ADMIN_ID,
             "text": build_digest_text(week_label, counters, at)}]


# ================================================================
# Paketa 4 — ROJA E LINKEVE (kontroll javor, hesht kur gjithçka
# punon) dhe KUJTESA E MËNGJESIT për pikat në pritje > 24 orë.
# Të dyja planifikohen nga _reminder_loop, si kujtesat e tjera.
# ================================================================
LINK_CHECK_EVERY_DAYS = 7
_LINK_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0 Safari/537.36")


def collect_link_urls():
    """URL-t që kontrollon roja: WORKS + WORKS_EN të dedupliluara
    (rendi i parë që shfaqen) + WEBAPP_URL."""
    seen, out = set(), []
    for table in (WORKS, WORKS_EN):
        for items in table.values():
            for _label, url in items:
                if url and url not in seen:
                    seen.add(url)
                    out.append(url)
    if WEBAPP_URL not in seen:
        out.append(WEBAPP_URL)
    return out


def plan_link_check(at: datetime = None) -> bool:
    """Planifikues i pastër: True (dhe e shënon datën në settings)
    nëse kontrolli javor është i duhuri — s'është bërë kurrë ose
    kanë kaluar >= 7 ditë (data lokale e Tiranës) nga i fundit."""
    at = at or datetime.now(timezone.utc)
    today = at.astimezone(TIRANA).date()
    last_d = None
    last = store.get_setting("last_link_check")
    if last:
        try:
            last_d = datetime.strptime(str(last), "%Y-%m-%d").date()
        except ValueError:
            last_d = None
    if last_d is not None and (today - last_d).days < LINK_CHECK_EVERY_DAYS:
        return False
    store.set_setting("last_link_check", today.isoformat())
    return True


def _fetch_url_status(url: str) -> int:
    """Fetcher-i real i rojës: GET me redirect-e, timeout ~15s dhe
    UA normale browseri. Kthen kodin final HTTP (4xx/5xx vijnë nga
    HTTPError); gabimet e rrjetit ngrihen si përjashtime."""
    req = urllib.request.Request(url, headers={"User-Agent": _LINK_UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return int(resp.getcode() or 200)
    except urllib.error.HTTPError as e:
        return int(e.code)


def plan_link_actions(at: datetime = None, fetcher=None):
    """Kontrolli javor i linkeve (kur është i duhuri): çdo URL
    provohet deri në 2 herë — 2xx/3xx = OK, >= 400 = i vdekur,
    përjashtim pas riprovave = 'nuk u verifikua' (raportohet
    veçmas). Probleme → NJË veprim për adminin; përndryshe []."""
    at = at or datetime.now(timezone.utc)
    if not plan_link_check(at):
        return []
    fetcher = fetcher or _fetch_url_status
    dead, unverified = [], []
    for url in collect_link_urls():
        status, err = None, None
        for _attempt in (1, 2):
            try:
                status = fetcher(url)
                err = None
                break
            except Exception as e:  # rrjet i paarritshëm, DNS, timeout
                err = e
        if err is not None:
            unverified.append((url, type(err).__name__))
        elif status is not None and 200 <= int(status) < 400:
            continue  # OK — heshtje
        else:
            dead.append((url, status))
    if not dead and not unverified:
        return []
    lines = ["🔗 <b>Roja e linkeve</b> — kontrolli javor gjeti "
             "probleme:\n"]
    if dead:
        lines.append("❌ <b>Linke të vdekura:</b>")
        lines += [f"• {u} — HTTP {s}" for u, s in dead]
    if unverified:
        lines.append("\n❓ <b>Nuk u verifikuan</b> (problem rrjeti — "
                     "provohen sërish kontrollin tjetër):")
        lines += [f"• {u} — nuk u verifikua ({e})"
                  for u, e in unverified]
    return [{"kind": "link_watchdog", "chat_id": ADMIN_ID,
             "text": "\n".join(lines)}]


PENDING_OLD_AFTER = timedelta(hours=24)
_PENDING_KIND_LABELS = (
    ("requests", "Kërkesa shërbimi", "kërkesë shërbimi"),
    ("bookings", "Kërkesa konsulte", "kërkesë konsulte"),
    ("agreements", "Marrëveshje në pritje", "marrëveshje"),
    ("briefs", "Brief-e pa projekt", "brief projekti"),
)


def collect_pending_old(at: datetime = None):
    """Pikat në pritje më të vjetra se 24 orë: kërkesat e shërbimit,
    rezervimet dhe marrëveshjet 'pending' + brief-et pa projekt.
    Kthen {'counts': {kind: n}, 'oldest': (label, dt) | None}."""
    at = at or datetime.now(timezone.utc)
    cutoff = at - PENDING_OLD_AFTER
    items = []  # (created_dt, kind)
    for r in store.list_requests(status="pending"):
        dt = parse_iso(r.get("created_at"))
        if dt and dt <= cutoff:
            items.append((dt, "requests"))
    for b in store.list_bookings().values():
        if b.get("status") != "pending":
            continue
        dt = parse_iso(b.get("created_at"))
        if dt and dt <= cutoff:
            items.append((dt, "bookings"))
    for a in store.list_agreements(status="pending"):
        dt = parse_iso(a.get("sent_at"))
        if dt and dt <= cutoff:
            items.append((dt, "agreements"))
    for br in store.list_briefs():
        if br.get("project_id"):
            continue
        dt = parse_iso(br.get("created_at"))
        if dt and dt <= cutoff:
            items.append((dt, "briefs"))
    counts = {}
    for _dt, kind in items:
        counts[kind] = counts.get(kind, 0) + 1
    oldest = None
    if items:
        dt, kind = min(items, key=lambda x: x[0])
        label = {k: lo for k, _pl, lo in _PENDING_KIND_LABELS}[kind]
        oldest = (label, dt)
    return {"counts": counts, "oldest": oldest}


def plan_pending_digest(at: datetime = None):
    """Kujtesa e mëngjesit për pikat në pritje > 24 orë: pas orës
    nëntë (ora e Tiranës), një herë në ditë, VETËM nëse ka pika —
    përndryshe heshtje totale. Flamuri vendoset kur dërgohet."""
    at = at or datetime.now(timezone.utc)
    local = at.astimezone(TIRANA)
    if local.hour < 9:
        return []
    today = local.date().isoformat()
    if store.get_setting("last_pending_digest") == today:
        return []
    found = collect_pending_old(at)
    counts = found["counts"]
    if not counts:
        return []
    store.set_setting("last_pending_digest", today)
    lines = ["🔔 <b>Kujtesë: pika në pritje prej më shumë se "
             "një dite</b>\n"]
    for kind, plural, _single in _PENDING_KIND_LABELS:
        if counts.get(kind):
            lines.append(f"• {plural}: <b>{counts[kind]}</b>")
    if found["oldest"]:
        label, dt = found["oldest"]
        days = max(1, (at - dt).days)
        lines.append(f"\n⏰ Më e vjetra: {label} · {days} ditë")
    return [{"kind": "pending_digest", "chat_id": ADMIN_ID,
             "text": "\n".join(lines)}]


async def adm_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F6: /raport — raporti i javës rrjedhëse, sipas kërkesës."""
    if not is_admin(update.effective_user):
        return
    now = datetime.now(timezone.utc)
    key = Store.week_key(now)
    await update.message.reply_text(
        build_digest_text(key, store.weekly_counters(key), now),
        parse_mode="HTML")


async def _link_watchdog_run(app):
    """Paketa 4: roja e linkeve si detyrë MË VETE në sfond —
    kontrolli bëhet në thread (rrjeti mund të jetë i ngadaltë)
    dhe njoftimi i adminit (vetëm nëse ka probleme) dërgohet pa
    vonuar asnjëherë kujtesat e tjera të loop-it."""
    try:
        acts = await asyncio.to_thread(plan_link_actions,
                                       datetime.now(timezone.utc))
    except Exception as e:
        log.warning("roja e linkeve dështoi: %s", e)
        return
    for act in acts:
        try:
            await app.bot.send_message(act["chat_id"], act["text"],
                                       parse_mode="HTML")
        except Exception as e:
            log.warning("roja e linkeve: dërgimi dështoi: %s", e)


async def _reminder_loop(app):
    """Detyra në sfond: çdo ~30 min dërgon kujtesat e planifikuara.
    Gabimet kapen gjithmonë — loop-i s'rrëzon kurrë aplikacionin."""
    while True:
        try:
            # çdo planifikues izolohet në try-në e vet (auditi 360°,
            # D10): dështimi i njërit s'i bllokon të tjerët atë cikël
            acts = []
            for planner in (plan_reminders, plan_digest,
                            plan_pending_digest):
                try:
                    acts += planner(datetime.now(timezone.utc))
                except Exception as e:
                    log.warning("planifikuesi %s dështoi: %s",
                                getattr(planner, "__name__", "planner"), e)
            for act in acts:
                try:
                    await app.bot.send_message(
                        act["chat_id"], act["text"], parse_mode="HTML")
                except Exception as e:
                    log.warning("kujtesa (%s) s'u dërgua: %s",
                                act.get("kind"), e)
            # paketa 4: roja javore e linkeve — detyrë më vete
            asyncio.create_task(_link_watchdog_run(app))
        except Exception as e:
            log.warning("reminder loop gabim: %s", e)
        await asyncio.sleep(1800)


async def post_init(app):
    """Regjistrohet në build_app: nis detyrën e kujtesave në sfond."""
    task = asyncio.create_task(_reminder_loop(app))
    try:
        app.bot_data["reminder_task"] = task
    except Exception:
        pass
    log.info("Kujtesat automatike u aktivizuan (konsulta + skadime).")


# ---------------------------------------------------------------- F4: broadcast
async def adm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/njoftim <teksti...> — broadcast te çdo klient me akses aktiv.
    Vetëm admin; pa tekst → përdorimi; dërgimi bëhet me radhë dhe
    dështimet (klientë që e kanë bllokuar botin etj.) numërohen."""
    if not is_admin(update.effective_user):
        return
    text = " ".join(context.args or []).strip()
    if not text:
        await update.message.reply_text(
            "Përdorimi: /njoftim <teksti i njoftimit>\n"
            "Njoftimi u shkon të gjithë klientëve me akses aktiv.")
        return
    body = f"📣 <b>Njoftim nga Erioni</b>\n\n{text}"
    delivered = failed = 0
    for uid_s in list(store.list_clients()):
        uid = int(uid_s)
        if store.get_client(uid) is None:  # jo aktiv / skaduar / revokuar
            continue
        try:
            await context.bot.send_message(uid, body, parse_mode="HTML")
            delivered += 1
        except Exception as e:
            failed += 1
            log.warning("broadcast te %s dështoi: %s", uid, e)
    await update.message.reply_text(
        f"📣 <b>Njoftimi u dërgua.</b>\n"
        f"✓ Të dorëzuara: {delivered}\n"
        f"✗ Dështuan: {failed}", parse_mode="HTML")


# ---------------------------------------------------------------- biseda direkte (relay)
async def talk_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    context.user_data["talk"] = True
    lang = ulang(update.effective_user)
    await update.effective_message.reply_text(
        t(lang, "talk_start"), parse_mode="HTML")


async def talk_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("talk", None)
    if has_access(update.effective_user):
        lang = ulang(update.effective_user)
        await update.effective_message.reply_text(
            t(lang, "talk_stop"), reply_markup=client_kb(lang))


# ---------- F6: relay i plotë mediatik ----------
MEDIA_ATTRS = ("voice", "video_note", "document", "animation", "sticker",
               "audio", "video", "location", "contact", "photo")


def media_kind(msg):
    """Lloji i medias së mesazhit (ose None nëse s'ka media)."""
    if msg is None:
        return None
    for attr in MEDIA_ATTRS:
        try:
            if getattr(msg, attr, None):
                return attr
        except Exception:
            pass
    return None


async def _deliver_to_client(context, target: int, msg) -> bool:
    """Dërgon përgjigjen e adminit te klienti: tekst → mesazh i
    formatuar; media → kopjim native (copy_message), që klienti ta
    marrë file-in/zërin siç u dërgua."""
    if getattr(msg, "text", None):
        await context.bot.send_message(
            target, t(store.get_lang(target), "admin_says", text=msg.text),
            parse_mode="HTML")
        return True
    if media_kind(msg):
        await context.bot.copy_message(
            target, from_chat_id=msg.chat_id, message_id=msg.message_id)
        return True
    return False


async def adm_pergjigju(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """F6: /pergjigju <user_id> — mesazhi tjetër i adminit (tekst ose
    media) i dërgohet atij klienti; pastaj mënyra mbyllet vetë."""
    if not is_admin(update.effective_user):
        return
    uid, _ = _parse_uid_arg(context)
    if uid is None:
        await update.message.reply_text(
            "Përdorimi: /pergjigju <user_id> — pastaj shkruaj ose dërgo "
            "median; mesazhi yt tjetër i shkon klientit.")
        return
    rec = store.get_client_any(uid)
    if not rec:
        await update.message.reply_text("Ky user_id nuk u gjet te klientët.")
        return
    context.user_data["reply_to"] = uid
    await update.message.reply_text(
        f"✍️ Po i përgjigjesh <b>{_esc(rec.get('name')) or 'klientit'}</b> "
        f"(id {uid}).\nMesazhi yt i radhës — tekst ose media — i dërgohet "
        "atij direkt. /anulo për anullim.", parse_mode="HTML")


async def admin_pergjigju_step(update: Update,
                               context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Nëse admini është në mënyrën /pergjigju, mesazhi aktual i
    dërgohet klientit të zgjedhur dhe mënyra mbyllet."""
    uid = context.user_data.get("reply_to")
    if not uid:
        return False
    msg = update.message
    if msg is None or not (getattr(msg, "text", None) or media_kind(msg)):
        return False
    try:
        await _deliver_to_client(context, uid, msg)
    except Exception as e:
        await msg.reply_text(f"⚠️ Dërgimi dështoi: {e}")
        return True
    context.user_data.pop("reply_to", None)
    await msg.reply_text("✔️ U dërgua te klienti.")
    return True


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admini i përgjigjet mesazhit të përcjellë → relay te klienti.
    Teksti dërgohet i formatuar; media kopjohet native (F6)."""
    msg = update.message
    if not msg or not msg.reply_to_message:
        return False
    target = store.relay_target(msg.reply_to_message.message_id)
    if not target:
        return False
    try:
        if not await _deliver_to_client(context, target, msg):
            return False
        await msg.reply_text("✔️ U dërgua te klienti.")
    except Exception as e:
        await msg.reply_text(f"⚠️ Dërgimi dështoi: {e}")
    return True


async def media_dispatch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatch-i i mesazheve JO-tekst (foto, zë, dokumente...):
    admini → /pergjigju ose reply native me media; klienti në talk
    mode → header identiteti + kopjim te admini (me hartë relay);
    vizitori → vetëm ekrani i kyçjes. Teksti kalon nga fallback_text."""
    user = update.effective_user
    msg = update.message
    if user is None or msg is None:
        return
    if is_admin(user):
        # F5: kapja e zërit të mirëseardhjes ka përparësi mbi relay-n
        if context.user_data.get("capture_voice"):
            voice = getattr(msg, "voice", None)
            if voice is not None:
                store.set_welcome_voice(voice.file_id)
                context.user_data.pop("capture_voice", None)
                await msg.reply_text(
                    "🎙 <b>U ruajt!</b> Mesazhi zanor i mirëseardhjes u "
                    "vendos — klientët e rinj do ta marrin pas "
                    "aktivizimit.\n/heq me /hiq_mireseardhjen.",
                    parse_mode="HTML")
                return
            await msg.reply_text(
                "🎙 Po pres një <b>mesazh zanor</b> — dërgoje tani, ose "
                "/anulo për ta lënë siç është.", parse_mode="HTML")
            return
        if await admin_pergjigju_step(update, context):
            return
        await admin_reply(update, context)
        return
    lang = ulang(user)
    flow = context.user_data.get("flow") or {}
    if flow.get("kind"):
        await msg.reply_text(t(lang, "flow_needs_text"))
        return
    if not has_access(user):
        await show_lock(update, context, t(lang, "lock_note_private"))
        return
    if context.user_data.get("talk"):
        # talk: ÇDO mesazh jo-tekst përcillet me copy_message — edhe
        # llojet jashtë MEDIA_ATTRS (dice, poll, venue...) që Telegrami
        # di t'i kopjojë; caption-i NUK është routing teksti (D15)
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"💬 <b>Mesazh nga klienti</b> {_esc(user.first_name)} "
                f"(@{_esc(user.username) or '—'}, id {user.id}):",
                parse_mode="HTML")
            copied = await context.bot.copy_message(
                ADMIN_ID, from_chat_id=msg.chat_id,
                message_id=msg.message_id)
            store.map_relay(copied.message_id, user.id)
            await msg.reply_text(t(lang, "talk_sent"))
            await _maybe_after_hours(context, user, lang)
        except Exception as e:
            log.warning("kopjimi i medias së klientit dështoi: %s", e)
            await msg.reply_text(t(lang, "talk_send_fail"))
        return
    if media_kind(msg) is None:
        return  # lloj i panjohur jashtë talk-ut: injorohet (i përcaktuar)
    await msg.reply_text(t(lang, "talk_media_hint"), parse_mode="HTML")


def _exit_client_flow(context: ContextTypes.DEFAULT_TYPE):
    """Del nga çdo rrjedhë klienti aktive (brief / rezervim / vlerësim /
    bisedë direkte) dhe pastron të dhënat e përkohshme të rrjedhës."""
    context.user_data.pop("flow", None)
    context.user_data.pop("brief", None)
    context.user_data.pop("booking", None)
    context.user_data.pop("talk", None)


async def _route_menu_action(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             action: str, lang: str) -> bool:
    """Navigimi i menusë së klientit sipas veprimit (MENU_ROUTES).
    Kthen True kur veprimi u trajtua. Sjellja është e njëjtë si
    dispatch-i i mëparshëm në gjendje idle — përfshirë portat e
    aksesit te home/guide/more për vizitorët."""
    user = update.effective_user
    if action == "services":
        await show_services(update, context)
    elif action == "works":
        await show_works(update, context)
    elif action == "card":
        await show_card(update, context)
    elif action == "access":
        await show_access(update, context)
    elif action == "talk":
        await talk_start(update, context)
    elif action == "brief":
        await brief_menu_start(update, context)
    elif action == "faq":
        await show_faq(update, context)
    elif action == "cv":
        await show_cv(update, context)
    elif action == "projects":
        await show_projects(update, context)
    elif action == "booking":
        await booking_menu_start(update, context)
    elif action == "lang":
        await show_lang_chooser(update, context)
    elif action == "home":
        # paketa 4: 🏠 Kreu — kthen te faqja kryesore me tastierën
        # kryesore nga kudo
        if not has_access(user):
            await show_lock(update, context, t(lang, "lock_note_private"))
            return True
        await show_home(update, context)
    elif action == "guide":
        # paketa 4: 🧭 Udhëzuesi — rinis turin, edhe pas përfundimit
        if not has_access(user):
            await show_lock(update, context, t(lang, "lock_note_private"))
            return True
        await start_tour(context, user.id, lang)
    elif action in ("more", "back_home"):
        # paketa 3 (F4): ndërrimi kryesore <-> "Më shumë"
        if not has_access(user):
            await show_lock(update, context, t(lang, "lock_note_private"))
            return True
        await update.message.reply_text(
            t(lang, "menu_prompt"),
            reply_markup=client_kb(lang, more=(action == "more")))
    else:
        return False
    return True


async def _client_text_dispatch(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                text: str, lang: str,
                                admin_tester: bool = False) -> bool:
    """Trajtimi i tekstit për zonën e klientit. Kthen True kur teksti
    u trajtua; False kur s'ka asgjë për të bërë (vetëm admini në idle
    me tekst të rastësishëm — heshtja e vjetër e adminit ruhet).

    RREGULLI I RI (rregullimi UX): etiketa e menusë (MENU_ROUTES, të
    dyja gjuhët) NDËRPRET çdo rrjedhë aktive — brief, rezervim,
    vlerësim, bisedë — në vend që të gëlltitet prej saj (bug-u i
    screenshot-it: "☰ Më shumë" gjatë brief-it s'prodhonte asgjë).
    Vizitori i kyçur përjashtohet: rrjedhat e derës (code/req) e
    konsumojnë tekstin si më parë, pa ndryshim."""
    user = update.effective_user
    flow = context.user_data.get("flow") or {}
    kind = flow.get("kind")
    # --- dera (vizitori): gjendja e kyçjes NUK ndryshon ---
    if kind == "code":
        await code_text(update, context)
        return True
    if kind == "req":
        await req_text_step(update, context)
        return True
    action = MENU_ROUTES.get(text)
    talking = bool(context.user_data.get("talk"))
    in_flow = kind in ("brief", "booking", "review") or talking
    # --- aksesi skadoi/u revokua NË MES të rrjedhës (D3): rrjedha
    # pastrohet dhe mesazhi zbarkon në rrugën e kyçjes, jo në rrjedhë
    if in_flow and not has_access(user):
        _exit_client_flow(context)
        return False
    # --- ndërprerja globale: etiketa e menusë mund çdo rrjedhë ---
    if action and in_flow and has_access(user):
        same_flow = ((action == "brief" and kind == "brief")
                     or (action == "booking" and kind == "booking")
                     or (action == "talk" and talking and kind is None))
        _exit_client_flow(context)
        if not same_flow:
            # shënimi dërgohet NJË herë, vetëm kur rrjedha braktiset
            # vërtet; rinisja e së njëjtës rrjedhë s'ka nevojë për të
            await update.message.reply_text(t(lang, "flow_interrupted"))
        await _route_menu_action(update, context, action, lang)
        return True
    # --- rrjedhat që presin tekst ---
    if kind == "brief":
        await brief_text_step(update, context)
        return True
    if kind == "review":  # F1: komenti i vlerësimit
        await review_text_step(update, context)
        return True
    if kind == "booking":
        await booking_text_step(update, context)
        return True
    # --- idle: navigimi normal i menusë ---
    if action:
        return await _route_menu_action(update, context, action, lang)
    if admin_tester:
        return False
    if has_access(user):
        if talking:
            # relay i bisedës (D4/D19): trupi shpëton HTML-in, prehet
            # te kufiri i Telegramit dhe dështimi i dërgimit i kthehet
            # klientit si mesazh — jo si përjashtim që ikën nga handler-i
            body = update.message.text or ""
            if len(body) > 3800:
                body = body[:3800] + "…"
            try:
                sent = await context.bot.send_message(
                    ADMIN_ID,
                    f"💬 <b>Mesazh nga klienti</b> {_esc(user.first_name)} "
                    f"(@{_esc(user.username) or '—'}, id {user.id}):\n\n"
                    f"{_esc(body)}",
                    parse_mode="HTML")
            except Exception as e:
                log.warning("relay i bisedës dështoi: %s", e)
                await update.message.reply_text(t(lang, "talk_send_fail"))
                return True
            store.map_relay(sent.message_id, user.id)
            await update.message.reply_text(t(lang, "talk_sent"))
            await _maybe_after_hours(context, user, lang)
        else:
            await update.message.reply_text(
                t(lang, "menu_prompt"), reply_markup=client_kb(lang))
        return True
    return False


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatch-i qendror i tekstit: rrjedhat aktive → menuja → relay → kyçja."""
    user = update.effective_user
    text = (update.message.text or "").strip()
    lang = ulang(user)
    if is_admin(user):
        if context.user_data.get("capture_voice"):  # F5: tekst ≠ zë
            await update.message.reply_text(
                "🎙 Po pres një <b>mesazh zanor</b> — dërgoje tani, ose "
                "/anulo për ta lënë siç është.", parse_mode="HTML")
            return
        if await admin_pergjigju_step(update, context):
            return
        await admin_reply(update, context)
        # Admini duke testuar ekranet e klientit: etiketat e menusë dhe
        # rrjedhat e klientit trajtohen njësoj si për klientin — teksti
        # i rastësishëm në idle mbetet pa përgjigje, si më parë.
        await _client_text_dispatch(update, context, text, lang,
                                    admin_tester=True)
        return
    if await _client_text_dispatch(update, context, text, lang):
        return
    await show_lock(update, context, t(lang, "lock_note_private"))


async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("req", None)
    context.user_data.pop("brief", None)
    context.user_data.pop("booking", None)
    context.user_data.pop("reply_to", None)
    context.user_data.pop("capture_voice", None)  # F5
    context.user_data.pop("flow", None)
    lang = ulang(update.effective_user)
    if has_access(update.effective_user):
        await update.effective_message.reply_text(
            t(lang, "cancelled"), reply_markup=client_kb(lang))
    else:
        await show_lock(update, context)


# ---------------------------------------------------------------- komandat e adminit
async def adm_create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        return
    days, note = DEFAULT_DAYS, ""
    args = context.args or []
    if args:
        if re.fullmatch(r"-?[0-9]+", args[0] or ""):
            # numër (edhe negativ/absurd): shtrënguar 1..365 pa int()
            # mbi vargje gjigante — shenja + gjatësia vendosin skajin
            digits = args[0].lstrip("-")
            if args[0].startswith("-") or digits.strip("0") == "":
                days = 1
            elif len(digits) > 3:
                days = 365
            else:
                days = max(1, min(365, int(args[0])))
            note = " ".join(args[1:])
        else:
            note = " ".join(args)
    code = store.create_code(days=days, note=note)
    uname = context.bot.username or "<bot>"
    await update.message.reply_text(
        "🔑 <b>Kod i ri unik u krijua</b>\n\n"
        f"Kodi: <code>{code}</code>\n"
        f"Shënimi: {note or '—'}\n"
        f"Afati: {days} ditë nga sot\n\n"
        "Jepja klientit në DM, ose dërgo linkun e tij personal:\n"
        f"<code>https://t.me/{uname}?start={code}</code>\n\n"
        "⚠️ Kodi lidhet me llogarinë e parë që e përdor — përcjellja nuk punon.",
        parse_mode="HTML")


async def adm_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        return
    rows = store.list_codes()
    if not rows:
        await update.message.reply_text("S'ka kode të krijuara ende.")
        return
    lines = ["🔑 <b>Kodet e krijuara</b> (teksti i kodit s'ruhet — shihet vetëm në krijim):\n"]
    for _, r in sorted(rows, key=lambda x: x[1].get("created_at") or "",
                       reverse=True)[:20]:
        if r.get("revoked"):
            st = "🚫 revokuar"
        elif r.get("bound_user_id"):
            st = f"🔓 përdorur nga id {r['bound_user_id']}"
        else:
            st = "🟡 në pritje (i papërdorur)"
        lines.append(f"• {st} · skadon {fmt_date(r.get('expires_at'))} · {r.get('note') or '—'}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def adm_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        return
    clients = store.list_clients()
    if not clients:
        await update.message.reply_text("S'ka klientë ende.")
        return
    lines = ["👥 <b>Klientët</b>:\n"]
    for uid, r in clients.items():
        st = "🚫 revokuar" if r.get("revoked") else f"✅ deri {fmt_date(r.get('expires_at'))}"
        lines.append(f"• {_esc(r.get('name'))} (@{_esc(r.get('username')) or '—'}, id <code>{uid}</code>) — "
                     f"{_esc(r.get('service')) or '—'} · {st}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ---------------------------------------------------------------- paketa 4: dosja e klientit + shënimet private
AGR_STATUS_LABELS = {"pending": "në pritje", "accepted": "e pranuar",
                     "declined": "e refuzuar"}


def build_dossier_text(uid: int):
    """Dosja e klientit në NJË mesazh (vetëm admin): identiteti,
    gjuha, aksesi + skadimi, burimi (kod/kërkesë + shënimi),
    projektet me fazat, rezervimet (e radhës + në pritje),
    marrëveshja e fundit, vlerësimet, numri i brief-eve, data e
    aktivizimit dhe shënimet e fundit private të adminit.
    Kthen None nëse klienti s'ekziston."""
    rec = store.get_client_any(uid)
    if not rec:
        return None
    now = datetime.now(timezone.utc)
    lang = rec.get("lang") or store.get_lang(uid)
    lines = [
        "🗂 <b>DOSJA E KLIENTIT</b>",
        f"👤 {_esc(rec.get('name')) or '—'} (@{_esc(rec.get('username')) or '—'}, "
        f"id <code>{uid}</code>)",
        f"🌍 Gjuha: {'English' if lang == 'en' else 'Shqip'}",
    ]
    exp = parse_iso(rec.get("expires_at"))
    if rec.get("revoked"):
        access = "🚫 i revokuar"
    elif exp and exp <= now:
        access = f"⌛ i skaduar më {fmt_date(rec.get('expires_at'))}"
    else:
        access = f"✅ aktiv deri më {fmt_date(rec.get('expires_at'))}"
    lines.append(f"🔐 Aksesi: {access}")
    via = rec.get("via")
    if via == "code":
        note = ""
        for _h, c in store.list_codes():
            if c.get("bound_user_id") == uid:
                note = c.get("note") or ""
                break
        src = "kod personal" + (f" · shënimi i kodit: {_esc(note)}" if note
                                 else "")
    elif via == "approval":
        src = "kërkesë shërbimi e miratuar"
        if rec.get("service"):
            src += f" · shërbimi: {_esc(rec['service'])}"
    else:
        src = via or "—"
    lines.append(f"🧾 Burimi: {src}")
    lines.append(f"📅 U aktivizua më: {fmt_date(rec.get('activated_at'))}")
    # projektet me fazën aktuale
    lines.append("\n🚧 <b>Projektet:</b>")
    projects = store.list_projects(uid)
    if projects:
        for p in projects:
            stage = PROJECT_STAGES[max(0, min(
                len(PROJECT_STAGES) - 1, _safe_int(p.get("stage"), 0)))]
            mark = "✅ i përfunduar" if p.get("done") else stage
            lines.append(f"• {_esc(p.get('title')) or 'Projekt'} — {mark}")
    else:
        lines.append("• asnjë")
    # rezervimet: konsulta e radhës e miratuar + numri në pritje
    mine = [b for b in store.list_bookings().values()
            if b.get("client_id") == uid]
    pend_b = [b for b in mine if b.get("status") == "pending"]
    upcoming = []
    for b in mine:
        if b.get("status") != "approved":
            continue
        slot = store.get_slot(b["slot_id"])
        dt = parse_iso(slot["dt_iso"]) if slot else None
        if dt and dt > now:
            upcoming.append((dt, b))
    upcoming.sort(key=lambda x: x[0])
    lines.append("\n🗓 <b>Rezervimet:</b>")
    if upcoming:
        dt, b = upcoming[0]
        lines.append(
            f"• Konsulta e radhës: <b>{fmt_slot(dt)}</b> "
            f"({SERVICE_NAMES.get(b['service_key'], b['service_key'])})")
    else:
        lines.append("• asnjë konsultë e miratuar në të ardhmen")
    lines.append(f"• Në pritje: {len(pend_b)}")
    # marrëveshja më e fundit
    lines.append("\n✍ <b>Marrëveshja:</b>")
    agr = store.latest_agreement_for(uid)
    if agr:
        st = AGR_STATUS_LABELS.get(agr.get("status"),
                                   agr.get("status") or "—")
        when = agr.get("decided_at") or agr.get("sent_at")
        lines.append(f"• «{_esc(agr.get('title')) or '—'}» — {st} · "
                     f"{fmt_date(when)}")
    else:
        lines.append("• asnjë")
    # vlerësimet: numri + yjet e fundit (vetëm simbole për klientin;
    # dosja është zonë admini)
    revs = [r for r in store.list_reviews() if r.get("client_id") == uid]
    lines.append("\n⭐ <b>Vlerësimet:</b>")
    if revs:
        stars = "⭐" * max(0, min(5, _safe_int(revs[0].get("stars"), 0)))
        lines.append(f"• gjithsej {len(revs)} · i fundit: {stars}")
    else:
        lines.append("• asnjë")
    lines.append(f"\n🚀 <b>Brief-e projektesh:</b> "
                 f"{len(store.list_briefs(uid))}")
    # shënimet private të adminit — vetëm 3 të fundit, me data
    notes = store.client_notes(uid)
    if notes:
        lines.append("\n🗒 <b>Shënimet e tua private (më të fundit):</b>")
        for n in notes[-3:]:
            lines.append(f"• {fmt_date(n.get('ts'))} — "
                         f"{_esc(n.get('text'))}")
    return "\n".join(lines)


async def adm_dossier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paketa 4: /dosja <user_id> — dosja e plotë e klientit."""
    if not is_admin(update.effective_user):
        return
    uid, _ = _parse_uid_arg(context)
    if uid is None:
        await update.message.reply_text("Përdorimi: /dosja <user_id>")
        return
    text = build_dossier_text(uid)
    if text is None:
        await update.message.reply_text("Ky user_id nuk u gjet te klientët.")
        return
    await update.message.reply_text(text, parse_mode="HTML")


async def adm_client_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paketa 4: /shenim_klienti <user_id> <teksti> — shënim privat
    i adminit te regjistri i klientit (shfaqet vetëm te /dosja)."""
    if not is_admin(update.effective_user):
        return
    uid, rest = _parse_uid_arg(context)
    if uid is None or not rest:
        await update.message.reply_text(
            "Përdorimi: /shenim_klienti <user_id> <teksti i shënimit>")
        return
    note = store.add_client_note(uid, " ".join(rest))
    if note is None:
        await update.message.reply_text("Ky user_id nuk u gjet te klientët.")
        return
    rec = store.get_client_any(uid) or {}
    await update.message.reply_text(
        f"🗒 Shënimi u shtua te dosja e <b>{_esc(rec.get('name')) or 'klientit'}</b> "
        f"(id {uid}) — e sheh te /dosja.", parse_mode="HTML")


async def adm_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fiks 4: /backup — vetëm admin; për të tjerët heshtje totale."""
    if not is_admin(update.effective_user):
        return
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    await send_backup(
        context,
        f"💾 Backup manual i të dhënave — {now} (UTC)\n"
        f"👥 Klientë gjithsej: {len(store.list_clients())}")
    await update.message.reply_text("💾 Backup-i u dërgua më sipër 👆")


async def adm_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/statusi [teksti] — statusi i disponueshmërisë që shohin klientët.
    Vetëm admin; për të gjithë të tjerët heshtje totale (si /backup)."""
    if not is_admin(update.effective_user):
        return
    args = [a for a in (context.args or []) if a.strip()]
    if not args:
        await update.message.reply_text(
            "🟢 <b>Statusi aktual i disponueshmërisë</b>\n\n"
            f"{store.get_status()}\n\n"
            "Për ta ndryshuar: /statusi &lt;teksti i ri&gt; "
            "(max ~120 karaktere). Shfaqet te faqja kryesore e klientëve.",
            parse_mode="HTML")
        return
    text = " ".join(args).strip()[:120]
    store.set_status(text)
    await update.message.reply_text(
        "✅ <b>Statusi u përditësua</b> — tani klientët shohin:\n\n"
        f"{store.get_status()}", parse_mode="HTML")


# ================================================================
# Paketa 3 (F6) — ORARI I PUNËS + PËRGJIGJJA AUTOMATIKE JASHTË ORARIT
# Kur mesazhi i klientit përcillet jashtë orarit, klienti merr një
# njoftim të sjellshëm — maksimumi një herë në ditë kalendarike
# (ora e Tiranës) për klient.
# ================================================================
def is_work_time(at: datetime = None) -> bool:
    """A është 'at' (parazgjedhje: tani, Europe/Tirane) brenda orarit
    të punës? E hënë–e premte (fundjava vetëm nëse është hapur),
    work_start <= ora < work_end."""
    at = at or datetime.now(TIRANA)
    if at.tzinfo is None:
        at = at.replace(tzinfo=TIRANA)
    at = at.astimezone(TIRANA)
    ws = store.get_work_settings()
    if at.weekday() >= 5 and not ws.get("weekend"):
        return False
    return ws["start"] <= at.strftime("%H:%M") < ws["end"]


async def _maybe_after_hours(context, user, lang: str):
    """Pas përcjelljes së mesazhit të klientit: nëse jemi jashtë
    orarit, dërgo njoftimin 'after_hours' (maks. 1/ditë për klient).
    Dështimet kapen në heshtje — relay s'prishet kurrë prej tij."""
    try:
        if is_work_time():
            return
        today = datetime.now(TIRANA).date().isoformat()
        if store.get_after_hours_day(user.id) == today:
            return
        store.set_after_hours_day(user.id, today)
        await context.bot.send_message(
            user.id, t(lang, "after_hours"), parse_mode="HTML")
    except Exception as e:
        log.warning("njoftimi jashtë orarit dështoi: %s", e)


def _work_schedule_text() -> str:
    ws = store.get_work_settings()
    return (f"{ws['start']}–{ws['end']}, fundjava "
            f"{'e hapur' if ws['weekend'] else 'e mbyllur'}")


async def adm_work_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/orari HH:MM-HH:MM — vendos orarin e punës (validim i plotë).
    Pa argumente: tregon orarin aktual."""
    if not is_admin(update.effective_user):
        return
    arg = " ".join(context.args or []).strip()
    if not arg:
        await update.message.reply_text(
            "🕘 <b>Orari aktual i punës</b>: " + _work_schedule_text()
            + "\n\nNdryshoje me /orari &lt;HH:MM-HH:MM&gt; "
              "(p.sh. /orari 09:00-18:00).", parse_mode="HTML")
        return
    m = re.fullmatch(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", arg)
    ok = False
    if m:
        h1, m1, h2, m2 = (int(x) for x in m.groups())
        ok = (0 <= h1 <= 23 and 0 <= h2 <= 23 and 0 <= m1 <= 59
              and 0 <= m2 <= 59 and (h1, m1) < (h2, m2))
    if not ok:
        await update.message.reply_text(
            "⚠️ Format i gabuar. Përdor /orari <HH:MM-HH:MM> me orë të "
            "vlefshme dhe fillimin para fundit (p.sh. /orari 09:00-18:00).")
        return
    store.set_work_hours(f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}")
    await update.message.reply_text(
        "🕘 <b>Orari i punës u përditësua</b>: " + _work_schedule_text()
        + "\nJashtë këtij orari, klientët marrin përgjigjen automatike "
          "(maksimumi një herë në ditë).", parse_mode="HTML")


async def adm_work_weekend(update: Update,
                           context: ContextTypes.DEFAULT_TYPE):
    """/orari_fundjave on|off — e shtuna/e diela si ditë pune ose jo."""
    if not is_admin(update.effective_user):
        return
    arg = (context.args or [""])[0].strip().lower()
    if arg not in ("on", "off"):
        await update.message.reply_text(
            "Përdorimi: /orari_fundjave on|off — orari aktual: "
            + _work_schedule_text())
        return
    store.set_work_weekend(arg == "on")
    await update.message.reply_text(
        "🕘 <b>Orari i punës</b>: " + _work_schedule_text(),
        parse_mode="HTML")


async def adm_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        return
    uid, _ = _parse_uid_arg(context)
    if uid is None:
        await update.message.reply_text("Përdorimi: /revoko <user_id> (merr ID-në nga /klientet)")
        return
    if store.revoke_client(uid):
        await update.message.reply_text(f"🚫 Aksesi i klientit {uid} u revokua (edhe kodi i tij).")
        try:
            await context.bot.send_message(
                uid, "🔒 Aksesi yt në portalin e klientëve përfundoi. "
                     "Për çdo gjë, kontakto Erionin në Instagram: @erjonixx")
        except Exception:
            pass
    else:
        await update.message.reply_text("Ky user_id nuk u gjet te klientët.")


async def adm_extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        return
    uid, rest = _parse_uid_arg(context)
    days = 30
    if uid is None or (rest and not _UID_ARG.fullmatch(rest[0] or "")):
        await update.message.reply_text("Përdorimi: /zgjat <user_id> [ditë]")
        return
    if rest:
        days = int(rest[0])
        if days < 1:
            await update.message.reply_text("Përdorimi: /zgjat <user_id> [ditë]")
            return
    if store.extend_client(uid, days):
        rec = store.get_client_any(uid)
        await update.message.reply_text(
            f"✅ Aksesi i {uid} u zgjat me {days} ditë — tani skadon {fmt_date(rec['expires_at'])}.")
    else:
        await update.message.reply_text("Ky user_id nuk u gjet te klientët.")


# ---------------------------------------------------------------- ndërtimi
def build_app():
    if not TOKEN:
        raise SystemExit("Mungon CLIENT_BOT_TOKEN — vendose në .env / variabël ambienti.")
    req = HTTPXRequest(connect_timeout=25.0, read_timeout=40.0,
                       write_timeout=40.0, pool_timeout=10.0,
                       httpx_kwargs=_HTTPX_KWARGS)
    app = Application.builder().token(TOKEN).request(req).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("panel", cmd_start))
    app.add_handler(CommandHandler("akses", show_access))
    app.add_handler(CommandHandler("ndalo", talk_stop))
    app.add_handler(CommandHandler("anulo", cancel_conv))
    # komandat e adminit
    app.add_handler(CommandHandler("krijo_kod", adm_create_code))
    app.add_handler(CommandHandler("kodet", adm_codes))
    app.add_handler(CommandHandler("klientet", adm_clients))
    app.add_handler(CommandHandler("revoko", adm_revoke))
    app.add_handler(CommandHandler("zgjat", adm_extend))
    app.add_handler(CommandHandler("backup", adm_backup))
    app.add_handler(CommandHandler("statusi", adm_status))
    app.add_handler(CommandHandler("projekt", adm_project))
    app.add_handler(CommandHandler("faza", adm_project_stage))
    app.add_handler(CommandHandler("shenim_projekti", adm_project_note))
    app.add_handler(CommandHandler("projekt_fund", adm_project_finish))
    app.add_handler(CommandHandler("slot", adm_slot))
    app.add_handler(CommandHandler("slotet", adm_slots))
    app.add_handler(CommandHandler("slot_fshi", adm_slot_delete))
    app.add_handler(CommandHandler("njoftim", adm_broadcast))
    app.add_handler(CommandHandler("pergjigju", adm_pergjigju))
    app.add_handler(CommandHandler("vleresime", adm_reviews))      # paketa 1–6 (F1)
    app.add_handler(CommandHandler("mireseardhje", adm_voice_set))  # F5
    app.add_handler(CommandHandler("hiq_mireseardhjen", adm_voice_clear))
    app.add_handler(CommandHandler("raport", adm_report))           # F6
    app.add_handler(CommandHandler("marreveshje", adm_agreement))   # paketa 3
    app.add_handler(CommandHandler("orari", adm_work_hours))        # paketa 3
    app.add_handler(CommandHandler("orari_fundjave", adm_work_weekend))
    app.add_handler(CommandHandler("dosja", adm_dossier))           # paketa 4
    app.add_handler(CommandHandler("shenim_klienti", adm_client_note))
    # callback-et (secili me prefiksin e vet, pa konflikte)
    app.add_handler(CallbackQueryHandler(lang_cb, pattern=r"^lang:(sq|en)$"))
    app.add_handler(CallbackQueryHandler(gate_code_cb, pattern=r"^gate:code$"))
    app.add_handler(CallbackQueryHandler(gate_req_cb, pattern=r"^gate:req$"))
    app.add_handler(CallbackQueryHandler(review_stars_cb, pattern=r"^rev:s:"))
    app.add_handler(CallbackQueryHandler(review_skip_cb, pattern=r"^rev:skip:"))
    app.add_handler(CallbackQueryHandler(review_tskip_cb, pattern=r"^rev:tskip$"))
    app.add_handler(CallbackQueryHandler(review_admin_cb, pattern=r"^revadm:"))
    app.add_handler(CallbackQueryHandler(req_service_cb, pattern=r"^svc:"))
    app.add_handler(CallbackQueryHandler(req_contact_skip, pattern=r"^req:nocontact$"))
    app.add_handler(CallbackQueryHandler(admin_decision_cb, pattern=r"^adm:(ok|no):[0-9a-f]+$"))
    app.add_handler(CallbackQueryHandler(service_detail_cb, pattern=r"^det:"))
    app.add_handler(CallbackQueryHandler(works_cb, pattern=r"^works:"))
    app.add_handler(CallbackQueryHandler(brief_start_cb, pattern=r"^cli:brief$"))
    app.add_handler(CallbackQueryHandler(brief_service_cb, pattern=r"^briefsvc:"))
    app.add_handler(CallbackQueryHandler(brief_budget_cb, pattern=r"^briefbud:\d+$"))
    app.add_handler(CallbackQueryHandler(card_image_cb, pattern=r"^cli:cardimg$"))
    app.add_handler(CallbackQueryHandler(book_service_cb, pattern=r"^booksvc:"))
    app.add_handler(CallbackQueryHandler(book_slot_cb, pattern=r"^bookslot:"))
    app.add_handler(CallbackQueryHandler(booking_decision_cb, pattern=r"^bookadm:(ok|no):[0-9a-f]+$"))
    app.add_handler(CallbackQueryHandler(agreement_cb, pattern=r"^agr:(accept|decline)(:[0-9a-f]+)?$"))
    # paketa 4: anulimi i rezervimit nga klienti, veprimet një-prekje
    # mbi brief-in dhe hapat e turit udhëzues
    app.add_handler(CallbackQueryHandler(booking_cancel_cb, pattern=r"^book:cancel:[0-9a-f]+$"))
    app.add_handler(CallbackQueryHandler(brief_action_cb, pattern=r"^brief:(proj|agr|reply):[0-9a-f]+$"))
    app.add_handler(CallbackQueryHandler(tour_cb, pattern=r"^tour:"))
    # i gjithë teksti kalon nga dispatch-i qendror (rrjedha/menu/relay/kyçje)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))
    # mediat (foto/zë/dokumente...) kalojnë nga dispatch-i mediatik (F6)
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & ~filters.TEXT, media_dispatch))
    # detyra në sfond: kujtesat e konsultave + skadimet e aksesit (F2/F3)
    app.post_init = post_init

    log.info("EN Private Clients Bot u ndez (admin %s).", ADMIN_ID)
    return app


def main():
    # Përdorim i pavarur: polling (zhvillim lokal / shërbim më vete).
    # Në Botkeep integrohet si bot i tretë në supervisor-in e telegram-bots
    # (build_app() thirret prej tij me webhook /wh/enclient).
    app = build_app()
    app.run_polling(bootstrap_retries=100, poll_interval=2.0)


if __name__ == "__main__":
    main()
