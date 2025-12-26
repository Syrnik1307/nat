"""Тест API журнала посещений с виртуальными уроками"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.test import RequestFactory
from schedule.models import Group, RecurringLesson, Lesson
from accounts.attendance_views import GroupAttendanceLogViewSet
from accounts.models import CustomUser

print("=" * 60)
print("Тест API /groups/{id}/attendance-log/")
print("=" * 60)

# Найти группу с регулярными уроками
groups = Group.objects.filter(recurring_lessons__isnull=False).distinct()

if not groups.exists():
    print("Нет групп с регулярными уроками!")
else:
    group = groups.first()
    print(f"\nТестируем группу: {group.id} - {group.name}")
    print(f"Учитель: {group.teacher}")
    
    # Получаем учителя
    teacher = group.teacher
    
    # Симулируем API запрос
    factory = RequestFactory()
    request = factory.get(f'/api/groups/{group.id}/attendance-log/')
    request.user = teacher
    
    view = GroupAttendanceLogViewSet()
    response = view.list(request, group_id=group.id)
    
    print(f"\nСтатус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.data
        lessons = data.get('lessons', [])
        students = data.get('students', [])
        
        print(f"Уроков в ответе: {len(lessons)}")
        print(f"Учеников: {len(students)}")
        
        # Показать уроки
        print("\nУроки:")
        for i, lesson in enumerate(lessons[:15]):
            is_recurring = '(виртуальный)' if isinstance(lesson.get('id'), str) else '(реальный)'
            title = lesson.get('title', 'Без названия')
            start = lesson.get('start_time', 'N/A')
            if hasattr(start, 'strftime'):
                start = start.strftime('%Y-%m-%d %H:%M')
            print(f"  {i+1}. {lesson.get('id')} | {start} | {title} {is_recurring}")
        
        if len(lessons) > 15:
            print(f"  ... и ещё {len(lessons) - 15}")
            
        # Статистика
        meta = data.get('meta', {})
        stats = meta.get('stats', {})
        print(f"\nСтатистика:")
        print(f"  Всего уроков: {stats.get('lessons_count')}")
        print(f"  Учеников: {stats.get('students_count')}")
        print(f"  Средняя посещаемость: {stats.get('avg_attendance_percent')}%")
    else:
        print(f"Ошибка: {response.data}")

print("\n" + "=" * 60)
print("Тест завершён")
