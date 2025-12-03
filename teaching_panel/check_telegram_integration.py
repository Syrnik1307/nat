"""
Скрипт для проверки Telegram интеграции и диагностики проблем с уведомлениями.

Usage:
    cd teaching_panel
    python check_telegram_integration.py
"""
import os
import django
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings
from accounts.models import NotificationSettings, NotificationLog

User = get_user_model()


def check_telegram_integration():
    print("🔍 Проверка Telegram интеграции\n")
    print("="*60)
    
    # 1. Проверка токена
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token or token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ TELEGRAM_BOT_TOKEN не настроен!")
        print("   Добавьте токен в .env файл:")
        print("   TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather\n")
    else:
        print(f"✅ TELEGRAM_BOT_TOKEN настроен (длина: {len(token)} символов)\n")
    
    # 2. Проверка студентов с Telegram
    print("="*60)
    print("📱 Студенты с привязанным Telegram:\n")
    
    students = User.objects.filter(role='student', is_active=True)
    linked_students = students.exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id='')
    
    print(f"Всего активных студентов: {students.count()}")
    print(f"Студентов с Telegram: {linked_students.count()}\n")
    
    if linked_students.exists():
        for student in linked_students:
            print(f"  ✅ {student.get_full_name() or student.email}")
            print(f"     Chat ID: {student.telegram_chat_id}")
            
            # Проверка настроек уведомлений
            try:
                settings_obj = NotificationSettings.objects.get(user=student)
                print(f"     Telegram enabled: {settings_obj.telegram_enabled}")
                print(f"     New homework: {settings_obj.notify_new_homework}")
                print(f"     Graded: {settings_obj.notify_homework_graded}")
            except NotificationSettings.DoesNotExist:
                print("     ⚠️  NotificationSettings не найдены (будут созданы при первой отправке)")
            print()
    else:
        print("  ⚠️  Нет студентов с привязанным Telegram")
        print("     Студент должен:")
        print("     1. Открыть бота в Telegram")
        print("     2. Отправить /start")
        print("     3. Нажать '🔗 Привязать аккаунт'")
        print("     4. Ввести invite_code своей группы\n")
    
    # 3. Проверка учителей
    print("="*60)
    print("👨‍🏫 Учителя с привязанным Telegram:\n")
    
    teachers = User.objects.filter(role='teacher', is_active=True)
    linked_teachers = teachers.exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id='')
    
    print(f"Всего активных учителей: {teachers.count()}")
    print(f"Учителей с Telegram: {linked_teachers.count()}\n")
    
    if linked_teachers.exists():
        for teacher in linked_teachers:
            print(f"  ✅ {teacher.get_full_name() or teacher.email}")
            print(f"     Chat ID: {teacher.telegram_chat_id}\n")
    else:
        print("  ⚠️  Нет учителей с привязанным Telegram\n")
    
    # 4. Последние уведомления
    print("="*60)
    print("📬 Последние 10 попыток отправки уведомлений:\n")
    
    recent_logs = NotificationLog.objects.order_by('-created_at')[:10]
    
    if recent_logs.exists():
        for log in recent_logs:
            status_icon = "✅" if log.status == 'sent' else "❌" if log.status == 'failed' else "⏭️"
            print(f"{status_icon} {log.created_at.strftime('%d.%m %H:%M')} | {log.user.email}")
            print(f"   Type: {log.notification_type} | Status: {log.status}")
            if log.status == 'failed' or log.status == 'skipped':
                print(f"   Error: {log.error_message}")
            print()
    else:
        print("  Нет записей в NotificationLog")
        print("  Уведомления еще не отправлялись\n")
    
    # 5. Рекомендации
    print("="*60)
    print("💡 Рекомендации:\n")
    
    if not token or token == 'YOUR_BOT_TOKEN_HERE':
        print("1. Получите токен бота от @BotFather в Telegram")
        print("2. Добавьте токен в teaching_panel/.env:")
        print("   TELEGRAM_BOT_TOKEN=ваш_токен\n")
    
    if not linked_students.exists():
        print("1. Запустите бота: python telegram_bot.py")
        print("2. Студент должен связать аккаунт через /link")
        print("3. Используйте invite_code группы для связывания\n")
    
    if linked_students.exists() and not recent_logs.filter(status='sent').exists():
        print("1. Проверьте, что бот запущен: python telegram_bot.py")
        print("2. Проверьте, что TELEGRAM_BOT_TOKEN правильный")
        print("3. Попробуйте опубликовать ДЗ и проверьте логи\n")
    
    print("="*60)
    print("\n📖 Для детальной диагностики см. TELEGRAM_BOT_FULL_FLOW_TEST.md")


if __name__ == '__main__':
    try:
        check_telegram_integration()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
