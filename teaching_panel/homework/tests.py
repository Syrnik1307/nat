from django.test import TestCase
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch
from schedule.models import Group, Lesson
from .models import Homework, Question, Choice, StudentSubmission, Answer

User = get_user_model()

class HomeworkAutoScoreTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(email='t@example.com', password='pass', role='teacher')
        self.student = User.objects.create_user(email='s@example.com', password='pass', role='student')
        self.group = Group.objects.create(name='G1', teacher=self.teacher)
        self.group.students.add(self.student)
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        self.lesson = Lesson.objects.create(title='L1', group=self.group, teacher=self.teacher, start_time=start, end_time=end)
        self.hw = Homework.objects.create(teacher=self.teacher, lesson=self.lesson, title='HW1')

    def test_single_choice_correct(self):
        q = Question.objects.create(homework=self.hw, prompt='Q1', question_type='SINGLE_CHOICE', points=5, order=1)
        c1 = Choice.objects.create(question=q, text='A', is_correct=True)
        c2 = Choice.objects.create(question=q, text='B', is_correct=False)
        submission = StudentSubmission.objects.create(homework=self.hw, student=self.student)
        ans = Answer.objects.create(submission=submission, question=q)
        ans.selected_choices.add(c1)
        ans.evaluate()
        submission.compute_auto_score()
        self.assertEqual(ans.auto_score, 5)
        self.assertEqual(submission.total_score, 5)

    def test_multi_choice_partial(self):
        q = Question.objects.create(homework=self.hw, prompt='Q2', question_type='MULTI_CHOICE', points=10, order=2)
        correct1 = Choice.objects.create(question=q, text='A', is_correct=True)
        correct2 = Choice.objects.create(question=q, text='B', is_correct=True)
        wrong = Choice.objects.create(question=q, text='C', is_correct=False)
        submission = StudentSubmission.objects.create(homework=self.hw, student=self.student)
        ans = Answer.objects.create(submission=submission, question=q)
        ans.selected_choices.add(correct1, wrong)
        ans.evaluate()
        submission.compute_auto_score()
        # Partial scoring: true_pos=1, false_pos=1 -> partial=max(0,1-1)=0 => score 0
        self.assertEqual(ans.auto_score, 0)
        self.assertEqual(submission.total_score, 0)

    def test_multi_choice_full(self):
        q = Question.objects.create(homework=self.hw, prompt='Q3', question_type='MULTI_CHOICE', points=10, order=3)
        c1 = Choice.objects.create(question=q, text='A', is_correct=True)
        c2 = Choice.objects.create(question=q, text='B', is_correct=True)
        submission = StudentSubmission.objects.create(homework=self.hw, student=self.student)
        ans = Answer.objects.create(submission=submission, question=q)
        ans.selected_choices.add(c1, c2)
        ans.evaluate()
        submission.compute_auto_score()
        self.assertEqual(ans.auto_score, 10)
        self.assertEqual(submission.total_score, 10)

    def test_text_question_flags_manual_review(self):
        q = Question.objects.create(homework=self.hw, prompt='Q4', question_type='TEXT', points=7, order=4)
        submission = StudentSubmission.objects.create(homework=self.hw, student=self.student)
        ans = Answer.objects.create(submission=submission, question=q, text_answer='My answer')
        ans.evaluate()
        self.assertTrue(ans.needs_manual_review)
        self.assertIsNone(ans.auto_score)

    def test_text_decimal_comma_vs_dot(self):
        """4,5 и 4.5 должны считаться одинаковыми ответами."""
        q = Question.objects.create(
            homework=self.hw, prompt='Чему равно 9/2?', 
            question_type='TEXT', points=5, order=5,
            config={'correctAnswer': '4.5'}
        )
        submission = StudentSubmission.objects.create(homework=self.hw, student=self.student)
        # Ученик вводит запятую вместо точки
        ans = Answer.objects.create(submission=submission, question=q, text_answer='4,5')
        ans.evaluate()
        self.assertEqual(ans.auto_score, 5)
        self.assertFalse(ans.needs_manual_review)

    def test_text_decimal_dot_vs_comma(self):
        """Учитель указал запятую, ученик ввёл точку."""
        q = Question.objects.create(
            homework=self.hw, prompt='Чему равно 7/2?', 
            question_type='TEXT', points=5, order=6,
            config={'correctAnswer': '3,5'}
        )
        submission = StudentSubmission.objects.create(homework=self.hw, student=self.student)
        ans = Answer.objects.create(submission=submission, question=q, text_answer='3.5')
        ans.evaluate()
        self.assertEqual(ans.auto_score, 5)
        self.assertFalse(ans.needs_manual_review)

    def test_fill_blanks_decimal_normalization(self):
        """FILL_BLANKS: 2,5 и 2.5 должны быть эквивалентны."""
        import json
        q = Question.objects.create(
            homework=self.hw, prompt='Заполни пропуски', 
            question_type='FILL_BLANKS', points=10, order=7,
            config={'answers': ['2.5', '3,14']}
        )
        submission = StudentSubmission.objects.create(homework=self.hw, student=self.student)
        # Ученик вводит с запятой и с точкой
        ans = Answer.objects.create(
            submission=submission, question=q, 
            text_answer=json.dumps(['2,5', '3.14'])
        )
        ans.evaluate()
        self.assertEqual(ans.auto_score, 10)


class SubmissionApiGuardsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(email='t2@example.com', password='pass', role='teacher')
        self.student = User.objects.create_user(email='s2@example.com', password='pass', role='student')
        self.group = Group.objects.create(name='G2', teacher=self.teacher)
        self.group.students.add(self.student)
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        self.lesson = Lesson.objects.create(title='L2', group=self.group, teacher=self.teacher, start_time=start, end_time=end)
        self.hw = Homework.objects.create(teacher=self.teacher, lesson=self.lesson, title='HW2', status='published', published_at=timezone.now())

    def test_student_cannot_create_submission_as_submitted(self):
        self.client.force_authenticate(user=self.student)
        resp = self.client.post('/api/submissions/', {
            'homework': self.hw.id,
            'status': 'submitted',
            'submitted_at': timezone.now().isoformat(),
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data.get('status'), 'in_progress')
        self.assertIsNone(resp.data.get('submitted_at'))


class SubmissionNotificationsTests(TestCase):
    @override_settings(TELEGRAM_BOT_TOKEN='test-token')
    @patch('accounts.notifications.requests.post')
    def test_feedback_notifies_student_only_once(self, mock_post):
        """Повторное сохранение feedback не должно спамить 'homework_graded'."""
        # Telegram API mock
        mock_post.return_value.ok = True
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'OK'

        client = APIClient()
        teacher = User.objects.create_user(email='t3@example.com', password='pass', role='teacher')
        student = User.objects.create_user(email='s3@example.com', password='pass', role='student')
        student.telegram_chat_id = 123
        student.save(update_fields=['telegram_chat_id'])

        group = Group.objects.create(name='G3', teacher=teacher)
        group.students.add(student)
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        lesson = Lesson.objects.create(title='L3', group=group, teacher=teacher, start_time=start, end_time=end)
        hw = Homework.objects.create(teacher=teacher, lesson=lesson, title='HW3', status='published', published_at=timezone.now())

        submission = StudentSubmission.objects.create(homework=hw, student=student, status='submitted', submitted_at=timezone.now())

        client.force_authenticate(user=teacher)

        # First feedback -> should notify
        resp1 = client.patch(f'/api/submissions/{submission.id}/feedback/', {
            'score': 10,
            'comment': 'ok',
        }, format='json')
        self.assertEqual(resp1.status_code, 200)

        # Second feedback edit (already graded) -> should NOT notify again
        resp2 = client.patch(f'/api/submissions/{submission.id}/feedback/', {
            'score': 10,
            'comment': 'updated',
        }, format='json')
        self.assertEqual(resp2.status_code, 200)

        # Only one actual Telegram send should happen
        self.assertEqual(mock_post.call_count, 1)
