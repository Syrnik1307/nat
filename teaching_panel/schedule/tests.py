from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.urls import reverse
from datetime import timedelta
from .models import Group, Lesson, RecurringLesson
from zoom_pool.models import ZoomAccount

User = get_user_model()

class RecurringLessonCalendarTests(TestCase):
	def setUp(self):
		self.teacher = User.objects.create_user(email='teach@example.com', password='pass', role='teacher')
		self.student = User.objects.create_user(email='stud@example.com', password='pass', role='student')
		self.group = Group.objects.create(name='Group1', teacher=self.teacher)
		self.group.students.add(self.student)
		self.client = APIClient()
		self.client.force_authenticate(user=self.teacher)

	def test_recurring_expansion(self):
		today = timezone.now().date()
		RecurringLesson.objects.create(
			title='Daily RL',
			group=self.group,
			teacher=self.teacher,
			day_of_week=today.weekday(),
			week_type='ALL',
			start_time=(timezone.now() + timedelta(minutes=30)).time(),
			end_time=(timezone.now() + timedelta(minutes=90)).time(),
			start_date=today,
			end_date=today + timedelta(days=2)
		)
		# Use date-only params to exercise fallback parsing
		start_param = today.isoformat()
		end_param = (today + timedelta(days=2)).isoformat()
		resp = self.client.get(f'/api/schedule/lessons/calendar_feed/?start={start_param}&end={end_param}&group={self.group.id}&teacher={self.teacher.id}')
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		recurring = [e for e in data if str(e['id']).startswith('recurring-')]
		self.assertTrue(len(recurring) >= 1)

	def test_real_lesson_blocks_recurring(self):
		start = timezone.now() + timedelta(hours=1)
		end = start + timedelta(hours=1)
		Lesson.objects.create(title='Real', group=self.group, teacher=self.teacher, start_time=start, end_time=end)
		RecurringLesson.objects.create(
			title='Potential Conflict',
			group=self.group,
			teacher=self.teacher,
			day_of_week=start.date().weekday(),
			week_type='ALL',
			start_time=start.time(),
			end_time=end.time(),
			start_date=start.date(),
			end_date=start.date()
		)
		resp = self.client.get(f'/api/schedule/lessons/calendar_feed/?start={(start - timedelta(days=1)).isoformat()}&end={(end + timedelta(days=1)).isoformat()}&group={self.group.id}')
		data = resp.json()
		overlapping_virtual = [e for e in data if 'Potential Conflict' in e['title']]
		self.assertEqual(len(overlapping_virtual), 0)

class LessonValidationTests(TestCase):
	def setUp(self):
		self.teacher = User.objects.create_user(email='teach2@example.com', password='pass', role='teacher')
		self.group = Group.objects.create(name='G2', teacher=self.teacher)
		self.client = APIClient()
		self.client.force_authenticate(user=self.teacher)

	def test_end_time_must_be_after_start(self):
		start = timezone.now()
		end = start - timedelta(minutes=30)
		payload = {
			'title': 'Bad', 'group': self.group.id, 'teacher': self.teacher.id,
			'start_time': start.isoformat(), 'end_time': end.isoformat()
		}
		resp = self.client.post('/api/schedule/lessons/', payload, format='json')
		self.assertEqual(resp.status_code, 400)
		self.assertIn('end_time', resp.json())

	def test_overlap_same_teacher(self):
		start = timezone.now() + timedelta(hours=1)
		end = start + timedelta(hours=1)
		Lesson.objects.create(title='First', group=self.group, teacher=self.teacher, start_time=start, end_time=end)
		payload = {
			'title': 'Overlap', 'group': self.group.id, 'teacher': self.teacher.id,
			'start_time': (start + timedelta(minutes=30)).isoformat(),
			'end_time': (end + timedelta(minutes=30)).isoformat()
		}
		resp = self.client.post('/api/schedule/lessons/', payload, format='json')
		self.assertEqual(resp.status_code, 400)
		self.assertTrue('пересекающийся' in str(resp.json()))


class LessonStartNewAPITests(TestCase):
	def setUp(self):
		self.User = get_user_model()
		self.teacher = self.User.objects.create_user(email='teacher@example.com', password='Pass1234', role='teacher')
		self.student = self.User.objects.create_user(email='student@example.com', password='Pass1234', role='student')
		self.group = Group.objects.create(name='StartNew Group', teacher=self.teacher)
		self.group.students.add(self.student)
		start = timezone.now() + timedelta(minutes=10)
		end = start + timedelta(minutes=45)
		self.lesson = Lesson.objects.create(title='Geometry', group=self.group, teacher=self.teacher, start_time=start, end_time=end)
		self.client = APIClient()
		self.client.force_authenticate(user=self.teacher)

	def test_start_new_returns_400_if_too_early(self):
		# Сдвигаем время урока дальше чем за 15 минут (например +30)
		self.lesson.start_time = timezone.now() + timedelta(minutes=30)
		self.lesson.save()
		url = reverse('schedule-lesson-start-new', args=[self.lesson.id])
		resp = self.client.post(url, {})
		self.assertEqual(resp.status_code, 400)
		self.assertIn('15 минут', resp.data['detail'])

	def test_start_new_503_without_accounts(self):
		# Сдвигаем время урока чтобы можно было стартовать
		self.lesson.start_time = timezone.now() + timedelta(minutes=5)
		self.lesson.save()
		url = reverse('schedule-lesson-start-new', args=[self.lesson.id])
		resp = self.client.post(url, {})
		self.assertEqual(resp.status_code, 503)
		self.assertIn('заняты', resp.data['detail'])

	def test_start_new_success_with_account(self):
		self.lesson.start_time = timezone.now() + timedelta(minutes=5)
		self.lesson.save()
		ZoomAccount.objects.create(email='zoom@test.com', api_key='k', api_secret='s', max_concurrent_meetings=1)
		url = reverse('schedule-lesson-start-new', args=[self.lesson.id])
		resp = self.client.post(url, {})
		self.assertEqual(resp.status_code, 200)
		self.assertIn('zoom_join_url', resp.data)
		self.lesson.refresh_from_db()
		self.assertIsNotNone(self.lesson.zoom_account)
		account = self.lesson.zoom_account
		self.assertEqual(account.current_meetings, 1)
