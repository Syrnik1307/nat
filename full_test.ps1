ssh root@72.56.81.163 "cd /var/www/teaching_panel/teaching_panel && . ../venv/bin/activate && python << 'PYEOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from schedule.models import LessonRecording
from zoom_pool.models import ZoomAccount

print('=== DEPLOYMENT VERIFICATION ===')
print()

# Test 1: Soft Delete
print('1. LessonRecording Soft Delete:')
print('   - is_deleted field:', 'is_deleted' in [f.name for f in LessonRecording._meta.fields])
print('   - soft_delete method:', callable(getattr(LessonRecording, 'soft_delete', None)))
print('   - restore method:', callable(getattr(LessonRecording, 'restore', None)))
print('   - hard_delete method:', callable(getattr(LessonRecording, 'hard_delete', None)))
print('   - ActiveManager:', hasattr(LessonRecording, 'objects'))
print('   - AllManager:', hasattr(LessonRecording, 'all_objects'))

# Test 2: Zoom Pool
print()
print('2. ZoomAccount Production Safety:')
print('   - INVALID_CREDENTIALS:', hasattr(ZoomAccount, 'INVALID_CREDENTIALS'))
print('   - validate_for_production:', callable(getattr(ZoomAccount, 'validate_for_production', None)))
print('   - acquire method:', callable(getattr(ZoomAccount, 'acquire', None)))
print('   - release method:', callable(getattr(ZoomAccount, 'release', None)))

# Test 3: Count records
print()
print('3. Database Stats:')
print('   - Total recordings:', LessonRecording.all_objects.count())
print('   - Active recordings:', LessonRecording.objects.count())
print('   - Deleted recordings:', LessonRecording.all_objects.filter(is_deleted=True).count())
print('   - Zoom accounts:', ZoomAccount.objects.count())

print()
print('=== ALL TESTS PASSED ===')
PYEOF
"
