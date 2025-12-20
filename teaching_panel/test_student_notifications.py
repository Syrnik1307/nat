#!/usr/bin/env python
"""Test student notifications using teacher's chat_id temporarily"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser, NotificationSettings
from accounts.notifications import send_telegram_notification

# Находим студента и преподавателя
student = CustomUser.objects.filter(role='student').first()
teacher = CustomUser.objects.filter(role='teacher', telegram_chat_id__isnull=False).exclude(telegram_chat_id='').first()

if not student:
    print("❌ Нет студентов в системе")
    exit(1)

if not teacher:
    print("❌ Нет преподавателя с Telegram")
    exit(1)

print(f"📝 Тестируем студента: {student.email}")
print(f"👨‍🏫 Используем chat_id преподавателя: {teacher.telegram_chat_id}")

# Временно назначаем chat_id студенту
old_chat_id = student.telegram_chat_id
student.telegram_chat_id = teacher.telegram_chat_id
student.save(update_fields=['telegram_chat_id'])

# Создаём/обновляем настройки
ns, _ = NotificationSettings.objects.get_or_create(user=student)
ns.telegram_enabled = True
ns.notify_lesson_reminders = True
ns.notify_new_homework = True
ns.notify_homework_graded = True
ns.notify_homework_deadline = True
ns.save()

print(f"\n🧪 Отправляем тестовые уведомления студенту:\n")

# 1. Напоминание об уроке
msg = "⏰ [ТЕСТ-СТУДЕНТ] Напоминание об уроке!\nУрок: Математика\nГруппа: Тестовая\nНачало через ~30 мин."
ok = send_telegram_notification(student, 'lesson_reminder', msg)
print(f"   lesson_reminder: {'✅' if ok else '❌'}")

# 2. Новое ДЗ
msg = "📚 [ТЕСТ-СТУДЕНТ] Новое домашнее задание!\nТема: Тригонометрия\nПреподаватель: Тестовый"
ok = send_telegram_notification(student, 'new_homework', msg)
print(f"   new_homework: {'✅' if ok else '❌'}")

# 3. ДЗ проверено
msg = "✅ [ТЕСТ-СТУДЕНТ] Ваша работа проверена!\nДЗ: Тригонометрия\nБалл: 95/100"
ok = send_telegram_notification(student, 'homework_graded', msg)
print(f"   homework_graded: {'✅' if ok else '❌'}")

# 4. Дедлайн
msg = "📎 [ТЕСТ-СТУДЕНТ] Не забудьте сдать ДЗ!\nОсталось: 2 дня до дедлайна"
ok = send_telegram_notification(student, 'homework_deadline', msg)
print(f"   homework_deadline: {'✅' if ok else '❌'}")

# Восстанавливаем оригинальный chat_id
student.telegram_chat_id = old_chat_id
student.save(update_fields=['telegram_chat_id'])

print(f"\n✅ Тест завершён! Проверьте Telegram преподавателя.")
