<!-- Created by Erion Nezha — © 2026 All rights reserved -->
# Botët Telegram në Render (falas)

Një Web Service i vetëm falas mban ndezur të 3 botët:
**@lexolibra_bot**, **@dertlii_bot**, **@lexolibra_help_bot**.

## Si funksionon

- `supervisor.py` ndez një HTTP server minimal (e kërkon Render) + 3 botët si
  nënprocese, dhe i rindez automatikisht nëse ndonjë del.
- Plani falas jep **750 orë/muaj** — një shërbim 24/7 harxhon ~730 orë,
  pra **një** shërbim i vetëm falas mjafton për gjithë muajin.
- Shërbimet falas "flenë" pas 15 minutash pa trafik — prandaj nevojitet një
  ping i jashtëm (UptimeRobot, falas) çdo 5 minuta që e mban zgjuar.

## Hapat (një herë)

1. Krijo llogari falas në **render.com** (me "Sign up with GitHub").
2. Në dashboard: **New + → Blueprint** → zgjidh repo-n `telegram-bots` →
   **Apply**. (Ose: New + → Web Service → zgjidh repo-n manualisht me
   Build Command `pip install -r requirements.txt` dhe Start Command
   `python supervisor.py`, plani **Free**.)
3. Te **Environment**, plotëso:
   - `TELEGRAM_TOKEN` → tokeni i @lexolibra_bot
   - `DERTLI_TG_TOKEN` → tokeni i @dertlii_bot
   - `SUPPORT_BOT_TOKEN` → tokeni i @lexolibra_help_bot
   - `ADMIN_ID` → `1318275745` (gati e plotësuar)
4. **Deploy** — pas ~2 minutash log-u tregon "ndezja e botit" për të 3.
5. Testo në Telegram: `/start` te secili bot.
6. **Anti-gjumë (e detyrueshme):** krijo llogari falas në
   **uptimerobot.com** → Add Monitor → lloji **HTTP(s)**, URL-në e shërbimit
   tënd Render (p.sh. `https://telegram-bots-xxxx.onrender.com`), intervali
   **5 minuta**. Ky ping e mban shërbimin zgjuar përgjithmonë brenda
   kuotës falas.

## Shënime

- Token-at ruhen vetëm në Render si env vars — kurrë në kod, kurrë në GitHub.
- Statistikat/kozmimet e botëve ruhen në diskun kalimtar të Render:
  zerohen sa herë bëhet redeploy (nuk prish asgjë funksionale).
- Audio-përmbledhjet e Lexo Libra shkarkohen automatikisht nga
  `lexolibra.netlify.app/audio/` herën e parë që dikush shtyp "🔊 Dëgjo".
