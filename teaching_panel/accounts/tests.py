from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import CustomUser
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
