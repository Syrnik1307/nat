ssh root@72.56.81.163 "cd /var/www/teaching_panel/teaching_panel && . ../venv/bin/activate && python -c \"
from schedule.models import LessonRecording
print('=== Soft Delete Test ===')
print('LessonRecording has is_deleted:', hasattr(LessonRecording, 'is_deleted'))
print('LessonRecording has soft_delete:', hasattr(LessonRecording, 'soft_delete'))

from zoom_pool.models import ZoomAccount
print('\\n=== Zoom Pool Test ===')
print('ZoomAccount has acquire:', hasattr(ZoomAccount, 'acquire'))
print('ZoomAccount has INVALID_CREDENTIALS:', hasattr(ZoomAccount, 'INVALID_CREDENTIALS'))

from accounts.payments_service import PaymentService
print('\\n=== Payment Service Test ===')
print('PaymentService exists:', PaymentService is not None)

print('\\n=== All imports successful ===')
\""
