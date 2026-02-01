#!/usr/bin/env python
"""Test real Django logging through TelegramErrorHandler."""
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

import logging

# Get the django.request logger that has telegram handler
logger = logging.getLogger('django.request')

print("=== Testing real Django logger with TelegramErrorHandler ===")

# Simulate an error with exception
try:
    raise ValueError("Test exception for Telegram alert system verification")
except Exception as e:
    logger.error(
        "Test 500 error from telegram alert verification script",
        exc_info=True,
        extra={'status_code': 500}
    )
    print("Error logged! Check Telegram for the alert.")

print()
print("=== Testing anti-spam (same error twice) ===")
try:
    raise ValueError("Duplicate test error")
except Exception as e:
    logger.error("Duplicate error test #1", exc_info=True)
    logger.error("Duplicate error test #1", exc_info=True)  # Should be throttled
    print("2 identical errors logged - second should be throttled")

print()
print("Done! Check your Telegram for alerts.")
