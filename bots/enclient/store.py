#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created by Erion Nezha — © 2026 All rights reserved
"""
Ruajtja e gjendjes për botin privat të klientëve (EN Private Clients).

Parime sigurie:
- Kodet e aksesit NUK ruhen kurrë në tekst të qartë — ruhet vetëm hash-i
  SHA-256 i kodit të normalizuar. Kodi i qartë i tregohet adminit vetëm
  një herë, në momentin e krijimit.
- Çdo kod lidhet (bind) me ID-në Telegram të klientit të parë që e
  përdor; përcjellja te një llogari tjetër nuk punon.
- Shkrimet janë atomike (file i përkohshëm + os.replace) dhe bëhen nën
  një kyç (lock) — file-i i të dhënave nuk prishet nga aksese paralele.

Struktura e data.json:
{
  "codes":   { "<sha256>": {"note": str, "created_at": iso, "expires_at": iso,
                            "bound_user_id": int|None, "revoked": bool} },
  "clients": { "<user_id>": {"name": str, "username": str, "service": str,
                             "activated_at": iso, "expires_at": iso,
                             "via": "code"|"approval", "revoked": bool} },
  "requests": { "<req_id>": {"user_id": int, "name": str, "username": str,
                             "service": str, "contact": str, "desc": str,
                             "status": "pending"|"approved"|"rejected",
                             "created_at": iso} },
  "attempts": { "<user_id>": {"fails": int, "locked_until": iso|None,
                              "window_start": iso} },
  "relay":   { "<admin_msg_id>": int }   # msg i përcjellë te admini -> user_id i klientit
}
"""
import hashlib
import json
import os
import secrets
import string
import threading
from datetime import datetime, timedelta, timezone

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # pa 0/O/1/I — pa keqkuptime


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_iso(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def normalize_code(raw: str) -> str:
    """Normalizim tolerant: ' en-7kx4 9210 ', 'EN7KX49210' dhe
    'EN-7KX4-9210' japin të njëjtën vlerë 'EN7KX49210' — hashi krahasohet
    mbi këtë formë, prandaj gabimet e shkrimit të klientit s'e bllokojnë."""
    s = (raw or "").upper().replace("—", "-").replace("-", "")
    return "".join(s.split())


def hash_code(raw: str) -> str:
    return hashlib.sha256(normalize_code(raw).encode("utf-8")).hexdigest()


def generate_code() -> str:
    """Kod i ri unik në formatin EN-XXXX-XXXX."""
    part = lambda: "".join(secrets.choice(_ALPHABET) for _ in range(4))
    return f"EN-{part()}-{part()}"


class Store:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._data = self._load()

    # ---------- bazë ----------
    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                for k in ("codes", "clients", "requests", "attempts", "relay"):
                    d.setdefault(k, {})
                return d
        except (OSError, ValueError):
            pass
        return {"codes": {}, "clients": {}, "requests": {}, "attempts": {}, "relay": {}}

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    # ---------- kodet ----------
    def create_code(self, days: int = 30, note: str = "", at: datetime = None):
        """Krijon kod të ri; kthen kodin në tekst të qartë (vetëm këtë herë)."""
        at = at or now_utc()
        code = generate_code()
        with self._lock:
            while hash_code(code) in self._data["codes"]:
                code = generate_code()
            self._data["codes"][hash_code(code)] = {
                "note": note or "",
                "created_at": iso(at),
                "expires_at": iso(at + timedelta(days=days)),
                "bound_user_id": None,
                "revoked": False,
            }
            self._save()
        return code

    def redeem_code(self, raw_code: str, user_id: int, at: datetime = None):
        """Provon zhbllokimin me kod. Kthen (status, record|None).

        status: "ok" | "invalid" | "expired" | "revoked" | "bound_other"
        Në "ok", kodi lidhet me user_id (nëse s'ishte i lidhur) dhe
        klienti aktivizohet me të njëjtin afat skadence si kodi.
        """
        at = at or now_utc()
        h = hash_code(raw_code)
        with self._lock:
            rec = self._data["codes"].get(h)
            if rec is None:
                return "invalid", None
            if rec.get("revoked"):
                return "revoked", rec
            exp = parse_iso(rec.get("expires_at"))
            if exp and at > exp:
                return "expired", rec
            bound = rec.get("bound_user_id")
            if bound is not None and bound != user_id:
                return "bound_other", rec
            rec["bound_user_id"] = user_id
            self._save()
            return "ok", dict(rec)

    def revoke_code(self, raw_code: str) -> bool:
        with self._lock:
            rec = self._data["codes"].get(hash_code(raw_code))
            if rec is None:
                return False
            rec["revoked"] = True
            self._save()
            return True

    def list_codes(self):
        with self._lock:
            return [(h, dict(r)) for h, r in self._data["codes"].items()]

    # ---------- klientët ----------
    def activate_client(self, user_id: int, name: str, username: str,
                        service: str, days: int, via: str, at: datetime = None,
                        expires_at: datetime = None):
        at = at or now_utc()
        exp = expires_at or (at + timedelta(days=days))
        with self._lock:
            self._data["clients"][str(user_id)] = {
                "name": name or "",
                "username": username or "",
                "service": service or "",
                "activated_at": iso(at),
                "expires_at": iso(exp),
                "via": via,
                "revoked": False,
            }
            self._save()
        return dict(self._data["clients"][str(user_id)])

    def get_client(self, user_id: int, at: datetime = None):
        """Kthen klientin aktiv ose None (nëse s'ekziston / revokuar / skaduar)."""
        at = at or now_utc()
        with self._lock:
            rec = self._data["clients"].get(str(user_id))
            if not rec or rec.get("revoked"):
                return None
            exp = parse_iso(rec.get("expires_at"))
            if exp and at > exp:
                return None
            return dict(rec)

    def get_client_any(self, user_id: int):
        with self._lock:
            rec = self._data["clients"].get(str(user_id))
            return dict(rec) if rec else None

    def revoke_client(self, user_id: int) -> bool:
        with self._lock:
            rec = self._data["clients"].get(str(user_id))
            if rec is None:
                return False
            rec["revoked"] = True
            # revoko edhe kodet e lidhura me këtë klient
            for c in self._data["codes"].values():
                if c.get("bound_user_id") == user_id:
                    c["revoked"] = True
            self._save()
            return True

    def extend_client(self, user_id: int, days: int, at: datetime = None) -> bool:
        at = at or now_utc()
        with self._lock:
            rec = self._data["clients"].get(str(user_id))
            if rec is None:
                return False
            base = parse_iso(rec.get("expires_at")) or at
            if base < at:
                base = at
            rec["expires_at"] = iso(base + timedelta(days=days))
            rec["revoked"] = False
            self._save()
            return True

    def list_clients(self):
        with self._lock:
            return {uid: dict(r) for uid, r in self._data["clients"].items()}

    # ---------- kërkesat për shërbim ----------
    def create_request(self, user_id: int, name: str, username: str,
                       service: str, contact: str, desc: str,
                       at: datetime = None) -> str:
        at = at or now_utc()
        req_id = secrets.token_hex(4)
        with self._lock:
            while req_id in self._data["requests"]:
                req_id = secrets.token_hex(4)
            self._data["requests"][req_id] = {
                "user_id": user_id, "name": name or "", "username": username or "",
                "service": service or "", "contact": contact or "", "desc": desc or "",
                "status": "pending", "created_at": iso(at),
            }
            self._save()
        return req_id

    def get_request(self, req_id: str):
        with self._lock:
            rec = self._data["requests"].get(req_id)
            return dict(rec) if rec else None

    def set_request_status(self, req_id: str, status: str) -> bool:
        with self._lock:
            rec = self._data["requests"].get(req_id)
            if rec is None:
                return False
            rec["status"] = status
            self._save()
            return True

    # ---------- tentativat e gabuara / kyçja ----------
    MAX_FAILS = 3
    LOCK_MINUTES = 60
    WINDOW_MINUTES = 15

    def is_locked(self, user_id: int, at: datetime = None) -> bool:
        at = at or now_utc()
        with self._lock:
            rec = self._data["attempts"].get(str(user_id))
            if not rec:
                return False
            lu = parse_iso(rec.get("locked_until"))
            return bool(lu and at < lu)

    def register_fail(self, user_id: int, at: datetime = None):
        """Regjistron një kod të gabuar. Kthen True nëse sapo u kyç."""
        at = at or now_utc()
        with self._lock:
            key = str(user_id)
            rec = self._data["attempts"].get(key) or {
                "fails": 0, "locked_until": None, "window_start": iso(at)}
            ws = parse_iso(rec.get("window_start"))
            if ws is None or at - ws > timedelta(minutes=self.WINDOW_MINUTES):
                rec = {"fails": 0, "locked_until": None, "window_start": iso(at)}
            rec["fails"] = int(rec.get("fails", 0)) + 1
            locked_now = False
            if rec["fails"] >= self.MAX_FAILS:
                rec["locked_until"] = iso(at + timedelta(minutes=self.LOCK_MINUTES))
                rec["fails"] = 0
                locked_now = True
            self._data["attempts"][key] = rec
            self._save()
            return locked_now

    def clear_fails(self, user_id: int):
        with self._lock:
            self._data["attempts"].pop(str(user_id), None)
            self._save()

    # ---------- relay i mesazheve admin <-> klient ----------
    def map_relay(self, admin_msg_id: int, user_id: int):
        with self._lock:
            self._data["relay"][str(admin_msg_id)] = user_id
            # mbaj hartën të lehtë: max 500 hyrjet e fundit
            if len(self._data["relay"]) > 500:
                for k in list(self._data["relay"])[:-500]:
                    del self._data["relay"][k]
            self._save()

    def relay_target(self, admin_msg_id: int):
        with self._lock:
            return self._data["relay"].get(str(admin_msg_id))
