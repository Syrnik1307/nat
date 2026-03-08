"""
Feature flag for Parent Dashboard module.

The module is DISABLED by default and will NOT activate on production.
Enable via environment variable: PARENT_DASHBOARD_ENABLED=1

Only enable on local dev and staging (stage.lectiospace.ru).
NEVER set this on production until explicitly approved.

This file is imported by settings.py and other modules to check the flag.
It does NOT import Django settings to avoid circular imports.
"""
import os


def is_parent_dashboard_enabled() -> bool:
    """Check if Parent Dashboard module is enabled via environment variable."""
    return os.environ.get('PARENT_DASHBOARD_ENABLED', '').lower() in ('1', 'true', 'yes')


# Module-level constant for fast checks
PARENT_DASHBOARD_ENABLED = is_parent_dashboard_enabled()
