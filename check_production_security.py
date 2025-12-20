#!/usr/bin/env python
"""
🔒 Production Security Checklist
Проверяет готовность проекта к production.

Использование:
    python check_production_security.py [--fix]
"""

import os
import sys
import re
from pathlib import Path

# Цвета для вывода
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def ok(msg):
    print(f"  {Colors.GREEN}✅ {msg}{Colors.ENDC}")

def warn(msg):
    print(f"  {Colors.YELLOW}⚠️  {msg}{Colors.ENDC}")

def error(msg):
    print(f"  {Colors.RED}❌ {msg}{Colors.ENDC}")

def info(msg):
    print(f"  {Colors.BLUE}ℹ️  {msg}{Colors.ENDC}")

def header(msg):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{msg}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def check_env_file():
    """Проверяет наличие и содержимое .env файла"""
    header("1. Проверка .env файла")
    
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        error(".env файл не найден!")
        warn("Создайте .env файл на основе .env.example")
        return False
    
    ok(".env файл существует")
    
    # Читаем содержимое
    with open(env_path, 'r') as f:
        content = f.read()
    
    required_vars = {
        'SECRET_KEY': 'Секретный ключ Django',
        'DEBUG': 'Режим отладки (должен быть False)',
        'ALLOWED_HOSTS': 'Разрешённые хосты',
    }
    
    critical_vars = {
        'RECAPTCHA_PUBLIC_KEY': 'reCAPTCHA публичный ключ',
        'RECAPTCHA_PRIVATE_KEY': 'reCAPTCHA приватный ключ',
        'RECAPTCHA_ENABLED': 'Включение reCAPTCHA',
    }
    
    security_vars = {
        'SECURE_SSL_REDIRECT': 'HTTPS редирект',
        'SESSION_COOKIE_SECURE': 'Защищённые cookies',
        'CSRF_COOKIE_SECURE': 'Защищённые CSRF cookies',
        'SECURE_HSTS_SECONDS': 'HSTS заголовок',
        'CSRF_TRUSTED_ORIGINS': 'Доверенные origins для CSRF',
    }
    
    all_ok = True
    
    # Проверяем обязательные
    for var, desc in required_vars.items():
        if var + '=' in content:
            value = re.search(rf'{var}=(.+)', content)
            if value:
                val = value.group(1).strip().strip('"').strip("'")
                if var == 'DEBUG' and val.lower() in ('true', '1', 'yes'):
                    error(f"{var}: DEBUG=True в production опасен!")
                    all_ok = False
                elif var == 'SECRET_KEY' and 'insecure' in val:
                    error(f"{var}: Используется дефолтный небезопасный ключ!")
                    all_ok = False
                else:
                    ok(f"{var}: настроен")
        else:
            error(f"{var}: НЕ НАЙДЕН ({desc})")
            all_ok = False
    
    # Проверяем критичные
    for var, desc in critical_vars.items():
        if var + '=' in content:
            value = re.search(rf'{var}=(.+)', content)
            if value:
                val = value.group(1).strip().strip('"').strip("'")
                if '6LeIxAcTAAAAA' in val:  # Тестовые ключи Google
                    warn(f"{var}: Используются ТЕСТОВЫЕ ключи reCAPTCHA!")
                else:
                    ok(f"{var}: настроен")
        else:
            warn(f"{var}: не найден ({desc})")
    
    # Проверяем security
    for var, desc in security_vars.items():
        if var + '=' in content:
            ok(f"{var}: настроен")
        else:
            warn(f"{var}: не найден ({desc})")
    
    return all_ok


def check_redis():
    """Проверяет доступность Redis"""
    header("2. Проверка Redis (нужен для бана по fingerprint)")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        ok("Redis доступен на localhost:6379")
        return True
    except ImportError:
        warn("Библиотека redis не установлена")
        info("Установите: pip install redis")
        return False
    except Exception as e:
        error(f"Redis недоступен: {e}")
        info("Запустите: docker run -d -p 6379:6379 redis")
        return False


def check_bot_protection():
    """Проверяет наличие системы защиты от ботов"""
    header("3. Проверка системы Bot Protection")
    
    bot_protection_path = Path(__file__).parent / 'teaching_panel' / 'accounts' / 'bot_protection.py'
    
    if not bot_protection_path.exists():
        error("bot_protection.py не найден!")
        return False
    
    ok("bot_protection.py существует")
    
    # Проверяем frontend
    frontend_path = Path(__file__).parent / 'frontend' / 'src' / 'utils' / 'botProtection.js'
    
    if not frontend_path.exists():
        error("Frontend botProtection.js не найден!")
        return False
    
    ok("Frontend botProtection.js существует")
    
    # Проверяем middleware в settings
    settings_path = Path(__file__).parent / 'teaching_panel' / 'teaching_panel' / 'settings.py'
    with open(settings_path, 'r') as f:
        settings_content = f.read()
    
    if 'BotProtectionMiddleware' in settings_content:
        ok("BotProtectionMiddleware включён в MIDDLEWARE")
    else:
        error("BotProtectionMiddleware НЕ включён в MIDDLEWARE!")
        return False
    
    return True


def check_webhooks():
    """Проверяет настройку webhook секретов"""
    header("4. Проверка Webhook Security")
    
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        warn(".env файл не найден, пропускаем проверку webhooks")
        return True
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    webhooks = {
        'YOOKASSA_WEBHOOK_SECRET': 'YooKassa webhooks',
        'ZOOM_WEBHOOK_SECRET_TOKEN': 'Zoom webhooks',
    }
    
    all_ok = True
    for var, desc in webhooks.items():
        if var + '=' in content:
            value = re.search(rf'{var}=(.+)', content)
            if value and value.group(1).strip():
                ok(f"{var}: настроен")
            else:
                warn(f"{var}: пустое значение ({desc})")
        else:
            warn(f"{var}: не найден ({desc})")
    
    return all_ok


def check_https_settings():
    """Проверяет настройки HTTPS"""
    header("5. Проверка HTTPS настроек")
    
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        error(".env файл не найден!")
        return False
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    https_vars = [
        ('SECURE_SSL_REDIRECT', 'True'),
        ('SESSION_COOKIE_SECURE', 'True'),
        ('CSRF_COOKIE_SECURE', 'True'),
    ]
    
    all_ok = True
    for var, expected in https_vars:
        value = re.search(rf'{var}=(.+)', content)
        if value:
            val = value.group(1).strip().strip('"').strip("'")
            if val.lower() == expected.lower():
                ok(f"{var}={val}")
            else:
                warn(f"{var}={val} (рекомендуется {expected})")
        else:
            warn(f"{var}: не найден (рекомендуется {expected})")
    
    return all_ok


def check_rate_limiting():
    """Проверяет настройки rate limiting"""
    header("6. Проверка Rate Limiting")
    
    settings_path = Path(__file__).parent / 'teaching_panel' / 'teaching_panel' / 'settings.py'
    
    with open(settings_path, 'r') as f:
        content = f.read()
    
    if 'DEFAULT_THROTTLE_RATES' in content:
        ok("Rate limiting настроен в settings.py")
    else:
        error("DEFAULT_THROTTLE_RATES не найден в settings.py!")
        return False
    
    if "'login'" in content:
        ok("Login rate limiting настроен")
    else:
        warn("Login rate limiting не настроен")
    
    return True


def check_password_policy():
    """Проверяет политику паролей"""
    header("7. Проверка политики паролей")
    
    settings_path = Path(__file__).parent / 'teaching_panel' / 'teaching_panel' / 'settings.py'
    
    with open(settings_path, 'r') as f:
        content = f.read()
    
    validators = [
        'UserAttributeSimilarityValidator',
        'MinimumLengthValidator',
        'CommonPasswordValidator',
        'NumericPasswordValidator',
    ]
    
    all_ok = True
    for v in validators:
        if v in content:
            ok(f"{v}: включён")
        else:
            warn(f"{v}: не найден")
            all_ok = False
    
    return all_ok


def check_sentry():
    """Проверяет настройку Sentry для мониторинга ошибок"""
    header("8. Проверка Sentry (мониторинг ошибок)")
    
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        warn(".env файл не найден")
        return True
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    if 'SENTRY_DSN=' in content:
        value = re.search(r'SENTRY_DSN=(.+)', content)
        if value and value.group(1).strip():
            ok("Sentry DSN настроен")
            return True
        else:
            warn("SENTRY_DSN пустой")
    else:
        warn("SENTRY_DSN не настроен (рекомендуется для production)")
    
    info("Зарегистрируйтесь на https://sentry.io/ для мониторинга ошибок")
    return True


def main():
    print(f"\n{Colors.BOLD}🔒 PRODUCTION SECURITY CHECKLIST{Colors.ENDC}")
    print(f"{Colors.BOLD}   Teaching Panel LMS{Colors.ENDC}\n")
    
    results = []
    
    results.append(("Env файл", check_env_file()))
    results.append(("Redis", check_redis()))
    results.append(("Bot Protection", check_bot_protection()))
    results.append(("Webhooks", check_webhooks()))
    results.append(("HTTPS", check_https_settings()))
    results.append(("Rate Limiting", check_rate_limiting()))
    results.append(("Password Policy", check_password_policy()))
    results.append(("Sentry", check_sentry()))
    
    # Итоговый отчёт
    header("ИТОГОВЫЙ ОТЧЁТ")
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        if ok:
            print(f"  {Colors.GREEN}✅ {name}{Colors.ENDC}")
        else:
            print(f"  {Colors.RED}❌ {name}{Colors.ENDC}")
    
    print()
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Готов к production.{Colors.ENDC}")
        return 0
    elif passed >= total - 2:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  Почти готов. Исправьте отмеченные проблемы.{Colors.ENDC}")
        return 1
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ НЕ ГОТОВ к production! Много проблем.{Colors.ENDC}")
        return 2


if __name__ == '__main__':
    sys.exit(main())
