"""
Simple test script for Zoom Pool system (no emojis for PowerShell compatibility)
Run with: python manage.py test_zoom_simple
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from schedule.models import ZoomAccount, Lesson, Group
from accounts.models import CustomUser
from schedule.tasks import release_stuck_zoom_accounts


class Command(BaseCommand):
    help = 'Test Zoom Pool system'
    
    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("Testing Zoom Pool System")
        self.stdout.write("=" * 60)
        
        # Step 1: Check Zoom accounts
        self.stdout.write("\nStep 1: Checking Zoom Accounts")
        self.stdout.write("-" * 60)
        
        zoom_accounts = ZoomAccount.objects.all()
        self.stdout.write(f"Total accounts: {zoom_accounts.count()}")
        
        if zoom_accounts.count() == 0:
            self.stdout.write(self.style.WARNING("No Zoom accounts! Creating test accounts..."))
            ZoomAccount.objects.create(
                name="Test Zoom Account 1",
                api_key="fake_api_key_1",
                api_secret="fake_secret_1",
                zoom_user_id="test_user_1"
            )
            ZoomAccount.objects.create(
                name="Test Zoom Account 2",
                api_key="fake_api_key_2",
                api_secret="fake_secret_2",
                zoom_user_id="test_user_2"
            )
            self.stdout.write(self.style.SUCCESS("Created 2 test accounts"))
            zoom_accounts = ZoomAccount.objects.all()
        
        for account in zoom_accounts:
            status = "BUSY" if account.is_busy else "FREE"
            self.stdout.write(f"  [{status}] {account.name}")
            if account.current_lesson:
                self.stdout.write(f"        Lesson: {account.current_lesson.title} (ID: {account.current_lesson.id})")
        
        # Step 2: Create test lesson
        self.stdout.write("\nStep 2: Creating test lesson")
        self.stdout.write("-" * 60)
        
        try:
            teacher = CustomUser.objects.filter(role='teacher').first()
            group = Group.objects.first()
            
            if not teacher or not group:
                self.stdout.write(self.style.WARNING("No teacher or group found. Creating..."))
                if not teacher:
                    teacher = CustomUser.objects.create_user(
                        email='testteacher@example.com',
                        password='test123',
                        role='teacher',
                        first_name='Test',
                        last_name='Teacher'
                    )
                if not group:
                    group = Group.objects.create(
                        name='Test Group',
                        teacher=teacher,
                        description='Test group for Zoom Pool'
                    )
            
            # Remove old test lessons
            Lesson.objects.filter(title__startswith='[TEST]').delete()
            
            test_lesson = Lesson.objects.create(
                title='[TEST] Zoom Pool Test Lesson',
                teacher=teacher,
                group=group,
                start_time=timezone.now(),
                end_time=timezone.now() + timedelta(hours=1),
                topics='Testing atomic Zoom account capture'
            )
            self.stdout.write(self.style.SUCCESS(f"Lesson created: ID={test_lesson.id}"))
            self.stdout.write(f"  Teacher: {test_lesson.teacher.email}")
            self.stdout.write(f"  Group: {test_lesson.group.name}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating lesson: {e}"))
            test_lesson = None
        
        # Step 3: Test atomic capture
        self.stdout.write("\nStep 3: Testing atomic capture (select_for_update)")
        self.stdout.write("-" * 60)
        
        if test_lesson:
            from django.db import transaction
            
            try:
                with transaction.atomic():
                    free_account = ZoomAccount.objects.select_for_update().filter(
                        is_busy=False
                    ).first()
                    
                    if free_account:
                        self.stdout.write(f"Captured account: {free_account.name}")
                        
                        free_account.is_busy = True
                        free_account.current_lesson = test_lesson
                        free_account.save()
                        
                        from schedule.zoom_client import my_zoom_api_client
                        meeting_data = my_zoom_api_client.create_meeting(
                            topic=test_lesson.title,
                            start_time=test_lesson.start_time.isoformat(),
                            duration=60
                        )
                        
                        test_lesson.zoom_meeting_id = meeting_data['id']
                        test_lesson.zoom_start_url = meeting_data['start_url']
                        test_lesson.zoom_join_url = meeting_data['join_url']
                        test_lesson.zoom_password = meeting_data.get('password', '')
                        test_lesson.zoom_account_used = free_account
                        test_lesson.save()
                        
                        self.stdout.write(self.style.SUCCESS(f"Meeting created: {meeting_data['id']}"))
                        self.stdout.write(f"  Start URL: {meeting_data['start_url'][:60]}...")
                        
                    else:
                        self.stdout.write(self.style.WARNING("All accounts are busy!"))
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error capturing: {e}"))
        else:
            self.stdout.write("Skip - no test lesson")
        
        # Step 4: Check state after capture
        self.stdout.write("\nStep 4: Account state after capture")
        self.stdout.write("-" * 60)
        
        for account in ZoomAccount.objects.all():
            status = "BUSY" if account.is_busy else "FREE"
            self.stdout.write(f"  [{status}] {account.name}")
            if account.current_lesson:
                self.stdout.write(f"        Lesson #{account.current_lesson.id}: {account.current_lesson.title}")
        
        # Step 5: Test webhook
        self.stdout.write("\nStep 5: Testing Webhook (release account)")
        self.stdout.write("-" * 60)
        
        if test_lesson and test_lesson.zoom_meeting_id:
            try:
                self.stdout.write(f"Simulating webhook for meeting_id: {test_lesson.zoom_meeting_id}")
                
                lesson = Lesson.objects.select_related('zoom_account_used').get(
                    zoom_meeting_id=test_lesson.zoom_meeting_id
                )
                
                zoom_account = lesson.zoom_account_used
                if zoom_account and zoom_account.is_busy:
                    zoom_account.is_busy = False
                    zoom_account.current_lesson = None
                    zoom_account.save()
                    self.stdout.write(self.style.SUCCESS(f"Account {zoom_account.name} released via webhook"))
                else:
                    self.stdout.write(self.style.WARNING("Account was already free"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Webhook error: {e}"))
        else:
            self.stdout.write("Skip - no meeting_id for test")
        
        # Step 6: Test Celery task
        self.stdout.write("\nStep 6: Testing Celery task (stuck accounts)")
        self.stdout.write("-" * 60)
        
        if test_lesson:
            test_lesson.end_time = timezone.now() - timedelta(minutes=20)
            test_lesson.save()
            
            account = ZoomAccount.objects.first()
            account.is_busy = True
            account.current_lesson = test_lesson
            account.save()
            
            self.stdout.write("Created stuck lesson (ended 20 min ago)")
            self.stdout.write(f"  Account {account.name} marked as busy")
        
        try:
            self.stdout.write("\nRunning release_stuck_zoom_accounts()...")
            result = release_stuck_zoom_accounts()
            
            self.stdout.write("\nResult:")
            self.stdout.write(f"  Released stuck: {result['released_stuck']}")
            self.stdout.write(f"  Released orphaned: {result['released_orphaned']}")
            self.stdout.write(f"  Total: {result['total']}")
            
            if result['total'] > 0:
                self.stdout.write(self.style.SUCCESS("Task successfully released accounts"))
            else:
                self.stdout.write(self.style.WARNING("Task found no stuck accounts"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Celery task error: {e}"))
        
        # Final state
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Final System State")
        self.stdout.write("=" * 60)
        
        total_accounts = ZoomAccount.objects.count()
        busy_accounts = ZoomAccount.objects.filter(is_busy=True).count()
        free_accounts = total_accounts - busy_accounts
        
        self.stdout.write("\nStatistics:")
        self.stdout.write(f"  Total accounts: {total_accounts}")
        self.stdout.write(f"  Busy: {busy_accounts}")
        self.stdout.write(f"  Free: {free_accounts}")
        
        total_lessons = Lesson.objects.count()
        with_zoom = Lesson.objects.exclude(zoom_meeting_id__isnull=True).exclude(zoom_meeting_id='').count()
        self.stdout.write(f"\n  Total lessons: {total_lessons}")
        self.stdout.write(f"  With Zoom meeting: {with_zoom}")
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Testing completed!"))
        self.stdout.write("=" * 60)
        
        self.stdout.write("\nUseful API endpoints:")
        self.stdout.write("  GET  /schedule/api/zoom-accounts/")
        self.stdout.write("  GET  /schedule/api/zoom-accounts/status_summary/")
        self.stdout.write("  POST /schedule/lesson/<id>/start/")
        self.stdout.write("  POST /schedule/webhook/zoom/")
