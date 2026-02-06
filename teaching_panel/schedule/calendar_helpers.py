"""
Вспомогательные функции для работы с расписанием
"""
from datetime import datetime, timedelta, date, time
from django.utils import timezone
from .models import Lesson, RecurringLesson


def get_week_number(target_date, semester_start_date):
    """
    Определение номера недели относительно начала семестра
    
    Args:
        target_date: дата для проверки
        semester_start_date: дата начала семестра
    
    Returns:
        'UPPER' или 'LOWER' для четных/нечетных недель
    """
    delta = (target_date - semester_start_date).days
    week_number = delta // 7
    
    return 'UPPER' if week_number % 2 == 0 else 'LOWER'


def get_lessons_for_calendar(teacher, start_date, end_date):
    """
    Получение всех уроков для календаря (разовые + сгенерированные из регулярных)
    
    Args:
        teacher: объект CustomUser (преподаватель)
        start_date: начало периода (datetime.date)
        end_date: конец периода (datetime.date)
    
    Returns:
        list: список объектов Lesson и виртуальных уроков (dict)
    """
    calendar_events = []
    
    # 1. Получаем все разовые уроки в диапазоне
    one_time_lessons = Lesson.objects.filter(
        teacher=teacher,
        start_time__date__gte=start_date,
        start_time__date__lte=end_date
    ).select_related('group', 'teacher', 'zoom_account_used')
    
    # Добавляем разовые уроки
    calendar_events.extend(list(one_time_lessons))
    
    # 2. Получаем все регулярные уроки, которые пересекаются с диапазоном
    recurring_lessons = RecurringLesson.objects.filter(
        teacher=teacher,
        start_date__lte=end_date,
        end_date__gte=start_date
    ).select_related('group', 'teacher')
    
    # 3. Генерируем виртуальные события из регулярных уроков
    for recurring in recurring_lessons:
        # Определяем начало генерации (максимум из start_date и recurring.start_date)
        gen_start = max(start_date, recurring.start_date)
        # Определяем конец генерации (минимум из end_date и recurring.end_date)
        gen_end = min(end_date, recurring.end_date)
        
        # Итерируемся по каждому дню в диапазоне
        current_date = gen_start
        while current_date <= gen_end:
            # Проверяем, совпадает ли день недели
            if current_date.weekday() == recurring.day_of_week:
                # Проверяем тип недели (верхняя/нижняя)
                week_type = get_week_number(current_date, recurring.start_date)
                
                if recurring.week_type == 'ALL' or recurring.week_type == week_type:
                    # Создаем виртуальное событие (dict, не сохраняется в БД)
                    # Используем timezone.make_aware() для корректной обработки DST
                    virtual_lesson = {
                        'id': f'recurring_{recurring.id}_{current_date.isoformat()}',
                        'title': recurring.title,
                        'group': recurring.group,
                        'teacher': recurring.teacher,
                        'start_time': timezone.make_aware(
                            datetime.combine(current_date, recurring.start_time),
                            timezone.get_current_timezone()
                        ),
                        'end_time': timezone.make_aware(
                            datetime.combine(current_date, recurring.end_time),
                            timezone.get_current_timezone()
                        ),
                        'topics': recurring.topics,
                        'location': recurring.location,
                        'is_recurring': True,
                        'recurring_lesson_id': recurring.id,
                        # Zoom поля пустые (урок еще не запущен)
                        'zoom_start_url': None,
                        'zoom_join_url': None,
                        'zoom_meeting_id': None,
                    }
                    calendar_events.append(virtual_lesson)
            
            current_date += timedelta(days=1)
    
    return calendar_events


def get_lessons_for_student(student, start_date, end_date):
    """
    Получение всех уроков для студента (по его группам)
    
    Args:
        student: объект CustomUser (студент)
        start_date: начало периода
        end_date: конец периода
    
    Returns:
        list: уроки студента (разовые + сгенерированные регулярные)
    """
    calendar_events = []
    
    # Получаем группы студента
    student_groups = student.enrolled_groups.all()
    
    # Разовые уроки
    one_time_lessons = Lesson.objects.filter(
        group__in=student_groups,
        start_time__date__gte=start_date,
        start_time__date__lte=end_date
    ).select_related('group', 'teacher', 'zoom_account_used')
    
    calendar_events.extend(list(one_time_lessons))
    
    # Регулярные уроки
    recurring_lessons = RecurringLesson.objects.filter(
        group__in=student_groups,
        start_date__lte=end_date,
        end_date__gte=start_date
    ).select_related('group', 'teacher')
    
    # Генерация виртуальных событий
    for recurring in recurring_lessons:
        gen_start = max(start_date, recurring.start_date)
        gen_end = min(end_date, recurring.end_date)
        
        current_date = gen_start
        while current_date <= gen_end:
            if current_date.weekday() == recurring.day_of_week:
                week_type = get_week_number(current_date, recurring.start_date)
                
                if recurring.week_type == 'ALL' or recurring.week_type == week_type:
                    # Используем timezone.make_aware() для корректной обработки DST
                    virtual_lesson = {
                        'id': f'recurring_{recurring.id}_{current_date.isoformat()}',
                        'title': recurring.title,
                        'group': recurring.group,
                        'teacher': recurring.teacher,
                        'start_time': timezone.make_aware(
                            datetime.combine(current_date, recurring.start_time),
                            timezone.get_current_timezone()
                        ),
                        'end_time': timezone.make_aware(
                            datetime.combine(current_date, recurring.end_time),
                            timezone.get_current_timezone()
                        ),
                        'topics': recurring.topics,
                        'location': recurring.location,
                        'is_recurring': True,
                        'recurring_lesson_id': recurring.id,
                        'zoom_start_url': None,
                        'zoom_join_url': None,
                        'zoom_meeting_id': None,
                    }
                    calendar_events.append(virtual_lesson)
            
            current_date += timedelta(days=1)
    
    return calendar_events
