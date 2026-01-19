"""
Тест безопасного удаления записей с Zoom.

ПРАВИЛО: Запись удаляется с Zoom ТОЛЬКО если:
1. recording.gdrive_file_id установлен
2. recording.status == 'ready'
3. Файл реально существует на Google Drive

Этот тест проверяет все эти условия.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording, Lesson
from schedule.tasks import _delete_from_zoom
from django.contrib.auth import get_user_model
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

User = get_user_model()


def test_safety_checks():
    """Тестирует что _delete_from_zoom НЕ удаляет без проверок"""
    
    print("=" * 60)
    print("ТЕСТ: Безопасное удаление записей с Zoom")
    print("=" * 60)
    
    # Получаем учителя с Zoom credentials
    teacher = User.objects.filter(
        role='teacher',
        zoom_account_id__isnull=False
    ).exclude(zoom_account_id='').first()
    
    if not teacher:
        print("❌ Нет учителя с Zoom credentials для теста")
        return False
    
    print(f"✓ Учитель для теста: {teacher.email}")
    
    # Создаём тестовую запись БЕЗ gdrive_file_id
    test_lesson = Lesson.objects.filter(
        teacher=teacher,
        zoom_meeting_id__isnull=False
    ).first()
    
    if not test_lesson:
        print("❌ Нет урока с zoom_meeting_id для теста")
        return False
    
    print(f"✓ Урок для теста: {test_lesson.id} (zoom: {test_lesson.zoom_meeting_id})")
    
    # Тест 1: Запись без gdrive_file_id
    print("\n--- ТЕСТ 1: Запись без gdrive_file_id ---")
    
    # Создаём временную запись
    rec = LessonRecording(
        lesson=test_lesson,
        zoom_recording_id='test_safety_123',
        status='ready',
        gdrive_file_id='',  # ПУСТОЙ - не должна удаляться!
        storage_provider='zoom'
    )
    
    result = _delete_from_zoom(rec, teacher)
    
    if result:
        print("❌ ПРОВАЛ: Удаление прошло БЕЗ gdrive_file_id!")
        return False
    else:
        print("✓ PASSED: Удаление заблокировано без gdrive_file_id")
    
    # Тест 2: Запись со статусом != ready
    print("\n--- ТЕСТ 2: Запись со статусом 'processing' ---")
    
    rec.gdrive_file_id = 'fake_file_id_12345'
    rec.status = 'processing'  # НЕ ready - не должна удаляться!
    
    result = _delete_from_zoom(rec, teacher)
    
    if result:
        print("❌ ПРОВАЛ: Удаление прошло со статусом 'processing'!")
        return False
    else:
        print("✓ PASSED: Удаление заблокировано со статусом != ready")
    
    # Тест 3: Файл не существует на GDrive
    print("\n--- ТЕСТ 3: Файл не существует на GDrive ---")
    
    rec.status = 'ready'
    rec.gdrive_file_id = 'nonexistent_file_12345'  # Такого файла нет
    
    result = _delete_from_zoom(rec, teacher)
    
    if result:
        print("❌ ПРОВАЛ: Удаление прошло с несуществующим файлом на GDrive!")
        return False
    else:
        print("✓ PASSED: Удаление заблокировано - файл не найден на GDrive")
    
    print("\n" + "=" * 60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("Записи НЕ будут удаляться с Zoom без верификации GDrive")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    success = test_safety_checks()
    sys.exit(0 if success else 1)
