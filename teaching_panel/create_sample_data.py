# Script to create sample data for Teaching Panel
# Run with: python manage.py shell < create_sample_data.py

from django.contrib.auth.models import User
from core.models import Course, Lesson, Assignment
from datetime import datetime, timedelta

print("Creating sample data...")

# Get or create admin user
try:
    teacher = User.objects.get(username='admin')
    print(f"✓ Using existing teacher: {teacher.username}")
except User.DoesNotExist:
    teacher = User.objects.create_user(
        username='admin',
        email='admin@example.com',
        password='admin123',
        first_name='John',
        last_name='Teacher'
    )
    print(f"✓ Created teacher: {teacher.username}")

# Create sample students
students = []
for i in range(1, 4):
    username = f'student{i}'
    try:
        student = User.objects.get(username=username)
    except User.DoesNotExist:
        student = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='student123',
            first_name=f'Student',
            last_name=f'Number {i}'
        )
    students.append(student)
    print(f"✓ Student: {student.username}")

# Create sample courses
courses_data = [
    {
        'title': 'Introduction to Python Programming',
        'description': 'Learn Python from scratch with practical examples and projects.'
    },
    {
        'title': 'Web Development with Django',
        'description': 'Build modern web applications using Django framework.'
    },
    {
        'title': 'React for Beginners',
        'description': 'Master React.js and create interactive user interfaces.'
    }
]

courses = []
for course_data in courses_data:
    course, created = Course.objects.get_or_create(
        title=course_data['title'],
        defaults={
            'description': course_data['description'],
            'teacher': teacher
        }
    )
    # Add students to course
    course.students.set(students)
    courses.append(course)
    status = "Created" if created else "Already exists"
    print(f"✓ Course: {course.title} - {status}")

# Create sample lessons
base_date = datetime.now() + timedelta(days=1)

lessons_data = [
    {'title': 'Introduction and Setup', 'offset_days': 0},
    {'title': 'Basic Concepts', 'offset_days': 2},
    {'title': 'Advanced Topics', 'offset_days': 4},
]

for course in courses:
    for i, lesson_data in enumerate(lessons_data):
        start_time = base_date + timedelta(days=lesson_data['offset_days'], hours=10)
        end_time = start_time + timedelta(hours=2)
        
        lesson, created = Lesson.objects.get_or_create(
            course=course,
            title=lesson_data['title'],
            defaults={
                'description': f'Lesson {i+1} for {course.title}',
                'start_time': start_time,
                'end_time': end_time
            }
        )
        
        # Create assignment for each lesson
        if created:
            assignment, _ = Assignment.objects.get_or_create(
                lesson=lesson,
                title=f'Homework: {lesson.title}',
                defaults={
                    'description': f'Complete the exercises from {lesson.title}',
                    'due_date': end_time + timedelta(days=3),
                    'max_points': 100
                }
            )
            print(f"  ✓ Lesson: {lesson.title} (with assignment)")

print("\n✅ Sample data created successfully!")
print("\n📊 Summary:")
print(f"  - Teachers: 1")
print(f"  - Students: {len(students)}")
print(f"  - Courses: {Course.objects.count()}")
print(f"  - Lessons: {Lesson.objects.count()}")
print(f"  - Assignments: {Assignment.objects.count()}")
print("\n🌐 Open http://127.0.0.1:8000/admin to see the data")
print("🚀 Open http://localhost:3000 to see the frontend")
