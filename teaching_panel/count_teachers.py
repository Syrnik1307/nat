import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from accounts.models import CustomUser

teachers = CustomUser.objects.filter(role='teacher')
print(f"Всего учителей в БД: {teachers.count()}")
print(f"С заполненным gdrive_folder_id: {teachers.exclude(gdrive_folder_id='').count()}")
