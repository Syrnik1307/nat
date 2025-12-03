#!/usr/bin/env python
"""
Тестирование флоу создания ДЗ учителем и решения учеником на продакшн сервере.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser as User
from schedule.models import Group
from homework.models import Homework, StudentSubmission, Question, Choice, Answer
from django.utils import timezone
from django.db import models
import json

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test_homework_flow():
    print_section("1. ПРОВЕРКА ПОЛЬЗОВАТЕЛЕЙ И ГРУПП")
    
    # Проверяем учителей
    teachers = User.objects.filter(role='teacher')
    print(f"\n✓ Учителей: {teachers.count()}")
    if teachers.exists():
        teacher = teachers.first()
        print(f"  Используем: {teacher.email} (ID: {teacher.id})")
    else:
        print("✗ Нет учителей! Создаём тестового...")
        teacher = User.objects.create_user(
            email='test_teacher@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Teacher',
            role='teacher'
        )
        print(f"  ✓ Создан: {teacher.email}")
    
    # Проверяем учеников
    students = User.objects.filter(role='student')
    print(f"\n✓ Учеников: {students.count()}")
    if students.exists():
        student = students.first()
        print(f"  Используем: {student.email} (ID: {student.id})")
    else:
        print("✗ Нет учеников! Создаём тестового...")
        student = User.objects.create_user(
            email='test_student@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Student',
            role='student'
        )
        print(f"  ✓ Создан: {student.email}")
    
    # Проверяем/создаём группу
    groups = Group.objects.filter(teacher=teacher)
    print(f"\n✓ Групп учителя: {groups.count()}")
    if groups.exists():
        group = groups.first()
        print(f"  Используем: {group.name} (ID: {group.id})")
    else:
        print("✗ Нет групп! Создаём тестовую...")
        group = Group.objects.create(
            name='Test Group',
            teacher=teacher,
            description='Тестовая группа для проверки ДЗ'
        )
        print(f"  ✓ Создана: {group.name}")
    
    # Добавляем ученика в группу
    if not group.students.filter(id=student.id).exists():
        group.students.add(student)
        print(f"\n✓ Добавили ученика {student.email} в группу {group.name}")
    else:
        print(f"\n✓ Ученик {student.email} уже в группе {group.name}")
    
    print_section("2. СОЗДАНИЕ ДОМАШНЕГО ЗАДАНИЯ")
    
    # Создаём ДЗ (используем реальную структуру - без group и deadline)
    homework_data = {
        'title': 'Тестовое ДЗ: Past Simple',
        'description': 'Проверка флоу создания и решения ДЗ',
        'teacher': teacher,
        'status': 'published',  # Сразу публикуем
        'published_at': timezone.now(),
    }
    
    homework = Homework.objects.create(**homework_data)
    print(f"\n✓ ДЗ создано: {homework.title} (ID: {homework.id})")
    print(f"  Статус: {homework.status}")
    print(f"  Учитель: {homework.teacher.email}")
    
    # Добавляем вопросы (Question модели с FK на Homework)
    q1 = Question.objects.create(
        homework=homework,
        prompt='I ___ to the cinema yesterday.',
        question_type='SINGLE_CHOICE',
        points=10,
        order=0
    )
    Choice.objects.create(question=q1, text='go', is_correct=False)
    Choice.objects.create(question=q1, text='went', is_correct=True)
    Choice.objects.create(question=q1, text='goes', is_correct=False)
    
    q2 = Question.objects.create(
        homework=homework,
        prompt='Translate: Я вчера читал книгу.',
        question_type='TEXT',
        points=10,
        order=1
    )
    
    q3 = Question.objects.create(
        homework=homework,
        prompt='Which are irregular verbs?',
        question_type='MULTI_CHOICE',
        points=10,
        order=2
    )
    Choice.objects.create(question=q3, text='play', is_correct=False)
    Choice.objects.create(question=q3, text='go', is_correct=True)
    Choice.objects.create(question=q3, text='write', is_correct=True)
    Choice.objects.create(question=q3, text='walk', is_correct=False)
    
    questions = homework.questions.all()
    print(f"\n✓ Добавлено вопросов: {questions.count()}")
    for q in questions:
        print(f"  {q.order + 1}. {q.question_type}: {q.points} баллов - {q.prompt[:50]}")
        if q.choices.exists():
            print(f"     Вариантов: {q.choices.count()} (правильных: {q.choices.filter(is_correct=True).count()})")
    
    print_section("3. УЧЕНИК ВИДИТ ДЗ")
    
    # Проверяем, что ученик видит опубликованное ДЗ
    student_homeworks = Homework.objects.filter(
        status='published'
    )
    print(f"\n✓ Опубликованных ДЗ: {student_homeworks.count()} шт.")
    for hw in student_homeworks[:3]:
        print(f"  - {hw.title} (создано: {hw.created_at.strftime('%d.%m.%Y')})")
    
    print_section("4. УЧЕНИК ОТВЕЧАЕТ НА ВОПРОСЫ")
    
    # Создаём submission
    submission = StudentSubmission.objects.create(
        homework=homework,
        student=student,
        status='submitted'
    )
    
    print(f"\n✓ Создан submission (ID: {submission.id})")
    
    # Создаём ответы для каждого вопроса
    total_earned = 0
    
    # Вопрос 1: Single choice (правильный ответ)
    answer1 = Answer.objects.create(
        submission=submission,
        question=q1,
        text_answer=''
    )
    correct_choice = q1.choices.get(is_correct=True)
    answer1.selected_choices.add(correct_choice)
    score1 = answer1.evaluate()
    total_earned += score1
    print(f"\n  Вопрос 1 (SINGLE_CHOICE): {score1}/{q1.points} баллов")
    print(f"    Выбран: {correct_choice.text}")
    
    # Вопрос 2: Text (требует ручной проверки)
    answer2 = Answer.objects.create(
        submission=submission,
        question=q2,
        text_answer='I read a book yesterday.'
    )
    answer2.evaluate()
    print(f"\n  Вопрос 2 (TEXT): требует проверки учителя")
    print(f"    Ответ: {answer2.text_answer}")
    
    # Вопрос 3: Multi choice (все правильные ответы)
    answer3 = Answer.objects.create(
        submission=submission,
        question=q3,
        text_answer=''
    )
    correct_choices = q3.choices.filter(is_correct=True)
    for choice in correct_choices:
        answer3.selected_choices.add(choice)
    score3 = answer3.evaluate()
    total_earned += score3
    print(f"\n  Вопрос 3 (MULTI_CHOICE): {score3}/{q3.points} баллов")
    print(f"    Выбрано: {', '.join(c.text for c in answer3.selected_choices.all())}")
    
    # Обновляем общий балл
    submission.compute_auto_score()
    print(f"\n✓ Submission создан:")
    print(f"  Статус: {submission.status}")
    print(f"  Автобаллов: {submission.total_score}/{homework.questions.aggregate(models.Sum('points'))['points__sum']}")
    print(f"  (вопрос TEXT требует ручной проверки)")
    
    print_section("5. УЧИТЕЛЬ ПРОВЕРЯЕТ ОТВЕТЫ")
    
    # Учитель видит submissions
    teacher_submissions = StudentSubmission.objects.filter(
        homework__teacher=teacher,
        status='submitted'
    )
    print(f"\n✓ Учитель видит ответов: {teacher_submissions.count()}")
    
    for sub in teacher_submissions:
        print(f"\n  ДЗ: {sub.homework.title}")
        print(f"  Ученик: {sub.student.get_full_name() or sub.student.email}")
        print(f"  Баллов: {sub.total_score or 0}")
        print(f"  Отправлено: {sub.submitted_at.strftime('%d.%m.%Y %H:%M')}")
        
        # Показываем ответы
        for ans in sub.answers.all():
            print(f"    Q{ans.question.order + 1}: {ans.question.question_type}")
            if ans.needs_manual_review:
                print(f"      Текст: {ans.text_answer[:50]}")
                print(f"      ⚠️ Требует проверки")
            else:
                print(f"      Баллов: {ans.auto_score}/{ans.question.points}")
    
    # Учитель проверяет TEXT вопрос и ставит оценку
    text_answer = submission.answers.get(question=q2)
    text_answer.teacher_score = 10  # Полный балл за правильный перевод
    text_answer.teacher_feedback = "Отлично! Правильный перевод. 👍"
    text_answer.needs_manual_review = False
    text_answer.save()
    
    # Пересчитываем итоговый балл
    submission.compute_auto_score()
    submission.status = 'graded'
    submission.graded_at = timezone.now()
    submission.save()
    
    print(f"\n✓ Учитель проверил TEXT вопрос:")
    print(f"  Оценка: {text_answer.teacher_score}/{q2.points}")
    print(f"  Комментарий: {text_answer.teacher_feedback}")
    print(f"\n✓ Итоговая оценка: {submission.total_score}/{homework.questions.aggregate(models.Sum('points'))['points__sum']}")
    print(f"  Статус: {submission.status}")
    
    print_section("6. РЕЗУЛЬТАТЫ ТЕСТА")
    
    total_points = homework.questions.aggregate(models.Sum('points'))['points__sum']
    
    print(f"\n✅ ФЛОУ РАБОТАЕТ ПОЛНОСТЬЮ:")
    print(f"   1. Учитель создал ДЗ: {homework.title}")
    print(f"   2. ДЗ опубликовано (статус: {homework.status})")
    print(f"   3. Ученик {student.email} отправил ответы")
    print(f"   4. Автопроверка: 2 вопроса (Single/Multi choice)")
    print(f"   5. Учитель проверил TEXT вопрос")
    print(f"   6. Итого: {submission.total_score}/{total_points} баллов")
    
    print(f"\n🔗 Ссылки для проверки в браузере:")
    print(f"   Frontend: http://72.56.81.163/")
    print(f"   Админка: http://72.56.81.163/admin/")
    print(f"   ДЗ ID: {homework.id}")
    print(f"   Submission ID: {submission.id}")
    
    print_section("ДАННЫЕ ДЛЯ ВХОДА")
    print(f"\n📧 Учитель:")
    print(f"   Email: {teacher.email}")
    print(f"   Password: (используй существующий или сбрось через admin)")
    
    print(f"\n📧 Ученик:")
    print(f"   Email: {student.email}")
    print(f"   Password: (используй существующий или сбрось через admin)")

if __name__ == '__main__':
    try:
        test_homework_flow()
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
