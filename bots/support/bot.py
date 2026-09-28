#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created by Erion Nezha — © 2026 All rights reserved
"""
Lexo Libra — Bot Ndihme 🤝
Ndihmë për lexuesit: pyetje të shpeshta + raportim problemesh te administratori.

Sekretet merren VETËM nga variablat e ambientit:
  SUPPORT_BOT_TOKEN — token-i nga @BotFather (i detyrueshëm)
  ADMIN_ID          — ID-ja numerike e administratorit (për raportimet)
Kurrë mos shkruaj token-in në kod apo file.
"""
import logging
import os

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lexolibra-support")
logging.getLogger("httpx").setLevel(logging.WARNING)

# Fortësi ndaj ambientit: httpx thyhet me hyrje IPv6 si [::1] në no_proxy,
# dhe proxy-ja e daljes bën TLS-interception (duhet CA-ja e saj).
for _var in ("no_proxy", "NO_PROXY"):
    _val = os.environ.get(_var, "")
    if "[" in _val:
        os.environ[_var] = ",".join(p for p in _val.split(",") if "[" not in p)
_CA = os.environ.get("SSL_CERT_FILE", "")
_HTTPX_KWARGS = {"verify": _CA} if _CA and os.path.isfile(_CA) else {}

TOKEN = os.environ.get("SUPPORT_BOT_TOKEN", "").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or 0)

SITE_URL = "https://lexolibra.netlify.app/"
MAIN_BOT_URL = "https://t.me/lexolibra_bot"
APK_URL = "https://apk.e-droid.net/apk/app4198383-jf5ecq.apk?v=2"

# Pyetjet e shpeshta: (id, titull i shkurtër, përgjigjja)
FAQ = [
    ("shkarko",
     "⬇️ Si shkarkoj librin?",
     "Hap librin te faqja <b>lexolibra.netlify.app</b> (ose te @lexolibra_bot) "
     "dhe shtyp butonin <b>⬇️ Shkarko</b>. Libri shkarkohet si PDF — "
     "hape me çdo lexues PDF në telefon apo kompjuter."),
    ("hapet",
     "📖 Pse s'më hapet libri?",
     "Kontrollo këto me radhë:\n"
     "1️⃣ A ke internet të qëndrueshëm?\n"
     "2️⃣ A ke aplikacion për PDF (p.sh. Adobe Reader)?\n"
     "3️⃣ Nëse linku është MEGA, provo ta hapësh në browser ose me aplikacionin MEGA.\n"
     "Nëse s'punohet prapë, përdor 📩 <b>Raporto problem</b> dhe na thuaj titullin e librit."),
    ("audio",
     "🔊 Si dëgjoj përmbledhjen audio?",
     "Te çdo libër ka butonin <b>🔊 Dëgjo përmbledhjen</b> — "
     "shtype dhe dëgjon përmbledhjen me zë neural shqip. "
     "Duhet vetëm internet; nëse s'luhet, rifresko faqen dhe provo sërish."),
    ("aplikacioni",
     "📱 Ku e gjej aplikacionin Android?",
     "Aplikacionin <b>Lexo Libra</b> për Android e shkarkon këtu:\n"
     f"⬇️ <a href=\"{APK_URL}\">Shkarko APK</a>\n\n"
     "Pas shkarkimit, lejo instalimin nga burime të panjohura dhe instaloje."),
    ("mungon",
     "🔎 Si kërkoj një titull që mungon?",
     "Hap <b>@lexolibra_bot</b>, shtyp 📩 <b>Kërko një titull</b> dhe shkruaj "
     "titullin + autorin. Kërkesa shkon direkt te administratori dhe "
     "ti njoftohesh kur libri shtohet. 📚"),
]

ASK_REPORT = 1

MENU_KB = ReplyKeyboardMarkup(
    [["❓ Pyetje të shpeshta"], ["📩 Raporto problem"], ["📚 Hap Lexo Libra"]],
    resize_keyboard=True,
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Përshëndetje! Jam <b>ndihmësi i Lexo Libra</b>.\n\n"
        "Zgjidh nga menuja më poshtë:\n"
        "• ❓ <b>Pyetje të shpeshta</b> — përgjigje të gatshme\n"
        "• 📩 <b>Raporto problem</b> — na trego çfarë s'punon\n"
        "• 📚 <b>Hap Lexo Libra</b> — faqja dhe boti kryesor",
        parse_mode="HTML",
        reply_markup=MENU_KB,
    )


async def show_faq_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton(titulli, callback_data=f"faq:{fid}")]
          for fid, titulli, _ in FAQ]
    await update.message.reply_text(
        "❓ <b>Pyetjet më të shpeshta</b> — zgjidh një:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def on_faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    fid = q.data.split(":", 1)[1]
    for _fid, _titulli, pergjigjja in FAQ:
        if _fid == fid:
            kb = [[InlineKeyboardButton("⬅️ Kthehu te pyetjet",
                                        callback_data="faq:back")]]
            await q.edit_message_text(
                f"<b>{_titulli}</b>\n\n{pergjigjja}\n\n"
                "<i>S'te ndihmoi? Përdor 📩 Raporto problem.</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(kb),
                disable_web_page_preview=True,
            )
            return


async def on_faq_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [[InlineKeyboardButton(titulli, callback_data=f"faq:{fid}")]
          for fid, titulli, _ in FAQ]
    await q.edit_message_text(
        "❓ <b>Pyetjet më të shpeshta</b> — zgjidh një:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def show_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🌐 Faqja Lexo Libra", url=SITE_URL)],
        [InlineKeyboardButton("🤖 Boti kryesor @lexolibra_bot", url=MAIN_BOT_URL)],
        [InlineKeyboardButton("📱 Shkarko aplikacionin Android", url=APK_URL)],
    ]
    await update.message.reply_text(
        "📚 <b>Lexo Libra</b> — zgjidh ku do të shkosh:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📩 <b>Raporto problem</b>\n\n"
        "Shkruaj me pak fjalë çfarë nuk punon (p.sh. titullin e librit + "
        "çfarë ndodh). Mesazhi yt shkon direkt te administratori.\n\n"
        "Shkruaj /anulo për të dalë.",
        parse_mode="HTML",
    )
    return ASK_REPORT


async def report_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    teksti = (update.message.text or "").strip()
    if not teksti:
        await update.message.reply_text("Shkruaj diçka, të lutem, ose /anulo.")
        return ASK_REPORT

    emri = user.full_name
    uname = f"@{user.username}" if user.username else "(pa username)"
    raporti = (
        "📩 <b>Raportim i ri problemi</b>\n\n"
        f"👤 {emri} {uname} (id: <code>{user.id}</code>)\n\n"
        f"📝 {teksti}"
    )
    if ADMIN_ID:
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=raporti,
                                           parse_mode="HTML")
            await update.message.reply_text(
                "✅ Faleminderit! Raportimi yt iu dërgua administratorit. "
                "Do të të kontaktojmë nëse na duhet më shumë info. 🤝",
                reply_markup=MENU_KB,
            )
        except Exception as e:
            log.warning("Dërgimi te admini dështoi: %s", type(e).__name__)
            await update.message.reply_text(
                "😕 S'munda ta dërgoj raportimin tani. Provo përsëri pas pak.",
                reply_markup=MENU_KB,
            )
    else:
        await update.message.reply_text(
            "😕 Shërbimi i raportimeve s'është aktiv tani.",
            reply_markup=MENU_KB,
        )
    return ConversationHandler.END


async def report_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("U anulua. 👍", reply_markup=MENU_KB)
    return ConversationHandler.END


async def on_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    if t == "❓ Pyetje të shpeshta":
        await show_faq_list(update, context)
    elif t == "📚 Hap Lexo Libra":
        await show_links(update, context)
    elif t == "📩 Raporto problem":
        return await report_start(update, context)
    else:
        await update.message.reply_text(
            "Zgjidh një opsion nga menuja më poshtë 👇",
            reply_markup=MENU_KB,
        )


def main():
    if not TOKEN:
        raise SystemExit("Mungon SUPPORT_BOT_TOKEN — vendose si variabël ambienti.")
    req = HTTPXRequest(connect_timeout=25.0, read_timeout=40.0,
                       write_timeout=40.0, pool_timeout=10.0,
                       httpx_kwargs=_HTTPX_KWARGS)
    app = Application.builder().token(TOKEN).request(req).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📩 Raporto problem$"),
                                     report_start)],
        states={ASK_REPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                            report_received)]},
        fallbacks=[CommandHandler("anulo", report_cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ndihme", cmd_start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(on_faq_callback,
                                         pattern=r"^faq:(shkarko|hapet|audio|aplikacioni|mungon)$"))
    app.add_handler(CallbackQueryHandler(on_faq_back, pattern=r"^faq:back$"))
    # Tekstet e menusë që nuk u kapën nga ConversationHandler
    app.add_handler(MessageHandler(filters.Regex(r"^(❓ Pyetje të shpeshta|📚 Hap Lexo Libra)$"),
                                    on_menu_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_menu_text))

    log.info("Lexo Libra Support Bot u ndez.")
    app.run_polling(bootstrap_retries=100, poll_interval=2.0)


if __name__ == "__main__":
    main()
