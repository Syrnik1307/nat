#!/usr/bin/env python
"""
==========================================================================
КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ GOOGLE DRIVE STORAGE
==========================================================================

Проверяет ВСЕ функции работы с Google Drive:
1. Подключение и авторизация
2. Работа с папками (создание, поиск)
3. Загрузка файлов
4. Скачивание и стриминг
5. Удаление файлов
6. Квоты и статистика
7. Проверка существования файлов (file_exists)
8. Кэширование структуры папок

Запуск:
  cd teaching_panel
  python test_gdrive_comprehensive.py
"""

import os
import sys
import io
import time
import tempfile
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.conf import settings
from django.core.cache import cache

# Цвета для терминала
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def ok(msg):
    print(f"  {Colors.GREEN}[OK]{Colors.END} {msg}")

def fail(msg):
    print(f"  {Colors.RED}[FAIL]{Colors.END} {msg}")

def warn(msg):
    print(f"  {Colors.YELLOW}[WARN]{Colors.END} {msg}")

def info(msg):
    print(f"  {Colors.BLUE}[INFO]{Colors.END} {msg}")

def header(msg):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}  {msg}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")

def section(msg):
    print(f"\n{Colors.BLUE}--- {msg} ---{Colors.END}")

# Счётчики результатов
results = {
    'passed': 0,
    'failed': 0,
    'warnings': 0
}

def test_pass(msg):
    results['passed'] += 1
    ok(msg)

def test_fail(msg):
    results['failed'] += 1
    fail(msg)

def test_warn(msg):
    results['warnings'] += 1
    warn(msg)


# ==============================================================================
# ТЕСТ 1: Проверка конфигурации
# ==============================================================================
def test_configuration():
    header("1. КОНФИГУРАЦИЯ GOOGLE DRIVE")
    
    # Проверяем USE_GDRIVE_STORAGE
    gdrive_enabled = getattr(settings, 'USE_GDRIVE_STORAGE', False)
    if gdrive_enabled:
        test_pass(f"USE_GDRIVE_STORAGE = True (включено)")
    else:
        test_warn(f"USE_GDRIVE_STORAGE = False (выключено)")
    
    # Проверяем токен файл
    token_path = getattr(settings, 'GDRIVE_TOKEN_FILE', 'gdrive_token.json')
    if os.path.exists(token_path):
        test_pass(f"Token файл найден: {token_path}")
        # Проверяем валидность JSON
        try:
            import json
            with open(token_path) as f:
                token_data = json.load(f)
            if 'refresh_token' in token_data:
                test_pass(f"Token содержит refresh_token")
            else:
                test_warn("Token без refresh_token - могут быть проблемы с обновлением")
        except json.JSONDecodeError as e:
            test_fail(f"Token файл повреждён: {e}")
    else:
        test_fail(f"Token файл НЕ найден: {token_path}")
    
    # Проверяем ROOT_FOLDER_ID
    root_id = getattr(settings, 'GDRIVE_ROOT_FOLDER_ID', '')
    if root_id:
        test_pass(f"GDRIVE_ROOT_FOLDER_ID = {root_id[:20]}...")
    else:
        test_fail("GDRIVE_ROOT_FOLDER_ID не установлен!")
    
    return gdrive_enabled


# ==============================================================================
# ТЕСТ 2: Инициализация менеджера
# ==============================================================================
def test_manager_init():
    header("2. ИНИЦИАЛИЗАЦИЯ GOOGLE DRIVE MANAGER")
    
    try:
        from schedule.gdrive_utils import get_gdrive_manager, GoogleDriveManager, DummyGoogleDriveManager
        
        gdrive = get_gdrive_manager()
        
        if isinstance(gdrive, GoogleDriveManager):
            test_pass("Инициализирован РЕАЛЬНЫЙ GoogleDriveManager")
        elif isinstance(gdrive, DummyGoogleDriveManager):
            test_warn("Инициализирован DUMMY менеджер (тестовый режим)")
        else:
            test_warn(f"Неизвестный тип менеджера: {type(gdrive)}")
        
        # Проверяем service
        if hasattr(gdrive, 'service') and gdrive.service:
            test_pass("Google Drive API service создан")
        elif hasattr(gdrive, 'service'):
            test_warn("Service = None (dummy режим)")
        
        # Проверяем root_folder_id
        if hasattr(gdrive, 'root_folder_id'):
            if gdrive.root_folder_id:
                test_pass(f"root_folder_id = {gdrive.root_folder_id[:20]}...")
            else:
                test_warn("root_folder_id пустой")
        
        return gdrive
        
    except Exception as e:
        test_fail(f"Ошибка инициализации: {e}")
        return None


# ==============================================================================
# ТЕСТ 3: Проверка доступа к корневой папке
# ==============================================================================
def test_root_folder_access(gdrive):
    header("3. ДОСТУП К КОРНЕВОЙ ПАПКЕ")
    
    if not gdrive or not hasattr(gdrive, 'service') or not gdrive.service:
        test_warn("Пропуск теста - dummy режим")
        return True
    
    root_id = getattr(settings, 'GDRIVE_ROOT_FOLDER_ID', '')
    if not root_id:
        test_fail("GDRIVE_ROOT_FOLDER_ID не установлен")
        return False
    
    try:
        folder_info = gdrive.service.files().get(
            fileId=root_id,
            fields='id, name, mimeType, trashed'
        ).execute()
        
        if folder_info.get('trashed'):
            test_fail(f"Корневая папка в корзине!")
            return False
        
        test_pass(f"Папка доступна: {folder_info.get('name')}")
        info(f"ID: {folder_info.get('id')}")
        info(f"Type: {folder_info.get('mimeType')}")
        
        return True
        
    except Exception as e:
        test_fail(f"Ошибка доступа к корневой папке: {e}")
        return False


# ==============================================================================
# ТЕСТ 4: Создание тестовой папки
# ==============================================================================
def test_create_folder(gdrive):
    header("4. СОЗДАНИЕ ПАПОК")
    
    if not gdrive or not hasattr(gdrive, 'service') or not gdrive.service:
        test_warn("Пропуск - dummy режим")
        return None
    
    root_id = getattr(settings, 'GDRIVE_ROOT_FOLDER_ID', '')
    test_folder_name = f"_TEST_FOLDER_{uuid.uuid4().hex[:8]}"
    
    try:
        folder_id = gdrive.create_folder(test_folder_name, root_id)
        if folder_id:
            test_pass(f"Папка создана: {test_folder_name}")
            info(f"ID: {folder_id}")
            return folder_id
        else:
            test_fail("create_folder вернул None")
            return None
            
    except Exception as e:
        test_fail(f"Ошибка создания папки: {e}")
        return None


# ==============================================================================
# ТЕСТ 5: Загрузка файла
# ==============================================================================
def test_upload_file(gdrive, folder_id):
    header("5. ЗАГРУЗКА ФАЙЛА")
    
    if not gdrive or not hasattr(gdrive, 'service') or not gdrive.service:
        test_warn("Пропуск - dummy режим")
        return None
    
    if not folder_id:
        test_warn("Пропуск - нет тестовой папки")
        return None
    
    # Создаём тестовый файл
    test_content = b"Test file content for Google Drive upload test\n" * 100
    test_file_name = f"_test_file_{uuid.uuid4().hex[:8]}.txt"
    
    try:
        # Загружаем через file object (как в homework upload)
        file_obj = io.BytesIO(test_content)
        
        result = gdrive.upload_file(
            file_path_or_object=file_obj,
            file_name=test_file_name,
            folder_id=folder_id,
            mime_type='text/plain'
        )
        
        if result and result.get('file_id'):
            test_pass(f"Файл загружен: {test_file_name}")
            info(f"File ID: {result['file_id']}")
            info(f"Size: {result.get('size', 'unknown')} bytes")
            info(f"Web link: {result.get('web_view_link', 'N/A')}")
            return result['file_id']
        else:
            test_fail("upload_file не вернул file_id")
            return None
            
    except Exception as e:
        test_fail(f"Ошибка загрузки: {e}")
        import traceback
        traceback.print_exc()
        return None


# ==============================================================================
# ТЕСТ 6: Проверка существования файла (file_exists)
# ==============================================================================
def test_file_exists(gdrive, file_id):
    header("6. ПРОВЕРКА СУЩЕСТВОВАНИЯ ФАЙЛА (file_exists)")
    
    if not gdrive:
        test_warn("Пропуск - менеджер не инициализирован")
        return
    
    # Тест 1: Реальный файл
    if file_id:
        try:
            exists = gdrive.file_exists(file_id)
            if exists:
                test_pass(f"file_exists({file_id[:20]}...) = True (корректно)")
            else:
                test_fail(f"file_exists вернул False для существующего файла!")
        except Exception as e:
            test_fail(f"Ошибка file_exists: {e}")
    
    # Тест 2: Несуществующий файл
    try:
        fake_id = "nonexistent_file_12345xyz"
        exists = gdrive.file_exists(fake_id)
        if not exists:
            test_pass(f"file_exists(fake_id) = False (корректно)")
        else:
            test_fail("file_exists вернул True для несуществующего файла!")
    except Exception as e:
        test_fail(f"Ошибка file_exists для fake: {e}")
    
    # Тест 3: Пустой ID
    try:
        exists = gdrive.file_exists('')
        if not exists:
            test_pass("file_exists('') = False (корректно)")
        else:
            test_fail("file_exists('') вернул True!")
    except Exception as e:
        test_fail(f"Ошибка file_exists для пустой строки: {e}")
    
    # Тест 4: None
    try:
        exists = gdrive.file_exists(None)
        if not exists:
            test_pass("file_exists(None) = False (корректно)")
        else:
            test_fail("file_exists(None) вернул True!")
    except Exception as e:
        test_fail(f"Ошибка file_exists для None: {e}")


# ==============================================================================
# ТЕСТ 7: Получение ссылок
# ==============================================================================
def test_links(gdrive, file_id):
    header("7. ГЕНЕРАЦИЯ ССЫЛОК")
    
    if not gdrive:
        test_warn("Пропуск - менеджер не инициализирован")
        return
    
    test_file_id = file_id or "example_file_id"
    
    # Embed link
    try:
        embed_link = gdrive.get_embed_link(test_file_id)
        if embed_link and 'drive.google.com' in embed_link:
            test_pass(f"get_embed_link() = {embed_link}")
        else:
            test_fail(f"Некорректный embed_link: {embed_link}")
    except Exception as e:
        test_fail(f"Ошибка get_embed_link: {e}")
    
    # Direct download link
    try:
        download_link = gdrive.get_direct_download_link(test_file_id)
        if download_link and 'drive.google.com' in download_link:
            test_pass(f"get_direct_download_link() = {download_link}")
        else:
            test_fail(f"Некорректный download_link: {download_link}")
    except Exception as e:
        test_fail(f"Ошибка get_direct_download_link: {e}")
    
    # Streaming link
    try:
        stream_link = gdrive.get_streaming_link(test_file_id)
        if stream_link and 'drive.google.com' in stream_link:
            test_pass(f"get_streaming_link() = {stream_link}")
        else:
            test_fail(f"Некорректный streaming_link: {stream_link}")
    except Exception as e:
        test_fail(f"Ошибка get_streaming_link: {e}")


# ==============================================================================
# ТЕСТ 8: Квота диска
# ==============================================================================
def test_drive_quota(gdrive):
    header("8. КВОТА GOOGLE DRIVE")
    
    if not gdrive or not hasattr(gdrive, 'service') or not gdrive.service:
        test_warn("Пропуск - dummy режим")
        return
    
    try:
        quota = gdrive.get_drive_quota()
        
        if quota.get('error'):
            test_fail(f"Ошибка получения квоты: {quota['error']}")
            return
        
        test_pass("get_drive_quota() успешно")
        info(f"Лимит: {quota.get('limit_gb', 0)} GB")
        info(f"Использовано: {quota.get('usage_gb', 0)} GB")
        info(f"Свободно: {quota.get('free_gb', 0)} GB")
        info(f"Использование: {quota.get('usage_percent', 0)}%")
        
        if quota.get('usage_percent', 0) > 90:
            test_warn("ВНИМАНИЕ: Использовано более 90% квоты!")
        
    except Exception as e:
        test_fail(f"Ошибка get_drive_quota: {e}")


# ==============================================================================
# ТЕСТ 9: Структура папок учителя
# ==============================================================================
def test_teacher_folder_structure(gdrive):
    header("9. СТРУКТУРА ПАПОК УЧИТЕЛЯ")
    
    if not gdrive or not hasattr(gdrive, 'service') or not gdrive.service:
        test_warn("Пропуск - dummy режим")
        return
    
    try:
        from accounts.models import CustomUser
        
        # Получаем любого учителя для теста
        teacher = CustomUser.objects.filter(role='teacher').first()
        
        if not teacher:
            test_warn("Нет учителей в БД для тестирования")
            return
        
        info(f"Тестируем на учителе: {teacher.email}")
        
        # Очищаем кэш для чистого теста
        cache_key = f"gdrive_folders_teacher_{teacher.id}"
        cache.delete(cache_key)
        
        start_time = time.time()
        folders = gdrive.get_or_create_teacher_folder(teacher)
        elapsed = time.time() - start_time
        
        if folders:
            test_pass(f"get_or_create_teacher_folder() за {elapsed:.2f}s")
            
            expected_keys = ['root', 'recordings', 'homework', 'materials', 'students']
            for key in expected_keys:
                if key in folders and folders[key]:
                    info(f"  {key}: {folders[key][:20]}...")
                else:
                    test_fail(f"Отсутствует папка: {key}")
        else:
            test_fail("get_or_create_teacher_folder вернул None")
        
        # Тест кэширования
        start_time = time.time()
        folders_cached = gdrive.get_or_create_teacher_folder(teacher)
        elapsed_cached = time.time() - start_time
        
        if elapsed_cached < 0.1:
            test_pass(f"Кэширование работает ({elapsed_cached:.4f}s)")
        else:
            test_warn(f"Кэш медленный ({elapsed_cached:.2f}s)")
            
    except Exception as e:
        test_fail(f"Ошибка get_or_create_teacher_folder: {e}")
        import traceback
        traceback.print_exc()


# ==============================================================================
# ТЕСТ 10: Удаление файла
# ==============================================================================
def test_delete_file(gdrive, file_id):
    header("10. УДАЛЕНИЕ ФАЙЛА")
    
    if not gdrive or not hasattr(gdrive, 'service') or not gdrive.service:
        test_warn("Пропуск - dummy режим")
        return
    
    if not file_id:
        test_warn("Пропуск - нет тестового файла для удаления")
        return
    
    try:
        gdrive.delete_file(file_id)
        test_pass(f"delete_file({file_id[:20]}...) успешно")
        
        # Проверяем что файл действительно удалён
        exists = gdrive.file_exists(file_id)
        if not exists:
            test_pass("Файл успешно удалён (file_exists = False)")
        else:
            test_fail("Файл всё ещё существует после delete_file!")
            
    except Exception as e:
        test_fail(f"Ошибка delete_file: {e}")


# ==============================================================================
# ТЕСТ 11: Удаление тестовой папки
# ==============================================================================
def test_delete_folder(gdrive, folder_id):
    header("11. ОЧИСТКА (удаление тестовой папки)")
    
    if not gdrive or not hasattr(gdrive, 'service') or not gdrive.service:
        test_warn("Пропуск - dummy режим")
        return
    
    if not folder_id:
        test_warn("Пропуск - нет тестовой папки для удаления")
        return
    
    try:
        gdrive.service.files().delete(fileId=folder_id).execute()
        test_pass(f"Тестовая папка удалена")
    except Exception as e:
        test_warn(f"Не удалось удалить тестовую папку: {e}")


# ==============================================================================
# ТЕСТ 12: Проверка API стриминга записей
# ==============================================================================
def test_recording_stream_api():
    header("12. API СТРИМИНГА ЗАПИСЕЙ")
    
    try:
        from schedule.models import LessonRecording
        
        # Проверяем наличие записей с gdrive_file_id
        recordings_count = LessonRecording.objects.exclude(
            gdrive_file_id__isnull=True
        ).exclude(gdrive_file_id='').count()
        
        if recordings_count > 0:
            test_pass(f"Записи с gdrive_file_id: {recordings_count}")
            
            # Выборочная проверка
            sample = LessonRecording.objects.exclude(
                gdrive_file_id__isnull=True
            ).exclude(gdrive_file_id='').first()
            
            info(f"Пример: ID={sample.id}, file_id={sample.gdrive_file_id[:20] if sample.gdrive_file_id else 'N/A'}...")
            info(f"  storage_provider: {sample.storage_provider}")
            info(f"  play_url: {sample.play_url[:50] if sample.play_url else 'N/A'}...")
        else:
            test_warn("Нет записей с gdrive_file_id")
            
    except Exception as e:
        test_fail(f"Ошибка проверки записей: {e}")


# ==============================================================================
# ТЕСТ 13: Проверка Homework файлов
# ==============================================================================
def test_homework_files():
    header("13. ФАЙЛЫ ДОМАШНИХ ЗАДАНИЙ")
    
    try:
        from homework.models import Homework, StudentSubmission
        
        # Проверяем наличие GDrive ссылок в ДЗ
        homeworks = Homework.objects.all().count()
        submissions = StudentSubmission.objects.all().count()
        
        info(f"Homework: {homeworks}")
        info(f"StudentSubmission: {submissions}")
        
        # Проверяем наличие gdrive_file_id в questions
        homeworks_with_gdrive = 0
        for hw in Homework.objects.all()[:100]:
            if hw.questions:
                questions_str = str(hw.questions)
                if 'gdrive' in questions_str.lower() or 'drive.google.com' in questions_str:
                    homeworks_with_gdrive += 1
        
        if homeworks_with_gdrive > 0:
            test_pass(f"ДЗ с GDrive файлами: {homeworks_with_gdrive}")
        else:
            test_warn("ДЗ без GDrive файлов (или их мало)")
        
        test_pass(f"Homework models импортированы успешно")
            
    except Exception as e:
        test_fail(f"Ошибка проверки homework: {e}")


# ==============================================================================
# ТЕСТ 14: Проверка gdrive_folder_service
# ==============================================================================
def test_gdrive_folder_service():
    header("14. GDRIVE FOLDER SERVICE")
    
    try:
        from accounts.gdrive_folder_service import (
            get_gdrive_manager,
            create_teacher_folder_on_subscription,
            get_teacher_storage_usage,
            check_storage_limit
        )
        
        test_pass("Импорт gdrive_folder_service успешен")
        
        # Проверяем наличие функций
        info(f"create_teacher_folder_on_subscription: {callable(create_teacher_folder_on_subscription)}")
        info(f"get_teacher_storage_usage: {callable(get_teacher_storage_usage)}")
        info(f"check_storage_limit: {callable(check_storage_limit)}")
        
    except ImportError as e:
        test_fail(f"Ошибка импорта: {e}")
    except Exception as e:
        test_fail(f"Ошибка: {e}")


# ==============================================================================
# ТЕСТ 15: Проверка GoogleDriveStorage backend
# ==============================================================================
def test_gdrive_storage_backend():
    header("15. GOOGLE DRIVE STORAGE BACKEND")
    
    try:
        from schedule.gdrive_storage import GoogleDriveStorage
        
        test_pass("Импорт GoogleDriveStorage успешен")
        
        # Создаём инстанс без teacher (fallback режим)
        storage = GoogleDriveStorage(folder_type='homework')
        
        info(f"folder_type: {storage.folder_type}")
        info(f"teacher: {storage.teacher}")
        info(f"student: {storage.student}")
        
        test_pass("GoogleDriveStorage инициализирован")
        
    except ImportError as e:
        test_fail(f"Ошибка импорта: {e}")
    except Exception as e:
        test_fail(f"Ошибка: {e}")


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print("\n" + "="*60)
    print(f"{Colors.BOLD}  КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ GOOGLE DRIVE STORAGE{Colors.END}")
    print("="*60)
    print(f"Дата: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Сохраняем для очистки
    test_folder_id = None
    test_file_id = None
    
    try:
        # 1. Конфигурация
        gdrive_enabled = test_configuration()
        
        # 2. Инициализация менеджера
        gdrive = test_manager_init()
        
        # 3. Доступ к корневой папке
        if gdrive:
            test_root_folder_access(gdrive)
        
        # 4. Создание папки
        if gdrive:
            test_folder_id = test_create_folder(gdrive)
        
        # 5. Загрузка файла
        if gdrive and test_folder_id:
            test_file_id = test_upload_file(gdrive, test_folder_id)
        
        # 6. Проверка существования файла
        test_file_exists(gdrive, test_file_id)
        
        # 7. Генерация ссылок
        test_links(gdrive, test_file_id)
        
        # 8. Квота диска
        test_drive_quota(gdrive)
        
        # 9. Структура папок учителя
        test_teacher_folder_structure(gdrive)
        
        # 10. Удаление файла
        test_delete_file(gdrive, test_file_id)
        
        # 11. Удаление папки
        test_delete_folder(gdrive, test_folder_id)
        
        # 12. API стриминга
        test_recording_stream_api()
        
        # 13. Homework файлы
        test_homework_files()
        
        # 14. Folder service
        test_gdrive_folder_service()
        
        # 15. Storage backend
        test_gdrive_storage_backend()
        
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        print(f"\n{Colors.RED}КРИТИЧЕСКАЯ ОШИБКА: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
    
    # Итоги
    print("\n" + "="*60)
    print(f"{Colors.BOLD}  ИТОГИ ТЕСТИРОВАНИЯ{Colors.END}")
    print("="*60)
    print(f"  {Colors.GREEN}Пройдено:{Colors.END} {results['passed']}")
    print(f"  {Colors.RED}Провалено:{Colors.END} {results['failed']}")
    print(f"  {Colors.YELLOW}Предупреждений:{Colors.END} {results['warnings']}")
    print("="*60)
    
    if results['failed'] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ!{Colors.END}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
