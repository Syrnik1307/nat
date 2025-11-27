"""
Скрипт для создания тестовых пользователей для нагрузочного тестирования
Создаёт 1000 учителей и 3000 учеников

Запуск:
    python create_load_test_users.py
"""
import os
import sys
import django
from django.db import transaction

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
from core.models import Course
from schedule.models import Group
from homework.models import Homework, Question, Choice, StudentSubmission, Answer


def create_test_users():
    """Создаёт тестовых пользователей"""
    print("🚀 Начинаем создание тестовых пользователей...")
    
    with transaction.atomic():
        # Создаём учителей ПЕРВЫМИ (нужны для курсов)
        print("👨‍🏫 Создание учителей...")
        teachers_created = 0
        for i in range(1, 1001):
            email = f"teacher{i}@example.com"
            
            if not CustomUser.objects.filter(email=email).exists():
                CustomUser.objects.create_user(
                    email=email,
                    password='testpassword123',
                    first_name=f"Учитель",
                    last_name=f"Тестовый{i}",
                    role='teacher',
                    phone_number=f"+7900{i:07d}"
                )
                teachers_created += 1
                
                if teachers_created % 100 == 0:
                    print(f"  Создано {teachers_created} учителей...")
        
        print(f"✅ Создано {teachers_created} учителей")
        
        # Теперь создаём курсы (с учителями)
        print("📚 Создание курсов...")
        teachers = list(CustomUser.objects.filter(role='teacher')[:100])
        courses = []
        for i in range(10):
            course, created = Course.objects.get_or_create(
                title=f"Курс {i+1}",
                defaults={
                    'description': f"Тестовый курс {i+1}",
                    'teacher': teachers[i % len(teachers)]
                }
            )
            courses.append(course)
        print(f"✅ Создано {len(courses)} курсов")
        
        # Создаём группы
        print("👥 Создание групп...")
        groups = []
        for i in range(50):
            group, created = Group.objects.get_or_create(
                name=f"Группа {i+1}",
                defaults={
                    'teacher': teachers[i % len(teachers)],
                    'description': f"Тестовая группа {i+1}"
                }
            )
            groups.append(group)
        print(f"✅ Создано {len(groups)} групп")
        
        # Создаём учеников
        print("👨‍🎓 Создание учеников...")
        students_created = 0
        for i in range(1, 3001):
            email = f"student{i}@example.com"
            
            if not CustomUser.objects.filter(email=email).exists():
                user = CustomUser.objects.create_user(
                    email=email,
                    password='testpassword123',
                    first_name=f"Ученик",
                    last_name=f"Тестовый{i}",
                    role='student',
                    phone_number=f"+7800{i:07d}"
                )
                students_created += 1
                
                if students_created % 300 == 0:
                    print(f"  Создано {students_created} учеников...")
        
        print(f"✅ Создано {students_created} учеников")
        
        # Создаём домашние задания
        print("📝 Создание домашних заданий...")
        homeworks_created = 0
        
        for teacher in teachers:
            for i in range(5):  # 5 заданий на учителя
                homework, created = Homework.objects.get_or_create(
                    title=f"ДЗ {i+1} от {teacher.get_full_name()}",
                    defaults={
                        'description': f"Тестовое задание {i+1}",
                        'teacher': teacher
                    }
                )
                
                if created:
                    # Создаём вопросы
                    for q in range(5):  # 5 вопросов в каждом задании
                        question = Question.objects.create(
                            homework=homework,
                            prompt=f"Вопрос {q+1}",
                            question_type='SINGLE_CHOICE',
                            points=20,
                            order=q
                        )
                        
                        # Создаём варианты ответов
                        for a in range(4):
                            Choice.objects.create(
                                question=question,
                                text=f"Вариант {a+1}",
                                is_correct=(a == 0)
                            )
                    
                    homeworks_created += 1
        
        print(f"✅ Создано {homeworks_created} заданий")
        
        # Создаём работы учеников
        print("📋 Создание работ учеников...")
        students = CustomUser.objects.filter(role='student')[:500]
        homeworks = Homework.objects.all()[:100]
        submissions_created = 0
        
        for student in students:
            for homework in list(homeworks)[:3]:  # По 3 работы на ученика
                submission, created = StudentSubmission.objects.get_or_create(
                    student=student,
                    homework=homework,
                    defaults={
                        'status': 'submitted' if submissions_created % 2 == 0 else 'graded'
                    }
                )
                
                if created:
                    # Создаём ответы
                    questions = homework.questions.all()
                    for question in questions:
                        choices = list(question.choices.all())
                        if choices:
                            answer = Answer.objects.create(
                                submission=submission,
                                question=question,
                                auto_score=question.points if submissions_created % 3 == 0 else 0
                            )
                            answer.selected_choices.add(choices[0])
                            
                            # Половина работ уже проверена учителем
                            if submission.status == 'graded':
                                answer.teacher_score = question.points - (submissions_created % 5)
                                answer.teacher_feedback = "Хорошая работа!"
                                answer.save()
                    
                    # Пересчитываем итоговый балл
                    submission.compute_auto_score()
                    
                    submissions_created += 1
                    
                    if submissions_created % 100 == 0:
                        print(f"  Создано {submissions_created} работ...")
        
        print(f"✅ Создано {submissions_created} работ")
    
    print("\n🎉 Создание тестовых данных завершено!")
    print(f"""
📊 Статистика:
   • Курсы: {Course.objects.count()}
   • Группы: {Group.objects.count()}
   • Учителя: {CustomUser.objects.filter(role='teacher').count()}
   • Ученики: {CustomUser.objects.filter(role='student').count()}
   • Домашние задания: {Homework.objects.count()}
   • Вопросы: {Question.objects.count()}
   • Работы учеников: {StudentSubmission.objects.count()}
   • Ответы: {Answer.objects.count()}
    """)


if __name__ == '__main__':
    try:
        create_test_users()
    except KeyboardInterrupt:
        print("\n❌ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
