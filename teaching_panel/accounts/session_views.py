"""
Трекинг времени на платформе — heartbeat API.

Фронтенд шлёт POST /api/session/heartbeat/ каждые 60 секунд.
Backend отвечает текущей сессией и суммарным временем за сегодня.

Также предоставляет GET /api/session/daily-time/ для получения
суммы времени по дням (для heatmap интеграции).
"""
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import PlatformSession


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def session_heartbeat(request):
    """
    POST /api/session/heartbeat/
    
    Фронтенд шлёт каждые 60 сек.
    Ответ: текущая сессия + время за сегодня.
    """
    session, created = PlatformSession.heartbeat(request.user)
    
    today = timezone.now().date()
    today_minutes = PlatformSession.get_daily_minutes(request.user, today)
    
    return Response({
        'session_id': session.id,
        'session_started': session.started_at.isoformat(),
        'session_duration_minutes': session.current_duration_minutes,
        'today_total_minutes': today_minutes,
        'is_new_session': created,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_daily_time(request):
    """
    GET /api/session/daily-time/?days=30&user_id=123
    
    Возвращает суммарное время на платформе по дням.
    - days: количество дней назад (default=30, max=365)
    - user_id: ID пользователя (только для учителей/админов, для просмотра ученика)
    
    Ответ: [{date: "2026-02-10", minutes: 45}, ...]
    """
    days = min(int(request.query_params.get('days', 30)), 365)
    user_id = request.query_params.get('user_id')
    
    # Определяем целевого пользователя
    target_user = request.user
    if user_id and str(user_id) != str(request.user.id):
        # Учителя и админы могут смотреть данные учеников
        if request.user.role not in ('teacher', 'admin'):
            return Response(
                {'detail': 'Нет доступа к данным другого пользователя'},
                status=status.HTTP_403_FORBIDDEN
            )
        from .models import CustomUser
        try:
            target_user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    today = timezone.now().date()
    start_date = today - timedelta(days=days - 1)
    
    # Агрегируем завершённые сессии по дням
    closed_sessions = (
        PlatformSession.objects
        .filter(
            user=target_user,
            is_active=False,
            started_at__date__gte=start_date,
        )
        .extra(select={'session_date': "DATE(started_at)"})
        .values('session_date')
        .annotate(total_minutes=Sum('duration_minutes'))
        .order_by('session_date')
    )
    
    # Собираем в словарь
    daily_map = {}
    for entry in closed_sessions:
        date_str = str(entry['session_date'])
        daily_map[date_str] = entry['total_minutes'] or 0
    
    # Прибавляем активную сессию, если есть
    active_session = PlatformSession.objects.filter(
        user=target_user,
        is_active=True,
    ).first()
    
    if active_session:
        active_date = active_session.started_at.date().isoformat()
        if active_date >= start_date.isoformat():
            daily_map[active_date] = daily_map.get(active_date, 0) + active_session.current_duration_minutes
    
    # Формируем полный массив по дням
    result = []
    current = start_date
    total_minutes = 0
    while current <= today:
        date_str = current.isoformat()
        minutes = daily_map.get(date_str, 0)
        total_minutes += minutes
        result.append({
            'date': date_str,
            'minutes': minutes,
        })
        current += timedelta(days=1)
    
    return Response({
        'user_id': target_user.id,
        'user_name': target_user.get_full_name() or target_user.email,
        'user_role': target_user.role,
        'period_days': days,
        'total_minutes': total_minutes,
        'total_hours': round(total_minutes / 60, 1),
        'avg_daily_minutes': round(total_minutes / max(days, 1), 1),
        'daily_time': result,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def session_close(request):
    """
    POST /api/session/close/
    
    Явное закрытие сессии (при выходе/закрытии вкладки).
    Фронтенд вызывает через navigator.sendBeacon().
    """
    closed_count = 0
    active_sessions = PlatformSession.objects.filter(
        user=request.user,
        is_active=True,
    )
    for session in active_sessions:
        session.close_session()
        closed_count += 1
    
    return Response({
        'closed_sessions': closed_count,
        'status': 'ok',
    })
