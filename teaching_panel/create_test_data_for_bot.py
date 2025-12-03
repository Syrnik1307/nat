"""
Скрипт для создания тестовых данных для Telegram бота.

Usage:
    cd teaching_panel
    python create_test_data_for_bot.py
"""
import os
import django
import sys
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from schedule.models import Group, Lesson
from homework.models import Homework, Question
from accounts.models import NotificationSettings

User = get_user_model()


def create_test_data():
    print("🔧 Creating test data for Telegram bot testing...\n")
    
    # 1. Create teacher
    teacher_email = "teacher.bot@test.com"
    teacher, teacher_created = User.objects.get_or_create(
        email=teacher_email,
        defaults={
            'first_name': 'Иван',
            'last_name': 'Учителев',
            'role': 'teacher',
            'is_active': True,
        }
    )
    if teacher_created:
        teacher.set_password('test123')
        teacher.save()
        print(f"✅ Created teacher: {teacher.email} (password: test123)")
    else:
        print(f"✅ Teacher exists: {teacher.email}")
    
    # Enable notifications
    settings, _ = NotificationSettings.objects.get_or_create(user=teacher)
    settings.telegram_enabled = True
    settings.notify_homework_submitted = True
    settings.save()
    
    # 2. Create student
    student_email = "student.bot@test.com"
    student, student_created = User.objects.get_or_create(
        email=student_email,
        defaults={
            'first_name': 'Петр',
            'last_name': 'Студентов',
            'role': 'student',
            'is_active': True,
        }
    )
    if student_created:
        student.set_password('test123')
        student.save()
        print(f"✅ Created student: {student.email} (password: test123)")
    else:
        print(f"✅ Student exists: {student.email}")
    
    # Enable notifications
    settings, _ = NotificationSettings.objects.get_or_create(user=student)
    settings.telegram_enabled = True
    settings.notify_new_homework = True
    settings.notify_homework_graded = True
    settings.save()
    
    # 3. Create group
    group, group_created = Group.objects.get_or_create(
        name="Тестовая группа для бота",
        defaults={
            'teacher': teacher,
            'description': 'Группа для тестирования Telegram уведомлений',
        }
    )
    if group_created or not group.invite_code:
        group.generate_invite_code()
        print(f"✅ Created group: {group.name} (invite_code: {group.invite_code})")
    else:
        print(f"✅ Group exists: {group.name} (invite_code: {group.invite_code})")
    
    # Add student to group
    if student not in group.students.all():
        group.students.add(student)
        print(f"✅ Added student to group")
    
    # 4. Create lesson
    lesson_start = timezone.now() + timezone.timedelta(hours=2)
    lesson, lesson_created = Lesson.objects.get_or_create(
        title="Тестовый урок для бота",
        group=group,
        defaults={
            'description': 'Урок для тестирования уведомлений',
            'start_time': lesson_start,
            'duration': 60,
        }
    )
    if lesson_created:
        print(f"✅ Created lesson: {lesson.title} (start: {lesson_start.strftime('%d.%m %H:%M')})")
    else:
        print(f"✅ Lesson exists: {lesson.title}")
    
    # 5. Create homework (draft - ready to publish)
    homework, hw_created = Homework.objects.get_or_create(
        title="Тест Telegram уведомлений",
        lesson=lesson,
        defaults={
            'description': 'ДЗ для проверки работы бота',
            'teacher': teacher,
            'max_score': 10,
            'status': 'draft',  # Важно! Будем публиковать через UI
        }
    )
    if hw_created:
        print(f"✅ Created homework: {homework.title} (status: {homework.status})")
        
        # Add questions
        Question.objects.create(
            homework=homework,
            question_type='SINGLE_CHOICE',
            order=1,
            text='Какой язык программирования используется в Teaching Panel?',
            config={
                'options': [
                    {'id': 'a', 'text': 'Python'},
                    {'id': 'b', 'text': 'Java'},
                    {'id': 'c', 'text': 'JavaScript'},
                ],
                'correctAnswer': 'a'
            },
            points=5
        )
        
        Question.objects.create(
            homework=homework,
            question_type='FILL_BLANKS',
            order=2,
            text='Telegram бот отправляет уведомления через ____ API',
            config={
                'correctAnswer': 'Telegram'
            },
            points=5
        )
        print(f"✅ Added 2 questions to homework")
    else:
        print(f"✅ Homework exists: {homework.title}")
    
    print("\n" + "="*60)
    print("🎉 Test data created successfully!")
    print("="*60)
    print("\n📝 Next steps:")
    print(f"1. Link student account in Telegram:")
    print(f"   - Open bot in Telegram")
    print(f"   - Send /start")
    print(f"   - Click '🔗 Привязать аккаунт'")
    print(f"   - Enter invite code: {group.invite_code}")
    print()
    print(f"2. Login as teacher:")
    print(f"   - Email: {teacher_email}")
    print(f"   - Password: test123")
    print()
    print(f"3. Login as student:")
    print(f"   - Email: {student_email}")
    print(f"   - Password: test123")
    print()
    print(f"4. Publish homework:")
    print(f"   - Go to Homework → '{homework.title}'")
    print(f"   - Click '📢 Опубликовать'")
    print(f"   - Check Telegram for notification!")
    print()


if __name__ == '__main__':
    try:
        create_test_data()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
