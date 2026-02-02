import os, sys, django
os.environ['DJANGO_SETTINGS_MODULE']='teaching_panel.settings'
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
django.setup()
from schedule.models import Lesson, LessonRecording
from accounts.models import Subscription
from homework.models import HomeworkSubmission
print('=== DB Check ===')
print('Lessons:', Lesson.objects.count())
print('Recordings:', LessonRecording.objects.count())
print('Subscriptions:', Subscription.objects.count())
print('HomeworkSubmissions:', HomeworkSubmission.objects.count())
print('Active lessons:', Lesson.objects.filter(status='in_progress').count())
print('=== OK ===')
