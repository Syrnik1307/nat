$ErrorActionPreference = 'Stop'

$py = @'
from datetime import timedelta
from django.utils import timezone
from accounts.models import CustomUser
from schedule.models import Group, Lesson
from homework.models import Homework, Question, Choice


def ensure_user(email, role, first, last):
    user, created = CustomUser.objects.get_or_create(email=email, defaults={'role': role, 'is_active': True})
    if created:
        user.first_name = first
        user.last_name = last
        user.set_password('Test1234!')
        user.save()
    return user


def main():
    teacher = ensure_user('smoke_hw_teacher@test.local', 'teacher', 'Smoke', 'Teacher')
    student = ensure_user('smoke_hw_student@test.local', 'student', 'Smoke', 'Student')

    group, _ = Group.objects.get_or_create(
        name='SMOKE HW GROUP',
        teacher=teacher,
        defaults={'description': 'Smoke homework group'},
    )
    group.students.add(student)

    start = timezone.now() + timedelta(hours=1)
    end = start + timedelta(hours=1)

    lesson, created = Lesson.objects.get_or_create(
        group=group,
        teacher=teacher,
        title='SMOKE HW Lesson',
        defaults={'start_time': start, 'end_time': end},
    )
    if not created:
        changed = False
        if not lesson.start_time:
            lesson.start_time = start
            changed = True
        if not lesson.end_time:
            lesson.end_time = end
            changed = True
        if changed:
            lesson.save(update_fields=['start_time', 'end_time'])

    homework, _ = Homework.objects.get_or_create(
        title='SMOKE HW Autogen',
        teacher=teacher,
        defaults={'lesson': lesson, 'status': 'draft'},
    )

    homework.lesson = lesson
    homework.status = 'published'
    homework.published_at = timezone.now()
    homework.description = 'Auto smoke homework for prod smoke script.'
    homework.save(update_fields=['lesson', 'status', 'published_at', 'description'])

    homework.questions.all().delete()

    q1 = Question.objects.create(
        homework=homework,
        prompt='Smoke single choice?',
        question_type='SINGLE_CHOICE',
        points=1,
        order=1,
    )
    c1 = Choice.objects.create(question=q1, text='Option A', is_correct=True)
    c2 = Choice.objects.create(question=q1, text='Option B', is_correct=False)
    q1.config = {
        'options': [
            {'id': str(c1.id), 'text': 'Option A'},
            {'id': str(c2.id), 'text': 'Option B'},
        ],
        'correctOptionId': str(c1.id),
    }
    q1.save(update_fields=['config'])

    q2 = Question.objects.create(
        homework=homework,
        prompt='Smoke multi choice?',
        question_type='MULTI_CHOICE',
        points=2,
        order=2,
    )
    m1 = Choice.objects.create(question=q2, text='M1', is_correct=True)
    m2 = Choice.objects.create(question=q2, text='M2', is_correct=True)
    m3 = Choice.objects.create(question=q2, text='M3', is_correct=False)
    q2.config = {
        'options': [
            {'id': str(m1.id), 'text': 'M1'},
            {'id': str(m2.id), 'text': 'M2'},
            {'id': str(m3.id), 'text': 'M3'},
        ],
        'correctOptionIds': [str(m1.id), str(m2.id)],
    }
    q2.save(update_fields=['config'])

    print('CREATED_HW', homework.id)
    print('STUDENT', student.id, student.email)
    print('TEACHER', teacher.id, teacher.email)
    print('GROUP', group.id, group.name)
    print('LESSON', lesson.id, lesson.title)


main()
'@

$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))

$remote = "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && echo $b64 | base64 -d | python manage.py shell"

ssh tp "$remote"
