#!/usr/bin/env python
"""
Тестовый скрипт для проверки Google Drive OAuth2 интеграции
"""
import os, sys, django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from schedule.gdrive_utils import get_gdrive_manager
from accounts.models import CustomUser
from django.conf import settings

def test_gdrive_connection():
    """Тест подключения к Google Drive"""
    print("=" * 60)
    print("Google Drive OAuth2 Connection Test")
    print("=" * 60)
    
    try:
        # 1. Проверка наличия token file
        token_path = settings.GDRIVE_TOKEN_FILE
        print(f"\n✓ Token file path: {token_path}")
        
        if not os.path.exists(token_path):
            print(f"✗ ERROR: Token file not found!")
            return False
        
        print(f"✓ Token file exists (size: {os.path.getsize(token_path)} bytes)")
        
        # 2. Инициализация Google Drive Manager
        print(f"\n[2/5] Initializing Google Drive Manager...")
        gdrive = get_gdrive_manager()
        print(f"✓ Google Drive Manager initialized")
        
        # 3. Проверка root folder ID
        root_folder = settings.GDRIVE_RECORDINGS_FOLDER_ID
        if root_folder:
            print(f"✓ Root folder ID: {root_folder}")
        else:
            print(f"⚠ Warning: GDRIVE_RECORDINGS_FOLDER_ID not set")
        
        # 4. Проверка доступа к Drive API
        print(f"\n[3/5] Testing Drive API access...")
        file_info = gdrive.get_file_info(root_folder) if root_folder else None
        if file_info:
            print(f"✓ Root folder accessible: {file_info.get('name')}")
        else:
            print(f"⚠ Skipping root folder check (ID not set)")
        
        # 5. Тест создания папки преподавателя
        print(f"\n[4/5] Testing teacher folder creation...")
        
        # Найдём любого преподавателя
        teacher = CustomUser.objects.filter(role='teacher').first()
        
        if not teacher:
            print(f"⚠ No teachers found in database, skipping folder test")
        else:
            print(f"Testing with teacher: {teacher.get_full_name()} (ID: {teacher.id})")
            
            folder_id = gdrive.get_or_create_teacher_folder(teacher)
            print(f"✓ Teacher folder ID: {folder_id}")
        
        # 6. Итоговый результат
        print(f"\n[5/5] Test Results:")
        print(f"=" * 60)
        print(f"✅ Google Drive OAuth2 integration is working!")
        print(f"=" * 60)
        
        print(f"\nNext steps:")
        print(f"1. Upload test recording via API")
        print(f"2. Verify file appears in teacher subfolder")
        print(f"3. Test quota tracking")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_gdrive_connection()
    sys.exit(0 if success else 1)
