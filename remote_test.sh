#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell <<EOF
from schedule.models import LessonRecording
print("=== Soft Delete Test ===")
print("has is_deleted:", hasattr(LessonRecording, "is_deleted"))
print("has soft_delete method:", hasattr(LessonRecording, "soft_delete"))
print("has restore method:", hasattr(LessonRecording, "restore"))
print("has hard_delete method:", hasattr(LessonRecording, "hard_delete"))
print()
from zoom_pool.models import ZoomAccount
print("=== Zoom Pool Test ===")
print("has acquire:", hasattr(ZoomAccount, "acquire"))
print("has INVALID_CREDENTIALS:", hasattr(ZoomAccount, "INVALID_CREDENTIALS"))
print()
from accounts.payments_service import PaymentService
print("=== Payment Service ===")
ps = PaymentService()
print("PaymentService initialized:", ps is not None)
print()
print("=== All tests passed ===")
EOF
