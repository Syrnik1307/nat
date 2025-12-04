#!/usr/bin/env python3
"""
Скрипт для создания тестовых данных для системы посещаемости и рейтинга
Запускать на продакшн сервере через manage.py shell
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from schedule.models import Group, Lesson
from accounts.models import AttendanceRecord, UserRating

User = get_user_model()

def create_test_data():
    """Создает полный набор тестовых данных"""
    
    print("=" * 60)
    print(" Создание тестовых данных для системы посещаемости")
    print("=" * 60)
    
    # 1. Найти или создать учителя
    print("\n1. Поиск учителя...")
    try:
        teacher = User.objects.filter(role='teacher').first()
        if not teacher:
            print("   Создаю нового учителя...")
            teacher = User.objects.create_user(
                email='test.teacher@attendance.com',
                password='TestPass123!',
                role='teacher',
                first_name='Тестовый',
                last_name='Учитель'
            )
            print(f"   ✓ Создан учитель: {teacher.email}")
        else:
            print(f"   ✓ Используется учитель: {teacher.email} (ID={teacher.id})")
    except Exception as e:
        print(f"   ✗ Ошибка при создании учителя: {e}")
        return
    
    # 2. Создать группу с тестовыми студентами
    print("\n2. Создание тестовой группы...")
    try:
        group = Group.objects.create(
            name=f"Тестовая группа {datetime.now().strftime('%H:%M')}",
            teacher=teacher,
            description="Группа для тестирования системы посещаемости"
        )
        print(f"   ✓ Создана группа: {group.name} (ID={group.id})")
    except Exception as e:
        print(f"   ✗ Ошибка при создании группы: {e}")
        return
    
    # 3. Создать тестовых студентов
    print("\n3. Создание тестовых студентов...")
    students = []
    student_names = [
        ("Иван", "Иванов"),
        ("Мария", "Петрова"),
        ("Алексей", "Сидоров"),
        ("Анна", "Кузнецова"),
        ("Дмитрий", "Смирнов"),
    ]
    
    for first_name, last_name in student_names:
        try:
            email = f"{first_name.lower()}.{last_name.lower()}@test.student.com"
            student, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'role': 'student',
                    'first_name': first_name,
                    'last_name': last_name,
                    'password': User.objects.make_random_password()
                }
            )
            if created:
                student.set_password('StudentPass123!')
                student.save()
            
            group.students.add(student)
            students.append(student)
            print(f"   ✓ {'Создан' if created else 'Добавлен'} студент: {first_name} {last_name}")
        except Exception as e:
            print(f"   ✗ Ошибка при создании студента {first_name}: {e}")
    
    # 4. Создать уроки за последние 2 недели
    print("\n4. Создание уроков...")
    lessons = []
    lesson_topics = [
        "Введение в Python",
        "Переменные и типы данных",
        "Условные операторы",
        "Циклы for и while",
        "Функции",
        "Списки и кортежи",
        "Словари и множества",
        "Работа с файлами",
        "Исключения",
        "ООП: Классы и объекты"
    ]
    
    now = timezone.now()
    for i in range(10):
        try:
            lesson_date = now - timedelta(days=14-i, hours=10)
            lesson_end = lesson_date + timedelta(minutes=90)
            lesson = Lesson.objects.create(
                group=group,
                title=lesson_topics[i],
                start_time=lesson_date,
                end_time=lesson_end,
                teacher=teacher
            )
            lessons.append(lesson)
            print(f"   ✓ Создан урок {i+1}: {lesson.title} ({lesson_date.strftime('%Y-%m-%d')})")
        except Exception as e:
            print(f"   ✗ Ошибка при создании урока {i+1}: {e}")
    
    # 5. Создать записи посещаемости
    print("\n5. Создание записей посещаемости...")
    import random
    
    statuses = ['attended', 'absent', 'watched_recording']
    attendance_created = 0
    
    for lesson in lessons:
        for student in students:
            try:
                # Генерируем случайный статус с весами:
                # 70% - присутствовал, 20% - отсутствовал, 10% - посмотрел запись
                status = random.choices(
                    statuses,
                    weights=[70, 20, 10],
                    k=1
                )[0]
                
                AttendanceRecord.objects.create(
                    lesson=lesson,
                    student=student,
                    status=status,
                    auto_recorded=False,
                    recorded_at=lesson.start_time
                )
                attendance_created += 1
            except Exception as e:
                print(f"   ⚠ Пропуск записи для {student.first_name}: {e}")
    
    print(f"   ✓ Создано записей посещаемости: {attendance_created}")
    
    # 6. Пересчитать рейтинги
    print("\n6. Пересчет рейтингов студентов...")
    from accounts.attendance_service import RatingService
    
    rating_service = RatingService()
    ratings_created = 0
    
    for student in students:
        try:
            rating_service.recalculate_student_rating(
                student_id=student.id,
                group_id=group.id
            )
            ratings_created += 1
            print(f"   ✓ Рейтинг пересчитан для: {student.first_name} {student.last_name}")
        except Exception as e:
            print(f"   ✗ Ошибка при пересчете рейтинга {student.first_name}: {e}")
    
    print(f"   ✓ Пересчитано рейтингов: {ratings_created}")
    
    # 7. Вывести итоговую статистику
    print("\n" + "=" * 60)
    print(" ИТОГИ")
    print("=" * 60)
    print(f"✓ Учитель: {teacher.email} (ID={teacher.id})")
    print(f"✓ Группа: {group.name} (ID={group.id})")
    print(f"✓ Студентов: {len(students)}")
    print(f"✓ Уроков: {len(lessons)}")
    print(f"✓ Записей посещаемости: {attendance_created}")
    print(f"✓ Рейтингов: {ratings_created}")
    print()
    print("=" * 60)
    print(" ДАННЫЕ ДЛЯ ВХОДА")
    print("=" * 60)
    print(f"Учитель:")
    print(f"  Email: {teacher.email}")
    print(f"  Password: (используйте существующий или сбросьте)")
    print()
    print(f"Студенты:")
    for student in students:
        print(f"  Email: {student.email}")
        print(f"  Password: StudentPass123!")
    print()
    print("=" * 60)
    print(" ССЫЛКИ ДЛЯ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"API Endpoints:")
    print(f"  Список групп: GET /api/groups/")
    print(f"  Журнал посещений: GET /api/groups/{group.id}/attendance-log/")
    print(f"  Рейтинг группы: GET /api/groups/{group.id}/rating/")
    print(f"  Отчет группы: GET /api/groups/{group.id}/report/")
    print()

if __name__ == "__main__":
    create_test_data()
