from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from schedule.models import Group, Lesson
from homework.models import Homework, Question, StudentSubmission, Answer
from accounts.models import AttendanceRecord

User = get_user_model()


class TeacherStatsSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(email='teacher_stats@example.com', password='pass', role='teacher')
        self.student = User.objects.create_user(email='student_stats@example.com', password='pass', role='student')

        self.group = Group.objects.create(name='G-Stats', teacher=self.teacher)
        self.group.students.add(self.student)

        now = timezone.now()
        start = now - timezone.timedelta(hours=2)
        end = now - timezone.timedelta(hours=1)
        self.lesson = Lesson.objects.create(
            title='L-Stats',
            group=self.group,
            teacher=self.teacher,
            start_time=start,
            end_time=end,
        )

        self.hw = Homework.objects.create(
            teacher=self.teacher,
            lesson=self.lesson,
            title='HW-Stats',
            status='published',
            published_at=now,
            deadline=now - timezone.timedelta(days=1),
            is_template=False,
        )

        self.question = Question.objects.create(
            homework=self.hw,
            prompt='Q',
            question_type='SINGLE_CHOICE',
            points=1,
            order=1,
        )

        submitted_at = now - timezone.timedelta(days=2)
        graded_at = now - timezone.timedelta(days=1, hours=20)
        self.submission = StudentSubmission.objects.create(
            homework=self.hw,
            student=self.student,
            status='graded',
            submitted_at=submitted_at,
            graded_at=graded_at,
        )

        Answer.objects.create(
            submission=self.submission,
            question=self.question,
            auto_score=1,
            teacher_score=None,
        )

    def test_summary_for_teacher_has_nonzero_core_fields(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get('/api/teacher-stats/summary/')
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertGreaterEqual(data.get('total_groups', 0), 1)
        self.assertGreaterEqual(data.get('total_students', 0), 1)
        self.assertGreaterEqual(data.get('total_lessons', 0), 1)

        # Метрики ДЗ
        self.assertIn('pending_submissions', data)
        self.assertIn('graded_count_30d', data)
        self.assertGreaterEqual(data.get('auto_graded_answers', 0), 1)

    def test_summary_allows_admin_role(self):
        admin = User.objects.create_user(email='admin_stats@example.com', password='pass', role='admin')

        group = Group.objects.create(name='G-AdminStats', teacher=admin)
        group.students.add(self.student)

        now = timezone.now()
        start = now - timezone.timedelta(hours=2)
        end = now - timezone.timedelta(hours=1)
        lesson = Lesson.objects.create(
            title='L-AdminStats',
            group=group,
            teacher=admin,
            start_time=start,
            end_time=end,
        )

        Homework.objects.create(
            teacher=admin,
            lesson=lesson,
            title='HW-AdminStats',
            status='published',
            published_at=now,
            is_template=False,
        )

        self.client.force_authenticate(user=admin)
        resp = self.client.get('/api/teacher-stats/summary/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data.get('total_groups', 0), 1)
        self.assertGreaterEqual(data.get('total_students', 0), 1)


class StudentStatsSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(email='teacher_student_stats@example.com', password='pass', role='teacher')
        self.student = User.objects.create_user(email='student_student_stats@example.com', password='pass', role='student')

        self.group = Group.objects.create(name='G-StudentStats', teacher=self.teacher)
        self.group.students.add(self.student)

        now = timezone.now()
        # 2 lessons in the past
        self.lesson1 = Lesson.objects.create(
            title='L-1',
            group=self.group,
            teacher=self.teacher,
            start_time=now - timezone.timedelta(days=3, hours=2),
            end_time=now - timezone.timedelta(days=3, hours=1),
        )
        self.lesson2 = Lesson.objects.create(
            title='L-2',
            group=self.group,
            teacher=self.teacher,
            start_time=now - timezone.timedelta(days=2, hours=2),
            end_time=now - timezone.timedelta(days=2, hours=1),
        )

        AttendanceRecord.objects.create(lesson=self.lesson1, student=self.student, status=AttendanceRecord.STATUS_ATTENDED)
        AttendanceRecord.objects.create(lesson=self.lesson2, student=self.student, status=AttendanceRecord.STATUS_WATCHED_RECORDING)

        # Homework #1 attached to lesson
        self.hw1 = Homework.objects.create(
            teacher=self.teacher,
            lesson=self.lesson1,
            title='HW-1',
            status='published',
            published_at=now,
            deadline=now - timezone.timedelta(days=1),
            is_template=False,
        )
        self.q1 = Question.objects.create(
            homework=self.hw1,
            prompt='Q1',
            question_type='SINGLE_CHOICE',
            points=1,
            order=1,
        )

        # Homework #2 assigned directly to group (no lesson)
        self.hw2 = Homework.objects.create(
            teacher=self.teacher,
            lesson=None,
            title='HW-2',
            status='published',
            published_at=now,
            deadline=now - timezone.timedelta(days=1),
            is_template=False,
        )
        self.hw2.assigned_groups.add(self.group)
        self.q2 = Question.objects.create(
            homework=self.hw2,
            prompt='Q2',
            question_type='SINGLE_CHOICE',
            points=1,
            order=1,
        )

        self.sub1 = StudentSubmission.objects.create(
            homework=self.hw1,
            student=self.student,
            status='graded',
            submitted_at=now - timezone.timedelta(days=2),
            graded_at=now - timezone.timedelta(days=2, hours=-1),
        )
        self.sub2 = StudentSubmission.objects.create(
            homework=self.hw2,
            student=self.student,
            status='submitted',
            submitted_at=now - timezone.timedelta(days=1, hours=2),
            graded_at=None,
        )

        # Checked answers: one correct, one incorrect
        Answer.objects.create(submission=self.sub1, question=self.q1, auto_score=1, teacher_score=None, needs_manual_review=False)
        Answer.objects.create(submission=self.sub2, question=self.q2, auto_score=0, teacher_score=None, needs_manual_review=False)

    def test_student_stats_summary(self):
        self.client.force_authenticate(user=self.student)
        resp = self.client.get('/api/student-stats/summary/')
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        overall = data.get('overall', {})

        self.assertEqual(overall.get('groups_count'), 1)
        self.assertEqual(overall.get('attendance_total_marked'), 2)
        self.assertEqual(overall.get('attendance_present'), 2)
        self.assertEqual(overall.get('attendance_percent'), 100.0)

        self.assertEqual(overall.get('homeworks_total'), 2)
        self.assertEqual(overall.get('homeworks_completed'), 2)
        self.assertEqual(overall.get('homework_percent'), 100.0)

        self.assertEqual(overall.get('homework_answers_checked'), 2)
        self.assertEqual(overall.get('homework_errors'), 1)

        groups = data.get('groups', [])
        self.assertEqual(len(groups), 1)
        g0 = groups[0]
        self.assertEqual(g0.get('id'), self.group.id)
        self.assertEqual(g0.get('homeworks_total'), 2)
        self.assertEqual(g0.get('homeworks_completed'), 2)
        self.assertEqual(g0.get('homework_answers_checked'), 2)
        self.assertEqual(g0.get('homework_errors'), 1)
