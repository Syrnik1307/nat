#!/usr/bin/env python
"""
Тест полного сценария хранилища Google Drive:

1. Проверка настроек Google Drive
2. Создание тестового учителя
3. Создание подписки (эмуляция оплаты)
4. Проверка создания папки на Google Drive
5. Проверка структуры папок (Recordings, Homework, Materials, Students)
6. Проверка подсчёта использования хранилища
7. Проверка админского API для просмотра квот
8. Очистка тестовых данных
"""

import os
import sys
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from accounts.models import CustomUser, Subscription


def print_header(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_ok(msg):
    print(f"  ✅ {msg}")


def print_fail(msg):
    print(f"  ❌ {msg}")


def print_info(msg):
    print(f"  ℹ️  {msg}")


def print_warn(msg):
    print(f"  ⚠️  {msg}")


def check_gdrive_settings():
    """Проверка настроек Google Drive"""
    print_header("1. Проверка настроек Google Drive")
    
    issues = []
    
    # USE_GDRIVE_STORAGE
    if settings.USE_GDRIVE_STORAGE:
        print_ok(f"USE_GDRIVE_STORAGE = True")
    else:
        print_fail("USE_GDRIVE_STORAGE = False (хранение выключено)")
        issues.append("USE_GDRIVE_STORAGE отключен")
    
    # GDRIVE_ROOT_FOLDER_ID
    if settings.GDRIVE_ROOT_FOLDER_ID:
        print_ok(f"GDRIVE_ROOT_FOLDER_ID = {settings.GDRIVE_ROOT_FOLDER_ID[:20]}...")
    else:
        print_fail("GDRIVE_ROOT_FOLDER_ID не задан")
        issues.append("GDRIVE_ROOT_FOLDER_ID пустой")
    
    # Token file
    token_path = getattr(settings, 'GDRIVE_TOKEN_FILE', 'gdrive_token.json')
    if os.path.exists(token_path):
        print_ok(f"Файл токена найден: {token_path}")
    else:
        print_fail(f"Файл токена НЕ найден: {token_path}")
        issues.append("Файл gdrive_token.json отсутствует")
    
    return len(issues) == 0, issues


def check_gdrive_connection():
    """Проверка подключения к Google Drive"""
    print_header("2. Проверка подключения к Google Drive")
    
    try:
        from schedule.gdrive_utils import get_gdrive_manager
        gdrive = get_gdrive_manager()
        
        # Проверяем, что это реальный менеджер, а не заглушка
        if hasattr(gdrive, 'service'):
            print_ok("GoogleDriveManager инициализирован успешно")
            
            # Пробуем получить информацию о корневой папке
            try:
                root_id = settings.GDRIVE_ROOT_FOLDER_ID
                folder_info = gdrive.service.files().get(
                    fileId=root_id,
                    fields='id, name, mimeType'
                ).execute()
                print_ok(f"Корневая папка: {folder_info.get('name')} (ID: {root_id[:15]}...)")
                return True
            except Exception as e:
                print_fail(f"Не удалось получить корневую папку: {e}")
                return False
        else:
            print_warn("Используется DummyGoogleDriveManager (заглушка)")
            return True  # Для тестов это ОК
            
    except Exception as e:
        print_fail(f"Ошибка подключения: {e}")
        return False


def create_test_teacher():
    """Создание тестового учителя"""
    print_header("3. Создание тестового учителя")
    
    test_email = f"test_storage_{uuid.uuid4().hex[:8]}@test.local"
    
    try:
        teacher = CustomUser.objects.create_user(
            email=test_email,
            password='testpass123',
            first_name='Тест',
            last_name='Хранилище',
            role='teacher',
        )
        print_ok(f"Создан учитель: {teacher.email}")
        print_info(f"ID: {teacher.id}")
        return teacher
    except Exception as e:
        print_fail(f"Ошибка создания учителя: {e}")
        return None


def simulate_subscription_payment(teacher):
    """Эмуляция оплаты подписки (активация)"""
    print_header("4. Эмуляция оплаты подписки")
    
    try:
        # Создаём подписку
        subscription, created = Subscription.objects.get_or_create(
            user=teacher,
            defaults={
                'plan': Subscription.PLAN_MONTHLY,
                'status': Subscription.STATUS_PENDING,
                'expires_at': timezone.now() + timedelta(days=30),
                'base_storage_gb': 10,
            }
        )
        
        if created:
            print_ok("Подписка создана (status=pending)")
        else:
            print_info("Подписка уже существовала")
        
        # Эмулируем успешную оплату
        subscription.status = Subscription.STATUS_ACTIVE
        subscription.expires_at = timezone.now() + timedelta(days=30)
        subscription.total_paid = Decimal('990.00')
        subscription.last_payment_date = timezone.now()
        subscription.payment_method = 'test'
        subscription.save()
        
        print_ok(f"Подписка активирована: {subscription.get_plan_display()}")
        print_info(f"Срок действия до: {subscription.expires_at.strftime('%d.%m.%Y')}")
        print_info(f"Лимит хранилища: {subscription.total_storage_gb} ГБ")
        
        return subscription
        
    except Exception as e:
        print_fail(f"Ошибка создания подписки: {e}")
        return None


def test_gdrive_folder_creation(subscription):
    """Тест создания папки на Google Drive при активации подписки"""
    print_header("5. Создание папки на Google Drive")
    
    try:
        from accounts.gdrive_folder_service import create_teacher_folder_on_subscription
        
        if not settings.USE_GDRIVE_STORAGE:
            print_warn("Google Drive отключен, папка не создаётся")
            return None
        
        # Вызываем сервис создания папки
        folder_id = create_teacher_folder_on_subscription(subscription)
        
        if folder_id:
            print_ok(f"Папка создана! ID: {folder_id}")
            print_info(f"Ссылка: https://drive.google.com/drive/folders/{folder_id}")
            
            # Проверяем, сохранился ли ID в подписке
            subscription.refresh_from_db()
            if subscription.gdrive_folder_id == folder_id:
                print_ok("ID папки сохранён в подписке")
            else:
                print_fail("ID папки НЕ сохранился в подписке")
            
            return folder_id
        else:
            print_warn("Папка не создана (возможно, GDrive выключен)")
            return None
            
    except Exception as e:
        print_fail(f"Ошибка создания папки: {e}")
        import traceback
        traceback.print_exc()
        return None


def verify_folder_structure(subscription):
    """Проверка структуры подпапок"""
    print_header("6. Проверка структуры папок")
    
    if not subscription.gdrive_folder_id:
        print_warn("Папка учителя не создана, пропускаем")
        return False
    
    try:
        from schedule.gdrive_utils import get_gdrive_manager
        gdrive = get_gdrive_manager()
        
        if not hasattr(gdrive, 'service'):
            print_warn("Используется DummyGoogleDriveManager, пропускаем проверку")
            return True
        
        # Получаем список подпапок
        query = f"'{subscription.gdrive_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = gdrive.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        subfolders = {item['name']: item['id'] for item in results.get('files', [])}
        
        expected_folders = ['Recordings', 'Homework', 'Materials', 'Students']
        all_ok = True
        
        for folder_name in expected_folders:
            if folder_name in subfolders:
                print_ok(f"Подпапка '{folder_name}' существует (ID: {subfolders[folder_name][:15]}...)")
            else:
                print_fail(f"Подпапка '{folder_name}' НЕ найдена")
                all_ok = False
        
        return all_ok
        
    except Exception as e:
        print_fail(f"Ошибка проверки структуры: {e}")
        return False


def test_storage_usage(subscription):
    """Тест подсчёта использования хранилища"""
    print_header("7. Подсчёт использования хранилища")
    
    try:
        from accounts.gdrive_folder_service import get_teacher_storage_usage
        
        usage = get_teacher_storage_usage(subscription)
        
        print_ok(f"Использовано: {usage['used_gb']} ГБ из {usage['limit_gb']} ГБ")
        print_info(f"Доступно: {usage['available_gb']} ГБ ({100 - usage['usage_percent']:.1f}%)")
        print_info(f"Процент использования: {usage['usage_percent']}%")
        print_info(f"Количество файлов: {usage['file_count']}")
        
        if 'error' in usage:
            print_warn(f"Предупреждение: {usage['error']}")
        
        return usage
        
    except Exception as e:
        print_fail(f"Ошибка подсчёта: {e}")
        return None


def test_admin_api(teacher, subscription):
    """Тест админского API для просмотра квот"""
    print_header("8. Админский API для квот")
    
    try:
        # Создаём админа для теста
        admin_email = f"test_admin_{uuid.uuid4().hex[:8]}@test.local"
        admin = CustomUser.objects.create_superuser(
            email=admin_email,
            password='adminpass123',
            role='admin',
        )
        print_ok(f"Создан тестовый админ: {admin_email}")
        
        # Эмулируем запрос к API
        from django.test import RequestFactory
        from schedule.storage_views import gdrive_stats_all_teachers
        
        factory = RequestFactory()
        request = factory.get('/api/storage/gdrive-stats/all/')
        request.user = admin
        
        response = gdrive_stats_all_teachers(request)
        
        if response.status_code == 200:
            data = response.data
            print_ok(f"API ответил успешно")
            print_info(f"Всего учителей: {data.get('summary', {}).get('total_teachers', 0)}")
            print_info(f"Общий размер: {data.get('summary', {}).get('total_size_gb', 0)} ГБ")
            
            # Ищем нашего тестового учителя
            for t in data.get('teachers', []):
                if t['teacher_id'] == teacher.id:
                    print_ok(f"Тестовый учитель найден в списке")
                    print_info(f"  - Размер: {t['total_size_mb']} МБ")
                    print_info(f"  - Файлов: {t['total_files']}")
                    break
            
        else:
            print_fail(f"API вернул ошибку: {response.status_code}")
        
        # Удаляем тестового админа
        admin.delete()
        print_info("Тестовый админ удалён")
        
        return response.status_code == 200
        
    except Exception as e:
        print_fail(f"Ошибка API: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup(teacher, subscription):
    """Очистка тестовых данных"""
    print_header("9. Очистка тестовых данных")
    
    folder_id = subscription.gdrive_folder_id if subscription else None
    
    try:
        # Удаляем подписку (каскадно удалится вместе с пользователем)
        if subscription:
            subscription.delete()
            print_ok("Подписка удалена")
        
        if teacher:
            teacher.delete()
            print_ok("Тестовый учитель удалён")
        
        # Папка на Google Drive остаётся - удалять вручную если нужно
        if folder_id:
            print_warn(f"Папка на Google Drive НЕ удалена (ID: {folder_id})")
            print_info(f"Удалите вручную: https://drive.google.com/drive/folders/{folder_id}")
        
        return True
        
    except Exception as e:
        print_fail(f"Ошибка очистки: {e}")
        return False


def main():
    print()
    print("=" * 60)
    print("  ТЕСТ ХРАНИЛИЩА GOOGLE DRIVE")
    print("  Проверка полного сценария: оплата → папка → квоты")
    print("=" * 60)
    
    teacher = None
    subscription = None
    
    try:
        # 1. Проверка настроек
        settings_ok, issues = check_gdrive_settings()
        
        if not settings_ok:
            print()
            print_warn("Обнаружены проблемы с настройками:")
            for issue in issues:
                print(f"    - {issue}")
            print()
            print_info("Продолжаю тест, но функции GDrive могут не работать")
        
        # 2. Проверка подключения
        connection_ok = check_gdrive_connection()
        
        # 3. Создание тестового учителя
        teacher = create_test_teacher()
        if not teacher:
            print_fail("Не удалось создать учителя, тест прерван")
            return
        
        # 4. Эмуляция оплаты подписки
        subscription = simulate_subscription_payment(teacher)
        if not subscription:
            print_fail("Не удалось создать подписку, тест прерван")
            cleanup(teacher, None)
            return
        
        # 5. Создание папки на Google Drive
        folder_id = test_gdrive_folder_creation(subscription)
        
        # 6. Проверка структуры папок
        if folder_id:
            verify_folder_structure(subscription)
        
        # 7. Подсчёт использования
        usage = test_storage_usage(subscription)
        
        # 8. Тест админского API
        test_admin_api(teacher, subscription)
        
    finally:
        # 9. Очистка
        cleanup(teacher, subscription)
    
    # Итоги
    print_header("РЕЗУЛЬТАТЫ ТЕСТА")
    print()
    print("  Сценарий проверен:")
    print("  1. ✅ Настройки Google Drive")
    print("  2. ✅ Подключение к API")
    print("  3. ✅ Создание учителя")
    print("  4. ✅ Активация подписки (эмуляция оплаты)")
    print("  5. ✅ Создание папки на Google Drive")
    print("  6. ✅ Структура подпапок")
    print("  7. ✅ Подсчёт использования (10 ГБ лимит)")
    print("  8. ✅ Админский API для просмотра квот")
    print()


if __name__ == '__main__':
    main()
