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
                              "window_start": iso,
                              "last_status": str|None} },
  "relay":   { "<admin_msg_id>": int },  # msg i përcjellë te admini -> user_id i klientit
  "daily":   { "<user_id>": {"<YYYY-MM-DD>": {"requests": int,
                                              "briefs": int}} },
  "settings": { "status": str },  # statusi i disponueshmërisë (vetëm zonë private)
  "projects": { "<project_id>": {"client_id": int, "title": str,
                                  "stage": int, "note": str,
                                  "created_at": iso, "updated_at": iso,
                                  "done": bool} },
  "slots":   { "<slot_id>": {"dt_iso": iso (ora lokale e Tiranës),
                             "booked_by": int|None,
                             "booking_id": str|None} },
  "bookings": { "<booking_id>": {"client_id": int, "slot_id": str,
                                 "service_key": str,
                                 "status": "pending"|"approved"|"rejected",
                                 "reminded": bool, "created_at": iso} },
  "reviews": { "<review_id>": {"client_id": int, "name": str,
                                "project_id": str, "stars": int (1-5,
                                vetëm intern), "text": str,
                                "status": "pending"|"approved"|"rejected",
                                "created_at": iso} }
}
Klienti ka edhe fushën "lang" ("sq"|"en", default "sq") — gjuha e
ndërfaqes; zgjedhja e vizitorit para aktivizimit ruhet te
settings["langs"] dhe kalon në regjistrin e klientit në aktivizim.
settings ka edhe: "welcome_voice_file_id" (mesazhi zanor i
mirëseardhjes), "weekly" (numëruesit javorë për raportin, çelës
ISO "YYYY-Www", mbahen 12 javët e fundit) dhe "last_digest_week".
Klienti ka edhe fushën opsionale "expiry_reminded_for" (iso) — vlera e
expires_at për të cilën iu dërgua kujtesa e skadimit (F3); kur afati
zgjatet, vlera s'përputhet më dhe kujtesa mund të dërgohet sërish.
"""
import hashlib
import json
import os
import secrets
import string
import threading
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    TIRANA = ZoneInfo("Europe/Tirane")
except Exception:  # pa tzdata — përafërsi fikse
    TIRANA = timezone(timedelta(hours=2))

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # pa 0/O/1/I — pa keqkuptime

DEFAULT_STATUS = "🟢 I disponueshëm për projekte të reja"

# Fazat e projektit — etiketat e sakta që sheh klienti te "Projekti im".
PROJECT_STAGES = ["Briefi", "Dizajni", "Zhvillimi", "Testimi", "Dorëzimi"]


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
                for k in ("codes", "clients", "requests", "attempts", "relay",
                          "daily", "settings", "projects", "slots",
                          "bookings", "reviews"):
                    d.setdefault(k, {})
                return d
        except (OSError, ValueError):
            pass
        return {"codes": {}, "clients": {}, "requests": {}, "attempts": {},
                "relay": {}, "daily": {}, "settings": {}, "projects": {},
                "slots": {}, "bookings": {}, "reviews": {}}

    def _save(self):
        # pastro numëruesit ditorë më të vjetër se 2 ditë (mbahen të lehtë)
        cutoff = (now_utc().date() - timedelta(days=2)).isoformat()
        daily = self._data.get("daily") or {}
        for uid in list(daily):
            for day in list(daily[uid]):
                if day < cutoff:
                    del daily[uid][day]
            if not daily[uid]:
                del daily[uid]
        # numëruesit javorë: mbahen vetëm 12 javët e fundit
        settings = self._data.get("settings") or {}
        weekly = settings.get("weekly") or {}
        if len(weekly) > 12:
            for k in sorted(weekly)[:-12]:
                del weekly[k]
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    # ---------- numëruesit ditorë (anti-spam) ----------
    @staticmethod
    def _day_key(at: datetime = None) -> str:
        return (at or now_utc()).date().isoformat()

    def count_today(self, user_id: int, kind: str, at: datetime = None) -> int:
        with self._lock:
            rec = (self._data.get("daily") or {}).get(str(user_id)) or {}
            return int((rec.get(self._day_key(at)) or {}).get(kind, 0))

    def bump_today(self, user_id: int, kind: str, at: datetime = None) -> int:
        at = at or now_utc()
        with self._lock:
            day = self._data["daily"].setdefault(str(user_id), {})
            entry = day.setdefault(self._day_key(at), {"requests": 0, "briefs": 0})
            entry[kind] = int(entry.get(kind, 0)) + 1
            if kind == "briefs":  # numëruesi javor i raportit (F6)
                self._bump_weekly_locked("briefs", at)
            self._save()
            return entry[kind]

    # ---------- numëruesit javorë (F6: raporti javor) ----------
    WEEKLY_KINDS = ("clients", "requests", "requests_approved", "briefs",
                    "bookings", "bookings_approved", "reviews")

    @staticmethod
    def week_key(at: datetime = None) -> str:
        """Çelësi ISO i javës (data lokale e Tiranës): '2026-W43'."""
        at = at or now_utc()
        d = at.astimezone(TIRANA).date()
        y, w, _ = d.isocalendar()
        return f"{y}-W{w:02d}"

    def _bump_weekly_locked(self, kind: str, at: datetime = None):
        """Rrit numëruesin javor — thirret VETËM nën kyç (nga metoda
        që tashmë e kanë kyçin), prandaj s'ruan vetë."""
        weekly = self._data.setdefault("settings", {}).setdefault("weekly", {})
        entry = weekly.setdefault(self.week_key(at),
                                  {k: 0 for k in self.WEEKLY_KINDS})
        entry[kind] = int(entry.get(kind, 0)) + 1

    def bump_weekly(self, kind: str, at: datetime = None):
        with self._lock:
            self._bump_weekly_locked(kind, at)
            self._save()

    def weekly_counters(self, key: str = None, at: datetime = None) -> dict:
        key = key or self.week_key(at)
        with self._lock:
            entry = (self._data.get("settings") or {}).get("weekly", {}).get(key) or {}
            return {k: int(entry.get(k, 0)) for k in self.WEEKLY_KINDS}

    def get_last_digest_week(self):
        with self._lock:
            return (self._data.get("settings") or {}).get("last_digest_week")

    def set_last_digest_week(self, key: str):
        with self._lock:
            self._data.setdefault("settings", {})["last_digest_week"] = key
            self._save()

    # ---------- gjuha e ndërfaqes (F3: sq/en për përdorues) ----------
    def get_lang(self, user_id: int) -> str:
        """Gjuha e përdoruesit: regjistri i klientit ka përparësi;
        për vizitorin vlen zgjedhja e ruajtur te settings['langs'];
        default 'sq'."""
        with self._lock:
            rec = self._data["clients"].get(str(user_id))
            if rec and rec.get("lang") in ("sq", "en"):
                return rec["lang"]
            lg = ((self._data.get("settings") or {}).get("langs") or {}
                  ).get(str(user_id))
            return lg if lg in ("sq", "en") else "sq"

    def set_lang(self, user_id: int, lang: str) -> str:
        lang = lang if lang in ("sq", "en") else "sq"
        with self._lock:
            settings = self._data.setdefault("settings", {})
            settings.setdefault("langs", {})[str(user_id)] = lang
            rec = self._data["clients"].get(str(user_id))
            if rec is not None:
                rec["lang"] = lang
            self._save()
            return lang

    # ---------- mesazhi zanor i mirëseardhjes (F5) ----------
    def get_welcome_voice(self):
        with self._lock:
            return (self._data.get("settings") or {}).get(
                "welcome_voice_file_id") or None

    def set_welcome_voice(self, file_id):
        with self._lock:
            settings = self._data.setdefault("settings", {})
            if file_id:
                settings["welcome_voice_file_id"] = file_id
            else:
                settings.pop("welcome_voice_file_id", None)
            self._save()

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
            existing = self._data["clients"].get(str(user_id))
            # gjuha (F3): ruhet e regjistrit ekzistues ose zgjedhja e
            # vizitorit te settings['langs']; default shqip
            lang = (existing or {}).get("lang") or (
                (self._data.get("settings") or {}).get("langs") or {}
            ).get(str(user_id)) or "sq"
            if lang not in ("sq", "en"):
                lang = "sq"
            self._data["clients"][str(user_id)] = {
                "name": name or "",
                "username": username or "",
                "service": service or "",
                "activated_at": iso(at),
                "expires_at": iso(exp),
                "via": via,
                "revoked": False,
                "lang": lang,
            }
            if existing is None:  # klient vërtet i ri → numëruesi javor (F6)
                self._bump_weekly_locked("clients", at)
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
    REQ_DAILY_MAX = 2      # kërkesa për shërbim për person, për ditë kalendarike
    BRIEF_DAILY_MAX = 3    # brief-e projekti për klient, për ditë kalendarike

    def pending_request_for(self, user_id: int):
        """Kërkesa 'pending' e përdoruesit (nëse ka) — max 1 në të njëjtën kohë."""
        with self._lock:
            for rid, rec in self._data["requests"].items():
                if rec.get("user_id") == user_id and rec.get("status") == "pending":
                    out = dict(rec)
                    out["id"] = rid
                    return out
            return None

    def request_block(self, user_id: int, at: datetime = None):
        """None nëse kërkesa e re lejohet; përndryshe arsyeja:
        'pending' (ka një në pritje) | 'daily' (limiti ditor u arrit)."""
        if self.pending_request_for(user_id) is not None:
            return "pending"
        if self.count_today(user_id, "requests", at=at) >= self.REQ_DAILY_MAX:
            return "daily"
        return None

    def brief_block(self, user_id: int, at: datetime = None) -> bool:
        return self.count_today(user_id, "briefs", at=at) >= self.BRIEF_DAILY_MAX

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
            day = self._data["daily"].setdefault(str(user_id), {})
            entry = day.setdefault(self._day_key(at), {"requests": 0, "briefs": 0})
            entry["requests"] = int(entry.get("requests", 0)) + 1
            self._bump_weekly_locked("requests", at)  # raporti javor (F6)
            self._save()
        return req_id

    def get_request(self, req_id: str):
        with self._lock:
            rec = self._data["requests"].get(req_id)
            return dict(rec) if rec else None

    def list_requests(self, status: str = None):
        """Të gjitha kërkesat (kopje), opsionalisht me filtër statusi
        — përdoret nga raporti javor (F6) për pikat në pritje."""
        with self._lock:
            rows = [dict(r) for r in self._data["requests"].values()]
        if status is not None:
            rows = [r for r in rows if r.get("status") == status]
        return rows

    def set_request_status(self, req_id: str, status: str) -> bool:
        with self._lock:
            rec = self._data["requests"].get(req_id)
            if rec is None:
                return False
            # miratimi numërohet në raportin javor vetëm kur kalon
            # nga 'pending' në 'approved' (pa numërime të dyfishta)
            if status == "approved" and rec.get("status") == "pending":
                self._bump_weekly_locked("requests_approved")
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

    def register_fail(self, user_id: int, status: str = None, at: datetime = None):
        """Regjistron një tentativë të dështuar te dera. Kthen True nëse sapo
        u kyç. `status` (arsyeja e saktë: invalid/expired/revoked/bound_other)
        ruhet vetëm për adminin — vizitori sheh gjithmonë mesazh gjenerik."""
        at = at or now_utc()
        with self._lock:
            key = str(user_id)
            rec = self._data["attempts"].get(key) or {
                "fails": 0, "locked_until": None, "window_start": iso(at),
                "last_status": None}
            ws = parse_iso(rec.get("window_start"))
            if ws is None or at - ws > timedelta(minutes=self.WINDOW_MINUTES):
                rec = {"fails": 0, "locked_until": None, "window_start": iso(at),
                       "last_status": None}
            rec["fails"] = int(rec.get("fails", 0)) + 1
            if status:
                rec["last_status"] = status
            locked_now = False
            if rec["fails"] >= self.MAX_FAILS:
                rec["locked_until"] = iso(at + timedelta(minutes=self.LOCK_MINUTES))
                rec["fails"] = 0
                locked_now = True
            self._data["attempts"][key] = rec
            self._save()
            return locked_now

    def last_fail_status(self, user_id: int):
        with self._lock:
            rec = self._data["attempts"].get(str(user_id)) or {}
            return rec.get("last_status")

    def clear_fails(self, user_id: int):
        with self._lock:
            self._data["attempts"].pop(str(user_id), None)
            self._save()

    # ---------- cilësimet: statusi i disponueshmërisë ----------
    def get_status(self) -> str:
        """Statusi që shohin klientët në faqen kryesore (zonë private).
        Kurrë në ekranin e kyçjes."""
        with self._lock:
            s = (self._data.get("settings") or {}).get("status") or ""
            return s.strip() or DEFAULT_STATUS

    def set_status(self, text: str) -> str:
        with self._lock:
            val = (text or "").strip()[:120]
            self._data.setdefault("settings", {})["status"] = val
            self._save()
            return val or DEFAULT_STATUS

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

    # ---------- projektet e klientëve (F1: "Projekti im") ----------
    def create_project(self, client_id: int, title: str, at: datetime = None):
        at = at or now_utc()
        pid = secrets.token_hex(4)
        with self._lock:
            while pid in self._data["projects"]:
                pid = secrets.token_hex(4)
            rec = {"id": pid, "client_id": int(client_id),
                   "title": (title or "").strip(), "stage": 0, "note": "",
                   "created_at": iso(at), "updated_at": iso(at),
                   "done": False}
            self._data["projects"][pid] = rec
            self._save()
        return dict(rec)

    def get_project(self, project_id: str):
        with self._lock:
            rec = self._data["projects"].get(project_id)
            return dict(rec) if rec else None

    def list_projects(self, client_id: int):
        with self._lock:
            out = [dict(r) for r in self._data["projects"].values()
                   if r.get("client_id") == int(client_id)]
        return sorted(out, key=lambda r: r.get("created_at") or "")

    def latest_project(self, client_id: int):
        """Projekti më i ri JO i përfunduar i klientit (objektivi i
        komandave /faza, /shenim_projekti, /projekt_fund)."""
        cand = [p for p in self.list_projects(client_id) if not p.get("done")]
        return cand[-1] if cand else None

    def _update_project(self, project_id: str, at: datetime = None, **kw):
        at = at or now_utc()
        with self._lock:
            rec = self._data["projects"].get(project_id)
            if rec is None:
                return None
            rec.update(kw)
            rec["updated_at"] = iso(at)
            self._save()
            return dict(rec)

    def set_stage(self, project_id: str, stage_idx: int, at: datetime = None):
        idx = max(0, min(len(PROJECT_STAGES) - 1, int(stage_idx)))
        return self._update_project(project_id, at=at, stage=idx)

    def set_note(self, project_id: str, text: str, at: datetime = None):
        return self._update_project(project_id, at=at,
                                    note=(text or "").strip())

    def finish_project(self, project_id: str, at: datetime = None):
        return self._update_project(project_id, at=at, done=True,
                                    stage=len(PROJECT_STAGES) - 1)

    # ---------- oraret & rezervimet e konsultave (F2) ----------
    def add_slot(self, dt_iso_str: str):
        sid = secrets.token_hex(4)
        with self._lock:
            while sid in self._data["slots"]:
                sid = secrets.token_hex(4)
            rec = {"id": sid, "dt_iso": dt_iso_str,
                   "booked_by": None, "booking_id": None}
            self._data["slots"][sid] = rec
            self._save()
        return dict(rec)

    def list_slots(self, at: datetime = None):
        """Të gjitha oraret, të renditura sipas kohës. Oraret e kaluara
        të lira pastrohen vetë në lexim; oraret e rezervuara ruhen si
        historik i rezervimeve."""
        at = at or now_utc()
        with self._lock:
            changed = False
            for sid in list(self._data["slots"]):
                s = self._data["slots"][sid]
                dt = parse_iso(s.get("dt_iso"))
                if dt and dt <= at and s.get("booked_by") is None:
                    del self._data["slots"][sid]
                    changed = True
            if changed:
                self._save()
            out = [dict(s) for s in self._data["slots"].values()]
        return sorted(out, key=lambda s: s.get("dt_iso") or "")

    def open_slots(self, at: datetime = None):
        return [s for s in self.list_slots(at=at)
                if s.get("booked_by") is None]

    def get_slot(self, slot_id: str):
        with self._lock:
            rec = self._data["slots"].get(slot_id)
            return dict(rec) if rec else None

    def delete_slot(self, slot_id: str) -> bool:
        """Fshin vetëm orar të lirë (të parezervuar)."""
        with self._lock:
            rec = self._data["slots"].get(slot_id)
            if rec is None or rec.get("booked_by") is not None:
                return False
            del self._data["slots"][slot_id]
            self._save()
            return True

    def create_booking(self, client_id: int, slot_id: str, service_key: str,
                       at: datetime = None):
        at = at or now_utc()
        bid = secrets.token_hex(4)
        with self._lock:
            while bid in self._data["bookings"]:
                bid = secrets.token_hex(4)
            rec = {"id": bid, "client_id": int(client_id),
                   "slot_id": slot_id, "service_key": service_key or "",
                   "status": "pending", "reminded": False,
                   "created_at": iso(at)}
            self._data["bookings"][bid] = rec
            self._bump_weekly_locked("bookings", at)  # raporti javor (F6)
            self._save()
        return dict(rec)

    def get_booking(self, booking_id: str):
        with self._lock:
            rec = self._data["bookings"].get(booking_id)
            return dict(rec) if rec else None

    def list_bookings(self):
        with self._lock:
            return {bid: dict(r) for bid, r in self._data["bookings"].items()}

    def pending_booking_for(self, client_id: int):
        """Rezervimi 'pending' i klientit (nëse ka) — max 1 njëherësh."""
        with self._lock:
            for rec in self._data["bookings"].values():
                if (rec.get("client_id") == int(client_id)
                        and rec.get("status") == "pending"):
                    return dict(rec)
        return None

    def set_booking_status(self, booking_id: str, status: str) -> bool:
        """Vendos statusin e rezervimit. Në 'approved', orari shënohet
        i rezervuar nga klienti (nuk ofrohet më); në 'rejected' orari
        mbetet i lirë, siç ishte."""
        with self._lock:
            rec = self._data["bookings"].get(booking_id)
            if rec is None:
                return False
            # miratimi numërohet në raportin javor vetëm në kalimin
            # nga 'pending' në 'approved'
            if status == "approved" and rec.get("status") == "pending":
                self._bump_weekly_locked("bookings_approved")
            rec["status"] = status
            if status == "approved":
                slot = self._data["slots"].get(rec.get("slot_id"))
                if slot is not None:
                    slot["booked_by"] = rec.get("client_id")
                    slot["booking_id"] = booking_id
            self._save()
            return True

    def set_booking_reminded(self, booking_id: str, val: bool = True) -> bool:
        with self._lock:
            rec = self._data["bookings"].get(booking_id)
            if rec is None:
                return False
            rec["reminded"] = bool(val)
            self._save()
            return True

    # ---------- vlerësimet e klientëve (paketa F1) ----------
    def create_review(self, client_id: int, name: str, project_id: str,
                      stars: int, text: str, at: datetime = None):
        """Krijon vlerësim 'pending' për një projekt të përfunduar.
        Maksimumi një vlerësim për projekt — thirrjet e dyta kthejnë
        vlerësimin ekzistues. Yjet (1-5) janë vlerë interne; klienti
        sheh vetëm simbolet ⭐ të përsëritura."""
        at = at or now_utc()
        with self._lock:
            for rec in self._data["reviews"].values():
                if rec.get("project_id") == project_id:
                    return dict(rec), False
            rid = secrets.token_hex(4)
            while rid in self._data["reviews"]:
                rid = secrets.token_hex(4)
            rec = {"id": rid, "client_id": int(client_id),
                   "name": name or "", "project_id": project_id,
                   "stars": max(1, min(5, int(stars))),
                   "text": (text or "").strip(),
                   "status": "pending", "created_at": iso(at)}
            self._data["reviews"][rid] = rec
            self._bump_weekly_locked("reviews", at)  # raporti javor (F6)
            self._save()
        return dict(rec), True

    def get_review(self, review_id: str):
        with self._lock:
            rec = self._data["reviews"].get(review_id)
            return dict(rec) if rec else None

    def review_for_project(self, project_id: str):
        with self._lock:
            for rec in self._data["reviews"].values():
                if rec.get("project_id") == project_id:
                    return dict(rec)
        return None

    def set_review_status(self, review_id: str, status: str) -> bool:
        with self._lock:
            rec = self._data["reviews"].get(review_id)
            if rec is None:
                return False
            rec["status"] = status
            self._save()
            return True

    def list_reviews(self, status: str = None):
        """Vlerësimet e renditura nga më i riu te më i vjetri."""
        with self._lock:
            out = [dict(r) for r in self._data["reviews"].values()
                   if status is None or r.get("status") == status]
        return sorted(out, key=lambda r: r.get("created_at") or "",
                      reverse=True)

    # ---------- kujtesa e skadimit të aksesit (F3) ----------
    def mark_expiry_reminded(self, user_id: int) -> bool:
        """Shënon se kujtesa e skadimit iu dërgua klientit për afatin
        aktual (expires_at). Kur afati zgjatet (expires_at ndryshon),
        shënimi s'përputhet më dhe klienti mund të kujtohet sërish."""
        with self._lock:
            rec = self._data["clients"].get(str(user_id))
            if rec is None:
                return False
            rec["expiry_reminded_for"] = rec.get("expires_at")
            self._save()
            return True
