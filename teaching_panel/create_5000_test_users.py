"""
Создание 5000 тестовых пользователей для нагрузочного тестирования
Запуск: python manage.py shell < create_5000_test_users.py

Структура:
- 500 учителей (teacher1@loadtest.local ... teacher500@loadtest.local)
- 4500 студентов (student1@loadtest.local ... student4500@loadtest.local)
- 200 групп (по 20-50 студентов в каждой)
- 1000 уроков (распределены по группам)

Пароль для всех: loadtest123
"""
import os
import sys
import random
from datetime import datetime, timedelta

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from schedule.models import Group, Lesson
from django.db import transaction

User = get_user_model()

# Настройки
NUM_TEACHERS = 500
NUM_STUDENTS = 4500
NUM_GROUPS = 200
NUM_LESSONS_PER_GROUP = 5
BATCH_SIZE = 100

print("=" * 60)
print("Creating 5000 test users for load testing")
print("=" * 60)

# =============================================================================
# STEP 1: Create Teachers
# =============================================================================
print(f"\n📚 Step 1: Creating {NUM_TEACHERS} teachers...")

existing_teachers = set(
    User.objects.filter(
        email__startswith="teacher", 
        email__endswith="@loadtest.local"
    ).values_list('email', flat=True)
)

teachers_to_create = []
for i in range(1, NUM_TEACHERS + 1):
    email = f"teacher{i}@loadtest.local"
    if email not in existing_teachers:
        teachers_to_create.append(User(
            email=email,
            role="teacher",
            first_name=f"Учитель",
            last_name=f"Тестовый-{i}",
            is_active=True
        ))
    
    if len(teachers_to_create) >= BATCH_SIZE:
        with transaction.atomic():
            for u in teachers_to_create:
                u.set_password("loadtest123")
            User.objects.bulk_create(teachers_to_create, ignore_conflicts=True)
        print(f"  Created batch... ({i}/{NUM_TEACHERS})")
        teachers_to_create = []

# Остаток
if teachers_to_create:
    with transaction.atomic():
        for u in teachers_to_create:
            u.set_password("loadtest123")
        User.objects.bulk_create(teachers_to_create, ignore_conflicts=True)

teacher_count = User.objects.filter(
    email__startswith="teacher",
    email__endswith="@loadtest.local"
).count()
print(f"✅ Teachers: {teacher_count}")

# =============================================================================
# STEP 2: Create Students
# =============================================================================
print(f"\n📚 Step 2: Creating {NUM_STUDENTS} students...")

existing_students = set(
    User.objects.filter(
        email__startswith="student",
        email__endswith="@loadtest.local"
    ).values_list('email', flat=True)
)

students_to_create = []
for i in range(1, NUM_STUDENTS + 1):
    email = f"student{i}@loadtest.local"
    if email not in existing_students:
        students_to_create.append(User(
            email=email,
            role="student",
            first_name=f"Студент",
            last_name=f"Тестовый-{i}",
            is_active=True
        ))
    
    if len(students_to_create) >= BATCH_SIZE:
        with transaction.atomic():
            for u in students_to_create:
                u.set_password("loadtest123")
            User.objects.bulk_create(students_to_create, ignore_conflicts=True)
        print(f"  Created batch... ({i}/{NUM_STUDENTS})")
        students_to_create = []

# Остаток
if students_to_create:
    with transaction.atomic():
        for u in students_to_create:
            u.set_password("loadtest123")
        User.objects.bulk_create(students_to_create, ignore_conflicts=True)

student_count = User.objects.filter(
    email__startswith="student",
    email__endswith="@loadtest.local"
).count()
print(f"✅ Students: {student_count}")

# =============================================================================
# STEP 3: Create Groups
# =============================================================================
print(f"\n📚 Step 3: Creating {NUM_GROUPS} groups...")

teachers = list(User.objects.filter(
    email__startswith="teacher",
    email__endswith="@loadtest.local"
))

students = list(User.objects.filter(
    email__startswith="student",
    email__endswith="@loadtest.local"
))

existing_groups = set(Group.objects.filter(
    name__startswith="LoadTest_"
).values_list('name', flat=True))

groups_created = 0
for i in range(1, NUM_GROUPS + 1):
    group_name = f"LoadTest_Group_{i}"
    if group_name in existing_groups:
        continue
    
    teacher = teachers[(i - 1) % len(teachers)]
    
    group = Group.objects.create(
        name=group_name,
        teacher=teacher,
        description=f"Load test group #{i}"
    )
    
    # Добавляем 20-50 случайных студентов
    num_students = random.randint(20, 50)
    sample_students = random.sample(students, min(num_students, len(students)))
    group.students.set(sample_students)
    
    groups_created += 1
    
    if groups_created % 50 == 0:
        print(f"  Created {groups_created}/{NUM_GROUPS} groups...")

group_count = Group.objects.filter(name__startswith="LoadTest_").count()
print(f"✅ Groups: {group_count}")

# =============================================================================
# STEP 4: Create Lessons
# =============================================================================
print(f"\n📚 Step 4: Creating lessons...")

groups = list(Group.objects.filter(name__startswith="LoadTest_"))

existing_lessons = Lesson.objects.filter(
    title__startswith="LoadTest_Lesson_"
).count()

if existing_lessons > 0:
    print(f"  Found {existing_lessons} existing load test lessons, skipping...")
else:
    lessons_to_create = []
    base_date = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    for group in groups:
        for day_offset in range(NUM_LESSONS_PER_GROUP):
            lesson_date = base_date + timedelta(days=day_offset)
            
            lessons_to_create.append(Lesson(
                title=f"LoadTest_Lesson_{group.id}_{day_offset}",
                group=group,
                teacher=group.teacher,
                start_time=lesson_date,
                end_time=lesson_date + timedelta(hours=1, minutes=30),
                topics="Load testing lesson",
                is_quick_lesson=False
            ))
    
    # Bulk create
    LESSON_BATCH = 500
    for i in range(0, len(lessons_to_create), LESSON_BATCH):
        batch = lessons_to_create[i:i + LESSON_BATCH]
        Lesson.objects.bulk_create(batch, ignore_conflicts=True)
        print(f"  Created lessons batch {i + len(batch)}/{len(lessons_to_create)}")

lesson_count = Lesson.objects.filter(title__startswith="LoadTest_Lesson_").count()
print(f"✅ Lessons: {lesson_count}")

# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

total_users = User.objects.count()
total_teachers = User.objects.filter(role="teacher").count()
total_students = User.objects.filter(role="student").count()
total_groups = Group.objects.count()
total_lessons = Lesson.objects.count()

print(f"""
📊 Database Statistics:
   Total Users:    {total_users}
   - Teachers:     {total_teachers}
   - Students:     {total_students}
   
   Total Groups:   {total_groups}
   Total Lessons:  {total_lessons}

🔐 Test Credentials:
   Email pattern:  teacher{{1-500}}@loadtest.local
                   student{{1-4500}}@loadtest.local
   Password:       loadtest123

🚀 Ready for load testing!
   Run: locust -f locustfile.py --host=http://127.0.0.1:8000
""")
