"""
Комплексный тест жизненного цикла Zoom аккаунтов
Проверяет: занятие → использование → автоматическое освобождение
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from zoom_pool.models import ZoomAccount
from schedule.models import Lesson, Group
from accounts.models import CustomUser
from schedule.tasks import release_finished_zoom_accounts


def test_zoom_account_lifecycle():
    """Тест полного цикла: занятие → использование → освобождение"""
    
    print("\n" + "="*70)
    print("🧪 ТЕСТ: Полный жизненный цикл Zoom аккаунта")
    print("="*70 + "\n")
    
    # 1. Подготовка: создаём тестовые данные
    print("📦 Шаг 1: Подготовка тестовых данных...")
    
    # Очищаем старые тестовые данные
    ZoomAccount.objects.filter(email='lifecycle_zoom@test.com').delete()
    Lesson.objects.filter(title__contains='(тест)').delete()
    Group.objects.filter(name='Lifecycle Test Group').delete()
    CustomUser.objects.filter(email='lifecycle_teacher@test.com').delete()
    
    # Создаём тестового учителя
    teacher = CustomUser.objects.create(
        email='lifecycle_teacher@test.com',
        first_name='Lifecycle',
        last_name='Teacher',
        role='teacher'
    )
    teacher.set_password('Test123!')
    teacher.save()
    print(f"   ✓ Создан учитель: {teacher.email}")
    
    # Создаём группу
    group = Group.objects.create(
        name='Lifecycle Test Group',
        teacher=teacher
    )
    print(f"   ✓ Создана группа: {group.name}")
    
    # Создаём Zoom аккаунт
    zoom_account = ZoomAccount.objects.create(
        email='lifecycle_zoom@test.com',
        api_key='test_key_lifecycle',
        api_secret='test_secret_lifecycle',
        max_concurrent_meetings=2,
        current_meetings=0,
        is_active=True
    )
    print(f"   ✓ Создан Zoom аккаунт: {zoom_account.email}")
    
    # 2. Создаём урок который уже закончился (для теста освобождения)
    print("\n📅 Шаг 2: Создание завершённого урока...")
    
    past_lesson = Lesson.objects.create(
        group=group,
        teacher=teacher,
        title='Завершённый урок (тест)',
        start_time=timezone.now() - timedelta(hours=2),
        end_time=timezone.now() - timedelta(minutes=10),  # закончился 10 минут назад (> grace period 5 min)
        zoom_account=zoom_account,
        zoom_meeting_id='test_meeting_past_123',
        zoom_join_url='https://zoom.us/j/test123',
        zoom_start_url='https://zoom.us/s/test123'
    )
    
    # Занимаем аккаунт вручную (эмулируем, что урок был запущен)
    zoom_account.acquire()
    print(f"   ✓ Создан завершённый урок: {past_lesson.title}")
    print(f"   ✓ Время окончания: {past_lesson.end_time}")
    print(f"   ✓ Zoom аккаунт занят: {zoom_account.current_meetings}/{zoom_account.max_concurrent_meetings}")
    
    # 3. Создаём текущий урок (который ещё идёт)
    print("\n🎓 Шаг 3: Создание текущего урока...")
    
    current_lesson = Lesson.objects.create(
        group=group,
        teacher=teacher,
        title='Текущий урок (тест)',
        start_time=timezone.now() - timedelta(minutes=30),
        end_time=timezone.now() + timedelta(minutes=30),
        zoom_account=zoom_account,
        zoom_meeting_id='test_meeting_current_456',
        zoom_join_url='https://zoom.us/j/test456',
        zoom_start_url='https://zoom.us/s/test456'
    )
    
    zoom_account.acquire()
    print(f"   ✓ Создан текущий урок: {current_lesson.title}")
    print(f"   ✓ Время окончания: {current_lesson.end_time}")
    print(f"   ✓ Zoom аккаунт занят: {zoom_account.current_meetings}/{zoom_account.max_concurrent_meetings}")
    
    # 4. Проверяем, что аккаунт полностью занят
    print("\n🔒 Шаг 4: Проверка занятости аккаунта...")
    
    zoom_account.refresh_from_db()
    assert zoom_account.current_meetings == 2, f"Ожидалось 2 встречи, получено {zoom_account.current_meetings}"
    assert not zoom_account.is_available(), "Аккаунт должен быть недоступен"
    print(f"   ✓ Аккаунт полностью занят: {zoom_account.current_meetings}/{zoom_account.max_concurrent_meetings}")
    print(f"   ✓ is_available() = {zoom_account.is_available()}")
    
    # 5. Запускаем задачу освобождения завершённых аккаунтов
    print("\n🤖 Шаг 5: Запуск Celery задачи освобождения...")
    
    result = release_finished_zoom_accounts()
    print(f"   ✓ Задача выполнена: {result}")
    
    # 6. Проверяем результаты
    print("\n✅ Шаг 6: Проверка результатов...")
    
    zoom_account.refresh_from_db()
    past_lesson.refresh_from_db()
    current_lesson.refresh_from_db()
    
    print(f"\n   Результаты по урокам:")
    print(f"   - Завершённый урок: zoom_account = {past_lesson.zoom_account}")
    print(f"   - Текущий урок: zoom_account = {current_lesson.zoom_account}")
    
    print(f"\n   Результаты по Zoom аккаунту:")
    print(f"   - current_meetings: {zoom_account.current_meetings}/{zoom_account.max_concurrent_meetings}")
    print(f"   - is_available(): {zoom_account.is_available()}")
    
    # Проверки
    assert past_lesson.zoom_account is None, "Завершённый урок должен был освободить аккаунт"
    assert current_lesson.zoom_account is not None, "Текущий урок не должен был освободить аккаунт"
    assert zoom_account.current_meetings == 1, f"Должна остаться 1 встреча, осталось {zoom_account.current_meetings}"
    assert zoom_account.is_available(), "Аккаунт должен стать доступным после освобождения"
    
    print(f"\n   ✅ Завершённый урок освободил аккаунт")
    print(f"   ✅ Текущий урок сохранил привязку к аккаунту")
    print(f"   ✅ Счётчик встреч корректно уменьшен: {zoom_account.current_meetings}")
    print(f"   ✅ Аккаунт снова доступен для новых встреч")
    
    # 7. Проверяем освобождение после окончания текущего урока
    print("\n⏰ Шаг 7: Эмуляция окончания текущего урока...")
    
    # Переносим время окончания в прошлое
    current_lesson.end_time = timezone.now() - timedelta(minutes=5)
    current_lesson.save()
    print(f"   ✓ Урок завершён: {current_lesson.end_time}")
    
    # Снова запускаем задачу
    result = release_finished_zoom_accounts()
    print(f"   ✓ Задача выполнена повторно: {result}")
    
    # Проверяем
    zoom_account.refresh_from_db()
    current_lesson.refresh_from_db()
    
    assert current_lesson.zoom_account is None, "Текущий урок должен был освободить аккаунт"
    assert zoom_account.current_meetings == 0, f"Все встречи должны быть освобождены, осталось {zoom_account.current_meetings}"
    assert zoom_account.is_available(), "Аккаунт должен быть полностью свободен"
    
    print(f"\n   ✅ Все уроки освободили аккаунты")
    print(f"   ✅ Счётчик встреч: {zoom_account.current_meetings}/{zoom_account.max_concurrent_meetings}")
    print(f"   ✅ Аккаунт полностью свободен и готов к использованию")
    
    # 8. Очистка
    print("\n🧹 Шаг 8: Очистка тестовых данных...")
    
    past_lesson.delete()
    current_lesson.delete()
    zoom_account.delete()
    group.delete()
    teacher.delete()
    
    print("   ✓ Тестовые данные удалены")
    
    # Итоговый результат
    print("\n" + "="*70)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("="*70)
    print("\nПроверено:")
    print("  ✓ Занятие Zoom аккаунта")
    print("  ✓ Автоматическое освобождение завершённых уроков")
    print("  ✓ Сохранение активных уроков")
    print("  ✓ Корректность счётчика current_meetings")
    print("  ✓ Логика доступности is_available()")
    print("  ✓ Полное освобождение всех встреч")
    print("\n")


if __name__ == '__main__':
    try:
        test_zoom_account_lifecycle()
    except AssertionError as e:
        print(f"\n❌ ОШИБКА ТЕСТА: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ НЕПРЕДВИДЕННАЯ ОШИБКА: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
