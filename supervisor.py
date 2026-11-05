# Created by Erion Nezha — © 2026 All rights reserved
"""Server i vetëm për botët Dertli + Support + EnClient në Botkeep (një proces).

Arkitektura (v2, 2026-10-13):
- NJË proces Python mban botët si Application-e PTB. (v1 kishte
  supervisor + nënprocese; memoria kalonte limitin 512MB → OOM loop.)
- @lexolibra_bot shërbehet nga shërbimi i vet lexolibra-bot (wbot.py).
- HTTP server (stdlib, threading) në $PORT:
  * GET  /         → health ("ok - telegram bots running")
  * POST /wh/<bot> → webhook i Telegram-it për atë bot (secret i detyrueshëm)
- Secili bot regjistron webhook-un e vet te Telegram në nisje; Telegram e
  zgjon vetë shërbimin kur vjen mesazh — pa keepalive, pa polling.
- Nëse WEBHOOK_SECRET mungon (zhvillim lokal), botët kalojnë në polling
  brenda të njëjtit proces.
- Postimi ditor i "librit të ditës" në kanalin @lexolibra (09:41, Tiranë)
  mbetet thread më vete si më parë (post_channel.py si nënproces i shkurtër).

NDRYSHIMI v3 (2026-10-31, rregullim kundër 503 "application is not
responding"):
- Serveri HTTP niset I PARI, para çdo pune me Telegram. Në v2 porta
  hapej VETËM pasi të dy botët regjistronin webhook-un (deri në 40
  riprova × 15s); nëse Telegram vonohej në nisje, Botkeep e shihte
  shërbimin si të vdekur dhe kthente 503.
- Regjistrimi i webhook-ut riprovohet PA FUND në background dhe NUK e
  vret më procesin (v2: pas 40 dështimeve ngrinte RuntimeError → procesi
  binte → ndërprerje derisa Botkeep ta rindezte).
- Çdo dështim nisjeje i një boti riprovohet pas 30s pa prekur botin tjetër.

NDRYSHIMI v3-merged (2026-11-05, AUDIT ULTRA-DEEP — K1/K3/H2/M1/M3):
- BASHKIMI me enclient: BOTS ka edhe "enclient" (CLIENT_BOT_TOKEN,
  kodi nga enclient-bot/deploy/botkeep-pkg/bots/enclient/). Pa këtë,
  deploy-i i v3-së do ta çaktivizonte @ErionNezhaBot (404 në /wh/enclient).
- K3: run_bot kap BaseException (modulet ngrenë SystemExit kur mungon
  token-i; except Exception nuk e kap) — përveç CancelledError që
  ri-ngrihet për mbyllje të pastër.
- H2: GET /health kthen JSON me gjendjen reale të READY (boti shënohet
  "ready" vetëm pas initialize + webhook/polling + start; 200 kur të 3
  botët janë gati, 503 kur ndonjë është poshtë). GET / mbetet 200
  gjithmonë (monitorët ekzistues varen nga ai). do_POST kthen 503
  derisa boti të jetë në READY, që Telegram-i ta riprovojë dërgimin.
- M3: do_POST ka cap 1 MB për Content-Length (413 mbi cap) + timeout
  leximi 15s (408 në timeout).
- M1: requirements.txt me versione të pin-uara + httpx i deklaruar.
"""
import asyncio
import http.server
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

from telegram import Update


def _load_dotenv():
    """Botkeep i ruan variablat në file-in .env (rrënja e projektit), jo në env të procesit.

    Ngarkohen me setdefault: env-i real (p.sh. Render) ka gjithmonë përparësi.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    except OSError:
        pass


_load_dotenv()

BASE = os.path.dirname(os.path.abspath(__file__))
SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()
BASE_URL = (
    os.environ.get("PUBLIC_BASE_URL")
    or os.environ.get("RENDER_EXTERNAL_URL")
    or "https://telegram-bots-dc9n.onrender.com"
).rstrip("/")

# SHËNIM: @lexolibra_bot NUK shërbehet këtu — ai ka shërbimin e vet
# (lexolibra-bot, wbot.py) me webhook + veçoritë e plota (klubi i leximit).
# Dy shërbime mbi të njëjtin token luftojnë për webhook/getUpdates.
# "enclient" është @ErionNezhaBot (portali i klientëve) — token-i
# CLIENT_BOT_TOKEN; kodi + assets nga enclient-bot/deploy/botkeep-pkg/.
BOTS = [
    ("dertli", os.path.join(BASE, "bots", "dertli", "bot.py")),
    ("support", os.path.join(BASE, "bots", "support", "bot.py")),
    ("enclient", os.path.join(BASE, "bots", "enclient", "bot.py")),
]
ROUTES = {f"/wh/{name}": name for name, _ in BOTS}
APPS = {}
# H2: READY përmban vetëm botët që kanë përfunduar plotësisht nisjen
# (initialize + regjistrim webhook/polling + start). APPS vendoset PARA
# initialize() — një bot në dritaren e initialize() nuk është gati, dhe
# /health + do_POST duhet ta raportojnë si "down"/503, jo "ready"/200.
READY = set()
LOOP = None

# Postimi ditor i "librit të ditës" në kanalin @lexolibra (ora e Tiranës).
POST_SCRIPT = os.path.join(BASE, "bots", "lexolibra", "post_channel.py")
POST_STATE_FILE = os.path.join(BASE, ".channel_post_last")
POST_HOUR, POST_MINUTE = 9, 41

try:
    from zoneinfo import ZoneInfo
    _TIRANA = ZoneInfo("Europe/Tirane")
except Exception:
    _TIRANA = None


def _tirana_now():
    now_utc = datetime.now(timezone.utc)
    if _TIRANA is not None:
        try:
            return now_utc.astimezone(_TIRANA)
        except Exception:
            pass
    return now_utc + timedelta(hours=2)  # fallback: CEST


def _last_posted_date():
    try:
        with open(POST_STATE_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _mark_posted(today):
    try:
        with open(POST_STATE_FILE, "w", encoding="utf-8") as f:
            f.write(today)
    except OSError as e:
        print(f"[channel-post] s'u ruajt gjendja: {e}", flush=True)


def channel_post_loop():
    """Planifikuesi i postimit ditor: një herë në ditë, pas orës 09:41 (Tiranë).

    Thread i lehtë (kontroll çdo 60s). Ekzekuton post_channel.py si nënproces,
    i cili trashëgon env vars e shërbimit (TELEGRAM_TOKEN). Nuk prek botët.
    """
    print("[channel-post] planifikuesi i postimit ditor ndezur", flush=True)
    while True:
        try:
            now = _tirana_now()
            today = now.strftime("%Y-%m-%d")
            due = (now.hour, now.minute) >= (POST_HOUR, POST_MINUTE)
            if due and _last_posted_date() != today:
                if not os.environ.get("TELEGRAM_TOKEN"):
                    print("[channel-post] kapërcehet: mungon TELEGRAM_TOKEN",
                          flush=True)
                else:
                    print(f"[channel-post] po postohet libri i ditës ({today})...",
                          flush=True)
                    r = subprocess.run([sys.executable, POST_SCRIPT],
                                       capture_output=True, text=True,
                                       timeout=180)
                    if r.returncode == 0:
                        _mark_posted(today)
                        print("[channel-post] u postua me sukses", flush=True)
                    else:
                        tail = ((r.stderr or "") + (r.stdout or ""))[-300:]
                        print(f"[channel-post] DËSHTOI (kodi {r.returncode}): "
                              f"{tail}", flush=True)
        except Exception as e:
            print(f"[channel-post] gabim: {type(e).__name__}: {e}", flush=True)
        time.sleep(60)


def load_app(name, path):
    spec = importlib.util.spec_from_file_location(f"botmod_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_app()


MAX_BODY = 1_048_576  # M3: cap 1 MB për body-n e webhook-ut (Telegram dërgon < 64 KB)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _respond(self, code, body=b"", content_type="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            # H2: readiness real — vetëm botët në READY (nisje e plotë:
            # initialize + webhook/polling + start), jo thjesht në APPS.
            bots = {name: ("ready" if name in READY else "down")
                    for name, _ in BOTS}
            ok = all(v == "ready" for v in bots.values())
            body = json.dumps(
                {"status": "ok" if ok else "degraded", "bots": bots},
                sort_keys=True).encode("utf-8")
            self._respond(200 if ok else 503, body, "application/json")
            return
        self._respond(200, b"ok - telegram bots running")

    def do_POST(self):
        name = ROUTES.get(self.path.split("?", 1)[0])
        if name is None:
            self.close_connection = True  # body e palexuar — mos e
            self._respond(404)            # interpreto si request tjetër
            return
        if not SECRET or \
                self.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET:
            self.close_connection = True
            self._respond(403)
            return
        # M3: cap-i kontrollohet PARA READY — edhe me botin poshtë,
        # një body >1 MB kthehet 413 pa u lexuar kurrë në memorie.
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length < 0:
            length = 0
        if length > MAX_BODY:
            self.close_connection = True
            self._respond(413)
            return
        app = APPS.get(name)
        if app is None or name not in READY or LOOP is None:
            # Boti s'ka përfunduar nisjen: Telegram-i riprovon dërgimin
            # (në vend që update-i të pranohej me 200 dhe të mbetej
            # i papërpunuar në queue-n e një app-i të pa-startuar).
            self.close_connection = True
            self._respond(503)
            return
        try:
            self.connection.settimeout(15)  # M3: timeout leximi
            raw = self.rfile.read(length) if length > 0 else b""
        except (OSError, ValueError):
            self._respond(408)
            return
        finally:
            try:
                self.connection.settimeout(None)
            except OSError:
                pass
        try:
            update = Update.de_json(json.loads(raw.decode("utf-8")), app.bot)
        except Exception:
            self._respond(400)
            return
        if update is None:
            self._respond(400)
            return
        asyncio.run_coroutine_threadsafe(app.update_queue.put(update), LOOP)
        self._respond(200)

    def log_message(self, *args):
        pass


async def register_webhook_forever(app, name):
    """Regjistrimi i webhook-ut riprovohet PA FUND dhe NUK e vret procesin.

    Në v2, pas 40 dështimeve ngrihej RuntimeError → procesi binte dhe
    shërbimi kthehej 503 derisa Botkeep ta rindezte. Tani: derisa të
    regjistrohet, boti thjesht nuk merr update-e; serveri HTTP përgjigjet
    normalisht gjatë gjithë kohës.
    """
    url = f"{BASE_URL}/wh/{name}"
    attempt = 0
    while True:
        attempt += 1
        try:
            await app.bot.set_webhook(
                url=url, secret_token=SECRET,
                allowed_updates=Update.ALL_TYPES)
            print(f"[server] webhook u regjistrua për '{name}': {url}",
                  flush=True)
            return
        except Exception as e:
            print(f"[server] set_webhook '{name}' dështoi "
                  f"(ripova {attempt}): {e}", flush=True)
            await asyncio.sleep(15)


async def run_bot(name, path):
    """Nis një bot; çdo dështim riprovohet pas 30s pa prekur botin tjetër
    dhe pa e vrarë procesin."""
    while True:
        try:
            app = load_app(name, path)
            APPS[name] = app
            await app.initialize()
            if SECRET:
                await register_webhook_forever(app, name)
            else:
                await app.updater.start_polling(poll_interval=2.0)
                print(f"[server] '{name}' në polling (pa WEBHOOK_SECRET)",
                      flush=True)
            await app.start()
            READY.add(name)
            print(f"[server] boti '{name}' gati", flush=True)
            return
        except asyncio.CancelledError:
            APPS.pop(name, None)
            READY.discard(name)
            raise
        except BaseException as e:
            # K3: modulet ngrenë SystemExit kur mungon token-i
            # (dertli bot.py:229, support bot.py:227, enclient bot.py:4310);
            # except Exception nuk e kap SystemExit-in → task-i vdiste
            # heshturazi dhe HTTP mbetej 200. Tani riprovohet pas 30s.
            APPS.pop(name, None)
            READY.discard(name)
            print(f"[server] boti '{name}' dështoi në nisje: "
                  f"{type(e).__name__}: {e} (riprovohet pas 30s)", flush=True)
            await asyncio.sleep(30)


async def amain():
    global LOOP
    LOOP = asyncio.get_running_loop()
    # v3: serveri HTTP niset I PARI, para çdo pune me Telegram. Kështu porta
    # e caktuar (SERVER_PORT) përgjigjet menjëherë, edhe nëse regjistrimi
    # i webhook-ut vonohet ose dështon — Botkeep nuk e sheh më shërbimin
    # si "not responding".
    port = int(os.environ.get("PORT") or os.environ.get("SERVER_PORT") or "10000")
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[server] HTTP server në portin {port}", flush=True)
    for name, path in BOTS:
        asyncio.create_task(run_bot(name, path))
    await asyncio.Event().wait()


def main():
    threading.Thread(target=channel_post_loop, daemon=True,
                     name="channel-post").start()
    asyncio.run(amain())


if __name__ == "__main__":
    main()
