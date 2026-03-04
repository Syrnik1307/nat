#!/usr/bin/env python3
"""
Multi-Agent Code Checker — применяет правила 6 агентов к коду автоматически.

Агенты-источники правил:
  1. db-guardian       — опасные миграции, tenant-код, NOT NULL без default
  2. security-reviewer — захардкоженные секреты, debug в prod, SQL injection
  3. code-reviewer     — мёртвый код, TODO, антипаттерны Django/React
  4. frontend-qa       — эмодзи в UI, отсутствие transition, display:none
  5. safe-feature-dev  — сломанные API контракты, required поля без default
  6. project-cleanup   — мусорные файлы, дубли, неиспользуемые импорты

Запуск:
  python scripts/agent_checks.py              # проверить staged файлы
  python scripts/agent_checks.py --all        # проверить весь проект
  python scripts/agent_checks.py --changed    # проверить uncommitted changes
  python scripts/agent_checks.py FILE1 FILE2  # проверить конкретные файлы

Выход: 0 = OK, 1 = найдены BLOCK (критические), 2 = только WARN
"""

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Fix Windows terminal encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Конфигурация ──

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "teaching_panel"
FRONTEND_DIR = REPO_ROOT / "frontend" / "src"

# Цвета для терминала
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


@dataclass
class Finding:
    agent: str
    level: str  # BLOCK | WARN
    file: str
    line: Optional[int]
    message: str


@dataclass
class CheckContext:
    files: list[Path] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def add(self, agent: str, level: str, filepath: str, line: Optional[int], msg: str):
        self.findings.append(Finding(agent, level, filepath, line, msg))

    @property
    def blocks(self):
        return [f for f in self.findings if f.level == "BLOCK"]

    @property
    def warns(self):
        return [f for f in self.findings if f.level == "WARN"]


# ── Утилиты ──

def get_staged_files() -> list[Path]:
    """Git staged files (added/modified)."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=REPO_ROOT, text=True
        )
        return [REPO_ROOT / f.strip() for f in out.splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        return []


def get_changed_files() -> list[Path]:
    """Uncommitted changed files."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=ACM"],
            cwd=REPO_ROOT, text=True
        )
        staged = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=REPO_ROOT, text=True
        )
        files = set(out.splitlines()) | set(staged.splitlines())
        return [REPO_ROOT / f.strip() for f in files if f.strip()]
    except subprocess.CalledProcessError:
        return []


def get_all_project_files() -> list[Path]:
    """All tracked Python and JS files."""
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "--cached"],
            cwd=REPO_ROOT, text=True
        )
        files = []
        for f in out.splitlines():
            f = f.strip()
            if f.endswith((".py", ".js", ".jsx", ".css")):
                files.append(REPO_ROOT / f)
        return files
    except subprocess.CalledProcessError:
        return []


def read_safe(path: Path) -> tuple[str, list[str]]:
    """Read file, return (content, lines). Empty on error."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        return content, content.splitlines()
    except Exception:
        return "", []


def is_python(p: Path) -> bool:
    return p.suffix == ".py"


def is_js(p: Path) -> bool:
    return p.suffix in (".js", ".jsx")


def is_css(p: Path) -> bool:
    return p.suffix == ".css"


def is_migration(p: Path) -> bool:
    return is_python(p) and "migrations" in str(p) and p.name != "__init__.py"


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


# ══════════════════════════════════════════════════════════════
# АГЕНТ 1: DB Guardian — безопасность миграций
# Источник: .github/agents/db-guardian.agent.md
# ══════════════════════════════════════════════════════════════

def check_db_guardian(ctx: CheckContext):
    migration_files = [f for f in ctx.files if is_migration(f)]
    if not migration_files:
        return

    # Определяем какие миграции новые (staged/uncommitted) — только они блокируют
    try:
        tracked = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            cwd=REPO_ROOT, text=True
        ).splitlines()
        tracked += subprocess.check_output(
            ["git", "diff", "--name-only"],
            cwd=REPO_ROOT, text=True
        ).splitlines()
        new_migrations = {REPO_ROOT / f.strip() for f in tracked if "migrations" in f}
    except subprocess.CalledProcessError:
        new_migrations = set()

    dangerous_ops = [
        (r"RemoveField", "Deletes column and data FOREVER"),
        (r"DeleteModel", "Deletes table FOREVER"),
        (r"RunSQL.*(?:DROP|TRUNCATE|DELETE)", "Dangerous SQL"),
    ]

    for mf in migration_files:
        content, lines = read_safe(mf)
        rpath = rel(mf)
        # Старые миграции — только WARN, новые — BLOCK
        level = "BLOCK" if mf in new_migrations else "WARN"

        # Опасные операции
        for pattern, desc in dangerous_ops:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    ctx.add("db-guardian", level, rpath, i, f"Dangerous migration: {desc}")

        # NOT NULL без default (tenant-катастрофа паттерн)
        for i, line in enumerate(lines, 1):
            if "null=False" in line and "default=" not in line and "primary_key" not in line:
                if "AddField" in content[max(0, content.find(line) - 200):content.find(line) + len(line)]:
                    ctx.add("db-guardian", "BLOCK", rpath, i,
                            "AddField с null=False без default — сломает INSERT для существующих строк")

        # Tenant-код в миграциях
        for i, line in enumerate(lines, 1):
            if re.search(r"\btenant\b", line, re.IGNORECASE) and "#" not in line.split("tenant")[0]:
                ctx.add("db-guardian", "BLOCK", rpath, i,
                        "Tenant-код в миграции! ЗАПРЕЩЕНО навсегда (инцидент 2026-02-08)")


# ══════════════════════════════════════════════════════════════
# АГЕНТ 2: Security Reviewer — уязвимости
# Источник: .github/agents/security-reviewer.agent.md
# ══════════════════════════════════════════════════════════════

def check_security(ctx: CheckContext):
    secret_patterns = [
        (r"(?:password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}['\"]", "Возможный захардкоженный секрет"),
        (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API key"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    ]
    # UI validation messages are not secrets
    ui_safe_words = [
        "label", "placeholder", "hint", "validation", "message", "error",
        "helperText", "title", "description", "<", ">", "{", "}",
    ]
    # Паттерны, которые являются нормальными (не секреты)
    safe_exceptions = [
        "ci-secret-key", "please-change", "disabled", "dummy", "example",
        "test", "mock", "placeholder", "localhost", "SECRET_KEY",
        "os.environ", "env(", "getenv", "fake_",
    ]

    # Файлы с тестовыми/демо данными — не проверяем на секреты
    safe_filenames = {
        "create_sample_data.py", "create_test_data.py", "create_load_test_users.py",
        "create_admin_user.py", "conftest.py", "ops_bot.py",
    }
    # Папки, где секреты нормальны
    safe_dirs = {"tests", "manual_tests", "management"}

    for f in ctx.files:
        if not is_python(f) and not is_js(f):
            continue
        content, lines = read_safe(f)
        rpath = rel(f)

        # Захардкоженные секреты
        is_safe_file = (
            f.name in safe_filenames
            or "test_" in f.name
            or f.name.startswith("tests")
            or any(d in f.parts for d in safe_dirs)
        )
        if is_safe_file:
            pass  # Тестовые файлы — пропускаем проверку секретов
        else:
            for pattern, desc in secret_patterns:
                for i, line in enumerate(lines, 1):
                    m = re.search(pattern, line, re.IGNORECASE)
                    if m:
                        matched = m.group(0)
                        is_ui_context = any(w in line.lower() for w in ui_safe_words)
                        is_safe = any(exc in matched.lower() or exc in line.lower() for exc in safe_exceptions)
                        if not is_safe and not is_ui_context:
                            ctx.add("security", "BLOCK", rpath, i, f"{desc}: ...{matched[:30]}...")

        # DEBUG = True в settings.py
        if f.name == "settings.py":
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("DEBUG") and "=True" in stripped.replace(" ", ""):
                    if "environ" not in line and "#" not in line.split("=")[0]:
                        ctx.add("security", "BLOCK", rpath, i,
                                "DEBUG = True захардкожен (должен быть из env)")

        # .raw() SQL без параметризации
        if is_python(f):
            for i, line in enumerate(lines, 1):
                if ".raw(" in line and "%" in line and "params" not in line:
                    ctx.add("security", "WARN", rpath, i,
                            "raw() SQL с % форматированием — возможная SQL injection")


# ══════════════════════════════════════════════════════════════
# АГЕНТ 3: Code Reviewer — стандарты кода
# Источник: .github/agents/code-reviewer.agent.md
# ══════════════════════════════════════════════════════════════

def check_code_quality(ctx: CheckContext):
    for f in ctx.files:
        content, lines = read_safe(f)
        rpath = rel(f)

        if is_python(f):
            for i, line in enumerate(lines, 1):
                # print() вместо logging
                stripped = line.strip()
                if (stripped.startswith("print(") 
                        and "migrations" not in str(f) 
                        and "manage.py" not in str(f)
                        and "management/commands" not in str(f).replace("\\", "/")
                        and "manual_tests" not in str(f)
                        and f.name not in ("create_sample_data.py", "create_test_data.py",
                                          "create_load_test_users.py", "create_admin_user.py",
                                          "setup_gdrive_oauth.py")):
                    ctx.add("code-review", "WARN", rpath, i,
                            "print() в production-коде — используй logging")

                # except: (голый) — ловит всё включая SystemExit
                if re.match(r"\s*except\s*:", line):
                    ctx.add("code-review", "WARN", rpath, i,
                            "Голый except: — ловит SystemExit/KeyboardInterrupt")

                # import * — загрязняет namespace
                if re.match(r"from .+ import \*", stripped) and "migrations" not in str(f):
                    ctx.add("code-review", "WARN", rpath, i,
                            "import * — загрязняет namespace, используй явные импорты")

        # TODO/FIXME/HACK — не блок, но предупреждение
        if is_python(f) or is_js(f):
            for i, line in enumerate(lines, 1):
                if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line):
                    tag = re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line).group(1)
                    ctx.add("code-review", "WARN", rpath, i, f"{tag} найден")


# ══════════════════════════════════════════════════════════════
# АГЕНТ 4: Frontend QA — UI качество
# Источник: .github/agents/frontend-qa.agent.md
# ══════════════════════════════════════════════════════════════

# Unicode ranges for common emoji
EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U00002600-\U000026FF"  # misc symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # ZWJ
    "\U000023CF-\U000023F3"  # misc technical
    "\U0000231A-\U0000231B"
    "]"
)


def check_frontend_qa(ctx: CheckContext):
    frontend_files = [f for f in ctx.files if is_js(f) and "frontend" in str(f)]
    css_files = [f for f in ctx.files if is_css(f) and "frontend" in str(f)]

    # Эмодзи в новых/изменённых файлах = BLOCK, в старых = WARN
    try:
        changed_out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            cwd=REPO_ROOT, text=True
        ).splitlines()
        changed_out += subprocess.check_output(
            ["git", "diff", "--name-only"],
            cwd=REPO_ROOT, text=True
        ).splitlines()
        changed_set = {REPO_ROOT / f.strip() for f in changed_out}
    except subprocess.CalledProcessError:
        changed_set = set()

    for f in frontend_files:
        content, lines = read_safe(f)
        rpath = rel(f)

        # Эмодзи в компонентах UI
        for i, line in enumerate(lines, 1):
            if EMOJI_RE.search(line):
                # Пропускаем комментарии
                stripped = line.strip()
                if not stripped.startswith("//") and not stripped.startswith("*") and not stripped.startswith("/*"):
                    level = "BLOCK" if f in changed_set else "WARN"
                    ctx.add("frontend-qa", level, rpath, i,
                            "Emoji in UI! Use lucide-react icons instead")

        # console.log в production-коде
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "console.log(" in stripped and not stripped.startswith("//"):
                ctx.add("frontend-qa", "WARN", rpath, i,
                        "console.log() — убери перед деплоем")

    for f in css_files:
        content, lines = read_safe(f)
        rpath = rel(f)

        # display: none без transition (FRONTEND_SMOOTHNESS_RULES)
        for i, line in enumerate(lines, 1):
            if "display: none" in line or "display:none" in line:
                # Проверяем есть ли transition рядом (+-5 строк)
                nearby = "\n".join(lines[max(0, i - 6):i + 5])
                if "transition" not in nearby and "opacity" not in nearby:
                    ctx.add("frontend-qa", "WARN", rpath, i,
                            "display:none без transition — используй opacity+visibility (SMOOTHNESS_RULES)")

        # Захардкоженные transition значения вместо CSS-токенов
        for i, line in enumerate(lines, 1):
            if re.search(r"transition.*\d+ms", line):
                if "--duration-" not in line and "--ease-" not in line:
                    ctx.add("frontend-qa", "WARN", rpath, i,
                            "Захардкоженный transition — используй CSS-токены (--duration-*, --ease-*)")


# ══════════════════════════════════════════════════════════════
# АГЕНТ 5: Safe Feature Dev — безопасность API
# Источник: .github/agents/safe-feature-dev.agent.md
# ══════════════════════════════════════════════════════════════

def check_safe_feature(ctx: CheckContext):
    for f in ctx.files:
        if not is_python(f) or "teaching_panel" not in str(f):
            continue
        content, lines = read_safe(f)
        rpath = rel(f)

        # Удаление URL-паттернов (ломает фронтенд)
        # Сложно определить по одному файлу, но можно искать закомментированные URL
        if f.name == "urls.py":
            for i, line in enumerate(lines, 1):
                if "debug_views" in line and not line.strip().startswith("#"):
                    ctx.add("safe-feature", "BLOCK", rpath, i,
                            "debug_views endpoint в production urls.py (security!)")

        # Tenant-код — ЗАПРЕЩЁН навсегда
        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()
            # Пропускаем комментарии и защитный код (который БЛОКИРУЕТ tenant)
            if stripped_line.startswith("#") or stripped_line.startswith("'") or stripped_line.startswith('"'):
                continue
            # BANNED_APPS/BANNED_MIDDLEWARE — это защитный код, не нарушение
            if "BANNED" in line or "assert" in line or "raise" in line or "RuntimeError" in line:
                continue
            if re.search(r"from\s+tenants|import\s+tenants|TenantMiddleware|TenantModelMixin|TenantViewSetMixin|set_current_tenant", line):
                ctx.add("safe-feature", "BLOCK", rpath, i,
                        "Tenant-код ЗАПРЕЩЁН навсегда (инцидент 2026-02-08)")

        # Добавление required поля в сериализатор без версионирования
        if "serializers.py" in str(f):
            for i, line in enumerate(lines, 1):
                if "required=True" in line:
                    ctx.add("safe-feature", "WARN", rpath, i,
                            "required=True в сериализаторе — старые клиенты могут сломаться")


# ══════════════════════════════════════════════════════════════
# АГЕНТ 6: Project Cleanup — мусор
# Источник: .github/agents/project-cleanup.agent.md
# ══════════════════════════════════════════════════════════════

def check_cleanup(ctx: CheckContext):
    for f in ctx.files:
        rpath = rel(f)

        # .txt файлы в корне проекта (мусор от отладки)
        if f.suffix == ".txt" and f.parent == REPO_ROOT:
            ctx.add("cleanup", "WARN", rpath, None,
                    "Debug .txt файл в корне проекта — добавь в .gitignore или удали")

        # .pyc файлы
        if f.suffix == ".pyc":
            ctx.add("cleanup", "WARN", rpath, None, ".pyc файл в git — добавь в .gitignore")

        # Бэкап-файлы
        if f.suffix in (".bak", ".save", ".orig", ".swp"):
            ctx.add("cleanup", "WARN", rpath, None,
                    f"Бэкап-файл ({f.suffix}) — не должен быть в git")


# ══════════════════════════════════════════════════════════════
# Отчёт
# ══════════════════════════════════════════════════════════════

AGENT_ICONS = {
    "db-guardian": "DB",
    "security": "SEC",
    "code-review": "CODE",
    "frontend-qa": "UI",
    "safe-feature": "SAFE",
    "cleanup": "CLEAN",
}


def print_report(ctx: CheckContext):
    if not ctx.findings:
        print(f"\n{GREEN}{BOLD}ALL CLEAR{RESET} — 6 агентов проверили, проблем нет")
        return

    # Группируем по агенту
    by_agent: dict[str, list[Finding]] = {}
    for f in ctx.findings:
        by_agent.setdefault(f.agent, []).append(f)

    print(f"\n{'='*60}")
    print(f"{BOLD}MULTI-AGENT CHECK REPORT{RESET}")
    print(f"{'='*60}")

    for agent, findings in sorted(by_agent.items()):
        icon = AGENT_ICONS.get(agent, "?")
        blocks = [f for f in findings if f.level == "BLOCK"]
        warns = [f for f in findings if f.level == "WARN"]

        agent_color = RED if blocks else YELLOW
        print(f"\n{agent_color}{BOLD}[{icon}] @{agent}{RESET}  ", end="")
        parts = []
        if blocks:
            parts.append(f"{RED}{len(blocks)} BLOCK{RESET}")
        if warns:
            parts.append(f"{YELLOW}{len(warns)} WARN{RESET}")
        print(" | ".join(parts))

        for f in findings:
            color = RED if f.level == "BLOCK" else YELLOW
            loc = f"{f.file}"
            if f.line:
                loc += f":{f.line}"
            print(f"  {color}{f.level}{RESET} {DIM}{loc}{RESET}")
            print(f"        {f.message}")

    print(f"\n{'='*60}")
    total_b = len(ctx.blocks)
    total_w = len(ctx.warns)
    if total_b > 0:
        print(f"{RED}{BOLD}BLOCKED{RESET}: {total_b} критических, {total_w} предупреждений")
        print(f"{DIM}Исправь BLOCK-проблемы перед коммитом. WARN — рекомендации.{RESET}")
    else:
        print(f"{YELLOW}{BOLD}PASSED с предупреждениями{RESET}: {total_w} WARN")
        print(f"{DIM}Рекомендуется исправить, но не блокирует коммит.{RESET}")
    print(f"{'='*60}\n")


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════

ALL_CHECKS = [
    check_db_guardian,
    check_security,
    check_code_quality,
    check_frontend_qa,
    check_safe_feature,
    check_cleanup,
]


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Code Checker")
    parser.add_argument("files", nargs="*", help="Конкретные файлы для проверки")
    parser.add_argument("--all", action="store_true", help="Проверить все файлы проекта")
    parser.add_argument("--changed", action="store_true", help="Проверить uncommitted файлы")
    parser.add_argument("--staged", action="store_true", help="Проверить staged файлы (default)")
    parser.add_argument("--quiet", action="store_true", help="Только exit code, без вывода")
    args = parser.parse_args()

    # Определяем файлы для проверки
    if args.files:
        files = [Path(f).resolve() for f in args.files]
    elif args.all:
        files = get_all_project_files()
    elif args.changed:
        files = get_changed_files()
    else:
        files = get_staged_files()

    # Фильтруем существующие
    files = [f for f in files if f.exists()]

    if not files:
        if not args.quiet:
            print(f"{DIM}Нет файлов для проверки{RESET}")
        sys.exit(0)

    if not args.quiet:
        print(f"{CYAN}Проверяю {len(files)} файлов через 6 агентов...{RESET}")

    ctx = CheckContext(files=files)

    for check in ALL_CHECKS:
        check(ctx)

    if not args.quiet:
        print_report(ctx)

    # Exit codes
    if ctx.blocks:
        sys.exit(1)  # BLOCK
    elif ctx.warns:
        sys.exit(0)  # WARN — не блокируем (мягкий режим)
    else:
        sys.exit(0)  # Clean


if __name__ == "__main__":
    main()
