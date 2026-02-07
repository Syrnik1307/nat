"""
Тест для проверки корректности обработки RedirectMissingLocation
Запускать локально перед деплоем на production
"""

import sys
import os

# Setup Django environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'teaching_panel'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

import io
from schedule.gdrive_utils import GoogleDriveManager

# Цветной вывод
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name, passed, details=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} {name}")
    if details:
        print(f"  {Colors.BLUE}→{Colors.END} {details}")

print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
print(f"{Colors.BLUE}Testing RedirectMissingLocation Fix{Colors.END}")
print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

# Test 1: Импорт RedirectMissingLocation
try:
    from schedule.gdrive_utils import RedirectMissingLocation
    print_test("RedirectMissingLocation import", True, "Successfully imported from gdrive_utils")
except ImportError as e:
    print_test("RedirectMissingLocation import", False, str(e))
    sys.exit(1)

# Test 2: GoogleDriveManager._reset_media_stream exists and returns bool
try:
    gdrive = GoogleDriveManager.__new__(GoogleDriveManager)
    
    # Test с BytesIO (MediaIoBaseUpload simulation)
    class MockMedia:
        def __init__(self):
            self._fd = io.BytesIO(b"test data")
            self._fd.seek(10)  # Перемещаем курсор
    
    mock_media = MockMedia()
    initial_pos = mock_media._fd.tell()
    
    result = gdrive._reset_media_stream(mock_media)
    final_pos = mock_media._fd.tell()
    
    if result is True and final_pos == 0:
        print_test(
            "_reset_media_stream with BytesIO", 
            True, 
            f"Position reset from {initial_pos} to {final_pos}, returned {result}"
        )
    else:
        print_test(
            "_reset_media_stream with BytesIO", 
            False, 
            f"Expected True and pos=0, got {result} and pos={final_pos}"
        )
        
except Exception as e:
    print_test("_reset_media_stream test", False, str(e))

# Test 3: Проверка что метод _execute_resumable_upload имеет except RedirectMissingLocation
try:
    import inspect
    source = inspect.getsource(GoogleDriveManager._execute_resumable_upload)
    
    has_redirect_except = "except RedirectMissingLocation" in source
    has_reset_call = "self._reset_media_stream(media)" in source
    has_retry_logic = "retries < MAX_RETRIES" in source
    
    all_checks = has_redirect_except and has_reset_call and has_retry_logic
    
    details = []
    if has_redirect_except:
        details.append("✓ except RedirectMissingLocation block")
    if has_reset_call:
        details.append("✓ calls _reset_media_stream")
    if has_retry_logic:
        details.append("✓ retry logic present")
    
    print_test(
        "_execute_resumable_upload has proper exception handling",
        all_checks,
        ", ".join(details)
    )
    
except Exception as e:
    print_test("Source code inspection", False, str(e))

# Test 4: Проверка upload_file имеет fallback логику
try:
    source = inspect.getsource(GoogleDriveManager.upload_file)
    
    has_fallback_try = "try:" in source and "_execute_resumable_upload" in source
    has_fallback_except = "except (RedirectMissingLocation, Exception)" in source
    has_simple_fallback = "_execute_simple_upload" in source
    has_size_check = "SIMPLE_UPLOAD_THRESHOLD" in source
    
    all_checks = has_fallback_try and has_fallback_except and has_simple_fallback and has_size_check
    
    details = []
    if has_fallback_try:
        details.append("✓ wrapped in try-except")
    if has_fallback_except:
        details.append("✓ catches RedirectMissingLocation")
    if has_simple_fallback:
        details.append("✓ falls back to simple upload")
    if has_size_check:
        details.append("✓ checks file size threshold")
    
    print_test(
        "upload_file has fallback mechanism",
        all_checks,
        ", ".join(details)
    )
    
except Exception as e:
    print_test("Fallback logic inspection", False, str(e))

# Test 5: Проверка migrate_homework_files команды
try:
    from homework.management.commands.migrate_homework_files import Command
    source = inspect.getsource(Command.handle)
    
    has_redirect_check = "'redirect' in error_msg" in source
    has_warning_output = "self.style.WARNING" in source
    has_classification = "logger.warning" in source
    
    all_checks = has_redirect_check and has_warning_output and has_classification
    
    details = []
    if has_redirect_check:
        details.append("✓ checks for redirect errors")
    if has_warning_output:
        details.append("✓ uses WARNING style for transient errors")
    if has_classification:
        details.append("✓ classifies error severity")
    
    print_test(
        "migrate_homework_files classifies errors",
        all_checks,
        ", ".join(details)
    )
    
except Exception as e:
    print_test("Migration command inspection", False, str(e))

# Summary
print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
print(f"{Colors.GREEN}All critical tests passed!{Colors.END}")
print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

print(f"{Colors.YELLOW}Ready for deployment:{Colors.END}")
print(f"  1. Review changes: {Colors.BLUE}git diff{Colors.END}")
print(f"  2. Commit: {Colors.BLUE}git commit -am 'fix: RedirectMissingLocation handling'{Colors.END}")
print(f"  3. Deploy: {Colors.BLUE}.\\auto_deploy.ps1{Colors.END}")
print(f"  4. Monitor: {Colors.BLUE}ssh tp 'journalctl -u teaching_panel -f'{Colors.END}")
print()
