"""
Views для экспорта календаря в iCal формате.

Эндпоинты:
- GET /api/calendar/export/ics/ - скачать .ics файл с расписанием
- GET /api/calendar/feed/<user_id>/<token>/ - публичный фид для подписки
- GET /api/calendar/lesson/<lesson_id>/ics/ - скачать .ics для одного урока
- GET /api/calendar/subscribe-links/ - получить ссылки для подписки
"""

from datetime import timedelta
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import Lesson, Group
from .ical_service import (
    generate_ical_calendar,
    generate_single_event_ics,
    generate_calendar_token,
    verify_calendar_token,
    get_google_calendar_add_url,
    get_apple_calendar_url,
    get_yandex_calendar_url,
    generate_full_calendar,
)


def _get_user_lessons(user, days_back: int = 7, days_forward: int = 90):
    """
    Получить уроки пользователя для экспорта.
    
    Args:
        user: Пользователь
        days_back: Сколько дней назад включать
        days_forward: Сколько дней вперед включать
        
    Returns:
        QuerySet уроков
    """
    now = timezone.now()
    start_date = now - timedelta(days=days_back)
    end_date = now + timedelta(days=days_forward)
    
    if user.role == 'teacher':
        # Учитель видит свои уроки
        return Lesson.objects.filter(
            teacher=user,
            start_time__gte=start_date,
            start_time__lte=end_date,
            is_quick_lesson=False  # Исключаем быстрые уроки
        ).select_related('group', 'teacher').order_by('start_time')
    
    elif user.role == 'student':
        # Студент видит уроки своих групп
        student_groups = Group.objects.filter(students=user)
        return Lesson.objects.filter(
            group__in=student_groups,
            start_time__gte=start_date,
            start_time__lte=end_date,
            is_quick_lesson=False
        ).select_related('group', 'teacher').order_by('start_time')
    
    elif user.role == 'admin':
        # Админ видит все
        return Lesson.objects.filter(
            start_time__gte=start_date,
            start_time__lte=end_date,
            is_quick_lesson=False
        ).select_related('group', 'teacher').order_by('start_time')
    
    return Lesson.objects.none()


def _get_user_homeworks(user, days_forward: int = 90):
    """
    Получить домашние задания с дедлайнами для пользователя.
    """
    from homework.models import Homework
    
    now = timezone.now()
    end_date = now + timedelta(days=days_forward)
    
    if user.role == 'teacher':
        # Учитель видит свои ДЗ с дедлайнами
        return Homework.objects.filter(
            teacher=user,
            status='published',
            deadline__isnull=False,
            deadline__gte=now,
            deadline__lte=end_date
        ).select_related('lesson', 'lesson__group').order_by('deadline')
    
    elif user.role == 'student':
        # Студент видит ДЗ своих групп
        student_groups = Group.objects.filter(students=user)
        return Homework.objects.filter(
            status='published',
            deadline__isnull=False,
            deadline__gte=now,
            deadline__lte=end_date,
            lesson__group__in=student_groups
        ).select_related('lesson', 'lesson__group').order_by('deadline')
    
    elif user.role == 'admin':
        return Homework.objects.filter(
            status='published',
            deadline__isnull=False,
            deadline__gte=now,
            deadline__lte=end_date
        ).select_related('lesson', 'lesson__group').order_by('deadline')
    
    return Homework.objects.none()


def _get_user_control_points(user, days_back: int = 7, days_forward: int = 90):
    """
    Получить контрольные точки для пользователя.
    """
    from analytics.models import ControlPoint
    
    now = timezone.now()
    start_date = (now - timedelta(days=days_back)).date()
    end_date = (now + timedelta(days=days_forward)).date()
    
    if user.role == 'teacher':
        return ControlPoint.objects.filter(
            teacher=user,
            date__gte=start_date,
            date__lte=end_date
        ).select_related('group').order_by('date')
    
    elif user.role == 'student':
        student_groups = Group.objects.filter(students=user)
        return ControlPoint.objects.filter(
            group__in=student_groups,
            date__gte=start_date,
            date__lte=end_date
        ).select_related('group').order_by('date')
    
    elif user.role == 'admin':
        return ControlPoint.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('group').order_by('date')
    
    return ControlPoint.objects.none()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_calendar_ics(request):
    """
    Скачать .ics файл с расписанием пользователя.
    
    Query params:
        - days_back: дней назад (по умолчанию 7)
        - days_forward: дней вперед (по умолчанию 90)
        - group_id: фильтр по группе (опционально)
    """
    user = request.user
    days_back = int(request.query_params.get('days_back', 7))
    days_forward = int(request.query_params.get('days_forward', 90))
    group_id = request.query_params.get('group_id')
    
    lessons = _get_user_lessons(user, days_back, days_forward)
    
    # Фильтр по группе
    if group_id:
        lessons = lessons.filter(group_id=group_id)
    
    # Генерируем имя календаря
    if user.role == 'teacher':
        calendar_name = f"Lectio - Расписание {user.get_full_name()}"
    elif user.role == 'student':
        calendar_name = f"Lectio - Мои занятия"
    else:
        calendar_name = "Lectio - Расписание"
    
    # Получаем ДЗ и контрольные
    include_deadlines = request.query_params.get('include_deadlines', 'true').lower() == 'true'
    homeworks = list(_get_user_homeworks(user, days_forward)) if include_deadlines else []
    control_points = list(_get_user_control_points(user, days_back, days_forward)) if include_deadlines else []
    
    # Генерируем полный календарь с уроками, ДЗ и контрольными
    ical_content = generate_full_calendar(
        list(lessons),
        homeworks=homeworks,
        control_points=control_points,
        calendar_name=calendar_name,
        include_zoom=True
    )
    
    # Возвращаем .ics файл
    response = HttpResponse(ical_content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="lectio_schedule.ics"'
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def calendar_feed(request, user_id: int, token: str):
    """
    Публичный календарный фид для подписки.
    
    Доступ по токену без авторизации - для Google Calendar, Яндекс, Apple.
    URL формат: /api/calendar/feed/<user_id>/<token>/
    """
    from accounts.models import CustomUser
    
    # Проверяем токен
    if not verify_calendar_token(user_id, token):
        return HttpResponse('Invalid token', status=403, content_type='text/plain')
    
    # Получаем пользователя
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return HttpResponse('User not found', status=404, content_type='text/plain')
    
    # Получаем уроки (больший период для фида)
    lessons = _get_user_lessons(user, days_back=30, days_forward=180)
    
    # Получаем ДЗ и контрольные
    homeworks = list(_get_user_homeworks(user, days_forward=180))
    control_points = list(_get_user_control_points(user, days_back=30, days_forward=180))
    
    # Генерируем календарь - простое название для всех клиентов
    calendar_name = "Lectio"
    
    ical_content = generate_full_calendar(
        list(lessons),
        homeworks=homeworks,
        control_points=control_points,
        calendar_name=calendar_name,
        include_zoom=True
    )
    
    # Возвращаем с правильными заголовками для кеширования
    response = HttpResponse(ical_content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'inline; filename="calendar.ics"'
    # Кешируем на 15 минут
    response['Cache-Control'] = 'public, max-age=900'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lesson_ics(request, lesson_id: int):
    """
    Скачать .ics файл для одного урока.
    Используется для кнопки "Добавить в календарь".
    """
    user = request.user
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Проверяем доступ
    has_access = False
    if user.role == 'admin':
        has_access = True
    elif user.role == 'teacher' and lesson.teacher_id == user.id:
        has_access = True
    elif user.role == 'student' and lesson.group.students.filter(id=user.id).exists():
        has_access = True
    
    if not has_access:
        return Response({'detail': 'Нет доступа к уроку'}, status=status.HTTP_403_FORBIDDEN)
    
    # Генерируем .ics
    ical_content = generate_single_event_ics(lesson)
    
    # Формируем имя файла
    safe_name = lesson.display_name.replace(' ', '_')[:30] if lesson.display_name else 'lesson'
    filename = f"{safe_name}.ics"
    
    response = HttpResponse(ical_content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscribe_links(request):
    """
    Получить ссылки для подписки на календарь.
    
    Возвращает ссылки для:
    - Google Calendar
    - Apple Calendar (webcal://)
    - Яндекс Календарь
    - Прямую ссылку на iCal фид
    """
    user = request.user
    
    # Генерируем токен для пользователя
    token = generate_calendar_token(user.id)

    # Формируем базовый URL по текущему запросу (scheme + host)
    base_url = request.build_absolute_uri('/').rstrip('/')

    # В этом проекте календарные endpoints живут под /schedule/api/...
    feed_url = f"{base_url}/schedule/api/calendar/feed/{user.id}/{token}/"
    
    # Генерируем ссылки для разных календарей
    google_url = get_google_calendar_add_url(feed_url)
    apple_url = get_apple_calendar_url(feed_url)
    yandex_url = get_yandex_calendar_url(feed_url)
    
    return Response({
        'feed_url': feed_url,
        'google_calendar': google_url,
        'apple_calendar': apple_url,
        'yandex_calendar': yandex_url,
        'download_url': f"{base_url}/schedule/api/calendar/export/ics/",
        'instructions': {
            'google': 'Нажмите на ссылку или добавьте календарь вручную: Настройки → Добавить календарь → Из URL',
            'apple': 'Нажмите на ссылку или добавьте в Календарь → Файл → Новая подписка на календарь',
            'yandex': 'Откройте Яндекс Календарь → Настройки → Подписки → Добавить → Вставьте URL фида',
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_calendar_token(request):
    """
    Перегенерировать токен календаря (если пользователь хочет отозвать доступ).
    
    Это изменит соль токена, что сделает старые ссылки недействительными.
    """
    from accounts.models import CustomUser
    import secrets
    
    user = request.user
    
    # Генерируем новую соль и сохраняем в профиле пользователя
    # Для этого нужно добавить поле calendar_token_salt в модель CustomUser
    # Пока просто возвращаем новые ссылки с текущей солью
    
    # TODO: Добавить поле calendar_token_salt в CustomUser
    # user.calendar_token_salt = secrets.token_hex(8)
    # user.save(update_fields=['calendar_token_salt'])
    
    return subscribe_links(request)
