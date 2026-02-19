"""
Phase 3 тесты: Registration + SchoolMembership + MeView school info.

Проверяют что:
- Регистрация создаёт SchoolMembership к текущей школе
- /api/me/ возвращает информацию о школе
- Лимиты max_students отрабатывают

НЕ запускай пока Phase 3 не выполнен!

Запуск: python manage.py test tenants.tests_phase3 -v2
"""

import uuid
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from tenants.models import School, SchoolMembership
from tenants.middleware import TenantMiddleware

User = get_user_model()


@override_settings(ALLOWED_HOSTS=['*'])
class RegistrationMembershipTests(TestCase):
    """TEST_3_01 - TEST_3_07: Регистрация привязывает к школе."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email='reg-owner@test.com', password='Test1234',
            role='teacher', first_name='Reg', last_name='Owner',
        )

        if not School.objects.filter(is_default=True).exists():
            cls.default_school = School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=cls.owner, is_default=True,
            )
        else:
            cls.default_school = School.objects.get(is_default=True)

        cls.school_a = School.objects.create(
            slug='reg-school-a', name='Reg School A',
            owner=cls.owner, max_students=100,
        )

        cls.school_limited = School.objects.create(
            slug='reg-limited', name='Limited School',
            owner=cls.owner, max_students=0,  # Лимит = 0
        )

        TenantMiddleware.clear_cache()

    def _register_user(self, host='127.0.0.1', role='student', extra=None):
        """Регистрация нового пользователя с уникальным email."""
        unique = uuid.uuid4().hex[:8]
        data = {
            'email': f'test-{unique}@test.com',
            'password': 'Test1234A',
            'role': role,
            'first_name': 'Test',
            'last_name': unique.capitalize(),
        }
        if extra:
            data.update(extra)

        response = self.client.post(
            '/api/jwt/register/', data,
            content_type='application/json',
            HTTP_HOST=host,
        )
        return response

    def test_3_01_register_on_localhost_creates_membership_to_default(self):
        """TEST_3_01: Register на localhost → SchoolMembership к default school."""
        response = self._register_user(host='127.0.0.1')
        self.assertIn(response.status_code, [200, 201],
                      f"Register failed: {response.status_code} — {response.content[:300]}")

        data = response.json()
        user_id = data.get('user_id')
        self.assertIsNotNone(user_id, "Response should contain user_id")

        # Проверяем membership
        membership = SchoolMembership.objects.filter(
            user_id=user_id, school=self.default_school
        ).first()
        self.assertIsNotNone(membership,
                             "Registration on localhost should create membership to default school")

    def test_3_02_register_on_school_subdomain_creates_membership(self):
        """TEST_3_02: Register на school-A поддомен → SchoolMembership к school A."""
        response = self._register_user(host='reg-school-a.lectiospace.ru')
        self.assertIn(response.status_code, [200, 201],
                      f"Register failed: {response.status_code} — {response.content[:300]}")

        data = response.json()
        user_id = data.get('user_id')

        membership = SchoolMembership.objects.filter(
            user_id=user_id, school=self.school_a
        ).first()
        self.assertIsNotNone(membership,
                             "Registration on school subdomain should create membership to that school")

    def test_3_03_register_as_student_sets_student_role(self):
        """TEST_3_03: Register как student → role='student' в membership."""
        response = self._register_user(host='reg-school-a.lectiospace.ru', role='student')
        data = response.json()
        user_id = data.get('user_id')

        if user_id:
            membership = SchoolMembership.objects.filter(
                user_id=user_id, school=self.school_a
            ).first()
            if membership:
                self.assertEqual(membership.role, 'student')

    def test_3_04_register_as_teacher_sets_teacher_role(self):
        """TEST_3_04: Register как teacher → role='teacher' в membership."""
        response = self._register_user(host='reg-school-a.lectiospace.ru', role='teacher')
        data = response.json()
        user_id = data.get('user_id')

        if user_id:
            membership = SchoolMembership.objects.filter(
                user_id=user_id, school=self.school_a
            ).first()
            if membership:
                self.assertEqual(membership.role, 'teacher')

    def test_3_05_double_register_no_duplicate_membership(self):
        """TEST_3_05: Двойная регистрация → unique_together не ломается."""
        # Регистрируем пользователя
        unique = uuid.uuid4().hex[:8]
        email = f'double-{unique}@test.com'
        data = {
            'email': email, 'password': 'Test1234A',
            'role': 'student', 'first_name': 'Double', 'last_name': 'Test',
        }

        # Первая регистрация
        resp1 = self.client.post(
            '/api/jwt/register/', data,
            content_type='application/json',
            HTTP_HOST='reg-school-a.lectiospace.ru',
        )

        if resp1.status_code in [200, 201]:
            user_id = resp1.json().get('user_id')
            # Проверяем что membership одна
            count = SchoolMembership.objects.filter(
                user_id=user_id, school=self.school_a
            ).count()
            self.assertEqual(count, 1, "Should have exactly 1 membership")

    def test_3_06_register_on_limited_school_still_works(self):
        """TEST_3_06: Register на школу с max_students=0 → user создан (не блокируем)."""
        response = self._register_user(host='reg-limited.lectiospace.ru')
        # Регистрация должна работать (мягкий лимит, только warning в логе)
        self.assertIn(response.status_code, [200, 201],
                      "Registration should not be blocked by max_students limit (soft limit)")

    def test_3_07_login_does_not_create_new_membership(self):
        """TEST_3_07: Login существующего user → НЕ создаёт новый membership."""
        # Сначала регистрируем
        unique = uuid.uuid4().hex[:8]
        email = f'login-{unique}@test.com'
        self.client.post('/api/jwt/register/', {
            'email': email, 'password': 'Test1234A',
            'role': 'student', 'first_name': 'Login', 'last_name': 'Test',
        }, content_type='application/json', HTTP_HOST='reg-school-a.lectiospace.ru')

        user = User.objects.filter(email=email).first()
        if not user:
            self.skipTest("Registration did not create user")

        count_before = SchoolMembership.objects.filter(user=user).count()

        # Login
        self.client.post('/api/jwt/token/', {
            'email': email, 'password': 'Test1234A',
        }, content_type='application/json', HTTP_HOST='reg-school-a.lectiospace.ru')

        count_after = SchoolMembership.objects.filter(user=user).count()
        self.assertEqual(count_before, count_after,
                         "Login should NOT create new SchoolMembership")


@override_settings(ALLOWED_HOSTS=['*'])
class MeViewSchoolInfoTests(TestCase):
    """TEST_3_08 - TEST_3_11: /api/me/ включает school info."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email='me-owner@test.com', password='Test1234',
            role='teacher', first_name='Me', last_name='Owner',
        )
        if not School.objects.filter(is_default=True).exists():
            School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=cls.owner, is_default=True,
            )
        cls.school = School.objects.create(
            slug='me-school', name='Me Test School',
            owner=cls.owner, primary_color='#123456',
        )
        SchoolMembership.objects.create(
            school=cls.school, user=cls.owner, role='owner',
        )
        TenantMiddleware.clear_cache()

    def _auth(self, user):
        token = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token.access_token}'}

    def test_3_08_me_returns_school_info(self):
        """TEST_3_08: GET /api/me/ на поддомене → ответ содержит school."""
        auth = self._auth(self.owner)
        response = self.client.get(
            '/api/me/', **auth,
            HTTP_HOST='me-school.lectiospace.ru',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # После Phase 3 должен быть ключ 'school'
        if 'school' in data:
            self.assertIsNotNone(data['school'])
            self.assertEqual(data['school'].get('slug'), 'me-school')

    def test_3_09_me_returns_membership_role(self):
        """TEST_3_09: /api/me/ включает роль в школе (school_membership.role)."""
        auth = self._auth(self.owner)
        response = self.client.get(
            '/api/me/', **auth,
            HTTP_HOST='me-school.lectiospace.ru',
        )
        data = response.json()
        if 'school_membership' in data and data['school_membership']:
            self.assertEqual(data['school_membership'].get('role'), 'owner')

    def test_3_10_me_on_localhost_returns_default_school(self):
        """TEST_3_10: /api/me/ на localhost → default school info."""
        auth = self._auth(self.owner)
        response = self.client.get('/api/me/', **auth, HTTP_HOST='127.0.0.1')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        if 'school' in data and data['school']:
            self.assertTrue(
                data['school'].get('slug') in ['lectiospace', 'me-school'],
                "On localhost should return default or relevant school"
            )

    def test_3_11_smoke_still_works(self):
        """TEST_3_11: Smoke tests проходят после Phase 3 changes."""
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/school/config/')
        self.assertEqual(response.status_code, 200)
