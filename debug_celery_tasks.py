#!/usr/bin/env python
"""
Диагностика зарегистрированных Celery задач.

Использование:
  python debug_celery_tasks.py

На продакшене:
  cd /var/www/teaching-panel
  source venv/bin/activate
  python debug_celery_tasks.py
"""
import os
import sys

# Добавляем путь к Django проекту
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DJANGO_PROJECT = os.path.join(BASE_DIR, 'teaching_panel')

if DJANGO_PROJECT not in sys.path:
    sys.path.insert(0, DJANGO_PROJECT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

# Теперь импортируем Celery app
from teaching_panel.celery import app

# Принудительный импорт модуля с задачами
try:
    import schedule.tasks
    print("✓ schedule.tasks imported successfully")
except ImportError as e:
    print(f"✗ Failed to import schedule.tasks: {e}")

# Выводим все зарегистрированные задачи
print("\n" + "="*60)
print("REGISTERED CELERY TASKS")
print("="*60)

all_tasks = sorted(app.tasks.keys())
custom_tasks = [t for t in all_tasks if not t.startswith('celery.')]

print(f"\nTotal tasks: {len(all_tasks)}")
print(f"Custom tasks: {len(custom_tasks)}")
print("\nCustom tasks list:")

for task_name in custom_tasks:
    print(f"  • {task_name}")

# Проверяем конкретную задачу
TARGET_TASK = 'schedule.tasks.release_stuck_zoom_accounts'
print("\n" + "="*60)
print(f"CHECKING: {TARGET_TASK}")
print("="*60)

if TARGET_TASK in app.tasks:
    print(f"\n✓ Task '{TARGET_TASK}' is REGISTERED")
    task = app.tasks[TARGET_TASK]
    print(f"  Module: {task.__module__}")
    print(f"  Name: {task.name}")
else:
    print(f"\n✗ Task '{TARGET_TASK}' is NOT FOUND!")
    print("\nPossible issues:")
    print("  1. Task module not imported")
    print("  2. @shared_task decorator missing name= parameter")
    print("  3. Celery worker needs restart")
    
    # Поищем похожие задачи
    similar = [t for t in custom_tasks if 'release' in t.lower() or 'zoom' in t.lower()]
    if similar:
        print(f"\nSimilar tasks found:")
        for t in similar:
            print(f"  • {t}")

# Проверяем, что функция существует в модуле
print("\n" + "="*60)
print("VERIFYING FUNCTION IN MODULE")
print("="*60)

try:
    from schedule.tasks import release_stuck_zoom_accounts
    print(f"\n✓ Function 'release_stuck_zoom_accounts' exists in schedule.tasks")
    print(f"  Callable: {callable(release_stuck_zoom_accounts)}")
    
    # Проверяем атрибуты Celery задачи
    if hasattr(release_stuck_zoom_accounts, 'name'):
        print(f"  Task name: {release_stuck_zoom_accounts.name}")
    if hasattr(release_stuck_zoom_accounts, 'delay'):
        print(f"  Has .delay(): True (Celery task)")
except ImportError as e:
    print(f"\n✗ Cannot import release_stuck_zoom_accounts: {e}")

print("\n" + "="*60)
print("CELERY BEAT SCHEDULE (from settings)")
print("="*60)

try:
    from django.conf import settings
    beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
    
    for name, config in beat_schedule.items():
        task = config.get('task', 'unknown')
        schedule_info = config.get('schedule', 'unknown')
        print(f"\n  [{name}]")
        print(f"    task: {task}")
        print(f"    schedule: {schedule_info}")
        
        # Проверяем, зарегистрирована ли задача
        if task in app.tasks:
            print(f"    status: ✓ registered")
        else:
            print(f"    status: ✗ NOT REGISTERED!")
except Exception as e:
    print(f"  Error reading CELERY_BEAT_SCHEDULE: {e}")

print("\n" + "="*60)
print("CONCLUSION")
print("="*60)

if TARGET_TASK in app.tasks:
    print("\n✓ All checks PASSED. Celery tasks are properly configured.")
    print("\nIf you still see errors, restart Celery:")
    print("  sudo systemctl restart celery celery-beat")
else:
    print("\n✗ Task registration FAILED. Check the errors above.")
    sys.exit(1)
