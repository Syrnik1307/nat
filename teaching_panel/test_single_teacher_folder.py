#!/usr/bin/env python
"""
Простой тест: создание ОДНОЙ папки учителя в правильной директории
"""

import os
import uuid
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from accounts.models import CustomUser, Subscription


def main():
    print("=" * 60)
    print("  ТЕСТ: Создание папки учителя при оплате подписки")
    print("=" * 60)
    print()
    
    # 1. Проверяем настройки
    print(f"📁 GDRIVE_ROOT_FOLDER_ID: {settings.GDRIVE_ROOT_FOLDER_ID}")
    print(f"📁 USE_GDRIVE_STORAGE: {settings.USE_GDRIVE_STORAGE}")
    print()
    
    if not settings.GDRIVE_ROOT_FOLDER_ID:
        print("❌ GDRIVE_ROOT_FOLDER_ID не настроен!")
        return
    
    # 2. Создаём тестового учителя с уникальным email
    unique_id = uuid.uuid4().hex[:8]
    test_email = f'test_storage_{unique_id}@test.local'
    
    print("👤 Создаю тестового учителя...")
    teacher = CustomUser.objects.create_user(
        email=test_email,
        password='testpass123',
        first_name='Иван',
        last_name='Тестов',
        role='teacher',
    )
    print(f"   ✅ Учитель создан: {teacher.email} (ID: {teacher.id})")
    
    try:
        # 3. Создаём подписку (эмуляция оплаты)
        print()
        print("💳 Эмулирую оплату подписки...")
        subscription = Subscription.objects.create(
            user=teacher,
            plan=Subscription.PLAN_MONTHLY,
            status=Subscription.STATUS_ACTIVE,
            expires_at=timezone.now() + timedelta(days=30),
            base_storage_gb=10,
            total_paid=Decimal('990.00'),
            last_payment_date=timezone.now(),
            payment_method='test',
        )
        print(f"   ✅ Подписка активирована: {subscription.get_plan_display()}")
        print(f"   📅 Действует до: {subscription.expires_at.strftime('%d.%m.%Y')}")
        print(f"   💾 Лимит хранилища: {subscription.total_storage_gb} ГБ")
        
        # 4. Создаём папку на Google Drive
        print()
        print("📂 Создаю папку на Google Drive...")
        
        from accounts.gdrive_folder_service import create_teacher_folder_on_subscription
        folder_id = create_teacher_folder_on_subscription(subscription)
        
        if folder_id:
            print(f"   ✅ Папка создана!")
            print(f"   📁 ID: {folder_id}")
            print(f"   🔗 Ссылка: https://drive.google.com/drive/folders/{folder_id}")
            
            # Проверяем структуру
            print()
            print("📂 Проверяю структуру подпапок...")
            
            from schedule.gdrive_utils import get_gdrive_manager
            gdrive = get_gdrive_manager()
            
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = gdrive.service.files().list(q=query, fields='files(id, name)').execute()
            subfolders = results.get('files', [])
            
            expected = ['Recordings', 'Homework', 'Materials', 'Students']
            for sf in subfolders:
                if sf['name'] in expected:
                    print(f"   ✅ {sf['name']}")
                    expected.remove(sf['name'])
            
            for missing in expected:
                print(f"   ❌ {missing} - НЕ НАЙДЕНА")
            
            # Проверяем, что папка в правильном месте
            print()
            print("📍 Проверяю расположение папки...")
            folder_info = gdrive.service.files().get(
                fileId=folder_id,
                fields='id, name, parents'
            ).execute()
            
            parents = folder_info.get('parents', [])
            if parents and parents[0] == settings.GDRIVE_ROOT_FOLDER_ID:
                print(f"   ✅ Папка находится в lectio.space (GDRIVE_ROOT_FOLDER_ID)")
            else:
                print(f"   ❌ Папка НЕ в правильной директории!")
                print(f"      Ожидали parent: {settings.GDRIVE_ROOT_FOLDER_ID}")
                print(f"      Получили: {parents}")
        else:
            print("   ❌ Папка не создана")
        
        # 5. Проверяем подсчёт хранилища
        print()
        print("📊 Проверяю подсчёт хранилища...")
        
        from accounts.gdrive_folder_service import get_teacher_storage_usage
        usage = get_teacher_storage_usage(subscription)
        
        print(f"   Использовано: {usage['used_gb']} ГБ из {usage['limit_gb']} ГБ")
        print(f"   Доступно: {usage['available_gb']} ГБ")
        print(f"   Файлов: {usage['file_count']}")
        
    finally:
        # 6. Очистка
        print()
        print("🧹 Очистка тестовых данных...")
        
        folder_to_delete = subscription.gdrive_folder_id if subscription else None
        
        if hasattr(teacher, 'subscription'):
            teacher.subscription.delete()
            print("   ✅ Подписка удалена")
        
        teacher.delete()
        print("   ✅ Учитель удалён")
        
        # Удаляем папку с Drive
        if folder_to_delete:
            try:
                from schedule.gdrive_utils import get_gdrive_manager
                gdrive = get_gdrive_manager()
                gdrive.service.files().delete(fileId=folder_to_delete).execute()
                print("   ✅ Папка на Google Drive удалена")
            except Exception as e:
                print(f"   ⚠️ Не удалось удалить папку: {e}")
    
    print()
    print("=" * 60)
    print("  ТЕСТ ЗАВЕРШЁН")
    print("=" * 60)


if __name__ == '__main__':
    main()
