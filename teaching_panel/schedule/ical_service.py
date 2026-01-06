"""
iCal (ICS) генератор для экспорта расписания в Google Calendar, Яндекс Календарь, Apple Calendar.

RFC 5545: https://tools.ietf.org/html/rfc5545

Поддерживаемые форматы:
- Одиночное событие (.ics файл)
- Календарный фид (подписка по URL)
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import List, Optional
from django.conf import settings
from django.utils import timezone


def escape_ical_text(text: str) -> str:
    """Экранирование текста для iCal (RFC 5545)."""
    if not text:
        return ''
    # Экранируем специальные символы
    text = text.replace('\\', '\\\\')
    text = text.replace(';', '\\;')
    text = text.replace(',', '\\,')
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '')
    return text


def format_ical_datetime(dt: datetime) -> str:
    """Форматирование datetime в iCal формат (UTC)."""
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    utc_dt = dt.astimezone(dt_timezone.utc)
    return utc_dt.strftime('%Y%m%dT%H%M%SZ')


def generate_uid(lesson_id: int, domain: str = 'lectio.space') -> str:
    """Генерация уникального UID для события."""
    return f"lesson-{lesson_id}@{domain}"


def generate_ical_event(lesson, include_zoom: bool = True) -> str:
    """
    Генерация одного события в формате iCal.
    
    Args:
        lesson: Объект Lesson
        include_zoom: Включать ли Zoom ссылку в описание
        
    Returns:
        Строка с событием в формате VEVENT
    """
    uid = generate_uid(lesson.id)
    dtstamp = format_ical_datetime(timezone.now())
    dtstart = format_ical_datetime(lesson.start_time)
    dtend = format_ical_datetime(lesson.end_time)
    
    # Название события
    summary = escape_ical_text(lesson.display_name or lesson.group.name)
    
    # Описание события
    description_parts = []
    
    # Группа
    if lesson.group:
        description_parts.append(f"Группа: {lesson.group.name}")
    
    # Темы урока
    if lesson.topics:
        description_parts.append(f"Темы: {lesson.topics}")
    
    # Zoom ссылка для студентов
    if include_zoom and lesson.zoom_join_url:
        description_parts.append(f"Подключиться к Zoom: {lesson.zoom_join_url}")
        if lesson.zoom_password:
            description_parts.append(f"Пароль: {lesson.zoom_password}")
    
    # Заметки
    if lesson.notes:
        description_parts.append(f"Заметки: {lesson.notes}")
    
    description = escape_ical_text('\n'.join(description_parts))
    
    # Локация (Zoom URL или физический адрес)
    location = ''
    if lesson.zoom_join_url:
        location = escape_ical_text(lesson.zoom_join_url)
    elif lesson.location:
        location = escape_ical_text(lesson.location)
    
    # Формируем VEVENT
    lines = [
        'BEGIN:VEVENT',
        f'UID:{uid}',
        f'DTSTAMP:{dtstamp}',
        f'DTSTART:{dtstart}',
        f'DTEND:{dtend}',
        f'SUMMARY:{summary}',
    ]
    
    if description:
        lines.append(f'DESCRIPTION:{description}')
    
    if location:
        lines.append(f'LOCATION:{location}')
    
    # URL для Zoom
    if lesson.zoom_join_url:
        lines.append(f'URL:{lesson.zoom_join_url}')
    
    # Статус события
    lines.append('STATUS:CONFIRMED')
    lines.append('TRANSP:OPAQUE')  # Показывать как "занято"
    
    lines.append('END:VEVENT')
    
    return '\r\n'.join(lines)


def generate_ical_calendar(
    lessons: List,
    calendar_name: str = 'Lectio - Расписание',
    include_zoom: bool = True
) -> str:
    """
    Генерация полного iCal календаря.
    
    Args:
        lessons: Список объектов Lesson
        calendar_name: Название календаря
        include_zoom: Включать ли Zoom ссылки
        
    Returns:
        Полный iCal файл в формате строки
    """
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Lectio//Teaching Panel//RU',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{escape_ical_text(calendar_name)}',
        'X-WR-TIMEZONE:Europe/Moscow',
    ]
    
    # Добавляем определение временной зоны
    lines.extend([
        'BEGIN:VTIMEZONE',
        'TZID:Europe/Moscow',
        'BEGIN:STANDARD',
        'DTSTART:19700101T000000',
        'TZOFFSETFROM:+0300',
        'TZOFFSETTO:+0300',
        'TZNAME:MSK',
        'END:STANDARD',
        'END:VTIMEZONE',
    ])
    
    # Добавляем события
    for lesson in lessons:
        event = generate_ical_event(lesson, include_zoom=include_zoom)
        lines.append(event)
    
    lines.append('END:VCALENDAR')
    
    return '\r\n'.join(lines)


def generate_calendar_token(user_id: int, salt: str = '') -> str:
    """
    Генерация токена для доступа к календарному фиду.
    
    Токен позволяет доступ к календарю без авторизации (для подписки в Google Calendar и др.).
    """
    secret = getattr(settings, 'SECRET_KEY', 'default-secret')
    data = f"{user_id}:{salt}:{secret}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def verify_calendar_token(user_id: int, token: str, salt: str = '') -> bool:
    """Проверка токена календарного фида."""
    expected = generate_calendar_token(user_id, salt)
    return secrets.compare_digest(token, expected)


# Ссылки для добавления в различные календари
def get_google_calendar_add_url(ical_url: str) -> str:
    """
    Генерация ссылки для добавления в Google Calendar.
    Google Calendar требует webcal:// протокол для подписки через cid=.
    Также можно использовать /calendar/u/0/r/settings/addbyurl для ручного добавления.
    """
    from urllib.parse import quote
    # Преобразуем https:// в webcal:// для корректной подписки
    webcal_url = ical_url
    if ical_url.startswith('https://'):
        webcal_url = ical_url.replace('https://', 'webcal://', 1)
    elif ical_url.startswith('http://'):
        webcal_url = ical_url.replace('http://', 'webcal://', 1)
    return f"https://calendar.google.com/calendar/r?cid={quote(webcal_url, safe='')}"


def get_apple_calendar_url(ical_url: str) -> str:
    """
    Генерация ссылки для Apple Calendar (webcal:// протокол).
    """
    if ical_url.startswith('https://'):
        return ical_url.replace('https://', 'webcal://', 1)
    elif ical_url.startswith('http://'):
        return ical_url.replace('http://', 'webcal://', 1)
    return f"webcal://{ical_url}"


def get_yandex_calendar_url(ical_url: str) -> str:
    """
    Генерация ссылки для Яндекс Календаря.
    Яндекс поддерживает добавление внешнего календаря по URL.
    """
    from urllib.parse import quote
    # Яндекс Календарь принимает ics URL напрямую через настройки
    # Но можно использовать webcal:// протокол
    return get_apple_calendar_url(ical_url)


def generate_single_event_ics(lesson) -> str:
    """
    Генерация .ics файла для одного события.
    Используется для кнопки "Добавить в календарь" на странице урока.
    """
    return generate_ical_calendar([lesson], calendar_name=lesson.display_name, include_zoom=True)


# ===== Дедлайны ДЗ и контрольных точек =====

def generate_homework_uid(homework_id: int, domain: str = 'lectio.space') -> str:
    """Генерация уникального UID для события дедлайна ДЗ."""
    return f"homework-{homework_id}@{domain}"


def generate_control_point_uid(cp_id: int, domain: str = 'lectio.space') -> str:
    """Генерация уникального UID для контрольной точки."""
    return f"control-point-{cp_id}@{domain}"


def generate_homework_deadline_event(homework) -> Optional[str]:
    """
    Генерация события дедлайна домашнего задания.
    
    Args:
        homework: Объект Homework с deadline
        
    Returns:
        Строка VEVENT или None если нет дедлайна
    """
    if not homework.deadline:
        return None
    
    uid = generate_homework_uid(homework.id)
    dtstamp = format_ical_datetime(timezone.now())
    
    # Дедлайн — это целодневное событие или конкретное время
    deadline_dt = homework.deadline
    dtstart = format_ical_datetime(deadline_dt)
    # Событие дедлайна длится 1 час (напоминание)
    dtend = format_ical_datetime(deadline_dt + timedelta(hours=1))
    
    # Название с эмодзи для визуального отличия
    summary = escape_ical_text(f"📝 ДЗ: {homework.title}")
    
    # Описание
    description_parts = [f"Дедлайн домашнего задания: {homework.title}"]
    
    if homework.description:
        description_parts.append(f"\n{homework.description[:200]}")
    
    if homework.lesson and homework.lesson.group:
        description_parts.append(f"\nГруппа: {homework.lesson.group.name}")
    
    description = escape_ical_text('\n'.join(description_parts))
    
    lines = [
        'BEGIN:VEVENT',
        f'UID:{uid}',
        f'DTSTAMP:{dtstamp}',
        f'DTSTART:{dtstart}',
        f'DTEND:{dtend}',
        f'SUMMARY:{summary}',
    ]
    
    if description:
        lines.append(f'DESCRIPTION:{description}')
    
    # Напоминание за 1 день
    lines.extend([
        'BEGIN:VALARM',
        'ACTION:DISPLAY',
        'DESCRIPTION:Напоминание о дедлайне ДЗ',
        'TRIGGER:-P1D',
        'END:VALARM',
    ])
    
    # Напоминание за 2 часа
    lines.extend([
        'BEGIN:VALARM',
        'ACTION:DISPLAY',
        'DESCRIPTION:Скоро дедлайн ДЗ!',
        'TRIGGER:-PT2H',
        'END:VALARM',
    ])
    
    lines.append('STATUS:CONFIRMED')
    lines.append('TRANSP:TRANSPARENT')  # Не блокирует время
    lines.append('END:VEVENT')
    
    return '\r\n'.join(lines)


def generate_control_point_event(control_point) -> str:
    """
    Генерация события контрольной точки.
    
    Args:
        control_point: Объект ControlPoint
        
    Returns:
        Строка VEVENT
    """
    uid = generate_control_point_uid(control_point.id)
    dtstamp = format_ical_datetime(timezone.now())
    
    # Контрольная точка — целодневное событие
    # Формат для целодневных событий: YYYYMMDD (без времени)
    date_str = control_point.date.strftime('%Y%m%d')
    
    # Название с эмодзи
    summary = escape_ical_text(f"📊 Контрольная: {control_point.title}")
    
    # Описание
    description_parts = [f"Контрольная точка: {control_point.title}"]
    description_parts.append(f"Максимум баллов: {control_point.max_points}")
    
    if control_point.group:
        description_parts.append(f"Группа: {control_point.group.name}")
    
    description = escape_ical_text('\n'.join(description_parts))
    
    lines = [
        'BEGIN:VEVENT',
        f'UID:{uid}',
        f'DTSTAMP:{dtstamp}',
        f'DTSTART;VALUE=DATE:{date_str}',  # Целодневное событие
        f'SUMMARY:{summary}',
    ]
    
    if description:
        lines.append(f'DESCRIPTION:{description}')
    
    # Напоминание за 1 день
    lines.extend([
        'BEGIN:VALARM',
        'ACTION:DISPLAY',
        'DESCRIPTION:Напоминание о контрольной',
        'TRIGGER:-P1D',
        'END:VALARM',
    ])
    
    lines.append('STATUS:CONFIRMED')
    lines.append('TRANSP:TRANSPARENT')
    lines.append('END:VEVENT')
    
    return '\r\n'.join(lines)


def generate_full_calendar(
    lessons: List,
    homeworks: List = None,
    control_points: List = None,
    calendar_name: str = 'Lectio - Расписание',
    include_zoom: bool = True
) -> str:
    """
    Генерация полного iCal календаря с уроками, дедлайнами ДЗ и контрольными.
    
    Args:
        lessons: Список объектов Lesson
        homeworks: Список объектов Homework с дедлайнами
        control_points: Список объектов ControlPoint
        calendar_name: Название календаря
        include_zoom: Включать ли Zoom ссылки
        
    Returns:
        Полный iCal файл
    """
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Lectio//Teaching Panel//RU',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{escape_ical_text(calendar_name)}',
        'X-WR-TIMEZONE:Europe/Moscow',
    ]
    
    # Временная зона
    lines.extend([
        'BEGIN:VTIMEZONE',
        'TZID:Europe/Moscow',
        'BEGIN:STANDARD',
        'DTSTART:19700101T000000',
        'TZOFFSETFROM:+0300',
        'TZOFFSETTO:+0300',
        'TZNAME:MSK',
        'END:STANDARD',
        'END:VTIMEZONE',
    ])
    
    # Уроки
    for lesson in lessons:
        event = generate_ical_event(lesson, include_zoom=include_zoom)
        lines.append(event)
    
    # Дедлайны ДЗ
    if homeworks:
        for hw in homeworks:
            event = generate_homework_deadline_event(hw)
            if event:
                lines.append(event)
    
    # Контрольные точки
    if control_points:
        for cp in control_points:
            event = generate_control_point_event(cp)
            lines.append(event)
    
    lines.append('END:VCALENDAR')
    
    return '\r\n'.join(lines)
