#!/usr/bin/env python
"""
DEPRECATED - ОПАСНЫЙ СКРИПТ!

Этот скрипт УДАЛЁН из использования, так как он удалял папки Teacher_*
БЕЗ ПРОВЕРКИ наличия активных файлов HomeworkFile внутри.

Это приводило к потере изображений в домашних заданиях!

См. RCA_HOMEWORK_IMAGES_LOSS.md для деталей.

Используйте вместо него:
  - cleanup_old_gdrive_folders.py (проверяет подписки)
  - safe_cleanup_gdrive.py (проверяет HomeworkFile)
"""

import sys

print("=" * 60)
print("ЭТОТ СКРИПТ ЗАБЛОКИРОВАН!")
print("=" * 60)
print()
print("Причина: Скрипт удалял папки Teacher_* без проверки,")
print("что приводило к потере файлов домашних заданий.")
print()
print("Используйте безопасные альтернативы:")
print("  - python cleanup_old_gdrive_folders.py (проверяет подписки)")
print("  - python safe_cleanup_gdrive.py (проверяет HomeworkFile)")
print()
print("Подробности: см. RCA_HOMEWORK_IMAGES_LOSS.md")
print("=" * 60)

sys.exit(1)


# ============================================================
# СТАРЫЙ ОПАСНЫЙ КОД (ОТКЛЮЧЁН)
# ============================================================
# import os
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
# import django
# django.setup()
# 
# from django.conf import settings
# from schedule.gdrive_utils import get_gdrive_manager
# from accounts.models import CustomUser
# 
# # ОПАСНО: Удаляло ВСЕ папки Teacher_* без проверки!
# gdrive = get_gdrive_manager()
# root_id = settings.GDRIVE_ROOT_FOLDER_ID
# query = f"'{root_id}' in parents and mimeType='application/vnd.google-apps.folder' and name contains 'Teacher_' and trashed=false"
# results = gdrive.service.files().list(q=query, fields='files(id, name)').execute()
# folders = results.get('files', [])
# for f in folders:
#     gdrive.service.files().delete(fileId=f['id']).execute()  # УДАЛЯЛО ФАЙЛЫ ДЗ!
