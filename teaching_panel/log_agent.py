#!/usr/bin/env python3
"""
Log Agent v3 — Production Monitoring Telegram Bot (Solo-Developer Edition)

Modules:
  1. Error Statistics   — /stats, /top_errors, /top_slow
  2. Proactive Alerts   — error spikes, service down, disk, RAM, Celery, DB, SSL
  3. System Monitoring  — /health, /status
  4. Security           — login flood, admin escalation, command audit
  5. Scheduled Reports  — 6h mini, 09:00 daily, Monday weekly
  6. Error Tracker      — /errors, /resolve, /fixed, /analyze

QUIET MODE: Bot only sends messages on errors/alerts.
Info/stats — only on explicit command.

Env vars:
  GEMINI_API_KEY        — Google Gemini API key (required for AI)
  LOG_AGENT_TG_TOKEN    — Telegram Bot Token (required)
  LOG_AGENT_TG_CHAT     — Telegram Chat ID for alerts (required)
  LOG_AGENT_INTERVAL    — Error scan interval in seconds (default 60)
  LOG_AGENT_ALLOWED_CHATS — comma-separated extra chat IDs
  GEMINI_MODEL          — model name (default gemini-2.0-flash)
"""

import os
import sys
import re
import json
import time
import signal
import hashlib
import logging
import logging.handlers
import argparse
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

TELEGRAM_BOT_TOKEN = os.environ.get("LOG_AGENT_TG_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("LOG_AGENT_TG_CHAT", "")

ALLOWED_CHATS: set = set(
    filter(None, os.environ.get("LOG_AGENT_ALLOWED_CHATS", "").split(","))
)
if TELEGRAM_CHAT_ID:
    ALLOWED_CHATS.add(TELEGRAM_CHAT_ID)

BATCH_INTERVAL = int(os.environ.get("LOG_AGENT_INTERVAL", "60"))
MAX_BATCH_SIZE = 30
DEDUP_WINDOW_MINUTES = int(os.environ.get("LOG_AGENT_DEDUP_MINUTES", "5"))

# Alert thresholds
SPIKE_THRESHOLD = int(os.environ.get("LOG_AGENT_SPIKE_THRESHOLD", "10"))
SPIKE_WINDOW_SEC = int(os.environ.get("LOG_AGENT_SPIKE_WINDOW", "300"))
DISK_WARN_PCT = 85
RAM_WARN_PCT = 90
DB_CONN_WARN_PCT = 80
SSL_WARN_DAYS = 14
CELERY_QUEUE_WARN = 100
LOGIN_FAIL_THRESHOLD = 20
LOGIN_FAIL_WINDOW_MIN = 10

LOG_FILES = {
    "django":          "/var/www/teaching_panel/teaching_panel/logs/django.log",
    "requests":        "/var/www/teaching_panel/teaching_panel/logs/requests.log",
    "frontend":        "/var/www/teaching_panel/teaching_panel/logs/frontend_errors.log",
    "gunicorn_error":  "/var/log/teaching_panel/error.log",
    "gunicorn_access": "/var/log/teaching_panel/access.log",
    "celery":          "/var/log/teaching_panel/celery.log",
    "celery_beat":     "/var/log/teaching_panel/celery_beat.log",
    "nginx_error":     "/var/log/nginx/teaching_panel_error.log",
    "nginx_access":    "/var/log/nginx/teaching_panel_access.log",
}

STATE_FILE   = "/var/www/teaching_panel/teaching_panel/logs/log_agent_state.json"
TRACKER_FILE = "/var/www/teaching_panel/teaching_panel/logs/error_tracker.json"
AUDIT_FILE   = "/var/www/teaching_panel/teaching_panel/logs/bot_audit.log"
AGENT_LOG    = "/var/log/teaching_panel/log_agent.log"
STATS_FILE   = "/var/www/teaching_panel/teaching_panel/logs/error_stats.json"

PROJECT_DIR  = "/var/www/teaching_panel"
MANAGE_PY    = os.path.join(PROJECT_DIR, "teaching_panel", "manage.py")
PYTHON_BIN   = os.path.join(PROJECT_DIR, "venv", "bin", "python")

SSL_CERT_DOMAINS = ["lectiospace.ru", "olga.lectiospace.ru"]

# ═══════════════════════════════════════════════════════════════════════════
# LOGGING (agent's own log — WARNING+ only, no info spam)
# ═══════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

try:
    os.makedirs(os.path.dirname(AGENT_LOG), exist_ok=True)
    _fh = logging.handlers.RotatingFileHandler(
        AGENT_LOG, maxBytes=10 * 1024 * 1024, backupCount=3
    )
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _fh.setLevel(logging.WARNING)
    logging.getLogger().addHandler(_fh)
except Exception:
    pass

logger = logging.getLogger("log_agent")

# ═══════════════════════════════════════════════════════════════════════════
# HTTP CLIENT
# ═══════════════════════════════════════════════════════════════════════════

try:
    import requests as _requests

    def http_post(url, headers, json_data, timeout=30):
        r = _requests.post(url, headers=headers, json=json_data, timeout=timeout)
        return r.status_code, r.json()

    def http_post_raw(url, headers, data_bytes, timeout=30):
        r = _requests.post(url, headers=headers, data=data_bytes, timeout=timeout)
        return r.status_code, r.json()

    def http_get(url, timeout=10):
        r = _requests.get(url, timeout=timeout)
        return r.status_code, r.text

except ImportError:
    import urllib.request
    import urllib.error

    def http_post(url, headers, json_data, timeout=30):
        data = json.dumps(json_data).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode())
                return resp.status, body
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode())
            return e.code, body

    def http_post_raw(url, headers, data_bytes, timeout=30):
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode())
                return resp.status, body
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode())
            return e.code, body

    def http_get(url, timeout=10):
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()


# ═══════════════════════════════════════════════════════════════════════════
# ERROR PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

ERROR_PATTERNS = [
    re.compile(r"(ERROR|CRITICAL|Traceback|Exception|Error:)", re.IGNORECASE),
    re.compile(r"\[ERROR\]|\[CRITICAL\]|worker timeout|Boot failed", re.IGNORECASE),
    re.compile(
        r"(\[error\]|\[crit\]|\[alert\]|\[emerg\]|upstream timed out|"
        r"connect\(\) failed|no live upstreams|502|503|504)", re.IGNORECASE,
    ),
    re.compile(
        r"(Task .+ raised|WorkerLostError|Restoring .+ unacknowledged|"
        r"connection reset|broker .+ lost)", re.IGNORECASE,
    ),
    re.compile(r'" (5\d{2}) '),
    re.compile(r'" (403) '),
    re.compile(r"SLOW[_ ]REQUEST|took \d{4,}ms", re.IGNORECASE),
    re.compile(r"(MemoryError|out of memory|killed process|OOM)", re.IGNORECASE),
    re.compile(r"(No space left on device|disk full|IOError)", re.IGNORECASE),
    re.compile(
        r"(OperationalError|IntegrityError|connection refused|"
        r"too many connections|deadlock)", re.IGNORECASE,
    ),
]

IGNORE_PATTERNS = [
    re.compile(r"GET /health"),
    re.compile(r"GET /favicon\.ico"),
    re.compile(r"kube-probe|health_?check", re.IGNORECASE),
    re.compile(r"ELB-HealthChecker"),
    re.compile(r"status=[123]\d{2}\b"),
    re.compile(r"\.php|wp-login|xmlrpc|\.env|\.git", re.IGNORECASE),
    re.compile(r"jwt/verify.*403|jwt/logout.*40[01]", re.IGNORECASE),
    re.compile(r"DisallowedHost", re.IGNORECASE),
]

# Login failure detection
LOGIN_FAIL_PATTERN = re.compile(
    r"(401|403).*(/api/jwt/token/|/api/login|/api/auth)", re.IGNORECASE
)


def is_error_line(line: str) -> bool:
    for pat in IGNORE_PATTERNS:
        if pat.search(line):
            return False
    for pat in ERROR_PATTERNS:
        if pat.search(line):
            return True
    return False


def line_fingerprint(line: str) -> str:
    cleaned = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\.\d]*", "", line)
    cleaned = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "IP", cleaned)
    cleaned = re.sub(r"\b\d{4,}\b", "N", cleaned)
    return hashlib.md5(cleaned.encode()).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════════════
# ERROR STATISTICS (Module 1)
# ═══════════════════════════════════════════════════════════════════════════

class ErrorStats:
    """Keeps rolling error/request statistics for stats commands."""

    def __init__(self, path=STATS_FILE):
        self.path = path
        # Rolling window of recent errors: list of {ts, source, fingerprint, text_short}
        self.recent_errors: List[dict] = []
        # Rolling window of request metrics: list of {ts, path, status, duration_ms}
        self.recent_requests: List[dict] = []
        # Hourly counts for trend analysis
        self.hourly_counts: Dict[str, int] = {}  # "YYYY-MM-DD-HH" → count
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as f:
                    data = json.load(f)
                self.hourly_counts = data.get("hourly_counts", {})
        except Exception:
            pass

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            # Trim old hourly counts (keep 30 days)
            cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d-%H")
            self.hourly_counts = {
                k: v for k, v in self.hourly_counts.items() if k >= cutoff
            }
            with open(self.path, "w") as f:
                json.dump({"hourly_counts": self.hourly_counts}, f)
        except Exception:
            pass

    def record_error(self, source: str, fingerprint: str, text: str):
        now = datetime.now()
        self.recent_errors.append({
            "ts": now.isoformat(),
            "source": source,
            "fp": fingerprint,
            "text": text[:200],
        })
        # Trim to last 24h
        cutoff = (now - timedelta(hours=24)).isoformat()
        self.recent_errors = [e for e in self.recent_errors if e["ts"] >= cutoff]

        hour_key = now.strftime("%Y-%m-%d-%H")
        self.hourly_counts[hour_key] = self.hourly_counts.get(hour_key, 0) + 1

    def record_request(self, path: str, status: int, duration_ms: float):
        now = datetime.now()
        self.recent_requests.append({
            "ts": now.isoformat(),
            "path": path,
            "status": status,
            "dur": duration_ms,
        })
        cutoff = (now - timedelta(hours=24)).isoformat()
        self.recent_requests = [r for r in self.recent_requests if r["ts"] >= cutoff]

    def get_summary(self, hours: int = 24) -> str:
        now = datetime.now()
        cutoff = (now - timedelta(hours=hours)).isoformat()

        errors = [e for e in self.recent_errors if e["ts"] >= cutoff]
        requests = [r for r in self.recent_requests if r["ts"] >= cutoff]

        total_err = len(errors)
        unique_fps = len(set(e["fp"] for e in errors))

        # Count by severity
        err_5xx = sum(1 for r in requests if 500 <= r["status"] < 600)
        err_4xx = sum(1 for r in requests if 400 <= r["status"] < 500)
        slow = sum(1 for r in requests if r["dur"] > 2000)
        avg_dur = (sum(r["dur"] for r in requests) / len(requests)) if requests else 0

        # Trend: compare current period with previous same-length period
        prev_cutoff = (now - timedelta(hours=hours * 2)).isoformat()
        prev_errors = [e for e in self.recent_errors
                       if prev_cutoff <= e["ts"] < cutoff]
        trend = ""
        if prev_errors:
            diff = total_err - len(prev_errors)
            if diff > 0:
                trend = f"📈 +{diff} vs пред. период"
            elif diff < 0:
                trend = f"📉 {diff} vs пред. период"
            else:
                trend = "➡️ без изменений"

        # By source
        by_source = defaultdict(int)
        for e in errors:
            by_source[e["source"]] += 1

        lines = [
            f"📊 *Статистика за {hours}ч*",
            "─" * 28,
            f"🔴 Ошибок: *{total_err}* ({unique_fps} уникальных)",
            f"  5xx: {err_5xx} | 4xx: {err_4xx} | Slow >2s: {slow}",
            f"  Avg response: {avg_dur:.0f}ms",
        ]
        if trend:
            lines.append(f"  {trend}")

        if by_source:
            lines.append("\n*По источникам:*")
            for src, cnt in sorted(by_source.items(), key=lambda x: -x[1]):
                lines.append(f"  {src}: {cnt}")

        return "\n".join(lines)

    def get_top_errors(self, hours: int = 24, limit: int = 5) -> str:
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        errors = [e for e in self.recent_errors if e["ts"] >= cutoff]

        if not errors:
            return "✅ Ошибок за последние %dч нет!" % hours

        # Group by fingerprint
        groups: Dict[str, dict] = {}
        for e in errors:
            fp = e["fp"]
            if fp not in groups:
                groups[fp] = {"count": 0, "source": e["source"],
                              "text": e["text"], "last": e["ts"]}
            groups[fp]["count"] += 1
            if e["ts"] > groups[fp]["last"]:
                groups[fp]["last"] = e["ts"]

        top = sorted(groups.values(), key=lambda x: -x["count"])[:limit]

        lines = [f"🔝 *Топ-{limit} ошибок за {hours}ч*", "─" * 28]
        for i, g in enumerate(top, 1):
            text = g["text"][:120].replace("*", "").replace("`", "'").replace("\n", " ")
            lines.append(f"{i}. [{g['source']}] x{g['count']}\n   {text}")

        return "\n".join(lines)

    def get_top_slow(self, hours: int = 24, limit: int = 5) -> str:
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        requests = [r for r in self.recent_requests
                    if r["ts"] >= cutoff and r["dur"] > 500]

        if not requests:
            return "✅ Медленных запросов (>500ms) не найдено."

        # Group by path
        groups: Dict[str, dict] = {}
        for r in requests:
            p = r["path"]
            if p not in groups:
                groups[p] = {"count": 0, "max_dur": 0, "total_dur": 0}
            groups[p]["count"] += 1
            groups[p]["max_dur"] = max(groups[p]["max_dur"], r["dur"])
            groups[p]["total_dur"] += r["dur"]

        top = sorted(groups.items(), key=lambda x: -x[1]["max_dur"])[:limit]

        lines = [f"🐌 *Топ-{limit} медленных эндпоинтов за {hours}ч*", "─" * 28]
        for i, (path, g) in enumerate(top, 1):
            avg = g["total_dur"] / g["count"]
            lines.append(
                f"{i}. `{path}`\n"
                f"   x{g['count']} | max {g['max_dur']:.0f}ms | avg {avg:.0f}ms"
            )

        return "\n".join(lines)

    def errors_in_window(self, seconds: int) -> int:
        """Count errors in last N seconds (for spike detection)."""
        cutoff = (datetime.now() - timedelta(seconds=seconds)).isoformat()
        return sum(1 for e in self.recent_errors if e["ts"] >= cutoff)


# ═══════════════════════════════════════════════════════════════════════════
# ERROR TRACKER (Module 6)
# ═══════════════════════════════════════════════════════════════════════════

class ErrorTracker:
    def __init__(self, path=TRACKER_FILE):
        self.path = path
        self.active: Dict[str, dict] = {}
        self.resolved: Dict[str, dict] = {}
        self._next_id = 1
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as f:
                    data = json.load(f)
                self.active = data.get("active", {})
                self.resolved = data.get("resolved", {})
                self._next_id = data.get("next_id", 1)
        except Exception as e:
            logger.warning("Tracker load error: %s", e)

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump({
                    "active": self.active,
                    "resolved": self.resolved,
                    "next_id": self._next_id,
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Tracker save error: %s", e)

    def record_error(self, fingerprint: str, source: str, snippet: str) -> int:
        if fingerprint in self.resolved:
            old = self.resolved.pop(fingerprint)
            self.active[fingerprint] = {
                "id": old.get("id", self._next_id),
                "source": source,
                "snippet": snippet[:200],
                "first_seen": old.get("first_seen", datetime.now().isoformat()),
                "last_seen": datetime.now().isoformat(),
                "count": 1,
                "reopened": True,
            }
            if "id" not in old:
                self._next_id += 1
            self.save()
            return self.active[fingerprint]["id"]

        if fingerprint in self.active:
            self.active[fingerprint]["last_seen"] = datetime.now().isoformat()
            self.active[fingerprint]["count"] = self.active[fingerprint].get("count", 0) + 1
            return self.active[fingerprint]["id"]
        else:
            eid = self._next_id
            self._next_id += 1
            self.active[fingerprint] = {
                "id": eid,
                "source": source,
                "snippet": snippet[:200],
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "count": 1,
            }
            self.save()
            return eid

    def resolve_by_id(self, error_id: int) -> Optional[str]:
        for fp, info in list(self.active.items()):
            if info.get("id") == error_id:
                info["resolved_at"] = datetime.now().isoformat()
                self.resolved[fp] = info
                del self.active[fp]
                self.save()
                return info.get("snippet", "?")
        return None

    def auto_resolve_stale(self, hours: int = 24) -> int:
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        resolved_count = 0
        for fp, info in list(self.active.items()):
            if info.get("last_seen", "") < cutoff:
                info["resolved_at"] = datetime.now().isoformat()
                info["auto_resolved"] = True
                self.resolved[fp] = info
                del self.active[fp]
                resolved_count += 1
        if resolved_count:
            self.save()
        return resolved_count

    def get_report(self) -> str:
        active_count = len(self.active)
        resolved_count = len(self.resolved)
        total = active_count + resolved_count

        lines = ["📊 *Трекер ошибок*", "─" * 28]

        if total == 0:
            lines.append("Ошибок пока не зафиксировано.")
            return "\n".join(lines)

        pct = int(resolved_count / total * 100) if total > 0 else 0
        bar_len = 20
        filled = int(bar_len * pct / 100)
        bar = "▓" * filled + "░" * (bar_len - filled)

        lines.append(
            f"✅ Починено: *{resolved_count}*  |  ❌ Активных: *{active_count}*  |  Всего: *{total}*"
        )
        lines.append(f"[{bar}] {pct}%")

        if self.active:
            lines.append("\n*Активные ошибки:*")
            sorted_active = sorted(
                self.active.values(), key=lambda x: x.get("count", 0), reverse=True
            )
            for info in sorted_active[:15]:
                snip = info.get("snippet", "?")[:80].replace("*", "").replace("`", "'")
                cnt = info.get("count", 1)
                eid = info.get("id", "?")
                reopened = " 🔄" if info.get("reopened") else ""
                lines.append(f"  #{eid} [{info.get('source', '?')}] x{cnt}{reopened}\n   {snip}")
            if len(sorted_active) > 15:
                lines.append(f"  ...и ещё {len(sorted_active) - 15}")

        if self.resolved:
            lines.append("\n*Последние починенные:*")
            sorted_resolved = sorted(
                self.resolved.values(),
                key=lambda x: x.get("resolved_at", ""),
                reverse=True,
            )
            for info in sorted_resolved[:5]:
                snip = info.get("snippet", "?")[:60].replace("*", "").replace("`", "'")
                auto = " (авто)" if info.get("auto_resolved") else ""
                lines.append(f"  ✅ #{info.get('id', '?')}{auto} — {snip}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# FILE STATE (log position tracking)
# ═══════════════════════════════════════════════════════════════════════════

class FileState:
    def __init__(self, path=STATE_FILE):
        self.path = path
        self.positions: Dict[str, dict] = {}
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as f:
                    self.positions = json.load(f)
        except Exception:
            self.positions = {}

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.positions, f, indent=2)
        except Exception:
            pass

    def get_pos(self, filepath: str) -> int:
        info = self.positions.get(filepath, {})
        try:
            current_inode = os.stat(filepath).st_ino
            if info.get("inode") != current_inode:
                return 0
        except OSError:
            return 0
        return info.get("pos", 0)

    def set_pos(self, filepath: str, pos: int):
        try:
            inode = os.stat(filepath).st_ino
        except OSError:
            inode = 0
        self.positions[filepath] = {"pos": pos, "inode": inode}


# ═══════════════════════════════════════════════════════════════════════════
# LOG COLLECTOR
# ═══════════════════════════════════════════════════════════════════════════

class LogCollector:
    def __init__(self, state: FileState, tracker: ErrorTracker, stats: ErrorStats):
        self.state = state
        self.tracker = tracker
        self.stats = stats
        self.dedup_cache: Dict[str, datetime] = {}
        self.deduped_count = 0
        # For request metrics parsing
        self._req_pattern = re.compile(
            r"method=(\S+)\s+path=(\S+)\s+status=(\d+)\s+duration=(\S+)"
        )

    def collect_errors(self) -> List[dict]:
        all_errors = []
        self.deduped_count = 0
        now = datetime.now()

        cutoff = now - timedelta(minutes=DEDUP_WINDOW_MINUTES)
        self.dedup_cache = {k: v for k, v in self.dedup_cache.items() if v > cutoff}

        for source, filepath in LOG_FILES.items():
            if not os.path.exists(filepath):
                continue
            try:
                errors = self._read_new_errors(source, filepath, now)
                all_errors.extend(errors)
            except Exception as e:
                logger.error("Error reading %s: %s", filepath, e)

        self.state.save()
        return all_errors[:MAX_BATCH_SIZE]

    def _read_new_errors(self, source: str, filepath: str, now: datetime) -> List[dict]:
        errors = []
        pos = self.state.get_pos(filepath)

        try:
            file_size = os.path.getsize(filepath)
        except OSError:
            return errors

        if pos > file_size:
            pos = 0
        if pos >= file_size:
            return errors

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            f.seek(pos)
            lines = f.readlines()
            new_pos = f.tell()

        # Also parse request metrics from requests.log
        if source == "requests":
            for line in lines:
                self._parse_request_metric(line.rstrip())

        error_buffer = []
        in_traceback = False

        for line in lines:
            line = line.rstrip("\n")
            if not line:
                continue

            if "Traceback (most recent call last)" in line:
                if error_buffer:
                    self._flush_error(errors, source, error_buffer, now)
                error_buffer = [line]
                in_traceback = True
                continue

            if in_traceback:
                error_buffer.append(line)
                if (line and not line.startswith(" ") and not line.startswith("\t")
                        and ":" in line and not line.startswith("Traceback")
                        and not line.startswith("  ")):
                    self._flush_error(errors, source, error_buffer, now)
                    error_buffer = []
                    in_traceback = False
                continue

            if is_error_line(line):
                self._flush_error(errors, source, [line], now)

        if error_buffer:
            self._flush_error(errors, source, error_buffer, now)

        self.state.set_pos(filepath, new_pos)
        return errors

    def _parse_request_metric(self, line: str):
        """Parse requests.log line for stats."""
        m = self._req_pattern.search(line)
        if m:
            try:
                path = m.group(2)
                status = int(m.group(3))
                dur_str = m.group(4).rstrip("s")
                duration_ms = float(dur_str) * 1000
                self.stats.record_request(path, status, duration_ms)
            except (ValueError, IndexError):
                pass

    def _flush_error(self, errors: list, source: str, lines: List[str], now: datetime):
        text = "\n".join(lines[-20:])
        fp = line_fingerprint(text)

        self.tracker.record_error(fp, source, text)
        self.stats.record_error(source, fp, text)

        if fp in self.dedup_cache:
            self.deduped_count += 1
            return
        self.dedup_cache[fp] = now

        errors.append({
            "source": source,
            "text": text,
            "timestamp": now.isoformat(),
            "fingerprint": fp,
        })


# ═══════════════════════════════════════════════════════════════════════════
# USER CONTEXT ENRICHMENT
# ═══════════════════════════════════════════════════════════════════════════

def enrich_errors_with_user_info(errors: List[dict]):
    req_log = LOG_FILES.get("requests", "")
    if not errors or not req_log or not os.path.exists(req_log):
        return

    recent = []
    try:
        with open(req_log, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 50000))
            pat = re.compile(
                r"method=(\S+)\s+path=(\S+)\s+status=(\d+)\s+duration=(\S+)\s+user=(\S+)\s+ip=(\S+)"
            )
            for raw in f:
                m = pat.search(raw)
                if m and int(m.group(3)) >= 400:
                    recent.append({
                        "method": m.group(1), "path": m.group(2),
                        "status": int(m.group(3)), "user": m.group(5),
                        "ip": m.group(6),
                    })
    except Exception:
        return

    recent = recent[-100:]
    for err in errors:
        t = err.get("text", "")
        u = re.search(r'user=(\S+)', t)
        ip = re.search(r'ip=(\S+)', t)
        if u:
            err["user_id"] = u.group(1)
        if ip:
            err["user_ip"] = ip.group(1)

        if "user_id" not in err:
            path_m = re.search(r'path=(/\S+)', t)
            if path_m:
                for req in reversed(recent):
                    if req["path"] == path_m.group(1):
                        err["user_id"] = req["user"]
                        err["user_ip"] = req["ip"]
                        break

        if "user_id" not in err and err.get("source") in ("django", "gunicorn_error"):
            for req in reversed(recent):
                if req["status"] >= 500:
                    err["user_id"] = req["user"]
                    err["user_ip"] = req["ip"]
                    break


# ═══════════════════════════════════════════════════════════════════════════
# GEMINI AI ANALYZER
# ═══════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Ты — опытный DevOps/SRE-инженер, анализирующий логи production Django+Gunicorn+Celery+Nginx+PostgreSQL приложения LectioSpace (платформа обучения).

Стек: Django 4.2, DRF, Gunicorn, Celery + Redis, Nginx, PostgreSQL, React frontend.
Домены: lectiospace.ru, olga.lectiospace.ru.

Для каждой ошибки:
1. 👤 КТО: user ID, IP, роль (student/teacher/admin)
2. 📍 ГДЕ: API endpoint, модуль/компонент
3. 📖 СЦЕНАРИЙ: что делал пользователь, что пошло не так
4. 🔴 КРИТИЧНОСТЬ: 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low
5. 🔍 ПРИЧИНА: техническая причина (1-2 предложения)
6. 🛠 РЕШЕНИЕ: конкретные команды или код
7. ⚡ ВЛИЯНИЕ: кого затрагивает

Формат — Markdown, компактно. Группируй связанные ошибки. Русский язык."""


def analyze_with_ai(errors: List[dict]) -> Optional[str]:
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set")
        return None

    parts = []
    for i, err in enumerate(errors, 1):
        ctx = ""
        if err.get("user_id"):
            ctx += f" | user={err['user_id']}"
        if err.get("user_ip"):
            ctx += f" ip={err['user_ip']}"
        parts.append(f"--- Ошибка #{i} [{err['source']}]{ctx} ---\n{err['text']}")

    user_msg = (
        f"Проанализируй {len(errors)} ошибок из продакшена "
        f"(собраны за последние {BATCH_INTERVAL} секунд):\n\n"
        + "\n\n".join(parts)
    )
    if len(user_msg) > 8000:
        user_msg = user_msg[:7900] + "\n\n...(обрезано)"

    payload = {
        "contents": [
            {
                "parts": [{"text": SYSTEM_PROMPT + "\n\n" + user_msg}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2000,
        }
    }

    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    try:
        data = json.dumps(payload).encode("utf-8")
        status, resp = http_post_raw(
            api_url,
            {"Content-Type": "application/json"},
            data,
            timeout=60,
        )
        if status == 200:
            candidates = resp.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts_resp = content.get("parts", [])
                if parts_resp:
                    return parts_resp[0].get("text", "")
        elif status == 429:
            logger.warning("Gemini rate limit, retry in 30s...")
            time.sleep(30)
            status, resp = http_post_raw(api_url, {"Content-Type": "application/json"}, data, timeout=60)
            if status == 200:
                candidates = resp.get("candidates", [])
                if candidates:
                    return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        logger.error("Gemini API error: %s — %s", status, str(resp)[:300])
        return None
    except Exception as e:
        logger.error("Gemini API exception: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════════════════════

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else ""
MAX_TG_LENGTH = 4000


def _escape_md(text: str) -> str:
    text = re.sub(r'(?<!`)_(?!`)', '\\_', text)
    text = text.replace('--', '—')
    text = text.replace('**', '')
    return text


def send_telegram(text: str, chat_id: str = None, max_retries: int = 3) -> bool:
    cid = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not cid:
        return False

    url = TELEGRAM_API_BASE + "/sendMessage"

    chunks = []
    if len(text) <= MAX_TG_LENGTH:
        chunks = [text]
    else:
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > MAX_TG_LENGTH:
                chunks.append(current)
                current = line
            else:
                current += ("\n" if current else "") + line
        if current:
            chunks.append(current)

    success = True
    for chunk in chunks:
        sent = False
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    payload = {
                        "chat_id": cid,
                        "text": _escape_md(chunk),
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    }
                else:
                    plain = chunk.replace("*", "").replace("`", "'").replace("_", " ")
                    payload = {"chat_id": cid, "text": plain, "disable_web_page_preview": True}

                status, resp = http_post(url, {"Content-Type": "application/json"}, payload, timeout=15)

                if status == 200:
                    sent = True
                    break
                elif status == 400:
                    continue
                elif status == 429:
                    time.sleep(5 * (attempt + 1))
                    continue
                else:
                    continue
            except Exception:
                time.sleep(3 * (attempt + 1))

        if not sent:
            success = False
        time.sleep(0.3)

    return success


def send_error_alert(errors: List[dict], deduped_count: int = 0) -> bool:
    """Only sends alerts about ERRORS — no info/status."""
    ts = datetime.now().strftime("%H:%M:%S")
    header = f"🔴 *{len(errors)} ошибок* — {ts}"
    if deduped_count > 0:
        header += f" (+{deduped_count} повторных)"

    lines = [header + "\n"]
    for err in errors[:10]:
        user_info = ""
        uid = err.get("user_id", "")
        ip = err.get("user_ip", "")
        if uid and uid != "anonymous":
            user_info += f" user={uid}"
        if ip:
            user_info += f" ip={ip}"

        short = (
            err["text"][:250]
            .replace("*", "").replace("`", "'")
            .replace("_", " ").replace("--", "—")
        )
        lines.append(f"• [{err['source']}]{user_info}\n  {short}")

    if len(errors) > 10:
        lines.append(f"...и ещё {len(errors) - 10}")

    return send_telegram("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════════════
# COMMAND AUDIT LOG (Module 4)
# ═══════════════════════════════════════════════════════════════════════════

def audit_log(chat_id: str, command: str):
    try:
        os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
        with open(AUDIT_FILE, "a") as f:
            f.write(f"{datetime.now().isoformat()} chat={chat_id} cmd={command}\n")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM MONITORS (Module 2 — Proactive Alerts)
# ═══════════════════════════════════════════════════════════════════════════

def _fmt_size(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def _run_cmd(cmd: list, timeout: int = 5) -> Optional[str]:
    try:
        return subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, timeout=timeout
        ).decode().strip()
    except Exception:
        return None


class SystemMonitor:
    """Checks system resources and sends proactive alerts."""

    def __init__(self):
        self.last_alerts: Dict[str, datetime] = {}
        # Cooldown: don't repeat same alert type within this window
        self.alert_cooldown = timedelta(minutes=30)
        # Login fail tracking
        self.login_fails: deque = deque(maxlen=1000)
        # Spike tracking
        self.last_spike_alert: Optional[datetime] = None

    def _should_alert(self, alert_type: str) -> bool:
        now = datetime.now()
        last = self.last_alerts.get(alert_type)
        if last and (now - last) < self.alert_cooldown:
            return False
        self.last_alerts[alert_type] = now
        return True

    def check_all(self) -> List[str]:
        """Returns list of alert messages (empty = all OK)."""
        alerts = []
        alerts.extend(self._check_disk())
        alerts.extend(self._check_ram())
        alerts.extend(self._check_services())
        alerts.extend(self._check_db_connections())
        alerts.extend(self._check_celery_queue())
        alerts.extend(self._check_ssl_certs())
        return alerts

    def _check_disk(self) -> List[str]:
        out = _run_cmd(["df", "--output=pcent,avail", "/"])
        if not out:
            return []
        lines = out.strip().split("\n")
        if len(lines) < 2:
            return []
        parts = lines[1].split()
        if not parts:
            return []
        try:
            pct = int(parts[0].replace("%", ""))
        except ValueError:
            return []
        if pct >= DISK_WARN_PCT and self._should_alert("disk"):
            avail = parts[1] if len(parts) > 1 else "?"
            return [f"⚠️ Диск: {pct}% занято (свободно: {avail})"]
        return []

    def _check_ram(self) -> List[str]:
        out = _run_cmd(["free", "-m"])
        if not out:
            return []
        for line in out.split("\n"):
            if line.startswith("Mem:"):
                parts = line.split()
                if len(parts) >= 3:
                    total, used = int(parts[1]), int(parts[2])
                    pct = int(used / total * 100) if total > 0 else 0
                    if pct >= RAM_WARN_PCT and self._should_alert("ram"):
                        return [f"⚠️ RAM: {pct}% ({used}MB/{total}MB)"]
        return []

    def _check_services(self) -> List[str]:
        alerts = []
        critical_services = ["teaching_panel", "nginx", "postgresql"]
        for svc in critical_services:
            out = _run_cmd(["systemctl", "is-active", svc])
            if out and out != "active" and self._should_alert(f"svc_{svc}"):
                alerts.append(f"🔴 Сервис *{svc}* не работает! (status: {out})")
        return alerts

    def _check_db_connections(self) -> List[str]:
        # Check PostgreSQL connections
        out = _run_cmd([
            "sudo", "-u", "postgres", "psql", "-t", "-c",
            "SELECT count(*) FROM pg_stat_activity WHERE state != 'idle';"
        ])
        if not out:
            return []
        try:
            active = int(out.strip())
        except ValueError:
            return []

        max_out = _run_cmd([
            "sudo", "-u", "postgres", "psql", "-t", "-c",
            "SHOW max_connections;"
        ])
        try:
            max_conn = int(max_out.strip()) if max_out else 100
        except ValueError:
            max_conn = 100

        pct = int(active / max_conn * 100) if max_conn > 0 else 0
        if pct >= DB_CONN_WARN_PCT and self._should_alert("db_conn"):
            return [f"⚠️ PostgreSQL: {active}/{max_conn} подключений ({pct}%)"]
        return []

    def _check_celery_queue(self) -> List[str]:
        out = _run_cmd(["celery", "-A", "teaching_panel", "inspect", "active_queues"], timeout=10)
        if out and "Error" in out and self._should_alert("celery"):
            return ["⚠️ Celery worker не отвечает!"]

        # Check queue length via Redis
        out = _run_cmd(["redis-cli", "llen", "celery"])
        if out:
            try:
                qlen = int(out.strip())
                if qlen >= CELERY_QUEUE_WARN and self._should_alert("celery_queue"):
                    return [f"⚠️ Celery очередь: {qlen} задач (порог: {CELERY_QUEUE_WARN})"]
            except ValueError:
                pass
        return []

    def _check_ssl_certs(self) -> List[str]:
        alerts = []
        for domain in SSL_CERT_DOMAINS:
            out = _run_cmd([
                "openssl", "s_client", "-connect", f"{domain}:443",
                "-servername", domain, "-showcerts"
            ], timeout=10)
            if not out:
                continue

            # Extract expiry date
            try:
                # pipe cert to openssl x509
                proc = subprocess.run(
                    ["openssl", "s_client", "-connect", f"{domain}:443",
                     "-servername", domain],
                    capture_output=True, timeout=10,
                    input=b"", text=False,
                )
                cert_data = proc.stdout
                proc2 = subprocess.run(
                    ["openssl", "x509", "-noout", "-enddate"],
                    capture_output=True, timeout=5,
                    input=cert_data, text=True,
                )
                date_str = proc2.stdout.strip().replace("notAfter=", "")
                if date_str:
                    # Parse: "Mar 15 12:00:00 2026 GMT"
                    from email.utils import parsedate_to_datetime
                    try:
                        exp = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                    except ValueError:
                        continue
                    days_left = (exp - datetime.now()).days
                    if days_left < SSL_WARN_DAYS and self._should_alert(f"ssl_{domain}"):
                        alerts.append(
                            f"⚠️ SSL *{domain}*: истекает через {days_left} дней! ({exp.strftime('%Y-%m-%d')})"
                        )
            except Exception:
                pass
        return alerts

    def check_error_spike(self, error_stats: ErrorStats) -> Optional[str]:
        """Check for error spike."""
        count = error_stats.errors_in_window(SPIKE_WINDOW_SEC)
        if count >= SPIKE_THRESHOLD:
            now = datetime.now()
            if self.last_spike_alert and (now - self.last_spike_alert).total_seconds() < 600:
                return None  # Don't spam spikes (10 min cooldown)
            self.last_spike_alert = now

            # Get top error in the spike
            cutoff = (now - timedelta(seconds=SPIKE_WINDOW_SEC)).isoformat()
            recent = [e for e in error_stats.recent_errors if e["ts"] >= cutoff]
            top_text = ""
            if recent:
                from collections import Counter
                fps = Counter(e["fp"] for e in recent)
                top_fp = fps.most_common(1)[0][0]
                for e in recent:
                    if e["fp"] == top_fp:
                        top_text = e["text"][:100].replace("*", "").replace("`", "'")
                        break

            return (
                f"🚨 *Всплеск ошибок!*\n"
                f"{count} ошибок за последние {SPIKE_WINDOW_SEC // 60} мин "
                f"(порог: {SPIKE_THRESHOLD})\n"
                f"Топ: {top_text}"
            )
        return None

    def check_login_floods(self, line: str) -> Optional[str]:
        """Track login failures for brute force detection."""
        if LOGIN_FAIL_PATTERN.search(line):
            ip_m = re.search(r'ip=(\S+)', line)
            ip = ip_m.group(1) if ip_m else "unknown"
            self.login_fails.append({
                "ts": datetime.now(),
                "ip": ip,
            })

            # Check flood from single IP
            cutoff = datetime.now() - timedelta(minutes=LOGIN_FAIL_WINDOW_MIN)
            recent_from_ip = [
                f for f in self.login_fails
                if f["ts"] >= cutoff and f["ip"] == ip
            ]
            if (len(recent_from_ip) >= LOGIN_FAIL_THRESHOLD
                    and self._should_alert(f"login_flood_{ip}")):
                return (
                    f"🔐 *Подозрительная активность!*\n"
                    f"{len(recent_from_ip)} неудачных логинов с IP `{ip}` "
                    f"за {LOGIN_FAIL_WINDOW_MIN} мин"
                )
        return None


# ═══════════════════════════════════════════════════════════════════════════
# HEALTH CHECK (for /health command)
# ═══════════════════════════════════════════════════════════════════════════

def run_health_checks() -> str:
    results = ["🏥 *Health Check*", "─" * 28]

    services = [
        "teaching_panel", "celery", "nginx",
        "redis-server", "postgresql", "log-agent",
    ]
    for svc in services:
        out = _run_cmd(["systemctl", "is-active", svc])
        if out:
            icon = "✅" if out == "active" else "⚠️"
            results.append(f"{icon} {svc}: {out}")
        else:
            results.append(f"❌ {svc}: не проверить")

    # HTTP
    results.append("")
    try:
        status, _ = http_get("http://127.0.0.1:8000/api/health/", timeout=5)
        icon = "✅" if status == 200 else "⚠️"
        results.append(f"{icon} API: HTTP {status}")
    except Exception as e:
        results.append(f"❌ API: {str(e)[:60]}")

    # External HTTPS
    try:
        status, _ = http_get("https://lectiospace.ru/", timeout=10)
        icon = "✅" if status == 200 else "⚠️"
        results.append(f"{icon} HTTPS: {status}")
    except Exception as e:
        results.append(f"❌ HTTPS: {str(e)[:60]}")

    # Disk
    try:
        out = subprocess.check_output(["df", "-h", "/"], timeout=5).decode()
        for line in out.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 5:
                use_pct = int(parts[4].replace("%", ""))
                icon = "✅" if use_pct < 80 else ("⚠️" if use_pct < 90 else "🔴")
                results.append(f"{icon} Диск: {parts[4]} ({parts[3]} свободно)")
    except Exception:
        pass

    # RAM
    try:
        out = subprocess.check_output(["free", "-m"], timeout=5).decode()
        for line in out.split("\n"):
            if line.startswith("Mem:"):
                parts = line.split()
                total, used = int(parts[1]), int(parts[2])
                pct = int(used / total * 100)
                icon = "✅" if pct < 80 else ("⚠️" if pct < 90 else "🔴")
                results.append(f"{icon} RAM: {used}MB/{total}MB ({pct}%)")
    except Exception:
        pass

    # Redis
    out = _run_cmd(["redis-cli", "ping"])
    if out:
        icon = "✅" if out == "PONG" else "❌"
        results.append(f"{icon} Redis: {out}")
    else:
        results.append("❌ Redis: не отвечает")

    # PostgreSQL
    out = _run_cmd(["pg_isready"])
    if out:
        icon = "✅" if "accepting" in out else "⚠️"
        results.append(f"{icon} PostgreSQL: {out[:60]}")

    # DB connections
    out = _run_cmd([
        "sudo", "-u", "postgres", "psql", "-t", "-c",
        "SELECT count(*) FROM pg_stat_activity;"
    ])
    if out:
        results.append(f"  📊 DB connections: {out.strip()}")

    # Log file sizes
    results.append("\n*Логи:*")
    for name, path in LOG_FILES.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            icon = "⚠️" if size > 100 * 1024 * 1024 else "📄"
            results.append(f"  {icon} {name}: {_fmt_size(size)}")

    return "\n".join(results)


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN ESCALATION DETECTION (Module 4)
# ═══════════════════════════════════════════════════════════════════════════

class SecurityMonitor:
    """Monitors for admin privilege escalation and other security events."""

    def __init__(self):
        self.last_admin_check: Optional[datetime] = None
        self.known_admins: set = set()

    def check_new_admins(self) -> Optional[str]:
        """Check if new admin accounts were created (every 5 min)."""
        now = datetime.now()
        if self.last_admin_check and (now - self.last_admin_check).total_seconds() < 300:
            return None
        self.last_admin_check = now

        try:
            out = subprocess.check_output(
                [PYTHON_BIN, MANAGE_PY, "shell", "-c",
                 "from django.contrib.auth import get_user_model; "
                 "User = get_user_model(); "
                 "admins = User.objects.filter(is_staff=True).values_list('id', 'email', 'date_joined'); "
                 "print(list(admins))"],
                stderr=subprocess.STDOUT, timeout=10,
                cwd=os.path.join(PROJECT_DIR, "teaching_panel"),
            ).decode().strip()

            # Parse admin list
            import ast
            try:
                admins = ast.literal_eval(out)
            except (ValueError, SyntaxError):
                return None

            current_ids = {str(a[0]) for a in admins}

            if not self.known_admins:
                self.known_admins = current_ids
                return None

            new_ids = current_ids - self.known_admins
            if new_ids:
                self.known_admins = current_ids
                new_admins = [a for a in admins if str(a[0]) in new_ids]
                names = ", ".join(f"{a[1]} (id={a[0]})" for a in new_admins)
                return f"🔐 *Новые admin-аккаунты:*\n{names}"

            self.known_admins = current_ids
        except Exception:
            pass
        return None


# ═══════════════════════════════════════════════════════════════════════════
# TELEGRAM BOT — Command Handler (long polling)
# ═══════════════════════════════════════════════════════════════════════════

class TelegramBot(threading.Thread):
    def __init__(self, agent: 'LogAgent'):
        super().__init__(daemon=True)
        self.agent = agent
        self.offset = 0

    def run(self):
        while self.agent.running:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._handle_update(update)
                    self.offset = update["update_id"] + 1
            except Exception as e:
                logger.error("TG poll error: %s", e)
                time.sleep(10)

    def _get_updates(self) -> list:
        url = TELEGRAM_API_BASE + "/getUpdates"
        payload = {
            "offset": self.offset,
            "timeout": 30,
            "allowed_updates": ["message"],
        }
        try:
            status, resp = http_post(url, {"Content-Type": "application/json"}, payload, timeout=40)
            if status == 200 and resp.get("ok"):
                return resp.get("result", [])
        except Exception:
            pass
        return []

    def _handle_update(self, update: dict):
        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if not text or not chat_id:
            return

        if ALLOWED_CHATS and chat_id not in ALLOWED_CHATS:
            send_telegram(f"⛔ Нет доступа. Ваш chat\\_id: {chat_id}", chat_id)
            return

        audit_log(chat_id, text)

        cmd = text.split()[0].lower().split("@")[0]
        args = text.split()[1:] if len(text.split()) > 1 else []

        handlers = {
            "/start": self._cmd_help,
            "/help": self._cmd_help,
            "/status": self._cmd_status,
            "/health": self._cmd_health,
            "/errors": self._cmd_errors,
            "/analyze": self._cmd_analyze,
            "/fixed": self._cmd_fixed,
            "/resolve": lambda cid: self._cmd_resolve(cid, args),
            "/stats": lambda cid: self._cmd_stats(cid, args),
            "/top_errors": lambda cid: self._cmd_top_errors(cid, args),
            "/top_slow": lambda cid: self._cmd_top_slow(cid, args),
            "/logs": lambda cid: self._cmd_logs(cid, args),
            "/audit": self._cmd_audit,
            "/mute": lambda cid: self._cmd_mute(cid, args),
            "/unmute": self._cmd_unmute,
        }

        handler = handlers.get(cmd)
        if handler:
            try:
                handler(chat_id)
            except Exception as e:
                send_telegram(f"❌ Ошибка: {str(e)[:200]}", chat_id)
        else:
            send_telegram("🤔 Неизвестная команда. /help", chat_id)

    # ── Help ──
    def _cmd_help(self, chat_id: str):
        send_telegram(
            "🤖 *Log Agent v3 — Команды*\n"
            "─" * 28 + "\n\n"
            "*Мониторинг:*\n"
            "/status — статус агента и сервисов\n"
            "/health — полный health-check (сервисы, диск, RAM, DB)\n\n"
            "*Ошибки:*\n"
            "/errors — активные ошибки\n"
            "/analyze — AI-анализ текущих ошибок (Gemini)\n"
            "/resolve N — пометить ошибку #N починенной\n"
            "/fixed — отчёт: починено vs осталось\n\n"
            "*Статистика:*\n"
            "/stats — сводка за 24ч (ошибки, 5xx, slow)\n"
            "/stats 7d — сводка за 7 дней\n"
            "/top\\_errors — топ-5 ошибок по частоте\n"
            "/top\\_slow — топ-5 медленных эндпоинтов\n\n"
            "*Утилиты:*\n"
            "/logs <source> — последние строки лога\n"
            "/audit — лог команд бота\n"
            "/mute 30m — заглушить алерты на 30 минут\n"
            "/unmute — снять mute\n",
            chat_id,
        )

    # ── Status ──
    def _cmd_status(self, chat_id: str):
        stats = self.agent.agent_stats
        started = datetime.fromisoformat(stats["started"])
        uptime_s = (datetime.now() - started).total_seconds()
        days = int(uptime_s // 86400)
        hours = int((uptime_s % 86400) // 3600)
        minutes = int((uptime_s % 3600) // 60)

        active = len(self.agent.tracker.active)
        resolved = len(self.agent.tracker.resolved)

        lines = [
            "🤖 *Log Agent v3*",
            "─" * 28,
            f"⏱ Аптайм: {days}д {hours}ч {minutes}м",
            f"🔄 Циклов: {stats['cycles']}",
            f"🔍 Ошибок: {stats['errors_found']}",
            f"🧠 AI: {stats['ai_calls']}",
            f"📱 TG: {stats['tg_messages']}",
            "",
            f"❌ Активных: *{active}*",
            f"✅ Починено: *{resolved}*",
            "",
        ]

        muted_until = self.agent.muted_until
        if muted_until and datetime.now() < muted_until:
            remaining = int((muted_until - datetime.now()).total_seconds() / 60)
            lines.append(f"🔇 Mute: ещё {remaining} мин")
            lines.append("")

        for svc in ["teaching_panel", "celery", "nginx", "redis-server", "postgresql"]:
            out = _run_cmd(["systemctl", "is-active", svc])
            icon = "✅" if out == "active" else "⚠️"
            lines.append(f"{icon} {svc}")

        send_telegram("\n".join(lines), chat_id)

    # ── Health ──
    def _cmd_health(self, chat_id: str):
        send_telegram("🏥 Проверяю...", chat_id)
        result = run_health_checks()
        send_telegram(result, chat_id)

    # ── Errors ──
    def _cmd_errors(self, chat_id: str):
        tracker = self.agent.tracker
        if not tracker.active:
            send_telegram("✅ Активных ошибок нет!", chat_id)
            return

        lines = [f"❌ *Активные ошибки* ({len(tracker.active)})\n"]
        sorted_errs = sorted(
            tracker.active.values(),
            key=lambda x: x.get("count", 0),
            reverse=True,
        )
        for info in sorted_errs[:20]:
            snip = info.get("snippet", "?")[:100].replace("*", "").replace("`", "'").replace("\n", " ")
            cnt = info.get("count", 1)
            eid = info.get("id", "?")
            src = info.get("source", "?")
            reopened = " 🔄" if info.get("reopened") else ""
            lines.append(f"*#{eid}* [{src}] x{cnt}{reopened}\n{snip}\n")

        lines.append("/resolve <id> — пометить починенной")
        send_telegram("\n".join(lines), chat_id)

    # ── Analyze ──
    def _cmd_analyze(self, chat_id: str):
        send_telegram("🔍 AI-анализ...", chat_id)

        all_errors = []
        for source, filepath in LOG_FILES.items():
            if not os.path.exists(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(0, 2)
                    f.seek(max(0, f.tell() - 50000))
                    for line in f:
                        if is_error_line(line.rstrip()):
                            all_errors.append({
                                "source": source,
                                "text": line.rstrip()[:300],
                                "timestamp": datetime.now().isoformat(),
                                "fingerprint": line_fingerprint(line),
                            })
            except Exception:
                pass

        if not all_errors:
            send_telegram("✅ Ошибок в логах не найдено!", chat_id)
            return

        seen = set()
        unique = []
        for err in all_errors:
            if err["fingerprint"] not in seen:
                seen.add(err["fingerprint"])
                unique.append(err)

        send_telegram(f"Найдено {len(all_errors)} ({len(unique)} уникальных). AI анализ...", chat_id)

        enrich_errors_with_user_info(unique)
        analysis = analyze_with_ai(unique[:MAX_BATCH_SIZE])
        if analysis:
            send_telegram(f"🧠 *AI-анализ* ({len(unique)} ошибок)\n{'─' * 28}\n{analysis}", chat_id)
            self.agent.agent_stats["ai_calls"] += 1
        else:
            send_telegram("❌ AI-анализ недоступен (проверь GEMINI\\_API\\_KEY).", chat_id)

    # ── Fixed ──
    def _cmd_fixed(self, chat_id: str):
        send_telegram(self.agent.tracker.get_report(), chat_id)

    # ── Resolve ──
    def _cmd_resolve(self, chat_id: str, args: list):
        if not args:
            send_telegram("Использование: /resolve <id>", chat_id)
            return
        try:
            error_id = int(args[0])
        except ValueError:
            send_telegram("❌ ID = число. /resolve 5", chat_id)
            return

        snippet = self.agent.tracker.resolve_by_id(error_id)
        if snippet:
            send_telegram(f"✅ #{error_id} — *починена!*\n{snippet[:100]}", chat_id)
        else:
            send_telegram(f"❌ #{error_id} не найдена. /errors", chat_id)

    # ── Stats ──
    def _cmd_stats(self, chat_id: str, args: list):
        hours = 24
        if args:
            raw = args[0].lower().rstrip("hd")
            try:
                if "d" in args[0].lower():
                    hours = int(raw) * 24
                else:
                    hours = int(raw)
            except ValueError:
                pass
        send_telegram(self.agent.error_stats.get_summary(hours), chat_id)

    # ── Top Errors ──
    def _cmd_top_errors(self, chat_id: str, args: list):
        hours = 24
        if args:
            try:
                raw = args[0].lower().rstrip("hd")
                if "d" in args[0].lower():
                    hours = int(raw) * 24
                else:
                    hours = int(raw)
            except ValueError:
                pass
        send_telegram(self.agent.error_stats.get_top_errors(hours), chat_id)

    # ── Top Slow ──
    def _cmd_top_slow(self, chat_id: str, args: list):
        hours = 24
        if args:
            try:
                raw = args[0].lower().rstrip("hd")
                if "d" in args[0].lower():
                    hours = int(raw) * 24
                else:
                    hours = int(raw)
            except ValueError:
                pass
        send_telegram(self.agent.error_stats.get_top_slow(hours), chat_id)

    # ── Logs ──
    def _cmd_logs(self, chat_id: str, args: list):
        if not args:
            sources = ", ".join(LOG_FILES.keys())
            send_telegram(f"Использование: /logs <source>\nДоступные: {sources}", chat_id)
            return

        source = args[0].lower()
        filepath = LOG_FILES.get(source)
        if not filepath or not os.path.exists(filepath):
            send_telegram(f"❌ Источник не найден: {source}", chat_id)
            return

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 5000))
                tail = f.read()

            tail_lines = tail.strip().split("\n")[-20:]
            text_out = "\n".join(tail_lines)
            if len(text_out) > 3500:
                text_out = text_out[-3500:]

            send_telegram(f"📄 *{source}*\n```\n{text_out}\n```", chat_id)
        except Exception as e:
            send_telegram(f"❌ Ошибка: {e}", chat_id)

    # ── Audit ──
    def _cmd_audit(self, chat_id: str):
        if not os.path.exists(AUDIT_FILE):
            send_telegram("Аудит-лог пуст.", chat_id)
            return
        try:
            with open(AUDIT_FILE, "r") as f:
                lines = f.readlines()
            last = lines[-20:] if len(lines) > 20 else lines
            send_telegram(f"📋 *Аудит* (посл. {len(last)})\n```\n{''.join(last)}```", chat_id)
        except Exception as e:
            send_telegram(f"❌ {e}", chat_id)

    # ── Mute/Unmute ──
    def _cmd_mute(self, chat_id: str, args: list):
        minutes = 30
        if args:
            raw = args[0].lower().rstrip("mh")
            try:
                if "h" in args[0].lower():
                    minutes = int(raw) * 60
                else:
                    minutes = int(raw)
            except ValueError:
                pass

        self.agent.muted_until = datetime.now() + timedelta(minutes=minutes)
        send_telegram(f"🔇 Алерты заглушены на {minutes} мин.", chat_id)

    def _cmd_unmute(self, chat_id: str):
        self.agent.muted_until = None
        send_telegram("🔊 Mute снят. Алерты включены.", chat_id)


# ═══════════════════════════════════════════════════════════════════════════
# SCHEDULED REPORTS (Module 5)
# ═══════════════════════════════════════════════════════════════════════════

class ScheduledReports(threading.Thread):
    def __init__(self, agent: 'LogAgent'):
        super().__init__(daemon=True)
        self.agent = agent
        self.last_daily: Optional[datetime] = None
        self.last_6h: Optional[datetime] = None
        self.last_weekly: Optional[datetime] = None

    def run(self):
        while self.agent.running:
            try:
                now = datetime.now()
                self._check_6h_report(now)
                self._check_daily_report(now)
                self._check_weekly_report(now)

                # Auto-resolve stale errors every 6h
                if now.hour in (3, 9, 15, 21) and now.minute < 6:
                    cnt = self.agent.tracker.auto_resolve_stale(hours=24)
                    if cnt:
                        send_telegram(
                            f"🔄 Авто-резолв: {cnt} ошибок не повторялись >24ч"
                        )
                    # Save stats
                    self.agent.error_stats.save()
            except Exception as e:
                logger.error("Report thread error: %s", e)

            time.sleep(300)  # Check every 5 min

    def _check_6h_report(self, now: datetime):
        """Mini report every 6 hours — ONLY if there are errors."""
        if now.hour not in (0, 6, 12, 18) or now.minute >= 10:
            return
        if self.last_6h and (now - self.last_6h).total_seconds() < 18000:
            return
        self.last_6h = now

        stats = self.agent.error_stats
        # Count errors in last 6h
        cutoff = (now - timedelta(hours=6)).isoformat()
        recent = [e for e in stats.recent_errors if e["ts"] >= cutoff]

        if not recent:
            return  # QUIET: no errors — no noise

        active = len(self.agent.tracker.active)
        msg = (
            f"📊 *Мини-отчёт ({now.strftime('%H:%M')})*\n"
            f"─" + "─" * 27 + "\n"
            f"🔴 Ошибок за 6ч: *{len(recent)}*\n"
            f"❌ Активных: *{active}*\n"
        )

        # Top error
        from collections import Counter
        fps = Counter(e["fp"] for e in recent)
        if fps:
            top_fp, top_cnt = fps.most_common(1)[0]
            for e in recent:
                if e["fp"] == top_fp:
                    msg += f"\nТоп: x{top_cnt} [{e['source']}]\n{e['text'][:100]}"
                    break

        send_telegram(msg)

    def _check_daily_report(self, now: datetime):
        """Full daily report at 09:00 — always sends."""
        if now.hour != 9 or now.minute >= 10:
            return
        if self.last_daily and self.last_daily.date() == now.date():
            return
        self.last_daily = now

        stats = self.agent.agent_stats
        tracker = self.agent.tracker
        error_stats = self.agent.error_stats
        uptime = now - datetime.fromisoformat(stats["started"])

        # Error trend: today vs yesterday
        today_cutoff = now.replace(hour=0, minute=0, second=0).isoformat()
        yesterday_cutoff = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
        today_errs = sum(1 for e in error_stats.recent_errors if e["ts"] >= today_cutoff)
        yesterday_errs = sum(
            1 for e in error_stats.recent_errors
            if yesterday_cutoff <= e["ts"] < today_cutoff
        )

        trend = ""
        if yesterday_errs > 0:
            diff = today_errs - yesterday_errs
            if diff > 0:
                trend = f"📈 +{diff} vs вчера"
            elif diff < 0:
                trend = f"📉 {diff} vs вчера"
            else:
                trend = "➡️ без изменений"

        msg = (
            f"📋 *Ежедневный отчёт*\n"
            f"📅 {now.strftime('%Y-%m-%d')}\n"
            f"{'─' * 28}\n"
            f"⏱ Аптайм: {uptime.days}д {uptime.seconds // 3600}ч\n"
            f"🔄 Циклов: {stats['cycles']}\n"
            f"🔍 Ошибок за 24ч: *{today_errs}* {trend}\n"
            f"🧠 AI-вызовов: {stats['ai_calls']}\n"
            f"\n"
            f"❌ Активных: *{len(tracker.active)}*\n"
            f"✅ Починено: *{len(tracker.resolved)}*\n"
        )

        if tracker.active:
            msg += "\n*Топ ошибки:*\n"
            top = sorted(
                tracker.active.values(),
                key=lambda x: x.get("count", 0),
                reverse=True,
            )[:5]
            for info in top:
                snip = info.get("snippet", "?")[:60].replace("*", "")
                msg += f"  #{info.get('id', '?')} x{info.get('count', 0)} — {snip}\n"

        send_telegram(msg)

    def _check_weekly_report(self, now: datetime):
        """Weekly report on Monday at 10:00."""
        if now.weekday() != 0 or now.hour != 10 or now.minute >= 10:
            return
        if self.last_weekly and (now - self.last_weekly).days < 6:
            return
        self.last_weekly = now

        error_stats = self.agent.error_stats
        tracker = self.agent.tracker

        # 7d vs previous 7d
        week_cutoff = (now - timedelta(days=7)).isoformat()
        prev_week_cutoff = (now - timedelta(days=14)).isoformat()

        this_week = sum(1 for e in error_stats.recent_errors if e["ts"] >= week_cutoff)

        # Hourly counts for trend
        hourly = error_stats.hourly_counts
        week_hours = sorted([
            (k, v) for k, v in hourly.items()
            if k >= (now - timedelta(days=7)).strftime("%Y-%m-%d-%H")
        ])

        # Find peak hour
        peak_hour = ""
        peak_count = 0
        for h, c in week_hours:
            if c > peak_count:
                peak_count = c
                peak_hour = h

        msg = (
            f"📊 *Недельный отчёт*\n"
            f"📅 {(now - timedelta(days=7)).strftime('%d.%m')} — {now.strftime('%d.%m.%Y')}\n"
            f"{'─' * 28}\n"
            f"🔴 Ошибок за неделю: *{this_week}*\n"
            f"❌ Активных: *{len(tracker.active)}*\n"
            f"✅ Починено всего: *{len(tracker.resolved)}*\n"
        )

        if peak_hour:
            msg += f"\n📈 Пиковый час: {peak_hour} ({peak_count} ошибок)"

        # Top 5 errors of the week
        week_errors = [e for e in error_stats.recent_errors if e["ts"] >= week_cutoff]
        if week_errors:
            from collections import Counter
            fps = Counter(e["fp"] for e in week_errors)
            msg += "\n\n*Топ-5 за неделю:*"
            for i, (fp, cnt) in enumerate(fps.most_common(5), 1):
                for e in week_errors:
                    if e["fp"] == fp:
                        text = e["text"][:80].replace("*", "").replace("`", "'")
                        msg += f"\n{i}. x{cnt} [{e['source']}] {text}"
                        break

        send_telegram(msg)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN AGENT
# ═══════════════════════════════════════════════════════════════════════════

class LogAgent:
    def __init__(self):
        self.state = FileState()
        self.tracker = ErrorTracker()
        self.error_stats = ErrorStats()
        self.collector = LogCollector(self.state, self.tracker, self.error_stats)
        self.system_monitor = SystemMonitor()
        self.security_monitor = SecurityMonitor()
        self.running = True
        self.muted_until: Optional[datetime] = None
        self.agent_stats = {
            "started": datetime.now().isoformat(),
            "cycles": 0,
            "errors_found": 0,
            "ai_calls": 0,
            "tg_messages": 0,
        }

    def stop(self, *args):
        self.running = False

    def is_muted(self) -> bool:
        if self.muted_until and datetime.now() < self.muted_until:
            return True
        return False

    def run(self):
        # Seek to end of all log files (don't process old logs)
        for source, filepath in LOG_FILES.items():
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                self.state.set_pos(filepath, size)
        self.state.save()

        # Startup message (minimal, one-time)
        send_telegram(
            f"🤖 *Log Agent v3 запущен*\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"📄 Логов: {sum(1 for f in LOG_FILES.values() if os.path.exists(f))}\n"
            f"AI: {'Gemini ✅' if GEMINI_API_KEY else '❌'}\n"
            f"/help — команды"
        )

        while self.running:
            try:
                self._cycle()
            except Exception as e:
                logger.error("Cycle error: %s", e, exc_info=True)

            for _ in range(BATCH_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)

    def _cycle(self):
        self.agent_stats["cycles"] += 1

        # 1. Collect errors from logs
        errors = self.collector.collect_errors()

        # 2. Proactive system checks (every cycle, but with cooldowns inside)
        if not self.is_muted():
            system_alerts = self.system_monitor.check_all()
            for alert in system_alerts:
                send_telegram(alert)
                self.agent_stats["tg_messages"] += 1

            # Spike detection
            spike = self.system_monitor.check_error_spike(self.error_stats)
            if spike:
                send_telegram(spike)
                self.agent_stats["tg_messages"] += 1

            # Security: new admins
            admin_alert = self.security_monitor.check_new_admins()
            if admin_alert:
                send_telegram(admin_alert)
                self.agent_stats["tg_messages"] += 1

        if not errors:
            return  # QUIET: no errors — no messages

        self.agent_stats["errors_found"] += len(errors)
        deduped = self.collector.deduped_count

        if self.is_muted():
            return  # Muted — don't send error alerts

        # 3. Enrich with user context
        enrich_errors_with_user_info(errors)

        # 4. Send raw error alert
        if send_error_alert(errors, deduped_count=deduped):
            self.agent_stats["tg_messages"] += 1

        # 5. AI analysis (only for batches with 3+ errors to save tokens)
        if GEMINI_API_KEY and len(errors) >= 3:
            try:
                analysis = analyze_with_ai(errors)
                if analysis:
                    self.agent_stats["ai_calls"] += 1
                    send_telegram(f"🧠 *AI-анализ* ({len(errors)} ошибок)\n{'─' * 28}\n{analysis}")
                    self.agent_stats["tg_messages"] += 1
            except Exception as e:
                logger.error("AI analysis failed: %s", e)

    def test_connections(self):
        """Test all connections (--test flag)."""
        print("=" * 50)
        print("🧪 Log Agent v3 — Connection Test")
        print("=" * 50)

        print("\n📄 Log files:")
        for source, filepath in LOG_FILES.items():
            exists = os.path.exists(filepath)
            size = os.path.getsize(filepath) if exists else 0
            status = f"✅ {_fmt_size(size)}" if exists else "❌ not found"
            print(f"  {source:20s} {status}")

        print(f"\n🧠 Gemini AI ({GEMINI_MODEL}):")
        if not GEMINI_API_KEY:
            print("  ❌ GEMINI_API_KEY not set")
        else:
            print(f"  Key: {GEMINI_API_KEY[:8]}...{GEMINI_API_KEY[-4:]}")
            try:
                result = analyze_with_ai([{
                    "source": "test", "text": "Test error: connection timeout",
                    "timestamp": "now", "fingerprint": "test",
                }])
                print(f"  ✅ OK ({len(result)} chars)" if result else "  ❌ No response")
            except Exception as e:
                print(f"  ❌ {e}")

        print("\n📱 Telegram:")
        if not TELEGRAM_BOT_TOKEN:
            print("  ❌ LOG_AGENT_TG_TOKEN not set")
        elif not TELEGRAM_CHAT_ID:
            print("  ❌ LOG_AGENT_TG_CHAT not set")
        else:
            print(f"  Token: {TELEGRAM_BOT_TOKEN[:8]}...")
            print(f"  Chat: {TELEGRAM_CHAT_ID}")
            ok = send_telegram("🧪 Log Agent v3 — тест пройден!")
            print(f"  {'✅ Sent' if ok else '❌ Failed'}")

        print(f"\n📊 Tracker: active={len(self.tracker.active)} resolved={len(self.tracker.resolved)}")
        print("=" * 50)


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Log Agent v3 — Production Monitor")
    parser.add_argument("--test", action="store_true", help="Test connections")
    parser.add_argument("--analyze-last", type=int, nargs="?", const=60,
                        help="Analyze last N minutes of logs")
    args = parser.parse_args()

    agent = LogAgent()

    if args.test:
        agent.test_connections()
        return

    if args.analyze_last:
        send_telegram("🔍 CLI анализ...")
        all_errors = []
        for source, filepath in LOG_FILES.items():
            if not os.path.exists(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(0, 2)
                    f.seek(max(0, f.tell() - 50000))
                    for line in f:
                        if is_error_line(line.rstrip()):
                            all_errors.append({
                                "source": source,
                                "text": line.rstrip()[:300],
                                "timestamp": datetime.now().isoformat(),
                                "fingerprint": line_fingerprint(line),
                            })
            except Exception:
                pass

        seen = set()
        unique = [e for e in all_errors if e["fingerprint"] not in seen and not seen.add(e["fingerprint"])]
        print(f"Found {len(all_errors)} errors ({len(unique)} unique)")

        enrich_errors_with_user_info(unique)
        analysis = analyze_with_ai(unique[:MAX_BATCH_SIZE])
        if analysis:
            print(analysis)
            send_telegram(f"🧠 *AI-анализ* ({len(unique)} ошибок)\n{'─' * 28}\n{analysis}")
        return

    # Signal handlers
    signal.signal(signal.SIGTERM, agent.stop)
    signal.signal(signal.SIGINT, agent.stop)

    # Background threads
    TelegramBot(agent).start()
    ScheduledReports(agent).start()

    # Main loop
    agent.run()


if __name__ == "__main__":
    main()
