#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE","teaching_panel.settings")
import django
django.setup()

from cleanup_old_gdrive_folders import cleanup_old_teacher_folders

print("Starting real cleanup of orphan teacher folders in TeachingPanel...")
cleanup_old_teacher_folders(dry_run=False)
print("Cleanup done.")
