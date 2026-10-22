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
vlerësime, CV-ja si dokument, formulari i projektit (brief), bisedë
direkte me Erionin (relay dykahësh), kartvizita, /akses. E GJITHA kjo
mbetet në zonën private — vizitori i kyçur sheh vetëm ekranin e derës.

Komandat e adminit (vetëm ADMIN_ID):
  /krijo_kod [ditë] [shënim]   /kodet   /klientet
  /revoko <user_id>            /zgjat <user_id> [ditë]   /panel
  /backup                      (vetëm admin; NUK është në menunë publike)
  /statusi [teksti]            (statusi i disponueshmërisë për klientët)

Sekretet VETËM nga ambienti / .env (kurë në kod):
  CLIENT_BOT_TOKEN  — token-i nga @BotFather (i detyrueshëm)
  ADMIN_ID          — ID-ja numerike e Erionit (default: 1318275745)
  ENCLIENT_DATA     — rruga e data.json (opsionale)
"""
import logging
import os
import sys
from datetime import datetime, timezone

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

from store import Store, normalize_code, parse_iso

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

# Rrjedhat shumë-hapëshe mbahen në user_data["flow"] = {"kind": ..., "step": ...}
# dhe drejtohen nga dispatch-i i tekstit/callback-eve (pa ConversationHandler:
# më e thjeshtë, pa paralajmërime PTB dhe plotësisht e testueshme lokalisht).

CLIENT_KB = ReplyKeyboardMarkup(
    [["💼 Shërbimet", "🗂 Shembuj pune"],
     ["📝 Nis një projekt", "💬 Fol me Erionin"],
     ["❓ FAQ", "🎴 Kartvizita ime"],
     ["📄 CV-ja ime", "🔐 Aksesi im"]],
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
            "/statusi [teksti] — statusi i disponueshmërisë që shohin klientët",
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
        [InlineKeyboardButton("🎴 Kartvizita dixhitale", url="https://erionnezha.github.io/erionxx-business-card/")],
        [InlineKeyboardButton("🌐 Portfolio", url="https://erionxx1.netlify.app")],
        [InlineKeyboardButton("💼 LinkedIn", url="https://www.linkedin.com/in/erion-nezha")],
        [InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/erjonixx/")],
    ])
    await update.effective_message.reply_text(
        "🎴 <b>Erion Nezha</b> — Software Developer\nTiranë, Shqipëri\n\n"
        "Ruaji kontaktet e mia:",
        parse_mode="HTML", reply_markup=kb)


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
        f"📞 Kontakti: {d.get('contact', '—')}")
    store.bump_today(user.id, "briefs")
    await update.message.reply_text(
        "✅ <b>Brief-i u dërgua!</b>\n\nErioni e lexon dhe të përgjigjet këtu "
        "me hapat e radhës dhe preventivin. Faleminderit për besimin!",
        parse_mode="HTML", reply_markup=CLIENT_KB)
    context.user_data.pop("brief", None)
    context.user_data.pop("flow", None)


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


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admini i përgjigjet mesazhit të përcjellë → relay te klienti."""
    msg = update.message
    if not msg or not msg.reply_to_message:
        return False
    target = store.relay_target(msg.reply_to_message.message_id)
    if not target:
        return False
    try:
        await context.bot.send_message(
            target, f"💬 <b>Erioni:</b>\n{msg.text or ''}", parse_mode="HTML")
        await msg.reply_text("✔️ U dërgua te klienti.")
    except Exception as e:
        await msg.reply_text(f"⚠️ Dërgimi dështoi: {e}")
    return True


MENU_DISPATCH = {
    "💼 Shërbimet": "services",
    "🗂 Shembuj pune": "works",
    "🎴 Kartvizita ime": "card",
    "🎴 Kartvizita": "card",
    "🔐 Aksesi im": "access",
    "💬 Fol me Erionin": "talk",
    "📝 Nis një projekt": "brief",
    "❓ FAQ": "faq",
    "📄 CV-ja ime": "cv",
}


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatch-i qendror i tekstit: rrjedhat aktive → menuja → relay → kyçja."""
    user = update.effective_user
    text = (update.message.text or "").strip()
    if is_admin(user):
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
    # i gjithë teksti kalon nga dispatch-i qendror (rrjedha/menu/relay/kyçje)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

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
