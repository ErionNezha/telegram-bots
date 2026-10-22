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

Sekretet VETËM nga ambienti / .env (kurë në kod):
  CLIENT_BOT_TOKEN  — token-i nga @BotFather (i detyrueshëm)
  ADMIN_ID          — ID-ja numerike e Erionit (default: 1318275745)
  ENCLIENT_DATA     — rruga e data.json (opsionale)
"""
import asyncio
import logging
import os
import sys
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
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
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
        ("🛍 KlikoBli — dyqani online", "https://klikobli.netlify.app"),
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
REVIEWS_TEXT = (
    "⭐ <b>Vlerësime nga përdorues realë</b>\n\n"
    "⭐⭐⭐⭐⭐\n"
    "Dizajn shumë i pëlqyer dhe navigim i lehtë nëpër aplikacion.\n"
    "<i>— vlerësim në Google Play (ERION TV)</i>\n\n"
    "⭐⭐⭐⭐⭐\n"
    "Kanale të shumta dhe funksionim i qëndrueshëm, pa ndërprerje.\n"
    "<i>— vlerësim në Google Play (ERION TV)</i>"
)

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

# Emrat shqip të ditëve/muajve për shfaqjen e orareve të konsultave.
AL_WEEKDAYS = ["e hënë", "e martë", "e mërkurë", "e enjte",
               "e premte", "e shtunë", "e diel"]
AL_MONTHS = ["janar", "shkurt", "mars", "prill", "maj", "qershor",
             "korrik", "gusht", "shtator", "tetor", "nëntor", "dhjetor"]


def fmt_slot(dt) -> str:
    """'e premte, 24 tetor — 18:00' (data/ora = të dhëna funksionale)."""
    if dt is None:
        return "—"
    return (f"{AL_WEEKDAYS[dt.weekday()]}, {dt.day} "
            f"{AL_MONTHS[dt.month - 1]} — {dt:%H:%M}")

# Rrjedhat shumë-hapëshe mbahen në user_data["flow"] = {"kind": ..., "step": ...}
# dhe drejtohen nga dispatch-i i tekstit/callback-eve (pa ConversationHandler:
# më e thjeshtë, pa paralajmërime PTB dhe plotësisht e testueshme lokalisht).

CLIENT_KB = ReplyKeyboardMarkup(
    [["💼 Shërbimet", "🗂 Shembuj pune"],
     ["📝 Nis një projekt", "🚧 Projekti im"],
     ["💬 Fol me Erionin", "🗓 Rezervo konsultë"],
     ["❓ FAQ", "📄 CV-ja ime"],
     ["🎴 Kartvizita ime", "🔐 Aksesi im"]],
    resize_keyboard=True,
)

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


def lock_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Kam kod aksesi", callback_data="gate:code")],
        [InlineKeyboardButton("📝 Kërkoj shërbim", callback_data="gate:req")],
    ])


async def show_lock(update: Update, context: ContextTypes.DEFAULT_TYPE, note: str = ""):
    text = (note + "\n\n" + LOCK_TEXT) if note else LOCK_TEXT
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text, parse_mode="HTML", reply_markup=lock_kb())
    else:
        await update.effective_message.reply_text(
            text, parse_mode="HTML", reply_markup=lock_kb())


async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = (user.first_name or "klient").strip()
    msg = update.effective_message
    await msg.reply_text(
        WELCOME_CLIENT.format(name=name, status=store.get_status()),
        parse_mode="HTML", reply_markup=CLIENT_KB)
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
            "/pergjigju &lt;user_id&gt; — mesazhi yt tjetër i shkon atij klienti",
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


# ---------------------------------------------------------------- /start
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.pop("talk", None)
    context.user_data.pop("reply_to", None)
    context.user_data.pop("flow", None)
    # Deep-link nga bio/DM: t.me/<bot>?start=EN-XXXX-XXXX → zhbllokim direkt
    if context.args and not has_access(user):
        code = (context.args[0] or "").strip()
        if normalize_code(code).startswith("EN"):
            await try_redeem(update, context, code)
            return
    if has_access(user):
        await show_home(update, context)
    else:
        await show_lock(update, context)


# ---------------------------------------------------------------- kodi
async def gate_code_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if has_access(q.from_user):
        await show_home(update, context)
        return
    if store.is_locked(q.from_user.id):
        await q.message.reply_text(
            "⏳ Llogaria jote është e kyçur përkohësisht nga tentativat e "
            "gabura. Provo më vonë.")
        return
    context.user_data["flow"] = {"kind": "code"}
    await q.message.reply_text(
        "🔑 Shkruaj kodin tënd të aksesit (formati: <code>EN-XXXX-XXXX</code>):",
        parse_mode="HTML")


async def try_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    user = update.effective_user
    if store.is_locked(user.id):
        await update.effective_message.reply_text(
            "⏳ Llogaria jote është e kyçur përkohësisht. Provo më vonë.")
        return
    status, rec = store.redeem_code(code, user.id)
    if status == "ok":
        store.clear_fails(user.id)
        store.activate_client(user.id, user.first_name or "", user.username or "",
                              "", DEFAULT_DAYS, via="code",
                              expires_at=parse_iso(rec["expires_at"]))
        await update.effective_message.reply_text(
            "✅ <b>Kodi u pranua.</b> Aksesi yt është aktiv deri më "
            f"<b>{fmt_date(rec['expires_at'])}</b>.", parse_mode="HTML")
        await notify_admin(context,
                           f"🔓 <b>Klient i ri u zhbllokua me kod</b>\n"
                           f"👤 {user.first_name or ''} (@{user.username or '—'}, id {user.id})\n"
                           f"📝 Shënimi i kodit: {rec.get('note') or '—'}")
        await show_home(update, context)
    else:
        await _gate_fail(update, context, status)


async def _gate_fail(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str):
    """Dështim te dera: vizitori sheh VETËM mesazhin gjenerik (Fiks 3);
    arsyeja e saktë ruhet dhe i raportohet vetëm adminit."""
    user = update.effective_user
    who = f"{user.first_name or ''} (@{user.username or '—'}, id {user.id})"
    locked = store.register_fail(user.id, status=status)
    await update.effective_message.reply_text(GATE_FAIL_TEXT, parse_mode="HTML")
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
        await update.effective_message.reply_text(
            "🔒 Shumë tentativa të gabuara — llogaria u kyç për një orë.")
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
    await update.message.reply_text(
        "Shkruaj sërish kodin, ose /anulo për t'u kthyer.")


# ---------------------------------------------------------------- kërkesa për shërbim
def service_kb(prefix: str):
    rows = [[InlineKeyboardButton(label, callback_data=f"{prefix}:{sid}")]
            for sid, label in SERVICES]
    return InlineKeyboardMarkup(rows)


async def gate_req_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if has_access(q.from_user):
        await show_home(update, context)
        return
    block = store.request_block(q.from_user.id)  # anti-spam (Fiks 2)
    if block == "pending":
        await q.message.reply_text(REQ_PENDING_TEXT, parse_mode="HTML")
        return
    if block == "daily":
        await q.message.reply_text(REQ_DAILY_TEXT, parse_mode="HTML")
        return
    context.user_data["flow"] = {"kind": "req", "step": "service"}
    context.user_data["req"] = {}
    await q.message.reply_text(
        "📝 <b>Kërkesë për shërbim</b>\n\nÇfarë shërbimi kërkon?",
        parse_mode="HTML", reply_markup=service_kb("svc"))


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
        "Si e ke <b>emrin</b> (emër mbiemër)?", parse_mode="HTML")


async def req_text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = context.user_data["flow"]
    step = flow.get("step")
    text = (update.message.text or "").strip()
    if step == "name":
        context.user_data["req"]["name"] = text
        flow["step"] = "desc"
        await update.message.reply_text(
            "Përshkruaje shkurtimisht <b>çfarë të duhet</b>:",
            parse_mode="HTML")
    elif step == "desc":
        context.user_data["req"]["desc"] = text
        flow["step"] = "contact"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            "⏭ Kapërce", callback_data="req:nocontact")]])
        await update.message.reply_text(
            "Një <b>kontakt</b> ku mund të të shkruaj Erioni "
            "(numër telefoni ose email). Mund ta kapërcesh — biseda vazhdon këtu.",
            parse_mode="HTML", reply_markup=kb)
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
    d = context.user_data.get("req", {})
    block = store.request_block(user.id)  # kontroll i dytë, në krijim (Fiks 2)
    if block:
        await update.effective_message.reply_text(
            REQ_PENDING_TEXT if block == "pending" else REQ_DAILY_TEXT,
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
        f"👤 {d.get('name') or user.first_name or ''} (@{user.username or '—'}, id {user.id})\n"
        f"💼 Shërbimi: {d.get('service', '—')}\n"
        f"📝 Nevoja: {d.get('desc', '—')}\n"
        f"📞 Kontakti: {d.get('contact') or '—'}",
        markup=kb)
    await update.effective_message.reply_text(
        "✅ <b>Kërkesa jote u dërgua.</b>\n\n"
        "Erioni e shqyrton personalisht. Kur të miratohet, boti hapet "
        "automatikisht për ty dhe merr njoftim këtu.\n\n"
        "Përgjigjja zakonisht vjen brenda ditës.",
        parse_mode="HTML")
    context.user_data.pop("req", None)
    context.user_data.pop("flow", None)


# ---------------------------------------------------------------- vendimet e adminit
async def admin_decision_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user):
        await q.answer("Vetëm admini.", show_alert=True)
        return
    _, action, req_id = q.data.split(":", 2)
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
    try:
        await context.bot.send_message(
            req["user_id"],
            "🎉 <b>Kërkesa jote u MIRATUA!</b>\n\n"
            f"Portali yt privat është aktiv deri më <b>{fmt_date(client['expires_at'])}</b>.\n\n"
            + WELCOME_CLIENT.format(name=(req["name"] or "klient").split()[0],
                                    status=store.get_status()),
            parse_mode="HTML", reply_markup=CLIENT_KB)
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
    await show_lock(update, None, "🔒 Së pari nevojitet kodi i aksesit.")
    return False


async def show_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    await update.effective_message.reply_text(
        "💼 <b>Shërbimet</b> — zgjidh për detaje:",
        parse_mode="HTML", reply_markup=service_kb("det"))


async def service_detail_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not has_access(q.from_user):
        await q.answer("Aksesi është i kyçur.", show_alert=True)
        return
    await q.answer()
    sid = q.data.split(":", 1)[1]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        "📝 Nis projekt të këtij lloji", callback_data="cli:brief")]])
    await q.message.reply_text(SERVICE_DETAILS.get(sid, ""), parse_mode="HTML",
                               reply_markup=kb)


def works_categories_kb():
    rows = [[InlineKeyboardButton(label, callback_data=f"works:{cid}")]
            for cid, label in WORK_CATEGORIES]
    rows.append([InlineKeyboardButton("⭐ Vlerësime", callback_data="works:reviews")])
    return InlineKeyboardMarkup(rows)


def works_category_kb(cid):
    rows = [[InlineKeyboardButton(t, url=u)] for t, u in WORKS[cid]]
    rows.append([InlineKeyboardButton("⬅ Kthehu", callback_data="works:cat")])
    return InlineKeyboardMarkup(rows)


async def show_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    await update.effective_message.reply_text(
        WORKS_HEADER, parse_mode="HTML", reply_markup=works_categories_kb())


async def works_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback-et e shembujve të punës: kategori / vlerësime / mbrapa.
    Vetëm klientë të zhbllokuar — vizitori merr vetëm sinjalin e kyçjes."""
    q = update.callback_query
    if not has_access(q.from_user):
        await q.answer("Aksesi është i kyçur.", show_alert=True)
        return
    await q.answer()
    data = (q.data or "").split(":", 1)[1] if ":" in (q.data or "") else "cat"
    if data == "reviews":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            "⬅ Kthehu", callback_data="works:cat")]])
        await q.message.reply_text(REVIEWS_TEXT, parse_mode="HTML",
                                   reply_markup=kb)
    elif data in WORKS:
        title = dict(WORK_CATEGORIES)[data]
        await q.message.reply_text(
            f"🗂 <b>{title}</b> — projekte live:",
            parse_mode="HTML", reply_markup=works_category_kb(data))
    else:  # "cat" → kthehu te kategoritë
        await q.message.reply_text(
            WORKS_HEADER, parse_mode="HTML", reply_markup=works_categories_kb())


async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    await update.effective_message.reply_text(FAQ_TEXT, parse_mode="HTML")


async def show_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📄 CV-ja ime: dërgon PDF-në e paketuar (assets/CV-Erion-Nezha.pdf).
    Vetëm klientë — vizitori s'merr as dokumentin, as përmbajtjen."""
    if not await guard_client(update):
        return
    if not os.path.isfile(CV_PATH):
        await update.effective_message.reply_text(
            "📄 CV-ja për momentin s'është e disponueshme këtu — kërkoja "
            "Erionit me 💬 <b>Fol me Erionin</b>.", parse_mode="HTML")
        return
    try:
        with open(CV_PATH, "rb") as f:
            await context.bot.send_document(
                update.effective_user.id, document=f,
                filename="CV-Erion-Nezha.pdf", caption=CV_CAPTION)
    except Exception as e:
        log.warning("dërgimi i CV-së dështoi: %s", e)
        await update.effective_message.reply_text(
            "📄 CV-ja s'u dërgua dot tani — kërkoja Erionit me 💬 "
            "<b>Fol me Erionin</b>.", parse_mode="HTML")


async def show_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Karta si imazh", callback_data="cli:cardimg")],
        [InlineKeyboardButton("🎴 Kartvizita dixhitale", url="https://erionnezha.github.io/erionxx-business-card/")],
        [InlineKeyboardButton("🌐 Portfolio", url="https://erionxx1.netlify.app")],
        [InlineKeyboardButton("💼 LinkedIn", url="https://www.linkedin.com/in/erion-nezha")],
        [InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/erjonixx/")],
    ])
    await update.effective_message.reply_text(
        "🎴 <b>Erion Nezha</b> — Software Developer\nTiranë, Shqipëri\n\n"
        "Ruaji kontaktet e mia:",
        parse_mode="HTML", reply_markup=kb)


async def card_image_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🖼 Karta si imazh: dërgon assets/card.png (me QR te boti) si foto.
    Vetëm klientë; nëse file-i mungon, mesazh i sjellshëm (si te CV-ja)."""
    q = update.callback_query
    if not has_access(q.from_user):
        await q.answer("Aksesi është i kyçur.", show_alert=True)
        return
    await q.answer()
    if not os.path.isfile(CARD_PATH):
        await q.message.reply_text(
            "🖼 Karta si imazh për momentin s'është e disponueshme — "
            "përdor lidhjet e kartvizitës më sipër.")
        return
    try:
        with open(CARD_PATH, "rb") as f:
            await context.bot.send_photo(
                q.from_user.id, photo=f, caption=CARD_IMG_CAPTION)
    except Exception as e:
        log.warning("dërgimi i kartës si imazh dështoi: %s", e)
        await q.message.reply_text(
            "🖼 Karta s'u dërgua dot tani — përdor lidhjet e kartvizitës "
            "më sipër.")


async def show_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_admin(user):
        await update.effective_message.reply_text("🔐 Je admini — akses i pakufizuar.")
        return
    rec = store.get_client(user.id)
    if not rec:
        await show_lock(update, context)
        return
    exp = parse_iso(rec["expires_at"])
    days = max(0, (exp - datetime.now(timezone.utc)).days) if exp else "—"
    await update.effective_message.reply_text(
        "🔐 <b>Aksesi yt</b>\n\n"
        f"• Statusi: ✅ Aktiv\n"
        f"• Skadon më: <b>{fmt_date(rec['expires_at'])}</b> (edhe {days} ditë)\n"
        f"• Shërbimi: {rec.get('service') or '—'}\n\n"
        "Për zgjatje, shkruaj Erionit me 💬 <b>Fol me Erionin</b>.",
        parse_mode="HTML")


# ---------------------------------------------------------------- brief-i i projektit
async def brief_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not has_access(q.from_user):
        await q.answer("Aksesi është i kyçur.", show_alert=True)
        return
    await q.answer()
    if store.brief_block(q.from_user.id):  # anti-spam (Fiks 2)
        await q.message.reply_text(BRIEF_DAILY_TEXT, parse_mode="HTML")
        return
    context.user_data["flow"] = {"kind": "brief", "step": "service"}
    context.user_data["brief"] = {}
    await q.message.reply_text(
        "📝 <b>Projekt i ri</b>\n\nÇfarë lloj projekti është?",
        parse_mode="HTML", reply_markup=service_kb("briefsvc"))


async def brief_menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_client(update):
        return
    if store.brief_block(update.effective_user.id):  # anti-spam (Fiks 2)
        await update.effective_message.reply_text(BRIEF_DAILY_TEXT, parse_mode="HTML")
        return
    context.user_data["flow"] = {"kind": "brief", "step": "service"}
    context.user_data["brief"] = {}
    await update.effective_message.reply_text(
        "📝 <b>Projekt i ri</b>\n\nÇfarë lloj projekti është?",
        parse_mode="HTML", reply_markup=service_kb("briefsvc"))


async def brief_service_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    flow = context.user_data.get("flow") or {}
    if flow.get("kind") != "brief":
        return
    sid = q.data.split(":", 1)[1]
    context.user_data.setdefault("brief", {})["service"] = SERVICE_NAMES.get(sid, sid)
    flow["step"] = "desc"
    await q.message.reply_text(
        "Përshkruaje projektin: çfarë duhet të bëjë, për kë është, "
        "çfarë faqesh/funksionesh mendon?", parse_mode="HTML")


async def brief_text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = context.user_data["flow"]
    step = flow.get("step")
    text = (update.message.text or "").strip()
    if step == "desc":
        context.user_data["brief"]["desc"] = text
        flow["step"] = "budget"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(b, callback_data=f"briefbud:{i}")]
                                    for i, b in enumerate(BUDGETS)])
        await update.message.reply_text(
            "Buxheti i përafërt?", reply_markup=kb)
    elif step == "deadline":
        context.user_data["brief"]["deadline"] = text
        flow["step"] = "contact"
        await update.message.reply_text(
            "Kontakti yt (telefon ose email):")
    elif step == "contact":
        context.user_data["brief"]["contact"] = text
        await brief_finish(update, context)


async def brief_budget_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    flow = context.user_data.get("flow") or {}
    if flow.get("kind") != "brief":
        return
    idx = int(q.data.split(":", 1)[1])
    context.user_data.setdefault("brief", {})["budget"] = BUDGETS[idx]
    flow["step"] = "deadline"
    await q.message.reply_text(
        "Kur të duhet gati? (p.sh. brenda muajit / kam një datë)")


async def brief_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    d = context.user_data.get("brief", {})
    if store.brief_block(user.id):  # kontroll përfundimtar (Fiks 2)
        await update.message.reply_text(BRIEF_DAILY_TEXT, parse_mode="HTML")
        context.user_data.pop("brief", None)
        context.user_data.pop("flow", None)
        return
    await notify_admin(
        context,
        "🚀 <b>BRIEF I RI PROJEKTI</b>\n"
        f"👤 {user.first_name or ''} (@{user.username or '—'}, id {user.id})\n"
        f"💼 Lloji: {d.get('service', '—')}\n"
        f"📝 Përshkrimi: {d.get('desc', '—')}\n"
        f"💰 Buxheti: {d.get('budget', '—')}\n"
        f"⏰ Afati: {d.get('deadline', '—')}\n"
        f"📞 Kontakti: {d.get('contact', '—')}\n\n"
        f"💡 <b>Gjurmim:</b> për ta ndjekur projektin te klienti, kopjo: "
        f"<code>/projekt {user.id} Titulli i projektit</code>")
    store.bump_today(user.id, "briefs")
    await update.message.reply_text(
        "✅ <b>Brief-i u dërgua!</b>\n\nErioni e lexon dhe të përgjigjet këtu "
        "me hapat e radhës dhe preventivin. Faleminderit për besimin!",
        parse_mode="HTML", reply_markup=CLIENT_KB)
    context.user_data.pop("brief", None)
    context.user_data.pop("flow", None)


# ---------------------------------------------------------------- F1: Projekti im
def project_view_text(rec) -> str:
    """Pamja e projektit për klientin: fazat me simbole + shiriti i
    progresit VETËM me simbole (✅/🔄/⚪ dhe ▰/▱) — kurrë përqindje
    apo numra fazash (urdhri 'mos vendos shifra')."""
    stage = int(rec.get("stage") or 0)
    done = bool(rec.get("done"))
    lines = [f"🚧 <b>{rec.get('title') or 'Projekt'}</b>"]
    for i, label in enumerate(PROJECT_STAGES):
        if done or i < stage:
            mark = "✅"
        elif i == stage:
            mark = "🔄"
        else:
            mark = "⚪"
        lines.append(f"{mark} {label}")
    filled = len(PROJECT_STAGES) if done else stage + 1
    lines.append("▰" * filled + "▱" * (len(PROJECT_STAGES) - filled))
    if rec.get("note"):
        lines.append(f"📝 <i>{rec['note']}</i>")
    lines.append(f"🕒 Përditësuar më: {fmt_date(rec.get('updated_at'))}")
    return "\n".join(lines)


async def show_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚧 Projekti im — vetëm klientë të zhbllokuar (portieri)."""
    if not await guard_client(update):
        return
    user = update.effective_user
    projects = store.list_projects(user.id) if not is_admin(user) else []
    active = [p for p in projects if not p.get("done")]
    finished = [p for p in projects if p.get("done")]
    ordered = active + finished
    if not ordered:
        await update.effective_message.reply_text(
            PROJECTS_EMPTY, parse_mode="HTML")
        return
    parts = [PROJECTS_HEADER] + [project_view_text(p) for p in ordered]
    await update.effective_message.reply_text(
        "\n\n".join(parts), parse_mode="HTML")


def _parse_uid_arg(context):
    """user_id nga args[0] (ose None nëse formati është gabim)."""
    args = context.args or []
    if not args or not args[0].lstrip("-").isdigit():
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
    try:
        await context.bot.send_message(
            uid,
            "🚧 <b>Përditësim projekti</b>\n\n" + project_view_text(rec),
            parse_mode="HTML")
    except Exception as e:
        log.warning("njoftimi i fazës s'u dërgua: %s", e)


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
    try:
        await context.bot.send_message(
            uid, CLIENT_FINISH_TEXT.format(title=rec.get("title") or "Projekt"),
            parse_mode="HTML")
    except Exception as e:
        log.warning("njoftimi i përfundimit s'u dërgua: %s", e)


# ---------------------------------------------------------------- F2: Rezervo konsultë
async def booking_menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🗓 Rezervo konsultë — pika e hyrjes nga menuja e klientit."""
    if not await guard_client(update):
        return
    user = update.effective_user
    if store.pending_booking_for(user.id):
        await update.effective_message.reply_text(
            BOOK_PENDING_TEXT, parse_mode="HTML")
        return
    context.user_data["flow"] = {"kind": "booking", "step": "service"}
    context.user_data["booking"] = {}
    await update.effective_message.reply_text(
        BOOK_START_TEXT, parse_mode="HTML", reply_markup=service_kb("booksvc"))


def _slot_rows(slots):
    return [[InlineKeyboardButton(fmt_slot(parse_iso(s["dt_iso"])),
                                  callback_data=f"bookslot:{s['id']}")]
            for s in slots]


async def book_service_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not has_access(q.from_user):
        await q.answer("Aksesi është i kyçur.", show_alert=True)
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
        await q.message.reply_text(BOOK_NO_SLOTS_TEXT, parse_mode="HTML")
        return
    flow["step"] = "slot"
    await q.message.reply_text(
        BOOK_PICK_SLOT_TEXT, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(_slot_rows(slots)))


async def book_slot_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not has_access(q.from_user):
        await q.answer("Aksesi është i kyçur.", show_alert=True)
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
        await q.message.reply_text(BOOK_PENDING_TEXT, parse_mode="HTML")
        return
    slot = store.get_slot(slot_id)
    if slot is None or slot.get("booked_by") is not None:
        slots = store.open_slots()
        context.user_data.pop("flow", None)
        context.user_data.pop("booking", None)
        if slots:
            context.user_data["flow"] = {"kind": "booking", "step": "slot"}
            context.user_data["booking"] = {"service_key": booking["service_key"]}
            await q.message.reply_text(
                BOOK_TAKEN_TEXT, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(_slot_rows(slots)))
        else:
            await q.message.reply_text(BOOK_NO_SLOTS_TEXT, parse_mode="HTML")
        return
    rec = store.create_booking(user.id, slot_id, booking["service_key"])
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Konfirmo", callback_data=f"bookadm:ok:{rec['id']}"),
        InlineKeyboardButton("❌ Refuzo", callback_data=f"bookadm:no:{rec['id']}"),
    ]])
    await notify_admin(
        context,
        "🗓 <b>KËRKESË E RE KONSULTE</b>\n"
        f"👤 {user.first_name or ''} (@{user.username or '—'}, id {user.id})\n"
        f"💼 Shërbimi: {SERVICE_NAMES.get(booking['service_key'], booking['service_key'])}\n"
        f"🗓 Orari: <b>{fmt_slot(parse_iso(slot['dt_iso']))}</b>",
        markup=kb)
    await q.message.reply_text(BOOK_SENT_TEXT, parse_mode="HTML")
    context.user_data.pop("flow", None)
    context.user_data.pop("booking", None)


async def booking_decision_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vendimi i adminit mbi kërkesën e konsultës (si te kërkesat)."""
    q = update.callback_query
    if not is_admin(q.from_user):
        await q.answer("Vetëm admini.", show_alert=True)
        return
    _, action, bid = q.data.split(":", 2)
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
    slot_label = fmt_slot(parse_iso(slot["dt_iso"])) if slot else "—"
    svc = SERVICE_NAMES.get(b["service_key"], b["service_key"])
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
                BOOK_REJECTED_TEXT.format(service=svc, slot=slot_label),
                parse_mode="HTML")
        except Exception as e:
            log.warning("refuzimi i konsultës s'u dërgua: %s", e)
        return
    store.set_booking_status(bid, "approved")
    try:
        await q.edit_message_text(
            q.message.text + "\n\n✅ <b>KONFIRMUAR</b>", parse_mode="HTML")
    except Exception:
        pass
    try:
        await context.bot.send_message(
            b["client_id"],
            BOOK_APPROVED_TEXT.format(service=svc, slot=slot_label),
            parse_mode="HTML")
    except Exception as e:
        log.warning("konfirmimi i konsultës s'u dërgua: %s", e)


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
            st = f"🔒 i rezervuar nga {c.get('name') or s['booked_by']}"
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
        slot_label = fmt_slot(dt)
        client = store.get_client_any(b["client_id"]) or {}
        actions.append({
            "kind": "booking_client", "chat_id": b["client_id"],
            "text": REMINDER_BOOKING_CLIENT.format(
                service=svc, slot=slot_label)})
        actions.append({
            "kind": "booking_admin", "chat_id": ADMIN_ID,
            "text": REMINDER_BOOKING_ADMIN.format(
                name=client.get("name") or "", username=client.get("username") or "—",
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
            "text": EXPIRY_CLIENT_TEXT.format(date=fmt_date(rec["expires_at"]))})
        store.mark_expiry_reminded(uid)
        reminded_names.append(
            f"{rec.get('name') or ''} (@{rec.get('username') or '—'}, id {uid})")
    if reminded_names:
        actions.append({
            "kind": "expiry_admin_summary", "chat_id": ADMIN_ID,
            "text": "⏰ <b>Kujtesë skadimi — klientët që u njoftuan</b>\n"
                    + "\n".join(f"• {n}" for n in reminded_names)
                    + "\n\nAfati i tyre skadon brenda pak ditësh — "
                      "zgjatje me /zgjat <user_id>."})
    return actions


async def _reminder_loop(app):
    """Detyra në sfond: çdo ~30 min dërgon kujtesat e planifikuara.
    Gabimet kapen gjithmonë — loop-i s'rrëzon kurrë aplikacionin."""
    while True:
        try:
            for act in plan_reminders(datetime.now(timezone.utc)):
                try:
                    await app.bot.send_message(
                        act["chat_id"], act["text"], parse_mode="HTML")
                except Exception as e:
                    log.warning("kujtesa (%s) s'u dërgua: %s",
                                act.get("kind"), e)
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
    await update.effective_message.reply_text(
        "💬 <b>Je në bisedë direkte me Erionin.</b>\n"
        "Shkruaj mesazhin tënd — i vjen atij menjëherë dhe përgjigjja të "
        "kthehet këtu.\nPër t'u kthyer te menuja: /ndalo",
        parse_mode="HTML")


async def talk_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("talk", None)
    if has_access(update.effective_user):
        await update.effective_message.reply_text("U ktheve te menuja 👇",
                                                  reply_markup=CLIENT_KB)


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
            target, f"💬 <b>Erioni:</b>\n{msg.text}", parse_mode="HTML")
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
        f"✍️ Po i përgjigjesh <b>{rec.get('name') or 'klientit'}</b> "
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
        if await admin_pergjigju_step(update, context):
            return
        await admin_reply(update, context)
        return
    flow = context.user_data.get("flow") or {}
    if flow.get("kind"):
        await msg.reply_text(
            "Kjo rrjedhë pret tekst — shkruaj përgjigjen, ose /anulo "
            "për t'u kthyer.")
        return
    if not has_access(user):
        await show_lock(update, context,
                        "🔒 Ky bot është privat. Hyrja bëhet vetëm me kod personal.")
        return
    if media_kind(msg) is None:
        return
    if context.user_data.get("talk"):
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"💬 <b>Mesazh nga klienti</b> {user.first_name or ''} "
                f"(@{user.username or '—'}, id {user.id}):",
                parse_mode="HTML")
            copied = await context.bot.copy_message(
                ADMIN_ID, from_chat_id=msg.chat_id,
                message_id=msg.message_id)
            store.map_relay(copied.message_id, user.id)
            await msg.reply_text("✔️ U dërgua te Erioni.")
        except Exception as e:
            log.warning("kopjimi i medias së klientit dështoi: %s", e)
            await msg.reply_text("⚠️ Dërgimi dështoi — provo sërish.")
    else:
        await msg.reply_text(
            "Për të dërguar foto, zë ose dokumente, aktivizo më parë "
            "💬 <b>Fol me Erionin</b> nga menuja.", parse_mode="HTML")


MENU_DISPATCH = {
    "💼 Shërbimet": "services",
    "🗂 Shembuj pune": "works",
    "🎴 Kartvizita ime": "card",
    "🎴 Kartvizita": "card",
    "🔐 Aksesi im": "access",
    "💬 Fol me Erionin": "talk",
    "📝 Nis një projekt": "brief",
    "🚧 Projekti im": "projects",
    "🗓 Rezervo konsultë": "booking",
    "❓ FAQ": "faq",
    "📄 CV-ja ime": "cv",
}


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatch-i qendror i tekstit: rrjedhat aktive → menuja → relay → kyçja."""
    user = update.effective_user
    text = (update.message.text or "").strip()
    if is_admin(user):
        if await admin_pergjigju_step(update, context):
            return
        await admin_reply(update, context)
        return
    flow = context.user_data.get("flow") or {}
    kind = flow.get("kind")
    if kind == "code":
        await code_text(update, context)
        return
    if kind == "req":
        await req_text_step(update, context)
        return
    if kind == "brief":
        await brief_text_step(update, context)
        return
    action = MENU_DISPATCH.get(text)
    if action == "services":
        await show_services(update, context)
        return
    if action == "works":
        await show_works(update, context)
        return
    if action == "card":
        await show_card(update, context)
        return
    if action == "access":
        await show_access(update, context)
        return
    if action == "talk":
        await talk_start(update, context)
        return
    if action == "brief":
        await brief_menu_start(update, context)
        return
    if action == "faq":
        await show_faq(update, context)
        return
    if action == "cv":
        await show_cv(update, context)
        return
    if action == "projects":
        await show_projects(update, context)
        return
    if action == "booking":
        await booking_menu_start(update, context)
        return
    if has_access(user):
        if context.user_data.get("talk"):
            sent = await context.bot.send_message(
                ADMIN_ID,
                f"💬 <b>Mesazh nga klienti</b> {user.first_name or ''} "
                f"(@{user.username or '—'}, id {user.id}):\n\n{update.message.text or ''}",
                parse_mode="HTML")
            store.map_relay(sent.message_id, user.id)
            await update.message.reply_text("✔️ Mesazhi u dërgua te Erioni.")
        else:
            await update.message.reply_text(
                "Zgjidh nga menuja më poshtë 👇", reply_markup=CLIENT_KB)
        return
    await show_lock(update, context,
                    "🔒 Ky bot është privat. Hyrja bëhet vetëm me kod personal.")


async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("req", None)
    context.user_data.pop("brief", None)
    context.user_data.pop("booking", None)
    context.user_data.pop("reply_to", None)
    context.user_data.pop("flow", None)
    if has_access(update.effective_user):
        await update.effective_message.reply_text("U anulua.",
                                                  reply_markup=CLIENT_KB)
    else:
        await show_lock(update, context)


# ---------------------------------------------------------------- komandat e adminit
async def adm_create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        return
    days, note = DEFAULT_DAYS, ""
    args = context.args or []
    if args:
        if args[0].isdigit():
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
    for _, r in sorted(rows, key=lambda x: x[1]["created_at"], reverse=True)[:20]:
        if r.get("revoked"):
            st = "🚫 revokuar"
        elif r.get("bound_user_id"):
            st = f"🔓 përdorur nga id {r['bound_user_id']}"
        else:
            st = "🟡 në pritje (i papërdorur)"
        lines.append(f"• {st} · skadon {fmt_date(r['expires_at'])} · {r.get('note') or '—'}")
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
        st = "🚫 revokuar" if r.get("revoked") else f"✅ deri {fmt_date(r['expires_at'])}"
        lines.append(f"• {r.get('name') or ''} (@{r.get('username') or '—'}, id <code>{uid}</code>) — "
                     f"{r.get('service') or '—'} · {st}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


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


async def adm_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        return
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.message.reply_text("Përdorimi: /revoko <user_id> (merr ID-në nga /klientet)")
        return
    uid = int(context.args[0])
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
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.message.reply_text("Përdorimi: /zgjat <user_id> [ditë]")
        return
    uid = int(context.args[0])
    days = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 30
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
    # callback-et (secili me prefiksin e vet, pa konflikte)
    app.add_handler(CallbackQueryHandler(gate_code_cb, pattern=r"^gate:code$"))
    app.add_handler(CallbackQueryHandler(gate_req_cb, pattern=r"^gate:req$"))
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
