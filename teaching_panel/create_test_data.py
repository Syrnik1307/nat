"""
Скрипт для создания тестовых данных
Запускать: python manage.py shell < create_test_data.py
"""
import os
import django
from datetime import datetime, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
from schedule.models import Group, Lesson, Attendance

# Создаем преподавателей
print("Создание преподавателей...")
teacher1 = CustomUser.objects.create_user(
    email='teacher1@example.com',
    password='teacher123',
    first_name='Иван',
    last_name='Петров',
    role='teacher'
)

teacher2 = CustomUser.objects.create_user(
    email='teacher2@example.com',
    password='teacher123',
    first_name='Мария',
    last_name='Иванова',
    role='teacher'
)

# Создаем студентов
print("Создание студентов...")
students = []
student_names = [
    ('Алексей', 'Смирнов'),
    ('Анна', 'Кузнецова'),
    ('Дмитрий', 'Попов'),
    ('Елена', 'Васильева'),
    ('Сергей', 'Соколов'),
]

for idx, (first, last) in enumerate(student_names, 1):
    student = CustomUser.objects.create_user(
        email=f'student{idx}@example.com',
        password='student123',
        first_name=first,
        last_name=last,
        role='student',
        agreed_to_marketing=(idx % 2 == 0)  # Четные согласились
    )
    students.append(student)

# Создаем группы
print("Создание групп...")
group1 = Group.objects.create(
    name='Python для начинающих',
    teacher=teacher1,
    description='Основы программирования на Python'
)
group1.students.add(students[0], students[1], students[2])

group2 = Group.objects.create(
    name='Веб-разработка с Django',
    teacher=teacher1,
    description='Создание веб-приложений с использованием Django'
)
group2.students.add(students[1], students[2], students[3])

group3 = Group.objects.create(
    name='React и современный фронтенд',
    teacher=teacher2,
    description='Разработка интерфейсов с React.js'
)
group3.students.add(students[2], students[3], students[4])

# Создаем занятия
print("Создание занятий...")
now = timezone.now()

# Занятия для группы 1 (прошлые и будущие)
lessons_data = [
    {
        'title': 'Введение в Python',
        'group': group1,
        'teacher': teacher1,
        'start_time': now - timedelta(days=7, hours=2),
        'end_time': now - timedelta(days=7, hours=0.5),
        'topics': 'Переменные, типы данных, операторы',
        'location': 'Аудитория 101',
    },
    {
        'title': 'Функции и модули',
        'group': group1,
        'teacher': teacher1,
        'start_time': now - timedelta(days=5, hours=2),
        'end_time': now - timedelta(days=5, hours=0.5),
        'topics': 'Определение функций, импорт модулей, пространства имен',
        'location': 'Аудитория 101',
    },
    {
        'title': 'ООП в Python',
        'group': group1,
        'teacher': teacher1,
        'start_time': now + timedelta(days=2, hours=10),
        'end_time': now + timedelta(days=2, hours=11, minutes=30),
        'topics': 'Классы, объекты, наследование, полиморфизм',
        'location': 'Онлайн',
    },
]

for lesson_data in lessons_data:
    lesson = Lesson.objects.create(**lesson_data)
    # Отмечаем посещаемость для прошлых уроков
    if lesson.start_time < now:
        for student in lesson.group.students.all():
            # 80% шанс присутствия
            import random
            status = random.choice(['present', 'present', 'present', 'present', 'absent'])
            Attendance.objects.create(
                lesson=lesson,
                student=student,
                status=status
            )

# Занятия для группы 2
lessons_data_2 = [
    {
        'title': 'Django: модели и БД',
        'group': group2,
        'teacher': teacher1,
        'start_time': now + timedelta(days=1, hours=14),
        'end_time': now + timedelta(days=1, hours=15, minutes=30),
        'topics': 'ORM, миграции, запросы к БД',
        'location': 'Аудитория 202',
    },
    {
        'title': 'Django: представления и шаблоны',
        'group': group2,
        'teacher': teacher1,
        'start_time': now + timedelta(days=3, hours=14),
        'end_time': now + timedelta(days=3, hours=15, minutes=30),
        'topics': 'Class-based views, Django Templates, статические файлы',
        'location': 'Аудитория 202',
    },
]

for lesson_data in lessons_data_2:
    Lesson.objects.create(**lesson_data)

# Занятия для группы 3
lessons_data_3 = [
    {
        'title': 'React: компоненты и props',
        'group': group3,
        'teacher': teacher2,
        'start_time': now + timedelta(days=1, hours=16),
        'end_time': now + timedelta(days=1, hours=17, minutes=30),
        'topics': 'Функциональные компоненты, передача пропсов, композиция',
        'location': 'Онлайн',
        'zoom_meeting_id': '123456789',
        'zoom_join_url': 'https://zoom.us/j/123456789',
    },
    {
        'title': 'React: состояние и хуки',
        'group': group3,
        'teacher': teacher2,
        'start_time': now + timedelta(days=4, hours=16),
        'end_time': now + timedelta(days=4, hours=17, minutes=30),
        'topics': 'useState, useEffect, useContext',
        'location': 'Онлайн',
    },
]

for lesson_data in lessons_data_3:
    Lesson.objects.create(**lesson_data)

print("\n✓ Тестовые данные успешно созданы!")
print(f"  - Преподавателей: {CustomUser.objects.filter(role='teacher').count()}")
print(f"  - Студентов: {CustomUser.objects.filter(role='student').count()}")
print(f"  - Групп: {Group.objects.count()}")
print(f"  - Занятий: {Lesson.objects.count()}")
print(f"  - Записей посещаемости: {Attendance.objects.count()}")
print("\nУчетные данные:")
print("  Админ: admin@example.com / admin123")
print("  Преподаватели: teacher1@example.com, teacher2@example.com / teacher123")
print("  Студенты: student1-5@example.com / student123")
