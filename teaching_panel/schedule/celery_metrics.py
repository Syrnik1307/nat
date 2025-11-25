"""
Метрики и мониторинг Celery задач
Эндпоинт для проверки статуса задач, истории выполнения
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from celery.result import AsyncResult
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from schedule.models import Lesson
from zoom_pool.models import ZoomAccount
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def celery_metrics(request):
    """
    Получить метрики выполнения Celery задач
    
    GET /api/celery/metrics/
    
    Доступно только для учителей и администраторов
    
    Returns:
        {
            "periodic_tasks": [
                {
                    "name": "release-finished-zoom-accounts",
                    "enabled": true,
                    "last_run_at": "2025-11-15T10:30:00Z",
                    "total_run_count": 145
                }
            ],
            "zoom_accounts": {
                "total": 5,
                "available": 3,
                "in_use": 2,
                "utilization_percent": 40.0
            },
            "lessons": {
                "active_now": 2,
                "today_total": 15,
                "with_zoom": 12,
                "without_zoom": 3
            },
            "health": "healthy"
        }
    """
    
    # Проверка прав (только учителя и админы)
    if request.user.role not in ['teacher', 'admin']:
        return Response({"detail": "Доступ запрещён"}, status=403)
    
    try:
        # 1. Метрики периодических задач
        periodic_tasks_data = []
        periodic_tasks = PeriodicTask.objects.all()
        
        for task in periodic_tasks:
            periodic_tasks_data.append({
                "name": task.name,
                "task": task.task,
                "enabled": task.enabled,
                "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
                "total_run_count": task.total_run_count,
                "schedule": str(task.interval) if task.interval else str(task.crontab)
            })
        
        # 2. Метрики Zoom аккаунтов
        zoom_accounts = ZoomAccount.objects.all()
        total_accounts = zoom_accounts.count()
        available_accounts = sum(1 for acc in zoom_accounts if acc.is_available())
        in_use_count = sum(acc.current_meetings for acc in zoom_accounts)
        max_capacity = sum(acc.max_concurrent_meetings for acc in zoom_accounts)
        
        utilization_percent = (in_use_count / max_capacity * 100) if max_capacity > 0 else 0
        
        zoom_metrics = {
            "total": total_accounts,
            "available": available_accounts,
            "in_use_meetings": in_use_count,
            "max_capacity": max_capacity,
            "utilization_percent": round(utilization_percent, 2)
        }
        
        # 3. Метрики уроков
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Активные уроки (идут сейчас)
        active_lessons = Lesson.objects.filter(
            start_time__lte=now,
            end_time__gte=now
        )
        
        # Уроки за сегодня
        today_lessons = Lesson.objects.filter(
            start_time__gte=today_start,
            start_time__lt=today_end
        )
        
        lessons_metrics = {
            "active_now": active_lessons.count(),
            "today_total": today_lessons.count(),
            "today_with_zoom": today_lessons.exclude(zoom_account__isnull=True).count(),
            "today_without_zoom": today_lessons.filter(zoom_account__isnull=True).count(),
            "active_with_zoom": active_lessons.exclude(zoom_account__isnull=True).count()
        }
        
        # 4. Общий статус здоровья
        health_status = "healthy"
        health_issues = []
        
        # Проверка: есть ли доступные аккаунты
        if available_accounts == 0 and total_accounts > 0:
            health_status = "warning"
            health_issues.append("Нет доступных Zoom аккаунтов")
        
        # Проверка: высокая загрузка (> 80%)
        if utilization_percent > 80:
            health_status = "warning"
            health_issues.append(f"Высокая загрузка Zoom аккаунтов: {utilization_percent}%")
        
        # Проверка: есть ли активные задачи
        active_periodic_tasks = [t for t in periodic_tasks_data if t['enabled']]
        if len(active_periodic_tasks) == 0:
            health_status = "critical"
            health_issues.append("Нет активных периодических задач")
        
        # Собираем ответ
        response_data = {
            "periodic_tasks": periodic_tasks_data,
            "zoom_accounts": zoom_metrics,
            "lessons": lessons_metrics,
            "health": {
                "status": health_status,
                "issues": health_issues
            },
            "timestamp": now.isoformat()
        }
        
        logger.info(f"Celery metrics requested by {request.user.email}")
        return Response(response_data)
    
    except Exception as e:
        logger.error(f"Error getting Celery metrics: {e}")
        return Response(
            {"detail": f"Ошибка получения метрик: {str(e)}"},
            status=500
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_task(request, task_name):
    """
    Вручную запустить Celery задачу
    
    POST /api/celery/trigger/<task_name>/
    
    Доступно только для администраторов
    
    Args:
        task_name: Имя задачи ('release_finished_zoom_accounts', 'send_lesson_reminders')
    
    Returns:
        {
            "task_id": "abc-123-def",
            "status": "pending",
            "message": "Задача запущена"
        }
    """
    
    # Только администраторы
    if request.user.role != 'admin':
        return Response({"detail": "Требуются права администратора"}, status=403)
    
    # Импортируем задачи
    from schedule.tasks import release_finished_zoom_accounts, send_lesson_reminders
    
    task_map = {
        'release_finished_zoom_accounts': release_finished_zoom_accounts,
        'send_lesson_reminders': send_lesson_reminders,
    }
    
    if task_name not in task_map:
        return Response(
            {"detail": f"Неизвестная задача: {task_name}"},
            status=400
        )
    
    try:
        # Запускаем задачу асинхронно
        task = task_map[task_name]
        result = task.delay()
        
        logger.info(f"Task {task_name} manually triggered by {request.user.email}, task_id={result.id}")
        
        return Response({
            "task_id": result.id,
            "task_name": task_name,
            "status": "pending",
            "message": "Задача успешно запущена"
        })
    
    except Exception as e:
        logger.error(f"Error triggering task {task_name}: {e}")
        return Response(
            {"detail": f"Ошибка запуска задачи: {str(e)}"},
            status=500
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_status(request, task_id):
    """
    Проверить статус выполнения задачи
    
    GET /api/celery/status/<task_id>/
    
    Returns:
        {
            "task_id": "abc-123-def",
            "status": "SUCCESS",
            "result": "Released 3 accounts",
            "date_done": "2025-11-15T10:35:00Z"
        }
    """
    
    if request.user.role not in ['teacher', 'admin']:
        return Response({"detail": "Доступ запрещён"}, status=403)
    
    try:
        result = AsyncResult(task_id)
        
        response_data = {
            "task_id": task_id,
            "status": result.status,
            "result": str(result.result) if result.result else None,
        }
        
        if result.date_done:
            response_data["date_done"] = result.date_done.isoformat()
        
        return Response(response_data)
    
    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        return Response(
            {"detail": f"Ошибка получения статуса: {str(e)}"},
            status=500
        )
