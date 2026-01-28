"""
API views для управления квотами хранилища (только для админов)
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Sum, Q, F
from django.shortcuts import get_object_or_404

from .models import TeacherStorageQuota, LessonRecording
from .serializers import TeacherStorageQuotaSerializer
from accounts.models import CustomUser


class QuotaPagination(PageNumberPagination):
    """Пагинация для списка квот"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def storage_quotas_list(request):
    """
    Список квот хранилища всех преподавателей (только для админа)
    
    Query параметры:
    - search: поиск по имени/email
    - exceeded: фильтр по превышению квоты (true/false)
    - warning: фильтр по предупреждениям (true/false)
    - sort: сортировка (usage_percent, used_bytes, total_quota_bytes)
    """
    # Проверка прав админа
    if request.user.role != 'admin':
        return Response(
            {'error': 'Доступ запрещен. Только для администраторов.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Базовый запрос
    quotas = TeacherStorageQuota.objects.select_related('teacher').all()
    
    # Поиск
    search = request.query_params.get('search', '').strip()
    if search:
        quotas = quotas.filter(
            Q(teacher__email__icontains=search) |
            Q(teacher__first_name__icontains=search) |
            Q(teacher__last_name__icontains=search)
        )
    
    # Фильтры
    exceeded = request.query_params.get('exceeded')
    if exceeded is not None:
        exceeded_bool = exceeded.lower() == 'true'
        quotas = quotas.filter(quota_exceeded=exceeded_bool)
    
    warning = request.query_params.get('warning')
    if warning is not None:
        warning_bool = warning.lower() == 'true'
        quotas = quotas.filter(warning_sent=warning_bool)
    
    # Сортировка
    sort_by = request.query_params.get('sort', '-used_bytes')
    allowed_sorts = ['usage_percent', 'used_bytes', 'total_quota_bytes', '-used_bytes', '-total_quota_bytes']
    
    if sort_by == 'usage_percent':
        # Сортировка по проценту использования (вычисляемое поле)
        quotas = sorted(
            quotas,
            key=lambda q: q.usage_percent,
            reverse=False
        )
        use_pagination = False
    elif sort_by in allowed_sorts:
        quotas = quotas.order_by(sort_by)
        use_pagination = True
    else:
        quotas = quotas.order_by('-used_bytes')
        use_pagination = True
    
    # Пагинация
    if use_pagination:
        paginator = QuotaPagination()
        page = paginator.paginate_queryset(quotas, request)
        if page is not None:
            serializer = TeacherStorageQuotaSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
    
    serializer = TeacherStorageQuotaSerializer(quotas, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def storage_quota_detail(request, quota_id):
    """
    Детали квоты конкретного преподавателя
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Доступ запрещен'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    quota = get_object_or_404(TeacherStorageQuota, id=quota_id)
    serializer = TeacherStorageQuotaSerializer(quota)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def increase_quota(request, quota_id):
    """
    Увеличение квоты преподавателя
    
    Body:
    {
        "additional_gb": 10
    }
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Доступ запрещен'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    quota = get_object_or_404(TeacherStorageQuota, id=quota_id)
    
    additional_gb = request.data.get('additional_gb')
    if not additional_gb:
        return Response(
            {'error': 'Укажите additional_gb'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        additional_gb = float(additional_gb)
        if additional_gb <= 0:
            return Response(
                {'error': 'additional_gb должен быть положительным числом'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {'error': 'Неверный формат additional_gb'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Увеличиваем квоту
    quota.increase_quota(additional_gb)
    
    serializer = TeacherStorageQuotaSerializer(quota)
    return Response({
        'message': f'Квота увеличена на {additional_gb} ГБ',
        'quota': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_quota_warnings(request, quota_id):
    """
    Сброс предупреждений для квоты
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Доступ запрещен'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    quota = get_object_or_404(TeacherStorageQuota, id=quota_id)
    quota.warning_sent = False
    quota.last_warning_at = None
    quota.save()
    
    serializer = TeacherStorageQuotaSerializer(quota)
    return Response({
        'message': 'Предупреждения сброшены',
        'quota': serializer.data
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_quota(request, quota_id):
    """
    Установка новой квоты преподавателя (абсолютное значение)
    
    Body:
    {
        "total_gb": 10
    }
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Доступ запрещен'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    quota = get_object_or_404(TeacherStorageQuota, id=quota_id)
    
    total_gb = request.data.get('total_gb')
    if total_gb is None:
        return Response(
            {'error': 'Укажите total_gb'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        total_gb = float(total_gb)
        if total_gb <= 0:
            return Response(
                {'error': 'total_gb должен быть положительным числом'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {'error': 'Неверный формат total_gb'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Устанавливаем новую квоту
    quota.total_quota_bytes = int(total_gb * (1024 ** 3))
    
    # Пересчитываем флаг превышения
    quota.quota_exceeded = quota.used_bytes > quota.total_quota_bytes
    quota.save()
    
    serializer = TeacherStorageQuotaSerializer(quota)
    return Response({
        'message': f'Квота установлена: {total_gb} ГБ',
        'quota': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def storage_statistics(request):
    """
    Общая статистика по хранилищу
    
    Возвращает:
    - total_teachers: общее количество преподавателей
    - total_quota_gb: суммарная квота в ГБ
    - total_used_gb: суммарно использовано ГБ
    - total_available_gb: суммарно доступно ГБ
    - average_usage_percent: средний процент использования
    - exceeded_count: количество превышений
    - warning_count: количество предупреждений
    - total_recordings: общее количество записей
    - top_users: топ-5 пользователей по использованию
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Доступ запрещен'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    quotas = TeacherStorageQuota.objects.all()
    
    # Агрегация
    aggregates = quotas.aggregate(
        total_quota=Sum('total_quota_bytes'),
        total_used=Sum('used_bytes'),
        total_recordings=Sum('recordings_count')
    )
    
    total_quota_gb = (aggregates['total_quota'] or 0) / (1024 ** 3)
    total_used_gb = (aggregates['total_used'] or 0) / (1024 ** 3)
    total_available_gb = total_quota_gb - total_used_gb
    
    # Процент использования
    if total_quota_gb > 0:
        average_usage_percent = (total_used_gb / total_quota_gb) * 100
    else:
        average_usage_percent = 0
    
    # Счетчики
    exceeded_count = quotas.filter(quota_exceeded=True).count()
    warning_count = quotas.filter(warning_sent=True).count()
    total_teachers = quotas.count()
    
    # Топ-5 по использованию
    top_users = quotas.select_related('teacher').order_by('-used_bytes')[:5]
    top_users_data = [
        {
            'teacher_name': quota.teacher.get_full_name() or quota.teacher.email,
            'teacher_id': quota.teacher.id,
            'used_gb': round(quota.used_gb, 2),
            'total_gb': round(quota.total_gb, 2),
            'usage_percent': round(quota.usage_percent, 1)
        }
        for quota in top_users
    ]
    
    return Response({
        'total_teachers': total_teachers,
        'total_quota_gb': round(total_quota_gb, 2),
        'total_used_gb': round(total_used_gb, 2),
        'total_available_gb': round(total_available_gb, 2),
        'average_usage_percent': round(average_usage_percent, 1),
        'exceeded_count': exceeded_count,
        'warning_count': warning_count,
        'total_recordings': aggregates['total_recordings'] or 0,
        'top_users': top_users_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_recordings_list(request, teacher_id):
    """
    Список записей конкретного преподавателя (для админа)
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Доступ запрещен'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    teacher = get_object_or_404(CustomUser, id=teacher_id, role='teacher')
    recordings = LessonRecording.objects.filter(
        lesson__group__teacher=teacher
    ).select_related('lesson', 'lesson__group').order_by('-created_at')
    
    # Пагинация
    paginator = QuotaPagination()
    page = paginator.paginate_queryset(recordings, request)
    
    recordings_data = [
        {
            'id': rec.id,
            'lesson_title': rec.lesson.title,
            'group_name': rec.lesson.group.name,
            'file_size_mb': round(rec.file_size / (1024 ** 2), 2) if rec.file_size else 0,
            'status': rec.status,
            'created_at': rec.created_at,
            'views_count': rec.views_count
        }
        for rec in (page if page else recordings)
    ]
    
    if page:
        return paginator.get_paginated_response(recordings_data)
    
    return Response(recordings_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_teacher_quota(request):
    """
    Создание квоты для преподавателя (если еще нет)
    
    Body:
    {
        "teacher_id": 123,
        "total_gb": 10
    }
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Доступ запрещен'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    teacher_id = request.data.get('teacher_id')
    total_gb = request.data.get('total_gb', 5)
    
    if not teacher_id:
        return Response(
            {'error': 'Укажите teacher_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    teacher = get_object_or_404(CustomUser, id=teacher_id, role='teacher')
    
    # Проверяем существование квоты
    if hasattr(teacher, 'storage_quota'):
        return Response(
            {'error': 'Квота для этого преподавателя уже существует'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Создаем квоту
    quota = TeacherStorageQuota.objects.create(
        teacher=teacher,
        total_quota_bytes=int(total_gb * (1024 ** 3))
    )
    
    serializer = TeacherStorageQuotaSerializer(quota)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ==================== Google Drive Storage Stats ====================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gdrive_stats_all_teachers(request):
    """
    Статистика Google Drive по всем учителям (только для админа)
    GET /api/storage/gdrive-stats/all/
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Доступ запрещен'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Проверяем, что Google Drive включен
        from django.conf import settings
        if not settings.USE_GDRIVE_STORAGE or not settings.GDRIVE_ROOT_FOLDER_ID:
            return Response({
                'error': 'Google Drive storage is not configured',
                'teachers': [],
                'summary': {
                    'total_teachers': 0,
                    'total_size': 0,
                    'total_size_gb': 0,
                    'total_files': 0
                }
            })
        
        from schedule.gdrive_utils import get_gdrive_manager
        gdrive = get_gdrive_manager()
        
        # Получаем всех учителей
        teachers = CustomUser.objects.filter(role='teacher')
        
        stats_list = []
        total_size = 0
        total_files = 0
        
        for teacher in teachers:
            try:
                teacher_stats = gdrive.get_teacher_storage_stats(teacher)
                
                stats_list.append({
                    'teacher_id': teacher.id,
                    'teacher_name': f"{teacher.first_name} {teacher.last_name}",
                    'teacher_email': teacher.email,
                    'total_size': teacher_stats['total_size'],
                    'total_size_mb': round(teacher_stats['total_size'] / (1024 * 1024), 2),
                    'total_size_gb': round(teacher_stats['total_size'] / (1024 * 1024 * 1024), 2),
                    'total_files': teacher_stats['total_files'],
                    'recordings': {
                        'size_mb': round(teacher_stats['recordings']['total_size'] / (1024 * 1024), 2),
                        'files': teacher_stats['recordings']['file_count']
                    },
                    'homework': {
                        'size_mb': round(teacher_stats['homework']['total_size'] / (1024 * 1024), 2),
                        'files': teacher_stats['homework']['file_count']
                    },
                    'materials': {
                        'size_mb': round(teacher_stats['materials']['total_size'] / (1024 * 1024), 2),
                        'files': teacher_stats['materials']['file_count']
                    },
                    'students_data': {
                        'size_mb': round(teacher_stats['students']['total_size'] / (1024 * 1024), 2),
                        'files': teacher_stats['students']['file_count']
                    }
                })
                
                total_size += teacher_stats['total_size']
                total_files += teacher_stats['total_files']
                
            except Exception as e:
                logger.error(f"Failed to get stats for teacher {teacher.id}: {e}", exc_info=True)
                continue
        
        # Сортировка по размеру
        stats_list.sort(key=lambda x: x['total_size'], reverse=True)
        
        # Получаем квоту Google Drive
        try:
            drive_quota = gdrive.get_drive_quota()
        except Exception as e:
            logger.error(f"Failed to get drive quota: {e}")
            drive_quota = {'limit_gb': 0, 'usage_gb': 0, 'free_gb': 0, 'usage_percent': 0}
        
        return Response({
            'teachers': stats_list,
            'summary': {
                'total_teachers': len(stats_list),
                'total_size': total_size,
                'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2) if total_size > 0 else 0,
                'total_files': total_files
            },
            'drive_quota': drive_quota
        })
        
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f'Failed to retrieve storage statistics: {str(e)}', exc_info=True)
        
        return Response(
            {'error': f'Failed to retrieve storage statistics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gdrive_stats_my_storage(request):
    """
    Статистика Google Drive текущего учителя
    GET /api/storage/gdrive-stats/my/
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только преподаватели могут просматривать статистику'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from schedule.gdrive_utils import get_gdrive_manager
        
        gdrive = get_gdrive_manager()
        stats = gdrive.get_teacher_storage_stats(request.user)
        
        return Response({
            'teacher_id': request.user.id,
            'teacher_name': f"{request.user.first_name} {request.user.last_name}",
            'total_size': stats['total_size'],
            'total_size_mb': round(stats['total_size'] / (1024 * 1024), 2),
            'total_size_gb': round(stats['total_size'] / (1024 * 1024 * 1024), 2),
            'total_files': stats['total_files'],
            'total_folders': stats['total_folders'],
            'breakdown': {
                'recordings': {
                    'size_mb': round(stats['recordings']['total_size'] / (1024 * 1024), 2),
                    'files': stats['recordings']['file_count'],
                    'percentage': round((stats['recordings']['total_size'] / stats['total_size'] * 100) if stats['total_size'] > 0 else 0, 1)
                },
                'homework': {
                    'size_mb': round(stats['homework']['total_size'] / (1024 * 1024), 2),
                    'files': stats['homework']['file_count'],
                    'percentage': round((stats['homework']['total_size'] / stats['total_size'] * 100) if stats['total_size'] > 0 else 0, 1)
                },
                'materials': {
                    'size_mb': round(stats['materials']['total_size'] / (1024 * 1024), 2),
                    'files': stats['materials']['file_count'],
                    'percentage': round((stats['materials']['total_size'] / stats['total_size'] * 100) if stats['total_size'] > 0 else 0, 1)
                },
                'students_data': {
                    'size_mb': round(stats['students']['total_size'] / (1024 * 1024), 2),
                    'files': stats['students']['file_count'],
                    'percentage': round((stats['students']['total_size'] / stats['total_size'] * 100) if stats['total_size'] > 0 else 0, 1)
                }
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve storage statistics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
