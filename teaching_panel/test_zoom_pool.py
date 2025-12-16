"""Тестовый скрипт для проверки Zoom Pool системы (ручной запуск).

Важно: этот файл НЕ должен выполнять код при импорте,
иначе `manage.py test` будет трогать реальную dev-БД.
"""


def main():
    import os

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
    try:
        import django

        django.setup()
    except Exception:
        # Если запускается из manage.py shell, django уже может быть инициализирован
        pass

    from django.utils import timezone
    from datetime import timedelta

    from schedule.models import Lesson, Group
    from zoom_pool.models import ZoomAccount
    from accounts.models import CustomUser
    from schedule.tasks import release_stuck_zoom_accounts

    print("=" * 60)
    print("🧪 Тестирование Zoom Pool системы")
    print("=" * 60)

    print("\n📊 Шаг 1: Проверка Zoom аккаунтов")
    print("-" * 60)

    zoom_accounts = ZoomAccount.objects.all()
    print(f"Всего аккаунтов: {zoom_accounts.count()}")

    if zoom_accounts.count() == 0:
        print("⚠️  Нет Zoom аккаунтов! Создаем тестовые...")
        ZoomAccount.objects.create(
            email="test_zoom_1@example.com",
            api_key="fake_api_key_1",
            api_secret="fake_secret_1",
            zoom_user_id="test_user_1",
        )
        ZoomAccount.objects.create(
            email="test_zoom_2@example.com",
            api_key="fake_api_key_2",
            api_secret="fake_secret_2",
            zoom_user_id="test_user_2",
        )
        print("✅ Создано 2 тестовых аккаунта")
        zoom_accounts = ZoomAccount.objects.all()

    for account in zoom_accounts:
        status_icon = "🔴" if getattr(account, 'in_use', False) else "🟢"
        print(f"{status_icon} {account.email} - {'ЗАНЯТ' if getattr(account, 'in_use', False) else 'СВОБОДЕН'}")

    print("\n📝 Шаг 2: Создание тестового урока")
    print("-" * 60)

    test_lesson = None
    try:
        teacher = CustomUser.objects.filter(role='teacher').first()
        group = Group.objects.first()

        if not teacher or not group:
            print("⚠️  Нет преподавателя или группы. Создаем...")
            if not teacher:
                teacher = CustomUser.objects.create_user(
                    email='testteacher@example.com',
                    password='test123',
                    role='teacher',
                    first_name='Test',
                    last_name='Teacher',
                )
            if not group:
                group = Group.objects.create(
                    name='Test Group',
                    teacher=teacher,
                    description='Test group for Zoom Pool',
                )

        Lesson.objects.filter(title__startswith='[TEST]').delete()

        test_lesson = Lesson.objects.create(
            title='[TEST] Zoom Pool Test Lesson',
            teacher=teacher,
            group=group,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            topics='Testing atomic Zoom account capture',
        )
        print(f"✅ Урок создан: ID={test_lesson.id}")
    except Exception as e:
        print(f"❌ Ошибка создания урока: {e}")

    print("\n⏰ Шаг 3: Тест Celery задачи (release_stuck_zoom_accounts)")
    print("-" * 60)
    try:
        print("\n🚀 Запуск release_stuck_zoom_accounts()...")
        result = release_stuck_zoom_accounts()
        print(f"Результат: {result}")
    except Exception as e:
        print(f"❌ Ошибка задачи: {e}")

    print("\n" + "=" * 60)
    print("✅ Скрипт завершён")
    print("=" * 60)


if __name__ == '__main__':
    main()
