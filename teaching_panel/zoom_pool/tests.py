from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from schedule.models import Group, Lesson

from .models import ZoomAccount, ZoomPoolUsageMetrics


class ZoomPoolUsageMetricsTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.teacher = User.objects.create_user(
			email='teacher@example.com',
			password='pass123',
			role='teacher',
		)
		self.group = Group.objects.create(name='Test Group', teacher=self.teacher)
		self.account_one = ZoomAccount.objects.create(
			email='zoom1@example.com',
			api_key='key1',
			api_secret='secret1',
			zoom_user_id='user1',
			max_concurrent_meetings=1,
		)
		self.account_two = ZoomAccount.objects.create(
			email='zoom2@example.com',
			api_key='key2',
			api_secret='secret2',
			zoom_user_id='user2',
			max_concurrent_meetings=1,
		)

	def create_active_lesson(self, account, start_delta=-30, end_delta=30):
		now = timezone.now()
		return Lesson.objects.create(
			title='Demo Lesson',
			group=self.group,
			teacher=self.teacher,
			start_time=now + timedelta(minutes=start_delta),
			end_time=now + timedelta(minutes=end_delta),
			zoom_account=account,
		)

	def test_refresh_usage_tracks_current_and_peak(self):
		metrics = ZoomPoolUsageMetrics.refresh_usage()
		self.assertEqual(metrics.current_in_use, 0)
		self.assertEqual(metrics.peak_in_use, 0)

		# Активный урок на первом аккаунте
		lesson_one = self.create_active_lesson(self.account_one)
		metrics = ZoomPoolUsageMetrics.refresh_usage()
		self.assertEqual(metrics.current_in_use, 1)
		self.assertEqual(metrics.current_sessions, 1)
		self.assertEqual(metrics.peak_in_use, 1)

		# Второй активный урок увеличивает пик
		lesson_two = self.create_active_lesson(self.account_two)
		metrics = ZoomPoolUsageMetrics.refresh_usage()
		self.assertEqual(metrics.current_in_use, 2)
		self.assertEqual(metrics.current_sessions, 2)
		self.assertEqual(metrics.peak_in_use, 2)

		# Завершаем вторую встречу (урок уже прошёл)
		lesson_two.end_time = timezone.now() - timedelta(minutes=10)
		lesson_two.save()
		metrics = ZoomPoolUsageMetrics.refresh_usage()
		self.assertEqual(metrics.current_in_use, 1)
		self.assertEqual(metrics.current_sessions, 1)
		self.assertEqual(metrics.peak_in_use, 2)

	def test_inactive_accounts_are_excluded_from_metrics(self):
		self.account_one.is_active = False
		self.account_one.save(update_fields=['is_active'])
		self.create_active_lesson(self.account_one)
		self.create_active_lesson(self.account_two)

		metrics = ZoomPoolUsageMetrics.refresh_usage()
		self.assertEqual(metrics.current_in_use, 1)
		self.assertEqual(metrics.current_sessions, 1)

		# Завершаем урок на активном аккаунте
		Lesson.objects.filter(zoom_account=self.account_two).update(
			end_time=timezone.now() - timedelta(minutes=10)
		)
		metrics = ZoomPoolUsageMetrics.refresh_usage()
		self.assertEqual(metrics.current_in_use, 0)
		self.assertEqual(metrics.current_sessions, 0)

	def test_peak_resets_each_month(self):
		metrics = ZoomPoolUsageMetrics.refresh_usage()
		older_month = (metrics.stats_month.replace(day=1) if metrics.stats_month else timezone.localdate().replace(day=1))
		if older_month.month == 1:
			older_month = older_month.replace(year=older_month.year - 1, month=12)
		else:
			older_month = older_month.replace(month=older_month.month - 1)
		metrics.stats_month = older_month
		metrics.peak_in_use = 5
		metrics.peak_sessions = 7
		metrics.save(update_fields=['stats_month', 'peak_in_use', 'peak_sessions'])

		self.create_active_lesson(self.account_one)
		metrics = ZoomPoolUsageMetrics.refresh_usage()
		self.assertEqual(metrics.stats_month, timezone.localdate().replace(day=1))
		self.assertEqual(metrics.peak_sessions, 1)
		self.assertEqual(metrics.peak_in_use, 1)
