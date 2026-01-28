#!/usr/bin/env python
"""Тест подсчёта размера папок в Google Drive"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
os.environ['USE_GDRIVE_STORAGE'] = '1'
os.environ['GDRIVE_ROOT_FOLDER_ID'] = '1u1V9O-enN0tAYj98zy40yinB84yyi8IB'

django.setup()

from schedule.gdrive_utils import get_gdrive_manager
from accounts.models import CustomUser

def main():
    gdrive = get_gdrive_manager()
    print(f'GDrive Root folder: {gdrive.root_folder_id}')
    print(f'GDrive Manager type: {type(gdrive).__name__}')

    print('\n--- Testing calculate_folder_size on root ---')
    stats = gdrive.calculate_folder_size(gdrive.root_folder_id)
    print(f'Root folder stats:')
    print(f'  Total size: {stats["total_size"]} bytes ({stats["total_size"]/1024/1024:.2f} MB)')
    print(f'  File count: {stats["file_count"]}')
    print(f'  Folder count: {stats["folder_count"]}')

    print('\n--- Testing per-teacher stats ---')
    teachers = CustomUser.objects.filter(role='teacher')[:3]
    for t in teachers:
        print(f'\nTeacher: {t.email}')
        try:
            teacher_stats = gdrive.get_teacher_storage_stats(t)
            print(f'  Total: {teacher_stats["total_size"]/1024/1024:.2f} MB')
            rec = teacher_stats.get("recordings", {})
            hw = teacher_stats.get("homework", {})
            mat = teacher_stats.get("materials", {})
            print(f'  Recordings: {rec.get("total_size", 0)/1024/1024:.2f} MB ({rec.get("file_count", 0)} files)')
            print(f'  Homework: {hw.get("total_size", 0)/1024/1024:.2f} MB ({hw.get("file_count", 0)} files)')
            print(f'  Materials: {mat.get("total_size", 0)/1024/1024:.2f} MB ({mat.get("file_count", 0)} files)')
        except Exception as e:
            print(f'  Error: {e}')

if __name__ == '__main__':
    main()
