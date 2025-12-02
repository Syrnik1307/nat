from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import CustomUser, Subscription
from schedule.models import Group, Lesson


class AdminStatsViewTests(APITestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            email='admin@example.com',
            password='StrongPass123',
            role='admin',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.admin)

        self.recent_teacher = self._create_user(
            email='teacher@example.com',
            role='teacher',
            hours_ago=6,
        )
        self.recent_student = self._create_user(
            email='student@example.com',
            role='student',
            hours_ago=4,
        )

        self.group = Group.objects.create(name='Test Group', teacher=self.recent_teacher)
        lesson_start = timezone.now() - timedelta(hours=3)
        Lesson.objects.create(
            title='Алгебра',
            group=self.group,
            teacher=self.recent_teacher,
            start_time=lesson_start,
            end_time=lesson_start + timedelta(hours=1),
        )

    def _create_user(self, email, role, hours_ago):
        user = CustomUser.objects.create_user(
            email=email,
            password='StrongPass123',
            role=role,
        )
        CustomUser.objects.filter(pk=user.pk).update(
            created_at=timezone.now() - timedelta(hours=hours_ago)
        )
        return CustomUser.objects.get(pk=user.pk)

    def test_growth_periods_present(self):
        url = reverse('accounts:admin_stats')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        growth_periods = response.data.get('growth_periods')
        self.assertIsInstance(growth_periods, list)
        self.assertEqual(len(growth_periods), 4)

        day_entry = next((item for item in growth_periods if item['key'] == 'day'), None)
        self.assertIsNotNone(day_entry)
        self.assertGreaterEqual(day_entry['teachers'], 1)
        self.assertGreaterEqual(day_entry['students'], 1)
        self.assertGreaterEqual(day_entry['lessons'], 1)
        self.assertEqual(day_entry['teachers'] + day_entry['students'], day_entry['total_users'])

        half_year_entry = next((item for item in growth_periods if item['key'] == 'half_year'), None)
        self.assertIsNotNone(half_year_entry)
        self.assertGreaterEqual(half_year_entry['lessons'], day_entry['lessons'])


class AdminTeacherSubscriptionViewTests(APITestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            email='chief@example.com',
            password='StrongPass123',
            role='admin',
            is_staff=True,
            is_superuser=True,
        )
        self.teacher = CustomUser.objects.create_user(
            email='mentor@example.com',
            password='StrongPass123',
            role='teacher',
        )
        self.client.force_authenticate(user=self.admin)
        self.url = reverse('accounts:admin_teacher_subscription', args=[self.teacher.id])

    def test_admin_can_activate_subscription_with_default_duration(self):
        response = self.client.post(self.url, {'action': 'activate'}, format='json')

        self.assertEqual(response.status_code, 200)
        subscription = Subscription.objects.get(user=self.teacher)
        self.assertEqual(subscription.status, Subscription.STATUS_ACTIVE)
        self.assertEqual(subscription.plan, Subscription.PLAN_MONTHLY)
        self.assertFalse(subscription.auto_renew)

        now = timezone.now()
        self.assertGreaterEqual(subscription.expires_at, now + timedelta(days=27))
        self.assertLessEqual(subscription.expires_at, now + timedelta(days=29))

    def test_admin_can_deactivate_subscription(self):
        self.client.post(self.url, {'action': 'activate'}, format='json')

        response = self.client.post(self.url, {'action': 'deactivate'}, format='json')

        self.assertEqual(response.status_code, 200)
        subscription = Subscription.objects.get(user=self.teacher)
        self.assertEqual(subscription.status, Subscription.STATUS_PENDING)
        self.assertLessEqual(subscription.expires_at, timezone.now())
        self.assertFalse(subscription.auto_renew)

    def test_non_admin_cannot_manage_subscription(self):
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(self.url, {'action': 'activate'}, format='json')

        self.assertEqual(response.status_code, 403)


class AdminTeacherStorageViewTests(APITestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            email='chief2@example.com',
            password='StrongPass123',
            role='admin',
            is_staff=True,
            is_superuser=True,
        )
        self.teacher = CustomUser.objects.create_user(
            email='mentor2@example.com',
            password='StrongPass123',
            role='teacher',
        )
        self.client.force_authenticate(user=self.admin)
        self.url = reverse('accounts:admin_teacher_storage', args=[self.teacher.id])

    def test_admin_can_add_extra_storage(self):
        response = self.client.post(self.url, {'extra_gb': 15}, format='json')

        self.assertEqual(response.status_code, 200)
        subscription = Subscription.objects.get(user=self.teacher)
        self.assertEqual(subscription.extra_storage_gb, 15)
        self.assertEqual(response.data['subscription']['extra_storage_gb'], 15)
        self.assertEqual(response.data['subscription']['total_storage_gb'], subscription.total_storage_gb)

    def test_rejects_invalid_storage_payload(self):
        response = self.client.post(self.url, {'extra_gb': 0}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_non_admin_cannot_add_storage(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(self.url, {'extra_gb': 5}, format='json')
        self.assertEqual(response.status_code, 403)
