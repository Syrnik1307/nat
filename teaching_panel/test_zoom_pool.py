"""
Тестовый скрипт для проверки Zoom Pool системы

Запуск:
    python manage.py shell < test_zoom_pool.py
    
Или в Django shell:
    exec(open('test_zoom_pool.py').read())
"""

from django.utils import timezone
from datetime import timedelta
from schedule.models import ZoomAccount, Lesson, Group
from accounts.models import CustomUser
from schedule.tasks import release_stuck_zoom_accounts
import json

print("=" * 60)
print("🧪 Тестирование Zoom Pool системы")
print("=" * 60)

# Шаг 1: Проверка Zoom аккаунтов
print("\n📊 Шаг 1: Проверка Zoom аккаунтов")
print("-" * 60)

zoom_accounts = ZoomAccount.objects.all()
print(f"Всего аккаунтов: {zoom_accounts.count()}")

if zoom_accounts.count() == 0:
    print("⚠️  Нет Zoom аккаунтов! Создаем тестовые...")
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
    print("✅ Создано 2 тестовых аккаунта")
    zoom_accounts = ZoomAccount.objects.all()

for account in zoom_accounts:
    status_icon = "🔴" if account.is_busy else "🟢"
    print(f"{status_icon} {account.name} - {'ЗАНЯТ' if account.is_busy else 'СВОБОДЕН'}")
    if account.current_lesson:
        print(f"   └─ Урок: {account.current_lesson.title} (ID: {account.current_lesson.id})")

# Шаг 2: Создание тестового урока
print("\n📝 Шаг 2: Создание тестового урока")
print("-" * 60)

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
                last_name='Teacher'
            )
        if not group:
            group = Group.objects.create(
                name='Test Group',
                teacher=teacher,
                description='Test group for Zoom Pool'
            )
    
    # Удаляем старые тестовые уроки
    Lesson.objects.filter(title__startswith='[TEST]').delete()
    
    test_lesson = Lesson.objects.create(
        title='[TEST] Zoom Pool Test Lesson',
        teacher=teacher,
        group=group,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=1),
        topics='Testing atomic Zoom account capture'
    )
    print(f"✅ Урок создан: ID={test_lesson.id}")
    print(f"   Преподаватель: {test_lesson.teacher.email}")
    print(f"   Группа: {test_lesson.group.name}")
    print(f"   Начало: {test_lesson.start_time.strftime('%Y-%m-%d %H:%M')}")
    
except Exception as e:
    print(f"❌ Ошибка создания урока: {e}")
    test_lesson = None

# Шаг 3: Тест атомарного захвата аккаунта
print("\n🔒 Шаг 3: Тест атомарного захвата (select_for_update)")
print("-" * 60)

if test_lesson:
    from django.db import transaction
    
    try:
        with transaction.atomic():
            # Ищем свободный аккаунт с блокировкой строки
            free_account = ZoomAccount.objects.select_for_update().filter(
                is_busy=False
            ).first()
            
            if free_account:
                print(f"🟢 Захвачен аккаунт: {free_account.name}")
                
                # Помечаем как занятый
                free_account.is_busy = True
                free_account.current_lesson = test_lesson
                free_account.save()
                
                # Симуляция создания Zoom встречи
                from schedule.zoom_client import my_zoom_api_client
                meeting_data = my_zoom_api_client.create_meeting(
                    topic=test_lesson.title,
                    start_time=test_lesson.start_time.isoformat(),
                    duration=60
                )
                
                # Сохраняем данные встречи
                test_lesson.zoom_meeting_id = meeting_data['id']
                test_lesson.zoom_start_url = meeting_data['start_url']
                test_lesson.zoom_join_url = meeting_data['join_url']
                test_lesson.zoom_password = meeting_data.get('password', '')
                test_lesson.zoom_account_used = free_account
                test_lesson.save()
                
                print(f"✅ Встреча создана: {meeting_data['id']}")
                print(f"   Start URL: {meeting_data['start_url'][:60]}...")
                print(f"   Join URL: {meeting_data['join_url'][:60]}...")
                
            else:
                print("⚠️  Все аккаунты заняты!")
                
    except Exception as e:
        print(f"❌ Ошибка захвата: {e}")
else:
    print("⏭️  Пропуск - нет тестового урока")

# Шаг 4: Проверка состояния после захвата
print("\n📊 Шаг 4: Состояние аккаунтов после захвата")
print("-" * 60)

for account in ZoomAccount.objects.all():
    status_icon = "🔴" if account.is_busy else "🟢"
    print(f"{status_icon} {account.name} - {'ЗАНЯТ' if account.is_busy else 'СВОБОДЕН'}")
    if account.current_lesson:
        print(f"   └─ Урок #{account.current_lesson.id}: {account.current_lesson.title}")

# Шаг 5: Тест webhook (освобождение аккаунта)
print("\n🔗 Шаг 5: Тест Webhook (освобождение аккаунта)")
print("-" * 60)

if test_lesson and test_lesson.zoom_meeting_id:
    try:
        # Симуляция webhook payload от Zoom
        webhook_payload = {
            'event': 'meeting.ended',
            'payload': {
                'object': {
                    'id': test_lesson.zoom_meeting_id
                }
            }
        }
        
        print(f"📨 Симуляция webhook для meeting_id: {test_lesson.zoom_meeting_id}")
        
        # Обработка webhook вручную (не через HTTP)
        meeting_id = webhook_payload['payload']['object']['id']
        lesson = Lesson.objects.select_related('zoom_account_used').get(
            zoom_meeting_id=meeting_id
        )
        
        zoom_account = lesson.zoom_account_used
        if zoom_account and zoom_account.is_busy:
            zoom_account.is_busy = False
            zoom_account.current_lesson = None
            zoom_account.save()
            print(f"✅ Аккаунт {zoom_account.name} освобожден через webhook")
        else:
            print("⚠️  Аккаунт уже был свободен")
            
    except Exception as e:
        print(f"❌ Ошибка webhook: {e}")
else:
    print("⏭️  Пропуск - нет meeting_id для теста")

# Шаг 6: Тест Celery задачи (зависшие аккаунты)
print("\n⏰ Шаг 6: Тест Celery задачи (освобождение зависших)")
print("-" * 60)

# Создаем "зависший" урок (закончился 20 минут назад)
if test_lesson:
    test_lesson.end_time = timezone.now() - timedelta(minutes=20)
    test_lesson.save()
    
    # Помечаем аккаунт как занятый
    account = ZoomAccount.objects.first()
    account.is_busy = True
    account.current_lesson = test_lesson
    account.save()
    
    print(f"🕐 Создан зависший урок (закончился 20 мин назад)")
    print(f"   Аккаунт {account.name} помечен как занятый")

try:
    # Запускаем задачу вручную (без Celery)
    print("\n🚀 Запуск release_stuck_zoom_accounts()...")
    result = release_stuck_zoom_accounts()
    
    print(f"\n📊 Результат:")
    print(f"   Освобождено зависших: {result['released_stuck']}")
    print(f"   Освобождено осиротевших: {result['released_orphaned']}")
    print(f"   Всего: {result['total']}")
    
    if result['total'] > 0:
        print("✅ Задача успешно освободила аккаунты")
    else:
        print("⚠️  Задача не нашла зависших аккаунтов")
        
except Exception as e:
    print(f"❌ Ошибка Celery задачи: {e}")

# Итоговое состояние
print("\n" + "=" * 60)
print("📊 Итоговое состояние системы")
print("=" * 60)

total_accounts = ZoomAccount.objects.count()
busy_accounts = ZoomAccount.objects.filter(is_busy=True).count()
free_accounts = total_accounts - busy_accounts

print(f"\n📈 Статистика:")
print(f"   Всего аккаунтов: {total_accounts}")
print(f"   Занято: {busy_accounts}")
print(f"   Свободно: {free_accounts}")

print(f"\n📝 Уроков всего: {Lesson.objects.count()}")
print(f"   С Zoom встречей: {Lesson.objects.exclude(zoom_meeting_id__isnull=True).exclude(zoom_meeting_id='').count()}")

print("\n" + "=" * 60)
print("✅ Тестирование завершено!")
print("=" * 60)

print("\n📚 Полезные команды для тестирования:")
print("""
# Проверить состояние аккаунтов через API:
curl http://127.0.0.1:8000/schedule/api/zoom-accounts/

# Получить сводку:
curl http://127.0.0.1:8000/schedule/api/zoom-accounts/status_summary/

# Запустить урок через API:
curl -X POST http://127.0.0.1:8000/schedule/lesson/1/start/ \\
     -H "Content-Type: application/json" \\
     -d '{"lesson_id": 1}'

# Симуляция webhook:
curl -X POST http://127.0.0.1:8000/schedule/webhook/zoom/ \\
     -H "Content-Type: application/json" \\
     -d '{"event": "meeting.ended", "payload": {"object": {"id": "12345678901"}}}'
""")
