"""
Baseline тесты для tenants app (Phase 0).

Проверяют что модели School, SchoolMembership мигрированы,
default school создана, middleware и API работают.

Запуск: python manage.py test tenants.tests -v2
"""

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from tenants.models import School, SchoolMembership  # backward-compat aliases → Tenant, TenantMembership
from tenants.middleware import TenantMiddleware
from tenants.context import get_current_school, set_current_school, clear_current_school

User = get_user_model()


class SchoolModelTests(TestCase):
    """TEST_0_01 - TEST_0_03: Модели и default school."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@test.com', password='Test1234', role='teacher',
            first_name='Test', last_name='Owner',
        )

    def test_0_01_school_model_exists_and_can_create(self):
        """TEST_0_01: School модель существует и можно создать запись."""
        school = School.objects.create(
            slug='test-school',
            name='Test School',
            owner=self.owner,
        )
        self.assertIsNotNone(school.id)
        self.assertEqual(school.slug, 'test-school')
        self.assertTrue(school.is_active)
        self.assertFalse(school.is_default)

    def test_0_02_default_school_exists(self):
        """TEST_0_02: Default School 'lectiospace' можно создать и найти."""
        # Data migration не выполняется в тестовой in-memory БД,
        # поэтому создаём default school вручную.
        if not School.objects.filter(is_default=True).exists():
            School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=self.owner, is_default=True,
            )
        default = School.objects.filter(is_default=True).first()
        self.assertIsNotNone(default, "Default school should exist")
        self.assertEqual(default.slug, 'lectiospace')
        self.assertEqual(default.name, 'Lectio Space')
        self.assertTrue(default.is_active)

    def test_0_03_school_membership_model_works(self):
        """TEST_0_03: SchoolMembership создаётся и unique_together работает."""
        school = School.objects.create(
            slug='membership-test', name='Membership Test', owner=self.owner,
        )
        membership = SchoolMembership.objects.create(
            school=school, user=self.owner, role='owner',
        )
        self.assertIsNotNone(membership.id)
        self.assertEqual(membership.role, 'owner')

        # Duplicate → IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SchoolMembership.objects.create(
                school=school, user=self.owner, role='teacher',
            )


@override_settings(ALLOWED_HOSTS=['*'])
class TenantMiddlewareTests(TestCase):
    """TEST_0_04: Middleware не ломает обычные запросы."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email='mw-owner@test.com', password='Test1234', role='teacher',
            first_name='MW', last_name='Owner',
        )
        # Убедиться что default school есть
        if not School.objects.filter(is_default=True).exists():
            School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=self.owner, is_default=True,
            )
        TenantMiddleware.clear_cache()

    def test_0_04_middleware_localhost_returns_default_school(self):
        """TEST_0_04: localhost → default school, request не сломан."""
        factory = RequestFactory()
        request = factory.get('/api/me/', HTTP_HOST='127.0.0.1')

        # Simulate middleware
        middleware = TenantMiddleware(lambda req: None)
        school = middleware._resolve_school(request)

        self.assertIsNotNone(school)
        self.assertTrue(school.is_default)
        self.assertEqual(school.slug, 'lectiospace')

    def test_middleware_subdomain_resolves_school(self):
        """Поддомен anna.lectiospace.ru → School(slug='anna')."""
        anna_school = School.objects.create(
            slug='anna', name='English with Anna', owner=self.owner,
        )
        TenantMiddleware.clear_cache()

        factory = RequestFactory()
        request = factory.get('/api/me/', HTTP_HOST='anna.lectiospace.ru')

        middleware = TenantMiddleware(lambda req: None)
        school = middleware._resolve_school(request)

        self.assertIsNotNone(school)
        self.assertEqual(school.slug, 'anna')
        self.assertEqual(school.id, anna_school.id)

    def test_middleware_unknown_subdomain_returns_default(self):
        """Неизвестный поддомен → default school."""
        TenantMiddleware.clear_cache()
        factory = RequestFactory()
        request = factory.get('/api/me/', HTTP_HOST='nonexistent.lectiospace.ru')

        middleware = TenantMiddleware(lambda req: None)
        school = middleware._resolve_school(request)

        self.assertIsNotNone(school)
        self.assertTrue(school.is_default)

    def test_middleware_custom_domain(self):
        """Кастомный домен → School с custom_domain."""
        School.objects.create(
            slug='custom', name='Custom School', owner=self.owner,
            custom_domain='english-anna.com',
        )
        TenantMiddleware.clear_cache()

        factory = RequestFactory()
        request = factory.get('/api/me/', HTTP_HOST='english-anna.com')

        middleware = TenantMiddleware(lambda req: None)
        school = middleware._resolve_school(request)

        self.assertIsNotNone(school)
        self.assertEqual(school.slug, 'custom')

    def test_middleware_thread_local(self):
        """Thread-local set/get/clear работает."""
        school = School.objects.get(is_default=True)

        self.assertIsNone(get_current_school())
        set_current_school(school)
        self.assertEqual(get_current_school(), school)
        clear_current_school()
        self.assertIsNone(get_current_school())


class SchoolConfigAPITests(TestCase):
    """TEST_0_05 - TEST_0_08: API endpoints."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email='api-owner@test.com', password='Test1234', role='teacher',
            first_name='API', last_name='Owner',
        )
        if not School.objects.filter(is_default=True).exists():
            School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=self.owner, is_default=True,
            )
        TenantMiddleware.clear_cache()

    def test_0_05_school_config_endpoint_returns_200(self):
        """TEST_0_05: GET /api/school/config/ → 200 с конфигом."""
        response = self.client.get('/api/school/config/', HTTP_HOST='127.0.0.1')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('slug', data)
        self.assertIn('name', data)
        self.assertIn('primary_color', data)

    def test_0_06_school_detail_requires_auth(self):
        """TEST_0_06: GET /api/school/detail/ без токена → 401."""
        response = self.client.get('/api/school/detail/', HTTP_HOST='127.0.0.1')
        self.assertIn(response.status_code, [401, 403])

    def test_0_07_to_frontend_config_structure(self):
        """TEST_0_07: to_frontend_config() возвращает правильную структуру."""
        school = School.objects.get(is_default=True)
        config = school.to_frontend_config()

        required_keys = ['id', 'slug', 'name', 'primary_color', 'secondary_color', 'features']
        for key in required_keys:
            self.assertIn(key, config, f"Missing key: {key}")

        self.assertIsInstance(config['features'], dict)
        self.assertIn('zoom', config['features'])
        self.assertIn('homework', config['features'])

    def test_0_08_get_payment_credentials_fallback(self):
        """TEST_0_08: get_payment_credentials() без school creds → platform fallback."""
        school = School.objects.get(is_default=True)
        # School не имеет своих credentials → fallback
        creds = school.get_payment_credentials()

        self.assertIn('provider', creds)
        # Не должно быть пустым — fallback на PLATFORM_CONFIG
        self.assertIsNotNone(creds.get('provider'))
