# Created by Erion Nezha — © 2026 All rights reserved
"""Supervisor për 3 botët Telegram në Render (një Web Service falas).

- Ndez një HTTP server minimal në $PORT (Render e kërkon për Web Service;
  shërben edhe për UptimeRobot/cron-job.org që e mbajnë zgjuar).
- Ndez 3 botët si nënprocese dhe i rindez automatikisht nëse dalin.
- Token-at vijnë nga env vars e Render (kurrë në kod).
"""
import http.server
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))

BOTS = [
    ("lexolibra", os.path.join(BASE, "bots", "lexolibra", "bot.py")),
    ("dertli", os.path.join(BASE, "bots", "dertli", "bot.py")),
    ("support", os.path.join(BASE, "bots", "support", "bot.py")),
]

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


class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok - telegram bots running")

    def log_message(self, *args):
        pass


def serve_health():
    port = int(os.environ.get("PORT", "10000"))
    srv = http.server.HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"[supervisor] health server në portin {port}", flush=True)
    srv.serve_forever()


def run_forever(name, script):
    while True:
        print(f"[supervisor] ndezja e botit '{name}'...", flush=True)
        proc = subprocess.Popen([sys.executable, script])
        proc.wait()
        print(f"[supervisor] boti '{name}' doli me kodin {proc.returncode}; "
              f"rindezje pas 5s...", flush=True)
        time.sleep(5)


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


def main():
    threading.Thread(target=serve_health, daemon=True).start()
    threads = []
    for name, script in BOTS:
        t = threading.Thread(target=run_forever, args=(name, script),
                             daemon=True)
        t.start()
        threads.append(t)
    t = threading.Thread(target=channel_post_loop, daemon=True,
                         name="channel-post")
    t.start()
    threads.append(t)
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
