#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# Ensure we import apps from the project source (teaching_panel/*) even if a stale copy exists at repo root
PROJECT_SRC = Path(__file__).resolve().parent / 'teaching_panel'
if PROJECT_SRC.exists():
    sys.path.insert(0, str(PROJECT_SRC))


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
