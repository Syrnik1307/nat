import os
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'teaching_panel.settings'
django.setup()

from accounts.models import User

teachers = User.objects.filter(role='teacher').exclude(telegram_id__isnull=True).exclude(telegram_id='')
print('Teachers with Telegram:')
for t in teachers[:5]:
    print(f'  {t.email}: TG ID={t.telegram_id}, @{t.telegram_username}')
print(f'Total: {teachers.count()}')
