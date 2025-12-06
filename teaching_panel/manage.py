#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# Reorder sys.path so site-packages stay ahead of our project source, preventing celery.py shadowing
PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_SRC = PROJECT_ROOT / 'teaching_panel'
sys.path = [p for p in sys.path if p not in {str(PROJECT_ROOT), str(PROJECT_SRC)}]
if PROJECT_SRC.exists():
    sys.path.append(str(PROJECT_SRC))
if PROJECT_ROOT.exists():
    sys.path.append(str(PROJECT_ROOT))


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
