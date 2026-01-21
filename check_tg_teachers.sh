#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
../venv/bin/python manage.py shell -c "
from accounts.models import User
teachers = User.objects.filter(role='teacher').exclude(telegram_id__isnull=True).exclude(telegram_id='')
print('Teachers with Telegram:')
for t in teachers[:5]:
    print(f'  {t.email}: TG ID={t.telegram_id}, @{t.telegram_username}')
print(f'Total: {teachers.count()}')
"
