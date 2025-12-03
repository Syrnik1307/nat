#!/usr/bin/env python3
"""
Create test users for production testing: deploy_teacher and deploy_student
Run on server: python create_prod_test_users.py
"""
import sys
import os

sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from accounts.models import CustomUser

def create_test_users():
    # Delete existing if any
    CustomUser.objects.filter(email__in=['deploy_teacher@test.com', 'deploy_student@test.com']).delete()
    
    # Create teacher
    teacher = CustomUser.objects.create_user(
        email='deploy_teacher@test.com',
        password='TestPass123!',
        role='teacher',
        first_name='Deploy',
        last_name='Teacher'
    )
    print(f'✅ Created teacher: {teacher.email} (ID: {teacher.id})')
    
    # Create student
    student = CustomUser.objects.create_user(
        email='deploy_student@test.com',
        password='TestPass123!',
        role='student',
        first_name='Deploy',
        last_name='Student'
    )
    print(f'✅ Created student: {student.email} (ID: {student.id})')
    
    print('\n📋 Credentials:')
    print('Teacher: deploy_teacher@test.com / TestPass123!')
    print('Student: deploy_student@test.com / TestPass123!')

if __name__ == '__main__':
    create_test_users()
