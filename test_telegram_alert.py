#!/usr/bin/env python
"""Test script for telegram alerting system."""
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from teaching_panel.telegram_logging import (
    TelegramErrorHandler, 
    AlertMessageFormatter, 
    TelegramAlertSender
)

# Test message formatting
msg = AlertMessageFormatter.format(
    level='ERROR',
    message='Test error from deployment verification',
    pathname='teaching_panel/telegram_logging.py',
    lineno=42,
    request_info={'method': 'GET', 'path': '/api/test/', 'user': 'admin@test.com', 'user_id': 1},
    exc_info=None,
    repeat_count=0
)
print('=== Formatted Message ===')
print(msg)
print()
print('=== Sending test alert ===')
result = TelegramAlertSender.send_message(msg)
print('Send result:', result)
