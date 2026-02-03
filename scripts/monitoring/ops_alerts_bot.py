"""Ops bot для управления алертами мониторинга (бесплатно).

Задача: дать несколько команд в Telegram:
- /status        — быстрый статус (HTTP + последние строки логов)
- /check         — выполнить быстрые проверки без отправки алертов
- /mute 30m      — заглушить алерты на 30 минут
- /unmute        — снять заглушку
- /mutestatus    — показать статус заглушки

Токен: используем ERRORS_BOT_TOKEN (бот, который уже шлёт алерты).
Разрешённые чаты: OPS_ALLOWED_CHAT_IDS (через запятую). Если не задано — ERRORS_CHAT_ID.

Запуск (на сервере):
  cd /opt/lectio-monitor
  python3 ops_alerts_bot.py

Рекомендуется запускать как systemd service.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Iterable, Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


CONFIG_FILE = Path(os.environ.get("LECTIO_MONITOR_CONFIG", "/opt/lectio-monitor/config.env"))
MUTE_FILE = Path(os.environ.get("ALERTS_MUTE_FILE", "/var/run/lectio-monitor/mute_until"))
LOG_DIR = Path(os.environ.get("LECTIO_MONITOR_LOG_DIR", "/var/log/lectio-monitor"))


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _parse_allowed_chat_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            continue
    return ids


def _tail_text(path: Path, max_lines: int = 40, max_chars: int = 3500) -> str:
    if not path.exists():
        return ""
    try:
        data = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    lines = data.splitlines()[-max_lines:]
    text = "\n".join(lines).strip()
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text


def _http_get_status(url: str, timeout: float = 8.0) -> tuple[bool, str]:
    try:
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": "LectioOpsBot/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
        return (200 <= int(code) < 400), f"HTTP {code}"
    except Exception as exc:
        return False, f"ERROR: {exc.__class__.__name__}"


def _format_mutestatus() -> str:
    if not MUTE_FILE.exists():
        return "Алерты не заглушены."
    try:
        until_raw = MUTE_FILE.read_text(encoding="utf-8", errors="ignore").strip()
        until = int(until_raw)
    except Exception:
        return "Файл заглушки повреждён."

    now = int(time.time())
    if now >= until:
        return "Алерты не заглушены (срок истёк)."

    remaining = until - now
    mins = remaining // 60
    return f"Алерты заглушены ещё на {mins} мин."


def _set_mute(seconds: int) -> str:
    until = int(time.time()) + max(0, seconds)
    MUTE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MUTE_FILE.write_text(str(until), encoding="utf-8")
    return _format_mutestatus()


def _clear_mute() -> str:
    try:
        if MUTE_FILE.exists():
            MUTE_FILE.unlink()
    except Exception:
        pass
    return "Заглушка снята."


_DURATION_RE = re.compile(r"^(\d+)(s|m|h|d)$", re.IGNORECASE)


def _parse_duration(arg: str) -> Optional[int]:
    arg = (arg or "").strip()
    if not arg:
        return None
    m = _DURATION_RE.match(arg)
    if not m:
        return None
    value = int(m.group(1))
    unit = m.group(2).lower()
    factor = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return value * factor


def _is_allowed(update: Update, allowed: set[int]) -> bool:
    chat = update.effective_chat
    if not chat:
        return False
    return int(chat.id) in allowed


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Команды мониторинга:\n"
        "/status — статус сайта + логи\n"
        "/check — быстрые проверки (без алертов)\n"
        "/mute 30m — заглушить алерты\n"
        "/unmute — снять заглушку\n"
        "/mutestatus — статус заглушки\n"
    )
    await update.message.reply_text(text)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    allowed: set[int] = context.bot_data["allowed_chat_ids"]
    if not _is_allowed(update, allowed):
        return

    site_url = os.environ.get("SITE_URL", "https://lectiospace.ru").rstrip("/")
    backend_url = os.environ.get("BACKEND_URL", site_url).rstrip("/")

    ok_main, main_status = _http_get_status(f"{site_url}/")
    ok_health, health_status = _http_get_status(f"{backend_url}/api/health/")

    parts: list[str] = []
    parts.append(f"Главная: {'OK' if ok_main else 'FAIL'} ({main_status})")
    parts.append(f"Health: {'OK' if ok_health else 'FAIL'} ({health_status})")
    parts.append("")
    parts.append(_format_mutestatus())

    logs = {
        "health": LOG_DIR / "health.log",
        "smoke": LOG_DIR / "smoke.log",
        "deep": LOG_DIR / "deep.log",
        "integration": LOG_DIR / "integration.log",
        "security": LOG_DIR / "security.log",
    }

    for name, path in logs.items():
        tail = _tail_text(path, max_lines=12)
        if tail:
            parts.append("")
            parts.append(f"{name}.log (tail):")
            parts.append(tail)

    message = "\n".join(parts)
    if len(message) > 3900:
        message = message[-3900:]

    await update.message.reply_text(message)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    allowed: set[int] = context.bot_data["allowed_chat_ids"]
    if not _is_allowed(update, allowed):
        return

    site_url = os.environ.get("SITE_URL", "https://lectiospace.ru").rstrip("/")
    backend_url = os.environ.get("BACKEND_URL", site_url).rstrip("/")

    checks: list[tuple[str, str]] = []
    for label, url in [
        ("/", f"{site_url}/"),
        ("/api/health/", f"{backend_url}/api/health/"),
        ("/api/jwt/token/", f"{backend_url}/api/jwt/token/"),
    ]:
        ok, status = _http_get_status(url)
        checks.append((label, f"{'OK' if ok else 'FAIL'} ({status})"))

    text = "Быстрые проверки:\n" + "\n".join([f"{k}: {v}" for k, v in checks])
    await update.message.reply_text(text)


async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    allowed: set[int] = context.bot_data["allowed_chat_ids"]
    if not _is_allowed(update, allowed):
        return

    if not context.args:
        await update.message.reply_text("Использование: /mute 30m или /mute 2h")
        return

    seconds = _parse_duration(context.args[0])
    if seconds is None:
        await update.message.reply_text("Неверный формат. Пример: /mute 30m, /mute 2h, /mute 1d")
        return

    await update.message.reply_text(_set_mute(seconds))


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    allowed: set[int] = context.bot_data["allowed_chat_ids"]
    if not _is_allowed(update, allowed):
        return
    await update.message.reply_text(_clear_mute())


async def cmd_mutestatus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    allowed: set[int] = context.bot_data["allowed_chat_ids"]
    if not _is_allowed(update, allowed):
        return
    await update.message.reply_text(_format_mutestatus())


def build_app() -> Application:
    _load_env_file(CONFIG_FILE)

    token = os.environ.get("ERRORS_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("ERRORS_BOT_TOKEN is not configured")

    allowed_raw = os.environ.get("OPS_ALLOWED_CHAT_IDS", "").strip()
    if not allowed_raw:
        allowed_raw = os.environ.get("ERRORS_CHAT_ID", "").strip()

    allowed = _parse_allowed_chat_ids(allowed_raw)
    if not allowed:
        raise SystemExit("No allowed chat IDs. Set OPS_ALLOWED_CHAT_IDS or ERRORS_CHAT_ID")

    app = Application.builder().token(token).build()
    app.bot_data["allowed_chat_ids"] = allowed

    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("mutestatus", cmd_mutestatus))

    return app


def main() -> None:
    app = build_app()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
