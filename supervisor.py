# Created by Erion Nezha — © 2026 All rights reserved
"""Server i vetëm për 3 botët Telegram në Render (një proces, plan falas).

Arkitektura (v2, 2026-10-13):
- NJË proces Python mban të 3 botët si Application-e PTB. (v1 kishte
  supervisor + 3 nënprocese; memoria kalonte limitin 512MB → OOM loop.)
- HTTP server (stdlib, threading) në $PORT:
  * GET  /         → health ("ok - telegram bots running")
  * POST /wh/<bot> → webhook i Telegram-it për atë bot (secret i detyrueshëm)
- Secili bot regjistron webhook-un e vet te Telegram në nisje; Telegram e
  zgjon vetë shërbimin kur vjen mesazh — pa keepalive, pa polling.
- Nëse WEBHOOK_SECRET mungon (zhvillim lokal), botët kalojnë në polling
  brenda të njëjtit proces.
- Postimi ditor i "librit të ditës" në kanalin @lexolibra (09:41, Tiranë)
  mbetet thread më vete si më parë (post_channel.py si nënproces i shkurtër).
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

BASE = os.path.dirname(os.path.abspath(__file__))
SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()
BASE_URL = os.environ.get(
    "RENDER_EXTERNAL_URL", "https://telegram-bots-dc9n.onrender.com"
).rstrip("/")

BOTS = [
    ("lexolibra", os.path.join(BASE, "bots", "lexolibra", "bot.py")),
    ("dertli", os.path.join(BASE, "bots", "dertli", "bot.py")),
    ("support", os.path.join(BASE, "bots", "support", "bot.py")),
]
ROUTES = {f"/wh/{name}": name for name, _ in BOTS}
APPS = {}
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


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _respond(self, code, body=b""):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        self._respond(200, b"ok - telegram bots running")

    def do_POST(self):
        name = ROUTES.get(self.path.split("?", 1)[0])
        if name is None:
            self._respond(404)
            return
        if not SECRET or \
                self.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET:
            self._respond(403)
            return
        app = APPS.get(name)
        if app is None or LOOP is None:
            self._respond(503)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""
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


async def amain():
    global LOOP
    LOOP = asyncio.get_running_loop()
    for name, path in BOTS:
        app = load_app(name, path)
        APPS[name] = app
        await app.initialize()
        if SECRET:
            url = f"{BASE_URL}/wh/{name}"
            for attempt in range(40):
                try:
                    await app.bot.set_webhook(
                        url=url, secret_token=SECRET,
                        allowed_updates=Update.ALL_TYPES)
                    print(f"[server] webhook u regjistrua për '{name}': {url}",
                          flush=True)
                    break
                except Exception as e:
                    print(f"[server] set_webhook '{name}' dështoi "
                          f"({attempt + 1}/40): {e}", flush=True)
                    await asyncio.sleep(15)
            else:
                raise RuntimeError(f"set_webhook dështoi për '{name}'")
        else:
            await app.updater.start_polling(poll_interval=2.0)
            print(f"[server] '{name}' në polling (pa WEBHOOK_SECRET)",
                  flush=True)
        await app.start()
        print(f"[server] boti '{name}' gati", flush=True)
    port = int(os.environ.get("PORT", "10000"))
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[server] HTTP server në portin {port}", flush=True)
    await asyncio.Event().wait()


def main():
    threading.Thread(target=channel_post_loop, daemon=True,
                     name="channel-post").start()
    asyncio.run(amain())


if __name__ == "__main__":
    main()
