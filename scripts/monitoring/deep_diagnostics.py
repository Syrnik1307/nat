#!/usr/bin/env python3
"""
LECTIO DEEP DIAGNOSTICS v1.0
============================
Глубокая диагностика системы с доступом к Django ORM.
Проверяет консистентность данных, бизнес-логику и интеграции.

Запуск:
  cd /var/www/teaching_panel/teaching_panel
  ../venv/bin/python ../scripts/monitoring/deep_diagnostics.py

Или через manage.py:
  python manage.py shell < ../scripts/monitoring/deep_diagnostics.py
"""

import os
import sys
import json
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
from pathlib import Path

# Автоматическое определение пути к проекту
# Скрипт лежит в: PROJECT_ROOT/scripts/monitoring/deep_diagnostics.py
# Django проект в: PROJECT_ROOT/teaching_panel/
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DJANGO_DIR = PROJECT_ROOT / 'teaching_panel'

# Добавляем в sys.path если еще нет
if str(DJANGO_DIR) not in sys.path:
    sys.path.insert(0, str(DJANGO_DIR))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django.conf import settings
from django.utils import timezone
from django.db import connection
from django.db.models import Count, Sum, Q, F

# Import models
from accounts.models import CustomUser, Subscription, Payment
from schedule.models import Group, Lesson, LessonRecording
from homework.models import Homework, StudentSubmission


class DiagnosticResult:
    """Результат одной проверки"""
    
    def __init__(self, category, name, status, message, details=None):
        self.category = category
        self.name = name
        self.status = status  # OK, WARN, FAIL, INFO
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        icon = {'OK': '✓', 'WARN': '⚠', 'FAIL': '✗', 'INFO': 'ℹ'}.get(self.status, '?')
        return f"[{icon}] {self.category}/{self.name}: {self.message}"


class LectioDiagnostics:
    """Глубокая диагностика Lectio"""
    
    def __init__(self):
        self.results = []
        self.now = timezone.now()
    
    def add_result(self, category, name, status, message, details=None):
        result = DiagnosticResult(category, name, status, message, details)
        self.results.append(result)
        print(result)
        return result
    
    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    
    def check_users_integrity(self):
        """Проверка целостности пользователей"""
        
        # Пользователи без email
        no_email = CustomUser.objects.filter(email='').count()
        if no_email > 0:
            self.add_result('USERS', 'Users without email', 'FAIL', 
                          f'{no_email} users have no email')
        else:
            self.add_result('USERS', 'Users without email', 'OK', 'All users have email')
        
        # Дублирующиеся email (case insensitive)
        from django.db.models.functions import Lower
        duplicates = CustomUser.objects.annotate(
            lower_email=Lower('email')
        ).values('lower_email').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        dup_count = duplicates.count()
        if dup_count > 0:
            self.add_result('USERS', 'Duplicate emails', 'WARN',
                          f'{dup_count} email addresses are duplicated')
        else:
            self.add_result('USERS', 'Duplicate emails', 'OK', 'No duplicate emails')
        
        # Учителя без подписки
        teachers = CustomUser.objects.filter(role='teacher', is_active=True)
        teachers_without_sub = teachers.filter(subscription__isnull=True).count()
        
        if teachers_without_sub > 0:
            self.add_result('USERS', 'Teachers without subscription', 'WARN',
                          f'{teachers_without_sub} active teachers have no subscription record')
        else:
            self.add_result('USERS', 'Teachers without subscription', 'OK',
                          'All teachers have subscription records')
    
    def check_students_groups(self):
        """Проверка связей студентов и групп"""
        
        students = CustomUser.objects.filter(role='student', is_active=True)
        total_students = students.count()
        
        # Студенты не в группах
        orphaned = students.annotate(
            group_count=Count('enrolled_groups')
        ).filter(group_count=0).count()
        
        if total_students > 0:
            orphan_percent = orphaned / total_students * 100
            
            if orphan_percent < 10:
                self.add_result('USERS', 'Students without groups', 'OK',
                              f'{orphaned}/{total_students} ({orphan_percent:.1f}%) orphaned')
            elif orphan_percent < 30:
                self.add_result('USERS', 'Students without groups', 'WARN',
                              f'{orphaned}/{total_students} ({orphan_percent:.1f}%) orphaned')
            else:
                self.add_result('USERS', 'Students without groups', 'FAIL',
                              f'{orphaned}/{total_students} ({orphan_percent:.1f}%) orphaned - data loss?')
        else:
            self.add_result('USERS', 'Students without groups', 'INFO', 'No students in system')
    
    # ==================== ПОДПИСКИ ====================
    
    def check_subscriptions(self):
        """Проверка подписок"""
        
        # Expired but still active
        expired_active = Subscription.objects.filter(
            status='active',
            expires_at__lt=self.now
        ).count()
        
        if expired_active > 0:
            self.add_result('SUBSCRIPTIONS', 'Expired but active', 'FAIL',
                          f'{expired_active} subscriptions expired but still marked active')
        else:
            self.add_result('SUBSCRIPTIONS', 'Expired but active', 'OK',
                          'All subscription statuses are consistent')
        
        # Subscriptions expiring soon (within 7 days)
        week_from_now = self.now + timedelta(days=7)
        expiring_soon = Subscription.objects.filter(
            status='active',
            expires_at__gt=self.now,
            expires_at__lt=week_from_now
        ).count()
        
        self.add_result('SUBSCRIPTIONS', 'Expiring soon', 'INFO',
                      f'{expiring_soon} subscriptions expire within 7 days')
        
        # Storage usage check
        over_limit = Subscription.objects.filter(
            used_storage_gb__gt=F('base_storage_gb') + F('extra_storage_gb')
        ).count()
        
        if over_limit > 0:
            self.add_result('SUBSCRIPTIONS', 'Storage over limit', 'WARN',
                          f'{over_limit} subscriptions over storage limit')
        else:
            self.add_result('SUBSCRIPTIONS', 'Storage over limit', 'OK',
                          'All within storage limits')
    
    # ==================== ПЛАТЕЖИ ====================
    
    def check_payments(self):
        """Проверка платежей"""
        
        # Pending payments older than 1 hour
        one_hour_ago = self.now - timedelta(hours=1)
        stuck_pending = Payment.objects.filter(
            status='pending',
            created_at__lt=one_hour_ago
        ).count()
        
        if stuck_pending > 0:
            self.add_result('PAYMENTS', 'Stuck pending payments', 'WARN',
                          f'{stuck_pending} payments pending for >1 hour')
        else:
            self.add_result('PAYMENTS', 'Stuck pending payments', 'OK',
                          'No stuck payments')
        
        # Failed payments in last 24h
        day_ago = self.now - timedelta(days=1)
        failed_24h = Payment.objects.filter(
            status='failed',
            created_at__gt=day_ago
        ).count()
        
        total_24h = Payment.objects.filter(created_at__gt=day_ago).count()
        
        if total_24h > 0:
            fail_rate = failed_24h / total_24h * 100
            if fail_rate < 10:
                self.add_result('PAYMENTS', 'Payment failure rate (24h)', 'OK',
                              f'{failed_24h}/{total_24h} failed ({fail_rate:.1f}%)')
            elif fail_rate < 30:
                self.add_result('PAYMENTS', 'Payment failure rate (24h)', 'WARN',
                              f'{failed_24h}/{total_24h} failed ({fail_rate:.1f}%)')
            else:
                self.add_result('PAYMENTS', 'Payment failure rate (24h)', 'FAIL',
                              f'{failed_24h}/{total_24h} failed ({fail_rate:.1f}%) - HIGH')
        else:
            self.add_result('PAYMENTS', 'Payment failure rate (24h)', 'INFO',
                          'No payments in last 24h')
        
        # Payments without subscription link
        orphaned_payments = Payment.objects.filter(subscription__isnull=True).count()
        if orphaned_payments > 0:
            self.add_result('PAYMENTS', 'Orphaned payments', 'WARN',
                          f'{orphaned_payments} payments without subscription link')
        else:
            self.add_result('PAYMENTS', 'Orphaned payments', 'OK',
                          'All payments linked to subscriptions')
    
    # ==================== ГРУППЫ И УРОКИ ====================
    
    def check_groups_lessons(self):
        """Проверка групп и уроков"""
        
        # Groups without students
        empty_groups = Group.objects.annotate(
            student_count=Count('students')
        ).filter(student_count=0).count()
        
        total_groups = Group.objects.count()
        
        if total_groups > 0:
            if empty_groups / total_groups < 0.3:
                self.add_result('GROUPS', 'Empty groups', 'OK',
                              f'{empty_groups}/{total_groups} groups have no students')
            else:
                self.add_result('GROUPS', 'Empty groups', 'WARN',
                              f'{empty_groups}/{total_groups} groups have no students')
        else:
            self.add_result('GROUPS', 'Empty groups', 'INFO', 'No groups in system')
        
        # Lessons without groups
        orphan_lessons = Lesson.objects.filter(group__isnull=True).count()
        if orphan_lessons > 0:
            self.add_result('LESSONS', 'Lessons without groups', 'WARN',
                          f'{orphan_lessons} lessons have no group')
        else:
            self.add_result('LESSONS', 'Lessons without groups', 'OK',
                          'All lessons have groups')
        
        # Lessons in the past without attendance
        week_ago = self.now - timedelta(days=7)
        past_lessons = Lesson.objects.filter(
            start_time__lt=week_ago,
            start_time__gt=self.now - timedelta(days=30)
        )
        
        # This is just informational
        self.add_result('LESSONS', 'Lessons in last month', 'INFO',
                      f'{past_lessons.count()} lessons conducted')
    
    # ==================== ЗАПИСИ ====================
    
    def check_recordings(self):
        """Проверка записей уроков"""
        
        total_recordings = LessonRecording.objects.count()
        
        # Recordings without files
        no_files = LessonRecording.objects.filter(
            Q(gdrive_file_id='') | Q(gdrive_file_id__isnull=True),
            Q(download_url='') | Q(download_url__isnull=True)
        ).count()
        
        if no_files > 0:
            if no_files / max(total_recordings, 1) < 0.1:
                self.add_result('RECORDINGS', 'Recordings without files', 'WARN',
                              f'{no_files}/{total_recordings} recordings have no file')
            else:
                self.add_result('RECORDINGS', 'Recordings without files', 'FAIL',
                              f'{no_files}/{total_recordings} recordings have no file - HIGH')
        else:
            self.add_result('RECORDINGS', 'Recordings without files', 'OK',
                          f'All {total_recordings} recordings have files')
        
        # Recordings without lesson or teacher
        orphaned = LessonRecording.objects.filter(
            lesson__isnull=True,
            teacher__isnull=True
        ).count()
        
        if orphaned > 0:
            self.add_result('RECORDINGS', 'Orphaned recordings', 'WARN',
                          f'{orphaned} recordings have no lesson or teacher')
        else:
            self.add_result('RECORDINGS', 'Orphaned recordings', 'OK',
                          'All recordings have owners')
        
        # Recordings with expired Zoom links (>7 days old with zoom URL but no gdrive)
        week_ago = self.now - timedelta(days=7)
        expired_zoom = LessonRecording.objects.filter(
            created_at__lt=week_ago,
            zoom_recording_id__isnull=False,
            gdrive_file_id=''
        ).exclude(zoom_recording_id='').count()
        
        if expired_zoom > 0:
            self.add_result('RECORDINGS', 'Recordings with expired Zoom links', 'WARN',
                          f'{expired_zoom} old recordings still using Zoom (not archived to GDrive)')
        else:
            self.add_result('RECORDINGS', 'Recordings with expired Zoom links', 'OK',
                          'No expired Zoom-only recordings')
    
    # ==================== ДОМАШНИЕ ЗАДАНИЯ ====================
    
    def check_homework(self):
        """Проверка домашних заданий"""
        
        # Homework without teacher
        no_teacher = Homework.objects.filter(teacher__isnull=True).count()
        if no_teacher > 0:
            self.add_result('HOMEWORK', 'Homework without teacher', 'FAIL',
                          f'{no_teacher} homeworks have no teacher')
        else:
            self.add_result('HOMEWORK', 'Homework without teacher', 'OK',
                          'All homeworks have teachers')
        
        # Submissions pending grading for >7 days
        week_ago = self.now - timedelta(days=7)
        old_pending = StudentSubmission.objects.filter(
            status='pending',
            submitted_at__lt=week_ago
        ).count()
        
        if old_pending > 0:
            self.add_result('HOMEWORK', 'Old ungraded submissions', 'WARN',
                          f'{old_pending} submissions pending grading >7 days')
        else:
            self.add_result('HOMEWORK', 'Old ungraded submissions', 'OK',
                          'No old ungraded submissions')
        
        # Homework with no submissions at all (past deadline)
        past_deadline = Homework.objects.filter(
            deadline__lt=self.now
        ).annotate(
            sub_count=Count('submissions')
        ).filter(sub_count=0).count()
        
        total_past = Homework.objects.filter(deadline__lt=self.now).count()
        
        self.add_result('HOMEWORK', 'Past-deadline homework without submissions', 'INFO',
                      f'{past_deadline}/{total_past} past-deadline homeworks have no submissions')
    
    # ==================== GOOGLE DRIVE ====================
    
    def check_gdrive(self):
        """Проверка Google Drive"""
        
        if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
            self.add_result('GDRIVE', 'Status', 'INFO', 'Google Drive storage disabled')
            return
        
        try:
            from schedule.gdrive_utils import get_gdrive_manager
            manager = get_gdrive_manager()
            
            # Test connection
            about = manager.service.about().get(fields='user,storageQuota').execute()
            user_email = about.get('user', {}).get('emailAddress', 'unknown')
            
            self.add_result('GDRIVE', 'Connection', 'OK', f'Connected as {user_email}')
            
            # Check quota
            quota = about.get('storageQuota', {})
            limit = int(quota.get('limit', 0))
            usage = int(quota.get('usage', 0))
            
            if limit > 0:
                percent = usage / limit * 100
                limit_gb = limit / (1024**3)
                usage_gb = usage / (1024**3)
                
                if percent < 80:
                    self.add_result('GDRIVE', 'Quota', 'OK',
                                  f'{usage_gb:.1f}GB / {limit_gb:.1f}GB ({percent:.1f}%)')
                elif percent < 95:
                    self.add_result('GDRIVE', 'Quota', 'WARN',
                                  f'{usage_gb:.1f}GB / {limit_gb:.1f}GB ({percent:.1f}%) - running low')
                else:
                    self.add_result('GDRIVE', 'Quota', 'FAIL',
                                  f'{usage_gb:.1f}GB / {limit_gb:.1f}GB ({percent:.1f}%) - FULL!')
            else:
                self.add_result('GDRIVE', 'Quota', 'INFO', 'Unlimited storage')
            
            # Check root folder access
            root_id = getattr(settings, 'GDRIVE_ROOT_FOLDER_ID', None)
            if root_id:
                try:
                    files = manager.service.files().list(
                        q=f"'{root_id}' in parents",
                        pageSize=1,
                        fields='files(id)'
                    ).execute()
                    self.add_result('GDRIVE', 'Root folder', 'OK', 'Accessible')
                except Exception as e:
                    self.add_result('GDRIVE', 'Root folder', 'FAIL', f'Cannot access: {str(e)[:50]}')
            else:
                self.add_result('GDRIVE', 'Root folder', 'WARN', 'GDRIVE_ROOT_FOLDER_ID not set')
                
        except Exception as e:
            self.add_result('GDRIVE', 'Connection', 'FAIL', f'Error: {str(e)[:80]}')
    
    # ==================== ZOOM ====================
    
    def check_zoom(self):
        """Проверка Zoom интеграции"""
        
        # Teachers with Zoom credentials
        teachers_with_zoom = CustomUser.objects.filter(
            role='teacher',
            zoom_account_id__isnull=False
        ).exclude(
            zoom_account_id=''
        ).exclude(
            zoom_account_id__in=['bad', 'test', 'invalid']
        )
        
        total_teachers = CustomUser.objects.filter(role='teacher', is_active=True).count()
        zoom_teachers = teachers_with_zoom.count()
        
        self.add_result('ZOOM', 'Teachers with credentials', 'INFO',
                      f'{zoom_teachers}/{total_teachers} teachers have Zoom credentials')
        
        # Test OAuth for first teacher
        if zoom_teachers > 0:
            teacher = teachers_with_zoom.first()
            try:
                from schedule.zoom_client import ZoomAPIClient
                client = ZoomAPIClient(
                    account_id=teacher.zoom_account_id,
                    client_id=teacher.zoom_client_id,
                    client_secret=teacher.zoom_client_secret
                )
                token = client._get_access_token()
                
                if token and len(token) > 20:
                    self.add_result('ZOOM', 'OAuth token', 'OK',
                                  f'Token obtained for {teacher.email}')
                else:
                    self.add_result('ZOOM', 'OAuth token', 'FAIL', 'Empty token returned')
            except Exception as e:
                self.add_result('ZOOM', 'OAuth token', 'FAIL', f'Error: {str(e)[:80]}')
        else:
            self.add_result('ZOOM', 'OAuth token', 'SKIP', 'No teachers with Zoom credentials')
    
    # ==================== ПРОИЗВОДИТЕЛЬНОСТЬ ====================
    
    def check_performance(self):
        """Проверка производительности БД"""
        
        import time
        
        # Simple query timing
        start = time.time()
        list(CustomUser.objects.all()[:100])
        user_time = time.time() - start
        
        start = time.time()
        list(Lesson.objects.select_related('group', 'teacher').all()[:100])
        lesson_time = time.time() - start
        
        start = time.time()
        list(LessonRecording.objects.select_related('lesson', 'teacher').all()[:100])
        recording_time = time.time() - start
        
        # Evaluate times
        if user_time < 0.1 and lesson_time < 0.2 and recording_time < 0.2:
            self.add_result('PERFORMANCE', 'Query times', 'OK',
                          f'Users: {user_time:.3f}s, Lessons: {lesson_time:.3f}s, Recordings: {recording_time:.3f}s')
        elif user_time < 0.5 and lesson_time < 0.5 and recording_time < 0.5:
            self.add_result('PERFORMANCE', 'Query times', 'WARN',
                          f'Slow queries - Users: {user_time:.3f}s, Lessons: {lesson_time:.3f}s')
        else:
            self.add_result('PERFORMANCE', 'Query times', 'FAIL',
                          f'Very slow - Users: {user_time:.3f}s, Lessons: {lesson_time:.3f}s')
        
        # Table sizes
        tables = {
            'Users': CustomUser.objects.count(),
            'Groups': Group.objects.count(),
            'Lessons': Lesson.objects.count(),
            'Recordings': LessonRecording.objects.count(),
            'Homeworks': Homework.objects.count(),
            'Submissions': StudentSubmission.objects.count(),
            'Payments': Payment.objects.count(),
        }
        
        table_info = ', '.join([f'{k}: {v}' for k, v in tables.items()])
        self.add_result('PERFORMANCE', 'Table sizes', 'INFO', table_info)
    
    # ==================== ГЛАВНЫЙ ЗАПУСК ====================
    
    def run_all(self):
        """Запуск всех проверок"""
        
        print("=" * 60)
        print("LECTIO DEEP DIAGNOSTICS")
        print(f"Started: {self.now.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        
        print("=== USERS ===")
        self.check_users_integrity()
        self.check_students_groups()
        print()
        
        print("=== SUBSCRIPTIONS ===")
        self.check_subscriptions()
        print()
        
        print("=== PAYMENTS ===")
        self.check_payments()
        print()
        
        print("=== GROUPS & LESSONS ===")
        self.check_groups_lessons()
        print()
        
        print("=== RECORDINGS ===")
        self.check_recordings()
        print()
        
        print("=== HOMEWORK ===")
        self.check_homework()
        print()
        
        print("=== GOOGLE DRIVE ===")
        self.check_gdrive()
        print()
        
        print("=== ZOOM ===")
        self.check_zoom()
        print()
        
        print("=== PERFORMANCE ===")
        self.check_performance()
        print()
        
        # Summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        status_counts = defaultdict(int)
        for r in self.results:
            status_counts[r.status] += 1
        
        print(f"Total checks: {len(self.results)}")
        print(f"  OK:       {status_counts['OK']}")
        print(f"  WARNINGS: {status_counts['WARN']}")
        print(f"  FAILURES: {status_counts['FAIL']}")
        print(f"  INFO:     {status_counts['INFO']}")
        print()
        
        if status_counts['FAIL'] > 0:
            print("CRITICAL ISSUES:")
            for r in self.results:
                if r.status == 'FAIL':
                    print(f"  - {r.category}/{r.name}: {r.message}")
        
        print()
        print(f"Completed: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return status_counts['FAIL']


if __name__ == '__main__':
    diag = LectioDiagnostics()
    exit_code = diag.run_all()
    sys.exit(exit_code)
