#!/usr/bin/env python
"""Sanitize sensitive data on staging."""
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings_staging")
import django; django.setup()

from accounts.models import Payment
for p in Payment.objects.all():
    p.payment_id = f"sanitized_{p.id}"
    p.payment_url = ""
    p.save(update_fields=["payment_id", "payment_url"])
c = Payment.objects.count()
print(f"Payments sanitized: {c}")
print("SANITIZE_COMPLETE")
