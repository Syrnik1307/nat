#!/usr/bin/env python
"""
Тестирование всех типов Telegram уведомлений.
Запуск: python manage.py runscript test_telegram_notifications

Либо напрямую:
    cd teaching_panel
    source ../venv/bin/activate  # или ..\venv\Scripts\Activate.ps1 на Windows
    python -c "import django; django.setup(); exec(open('test_telegram_notifications.py').read())"
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import json

from accounts.models import CustomUser, NotificationSettings, NotificationLog, Subscription
from accounts.notifications import send_telegram_notification, NOTIFICATION_FIELD_MAP


def separator(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def test_1_check_config():
    """Проверяем базовую конфигурацию"""
    separator("1. Проверка конфигурации")
    
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None) or os.getenv('TELEGRAM_BOT_TOKEN', '')
    if not token or token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ TELEGRAM_BOT_TOKEN не настроен!")
        return False
    
    print(f"✅ TELEGRAM_BOT_TOKEN: ...{token[-10:]}")
    
    # Проверка всех типов уведомлений
    print(f"\n📋 Настроенные типы уведомлений:")
    for notif_type, field in NOTIFICATION_FIELD_MAP.items():
        print(f"   - {notif_type} → {field}")
    
    return True


def test_2_find_test_users():
    """Ищем пользователей с Telegram"""
    separator("2. Поиск пользователей с Telegram")
    
    users_with_telegram = CustomUser.objects.filter(
        telegram_chat_id__isnull=False
    ).exclude(telegram_chat_id='')
    
    print(f"\n📊 Всего пользователей с telegram_chat_id: {users_with_telegram.count()}")
    
    result = {'teacher': None, 'student': None}
    
    for user in users_with_telegram[:20]:
        role = getattr(user, 'role', 'unknown')
        name = user.get_full_name() or user.email
        print(f"   👤 {name} ({user.email}) - role: {role}, chat_id: {user.telegram_chat_id}")
        
        if role == 'teacher' and result['teacher'] is None:
            result['teacher'] = user
        elif role == 'student' and result['student'] is None:
            result['student'] = user
    
    # Проверяем настройки уведомлений
    for role, user in result.items():
        if user:
            try:
                ns = NotificationSettings.objects.get(user=user)
                print(f"\n⚙️ Настройки {role} ({user.email}):")
                print(f"   telegram_enabled: {ns.telegram_enabled}")
                print(f"   notify_lesson_reminders: {ns.notify_lesson_reminders}")
                print(f"   notify_new_homework: {ns.notify_new_homework}")
                print(f"   notify_homework_graded: {ns.notify_homework_graded}")
                print(f"   notify_homework_submitted: {ns.notify_homework_submitted}")
                print(f"   notify_subscription_expiring: {ns.notify_subscription_expiring}")
                print(f"   notify_payment_success: {ns.notify_payment_success}")
            except NotificationSettings.DoesNotExist:
                print(f"\n⚠️ Нет NotificationSettings для {user.email}")
    
    return result


def test_3_send_test_notifications(users):
    """Отправляем тестовые уведомления"""
    separator("3. Отправка тестовых уведомлений")
    
    results = []
    
    # === УВЕДОМЛЕНИЯ ДЛЯ УЧЕНИКА ===
    student = users.get('student')
    if student:
        print(f"\n🎓 Тестируем уведомления для ученика: {student.email}")
        
        # 3.1 Напоминание об уроке
        msg = "⏰ [ТЕСТ] Напоминание об уроке!\nУрок: Тестовый урок\nГруппа: Тест\nНачало через ~30 мин."
        ok = send_telegram_notification(student, 'lesson_reminder', msg)
        results.append(('lesson_reminder', 'student', ok))
        print(f"   lesson_reminder: {'✅' if ok else '❌'}")
        
        # 3.2 Новое ДЗ
        msg = "📚 [ТЕСТ] Новое домашнее задание: Тест\nПреподаватель: Тестовый\nГруппа: Тест"
        ok = send_telegram_notification(student, 'new_homework', msg)
        results.append(('new_homework', 'student', ok))
        print(f"   new_homework: {'✅' if ok else '❌'}")
        
        # 3.3 ДЗ проверено
        msg = "✅ [ТЕСТ] 'Тестовое ДЗ' проверено.\nПреподаватель: Тестовый.\nИтоговый балл: 95."
        ok = send_telegram_notification(student, 'homework_graded', msg)
        results.append(('homework_graded', 'student', ok))
        print(f"   homework_graded: {'✅' if ok else '❌'}")
        
        # 3.4 Дедлайн ДЗ
        msg = "📎 [ТЕСТ] Напоминание о дедлайне!\nДЗ: Тест\nОсталось: 2 дня"
        ok = send_telegram_notification(student, 'homework_deadline', msg)
        results.append(('homework_deadline', 'student', ok))
        print(f"   homework_deadline: {'✅' if ok else '❌'}")
    else:
        print("\n⚠️ Нет ученика с Telegram для тестирования")
    
    # === УВЕДОМЛЕНИЯ ДЛЯ ПРЕПОДАВАТЕЛЯ ===
    teacher = users.get('teacher')
    if teacher:
        print(f"\n👨‍🏫 Тестируем уведомления для преподавателя: {teacher.email}")
        
        # 3.5 Ученик сдал ДЗ
        msg = "📘 [ТЕСТ] Новая сдача ДЗ\nТестовый Ученик отправил(а) 'Тест'.\nОткройте Teaching Panel, чтобы проверить работу."
        ok = send_telegram_notification(teacher, 'homework_submitted', msg)
        results.append(('homework_submitted', 'teacher', ok))
        print(f"   homework_submitted: {'✅' if ok else '❌'}")
        
        # 3.6 Подписка истекает
        msg = "⚠️ [ТЕСТ] Подписка Teaching Panel скоро истекает!\nОсталось: 3 дн.\nПродлите подписку."
        ok = send_telegram_notification(teacher, 'subscription_expiring', msg)
        results.append(('subscription_expiring', 'teacher', ok))
        print(f"   subscription_expiring: {'✅' if ok else '❌'}")
        
        # 3.7 Платёж прошёл
        msg = "💳 [ТЕСТ] Подписка активирована!\nПодписка активна до 20.01.2026\nСумма: 990 RUB"
        ok = send_telegram_notification(teacher, 'payment_success', msg)
        results.append(('payment_success', 'teacher', ok))
        print(f"   payment_success: {'✅' if ok else '❌'}")
        
        # 3.8 Хранилище заполнено
        msg = "🚨 [ТЕСТ] Хранилище заполнено!\nИспользовано: 9.5 ГБ из 10 ГБ (95%)\nУдалите старые записи."
        ok = send_telegram_notification(teacher, 'storage_quota_warning', msg)
        results.append(('storage_quota_warning', 'teacher', ok))
        print(f"   storage_quota_warning: {'✅' if ok else '❌'}")
    else:
        print("\n⚠️ Нет преподавателя с Telegram для тестирования")
    
    return results


def test_4_check_logs():
    """Проверяем логи уведомлений"""
    separator("4. Проверка логов уведомлений")
    
    recent_logs = NotificationLog.objects.order_by('-created_at')[:20]
    
    print(f"\n📜 Последние 20 записей в NotificationLog:")
    for log in recent_logs:
        status_icon = {
            'sent': '✅',
            'failed': '❌',
            'skipped': '⏭️'
        }.get(log.status, '❓')
        
        user_email = log.user.email if log.user else 'N/A'
        created = log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        error = f" ({log.error_message[:50]}...)" if log.error_message else ""
        
        print(f"   {status_icon} [{created}] {log.notification_type} → {user_email} [{log.channel}]{error}")


def test_5_summary(results):
    """Итоговый отчёт"""
    separator("5. ИТОГОВЫЙ ОТЧЁТ")
    
    if not results:
        print("⚠️ Тесты не выполнялись (нет пользователей с Telegram)")
        return
    
    sent = sum(1 for _, _, ok in results if ok)
    failed = len(results) - sent
    
    print(f"\n📊 Результаты тестов:")
    print(f"   ✅ Успешно отправлено: {sent}")
    print(f"   ❌ Не отправлено: {failed}")
    
    print(f"\n📋 Детали по типам:")
    for notif_type, role, ok in results:
        status = '✅ OK' if ok else '❌ FAIL'
        print(f"   [{role}] {notif_type}: {status}")
    
    if failed > 0:
        print("\n⚠️ ПРИЧИНЫ ОШИБОК (проверьте):")
        print("   - telegram_enabled = False в NotificationSettings")
        print("   - Конкретный тип уведомления отключен (notify_*)")
        print("   - telegram_chat_id не привязан")
        print("   - Дедупликация (такое же сообщение было недавно)")
        print("   - Ошибка Telegram API (неверный token, бот заблокирован)")


def run():
    """Главная функция запуска тестов"""
    print("\n🚀 ТЕСТИРОВАНИЕ TELEGRAM УВЕДОМЛЕНИЙ")
    print(f"   Дата/время: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Проверяем конфигурацию
    if not test_1_check_config():
        print("\n⛔ Тестирование прервано: TELEGRAM_BOT_TOKEN не настроен")
        return
    
    # 2. Ищем тестовых пользователей
    users = test_2_find_test_users()
    
    if not users.get('teacher') and not users.get('student'):
        print("\n⛔ Нет пользователей с привязанным Telegram!")
        print("   Привяжите Telegram через бота /start")
        return
    
    # 3. Отправляем тестовые уведомления
    results = test_3_send_test_notifications(users)
    
    # 4. Проверяем логи
    test_4_check_logs()
    
    # 5. Итоговый отчёт
    test_5_summary(results)
    
    print("\n" + "="*60)
    print("📱 ПРОВЕРЬТЕ TELEGRAM У ТЕСТОВЫХ ПОЛЬЗОВАТЕЛЕЙ!")
    print("="*60 + "\n")


if __name__ == '__main__':
    run()
