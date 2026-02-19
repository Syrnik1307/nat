#!/usr/bin/env python3
"""
AI Log Agent v2 — мониторинг логов + Telegram-бот с интерактивными командами.

Что делает:
  - Следит за лог-файлами продакшена (Django, Gunicorn, Celery, Nginx)
  - Группирует / дедуплицирует ошибки
  - Отправляет батчи на AI-анализ (DeepSeek)
  - Шлёт рекомендации в Telegram
  - Принимает команды через Telegram-бота
  - Ведёт трекер ошибок: какие починены, какие остаются

Команды Telegram:
  /status    — статус агента и сервисов
  /errors    — текущие активные ошибки
  /analyze   — прогнать AI-анализ логов прямо сейчас
  /tests     — запустить health-check + smoke-тесты
  /fixed     — отчёт: починено vs осталось
  /resolve N — отметить ошибку #N как починенную
  /health    — health-check (сервисы, диск, RAM, БД)
  /logs src  — последние 20 строк из лога
  /help      — справка

Переменные окружения:
  DEEPSEEK_API_KEY    — API ключ DeepSeek (обязательно)
  LOG_AGENT_TG_TOKEN  — Telegram Bot Token (обязательно)
  LOG_AGENT_TG_CHAT   — Telegram Chat ID для уведомлений (обязательно)
  LOG_AGENT_INTERVAL  — Интервал анализа в секундах (по умолчанию 60)
  LOG_AGENT_MODEL     — Модель DeepSeek (по умолчанию deepseek-chat)
"""

import os
import sys
import re
import json
import time
import signal
import hashlib
import logging
import argparse
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = os.environ.get("LOG_AGENT_MODEL", "deepseek-chat")

TELEGRAM_BOT_TOKEN = os.environ.get("LOG_AGENT_TG_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("LOG_AGENT_TG_CHAT", "")

# Кто может слать команды (chat_id). Пустой = только LOG_AGENT_TG_CHAT
ALLOWED_CHATS = set(
    filter(None, os.environ.get("LOG_AGENT_ALLOWED_CHATS", "").split(","))
)
if TELEGRAM_CHAT_ID:
    ALLOWED_CHATS.add(TELEGRAM_CHAT_ID)

# Интервал группировки ошибок (секунды)
BATCH_INTERVAL = int(os.environ.get("LOG_AGENT_INTERVAL", "60"))

# Макс. кол-во ошибок в одном батче для AI
MAX_BATCH_SIZE = 30

# Дедупликация — не слать одинаковые ошибки чаще чем раз в N минут
DEDUP_WINDOW_MINUTES = int(os.environ.get("LOG_AGENT_DEDUP_MINUTES", "5"))

# Пути к лог-файлам
LOG_FILES = {
    "django": "/var/www/teaching_panel/teaching_panel/logs/django.log",
    "requests": "/var/www/teaching_panel/teaching_panel/logs/requests.log",
    "frontend": "/var/www/teaching_panel/teaching_panel/logs/frontend_errors.log",
    "gunicorn_error": "/var/log/teaching_panel/error.log",
    "gunicorn_access": "/var/log/teaching_panel/access.log",
    "celery": "/var/log/teaching_panel/celery.log",
    "celery_beat": "/var/log/teaching_panel/celery_beat.log",
    "nginx_error": "/var/log/nginx/teaching_panel_error.log",
    "nginx_access": "/var/log/nginx/teaching_panel_access.log",
}

# Файл для хранения состояния (позиции чтения)
STATE_FILE = "/var/www/teaching_panel/teaching_panel/logs/log_agent_state.json"
TRACKER_FILE = "/var/www/teaching_panel/teaching_panel/logs/error_tracker.json"
AGENT_LOG = "/var/log/teaching_panel/log_agent.log"

PROJECT_DIR = "/var/www/teaching_panel"
MANAGE_PY = os.path.join(PROJECT_DIR, "teaching_panel", "manage.py")
PYTHON_BIN = os.path.join(PROJECT_DIR, "venv", "bin", "python")

# ---------------------------------------------------------------------------
# Логирование агента
# ---------------------------------------------------------------------------

import logging.handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# Добавляем файловый хендлер если возможно
try:
    os.makedirs(os.path.dirname(AGENT_LOG), exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        AGENT_LOG, maxBytes=10 * 1024 * 1024, backupCount=3
    )
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(fh)
except Exception:
    pass

logger = logging.getLogger("log_agent")

# ---------------------------------------------------------------------------
# HTTP-клиент (requests или urllib)
# ---------------------------------------------------------------------------

try:
    import requests as _requests

    def http_post(url, headers, json_data, timeout=30):
        r = _requests.post(url, headers=headers, json=json_data, timeout=timeout)
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

    def http_get(url, timeout=10):
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()


# ---------------------------------------------------------------------------
# Паттерны ошибок
# ---------------------------------------------------------------------------

ERROR_PATTERNS = [
    # Python/Django errors
    re.compile(r"(ERROR|CRITICAL|Traceback|Exception|Error:)", re.IGNORECASE),
    # Gunicorn errors
    re.compile(r"\[ERROR\]|\[CRITICAL\]|worker timeout|Boot failed", re.IGNORECASE),
    # Nginx errors
    re.compile(
        r"(\[error\]|\[crit\]|\[alert\]|\[emerg\]|upstream timed out|"
        r"connect\(\) failed|no live upstreams|502|503|504)",
        re.IGNORECASE,
    ),
    # Celery errors
    re.compile(
        r"(Task .+ raised|WorkerLostError|Restoring .+ unacknowledged|"
        r"connection reset|broker .+ lost)",
        re.IGNORECASE,
    ),
    # HTTP 5xx в access-логах
    re.compile(r'" (5\d{2}) '),
    # HTTP 403 Forbidden в access-логах (ошибки доступа у пользователей)
    re.compile(r'" (403) '),
    # Медленные запросы (из RequestMetricsMiddleware >2s)
    # NB: НЕ включаем duration=... — он матчит любой запрос с ≥2 знаками после точки.
    # SLOW_REQUEST уже логируется middleware для запросов >2s.
    re.compile(r"SLOW[_ ]REQUEST|took \d{4,}ms", re.IGNORECASE),
    # OOM / ресурсы
    re.compile(r"(MemoryError|out of memory|killed process|OOM)", re.IGNORECASE),
    # Disk
    re.compile(r"(No space left on device|disk full|IOError)", re.IGNORECASE),
    # Database
    re.compile(
        r"(OperationalError|IntegrityError|connection refused|"
        r"too many connections|deadlock)",
        re.IGNORECASE,
    ),
]

# Паттерны для игнорирования (шум)
IGNORE_PATTERNS = [
    re.compile(r"GET /health"),
    re.compile(r"GET /favicon\.ico"),
    re.compile(r"kube-probe|health_?check", re.IGNORECASE),
    re.compile(r"ELB-HealthChecker"),
    # Успешные request-metrics строки (status 1xx/2xx/3xx) — не ошибки
    re.compile(r"status=[123]\d{2}\b"),
    # Сканеры
    re.compile(r"\.php|wp-login|xmlrpc|\.env|\.git", re.IGNORECASE),
    # Легитимные 403 от JWT refresh (просроченный токен — норма)
    re.compile(r"jwt/verify.*403|jwt/logout.*40[01]", re.IGNORECASE),
    # DisallowedHost — сканеры с левым Host
    re.compile(r"DisallowedHost", re.IGNORECASE),
]


def is_error_line(line: str) -> bool:
    """Проверяет, содержит ли строка паттерн ошибки."""
    # Сначала проверим ignore
    for pat in IGNORE_PATTERNS:
        if pat.search(line):
            return False
    for pat in ERROR_PATTERNS:
        if pat.search(line):
            return True
    return False


def line_fingerprint(line: str) -> str:
    """Создаёт fingerprint для дедупликации (убираем timestamps и числа)."""
    # Убираем timestamp
    cleaned = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\.\d]*", "", line)
    # Убираем IP-адреса
    cleaned = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "IP", cleaned)
    # Убираем числа (ID, порты, etc)
    cleaned = re.sub(r"\b\d{4,}\b", "N", cleaned)
    return hashlib.md5(cleaned.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Error Tracker — отслеживание починенных / активных ошибок
# ---------------------------------------------------------------------------


class ErrorTracker:
    """
    Хранит историю ошибок:
      - active:   {fingerprint: {first_seen, last_seen, count, source, snippet, id}}
      - resolved: {fingerprint: {resolved_at, snippet, source, id}}
    """

    def __init__(self, path=TRACKER_FILE):
        self.path = path
        self.active = {}      # type: Dict[str, dict]
        self.resolved = {}    # type: Dict[str, dict]
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

    def record_error(self, fingerprint, source, snippet):
        """Записывает ошибку. Возвращает ID."""
        if fingerprint in self.resolved:
            # Ошибка вернулась — переоткрываем
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

    def resolve_by_id(self, error_id):
        """Отмечает ошибку как починенную по ID. Возвращает snippet или None."""
        for fp, info in list(self.active.items()):
            if info.get("id") == error_id:
                info["resolved_at"] = datetime.now().isoformat()
                self.resolved[fp] = info
                del self.active[fp]
                self.save()
                return info.get("snippet", "?")
        return None

    def auto_resolve_stale(self, hours=24):
        """Автоматически резолвит ошибки, которые не повторялись > N часов."""
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

    def get_report(self):
        """Формирует отчёт: починено vs осталось."""
        active_count = len(self.active)
        resolved_count = len(self.resolved)
        total = active_count + resolved_count

        lines = []
        lines.append("📊 *Трекер ошибок*")
        lines.append("─" * 28)

        if total == 0:
            lines.append("Ошибок пока не зафиксировано.")
            return "\n".join(lines)

        pct = int(resolved_count / total * 100) if total > 0 else 0
        bar_len = 20
        filled = int(bar_len * pct / 100)
        bar = "▓" * filled + "░" * (bar_len - filled)

        lines.append(
            "✅ Починено: *%d*  |  ❌ Активных: *%d*  |  Всего: *%d*"
            % (resolved_count, active_count, total)
        )
        lines.append("[%s] %d%%" % (bar, pct))
        lines.append("")

        if self.active:
            lines.append("*Активные ошибки:*")
            sorted_active = sorted(
                self.active.values(), key=lambda x: x.get("count", 0), reverse=True
            )
            for info in sorted_active[:15]:
                snip = info.get("snippet", "?")[:80].replace("*", "").replace("`", "'")
                cnt = info.get("count", 1)
                eid = info.get("id", "?")
                reopened = " 🔄" if info.get("reopened") else ""
                lines.append(
                    "  #%s [%s] x%d%s\n   %s" % (eid, info.get("source", "?"), cnt, reopened, snip)
                )
            if len(sorted_active) > 15:
                lines.append("  ...и ещё %d" % (len(sorted_active) - 15))

        if self.resolved:
            lines.append("")
            lines.append("*Последние починенные:*")
            sorted_resolved = sorted(
                self.resolved.values(),
                key=lambda x: x.get("resolved_at", ""),
                reverse=True,
            )
            for info in sorted_resolved[:5]:
                snip = info.get("snippet", "?")[:60].replace("*", "").replace("`", "'")
                auto = " (авто)" if info.get("auto_resolved") else ""
                lines.append("  ✅ #%s%s — %s" % (info.get("id", "?"), auto, snip))

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Состояние — запоминаем позицию чтения каждого файла
# ---------------------------------------------------------------------------


class FileState:
    """Хранит позиции чтения лог-файлов между перезапусками."""

    def __init__(self, path=STATE_FILE):
        self.path = path
        self.positions = {}  # {filepath: {"pos": int, "inode": int}}
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as f:
                    self.positions = json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить state: {e}")
            self.positions = {}

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.positions, f, indent=2)
        except Exception as e:
            logger.warning(f"Не удалось сохранить state: {e}")

    def get_pos(self, filepath: str) -> int:
        info = self.positions.get(filepath, {})
        # Проверяем inode - если файл пересоздан (logrotate), начинаем сначала
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


# ---------------------------------------------------------------------------
# Сборщик ошибок из лог-файлов
# ---------------------------------------------------------------------------


class LogCollector:
    """Читает новые строки из лог-файлов, фильтрует ошибки."""

    def __init__(self, state, tracker):
        self.state = state
        self.tracker = tracker
        self.dedup_cache = {}  # type: Dict[str, datetime]
        self.deduped_count = 0  # сколько ошибок подавлено дедупликацией за цикл

    def collect_errors(self) -> List[dict]:
        """Собирает новые ошибки из всех лог-файлов."""
        all_errors = []
        self.deduped_count = 0
        now = datetime.now()

        # Чистим устаревшие записи дедупликации
        cutoff = now - timedelta(minutes=DEDUP_WINDOW_MINUTES)
        self.dedup_cache = {
            k: v for k, v in self.dedup_cache.items() if v > cutoff
        }

        for source, filepath in LOG_FILES.items():
            if not os.path.exists(filepath):
                continue

            try:
                errors = self._read_new_errors(source, filepath, now)
                all_errors.extend(errors)
            except Exception as e:
                logger.error(f"Ошибка чтения {filepath}: {e}")

        self.state.save()
        return all_errors[:MAX_BATCH_SIZE]

    def _read_new_errors(
        self, source: str, filepath: str, now: datetime
    ) -> List[dict]:
        errors = []
        pos = self.state.get_pos(filepath)

        try:
            file_size = os.path.getsize(filepath)
        except OSError:
            return errors

        # Если файл стал меньше (truncated/rotated), начинаем сначала
        if pos > file_size:
            pos = 0

        if pos >= file_size:
            return errors  # Нет новых данных

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            f.seek(pos)
            lines = f.readlines()
            new_pos = f.tell()

        # Группируем многострочные ошибки (traceback)
        error_buffer = []
        in_traceback = False

        for line in lines:
            line = line.rstrip("\n")
            if not line:
                continue

            # Начало трейсбека
            if "Traceback (most recent call last)" in line:
                if error_buffer:
                    self._flush_error(errors, source, error_buffer, now)
                error_buffer = [line]
                in_traceback = True
                continue

            # Продолжение трейсбека
            if in_traceback:
                error_buffer.append(line)
                # Конец трейсбека — строка с именем исключения
                if (
                    line
                    and not line.startswith(" ")
                    and not line.startswith("\t")
                    and ":" in line
                    and not line.startswith("Traceback")
                    and not line.startswith("  ")
                ):
                    self._flush_error(errors, source, error_buffer, now)
                    error_buffer = []
                    in_traceback = False
                continue

            # Обычная ошибочная строка
            if is_error_line(line):
                self._flush_error(errors, source, [line], now)

        # Флашим буфер если остался незакрытый трейсбек
        if error_buffer:
            self._flush_error(errors, source, error_buffer, now)

        self.state.set_pos(filepath, new_pos)
        return errors

    def _flush_error(
        self, errors: list, source: str, lines: List[str], now: datetime
    ):
        text = "\n".join(lines[-20:])  # Ограничиваем 20 строк на ошибку
        fp = line_fingerprint(text)

        # Запись в трекер (всегда)
        self.tracker.record_error(fp, source, text)

        # Дедупликация для AI-батча
        if fp in self.dedup_cache:
            self.deduped_count += 1
            return
        self.dedup_cache[fp] = now

        errors.append(
            {
                "source": source,
                "text": text,
                "timestamp": now.isoformat(),
                "fingerprint": fp,
            }
        )


# ---------------------------------------------------------------------------
# Обогащение ошибок информацией о пользователе из requests.log
# ---------------------------------------------------------------------------

_REQUESTS_LOG = LOG_FILES.get("requests", "")


def _parse_request_log_line(line):
    """Парсит строку из requests.log: method=GET path=/api/... status=500 duration=0.1s user=20 ip=1.2.3.4"""
    m = re.search(
        r"method=(\S+)\s+path=(\S+)\s+status=(\d+)\s+duration=(\S+)\s+user=(\S+)\s+ip=(\S+)",
        line,
    )
    if not m:
        return None
    return {
        "method": m.group(1),
        "path": m.group(2),
        "status": int(m.group(3)),
        "duration": m.group(4),
        "user": m.group(5),
        "ip": m.group(6),
    }


def _get_recent_request_context(seconds=120):
    """Читает последние N секунд requests.log и возвращает 4xx/5xx запросы с user info."""
    if not _REQUESTS_LOG or not os.path.exists(_REQUESTS_LOG):
        return []

    results = []
    try:
        with open(_REQUESTS_LOG, "r", encoding="utf-8", errors="replace") as f:
            # Читаем последние ~50KB
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 50000))
            for raw_line in f:
                line = raw_line.rstrip()
                if not line:
                    continue
                parsed = _parse_request_log_line(line)
                if parsed and parsed["status"] >= 400:
                    results.append(parsed)
    except Exception as e:
        logger.debug("Cannot read requests.log for user context: %s", e)

    return results[-100:]  # Берём последние 100 записей


def enrich_errors_with_user_info(errors):
    """Обогащает ошибки информацией о пользователе, сопоставляя с requests.log."""
    if not errors:
        return

    recent_requests = _get_recent_request_context()
    if not recent_requests:
        return

    for err in errors:
        # Ищем совпадение по path из текста ошибки или по статусу
        err_text = err.get("text", "")

        # Извлекаем path из текста ошибки (если есть)
        path_match = re.search(r'path=(/\S+)', err_text)
        status_match = re.search(r'status=(\d+)', err_text)

        # Ищем user= и ip= прямо в тексте ошибки (из requests.log)
        user_in_text = re.search(r'user=(\S+)', err_text)
        ip_in_text = re.search(r'ip=(\S+)', err_text)

        if user_in_text:
            err["user_id"] = user_in_text.group(1)
        if ip_in_text:
            err["user_ip"] = ip_in_text.group(1)

        # Если user не найден в тексте — ищем в requests.log по path и времени
        if "user_id" not in err and path_match:
            err_path = path_match.group(1)
            for req in reversed(recent_requests):
                if req["path"] == err_path:
                    err["user_id"] = req["user"]
                    err["user_ip"] = req["ip"]
                    err["request_method"] = req["method"]
                    err["request_path"] = req["path"]
                    err["request_status"] = req["status"]
                    break

        # Если user всё ещё не найден — ищем по 5xx статусу
        if "user_id" not in err and err.get("source") in ("django", "gunicorn_error"):
            for req in reversed(recent_requests):
                if req["status"] >= 500:
                    err["user_id"] = req["user"]
                    err["user_ip"] = req["ip"]
                    err["request_method"] = req["method"]
                    err["request_path"] = req["path"]
                    err["request_status"] = req["status"]
                    break

        # Для frontend ошибок — user info уже в payload
        if err.get("source") == "frontend":
            fe_user = re.search(r'user_id[=:](\S+)', err_text)
            if fe_user:
                err["user_id"] = fe_user.group(1)


# ---------------------------------------------------------------------------
# DeepSeek AI Analyzer
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Ты — опытный DevOps/SRE-инженер, анализирующий логи production Django+Gunicorn+Celery+Nginx+PostgreSQL приложения LectioSpace (платформа обучения — учителя, студенты, расписание, ДЗ).

Стек: Django 4.2, DRF, Gunicorn (gthread), Celery + Redis, Nginx, PostgreSQL, React frontend.
Сервер: Ubuntu, systemd. Домены: lectiospace.ru, olga.lectiospace.ru.

При анализе ошибок ОБЯЗАТЕЛЬНО:

1. 👤 КТО: Укажи пользователя — user ID, IP, роль (student/teacher/admin) если есть в логах. Если user=anonymous — так и пиши.

2. 📍 ГДЕ: Какая страница/API endpoint (path=...) и какой модуль/компонент.

3. 📖 СЦЕНАРИЙ: Опиши пошагово что делал пользователь и что пошло не так. Например:
   «Студент с ID 20 зашёл на страницу ДЗ (/student/homework/5), нажал кнопку отправки, но сервер вернул 500 из-за ошибки валидации в HomeworkSerializer».

4. 🔴 КРИТИЧНОСТЬ: 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low

5. 🔍 ПРИЧИНА: Техническая причина (1-2 предложения)

6. 🛠 РЕШЕНИЕ: Конкретные команды или код для исправления

7. ⚡ ВЛИЯНИЕ: Кого затрагивает — одного юзера, всех студентов, всех, или только при определённых условиях.

Формат ответа — Markdown, компактно. Не повторяй сами логи целиком. Пиши на русском.
Группируй связанные ошибки. Если одна и та же ошибка повторяется — укажи сколько раз.
Если ошибка от фронтенда (source=frontend) — опиши какой UI компонент сломался и что видит пользователь."""


def analyze_with_ai(errors: List[dict]) -> Optional[str]:
    """Отправляет батч ошибок в DeepSeek и возвращает анализ."""
    if not DEEPSEEK_API_KEY:
        logger.error("DEEPSEEK_API_KEY не задан!")
        return None

    # Формируем сообщение с ошибками
    parts = []
    for i, err in enumerate(errors, 1):
        user_context = ""
        if err.get("user_id"):
            user_context += f" | user={err['user_id']}"
        if err.get("user_ip"):
            user_context += f" ip={err['user_ip']}"
        if err.get("request_path"):
            user_context += f" path={err['request_path']}"
        if err.get("request_method"):
            user_context += f" method={err['request_method']}"
        if err.get("request_status"):
            user_context += f" status={err['request_status']}"
        parts.append(
            f"--- Ошибка #{i} [{err['source']}]{user_context} ---\n{err['text']}"
        )

    user_msg = (
        f"Проанализируй {len(errors)} ошибок из продакшена "
        f"(собраны за последние {BATCH_INTERVAL} секунд):\n\n"
        + "\n\n".join(parts)
    )

    # Ограничиваем размер запроса (~8K chars max)
    if len(user_msg) > 8000:
        user_msg = user_msg[:7900] + "\n\n...(обрезано)"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }

    try:
        status, resp = http_post(DEEPSEEK_API_URL, headers, payload, timeout=60)

        if status == 200:
            return resp["choices"][0]["message"]["content"]
        elif status == 429:
            logger.warning("DeepSeek rate limit, повтор через 30 сек...")
            time.sleep(30)
            status, resp = http_post(DEEPSEEK_API_URL, headers, payload, timeout=60)
            if status == 200:
                return resp["choices"][0]["message"]["content"]

        logger.error(f"DeepSeek API ошибка: {status} — {resp}")
        return None

    except Exception as e:
        logger.error(f"DeepSeek API exception: {e}")
        return None


# ---------------------------------------------------------------------------
# Telegram отправка
# ---------------------------------------------------------------------------

TELEGRAM_API_BASE = "https://api.telegram.org/bot%s" % TELEGRAM_BOT_TOKEN if TELEGRAM_BOT_TOKEN else ""
MAX_TG_LENGTH = 4000  # Telegram limit ~4096


def _escape_markdown(text):
    """Экранируем проблемные символы для Telegram Markdown."""
    # Убираем символы, ломающие парсер Markdown Telegram
    text = re.sub(r'(?<!`)_(?!`)', '\\_', text)  # подчёркивания вне code
    text = text.replace('--', '—')  # двойной дефис ломает парсер
    text = text.replace('**', '')  # двойные звёзды — не используем bold-bold
    return text


def send_telegram(text, chat_id=None, max_retries=3):
    """Отправляет сообщение в Telegram с retry и экспоненциальным backoff."""
    cid = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not cid:
        logger.error("Telegram токен или chat ID не заданы!")
        return False

    url = TELEGRAM_API_BASE + "/sendMessage"

    # Разбиваем на части если текст длинный
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
        # Попытка 1: Markdown (экранированный)
        # Попытка 2: без parse_mode (plain text)
        # С retry на timeout
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    payload = {
                        "chat_id": cid,
                        "text": _escape_markdown(chunk),
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    }
                else:
                    # Fallback: plain text без parse_mode
                    plain = chunk.replace("*", "").replace("`", "'").replace("_", " ")
                    payload = {
                        "chat_id": cid,
                        "text": plain,
                        "disable_web_page_preview": True,
                    }

                status, resp = http_post(
                    url, {"Content-Type": "application/json"},
                    payload, timeout=15
                )

                if status == 200:
                    sent = True
                    break
                elif status == 400:
                    # Markdown parse error — сразу retry plain text
                    logger.warning("Telegram markdown error, retrying plain: %s", resp)
                    continue
                elif status == 429:
                    # Rate limit — ждём
                    wait = 5 * (attempt + 1)
                    logger.warning("Telegram rate limit, waiting %ds...", wait)
                    time.sleep(wait)
                    continue
                else:
                    logger.error("Telegram ошибка: %s — %s", status, resp)
                    continue

            except Exception as e:
                wait = 3 * (attempt + 1)
                logger.warning(
                    "Telegram timeout/error (attempt %d/%d): %s. Retry in %ds",
                    attempt + 1, max_retries, e, wait
                )
                time.sleep(wait)

        if not sent:
            logger.error("Telegram: не удалось отправить после %d попыток", max_retries)
            success = False

        time.sleep(0.3)  # Пауза между чанками

    return success


def send_raw_alert(errors: List[dict], deduped_count: int = 0) -> bool:
    """Отправляет алерт об ошибках в Telegram с информацией о пользователе."""
    ts = datetime.now().strftime("%H:%M:%S")
    header = f"⚠️ *{len(errors)} ошибок* на продакшене — {ts}"
    if deduped_count > 0:
        header += f" (+{deduped_count} повторных)"
    summary_lines = [header + "\n"]
    for err in errors[:15]:
        # User info
        user_info = ""
        uid = err.get("user_id", "")
        ip = err.get("user_ip", "")
        path = err.get("request_path", "")
        method = err.get("request_method", "")
        if uid and uid != "anonymous":
            user_info += f" user={uid}"
        if ip:
            user_info += f" ip={ip}"
        if path:
            user_info += f" {method} {path}" if method else f" {path}"

        short = (
            err["text"][:250]
            .replace("*", "")
            .replace("`", "'")
            .replace("_", " ")
            .replace("--", "—")
        )
        line = f"• [{err['source']}]{user_info}\n  {short}"
        summary_lines.append(line)
    if len(errors) > 15:
        summary_lines.append(f"...и ещё {len(errors) - 15} ошибок")
    return send_telegram("\n".join(summary_lines))


# ---------------------------------------------------------------------------
# Health checks / Smoke tests
# ---------------------------------------------------------------------------


def _fmt_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return "%.1f %s" % (size, unit)
        size /= 1024.0
    return "%.1f TB" % size


def run_health_checks():
    """Запускает проверки здоровья — сервисы, HTTP, диск, БД."""
    results = []
    results.append("🏥 *Health Check*")
    results.append("─" * 28)

    # 1. systemd сервисы
    services = ["teaching_panel", "celery", "nginx", "redis-server", "postgresql", "log-agent"]
    for svc in services:
        try:
            out = subprocess.check_output(
                ["systemctl", "is-active", svc], stderr=subprocess.STDOUT, timeout=5
            ).decode().strip()
            icon = "✅" if out == "active" else "⚠️"
            results.append("%s %s: %s" % (icon, svc, out))
        except Exception:
            results.append("❌ %s: не удалось проверить" % svc)

    # 2. HTTP endpoint
    results.append("")
    try:
        status, _ = http_get("http://127.0.0.1:8000/api/", timeout=5)
        icon = "✅" if status in (200, 301) else "⚠️"
        results.append("%s API endpoint: HTTP %d" % (icon, status))
    except Exception as e:
        results.append("❌ API endpoint: %s" % str(e)[:60])

    # 3. Внешний доступ
    try:
        status, _ = http_get("https://lectiospace.ru/", timeout=10)
        icon = "✅" if status == 200 else "⚠️"
        results.append("%s External HTTPS: %d" % (icon, status))
    except Exception as e:
        results.append("❌ External HTTPS: %s" % str(e)[:60])

    # 4. Диск
    try:
        out = subprocess.check_output(
            ["df", "-h", "/"], stderr=subprocess.STDOUT, timeout=5
        ).decode()
        for line in out.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 5:
                use_pct = int(parts[4].replace("%", ""))
                icon = "✅" if use_pct < 80 else ("⚠️" if use_pct < 90 else "🔴")
                results.append("%s Диск /: %s использовано (%s свободно)" % (icon, parts[4], parts[3]))
    except Exception:
        pass

    # 5. RAM
    try:
        out = subprocess.check_output(
            ["free", "-m"], stderr=subprocess.STDOUT, timeout=5
        ).decode()
        for line in out.strip().split("\n"):
            if line.startswith("Mem:"):
                parts = line.split()
                total, used = int(parts[1]), int(parts[2])
                pct = int(used / total * 100)
                icon = "✅" if pct < 80 else ("⚠️" if pct < 90 else "🔴")
                results.append("%s RAM: %dMB/%dMB (%d%%)" % (icon, used, total, pct))
    except Exception:
        pass

    # 6. Redis
    try:
        out = subprocess.check_output(
            ["redis-cli", "ping"], stderr=subprocess.STDOUT, timeout=5
        ).decode().strip()
        icon = "✅" if out == "PONG" else "❌"
        results.append("%s Redis: %s" % (icon, out))
    except Exception:
        results.append("❌ Redis: не отвечает")

    # 7. PostgreSQL
    try:
        out = subprocess.check_output(
            ["pg_isready"], stderr=subprocess.STDOUT, timeout=5
        ).decode().strip()
        icon = "✅" if "accepting" in out else "⚠️"
        results.append("%s PostgreSQL: %s" % (icon, out[:60]))
    except Exception:
        results.append("⚠️ PostgreSQL: не удалось проверить")

    # 8. Лог-файлы: размеры
    results.append("")
    results.append("*Размеры логов:*")
    for name, path in LOG_FILES.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            icon = "⚠️" if size > 100 * 1024 * 1024 else "📄"
            results.append("  %s %s: %s" % (icon, name, _fmt_size(size)))

    return "\n".join(results)


def run_smoke_tests():
    """Запускает быстрые smoke-тесты API endpoints."""
    results = []
    results.append("🧪 *Smoke Tests*")
    results.append("─" * 28)

    endpoints = [
        ("GET", "/api/", "Root API"),
        ("GET", "/health", "Health endpoint"),
        ("GET", "/api/tenants/public/olga/branding/", "Public branding"),
        ("GET", "/api/schedule/", "Schedule API"),
        ("GET", "/api/homework/", "Homework API"),
        ("POST", "/api/jwt/token/", "JWT auth (без данных)"),
    ]

    passed = 0
    failed = 0
    for method, path, name in endpoints:
        url = "http://127.0.0.1:8000" + path
        try:
            if method == "GET":
                status, _ = http_get(url, timeout=5)
            else:
                status, _ = http_post(
                    url, {"Content-Type": "application/json"}, {}, timeout=5
                )
            if status in (200, 301, 302, 401, 403, 400):
                results.append("✅ %s → %d" % (name, status))
                passed += 1
            else:
                results.append("❌ %s → %d" % (name, status))
                failed += 1
        except Exception as e:
            results.append("❌ %s → %s" % (name, str(e)[:50]))
            failed += 1

    results.append("")
    results.append("Итого: ✅ %d пройдено / ❌ %d провалено" % (passed, failed))
    return "\n".join(results)


# ---------------------------------------------------------------------------
# Telegram Bot — приём команд (long polling)
# ---------------------------------------------------------------------------

class TelegramBotThread(threading.Thread):
    """Фоновый тред: слушает Telegram updates через long-polling."""

    def __init__(self, agent):
        super(TelegramBotThread, self).__init__(daemon=True)
        self.agent = agent
        self.offset = 0

    def run(self):
        logger.info("TG Bot polling started")
        while self.agent.running:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._handle_update(update)
                    self.offset = update["update_id"] + 1
            except Exception as e:
                logger.error("TG Bot poll error: %s", e)
                time.sleep(10)

    def _get_updates(self):
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

    def _handle_update(self, update):
        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if not text or not chat_id:
            return

        # Проверка доступа
        if ALLOWED_CHATS and chat_id not in ALLOWED_CHATS:
            send_telegram("⛔ Нет доступа. Ваш chat\\_id: %s" % chat_id, chat_id)
            return

        logger.info("TG cmd from %s: %s", chat_id, text[:50])
        cmd = text.split()[0].lower().split("@")[0]  # убираем @botname

        if cmd == "/start" or cmd == "/help":
            self._cmd_help(chat_id)
        elif cmd == "/status":
            self._cmd_status(chat_id)
        elif cmd == "/errors":
            self._cmd_errors(chat_id)
        elif cmd == "/analyze":
            self._cmd_analyze(chat_id)
        elif cmd == "/tests":
            self._cmd_tests(chat_id)
        elif cmd == "/fixed" or cmd == "/report":
            self._cmd_fixed(chat_id)
        elif cmd == "/resolve":
            self._cmd_resolve(chat_id, text)
        elif cmd == "/health":
            self._cmd_health(chat_id)
        elif cmd == "/logs":
            self._cmd_logs(chat_id, text)
        else:
            send_telegram("🤔 Неизвестная команда. /help", chat_id)

    def _cmd_help(self, chat_id):
        send_telegram(
            "🤖 *AI Log Agent v2 — Команды*\n"
            + "─" * 28 + "\n"
            "/status — статус агента и сервисов\n"
            "/health — полный health-check\n"
            "/tests — smoke-тесты API endpoints\n"
            "/errors — текущие активные ошибки\n"
            "/analyze — AI-анализ логов сейчас\n"
            "/fixed — отчёт: починено vs осталось\n"
            "/resolve N — пометить ошибку #N починенной\n"
            "/logs <source> — последние строки лога\n"
            "/help — эта справка",
            chat_id,
        )

    def _cmd_status(self, chat_id):
        stats = self.agent.stats
        uptime_s = (datetime.now() - datetime.fromisoformat(stats["started"])).total_seconds()
        days = int(uptime_s // 86400)
        hours = int((uptime_s % 86400) // 3600)
        minutes = int((uptime_s % 3600) // 60)

        active = len(self.agent.tracker.active)
        resolved = len(self.agent.tracker.resolved)

        lines = [
            "🤖 *Log Agent Status*",
            "─" * 28,
            "⏱ Аптайм: %dд %dч %dм" % (days, hours, minutes),
            "🔄 Циклов: %d" % stats["cycles"],
            "🔍 Ошибок поймано: %d" % stats["errors_found"],
            "🧠 AI-вызовов: %d" % stats["ai_calls"],
            "📱 TG-сообщений: %d" % stats["tg_messages"],
            "",
            "❌ Активных ошибок: *%d*" % active,
            "✅ Починено: *%d*" % resolved,
            "",
        ]

        for svc in ["teaching_panel", "celery", "nginx", "redis-server", "postgresql"]:
            try:
                out = subprocess.check_output(
                    ["systemctl", "is-active", svc],
                    stderr=subprocess.STDOUT, timeout=3
                ).decode().strip()
                icon = "✅" if out == "active" else "⚠️"
                lines.append("%s %s" % (icon, svc))
            except Exception:
                lines.append("❓ %s" % svc)

        send_telegram("\n".join(lines), chat_id)

    def _cmd_errors(self, chat_id):
        tracker = self.agent.tracker
        if not tracker.active:
            send_telegram("✅ Активных ошибок нет!", chat_id)
            return

        lines = ["❌ *Активные ошибки* (%d)\n" % len(tracker.active)]
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
            lines.append("*#%s* [%s] x%d%s\n%s\n" % (eid, src, cnt, reopened, snip))

        lines.append("Для пометки: /resolve <id>")
        send_telegram("\n".join(lines), chat_id)

    def _cmd_analyze(self, chat_id):
        send_telegram("🔍 Запускаю AI-анализ логов...", chat_id)

        all_errors = []
        for source, filepath in LOG_FILES.items():
            if not os.path.exists(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(max(0, size - 50000))
                    lines = f.readlines()
                for line in lines:
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

        send_telegram(
            "Найдено %d ошибок (%d уникальных). Отправляю на AI..." % (len(all_errors), len(unique)),
            chat_id,
        )

        analysis = analyze_with_ai(unique[:MAX_BATCH_SIZE])
        if analysis:
            send_telegram(
                "🔍 *AI-анализ* (%d ошибок)\n%s\n%s" % (len(unique), "─" * 28, analysis),
                chat_id,
            )
            self.agent.stats["ai_calls"] += 1
        else:
            send_telegram("❌ AI-анализ недоступен.", chat_id)

    def _cmd_tests(self, chat_id):
        send_telegram("🧪 Запускаю тесты...", chat_id)
        health = run_health_checks()
        send_telegram(health, chat_id)
        smoke = run_smoke_tests()
        send_telegram(smoke, chat_id)

    def _cmd_health(self, chat_id):
        send_telegram("🏥 Проверяю здоровье...", chat_id)
        result = run_health_checks()
        send_telegram(result, chat_id)

    def _cmd_fixed(self, chat_id):
        report = self.agent.tracker.get_report()
        send_telegram(report, chat_id)

    def _cmd_resolve(self, chat_id, text):
        parts = text.split()
        if len(parts) < 2:
            send_telegram("Использование: /resolve <id>\nПример: /resolve 5", chat_id)
            return
        try:
            error_id = int(parts[1])
        except ValueError:
            send_telegram("❌ ID должен быть числом: /resolve 5", chat_id)
            return

        snippet = self.agent.tracker.resolve_by_id(error_id)
        if snippet:
            send_telegram(
                "✅ Ошибка #%d — *починена*!\n%s" % (error_id, snippet[:100]),
                chat_id,
            )
        else:
            send_telegram(
                "❌ Ошибка #%d не найдена среди активных.\n/errors" % error_id,
                chat_id,
            )

    def _cmd_logs(self, chat_id, text):
        parts = text.split()
        if len(parts) < 2:
            sources = ", ".join(LOG_FILES.keys())
            send_telegram("Использование: /logs <source>\nДоступные: %s" % sources, chat_id)
            return

        source = parts[1].lower()
        filepath = LOG_FILES.get(source)
        if not filepath:
            send_telegram("❌ Неизвестный источник: %s" % source, chat_id)
            return
        if not os.path.exists(filepath):
            send_telegram("❌ Файл не найден: %s" % filepath, chat_id)
            return

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 5000))
                tail = f.read()

            tail_lines = tail.strip().split("\n")[-20:]
            text_out = "\n".join(tail_lines)
            if len(text_out) > 3500:
                text_out = text_out[-3500:]

            send_telegram("📄 *%s* (последние строки)\n```\n%s\n```" % (source, text_out), chat_id)
        except Exception as e:
            send_telegram("❌ Ошибка чтения: %s" % e, chat_id)


# ---------------------------------------------------------------------------
# Основной цикл агента
# ---------------------------------------------------------------------------


class LogAgent:
    """Главный класс: collect → analyze → notify + TG бот + трекер."""

    def __init__(self):
        self.state = FileState()
        self.tracker = ErrorTracker()
        self.collector = LogCollector(self.state, self.tracker)
        self.running = True
        self.stats = {
            "started": datetime.now().isoformat(),
            "cycles": 0,
            "errors_found": 0,
            "ai_calls": 0,
            "tg_messages": 0,
        }

    def stop(self, *args):
        logger.info("Stopping...")
        self.running = False

    def run(self):
        """Главный цикл."""
        logger.info(
            "🤖 Log Agent v2 запущен. Интервал: %ds. Модель: %s. Файлов: %d.",
            BATCH_INTERVAL, DEEPSEEK_MODEL, len(LOG_FILES),
        )

        # Перематываем в конец файлов
        for source, filepath in LOG_FILES.items():
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                self.state.set_pos(filepath, size)
                logger.info("  📄 %s: %s (%s)", source, filepath, _fmt_size(size))
            else:
                logger.warning("  ❌ %s: %s — не найден", source, filepath)
        self.state.save()

        send_telegram(
            "🤖 *Log Agent v2 запущен*\n"
            "📅 %s\n"
            "⏱ Интервал: %dс\n"
            "📄 Файлов: %d\n"
            "📊 Активных: %d | Починено: %d\n"
            "\nКоманды: /help" % (
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                BATCH_INTERVAL,
                sum(1 for f in LOG_FILES.values() if os.path.exists(f)),
                len(self.tracker.active),
                len(self.tracker.resolved),
            )
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

        logger.info("Log Agent stopped.")

    def _cycle(self):
        self.stats["cycles"] += 1

        errors = self.collector.collect_errors()
        if not errors:
            return

        self.stats["errors_found"] += len(errors)
        deduped = self.collector.deduped_count
        logger.info(
            "Found %d new errors (%d deduped), sending alert...",
            len(errors), deduped
        )

        # 1. Обогащаем ошибки информацией о пользователе из requests.log
        enrich_errors_with_user_info(errors)

        # 2. Отправляем краткий raw-алерт
        if send_raw_alert(errors, deduped_count=deduped):
            self.stats["tg_messages"] += 1

        # 3. Отправляем AI-анализ с расшифровкой
        if DEEPSEEK_API_KEY and len(errors) > 0:
            try:
                analysis = analyze_with_ai(errors)
                if analysis:
                    self.stats["ai_calls"] = self.stats.get("ai_calls", 0) + 1
                    header = "🧠 *AI-анализ* (%d ошибок)\n%s\n" % (len(errors), "─" * 28)
                    send_telegram(header + analysis)
                    self.stats["tg_messages"] += 1
                else:
                    logger.warning("AI analysis returned None")
            except Exception as e:
                logger.error("AI analysis failed: %s", e, exc_info=True)

    def test_connections(self):
        """Тестирует все подключения."""
        print("=" * 50)
        print("🧪 Тест подключений Log Agent v2")
        print("=" * 50)

        print("\n📄 Лог-файлы:")
        for source, filepath in LOG_FILES.items():
            exists = os.path.exists(filepath)
            size = os.path.getsize(filepath) if exists else 0
            status = "✅ %s" % _fmt_size(size) if exists else "❌ не найден"
            print("  %-20s %s" % (source, status))

        print("\n🧠 DeepSeek API (%s):" % DEEPSEEK_MODEL)
        if not DEEPSEEK_API_KEY:
            print("  ❌ DEEPSEEK_API_KEY не задан")
        else:
            print("  Ключ: %s...%s" % (DEEPSEEK_API_KEY[:8], DEEPSEEK_API_KEY[-4:]))
            try:
                result = analyze_with_ai([{
                    "source": "test", "text": "Test: connection timeout",
                    "timestamp": "now", "fingerprint": "test",
                }])
                print("  ✅ OK (%d символов)" % len(result) if result else "  ❌ Нет ответа")
            except Exception as e:
                print("  ❌ %s" % e)

        print("\n📱 Telegram:")
        if not TELEGRAM_BOT_TOKEN:
            print("  ❌ LOG_AGENT_TG_TOKEN не задан")
        elif not TELEGRAM_CHAT_ID:
            print("  ❌ LOG_AGENT_TG_CHAT не задан")
        else:
            print("  Token: %s..." % TELEGRAM_BOT_TOKEN[:8])
            print("  Chat: %s" % TELEGRAM_CHAT_ID)
            ok = send_telegram("🧪 Log Agent v2 — тест пройден!")
            print("  %s" % ("✅ Отправлено" if ok else "❌ Ошибка"))

        print("\n📊 Трекер:")
        print("  Активных: %d | Починено: %d" % (
            len(self.tracker.active), len(self.tracker.resolved)
        ))
        print("=" * 50)


# ---------------------------------------------------------------------------
# Ежедневный дайджест
# ---------------------------------------------------------------------------


class DailyDigestThread(threading.Thread):
    def __init__(self, agent):
        super(DailyDigestThread, self).__init__(daemon=True)
        self.agent = agent
        self.last_digest_date = None

    def run(self):
        while self.agent.running:
            now = datetime.now()
            if now.hour == 9 and now.date() != self.last_digest_date:
                self._send_digest()
                self.last_digest_date = now.date()
            # Авторезолв каждые 6 часов
            if now.hour in (3, 9, 15, 21) and now.minute < 6:
                cnt = self.agent.tracker.auto_resolve_stale(hours=24)
                if cnt:
                    logger.info("Auto-resolved %d stale errors", cnt)
                    send_telegram(
                        "🔄 Авто-резолв: %d ошибок не повторялись >24ч и отмечены как починенные" % cnt
                    )
            time.sleep(300)

    def _send_digest(self):
        stats = self.agent.stats
        tracker = self.agent.tracker
        uptime = datetime.now() - datetime.fromisoformat(stats["started"])

        msg = (
            "📊 *Ежедневный дайджест*\n"
            "📅 %s\n"
            "%s\n"
            "⏱ Аптайм: %dд %dч\n"
            "🔄 Циклов: %d\n"
            "🔍 Ошибок поймано: %d\n"
            "🧠 AI-вызовов: %d\n"
            "\n"
            "❌ Активных: *%d*\n"
            "✅ Починено: *%d*\n"
        ) % (
            datetime.now().strftime("%Y-%m-%d"),
            "─" * 28,
            uptime.days, uptime.seconds // 3600,
            stats["cycles"],
            stats["errors_found"],
            stats["ai_calls"],
            len(tracker.active),
            len(tracker.resolved),
        )

        if tracker.active:
            msg += "\n*Топ ошибки:*\n"
            top = sorted(
                tracker.active.values(),
                key=lambda x: x.get("count", 0),
                reverse=True,
            )[:5]
            for info in top:
                msg += "  #%s x%d — %s\n" % (
                    info.get("id", "?"),
                    info.get("count", 0),
                    info.get("snippet", "?")[:60].replace("*", ""),
                )

        send_telegram(msg)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="AI Log Agent v2")
    parser.add_argument("--test", action="store_true", help="Тест подключений")
    parser.add_argument("--analyze-last", type=int, nargs="?", const=60)
    args = parser.parse_args()

    agent = LogAgent()

    if args.test:
        agent.test_connections()
        return

    if args.analyze_last:
        send_telegram("🔍 Запуск анализа из CLI...")
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
                                "source": source, "text": line.rstrip()[:300],
                                "timestamp": datetime.now().isoformat(),
                                "fingerprint": line_fingerprint(line),
                            })
            except Exception:
                pass

        seen = set()
        unique = [e for e in all_errors if e["fingerprint"] not in seen and not seen.add(e["fingerprint"])]
        print("Найдено %d ошибок (%d уникальных)" % (len(all_errors), len(unique)))

        analysis = analyze_with_ai(unique[:MAX_BATCH_SIZE])
        if analysis:
            print(analysis)
            send_telegram(
                "🔍 *AI-анализ по запросу* (%d ошибок)\n%s\n%s" % (
                    len(unique), "─" * 28, analysis
                )
            )
        return

    # Обработка сигналов
    signal.signal(signal.SIGTERM, agent.stop)
    signal.signal(signal.SIGINT, agent.stop)

    # Фоновые треды
    DailyDigestThread(agent).start()
    TelegramBotThread(agent).start()

    # Главный цикл
    agent.run()


if __name__ == "__main__":
    main()
