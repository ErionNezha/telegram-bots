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

BASE = os.path.dirname(os.path.abspath(__file__))

BOTS = [
    ("lexolibra", os.path.join(BASE, "bots", "lexolibra", "bot.py")),
    ("dertli", os.path.join(BASE, "bots", "dertli", "bot.py")),
    ("support", os.path.join(BASE, "bots", "support", "bot.py")),
]


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


def main():
    threading.Thread(target=serve_health, daemon=True).start()
    threads = []
    for name, script in BOTS:
        t = threading.Thread(target=run_forever, args=(name, script),
                             daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
