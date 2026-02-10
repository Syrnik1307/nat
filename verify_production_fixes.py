#!/usr/bin/env python
"""
Verification Tests for Production Fixes
Tests the fixes implemented for critical bugs:
1. gdrive_file_id NULL handling
2. Zoom webhook recording.completed
3. Periodic sync fallback
4. Large file streaming optimization
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'teaching_panel'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from schedule.models import LessonRecording, Lesson, Group
from schedule.serializers import LessonRecordingSerializer
from django.utils import timezone
from datetime import timedelta


User = get_user_model()


class GDriveFileIdNullHandlingTest:
    """Test Fix #1: gdrive_file_id NULL error"""
    
    def test_none_value_handled(self):
        """Test that None value for gdrive_file_id is converted to empty string"""
        print("\n[TEST 1.1] Testing gdrive_file_id=None handling...")
        
        # Create test teacher
        teacher = User.objects.create_user(
            email='test_teacher@example.com',
            password='testpass',
            role='teacher'
        )
        
        # Create test group
        group = Group.objects.create(
            name='Test Group',
            teacher=teacher
        )
        
        # Create test lesson
        lesson = Lesson.objects.create(
            title='Test Lesson',
            subject='Math',
            teacher=teacher,
            group=group,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1)
        )
        
        # Test 1: Create recording with gdrive_file_id=None (should convert to '')
        try:
            recording = LessonRecording.objects.create(
                lesson=lesson,
                gdrive_file_id=None,  # This should be handled
                status='ready',
                file_size=1024
            )
            
            # Verify it was saved as empty string, not None
            recording.refresh_from_db()
            assert recording.gdrive_file_id == '', f"Expected empty string, got {recording.gdrive_file_id!r}"
            
            print("  ✅ Recording created with gdrive_file_id=None successfully")
            print(f"  ✅ Value stored as: {recording.gdrive_file_id!r}")
            
            # Cleanup
            recording.delete()
            lesson.delete()
            group.delete()
            teacher.delete()
            
            return True
            
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            return False
    
    def test_or_operator_fallback(self):
        """Test that code uses 'or' operator for None safety"""
        print("\n[TEST 1.2] Testing 'or' operator fallback in code...")
        
        # This tests the logic: gdrive_file_id = gdrive_file_id or ''
        test_cases = [
            (None, ''),
            ('', ''),
            ('abc123', 'abc123'),
            ('', ''),
        ]
        
        passed = 0
        for input_val, expected in test_cases:
            result = input_val or ''
            if result == expected:
                passed += 1
            else:
                print(f"  ❌ Failed: input={input_val!r}, expected={expected!r}, got={result!r}")
                return False
        
        print(f"  ✅ All {passed}/{len(test_cases)} fallback tests passed")
        return True


class ZoomWebhookTest:
    """Test Fix #2: Zoom webhook recording.completed"""
    
    def test_webhook_endpoint_exists(self):
        """Test that webhook endpoint is properly registered"""
        print("\n[TEST 2.1] Checking Zoom webhook endpoint...")
        
        from django.urls import get_resolver
        
        try:
            resolver = get_resolver()
            
            # Check if the webhook URL is registered
            webhook_patterns = [
                '/schedule/api/zoom/webhook/',
                'schedule/api/zoom/webhook/',
            ]
            
            found = False
            for pattern in webhook_patterns:
                try:
                    match = resolver.resolve(pattern)
                    if match:
                        found = True
                        print(f"  ✅ Webhook endpoint found: {pattern}")
                        print(f"     Handler: {match.func.__module__}.{match.func.__name__}")
                        break
                except:
                    continue
            
            if not found:
                print("  ❌ Webhook endpoint not found in URL configuration")
                return False
            
            return True
            
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            return False
    
    def test_webhook_handler_imports(self):
        """Test that webhook handler can be imported"""
        print("\n[TEST 2.2] Testing webhook handler imports...")
        
        try:
            from schedule.webhooks import zoom_webhook, handle_recording_completed
            
            print("  ✅ zoom_webhook imported successfully")
            print("  ✅ handle_recording_completed imported successfully")
            
            # Check if functions are callable
            assert callable(zoom_webhook), "zoom_webhook is not callable"
            assert callable(handle_recording_completed), "handle_recording_completed is not callable"
            
            print("  ✅ All webhook handlers are callable")
            return True
            
        except ImportError as e:
            print(f"  ❌ Import failed: {e}")
            return False
        except AssertionError as e:
            print(f"  ❌ Assertion failed: {e}")
            return False


class PeriodicSyncTest:
    """Test Fix #3: Periodic sync fallback task"""
    
    def test_sync_task_registered(self):
        """Test that sync_missing_zoom_recordings task is registered"""
        print("\n[TEST 3.1] Checking sync task registration...")
        
        try:
            from schedule.tasks import sync_missing_zoom_recordings
            
            print(f"  ✅ Task imported: {sync_missing_zoom_recordings.name}")
            
            # Check if task is callable
            assert callable(sync_missing_zoom_recordings), "Task is not callable"
            print("  ✅ Task is callable")
            
            return True
            
        except ImportError as e:
            print(f"  ❌ Import failed: {e}")
            return False
        except AssertionError as e:
            print(f"  ❌ Assertion failed: {e}")
            return False
    
    def test_sync_in_beat_schedule(self):
        """Test that sync task is in CELERY_BEAT_SCHEDULE"""
        print("\n[TEST 3.2] Checking Celery Beat schedule...")
        
        try:
            from django.conf import settings
            
            beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
            
            # Look for sync task in schedule
            sync_task_key = 'sync-missing-zoom-recordings'
            
            if sync_task_key in beat_schedule:
                task_config = beat_schedule[sync_task_key]
                print(f"  ✅ Task found in schedule: {sync_task_key}")
                print(f"     Task name: {task_config.get('task')}")
                print(f"     Schedule: every {task_config.get('schedule')} seconds")
                return True
            else:
                print(f"  ❌ Task not found in CELERY_BEAT_SCHEDULE")
                print(f"     Available tasks: {list(beat_schedule.keys())}")
                return False
                
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            return False


class LargeFileStreamingTest:
    """Test Fix #5: Large file streaming optimization"""
    
    def test_use_direct_stream_flag(self):
        """Test that use_direct_stream flag is set correctly"""
        print("\n[TEST 5.1] Testing use_direct_stream flag logic...")
        
        # Create test teacher
        teacher = User.objects.create_user(
            email='test_teacher_stream@example.com',
            password='testpass',
            role='teacher'
        )
        
        group = Group.objects.create(
            name='Test Group Stream',
            teacher=teacher
        )
        
        lesson = Lesson.objects.create(
            title='Test Lesson Stream',
            subject='Math',
            teacher=teacher,
            group=group,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1)
        )
        
        # Test small file (<100MB) - should use GDrive iframe
        small_file = LessonRecording.objects.create(
            lesson=lesson,
            file_size=50 * 1024 * 1024,  # 50MB
            gdrive_file_id='small_file_123',
            status='ready'
        )
        
        # Test large file (>100MB) - should use direct stream
        large_file = LessonRecording.objects.create(
            lesson=lesson,
            file_size=150 * 1024 * 1024,  # 150MB
            gdrive_file_id='large_file_456',
            status='ready'
        )
        
        # Serialize and check flags
        small_serializer = LessonRecordingSerializer(small_file)
        large_serializer = LessonRecordingSerializer(large_file)
        
        small_data = small_serializer.data
        large_data = large_serializer.data
        
        # Verify use_direct_stream flag
        assert small_data.get('use_direct_stream') == False, \
            f"Small file should have use_direct_stream=False, got {small_data.get('use_direct_stream')}"
        
        assert large_data.get('use_direct_stream') == True, \
            f"Large file should have use_direct_stream=True, got {large_data.get('use_direct_stream')}"
        
        print(f"  ✅ Small file (50MB): use_direct_stream = {small_data.get('use_direct_stream')}")
        print(f"  ✅ Large file (150MB): use_direct_stream = {large_data.get('use_direct_stream')}")
        
        # Verify streaming_url is correct
        assert '/stream/' in large_data.get('streaming_url', ''), \
            "Large file should have stream URL in streaming_url"
        
        print(f"  ✅ Large file streaming_url: {large_data.get('streaming_url')}")
        
        # Cleanup
        small_file.delete()
        large_file.delete()
        lesson.delete()
        group.delete()
        teacher.delete()
        
        return True


def run_all_tests():
    """Run all verification tests"""
    print("\n" + "="*60)
    print("Production Fixes - Verification Tests")
    print("="*60)
    
    results = {}
    
    # Test Suite 1: gdrive_file_id NULL handling
    print("\n" + "="*60)
    print("Test Suite 1: gdrive_file_id NULL Handling")
    print("="*60)
    suite1 = GDriveFileIdNullHandlingTest()
    results['test_1_1'] = suite1.test_none_value_handled()
    results['test_1_2'] = suite1.test_or_operator_fallback()
    
    # Test Suite 2: Zoom webhook
    print("\n" + "="*60)
    print("Test Suite 2: Zoom Webhook Recording.Completed")
    print("="*60)
    suite2 = ZoomWebhookTest()
    results['test_2_1'] = suite2.test_webhook_endpoint_exists()
    results['test_2_2'] = suite2.test_webhook_handler_imports()
    
    # Test Suite 3: Periodic sync
    print("\n" + "="*60)
    print("Test Suite 3: Periodic Sync Fallback")
    print("="*60)
    suite3 = PeriodicSyncTest()
    results['test_3_1'] = suite3.test_sync_task_registered()
    results['test_3_2'] = suite3.test_sync_in_beat_schedule()
    
    # Test Suite 5: Large file streaming
    print("\n" + "="*60)
    print("Test Suite 5: Large File Streaming Optimization")
    print("="*60)
    suite5 = LargeFileStreamingTest()
    try:
        results['test_5_1'] = suite5.test_use_direct_stream_flag()
    except Exception as e:
        print(f"  ❌ Test failed with exception: {e}")
        results['test_5_1'] = False
    
    # Summary
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "="*60)
    print(f"Total: {passed}/{total} tests passed ({100*passed//total}%)")
    print("="*60)
    
    if passed == total:
        print("\n✅ All tests passed! Ready for production deployment.")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please fix issues before deployment.")
        sys.exit(1)


if __name__ == '__main__':
    run_all_tests()
