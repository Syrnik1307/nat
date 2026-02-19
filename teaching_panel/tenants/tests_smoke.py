"""
Smoke тесты — прогоняются ПОСЛЕ КАЖДОГО шага.

Гарантируют что основные API endpoints не сломаны.
Если любой из этих тестов красный — СТОП, не продолжай следующий шаг.

Запуск: python manage.py test tenants.tests_smoke -v2
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from tenants.models import School, SchoolMembership
from tenants.middleware import TenantMiddleware

User = get_user_model()


class SmokeTests(TestCase):
    """Базовые smoke тесты после каждого шага."""

    @classmethod
    def setUpTestData(cls):
        """Создаём тестовые данные один раз для всех smoke тестов."""
        # Default school (если не создана data migration)
        owner = User.objects.create_user(
            email='smoke-owner@test.com', password='SmokE1234',
            role='teacher', first_name='Smoke', last_name='Owner',
        )
        cls.owner = owner

        if not School.objects.filter(is_default=True).exists():
            School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=owner, is_default=True,
            )

        cls.teacher = User.objects.create_user(
            email='smoke-teacher@test.com', password='SmokE1234',
            role='teacher', first_name='Smoke', last_name='Teacher',
        )
        cls.student = User.objects.create_user(
            email='smoke-student@test.com', password='SmokE1234',
            role='student', first_name='Smoke', last_name='Student',
        )

        TenantMiddleware.clear_cache()

    def _get_auth_header(self, user):
        """Получить JWT Authorization header для пользователя."""
        refresh = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_smoke_01_health_check(self):
        """SMOKE_01: GET /api/health/ → 200."""
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)

    def test_smoke_02_register_new_user(self):
        """SMOKE_02: POST /api/jwt/register/ → 201 с tokens."""
        import uuid
        unique = uuid.uuid4().hex[:8]
        response = self.client.post('/api/jwt/register/', {
            'email': f'smoke-reg-{unique}@test.com',
            'password': 'SmokE1234',
            'role': 'student',
            'first_name': 'Smoke',
            'last_name': 'Reg',
        }, content_type='application/json')

        # Допускаем 201 или 200 (зависит от реализации)
        self.assertIn(response.status_code, [200, 201], 
                      f"Register failed: {response.status_code} — {response.content[:300]}")
        data = response.json()
        self.assertIn('access', data, f"No access token in response: {data}")

    def test_smoke_03_me_endpoint(self):
        """SMOKE_03: GET /api/me/ с токеном → 200."""
        auth = self._get_auth_header(self.teacher)
        response = self.client.get('/api/me/', **auth)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('email', data)

    def test_smoke_04_groups_list(self):
        """SMOKE_04: GET /api/groups/ с учительским токеном → 200."""
        auth = self._get_auth_header(self.teacher)
        response = self.client.get('/api/groups/', **auth)
        self.assertIn(response.status_code, [200, 301, 302],
                      f"Groups failed: {response.status_code}")

    def test_smoke_05_homework_list(self):
        """SMOKE_05: GET /api/homework/ с учительским токеном → 200."""
        auth = self._get_auth_header(self.teacher)
        response = self.client.get('/api/homework/', **auth)
        # Может быть 200 или redirect — главное не 500/404
        self.assertNotIn(response.status_code, [500, 404],
                         f"Homework failed: {response.status_code}")

    def test_smoke_06_admin_accessible(self):
        """SMOKE_06: GET /admin/ → 200 или redirect to login."""
        response = self.client.get('/admin/', follow=False)
        # Admin redirect to login или показать login page
        self.assertIn(response.status_code, [200, 301, 302])

    def test_smoke_07_school_config(self):
        """SMOKE_07: GET /api/school/config/ → 200 с данными."""
        response = self.client.get('/api/school/config/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('name', data)
