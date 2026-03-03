"""
Feature flag for Knowledge Map module.

The module is DISABLED by default and will NOT activate on production.
Enable via environment variable: KNOWLEDGE_MAP_ENABLED=1

This file is imported by settings.py and other modules to check the flag.
It does NOT import Django settings to avoid circular imports.
"""
import os


def is_knowledge_map_enabled() -> bool:
    """Check if Knowledge Map module is enabled via environment variable."""
    return os.environ.get('KNOWLEDGE_MAP_ENABLED', '').lower() in ('1', 'true', 'yes')


# Module-level constant for fast checks
KNOWLEDGE_MAP_ENABLED = is_knowledge_map_enabled()
