#!/usr/bin/env python3
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')

django.setup()

from accounts.models import User

print(f"Total users: {User.objects.count()}")
print("\nFirst 5 users:")
for u in User.objects.all()[:5]:
    print(f"  {u.email} ({u.get_role()})")
