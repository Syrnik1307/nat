"""
Feature flag for Support V2 module (full ticket UI + file attachments).

DISABLED by default — will NOT activate on production.
Enable via environment variable: SUPPORT_V2_ENABLED=1

Existing support endpoints (widget, health, status, basic CRUD) work
regardless of this flag. This flag gates ONLY the new functionality:
- File attachment upload/download endpoints
- Enhanced serializers with attachment support
"""
import os


def is_support_v2_enabled() -> bool:
    """Check if Support V2 module is enabled via environment variable."""
    return os.environ.get('SUPPORT_V2_ENABLED', '').lower() in ('1', 'true', 'yes')


# Module-level constant for fast checks
SUPPORT_V2_ENABLED = is_support_v2_enabled()
