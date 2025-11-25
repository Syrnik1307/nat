from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
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
