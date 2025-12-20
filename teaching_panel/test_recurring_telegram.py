#!/usr/bin/env python
"""
Тестирование Telegram рассылки в группы для регулярных уроков.
Запуск: cd teaching_panel && python test_recurring_telegram.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import requests

from accounts.models import CustomUser
from schedule.models import RecurringLesson, Group, RecurringLessonTelegramBindCode


def separator(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def test_1_check_config():
    """Проверяем базовую конфигурацию"""
    separator("1. Проверка конфигурации")
    
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None) or os.getenv('TELEGRAM_BOT_TOKEN', '')
    if not token or token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ TELEGRAM_BOT_TOKEN не настроен!")
        return None
    
    print(f"✅ TELEGRAM_BOT_TOKEN: ...{token[-10:]}")
    
    # Проверяем что бот работает
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if data.get('ok'):
            bot_info = data.get('result', {})
            print(f"✅ Бот: @{bot_info.get('username')} (id: {bot_info.get('id')})")
        else:
            print(f"❌ Ошибка бота: {data}")
            return None
    except Exception as e:
        print(f"❌ Не удалось подключиться к боту: {e}")
        return None
    
    return token


def test_2_find_recurring_lessons():
    """Ищем регулярные уроки с Telegram настройками"""
    separator("2. Поиск регулярных уроков с Telegram")
    
    all_rl = RecurringLesson.objects.select_related('group', 'teacher').all()
    print(f"\n📊 Всего регулярных уроков: {all_rl.count()}")
    
    with_telegram = all_rl.filter(telegram_notify_enabled=True)
    print(f"📊 С включенным Telegram: {with_telegram.count()}")
    
    with_group_notify = all_rl.filter(telegram_notify_to_group=True).exclude(telegram_group_chat_id='')
    print(f"📊 С chat_id группы: {with_group_notify.count()}")
    
    result = {'all': [], 'with_group': None}
    
    for rl in all_rl[:10]:
        group_name = rl.group.name if rl.group else 'N/A'
        teacher_name = rl.teacher.email if rl.teacher else 'N/A'
        print(f"\n   📚 ID={rl.id}: {rl.title or group_name}")
        print(f"      Группа: {group_name}, Учитель: {teacher_name}")
        print(f"      telegram_notify_enabled: {rl.telegram_notify_enabled}")
        print(f"      telegram_notify_to_group: {rl.telegram_notify_to_group}")
        print(f"      telegram_group_chat_id: '{rl.telegram_group_chat_id or 'НЕТ'}'")
        print(f"      telegram_notify_to_students: {rl.telegram_notify_to_students}")
        
        result['all'].append(rl)
        
        if rl.telegram_notify_to_group and rl.telegram_group_chat_id and not result['with_group']:
            result['with_group'] = rl
    
    return result


def test_3_bind_codes():
    """Проверяем коды привязки"""
    separator("3. Коды привязки (RecurringLessonTelegramBindCode)")
    
    codes = RecurringLessonTelegramBindCode.objects.select_related('recurring_lesson').order_by('-created_at')[:10]
    print(f"\n📊 Последние коды привязки:")
    
    for code in codes:
        rl_title = code.recurring_lesson.title if code.recurring_lesson else 'N/A'
        status = 'Использован' if code.used_at else ('Истёк' if code.expires_at and code.expires_at < timezone.now() else 'Активен')
        print(f"   🔑 {code.code}: {rl_title} [{status}]")
        if code.used_at:
            print(f"      Использован в: {code.used_chat_id}")


def test_4_send_test_to_group(token, rl):
    """Отправляем тестовое сообщение в группу"""
    separator("4. Отправка тестового сообщения в группу")
    
    if not rl:
        print("⚠️ Нет регулярного урока с chat_id группы для тестирования")
        return False
    
    chat_id = rl.telegram_group_chat_id.strip()
    if not chat_id:
        print("⚠️ chat_id пустой")
        return False
    
    group_name = rl.group.name if rl.group else 'N/A'
    teacher_name = rl.teacher.get_full_name() if rl.teacher else 'N/A'
    
    message = (
        f"🧪 *Тестовое сообщение*\n\n"
        f"📚 Урок: {rl.title or group_name}\n"
        f"👨‍🏫 Преподаватель: {teacher_name}\n"
        f"⏰ Время: {timezone.now().strftime('%H:%M')}\n\n"
        f"Это тестовое сообщение для проверки рассылки."
    )
    
    print(f"\n📤 Отправляем в chat_id: {chat_id}")
    print(f"   Урок: {rl.title or group_name}")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown',
    }
    
    try:
        resp = requests.post(url, json=data, timeout=10)
        result = resp.json()
        
        if result.get('ok'):
            print(f"✅ Сообщение отправлено!")
            return True
        else:
            error_code = result.get('error_code')
            description = result.get('description', '')
            print(f"❌ Ошибка: {error_code} - {description}")
            
            # Диагностика типичных ошибок
            if error_code == 400:
                if 'chat not found' in description.lower():
                    print("   💡 Группа не найдена. Возможно chat_id неверный или бот удалён из группы.")
                elif 'bot is not a member' in description.lower():
                    print("   💡 Бот не добавлен в группу.")
            elif error_code == 403:
                print("   💡 Бот заблокирован или не имеет прав писать в группу.")
            elif error_code == 401:
                print("   💡 Неверный токен бота.")
            
            return False
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False


def test_5_create_bind_code(token, rl):
    """Тест создания кода привязки"""
    separator("5. Тест создания кода привязки")
    
    if not rl:
        print("⚠️ Нет регулярного урока для теста")
        return
    
    from django.utils.crypto import get_random_string
    
    ttl_minutes = 30
    expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
    
    code = None
    for _ in range(10):
        candidate = get_random_string(8).upper()
        if not RecurringLessonTelegramBindCode.objects.filter(code=candidate).exists():
            code = candidate
            break
    
    if not code:
        print("❌ Не удалось сгенерировать код")
        return
    
    bind = RecurringLessonTelegramBindCode.objects.create(
        recurring_lesson=rl,
        code=code,
        expires_at=expires_at,
    )
    
    print(f"✅ Код создан: {code}")
    print(f"   Действует до: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Инструкция: /bindgroup {code}")
    
    # Удаляем тестовый код
    bind.delete()
    print(f"   (тестовый код удалён)")


def test_6_teacher_zoom_pmi():
    """Проверяем есть ли у учителей zoom_pmi_link"""
    separator("6. Проверка Zoom PMI у преподавателей")
    
    teachers = CustomUser.objects.filter(role='teacher')
    print(f"\n📊 Всего преподавателей: {teachers.count()}")
    
    with_pmi = teachers.exclude(zoom_pmi_link='').exclude(zoom_pmi_link__isnull=True)
    print(f"📊 С zoom_pmi_link: {with_pmi.count()}")
    
    for t in teachers[:5]:
        pmi = getattr(t, 'zoom_pmi_link', '') or ''
        status = '✅' if pmi.strip() else '❌'
        print(f"   {status} {t.email}: {pmi[:30] if pmi else 'НЕТ'}")


def run():
    """Главная функция"""
    print("\n🚀 ТЕСТИРОВАНИЕ TELEGRAM РАССЫЛКИ В ГРУППЫ")
    print(f"   Дата/время: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Проверяем конфигурацию
    token = test_1_check_config()
    if not token:
        print("\n⛔ Тестирование прервано: токен не настроен")
        return
    
    # 2. Ищем регулярные уроки
    lessons = test_2_find_recurring_lessons()
    
    # 3. Коды привязки
    test_3_bind_codes()
    
    # 4. Тест отправки в группу
    rl_with_group = lessons.get('with_group')
    test_4_send_test_to_group(token, rl_with_group)
    
    # 5. Тест создания кода привязки
    any_rl = lessons['all'][0] if lessons['all'] else None
    test_5_create_bind_code(token, any_rl)
    
    # 6. Проверка Zoom PMI
    test_6_teacher_zoom_pmi()
    
    print("\n" + "="*60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60 + "\n")


if __name__ == '__main__':
    run()
