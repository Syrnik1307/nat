#!/usr/bin/env python3
"""
============================================================
LECTIO OPS BOT — Единый бот управления production
============================================================
Объединяет: OPS-управление + алерты мониторинга + меню UI.
Работает даже если Django упал. Не зависит от Django.

Меню (inline keyboard):
  /menu          — Главное меню с кнопками
  /start         — То же самое

Мониторинг:
  /status        — Полный статус (сервисы, HTTP, диск, RAM, 500-ки)
  /health        — Health endpoint
  /logs          — Логи gunicorn (30 строк)
  /logs_nginx    — Логи nginx errors
  /logs_guardian — Логи guardian
  /disk          — Использование диска
  /top           — Топ процессов по CPU/RAM

Управление:
  /restart       — Restart gunicorn + celery
  /restart_all   — Restart всего (+ nginx)
  /guardian      — Запустить guardian проверку
  /pause         — Пауза guardian (maintenance)
  /resume        — Снять паузу guardian
  /deploy_lock   — Заблокировать деплой
  /deploy_unlock — Разблокировать

Аварийные:
  /rollback      — Git rollback на last_known_good
  /rollback_db   — Rollback + восстановление БД

Бэкапы:
  /backups       — Список бэкапов БД
  /restore       — Восстановить БД из бэкапа

Git:
  /branch        — Текущая ветка + коммит
  /branches      — Список веток
  /switch        — Переключить ветку
  /git_log       — Последние 15 коммитов

Алерты:
  /mute 30m      — Заглушить алерты guardian
  /unmute        — Снять заглушку
  /alerts        — Статус алертов

Безопасность:
  - Только ADMIN_CHAT_IDS могут выполнять команды
  - Destructive команды требуют подтверждения (inline buttons)
  - Все действия логируются

Конфигурация (/opt/lectio-monitor/ops_bot.env):
  OPS_BOT_TOKEN="<токен>"
  ADMIN_CHAT_IDS="123456789"

Запуск: systemd lectio-ops-bot.service
============================================================
"""
import asyncio
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# --- Минимальные зависимости ---
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        ContextTypes,
    )
except ImportError:
    print("ОШИБКА: python-telegram-bot не установлен")
    print("Установи: pip install python-telegram-bot==20.7")
    sys.exit(1)

# --- Конфиг ---
CONFIG_FILE = os.environ.get("OPS_BOT_CONFIG", "/opt/lectio-monitor/ops_bot.env")
MONITOR_CONFIG = "/opt/lectio-monitor/config.env"
STATE_DIR = "/var/run/lectio-monitor"
LOG_DIR = "/var/log/lectio-monitor"
PROJECT_ROOT = "/var/www/teaching_panel"
KNOWN_GOOD_FILE = f"{STATE_DIR}/last_known_good"
MUTE_FILE = f"{STATE_DIR}/mute_until"

# --- PostgreSQL ---
PG_DB = "teaching_panel"
PG_USER = "teaching_panel"
PG_BACKUP_DIR = "/var/backups/teaching_panel"

# --- Парсинг длительности для /mute ---
_DURATION_RE = re.compile(r"^(\d+)(s|m|h|d)$", re.IGNORECASE)


def _parse_duration(arg: str):
    """Парсит '30m', '2h', '1d' → секунды, или None"""
    arg = (arg or "").strip()
    if not arg:
        return None
    m = _DURATION_RE.match(arg)
    if not m:
        return None
    value = int(m.group(1))
    unit = m.group(2).lower()
    return value * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]

# Загрузка конфига
def load_env(path):
    """Читает KEY=VALUE файл, игнорирует комментарии"""
    env = {}
    if not os.path.exists(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip('"').strip("'")
    return env

config = load_env(CONFIG_FILE)
monitor_config = load_env(MONITOR_CONFIG)

OPS_BOT_TOKEN = config.get("OPS_BOT_TOKEN", os.environ.get("OPS_BOT_TOKEN", ""))
ADMIN_CHAT_IDS_STR = config.get(
    "ADMIN_CHAT_IDS",
    os.environ.get("ADMIN_CHAT_IDS", monitor_config.get("ERRORS_CHAT_ID", "")),
)
ADMIN_CHAT_IDS = set()
for cid in ADMIN_CHAT_IDS_STR.split(","):
    cid = cid.strip()
    if cid:
        try:
            ADMIN_CHAT_IDS.add(int(cid))
        except ValueError:
            pass

if not OPS_BOT_TOKEN:
    print("ОШИБКА: OPS_BOT_TOKEN не задан")
    print(f"Создай файл {CONFIG_FILE} с содержимым:")
    print('  OPS_BOT_TOKEN="<токен от @BotFather>"')
    print('  ADMIN_CHAT_IDS="<твой chat_id>"')
    sys.exit(1)

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [OPS] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{LOG_DIR}/ops_bot.log", encoding="utf-8")
        if os.path.isdir(LOG_DIR)
        else logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ops_bot")

# --- Утилиты ---

def run_cmd(cmd: str, timeout: int = 30) -> str:
    """Выполняет shell-команду, возвращает stdout+stderr"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        return output.strip()[-3000:]  # Ограничиваем длину для Telegram
    except subprocess.TimeoutExpired:
        return f"TIMEOUT: команда не завершилась за {timeout}с"
    except Exception as e:
        return f"ERROR: {e}"


def is_admin(update: Update) -> bool:
    """Проверяет что пользователь — админ"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else 0
    return chat_id in ADMIN_CHAT_IDS or user_id in ADMIN_CHAT_IDS


def admin_required(func):
    """Декоратор: только для админов"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text(
                "Доступ запрещён. Твой chat_id: "
                f"{update.effective_chat.id}"
            )
            logger.warning(
                f"Unauthorized access attempt: chat_id={update.effective_chat.id}, "
                f"user={update.effective_user.username if update.effective_user else 'unknown'}"
            )
            return
        logger.info(
            f"CMD: {update.message.text} from {update.effective_user.username}"
        )
        return await func(update, context)
    return wrapper


def truncate_for_tg(text: str, max_len: int = 4000) -> str:
    """Обрезает текст до лимита Telegram"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n\n... (обрезано)"


# Pending confirmations: chat_id -> (action, timestamp)
_pending_confirms = {}
CONFIRM_TIMEOUT = 60  # секунд


# --- Inline Keyboard Menu ---

def _main_menu_keyboard():
    """Главное меню — quick actions + секции"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("!! SOS: Revive Site !!", callback_data="act_sos"),
        ],
        [
            InlineKeyboardButton("Quick Restart", callback_data="act_quick_restart"),
            InlineKeyboardButton("Quick Backup", callback_data="act_quick_backup"),
        ],
        [
            InlineKeyboardButton("Quick Deploy", callback_data="act_deploy"),
            InlineKeyboardButton("Quick Health", callback_data="act_health"),
        ],
        [
            InlineKeyboardButton("Monitoring", callback_data="menu_monitoring"),
            InlineKeyboardButton("Management", callback_data="menu_management"),
        ],
        [
            InlineKeyboardButton("Emergency", callback_data="menu_emergency"),
            InlineKeyboardButton("Backups & DB", callback_data="menu_backups"),
        ],
        [
            InlineKeyboardButton("Git", callback_data="menu_git"),
            InlineKeyboardButton("Alerts", callback_data="menu_alerts"),
        ],
    ])


def _monitoring_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Status", callback_data="act_status"),
            InlineKeyboardButton("Health", callback_data="act_health"),
        ],
        [
            InlineKeyboardButton("Errors (500s)", callback_data="act_errors"),
            InlineKeyboardButton("Celery", callback_data="act_celery"),
        ],
        [
            InlineKeyboardButton("Logs Gunicorn", callback_data="act_logs"),
            InlineKeyboardButton("Logs Nginx", callback_data="act_logs_nginx"),
        ],
        [
            InlineKeyboardButton("Logs Guardian", callback_data="act_logs_guardian"),
            InlineKeyboardButton("Uptime", callback_data="act_uptime"),
        ],
        [
            InlineKeyboardButton("Disk", callback_data="act_disk"),
            InlineKeyboardButton("Top", callback_data="act_top"),
        ],
        [
            InlineKeyboardButton("SSL cert", callback_data="act_ssl"),
            InlineKeyboardButton("Users", callback_data="act_users"),
        ],
        [InlineKeyboardButton("<< Main menu", callback_data="menu_main")],
    ])


def _management_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Restart", callback_data="act_restart"),
            InlineKeyboardButton("Restart ALL", callback_data="act_restart_all"),
        ],
        [
            InlineKeyboardButton("Run Guardian", callback_data="act_guardian"),
            InlineKeyboardButton("Nginx test", callback_data="act_nginx_test"),
        ],
        [
            InlineKeyboardButton("Pause", callback_data="act_pause"),
            InlineKeyboardButton("Resume", callback_data="act_resume"),
        ],
        [
            InlineKeyboardButton("Deploy Lock", callback_data="act_deploy_lock"),
            InlineKeyboardButton("Deploy Unlock", callback_data="act_deploy_unlock"),
        ],
        [
            InlineKeyboardButton("Cleanup", callback_data="act_cleanup"),
        ],
        [InlineKeyboardButton("<< Main menu", callback_data="menu_main")],
    ])


def _emergency_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Rollback (code)", callback_data="act_rollback"),
        ],
        [
            InlineKeyboardButton("Rollback + DB", callback_data="act_rollback_db"),
        ],
        [InlineKeyboardButton("<< Main menu", callback_data="menu_main")],
    ])


def _backups_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Backup NOW", callback_data="act_backup"),
            InlineKeyboardButton("List backups", callback_data="act_backups"),
        ],
        [
            InlineKeyboardButton("Restore DB", callback_data="act_restore"),
            InlineKeyboardButton("DB health", callback_data="act_db"),
        ],
        [InlineKeyboardButton("<< Main menu", callback_data="menu_main")],
    ])


def _git_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Branch info", callback_data="act_branch"),
            InlineKeyboardButton("Branches", callback_data="act_branches"),
        ],
        [
            InlineKeyboardButton("Git log", callback_data="act_git_log"),
            InlineKeyboardButton("Switch", callback_data="act_switch"),
        ],
        [InlineKeyboardButton("<< Main menu", callback_data="menu_main")],
    ])


def _alerts_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Status", callback_data="act_alerts"),
        ],
        [
            InlineKeyboardButton("Mute 30m", callback_data="act_mute_30m"),
            InlineKeyboardButton("Mute 1h", callback_data="act_mute_1h"),
        ],
        [
            InlineKeyboardButton("Mute 2h", callback_data="act_mute_2h"),
            InlineKeyboardButton("Mute 6h", callback_data="act_mute_6h"),
        ],
        [
            InlineKeyboardButton("Unmute", callback_data="act_unmute"),
        ],
        [InlineKeyboardButton("<< Main menu", callback_data="menu_main")],
    ])


# --- Mute/Unmute helpers ---

def _get_mute_status() -> str:
    """Проверяет файл mute_until, возвращает человекочитаемый статус"""
    if not os.path.exists(MUTE_FILE):
        return "Алерты АКТИВНЫ (не заглушены)"
    try:
        with open(MUTE_FILE) as f:
            until = int(f.read().strip())
    except (ValueError, OSError):
        return "Файл заглушки повреждён"
    now = int(time.time())
    if now >= until:
        return "Алерты АКТИВНЫ (срок заглушки истёк)"
    remaining = until - now
    mins = remaining // 60
    if mins >= 60:
        return f"Алерты ЗАГЛУШЕНЫ ещё {mins // 60}ч {mins % 60}м"
    return f"Алерты ЗАГЛУШЕНЫ ещё {mins}м"


def _set_mute(seconds: int) -> str:
    """Создаёт файл mute_until"""
    until = int(time.time()) + max(0, seconds)
    run_cmd(f"mkdir -p {STATE_DIR}")
    try:
        with open(MUTE_FILE, "w") as f:
            f.write(str(until))
    except OSError:
        run_cmd(f"echo {until} | sudo tee {MUTE_FILE}")
    return _get_mute_status()


def _clear_mute() -> str:
    """Удаляет файл mute_until"""
    run_cmd(f"rm -f {MUTE_FILE}")
    return "Заглушка снята. Алерты АКТИВНЫ."


# --- Команды ---

@admin_required
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню с inline кнопками"""
    # Quick status line
    health = run_cmd(
        'curl -so/dev/null -w"%{http_code}" --max-time 3 '
        'http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" '
        '-H "X-Forwarded-Proto: https" 2>/dev/null || echo "fail"',
        timeout=5,
    )
    is_ok = health.strip() == "200"
    status_line = "OK" if is_ok else f"PROBLEM ({health.strip()})"
    mute_line = _get_mute_status()

    await update.message.reply_text(
        f"<b>Lectio OPS</b>\n\n"
        f"Site: <b>{status_line}</b>\n"
        f"{mute_line}\n\n"
        f"Choose a section:",
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )


@admin_required
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Lectio OPS Bot</b>\n\n"
        "Use /menu for interactive menu.\n\n"
        "<b>Monitoring:</b>\n"
        "/status — Full status\n"
        "/health — Health check\n"
        "/logs — Gunicorn logs\n"
        "/logs_nginx — Nginx errors\n"
        "/logs_guardian — Guardian logs\n"
        "/errors — Recent 500 errors\n"
        "/celery — Celery status\n"
        "/uptime — Service uptimes\n"
        "/ssl — SSL cert expiry\n"
        "/users — User stats\n"
        "/disk — Disk usage\n"
        "/top — Top processes\n\n"
        "<b>Management:</b>\n"
        "/deploy — Quick deploy\n"
        "/restart — Restart gunicorn+celery\n"
        "/restart_all — Restart all (+nginx)\n"
        "/nginx_test — Test nginx config\n"
        "/guardian — Run guardian now\n"
        "/pause — Pause guardian\n"
        "/resume — Resume guardian\n"
        "/cleanup — Clean old files\n\n"
        "<b>Emergency:</b>\n"
        "/rollback — Git rollback\n"
        "/rollback_db — Rollback + DB\n\n"
        "<b>Backups & DB:</b>\n"
        "/backups — List backups\n"
        "/restore — Restore DB\n"
        "/backup — Create backup now\n"
        "/db — DB health\n\n"
        "<b>Git:</b>\n"
        "/branch — Current branch\n"
        "/branches — All branches\n"
        "/switch — Switch branch\n"
        "/git_log — Last 15 commits\n\n"
        "<b>Users:</b>\n"
        "/adduser email [role] — Create user\n"
        "/resetpw email — Reset password\n\n"
        "<b>Alerts:</b>\n"
        "/mute 30m — Mute alerts\n"
        "/unmute — Unmute\n"
        "/alerts — Alert status\n\n"
        "<b>Deploy:</b>\n"
        "/deploy_lock — Lock deploy\n"
        "/deploy_unlock — Unlock\n",
        parse_mode="HTML",
    )


@admin_required
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Collecting status...")
    await _run_status(update.message)


async def _run_status(message):
    """Full status check — services, HTTP, disk, RAM, 500s"""
    output = run_cmd(f"""
echo "=== SERVICES ==="
for svc in teaching_panel celery celery-beat nginx redis-server lectio-ops-bot telegram_bot support_bot; do
    ST=$(systemctl is-active $svc 2>/dev/null || echo 'not-found')
    printf "  %-24s %s\\n" "$svc" "$ST"
done
echo ""
echo "=== HTTP ==="
HTTP=$(curl -so/dev/null -w"%{{http_code}}" --max-time 5 http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" -H "X-Forwarded-Proto: https" 2>/dev/null)
FRONT=$(curl -so/dev/null -w"%{{http_code}}" --max-time 5 https://lectiospace.ru/ 2>/dev/null)
echo "  Backend health: $HTTP"
echo "  Frontend:       $FRONT"
echo ""
echo "=== RESOURCES ==="
df -h / 2>/dev/null | tail -1 | awk '{{printf "  Disk: %s used of %s (%s)\\n", $3, $2, $5}}'
free -h 2>/dev/null | awk '/^Mem/ {{printf "  RAM:  %s used of %s\\n", $3, $2}}'
echo "  Load: $(cat /proc/loadavg 2>/dev/null | awk '{{print $1, $2, $3}}')"
echo ""
echo "=== DB ==="
DB_SIZE=$(sudo -u postgres psql -d {PG_DB} -tAc 'SELECT pg_size_pretty(pg_database_size(current_database()));' 2>/dev/null)
DB_CONNS=$(sudo -u postgres psql -d {PG_DB} -tAc 'SELECT count(*) FROM pg_stat_activity WHERE datname=current_database();' 2>/dev/null)
echo "  PostgreSQL: ${{DB_SIZE:-N/A}}, ${{DB_CONNS:-0}} connections"
echo ""
echo "=== RECENT 5xx ==="
COUNT_5XX=$(awk '$9 ~ /^5[0-9][0-9]$/' /var/log/nginx/access.log 2>/dev/null | wc -l)
echo "  Total 5xx in access.log: $COUNT_5XX"
awk '$9 ~ /^5[0-9][0-9]$/ {{print $4, $7, $9}}' /var/log/nginx/access.log 2>/dev/null | tail -3 | sed 's/^/  /'
echo ""
echo "=== GIT ==="
cd {PROJECT_ROOT} && echo "  Branch: $(git branch --show-current 2>/dev/null)" && echo "  Commit: $(git rev-parse --short HEAD 2>/dev/null) $(git log -1 --format=%s 2>/dev/null | head -c 60)"
echo ""
echo "=== GUARDIAN ==="
KG=$(cat {KNOWN_GOOD_FILE} 2>/dev/null || echo 'NOT SET')
echo "  Known good: $KG"
GLAST=$(tail -1 {LOG_DIR}/guardian.log 2>/dev/null || echo 'no log')
echo "  Last check: $GLAST"
""", timeout=25)
    await message.reply_text(
        f"<pre>{truncate_for_tg(output, 3900)}</pre>",
        parse_mode="HTML",
    )


HEALTH_CMD = (
    'curl -so/dev/null -w"%{http_code}" --max-time 5 '
    'http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" '
    '-H "X-Forwarded-Proto: https" 2>/dev/null || echo "000"'
)


async def _auto_revive(message):
    """Smart auto-recovery with escalating fixes. One tap = site alive."""
    steps = []
    ts_start = time.time()

    # Step 0: Check if site is actually down
    health = run_cmd(HEALTH_CMD, timeout=8).strip()
    if health == "200":
        await message.reply_text(
            "Site is already UP (HTTP 200).\nNo action needed.",
        )
        return
    steps.append(f"Site DOWN (HTTP {health})")
    await message.reply_text("SOS: site down, starting auto-recovery...")

    # Step 1: Restart core services (gunicorn + celery)
    run_cmd(
        "systemctl restart teaching_panel celery celery-beat 2>&1",
        timeout=30,
    )
    run_cmd("sleep 3")
    health = run_cmd(HEALTH_CMD, timeout=8).strip()
    if health == "200":
        elapsed = int(time.time() - ts_start)
        steps.append(f"Restarted gunicorn+celery -> UP! ({elapsed}s)")
        nl = chr(10)
        await message.reply_text(
            f"<b>SOS: RECOVERED</b>\n\n" + nl.join(f"{i+1}. {s}" for i, s in enumerate(steps)),
            parse_mode="HTML",
        )
        return
    steps.append(f"Restarted gunicorn+celery -> still {health}")

    # Step 2: Restart ALL services (nginx, redis, everything)
    run_cmd(
        "systemctl restart nginx redis-server teaching_panel celery celery-beat 2>&1",
        timeout=40,
    )
    run_cmd("sleep 5")
    health = run_cmd(HEALTH_CMD, timeout=8).strip()
    if health == "200":
        elapsed = int(time.time() - ts_start)
        steps.append(f"Restarted ALL services -> UP! ({elapsed}s)")
        nl = chr(10)
        await message.reply_text(
            f"<b>SOS: RECOVERED</b>\n\n" + nl.join(f"{i+1}. {s}" for i, s in enumerate(steps)),
            parse_mode="HTML",
        )
        return
    steps.append(f"Restarted ALL -> still {health}")

    # Step 3: Kill stuck processes + force restart
    run_cmd(
        "pkill -9 -f gunicorn 2>/dev/null; pkill -9 -f celery 2>/dev/null; sleep 2; "
        "systemctl restart teaching_panel celery celery-beat nginx redis-server 2>&1",
        timeout=40,
    )
    run_cmd("sleep 5")
    health = run_cmd(HEALTH_CMD, timeout=8).strip()
    if health == "200":
        elapsed = int(time.time() - ts_start)
        steps.append(f"Killed stuck + restarted -> UP! ({elapsed}s)")
        nl = chr(10)
        await message.reply_text(
            f"<b>SOS: RECOVERED</b>\n\n" + nl.join(f"{i+1}. {s}" for i, s in enumerate(steps)),
            parse_mode="HTML",
        )
        return
    steps.append(f"Kill + restart -> still {health}")

    # Step 4: Run guardian (full L1/L2/L3 recovery)
    run_cmd(
        "bash /opt/lectio-monitor/guardian.sh 2>&1",
        timeout=90,
    )
    run_cmd("sleep 5")
    health = run_cmd(HEALTH_CMD, timeout=8).strip()
    if health == "200":
        elapsed = int(time.time() - ts_start)
        steps.append(f"Guardian recovery -> UP! ({elapsed}s)")
        nl = chr(10)
        await message.reply_text(
            f"<b>SOS: RECOVERED</b>\n\n" + nl.join(f"{i+1}. {s}" for i, s in enumerate(steps)),
            parse_mode="HTML",
        )
        return
    steps.append(f"Guardian -> still {health}")

    # Step 5: Everything failed
    elapsed = int(time.time() - ts_start)
    steps.append(f"ALL auto-recovery failed ({elapsed}s)")
    nl = chr(10)
    await message.reply_text(
        f"<b>SOS: FAILED TO RECOVER</b>\n\n"
        + nl.join(f"{i+1}. {s}" for i, s in enumerate(steps))
        + "\n\nManual action needed:\n"
        "- /logs to check errors\n"
        "- /rollback to revert code\n"
        "- /rollback_db to revert code+DB\n"
        "- Check server via SSH",
        parse_mode="HTML",
    )


@admin_required
async def cmd_sos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SOS: автоматическое оживление сайта"""
    await _auto_revive(update.message)


@admin_required
async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    output = run_cmd(
        'curl -s -w "\\nHTTP: %{http_code}\\nTime: %{time_total}s" '
        '--max-time 10 http://127.0.0.1:8000/api/health/ '
        '-H "Host: lectiospace.ru" -H "X-Forwarded-Proto: https"',
        timeout=15,
    )
    await update.message.reply_text(f"<pre>{truncate_for_tg(output)}</pre>", parse_mode="HTML")


@admin_required
async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    output = run_cmd("journalctl -u teaching_panel -n 30 --no-pager 2>&1")
    await update.message.reply_text(
        f"<b>Gunicorn logs (30)</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_logs_nginx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    output = run_cmd("tail -30 /var/log/nginx/error.log 2>&1")
    await update.message.reply_text(
        f"<b>Nginx error log (30)</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_logs_guardian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    output = run_cmd("tail -40 /var/log/lectio-monitor/guardian.log 2>&1")
    await update.message.reply_text(
        f"<b>Guardian log (40)</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_disk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    output = run_cmd("df -h / /tmp 2>&1; echo ''; du -sh /var/www/teaching_panel/media /var/log 2>/dev/null; echo ''; sudo -u postgres psql teaching_panel -t -c \"SELECT pg_size_pretty(pg_database_size('teaching_panel'));\" 2>/dev/null | xargs -I{} echo 'DB size: {}'")
    await update.message.reply_text(f"<pre>{truncate_for_tg(output)}</pre>", parse_mode="HTML")


@admin_required
async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    output = run_cmd("ps aux --sort=-%cpu | head -15 2>&1")
    await update.message.reply_text(f"<pre>{truncate_for_tg(output)}</pre>", parse_mode="HTML")


# --- Команды действий ---

@admin_required
async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Перезапускаю gunicorn + celery...")
    output = run_cmd(
        "systemctl restart teaching_panel celery celery-beat 2>&1 && "
        "sleep 3 && "
        "echo 'Restart done' && "
        'curl -so/dev/null -w"Health: %{http_code}" --max-time 5 '
        'http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" '
        '-H "X-Forwarded-Proto: https"',
        timeout=30,
    )
    await update.message.reply_text(f"<pre>{output}</pre>", parse_mode="HTML")


@admin_required
async def cmd_restart_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Перезапускаю ВСЕ сервисы (nginx тоже)...")
    output = run_cmd(
        "systemctl restart teaching_panel celery celery-beat nginx redis-server 2>&1 && "
        "sleep 5 && "
        "echo 'Restart done' && "
        'HEALTH=$(curl -so/dev/null -w"%{http_code}" --max-time 5 '
        'http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" '
        '-H "X-Forwarded-Proto: https") && '
        'FRONT=$(curl -so/dev/null -w"%{http_code}" --max-time 5 https://lectiospace.ru/) && '
        'echo "Health: $HEALTH  Frontend: $FRONT"',
        timeout=40,
    )
    await update.message.reply_text(f"<pre>{output}</pre>", parse_mode="HTML")


@admin_required
async def cmd_guardian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Запускаю guardian проверку...")
    output = run_cmd(
        "/opt/lectio-monitor/guardian.sh 2>&1; "
        "echo '---'; "
        "tail -5 /var/log/lectio-monitor/guardian.log",
        timeout=60,
    )
    await update.message.reply_text(
        f"<b>Guardian result:</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_cmd("mkdir -p /var/run/lectio-monitor && touch /var/run/lectio-monitor/maintenance_mode")
    await update.message.reply_text("Guardian на паузе (maintenance mode ON)")


@admin_required
async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_cmd("rm -f /var/run/lectio-monitor/maintenance_mode /var/run/lectio-monitor/deploy_in_progress")
    await update.message.reply_text("Guardian активен (maintenance mode OFF)")


@admin_required
async def cmd_deploy_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_cmd("mkdir -p /var/run/lectio-monitor && touch /var/run/lectio-monitor/deploy_in_progress")
    await update.message.reply_text("Deploy заблокирован (guardian пауза)")


@admin_required
async def cmd_deploy_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    run_cmd("rm -f /var/run/lectio-monitor/deploy_in_progress")
    await update.message.reply_text("Deploy разблокирован")


# --- Опасные команды (с подтверждением) ---

@admin_required
async def cmd_rollback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Git rollback с подтверждением"""
    known_good = run_cmd(f"cat {KNOWN_GOOD_FILE} 2>/dev/null || echo 'NOT SET'")
    current = run_cmd(f"cd {PROJECT_ROOT} && git rev-parse --short HEAD")
    
    if "NOT SET" in known_good:
        await update.message.reply_text(
            "Нет записи о last_known_good.\n"
            "Guardian ещё не зафиксировал рабочую версию."
        )
        return
    
    good_commit = known_good.split()[0]
    if good_commit == current.strip():
        await update.message.reply_text(
            f"Уже на last_known_good: {good_commit}\n"
            "Если проблема не в коде, попробуй /restart"
        )
        return
    
    _pending_confirms[update.effective_chat.id] = ("rollback", time.time())
    
    keyboard = [
        [
            InlineKeyboardButton("Откатить", callback_data="confirm_rollback"),
            InlineKeyboardButton("Отмена", callback_data="cancel"),
        ]
    ]
    await update.message.reply_text(
        f"<b>ROLLBACK</b>\n\n"
        f"Текущий: <code>{current.strip()}</code>\n"
        f"Откат на: <code>{good_commit}</code> ({known_good})\n\n"
        f"Действия:\n"
        f"1. git reset --hard {good_commit}\n"
        f"2. pip install requirements\n"
        f"3. collectstatic\n"
        f"4. restart всех сервисов\n\n"
        f"<b>Подтвердить?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


@admin_required
async def cmd_rollback_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Git rollback + DB restore с подтверждением"""
    known_good = run_cmd(f"cat {KNOWN_GOOD_FILE} 2>/dev/null || echo 'NOT SET'")
    latest_backup = run_cmd(f"ls -t {PG_BACKUP_DIR}/pg_*.sql.gz 2>/dev/null | head -1")
    
    if not latest_backup or latest_backup.startswith("ERROR") or not latest_backup.strip():
        await update.message.reply_text("PG бэкапы не найдены.")
        return
    
    _pending_confirms[update.effective_chat.id] = ("rollback_db", time.time())
    
    keyboard = [
        [
            InlineKeyboardButton("Откатить + БД", callback_data="confirm_rollback_db"),
            InlineKeyboardButton("Отмена", callback_data="cancel"),
        ]
    ]
    await update.message.reply_text(
        f"<b>ROLLBACK + DB RESTORE</b>\n\n"
        f"Known good: <code>{known_good}</code>\n"
        f"DB backup: <code>{latest_backup}</code>\n\n"
        f"<b>ОПАСНО! Восстановление БД потеряет данные после бэкапа!</b>\n\n"
        f"Подтвердить?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def confirm_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок подтверждения (rollback, restore, switch, deploy)"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    
    if not is_admin(update):
        await query.edit_message_text("Access denied.")
        return
    
    if query.data == "cancel":
        _pending_confirms.pop(chat_id, None)
        await query.edit_message_text("Cancelled.")
        return
    
    # Проверяем pending confirm
    pending = _pending_confirms.pop(chat_id, None)
    if not pending:
        await query.edit_message_text("No pending confirmations.")
        return
    
    action = pending[0]
    ts = pending[1]
    if time.time() - ts > CONFIRM_TIMEOUT:
        await query.edit_message_text("Confirmation expired. Retry the command.")
        return
    
    if query.data == "confirm_deploy" and action == "deploy":
        await query.edit_message_text("Deploying...")
        await _do_deploy(query.message)
    
    elif query.data == "confirm_rollback" and action == "rollback":
        await query.edit_message_text("Executing rollback...")
        await _do_rollback(query.message, with_db=False)
    
    elif query.data == "confirm_rollback_db" and action == "rollback_db":
        await query.edit_message_text("Executing rollback + DB restore...")
        await _do_rollback(query.message, with_db=True)
    
    elif query.data.startswith("restore_") and action == "restore":
        idx = int(query.data.split("_")[1])
        backups = pending[2] if len(pending) > 2 else []
        if idx < len(backups):
            await query.edit_message_text(f"Restoring from {os.path.basename(backups[idx])}...")
            await _do_restore_db(query.message, backups[idx])
        else:
            await query.edit_message_text("Backup not found.")
    
    elif query.data.startswith("switch_") and action == "switch_select":
        target_branch = query.data[len("switch_"):]
        current = run_cmd(f"cd {PROJECT_ROOT} && git branch --show-current 2>/dev/null").strip()
        if target_branch == current:
            await query.edit_message_text(f"Already on {target_branch}")
            return
        await query.edit_message_text(f"Switching to {target_branch}...")
        await _do_switch_branch(query.message, target_branch)
    
    elif query.data == "confirm_switch" and action == "switch":
        target_branch = pending[2] if len(pending) > 2 else ""
        if not target_branch:
            await query.edit_message_text("Error: branch not specified")
            return
        await query.edit_message_text(f"Switching to {target_branch}...")
        await _do_switch_branch(query.message, target_branch)
    
    else:
        await query.edit_message_text("Unknown action.")


async def _do_rollback(message, with_db: bool):
    """Выполняет rollback"""
    good_commit = run_cmd(f"head -1 {KNOWN_GOOD_FILE} | awk '{{print $1}}'")
    if not good_commit:
        await message.reply_text("Ошибка: не могу прочитать known_good")
        return
    
    steps = []
    
    # 1. Maintenance mode
    run_cmd("touch /var/run/lectio-monitor/maintenance_mode /var/run/lectio-monitor/deploy_in_progress")
    steps.append("1. Maintenance mode ON")
    
    # 2. Backup current state (PostgreSQL)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pre_rollback = f"{PG_BACKUP_DIR}/pg_pre_rollback_{ts}.sql.gz"
    run_cmd(f"sudo -u postgres pg_dump {PG_DB} 2>/dev/null | gzip > {pre_rollback}", timeout=60)
    steps.append(f"2. PG backup: pg_pre_rollback_{ts}.sql.gz")
    
    # 3. Снимаем immutable
    run_cmd(f"chattr -i {PROJECT_ROOT}/frontend/build/index.html {PROJECT_ROOT}/frontend/build/favicon.svg {PROJECT_ROOT}/teaching_panel/teaching_panel/settings.py 2>/dev/null || true")
    steps.append("3. Immutable flags removed")
    
    # 4. Git rollback
    output = run_cmd(f"cd {PROJECT_ROOT} && git fetch origin 2>/dev/null; git reset --hard {good_commit}")
    steps.append(f"4. Git reset: {output[-100:]}")
    
    # 5. DB restore (optional)
    if with_db:
        latest_backup = run_cmd(f"ls -t {PG_BACKUP_DIR}/pg_*.sql.gz 2>/dev/null | head -1")
        if latest_backup and not latest_backup.startswith("ERROR") and latest_backup.strip():
            latest_backup = latest_backup.strip()
            restore_out = run_cmd(
                f"sudo -u postgres psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{PG_DB}' AND pid <> pg_backend_pid();\" 2>/dev/null; "
                f"sudo -u postgres dropdb --if-exists {PG_DB} 2>&1; "
                f"sudo -u postgres createdb -O {PG_USER} {PG_DB} 2>&1; "
                f"zcat {latest_backup} | sudo -u postgres psql -d {PG_DB} 2>&1 | tail -3",
                timeout=120,
            )
            steps.append(f"5. DB restored from {os.path.basename(latest_backup)}")
        else:
            steps.append("5. DB restore SKIPPED (no PG backup found)")
    
    # 6. pip install
    pip_out = run_cmd(f"cd {PROJECT_ROOT} && source venv/bin/activate && pip install -q -r teaching_panel/requirements.txt 2>&1 | tail -3 && echo PIP_OK", timeout=120)
    steps.append(f"6. pip: {'OK' if 'PIP_OK' in pip_out else 'WARN'}")
    
    # 7. collectstatic
    run_cmd(f"cd {PROJECT_ROOT}/teaching_panel && source ../venv/bin/activate && python manage.py collectstatic --noinput --clear 2>/dev/null || true")
    steps.append("7. collectstatic done")
    
    # 8. Fix permissions
    run_cmd(f"chown -R www-data:www-data {PROJECT_ROOT}/frontend/build {PROJECT_ROOT}/staticfiles {PROJECT_ROOT}/media 2>/dev/null; chmod -R 755 {PROJECT_ROOT}/frontend/build {PROJECT_ROOT}/staticfiles 2>/dev/null")
    steps.append("8. Permissions fixed")
    
    # 9. Restart services
    run_cmd("systemctl restart teaching_panel celery celery-beat nginx redis-server 2>/dev/null || true")
    steps.append("9. Services restarted")
    
    # 10. Restore immutable
    run_cmd(f"chattr +i {PROJECT_ROOT}/frontend/build/index.html {PROJECT_ROOT}/frontend/build/favicon.svg {PROJECT_ROOT}/teaching_panel/teaching_panel/settings.py 2>/dev/null || true")
    steps.append("10. Immutable restored")
    
    # 11. Wait and verify
    await asyncio.sleep(5)
    health = run_cmd('curl -so/dev/null -w"%{http_code}" --max-time 5 http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" -H "X-Forwarded-Proto: https"')
    front = run_cmd('curl -so/dev/null -w"%{http_code}" --max-time 5 https://lectiospace.ru/')
    steps.append(f"11. Verify: health={health} frontend={front}")
    
    # 12. Remove maintenance
    run_cmd("rm -f /var/run/lectio-monitor/maintenance_mode /var/run/lectio-monitor/deploy_in_progress")
    steps.append("12. Maintenance mode OFF")
    
    # Result
    ok = health.strip() == "200" and front.strip() == "200"
    header = "ROLLBACK OK" if ok else "ROLLBACK - ПРОБЛЕМЫ!"
    
    result_text = f"<b>{header}</b>\n\n" + "\n".join(steps)
    if not ok:
        result_text += (
            "\n\nРучная проверка:\n"
            "  journalctl -u teaching_panel -n 50\n"
            "  tail -20 /var/log/nginx/error.log"
        )
    
    await message.reply_text(
        f"<pre>{truncate_for_tg(result_text, 3800)}</pre>",
        parse_mode="HTML",
    )
    
    logger.info(f"Rollback {'OK' if ok else 'PROBLEMS'}: {good_commit}, with_db={with_db}")


# --- Бэкапы и восстановление ---

@admin_required
async def cmd_backups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список доступных PG бэкапов"""
    output = run_cmd(
        f"echo '=== PostgreSQL Backups ===' && echo '' && "
        f"ls -lht {PG_BACKUP_DIR}/pg_*.sql.gz 2>/dev/null | head -15 | awk '{{printf \"%s %s %s  %s  %s\\n\", $6, $7, $8, $5, $9}}' && "
        f"echo '' && echo '=== Current DB Size ===' && "
        f"sudo -u postgres psql -d {PG_DB} -tAc 'SELECT pg_size_pretty(pg_database_size(current_database()));' 2>/dev/null && "
        f"echo '' && echo '=== Last Cron Backup ===' && "
        f"tail -3 {PG_BACKUP_DIR}/backup.log 2>/dev/null || echo 'No backup log'",
        timeout=10,
    )
    if not output.strip():
        output = "No backups found"
    await update.message.reply_text(
        f"<pre>{truncate_for_tg(output)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Восстановление PostgreSQL из бэкапа с выбором"""
    # Ищем PG бэкапы
    backups_raw = run_cmd(
        f"ls -t {PG_BACKUP_DIR}/pg_*.sql.gz 2>/dev/null | head -6"
    )
    
    if not backups_raw.strip() or "ERROR" in backups_raw:
        await update.message.reply_text("PG бэкапов не найдено.")
        return
    
    backups = [b.strip() for b in backups_raw.strip().split("\n") if b.strip()]
    if not backups:
        await update.message.reply_text("PG бэкапов не найдено.")
        return
    
    # Создаём кнопки для каждого бэкапа
    keyboard = []
    for i, backup_path in enumerate(backups[:5]):
        name = os.path.basename(backup_path)
        size = run_cmd(f"stat -c%s {backup_path} 2>/dev/null || echo '?'")
        try:
            size_kb = f"{int(size) / 1024:.0f}KB"
        except ValueError:
            size_kb = "?KB"
        label = f"{name} ({size_kb})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"restore_{i}")])
    
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
    
    # Сохраняем список бэкапов в pending
    _pending_confirms[update.effective_chat.id] = ("restore", time.time(), backups)
    
    await update.message.reply_text(
        "<b>Выбери PG бэкап для восстановления:</b>\n\n"
        "Перед заменой будет создан бэкап текущей БД.\n"
        "<b>Данные после бэкапа будут потеряны!</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# --- Git: ветки ---

@admin_required
async def cmd_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Текущая ветка и коммит"""
    output = run_cmd(
        f"cd {PROJECT_ROOT} && "
        'echo "Ветка: $(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD)"; '
        'echo "Коммит: $(git rev-parse --short HEAD)"; '
        'echo "Дата: $(git log -1 --format=\'%ci\')"; '
        'echo "Сообщение: $(git log -1 --format=\'%s\')"; '
        'echo ""; echo "Known good: $(cat /var/run/lectio-monitor/last_known_good 2>/dev/null || echo NOT SET)"; '
        'echo ""; echo "Незакоммиченные:"; git status --short 2>/dev/null | head -10'
    )
    await update.message.reply_text(
        f"<pre>{truncate_for_tg(output)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_branches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список веток"""
    output = run_cmd(
        f"cd {PROJECT_ROOT} && git fetch origin --prune 2>/dev/null; "
        'echo "=== Локальные ==="; git branch -v --no-color 2>&1 | head -10; '
        'echo ""; echo "=== Remote (origin) ==="; git branch -rv --no-color 2>&1 | grep -v HEAD | head -15'
    )
    await update.message.reply_text(
        f"<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


@admin_required  
async def cmd_git_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последние коммиты"""
    output = run_cmd(
        f"cd {PROJECT_ROOT} && git log --oneline --decorate -15 --no-color 2>&1"
    )
    await update.message.reply_text(
        f"<b>Git log (15):</b>\n<pre>{truncate_for_tg(output)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключение ветки с подтверждением. Использование: /switch branch_name"""
    args = context.args
    if not args:
        # Показываем доступные ветки
        branches_raw = run_cmd(
            f"cd {PROJECT_ROOT} && git fetch origin --prune 2>/dev/null; "
            "git branch -a --no-color 2>&1 | grep -v HEAD | sed 's/^[* ]*//' | sed 's|remotes/origin/||' | sort -u | head -10"
        )
        branches = [b.strip() for b in branches_raw.strip().split("\n") if b.strip()]
        
        if not branches:
            await update.message.reply_text("Веток не найдено")
            return
        
        keyboard = []
        current = run_cmd(f"cd {PROJECT_ROOT} && git branch --show-current 2>/dev/null").strip()
        for br in branches[:6]:
            marker = " (current)" if br == current else ""
            keyboard.append([InlineKeyboardButton(
                f"{br}{marker}",
                callback_data=f"switch_{br}"
            )])
        keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
        
        _pending_confirms[update.effective_chat.id] = ("switch_select", time.time())
        
        await update.message.reply_text(
            "<b>Выбери ветку для переключения:</b>\n\n"
            f"Текущая: <code>{current}</code>\n\n"
            "После переключения:\n"
            "1. git checkout + pull\n"
            "2. pip install\n"
            "3. migrate\n"
            "4. collectstatic\n"
            "5. restart сервисов",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return
    
    target_branch = args[0].strip()
    _pending_confirms[update.effective_chat.id] = ("switch", time.time(), target_branch)
    
    current = run_cmd(f"cd {PROJECT_ROOT} && git branch --show-current 2>/dev/null").strip()
    
    keyboard = [
        [
            InlineKeyboardButton("Переключить", callback_data=f"confirm_switch"),
            InlineKeyboardButton("Отмена", callback_data="cancel"),
        ]
    ]
    await update.message.reply_text(
        f"<b>SWITCH BRANCH</b>\n\n"
        f"Текущая: <code>{current}</code>\n"
        f"Целевая: <code>{target_branch}</code>\n\n"
        f"Действия:\n"
        f"1. Бэкап БД\n"
        f"2. git checkout {target_branch}\n"
        f"3. git pull\n"
        f"4. pip install\n"
        f"5. migrate\n"
        f"6. collectstatic + permissions\n"
        f"7. restart всех сервисов\n\n"
        f"<b>Подтвердить?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _do_switch_branch(message, target_branch: str):
    """Выполняет переключение ветки"""
    steps = []
    
    # 1. Maintenance mode
    run_cmd("touch /var/run/lectio-monitor/maintenance_mode /var/run/lectio-monitor/deploy_in_progress")
    steps.append("1. Maintenance mode ON")
    
    current = run_cmd(f"cd {PROJECT_ROOT} && git branch --show-current 2>/dev/null").strip()
    steps.append(f"2. Текущая ветка: {current}")
    
    # 3. Бэкап БД
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_cmd(f"sudo -u postgres pg_dump -Fc teaching_panel -f /tmp/pre_switch_{ts}.pgdump 2>/dev/null || true")
    steps.append(f"3. Backup: pre_switch_{ts}.pgdump")
    
    # 4. Stash незакоммиченных изменений
    stash_out = run_cmd(f"cd {PROJECT_ROOT} && git stash 2>&1")
    if "No local changes" not in stash_out:
        steps.append(f"4. Stash: {stash_out[-60:]}")
    else:
        steps.append("4. Stash: не нужен (чисто)")
    
    # 5. Снимаем immutable
    run_cmd(f"chattr -i {PROJECT_ROOT}/frontend/build/index.html {PROJECT_ROOT}/frontend/build/favicon.svg {PROJECT_ROOT}/teaching_panel/teaching_panel/settings.py 2>/dev/null || true")
    steps.append("5. Immutable flags removed")
    
    # 6. Fetch + checkout
    run_cmd(f"cd {PROJECT_ROOT} && git fetch origin 2>/dev/null")
    checkout_out = run_cmd(f"cd {PROJECT_ROOT} && git checkout {target_branch} 2>&1")
    steps.append(f"6. Checkout: {checkout_out[-80:]}")
    
    # 7. Pull latest
    pull_out = run_cmd(f"cd {PROJECT_ROOT} && git pull origin {target_branch} 2>&1")
    steps.append(f"7. Pull: {pull_out[-80:]}")
    
    # 8. pip install
    pip_out = run_cmd(
        f"cd {PROJECT_ROOT} && source venv/bin/activate && "
        "pip install -q -r teaching_panel/requirements.txt 2>&1 | tail -3 && echo PIP_OK",
        timeout=120,
    )
    steps.append(f"8. pip: {'OK' if 'PIP_OK' in pip_out else 'WARN'}")
    
    # 9. Migrate (безопасно, --noinput)
    migrate_out = run_cmd(
        f"cd {PROJECT_ROOT}/teaching_panel && source ../venv/bin/activate && "
        "python manage.py migrate --noinput 2>&1 | tail -5",
        timeout=60,
    )
    steps.append(f"9. Migrate: {migrate_out[-80:]}")
    
    # 10. Collectstatic
    run_cmd(f"cd {PROJECT_ROOT}/teaching_panel && source ../venv/bin/activate && python manage.py collectstatic --noinput --clear 2>/dev/null || true")
    steps.append("10. Collectstatic done")
    
    # 11. Fix permissions
    run_cmd(f"chown -R www-data:www-data {PROJECT_ROOT}/frontend/build {PROJECT_ROOT}/staticfiles {PROJECT_ROOT}/media 2>/dev/null; chmod -R 755 {PROJECT_ROOT}/frontend/build {PROJECT_ROOT}/staticfiles 2>/dev/null")
    steps.append("11. Permissions fixed")
    
    # 12. Restart
    run_cmd("systemctl restart teaching_panel celery celery-beat nginx 2>/dev/null || true")
    steps.append("12. Services restarted")
    
    # 13. Restore immutable
    run_cmd(f"chattr +i {PROJECT_ROOT}/frontend/build/index.html {PROJECT_ROOT}/frontend/build/favicon.svg {PROJECT_ROOT}/teaching_panel/teaching_panel/settings.py 2>/dev/null || true")
    steps.append("13. Immutable restored")
    
    # 14. Verify
    await asyncio.sleep(5)
    health = run_cmd('curl -so/dev/null -w"%{http_code}" --max-time 5 http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" -H "X-Forwarded-Proto: https"')
    front = run_cmd('curl -so/dev/null -w"%{http_code}" --max-time 5 https://lectiospace.ru/')
    new_branch = run_cmd(f"cd {PROJECT_ROOT} && git branch --show-current 2>/dev/null").strip()
    new_commit = run_cmd(f"cd {PROJECT_ROOT} && git rev-parse --short HEAD").strip()
    steps.append(f"14. Verify: health={health} frontend={front}")
    steps.append(f"15. Ветка: {new_branch} @ {new_commit}")
    
    # 15. Maintenance off
    run_cmd("rm -f /var/run/lectio-monitor/maintenance_mode /var/run/lectio-monitor/deploy_in_progress")
    steps.append("16. Maintenance mode OFF")
    
    ok = health.strip() == "200" and front.strip() == "200"
    header = f"SWITCH OK: {new_branch}" if ok else "SWITCH - ПРОБЛЕМЫ!"
    
    result_text = f"<b>{header}</b>\n\n" + "\n".join(steps)
    if not ok:
        result_text += (
            f"\n\nДля отката: /switch {current}\n"
            f"Или: /rollback"
        )
    
    await message.reply_text(
        f"<pre>{truncate_for_tg(result_text, 3800)}</pre>",
        parse_mode="HTML",
    )
    logger.info(f"Switch branch {'OK' if ok else 'PROBLEMS'}: {current} -> {target_branch}")


async def _do_restore_db(message, backup_path: str):
    """Восстанавливает PostgreSQL из указанного PG дампа"""
    steps = []
    
    # Проверяем что файл существует
    check = run_cmd(f"test -f {backup_path} && echo EXISTS || echo MISSING")
    if "MISSING" in check:
        await message.reply_text(f"File not found: {backup_path}")
        return
    
    # 1. Maintenance mode
    run_cmd(f"touch {STATE_DIR}/maintenance_mode")
    steps.append("1. Maintenance mode ON")
    
    # 2. Backup current DB
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pre_restore = f"{PG_BACKUP_DIR}/pg_pre_restore_{ts}.sql.gz"
    run_cmd(f"sudo -u postgres pg_dump {PG_DB} 2>/dev/null | gzip > {pre_restore}", timeout=60)
    steps.append(f"2. Backup current: pg_pre_restore_{ts}.sql.gz")
    
    # 3. Integrity check backup (gzip + has tables)
    gz_ok = "ok" in run_cmd(f"gzip -t {backup_path} 2>&1 && echo ok || echo fail")
    steps.append(f"3. Gzip integrity: {'OK' if gz_ok else 'FAIL'}")
    if not gz_ok:
        run_cmd(f"rm -f {STATE_DIR}/maintenance_mode")
        steps.append("ABORTED: backup is corrupted!")
        result_lines = "\n".join(steps)
        await message.reply_text(f"<pre>{result_lines}</pre>", parse_mode="HTML")
        return
    
    # 4. Restore: drop + recreate + load
    restore_out = run_cmd(
        f"sudo -u postgres psql -c 'SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=\'{PG_DB}\' AND pid <> pg_backend_pid();' 2>/dev/null; "
        f"sudo -u postgres dropdb --if-exists {PG_DB} 2>&1; "
        f"sudo -u postgres createdb -O {PG_USER} {PG_DB} 2>&1; "
        f"zcat {backup_path} | sudo -u postgres psql -d {PG_DB} 2>&1 | tail -3",
        timeout=120,
    )
    steps.append(f"4. Restored from {os.path.basename(backup_path)}")
    
    # 5. Restart Django
    run_cmd("systemctl restart teaching_panel 2>/dev/null || true")
    steps.append("5. teaching_panel restarted")
    
    # 6. Verify
    await asyncio.sleep(3)
    health = run_cmd('curl -so/dev/null -w"%{http_code}" --max-time 5 http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" -H "X-Forwarded-Proto: https"')
    user_count = run_cmd(f"sudo -u postgres psql -d {PG_DB} -tAc 'SELECT count(*) FROM accounts_customuser;' 2>/dev/null").strip()
    steps.append(f"6. Health: {health}, Users: {user_count}")
    
    # 7. Maintenance off
    run_cmd(f"rm -f {STATE_DIR}/maintenance_mode")
    steps.append("7. Maintenance mode OFF")
    
    ok = health.strip() == "200"
    header = "RESTORE OK" if ok else "RESTORE - PROBLEMS!"
    
    result_text = f"<b>{header}</b>\n\n" + "\n".join(steps)
    if not ok:
        result_text += f"\n\nRollback: restore from {pre_restore}"
    
    await message.reply_text(
        f"<pre>{truncate_for_tg(result_text, 3800)}</pre>",
        parse_mode="HTML",
    )
    logger.info(f"PG restore {'OK' if ok else 'PROBLEMS'}: {backup_path}")


# --- Алерты: mute/unmute ---

@admin_required
async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заглушить алерты guardian на N минут/часов"""
    if not context.args:
        await update.message.reply_text(
            "Использование: /mute 30m\n"
            "Форматы: 30m, 2h, 1d, 300s"
        )
        return
    seconds = _parse_duration(context.args[0])
    if seconds is None:
        await update.message.reply_text("Неверный формат. Примеры: 30m, 2h, 1d")
        return
    result = _set_mute(seconds)
    await update.message.reply_text(result)


@admin_required
async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Снять заглушку алертов"""
    result = _clear_mute()
    await update.message.reply_text(result)


@admin_required
async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статус алертов + последние алерты из лога"""
    mute_status = _get_mute_status()
    guardian_mode = run_cmd(
        f'if [ -f {STATE_DIR}/maintenance_mode ]; then echo "PAUSED (maintenance)"; '
        f'elif [ -f {STATE_DIR}/deploy_in_progress ]; then echo "DEPLOY IN PROGRESS"; '
        f'else echo "ACTIVE"; fi'
    )
    # Последние алерты из guardian лога
    recent_alerts = run_cmd(
        f"grep -i 'ALERT\\|FAIL\\|ERROR\\|RECOVER\\|L[123]' {LOG_DIR}/guardian.log 2>/dev/null | tail -10"
    )

    text = (
        f"<b>Alerts</b>\n\n"
        f"{mute_status}\n"
        f"Guardian: {guardian_mode}\n\n"
    )
    if recent_alerts.strip():
        text += f"<b>Recent events:</b>\n<pre>{truncate_for_tg(recent_alerts, 2500)}</pre>"
    else:
        text += "No recent alerts."

    await update.message.reply_text(text, parse_mode="HTML")


# ====================================================================
# SOLO-DEV COMMANDS: практичные команды для единственного разработчика
# ====================================================================

@admin_required
async def cmd_deploy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick deploy: git pull + pip + migrate + collectstatic + restart"""
    _pending_confirms[update.effective_chat.id] = ("deploy", time.time())
    current = run_cmd(f"cd {PROJECT_ROOT} && git rev-parse --short HEAD").strip()
    branch = run_cmd(f"cd {PROJECT_ROOT} && git branch --show-current 2>/dev/null").strip()
    # Check if there are remote changes
    run_cmd(f"cd {PROJECT_ROOT} && git fetch origin {branch} 2>/dev/null", timeout=15)
    behind = run_cmd(f"cd {PROJECT_ROOT} && git rev-list HEAD..origin/{branch} --count 2>/dev/null").strip()

    keyboard = [[
        InlineKeyboardButton("DEPLOY", callback_data="confirm_deploy"),
        InlineKeyboardButton("Cancel", callback_data="cancel"),
    ]]
    await update.message.reply_text(
        f"<b>QUICK DEPLOY</b>\n\n"
        f"Branch: <code>{branch}</code>\n"
        f"Current: <code>{current}</code>\n"
        f"Commits behind origin: <b>{behind}</b>\n\n"
        f"Steps:\n"
        f"1. Backup DB\n"
        f"2. Remove immutable\n"
        f"3. git pull\n"
        f"4. pip install\n"
        f"5. migrate\n"
        f"6. collectstatic\n"
        f"7. Restart services\n"
        f"8. Restore immutable\n"
        f"9. Verify\n\n"
        f"<b>Confirm?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _do_deploy(message):
    """Выполняет quick deploy"""
    steps = []
    branch = run_cmd(f"cd {PROJECT_ROOT} && git branch --show-current 2>/dev/null").strip()

    # 1. Maintenance + deploy lock
    run_cmd(f"touch {STATE_DIR}/maintenance_mode {STATE_DIR}/deploy_in_progress")
    steps.append("1. Maintenance ON")

    # 2. Backup DB (PostgreSQL)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pre_deploy = f"{PG_BACKUP_DIR}/pg_pre_deploy_{ts}.sql.gz"
    run_cmd(f"sudo -u postgres pg_dump {PG_DB} 2>/dev/null | gzip > {pre_deploy}", timeout=60)
    steps.append(f"2. PG backup: pg_pre_deploy_{ts}.sql.gz")

    # 3. Remove immutable
    run_cmd(
        f"chattr -i {PROJECT_ROOT}/frontend/build/index.html "
        f"{PROJECT_ROOT}/frontend/build/favicon.svg "
        f"{PROJECT_ROOT}/teaching_panel/teaching_panel/settings.py 2>/dev/null || true"
    )
    steps.append("3. Immutable removed")

    # 4. Git pull
    pull_out = run_cmd(f"cd {PROJECT_ROOT} && git pull origin {branch} 2>&1", timeout=30)
    steps.append(f"4. Pull: {pull_out[-100:]}")

    # 5. pip install
    pip_out = run_cmd(
        f"cd {PROJECT_ROOT} && source venv/bin/activate && "
        "pip install -q -r teaching_panel/requirements.txt 2>&1 | tail -3 && echo PIP_OK",
        timeout=120,
    )
    steps.append(f"5. pip: {'OK' if 'PIP_OK' in pip_out else 'WARN'}")

    # 6. Migrate
    migrate_out = run_cmd(
        f"cd {PROJECT_ROOT}/teaching_panel && source ../venv/bin/activate && "
        "python manage.py migrate --noinput 2>&1 | tail -5",
        timeout=60,
    )
    steps.append(f"6. Migrate: {migrate_out[-80:]}")

    # 7. Collectstatic
    run_cmd(
        f"cd {PROJECT_ROOT}/teaching_panel && source ../venv/bin/activate && "
        "python manage.py collectstatic --noinput --clear 2>/dev/null || true"
    )
    steps.append("7. Collectstatic done")

    # 8. Fix permissions
    run_cmd(
        f"chown -R www-data:www-data {PROJECT_ROOT}/frontend/build "
        f"{PROJECT_ROOT}/staticfiles {PROJECT_ROOT}/media 2>/dev/null; "
        f"chmod -R 755 {PROJECT_ROOT}/frontend/build {PROJECT_ROOT}/staticfiles 2>/dev/null"
    )
    steps.append("8. Permissions fixed")

    # 9. Restart
    run_cmd("systemctl restart teaching_panel celery celery-beat nginx 2>/dev/null || true")
    steps.append("9. Services restarted")

    # 10. Restore immutable
    run_cmd(
        f"chattr +i {PROJECT_ROOT}/frontend/build/index.html "
        f"{PROJECT_ROOT}/frontend/build/favicon.svg "
        f"{PROJECT_ROOT}/teaching_panel/teaching_panel/settings.py 2>/dev/null || true"
    )
    steps.append("10. Immutable restored")

    # 11. Verify
    await asyncio.sleep(5)
    health = run_cmd(
        'curl -so/dev/null -w"%{http_code}" --max-time 5 '
        'http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" -H "X-Forwarded-Proto: https"'
    )
    front = run_cmd('curl -so/dev/null -w"%{http_code}" --max-time 5 https://lectiospace.ru/')
    new_commit = run_cmd(f"cd {PROJECT_ROOT} && git rev-parse --short HEAD").strip()
    steps.append(f"11. Verify: health={health} frontend={front}")
    steps.append(f"12. Now at: {new_commit}")

    # 12. Maintenance off, save known_good if ok
    run_cmd(f"rm -f {STATE_DIR}/maintenance_mode {STATE_DIR}/deploy_in_progress")
    ok = health.strip() == "200" and front.strip() == "200"
    if ok:
        run_cmd(f"echo '{new_commit} deploy {ts}' > {KNOWN_GOOD_FILE}")
        steps.append("13. Saved as known_good")

    header = f"DEPLOY OK: {new_commit}" if ok else "DEPLOY PROBLEMS!"
    result = f"<b>{header}</b>\n\n" + "\n".join(steps)
    if not ok:
        result += f"\n\nRollback: /rollback\nBackup: {pre_deploy}"

    await message.reply_text(f"<pre>{truncate_for_tg(result, 3800)}</pre>", parse_mode="HTML")
    logger.info(f"Deploy {'OK' if ok else 'PROBLEMS'}: {new_commit}")


@admin_required
async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создать бэкап PostgreSQL прямо сейчас"""
    await update.message.reply_text("Creating PG backup...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{PG_BACKUP_DIR}/pg_manual_{ts}.sql.gz"
    dump_out = run_cmd(
        f"sudo -u postgres pg_dump {PG_DB} 2>&1 | gzip > {backup_path}",
        timeout=60,
    )
    # Verify
    size = run_cmd(f"stat -c%s {backup_path} 2>/dev/null || echo '0'")
    try:
        size_kb = f"{int(size) / 1024:.0f}KB"
    except ValueError:
        size_kb = "?"
    # Quick integrity: check gzip and contains CREATE TABLE
    gz_ok = "ok" in run_cmd(f"gzip -t {backup_path} 2>&1 && echo ok || echo fail")
    has_tables = run_cmd(f"zcat {backup_path} 2>/dev/null | grep -c 'CREATE TABLE'")
    try:
        has_tables_ok = int(has_tables.strip()) > 0
    except ValueError:
        has_tables_ok = False
    ok = gz_ok and has_tables_ok and int(size or '0') > 1000
    status = "OK" if ok else "WARN: backup may be empty or corrupt"
    await update.message.reply_text(
        f"<b>PG Backup created</b>\n\n"
        f"File: <code>{backup_path}</code>\n"
        f"Size: {size_kb}\n"
        f"Gzip: {'OK' if gz_ok else 'FAIL'}\n"
        f"Tables: {'found' if has_tables else 'NONE'}\n"
        f"Status: {status}",
        parse_mode="HTML",
    )
    logger.info(f"Manual PG backup: {backup_path} ({size_kb}, ok={ok})")


@admin_required
async def cmd_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последние 500 ошибки с деталями"""
    output = run_cmd("""
echo "=== RECENT 5xx (nginx access.log) ==="
awk '$9 ~ /^5[0-9][0-9]$/ {print $1, $4, $7, $9}' /var/log/nginx/access.log 2>/dev/null | tail -15
echo ""
echo "=== GUNICORN TRACEBACKS ==="
grep -A3 'Traceback\\|Error\\|Exception' /var/log/syslog 2>/dev/null | grep -i 'teaching_panel\\|gunicorn' | tail -15
echo ""
echo "=== DJANGO ERRORS (last 20 lines with ERROR) ==="
journalctl -u teaching_panel --no-pager 2>/dev/null | grep -i 'error\\|exception\\|traceback' | tail -15
""", timeout=15)
    if not output.strip() or output.strip() == "=== RECENT 5xx (nginx access.log) ===\n\n=== GUNICORN TRACEBACKS ===\n\n=== DJANGO ERRORS (last 20 lines with ERROR) ===":
        output = "No recent errors found."
    await update.message.reply_text(
        f"<b>Recent errors</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика пользователей из PostgreSQL"""
    output = run_cmd(
        f"echo '=== USERS ===' && "
        f"echo 'Total:' $(sudo -u postgres psql -d {PG_DB} -tAc 'SELECT COUNT(*) FROM accounts_customuser;' 2>/dev/null) && "
        f"echo 'Teachers:' $(sudo -u postgres psql -d {PG_DB} -tAc \"SELECT COUNT(*) FROM accounts_customuser WHERE role='teacher';\" 2>/dev/null) && "
        f"echo 'Students:' $(sudo -u postgres psql -d {PG_DB} -tAc \"SELECT COUNT(*) FROM accounts_customuser WHERE role='student';\" 2>/dev/null) && "
        f"echo 'Admins:' $(sudo -u postgres psql -d {PG_DB} -tAc \"SELECT COUNT(*) FROM accounts_customuser WHERE role='admin';\" 2>/dev/null) && "
        f"echo '' && "
        f"echo '=== RECENT REGISTRATIONS ===' && "
        f"sudo -u postgres psql -d {PG_DB} -c 'SELECT date_joined::date, email, role FROM accounts_customuser ORDER BY date_joined DESC LIMIT 10;' 2>/dev/null && "
        f"echo '' && "
        f"echo '=== SUBSCRIPTIONS ===' && "
        f"sudo -u postgres psql -d {PG_DB} -c 'SELECT status, count(*) FROM accounts_subscription GROUP BY status;' 2>/dev/null && "
        f"echo '' && "
        f"echo '=== RECENT LOGINS ===' && "
        f"sudo -u postgres psql -d {PG_DB} -c 'SELECT last_login::timestamp(0), email FROM accounts_customuser WHERE last_login IS NOT NULL ORDER BY last_login DESC LIMIT 5;' 2>/dev/null",
        timeout=15,
    )
    await update.message.reply_text(
        f"<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_ssl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка SSL-сертификата"""
    output = run_cmd(
        'echo | openssl s_client -servername lectiospace.ru -connect lectiospace.ru:443 2>/dev/null | '
        'openssl x509 -noout -dates -subject -issuer 2>&1; '
        'echo ""; '
        'EXPIRY=$(echo | openssl s_client -servername lectiospace.ru -connect lectiospace.ru:443 2>/dev/null | '
        'openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2); '
        'if [ -n "$EXPIRY" ]; then '
        '  EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null); '
        '  NOW=$(date +%s); '
        '  DAYS=$(( (EPOCH - NOW) / 86400 )); '
        '  echo "Days until expiry: $DAYS"; '
        '  if [ "$DAYS" -lt 14 ]; then echo "WARNING: Certificate expiring soon!"; fi; '
        'fi',
        timeout=15,
    )
    await update.message.reply_text(
        f"<b>SSL Certificate</b>\n<pre>{truncate_for_tg(output)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_celery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статус Celery worker + beat"""
    output = run_cmd("""
echo "=== CELERY WORKER ==="
systemctl is-active celery 2>/dev/null || echo "not found"
echo ""
echo "=== CELERY BEAT ==="
systemctl is-active celery-beat 2>/dev/null || echo "not found"
echo ""
echo "=== WORKER PROCESSES ==="
ps aux | grep '[c]elery' | awk '{printf "  PID=%s CPU=%s MEM=%s %s\\n", $2, $3, $4, $11}' | head -5
echo ""
echo "=== REDIS (queue backend) ==="
redis-cli ping 2>/dev/null || echo "Redis not responding"
redis-cli info keyspace 2>/dev/null | head -5
echo ""
echo "=== RECENT CELERY LOGS ==="
journalctl -u celery -n 10 --no-pager 2>&1 | tail -10
""", timeout=15)
    await update.message.reply_text(
        f"<b>Celery status</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Аптайм сервисов"""
    output = run_cmd("""
echo "=== SERVER ==="
uptime
echo ""
echo "=== SERVICE UPTIMES ==="
for svc in teaching_panel nginx celery celery-beat redis-server telegram_bot support_bot lectio-ops-bot; do
    STATUS=$(systemctl is-active $svc 2>/dev/null)
    if [ "$STATUS" = "active" ]; then
        SINCE=$(systemctl show $svc --property=ActiveEnterTimestamp 2>/dev/null | cut -d= -f2)
        printf "  %-22s active since %s\\n" "$svc" "$SINCE"
    else
        printf "  %-22s %s\\n" "$svc" "$STATUS"
    fi
done
echo ""
echo "=== RESTARTS TODAY ==="
journalctl --since today | grep -c 'Started\\|Stopped' 2>/dev/null || echo "0"
""", timeout=15)
    await update.message.reply_text(
        f"<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Здоровье PostgreSQL"""
    output = run_cmd(
        f"echo '=== DATABASE ===' && "
        f"echo 'Engine: PostgreSQL 12' && "
        f"echo 'Name: {PG_DB}' && "
        f"echo 'Size:' $(sudo -u postgres psql -d {PG_DB} -tAc 'SELECT pg_size_pretty(pg_database_size(current_database()));' 2>/dev/null) && "
        f"echo '' && "
        f"echo '=== CONNECTIONS ===' && "
        f"sudo -u postgres psql -d {PG_DB} -tAc \"SELECT count(*) || ' active, ' || (SELECT setting FROM pg_settings WHERE name='max_connections') || ' max' FROM pg_stat_activity WHERE datname='{PG_DB}';\" 2>/dev/null && "
        f"echo '' && "
        f"echo '=== TOP 10 TABLES BY SIZE ===' && "
        f"sudo -u postgres psql -d {PG_DB} -c 'SELECT relname AS \"table\", pg_size_pretty(pg_total_relation_size(relid)) AS size, n_live_tup AS rows FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;' 2>/dev/null && "
        f"echo '' && "
        f"echo '=== PENDING MIGRATIONS ===' && "
        f"cd {PROJECT_ROOT}/teaching_panel && source ../venv/bin/activate && python manage.py showmigrations --plan 2>/dev/null | grep '\\[ \\]' | head -5 || echo 'None' && "
        f"echo '' && "
        f"echo '=== LAST PG BACKUP ===' && "
        f"ls -lht {PG_BACKUP_DIR}/pg_*.sql.gz 2>/dev/null | head -1 | awk '{{print $6, $7, $8, $5, $9}}'",
        timeout=20,
    )
    await update.message.reply_text(
        f"<b>Database health</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_resetpw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс пароля пользователя: /resetpw email@example.com"""
    args = context.args
    if not args:
        await update.message.reply_text(
            "<b>Usage:</b> /resetpw email@example.com\n\n"
            "Generates a new random password for the user.",
            parse_mode="HTML",
        )
        return

    email = args[0].strip().lower()

    # Generate 12-char password: letters + digits + special
    new_pw = run_cmd(
        f"cd {PROJECT_ROOT}/teaching_panel && source ../venv/bin/activate && "
        f"python -c \""
        f"import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','teaching_panel.settings'); django.setup(); "
        f"from accounts.models import CustomUser; from django.utils.crypto import get_random_string; "
        f"pw = get_random_string(12, 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#'); "
        f"u = CustomUser.objects.get(email='{email}'); u.set_password(pw); u.save(); "
        f"print('OK:' + pw)\"",
        timeout=15,
    )

    if new_pw.startswith("OK:"):
        password = new_pw[3:]
        await update.message.reply_text(
            f"Password reset for <b>{email}</b>\n\n"
            f"<tg-spoiler>{password}</tg-spoiler>\n\n"
            f"(tap to reveal, send to user privately)",
            parse_mode="HTML",
        )
    elif "DoesNotExist" in new_pw:
        await update.message.reply_text(f"User <b>{email}</b> not found.", parse_mode="HTML")
    else:
        await update.message.reply_text(
            f"<b>Error:</b>\n<pre>{truncate_for_tg(new_pw, 1000)}</pre>",
            parse_mode="HTML",
        )


@admin_required
async def cmd_adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание пользователя: /adduser email@example.com [role]"""
    args = context.args
    if not args:
        await update.message.reply_text(
            "<b>Usage:</b> /adduser email@example.com [role]\n\n"
            "Roles: student (default), teacher, admin\n"
            "A random password will be generated.",
            parse_mode="HTML",
        )
        return

    email = args[0].strip().lower()
    role = args[1].strip().lower() if len(args) > 1 else "student"

    if role not in ("student", "teacher", "admin"):
        await update.message.reply_text(
            f"Invalid role: <b>{role}</b>\nAllowed: student, teacher, admin",
            parse_mode="HTML",
        )
        return

    result = run_cmd(
        f"cd {PROJECT_ROOT}/teaching_panel && source ../venv/bin/activate && "
        f"python -c \""
        f"import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','teaching_panel.settings'); django.setup(); "
        f"from accounts.models import CustomUser; from django.utils.crypto import get_random_string; "
        f"if CustomUser.objects.filter(email='{email}').exists(): print('EXISTS'); "
        f"else: "
        f"  pw = get_random_string(12, 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#'); "
        f"  u = CustomUser.objects.create_user(email='{email}', password=pw, role='{role}'); "
        f"  print('OK:' + pw + ':' + str(u.id))\"",
        timeout=15,
    )

    if result.startswith("OK:"):
        parts = result[3:].split(":", 1)
        password = parts[0]
        uid = parts[1] if len(parts) > 1 else "?"
        await update.message.reply_text(
            f"User created!\n\n"
            f"Email: <b>{email}</b>\n"
            f"Role: <b>{role}</b>\n"
            f"ID: <b>{uid}</b>\n"
            f"Password: <tg-spoiler>{password}</tg-spoiler>\n\n"
            f"(tap to reveal, send credentials privately)",
            parse_mode="HTML",
        )
    elif "EXISTS" in result:
        await update.message.reply_text(
            f"User <b>{email}</b> already exists. Use /resetpw to reset password.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            f"<b>Error:</b>\n<pre>{truncate_for_tg(result, 1000)}</pre>",
            parse_mode="HTML",
        )


@admin_required
async def cmd_nginx_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тест конфигурации nginx"""
    output = run_cmd("nginx -t 2>&1")
    ok = "successful" in output
    header = "Nginx config OK" if ok else "Nginx config ERRORS!"
    await update.message.reply_text(
        f"<b>{header}</b>\n<pre>{truncate_for_tg(output)}</pre>",
        parse_mode="HTML",
    )


@admin_required
async def cmd_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистка старых файлов (бэкапы, кэш, логи)"""
    output = run_cmd(f"""
echo "=== BEFORE ==="
echo "Backups in /tmp: $(ls /tmp/*.pgdump 2>/dev/null | wc -l) files, $(du -sh /tmp/*.pgdump 2>/dev/null | tail -1 | awk '{{print $1}}')"
echo "Logs: $(du -sh /var/log/lectio-monitor 2>/dev/null | awk '{{print $1}}')"
echo "Pycache: $(find {PROJECT_ROOT} -name __pycache__ -type d 2>/dev/null | wc -l) dirs"
echo ""

# Keep only 5 newest backups
echo "=== CLEANING OLD BACKUPS (keep 5) ==="
ls -t /tmp/deploy_*.pgdump /tmp/backup_*.pgdump /tmp/pre_*.pgdump /tmp/manual_backup_*.pgdump 2>/dev/null | tail -n +6 | while read f; do
    echo "  Removing: $(basename $f)"
    rm -f "$f"
done
echo "Done"
echo ""

# Clean pycache
echo "=== CLEANING PYCACHE ==="
find {PROJECT_ROOT} -name __pycache__ -type d -exec rm -rf {{}} + 2>/dev/null
echo "Done"
echo ""

# Truncate old logs
echo "=== TRUNCATING OLD LOGS ==="
find /var/log/lectio-monitor -name '*.log' -size +10M 2>/dev/null | while read f; do
    echo "  Truncating: $(basename $f) ($(du -sh $f | awk '{{print $1}}'))"
    tail -1000 "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
echo "Done"
echo ""

echo "=== AFTER ==="
echo "Backups in /tmp: $(ls /tmp/*.pgdump 2>/dev/null | wc -l) files"
echo "Disk free: $(df / | awk 'NR==2{{print $4}}')KB"
""", timeout=30)
    await update.message.reply_text(
        f"<b>Cleanup done</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
        parse_mode="HTML",
    )


# --- Menu callback handler ---

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка inline кнопок меню"""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    if not is_admin(update):
        await query.edit_message_text("Access denied.")
        return

    data = query.data

    # --- Navigation between menu sections ---
    if data == "menu_main":
        health = run_cmd(
            'curl -so/dev/null -w"%{http_code}" --max-time 3 '
            'http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" '
            '-H "X-Forwarded-Proto: https" 2>/dev/null || echo "fail"',
            timeout=5,
        )
        is_ok = health.strip() == "200"
        status_line = "OK" if is_ok else f"PROBLEM ({health.strip()})"
        mute_line = _get_mute_status()
        await query.edit_message_text(
            f"<b>Lectio OPS</b>\n\n"
            f"Site: <b>{status_line}</b>\n"
            f"{mute_line}\n\n"
            f"Choose a section:",
            parse_mode="HTML",
            reply_markup=_main_menu_keyboard(),
        )
        return

    if data == "menu_monitoring":
        await query.edit_message_text(
            "<b>Monitoring</b>\nSelect action:",
            parse_mode="HTML",
            reply_markup=_monitoring_menu(),
        )
        return

    if data == "menu_management":
        await query.edit_message_text(
            "<b>Management</b>\nSelect action:",
            parse_mode="HTML",
            reply_markup=_management_menu(),
        )
        return

    if data == "menu_emergency":
        await query.edit_message_text(
            "<b>Emergency</b>\nDangerous actions (require confirm):",
            parse_mode="HTML",
            reply_markup=_emergency_menu(),
        )
        return

    if data == "menu_backups":
        await query.edit_message_text(
            "<b>Backups</b>\nSelect action:",
            parse_mode="HTML",
            reply_markup=_backups_menu(),
        )
        return

    if data == "menu_git":
        await query.edit_message_text(
            "<b>Git</b>\nSelect action:",
            parse_mode="HTML",
            reply_markup=_git_menu(),
        )
        return

    if data == "menu_alerts":
        mute_line = _get_mute_status()
        await query.edit_message_text(
            f"<b>Alerts</b>\n{mute_line}\n\nSelect action:",
            parse_mode="HTML",
            reply_markup=_alerts_menu(),
        )
        return

    # --- Действия из меню (отправляют результат новым сообщением) ---
    # Мы НЕ можем редактировать текущее сообщение с результатом длинной команды
    # и одновременно сохранить клавиатуру. Поэтому результат — новое сообщение,
    # а меню остается на месте.

    msg = query.message  # Для ответа новым сообщением

    # --- SOS & Quick Actions ---
    if data == "act_sos":
        await query.edit_message_text("SOS: starting auto-recovery...")
        await _auto_revive(msg)
        return

    if data == "act_quick_restart":
        await query.edit_message_text("Quick restart: gunicorn + celery + nginx...")
        output = run_cmd(
            "systemctl restart teaching_panel celery celery-beat nginx 2>&1 && "
            "sleep 4 && "
            'HEALTH=$(curl -so/dev/null -w"%{http_code}" --max-time 5 '
            'http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" '
            '-H "X-Forwarded-Proto: https" 2>/dev/null) && '
            'echo "Services restarted. Health: $HEALTH"',
            timeout=30,
        )
        await msg.reply_text(f"<pre>{output}</pre>", parse_mode="HTML")
        return

    if data == "act_quick_backup":
        await query.edit_message_text("Creating PG backup...")
        ts_now = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{PG_BACKUP_DIR}/pg_quick_{ts_now}.sql.gz"
        run_cmd(
            f"sudo -u postgres pg_dump {PG_DB} 2>/dev/null | gzip > {backup_path}",
            timeout=60,
        )
        size = run_cmd(f"stat -c%s {backup_path} 2>/dev/null || echo '0'")
        try:
            size_kb = f"{int(size.strip()) / 1024:.0f} KB"
        except ValueError:
            size_kb = "?"
        verify = run_cmd(f"zcat {backup_path} 2>/dev/null | head -1")
        ok = "PostgreSQL" in verify or "pg_dump" in verify
        status = "OK" if ok else "CHECK MANUALLY"
        await msg.reply_text(
            f"<b>Quick Backup</b>\n"
            f"File: <code>{backup_path}</code>\n"
            f"Size: {size_kb}\n"
            f"Status: {status}",
            parse_mode="HTML",
        )
        return

    if data == "act_status":
        await query.edit_message_text("Collecting status...")
        await _run_status(msg)
        return

    if data == "act_health":
        output = run_cmd(
            'curl -s -w "\\nHTTP: %{http_code}\\nTime: %{time_total}s" '
            '--max-time 10 http://127.0.0.1:8000/api/health/ '
            '-H "Host: lectiospace.ru" -H "X-Forwarded-Proto: https"',
            timeout=15,
        )
        await msg.reply_text(f"<pre>{truncate_for_tg(output)}</pre>", parse_mode="HTML")
        return

    if data == "act_logs":
        output = run_cmd("journalctl -u teaching_panel -n 30 --no-pager 2>&1")
        await msg.reply_text(
            f"<b>Gunicorn logs (30)</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
            parse_mode="HTML",
        )
        return

    if data == "act_logs_nginx":
        output = run_cmd("tail -30 /var/log/nginx/error.log 2>&1")
        await msg.reply_text(
            f"<b>Nginx error log (30)</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
            parse_mode="HTML",
        )
        return

    if data == "act_logs_guardian":
        output = run_cmd("tail -40 /var/log/lectio-monitor/guardian.log 2>&1")
        await msg.reply_text(
            f"<b>Guardian log (40)</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
            parse_mode="HTML",
        )
        return

    if data == "act_disk":
        output = run_cmd(
            "df -h / /tmp 2>&1; echo ''; "
            f"du -sh {PROJECT_ROOT}/media /var/log 2>/dev/null; echo ''; "
            "sudo -u postgres psql teaching_panel -t -c \"SELECT pg_size_pretty(pg_database_size('teaching_panel'));\" 2>/dev/null | xargs -I{} echo 'DB size: {}'"
        )
        await msg.reply_text(f"<pre>{truncate_for_tg(output)}</pre>", parse_mode="HTML")
        return

    if data == "act_top":
        output = run_cmd("ps aux --sort=-%cpu | head -15 2>&1")
        await msg.reply_text(f"<pre>{truncate_for_tg(output)}</pre>", parse_mode="HTML")
        return

    if data == "act_restart":
        await query.edit_message_text("Restarting gunicorn + celery...")
        output = run_cmd(
            "systemctl restart teaching_panel celery celery-beat 2>&1 && "
            "sleep 3 && echo 'Restart done' && "
            'curl -so/dev/null -w"Health: %{http_code}" --max-time 5 '
            'http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" '
            '-H "X-Forwarded-Proto: https"',
            timeout=30,
        )
        await msg.reply_text(f"<pre>{output}</pre>", parse_mode="HTML")
        return

    if data == "act_restart_all":
        await query.edit_message_text("Restarting ALL services...")
        output = run_cmd(
            "systemctl restart teaching_panel celery celery-beat nginx redis-server 2>&1 && "
            "sleep 5 && echo 'Restart done' && "
            'HEALTH=$(curl -so/dev/null -w"%{http_code}" --max-time 5 '
            'http://127.0.0.1:8000/api/health/ -H "Host: lectiospace.ru" '
            '-H "X-Forwarded-Proto: https") && '
            'FRONT=$(curl -so/dev/null -w"%{http_code}" --max-time 5 https://lectiospace.ru/) && '
            'echo "Health: $HEALTH  Frontend: $FRONT"',
            timeout=40,
        )
        await msg.reply_text(f"<pre>{output}</pre>", parse_mode="HTML")
        return

    if data == "act_guardian":
        await query.edit_message_text("Running guardian check...")
        output = run_cmd(
            "/opt/lectio-monitor/guardian.sh 2>&1; echo '---'; "
            "tail -5 /var/log/lectio-monitor/guardian.log",
            timeout=60,
        )
        await msg.reply_text(
            f"<b>Guardian result:</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
            parse_mode="HTML",
        )
        return

    if data == "act_pause":
        run_cmd(f"mkdir -p {STATE_DIR} && touch {STATE_DIR}/maintenance_mode")
        await msg.reply_text("Guardian paused (maintenance mode ON)")
        return

    if data == "act_resume":
        run_cmd(f"rm -f {STATE_DIR}/maintenance_mode {STATE_DIR}/deploy_in_progress")
        await msg.reply_text("Guardian resumed (maintenance mode OFF)")
        return

    if data == "act_deploy_lock":
        run_cmd(f"mkdir -p {STATE_DIR} && touch {STATE_DIR}/deploy_in_progress")
        await msg.reply_text("Deploy locked (guardian paused)")
        return

    if data == "act_deploy_unlock":
        run_cmd(f"rm -f {STATE_DIR}/deploy_in_progress")
        await msg.reply_text("Deploy unlocked")
        return

    # --- Emergency: rollback ---
    if data == "act_rollback":
        known_good = run_cmd(f"cat {KNOWN_GOOD_FILE} 2>/dev/null || echo 'NOT SET'")
        current = run_cmd(f"cd {PROJECT_ROOT} && git rev-parse --short HEAD")
        if "NOT SET" in known_good:
            await msg.reply_text("No last_known_good recorded yet.")
            return
        good_commit = known_good.split()[0]
        if good_commit == current.strip():
            await msg.reply_text(f"Already on last_known_good: {good_commit}\nTry /restart instead.")
            return
        _pending_confirms[chat_id] = ("rollback", time.time())
        keyboard = [[
            InlineKeyboardButton("ROLLBACK", callback_data="confirm_rollback"),
            InlineKeyboardButton("Cancel", callback_data="cancel"),
        ]]
        await msg.reply_text(
            f"<b>ROLLBACK</b>\n\n"
            f"Current: <code>{current.strip()}</code>\n"
            f"Target: <code>{good_commit}</code>\n\n"
            f"Confirm?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data == "act_rollback_db":
        known_good = run_cmd(f"cat {KNOWN_GOOD_FILE} 2>/dev/null || echo 'NOT SET'")
        latest_backup = run_cmd(f"ls -t {PG_BACKUP_DIR}/pg_*.sql.gz 2>/dev/null | head -1")
        if not latest_backup or latest_backup.startswith("ERROR") or not latest_backup.strip():
            await msg.reply_text("No PG backups found.")
            return
        _pending_confirms[chat_id] = ("rollback_db", time.time())
        keyboard = [[
            InlineKeyboardButton("ROLLBACK + DB", callback_data="confirm_rollback_db"),
            InlineKeyboardButton("Cancel", callback_data="cancel"),
        ]]
        await msg.reply_text(
            f"<b>ROLLBACK + DB RESTORE</b>\n\n"
            f"Known good: <code>{known_good}</code>\n"
            f"DB backup: <code>{os.path.basename(latest_backup.strip())}</code>\n\n"
            f"<b>DATA AFTER BACKUP WILL BE LOST!</b>\n\nConfirm?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # --- Backups ---
    if data == "act_backups":
        output = run_cmd(
            f"echo '=== PostgreSQL Backups ===' && echo '' && "
            f"ls -lht {PG_BACKUP_DIR}/pg_*.sql.gz 2>/dev/null | head -15 | awk '{{printf \"%s %s %s  %s  %s\\n\", $6, $7, $8, $5, $9}}' && "
            f"echo '' && echo '=== Current DB Size ===' && "
            f"sudo -u postgres psql -d {PG_DB} -tAc 'SELECT pg_size_pretty(pg_database_size(current_database()));' 2>/dev/null && "
            f"echo '' && echo '=== Last Cron Backup ===' && "
            f"tail -3 {PG_BACKUP_DIR}/backup.log 2>/dev/null || echo 'No backup log'",
            timeout=10,
        )
        if not output.strip():
            output = "No PG backups found"
        await msg.reply_text(f"<pre>{truncate_for_tg(output)}</pre>", parse_mode="HTML")
        return

    if data == "act_restore":
        # Build PG backup selection
        backups_raw = run_cmd(
            f"ls -t {PG_BACKUP_DIR}/pg_*.sql.gz 2>/dev/null | head -6"
        )
        if not backups_raw.strip() or "ERROR" in backups_raw:
            await msg.reply_text("No PG backups found.")
            return
        backups = [b.strip() for b in backups_raw.strip().split("\n") if b.strip()]
        if not backups:
            await msg.reply_text("No PG backups found.")
            return
        keyboard = []
        for i, bp in enumerate(backups[:5]):
            name = os.path.basename(bp)
            size = run_cmd(f"stat -c%s {bp} 2>/dev/null || echo '?'")
            try:
                size_kb = f"{int(size.strip()) / 1024:.0f}KB"
            except ValueError:
                size_kb = "?KB"
            keyboard.append([InlineKeyboardButton(f"{name} ({size_kb})", callback_data=f"restore_{i}")])
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        _pending_confirms[chat_id] = ("restore", time.time(), backups)
        await msg.reply_text(
            "<b>Select PG backup to restore:</b>\n\n"
            "Current DB will be backed up first.\n"
            "<b>Data after backup will be lost!</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # --- Git ---
    if data == "act_branch":
        output = run_cmd(
            f"cd {PROJECT_ROOT} && "
            'echo "Branch: $(git branch --show-current 2>/dev/null)"; '
            'echo "Commit: $(git rev-parse --short HEAD)"; '
            'echo "Date: $(git log -1 --format=\'%ci\')"; '
            'echo "Msg: $(git log -1 --format=\'%s\')"; '
            'echo ""; echo "Known good: $(cat /var/run/lectio-monitor/last_known_good 2>/dev/null || echo NOT SET)"; '
            'echo ""; echo "Uncommitted:"; git status --short 2>/dev/null | head -10'
        )
        await msg.reply_text(f"<pre>{truncate_for_tg(output)}</pre>", parse_mode="HTML")
        return

    if data == "act_branches":
        output = run_cmd(
            f"cd {PROJECT_ROOT} && git fetch origin --prune 2>/dev/null; "
            'echo "=== Local ==="; git branch -v --no-color 2>&1 | head -10; '
            'echo ""; echo "=== Remote ==="; git branch -rv --no-color 2>&1 | grep -v HEAD | head -15'
        )
        await msg.reply_text(
            f"<pre>{truncate_for_tg(output, 3800)}</pre>",
            parse_mode="HTML",
        )
        return

    if data == "act_git_log":
        output = run_cmd(f"cd {PROJECT_ROOT} && git log --oneline --decorate -15 --no-color 2>&1")
        await msg.reply_text(
            f"<b>Git log (15):</b>\n<pre>{truncate_for_tg(output)}</pre>",
            parse_mode="HTML",
        )
        return

    if data == "act_switch":
        # Same as /switch without args — show branch picker
        branches_raw = run_cmd(
            f"cd {PROJECT_ROOT} && git fetch origin --prune 2>/dev/null; "
            "git branch -a --no-color 2>&1 | grep -v HEAD | sed 's/^[* ]*//' | "
            "sed 's|remotes/origin/||' | sort -u | head -10"
        )
        branches = [b.strip() for b in branches_raw.strip().split("\n") if b.strip()]
        if not branches:
            await msg.reply_text("No branches found")
            return
        current = run_cmd(f"cd {PROJECT_ROOT} && git branch --show-current 2>/dev/null").strip()
        keyboard = []
        for br in branches[:6]:
            marker = " *" if br == current else ""
            keyboard.append([InlineKeyboardButton(f"{br}{marker}", callback_data=f"switch_{br}")])
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        _pending_confirms[chat_id] = ("switch_select", time.time())
        await msg.reply_text(
            f"<b>Switch branch</b>\nCurrent: <code>{current}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # --- Alerts menu actions ---
    if data == "act_alerts":
        mute_status = _get_mute_status()
        guardian_mode = run_cmd(
            f'if [ -f {STATE_DIR}/maintenance_mode ]; then echo "PAUSED"; '
            f'elif [ -f {STATE_DIR}/deploy_in_progress ]; then echo "DEPLOY LOCK"; '
            f'else echo "ACTIVE"; fi'
        )
        recent = run_cmd(
            f"grep -i 'ALERT\\|FAIL\\|ERROR\\|RECOVER' {LOG_DIR}/guardian.log 2>/dev/null | tail -8"
        )
        text = f"<b>Alerts</b>\n\n{mute_status}\nGuardian: {guardian_mode}\n\n"
        if recent.strip():
            text += f"<b>Recent:</b>\n<pre>{truncate_for_tg(recent, 2500)}</pre>"
        else:
            text += "No recent alerts."
        await msg.reply_text(text, parse_mode="HTML")
        return

    if data == "act_mute_30m":
        await msg.reply_text(_set_mute(30 * 60))
        return

    if data == "act_mute_1h":
        await msg.reply_text(_set_mute(60 * 60))
        return

    if data == "act_mute_2h":
        await msg.reply_text(_set_mute(2 * 60 * 60))
        return

    if data == "act_mute_6h":
        await msg.reply_text(_set_mute(6 * 60 * 60))
        return

    if data == "act_unmute":
        await msg.reply_text(_clear_mute())
        return

    # --- Solo-dev actions from menu ---
    if data == "act_deploy":
        # Deploy needs confirmation — create pending and show confirm button
        current = run_cmd(f"cd {PROJECT_ROOT} && git rev-parse --short HEAD").strip()
        branch = run_cmd(f"cd {PROJECT_ROOT} && git branch --show-current 2>/dev/null").strip()
        run_cmd(f"cd {PROJECT_ROOT} && git fetch origin {branch} 2>/dev/null", timeout=15)
        behind = run_cmd(f"cd {PROJECT_ROOT} && git rev-list HEAD..origin/{branch} --count 2>/dev/null").strip()
        _pending_confirms[chat_id] = ("deploy", time.time())
        keyboard = [[
            InlineKeyboardButton("DEPLOY", callback_data="confirm_deploy"),
            InlineKeyboardButton("Cancel", callback_data="cancel"),
        ]]
        await msg.reply_text(
            f"<b>QUICK DEPLOY</b>\n\n"
            f"Branch: <code>{branch}</code>\n"
            f"Current: <code>{current}</code>\n"
            f"Behind origin: <b>{behind}</b>\n\n"
            f"Confirm?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data == "act_backup":
        ts_now = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{PG_BACKUP_DIR}/pg_menu_{ts_now}.sql.gz"
        await query.edit_message_text("Creating PG backup...")
        run_cmd(
            f"sudo -u postgres pg_dump {PG_DB} 2>/dev/null | gzip > {backup_path}",
            timeout=60,
        )
        size = run_cmd(f"stat -c%s {backup_path} 2>/dev/null || echo '0'")
        try:
            size_kb = f"{int(size.strip()) / 1024:.0f} KB"
        except ValueError:
            size_kb = "?"
        verify = run_cmd(f"zcat {backup_path} 2>/dev/null | head -1")
        ok = "PostgreSQL" in verify or "pg_dump" in verify
        status = "OK" if ok else "CHECK MANUALLY"
        await msg.reply_text(
            f"<b>Backup created</b>\n"
            f"<code>{backup_path}</code>\n"
            f"Size: {size_kb} | Status: {status}",
            parse_mode="HTML",
        )
        return

    if data == "act_errors":
        output = run_cmd(
            'echo "=== 5xx (nginx) ==="; '
            "awk '$9 ~ /^5[0-9][0-9]$/ {print $1, $4, $7, $9}' /var/log/nginx/access.log 2>/dev/null | tail -15; "
            'echo ""; echo "=== Django errors ==="; '
            "journalctl -u teaching_panel --no-pager 2>/dev/null | grep -i 'error\\|exception\\|traceback' | tail -15",
            timeout=15,
        )
        if not output.strip():
            output = "No recent errors."
        await msg.reply_text(
            f"<b>Recent errors</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>",
            parse_mode="HTML",
        )
        return

    if data == "act_users":
        output = run_cmd(
            f"echo '=== USERS ===' && "
            f"echo 'Total:' $(sudo -u postgres psql -d {PG_DB} -tAc 'SELECT COUNT(*) FROM accounts_customuser;' 2>/dev/null) && "
            f"echo 'Teachers:' $(sudo -u postgres psql -d {PG_DB} -tAc \"SELECT COUNT(*) FROM accounts_customuser WHERE role='teacher';\" 2>/dev/null) && "
            f"echo 'Students:' $(sudo -u postgres psql -d {PG_DB} -tAc \"SELECT COUNT(*) FROM accounts_customuser WHERE role='student';\" 2>/dev/null) && "
            f"echo '' && "
            f"echo '=== RECENT REGISTRATIONS ===' && "
            f"sudo -u postgres psql -d {PG_DB} -c 'SELECT date_joined::date, email, role FROM accounts_customuser ORDER BY date_joined DESC LIMIT 5;' 2>/dev/null && "
            f"echo '' && "
            f"echo '=== SUBSCRIPTIONS ===' && "
            f"sudo -u postgres psql -d {PG_DB} -c 'SELECT status, count(*) FROM accounts_subscription GROUP BY status;' 2>/dev/null",
            timeout=15,
        )
        await msg.reply_text(f"<b>Users</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>", parse_mode="HTML")
        return

    if data == "act_ssl":
        output = run_cmd(
            'echo | openssl s_client -servername lectiospace.ru -connect lectiospace.ru:443 2>/dev/null | '
            'openssl x509 -noout -dates -subject 2>&1; echo ""; '
            'EXPIRY=$(echo | openssl s_client -servername lectiospace.ru -connect lectiospace.ru:443 2>/dev/null | '
            'openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2); '
            'if [ -n "$EXPIRY" ]; then DAYS=$(( ($(date -d "$EXPIRY" +%s) - $(date +%s)) / 86400 )); '
            'echo "Days left: $DAYS"; fi',
            timeout=15,
        )
        await msg.reply_text(f"<b>SSL</b>\n<pre>{truncate_for_tg(output)}</pre>", parse_mode="HTML")
        return

    if data == "act_celery":
        output = run_cmd(
            'echo "Worker: $(systemctl is-active celery 2>/dev/null)"; '
            'echo "Beat: $(systemctl is-active celery-beat 2>/dev/null)"; '
            'echo "Redis: $(redis-cli ping 2>/dev/null)"; echo ""; '
            'echo "=== Processes ==="; '
            "ps aux | grep '[c]elery' | awk '{printf \"  PID=%s CPU=%s MEM=%s\\n\", $2, $3, $4}' | head -5; "
            'echo ""; echo "=== Recent logs ==="; '
            "journalctl -u celery -n 8 --no-pager 2>&1 | tail -8",
            timeout=15,
        )
        await msg.reply_text(f"<b>Celery</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>", parse_mode="HTML")
        return

    if data == "act_uptime":
        output = run_cmd("""
uptime
echo ""
for svc in teaching_panel nginx celery celery-beat redis-server; do
    ST=$(systemctl is-active $svc 2>/dev/null)
    if [ "$ST" = "active" ]; then
        SINCE=$(systemctl show $svc --property=ActiveEnterTimestamp 2>/dev/null | cut -d= -f2)
        printf "  %-20s %s\\n" "$svc" "$SINCE"
    else
        printf "  %-20s %s\\n" "$svc" "$ST"
    fi
done
""", timeout=10)
        await msg.reply_text(f"<b>Uptime</b>\n<pre>{truncate_for_tg(output)}</pre>", parse_mode="HTML")
        return

    if data == "act_db":
        output = run_cmd(
            f"echo '=== DATABASE ===' && "
            f"echo 'Engine: PostgreSQL 12' && "
            f"echo 'Name: {PG_DB}' && "
            f"echo 'Size:' $(sudo -u postgres psql -d {PG_DB} -tAc 'SELECT pg_size_pretty(pg_database_size(current_database()));' 2>/dev/null) && "
            f"echo '' && "
            f"echo '=== TOP 10 TABLES ===' && "
            f"sudo -u postgres psql -d {PG_DB} -c 'SELECT relname AS \"table\", pg_size_pretty(pg_total_relation_size(relid)) AS size, n_live_tup AS rows FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;' 2>/dev/null && "
            f"echo '' && "
            f"echo '=== PENDING MIGRATIONS ===' && "
            f"cd {PROJECT_ROOT}/teaching_panel && source ../venv/bin/activate && python manage.py showmigrations --plan 2>/dev/null | grep '\\[ \\]' | head -5 || echo 'None' && "
            f"echo '' && "
            f"echo '=== LAST PG BACKUP ===' && "
            f"ls -lht {PG_BACKUP_DIR}/pg_*.sql.gz 2>/dev/null | head -1 | awk '{{print $6, $7, $8, $5, $9}}'",
            timeout=20,
        )
        await msg.reply_text(f"<b>DB</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>", parse_mode="HTML")
        return

    if data == "act_nginx_test":
        output = run_cmd("nginx -t 2>&1")
        ok = "successful" in output
        header = "Nginx OK" if ok else "Nginx ERRORS!"
        await msg.reply_text(f"<b>{header}</b>\n<pre>{output}</pre>", parse_mode="HTML")
        return

    if data == "act_cleanup":
        await query.edit_message_text("Cleaning up...")
        output = run_cmd(f"""
echo "=== Removing old backups (keep 5) ==="
ls -t /tmp/deploy_*.pgdump /tmp/backup_*.pgdump /tmp/pre_*.pgdump /tmp/manual_backup_*.pgdump 2>/dev/null | tail -n +6 | while read f; do
    echo "  rm $(basename $f)"; rm -f "$f"
done
echo "=== Cleaning pycache ==="
find {PROJECT_ROOT} -name __pycache__ -type d -exec rm -rf {{}} + 2>/dev/null; echo "Done"
echo "=== Disk free: $(df / | awk 'NR==2{{print $5}}') used ==="
""", timeout=30)
        await msg.reply_text(f"<b>Cleanup</b>\n<pre>{truncate_for_tg(output, 3800)}</pre>", parse_mode="HTML")
        return


# --- Confirmation callback handler (rollback, restore, switch) ---

def _callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes callback queries to the right handler based on data prefix"""
    data = update.callback_query.data
    if data.startswith("menu_") or data.startswith("act_"):
        return menu_callback_handler(update, context)
    else:
        return confirm_callback_handler(update, context)


def main():
    if not ADMIN_CHAT_IDS:
        print(f"WARNING: ADMIN_CHAT_IDS empty!")
        print(f"Bot will reject all commands.")
        print(f"Add your chat_id to {CONFIG_FILE}")

    logger.info(f"Starting OPS bot. Admin chat IDs: {ADMIN_CHAT_IDS}")

    app = Application.builder().token(OPS_BOT_TOKEN).build()

    # Menu
    app.add_handler(CommandHandler("start", cmd_menu))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("help", cmd_help))

    # Monitoring
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("logs_nginx", cmd_logs_nginx))
    app.add_handler(CommandHandler("logs_guardian", cmd_logs_guardian))
    app.add_handler(CommandHandler("disk", cmd_disk))
    app.add_handler(CommandHandler("top", cmd_top))

    # Management
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("restart_all", cmd_restart_all))
    app.add_handler(CommandHandler("guardian", cmd_guardian))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("deploy_lock", cmd_deploy_lock))
    app.add_handler(CommandHandler("deploy_unlock", cmd_deploy_unlock))

    # Emergency
    app.add_handler(CommandHandler("rollback", cmd_rollback))
    app.add_handler(CommandHandler("rollback_db", cmd_rollback_db))

    # Backups
    app.add_handler(CommandHandler("backups", cmd_backups))
    app.add_handler(CommandHandler("restore", cmd_restore))

    # Git
    app.add_handler(CommandHandler("branch", cmd_branch))
    app.add_handler(CommandHandler("branches", cmd_branches))
    app.add_handler(CommandHandler("switch", cmd_switch))
    app.add_handler(CommandHandler("git_log", cmd_git_log))

    # Alerts (merged from ops_alerts_bot)
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("alerts", cmd_alerts))

    # Solo-dev commands
    app.add_handler(CommandHandler("deploy", cmd_deploy))
    app.add_handler(CommandHandler("backup", cmd_backup))
    app.add_handler(CommandHandler("errors", cmd_errors))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("ssl", cmd_ssl))
    app.add_handler(CommandHandler("celery", cmd_celery))
    app.add_handler(CommandHandler("uptime", cmd_uptime))
    app.add_handler(CommandHandler("db", cmd_db))
    app.add_handler(CommandHandler("nginx_test", cmd_nginx_test))
    app.add_handler(CommandHandler("cleanup", cmd_cleanup))

    # SOS & quick actions
    app.add_handler(CommandHandler("sos", cmd_sos))

    # User management
    app.add_handler(CommandHandler("resetpw", cmd_resetpw))
    app.add_handler(CommandHandler("adduser", cmd_adduser))

    # Unified callback handler (menu buttons + confirmation buttons)
    app.add_handler(CallbackQueryHandler(_callback_router))

    logger.info("Unified OPS bot is running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
