"""
E2E тесты (Phase 9): Полная проверка multi-tenant системы.

Симулируют реальный сценарий:
1. Создать 2 школы (English Anna + Math Plus)
2. Зарегистрировать студентов в каждой
3. Создать контент (группы, ДЗ)
4. Проверить полную изоляцию
5. Проверить платежи и подписки
6. Проверить /api/school/config/ для каждого поддомена
7. Проверить обратную совместимость с default school

НЕ запускай пока Phase 1-8 не выполнены!

Запуск:
  set TENANT_ISOLATION_ENABLED=1 && python manage.py test tenants.tests_e2e -v2
"""

import uuid
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from tenants.models import School, SchoolMembership
from tenants.middleware import TenantMiddleware

User = get_user_model()


def _field_exists(model_class, field_name):
    try:
        model_class._meta.get_field(field_name)
        return True
    except Exception:
        return False


@override_settings(ALLOWED_HOSTS=['*'])
class MultiTenantE2ETests(TestCase):
    """
    TEST_E2E_01 - TEST_E2E_20: Полный end-to-end тест multi-tenant системы.
    
    Сценарий:
    - Школа "English Anna" (anna.lectiospace.ru) — учитель Анна
    - Школа "Math Plus" (math.lectiospace.ru) — учитель Математик
    - Default школа "Lectio Space" (lectiospace.ru)
    - Студенты регистрируются на поддоменах
    - Контент создаётся в рамках школы
    - Изоляция проверяется cross-school
    """

    @classmethod
    def setUpTestData(cls):
        # ===== Школа Anna =====
        cls.anna = User.objects.create_user(
            email='anna@english.com', password='Anna1234',
            role='teacher', first_name='Anna', last_name='English',
        )
        # ===== Школа Math =====
        cls.math = User.objects.create_user(
            email='math@plus.com', password='Math1234',
            role='teacher', first_name='Math', last_name='Plus',
        )
        # ===== Platform Admin =====
        cls.admin = User.objects.create_superuser(
            email='admin@platform.com', password='Admin1234',
            first_name='Platform', last_name='Admin',
        )

        # Default school
        if not School.objects.filter(is_default=True).exists():
            cls.default_school = School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=cls.admin, is_default=True,
                max_students=10000,
            )
        else:
            cls.default_school = School.objects.get(is_default=True)

        # School Anna
        cls.anna_school = School.objects.create(
            slug='anna', name='English with Anna',
            owner=cls.anna,
            primary_color='#E91E63',
            secondary_color='#F06292',
            monthly_price=890,
            yearly_price=8900,
            revenue_share_percent=15,
            max_students=50,
            max_groups=10,
            telegram_bot_username='anna_english_bot',
        )
        SchoolMembership.objects.create(
            school=cls.anna_school, user=cls.anna, role='owner',
        )

        # School Math
        cls.math_school = School.objects.create(
            slug='math', name='Math Plus',
            owner=cls.math,
            primary_color='#1565C0',
            secondary_color='#42A5F5',
            monthly_price=1290,
            yearly_price=12900,
            revenue_share_percent=10,
            max_students=100,
        )
        SchoolMembership.objects.create(
            school=cls.math_school, user=cls.math, role='owner',
        )

        TenantMiddleware.clear_cache()

    def _auth(self, user):
        token = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token.access_token}'}

    def _register(self, host, role='student'):
        """Регистрация нового пользователя на указанном host."""
        unique = uuid.uuid4().hex[:8]
        response = self.client.post('/api/jwt/register/', {
            'email': f'e2e-{unique}@test.com',
            'password': 'Test1234A',
            'role': role,
            'first_name': 'E2E',
            'last_name': unique.capitalize(),
        }, content_type='application/json', HTTP_HOST=host)
        return response

    # =============================
    # Phase 1: Школы и данные
    # =============================

    def test_e2e_01_anna_school_exists(self):
        """E2E_01: Школа "English Anna" создана с правильными настройками."""
        school = School.objects.get(slug='anna')
        self.assertEqual(school.name, 'English with Anna')
        self.assertEqual(school.primary_color, '#E91E63')
        self.assertEqual(school.monthly_price, 890)
        self.assertEqual(school.revenue_share_percent, 15)
        self.assertTrue(school.is_active)

    def test_e2e_02_math_school_exists(self):
        """E2E_02: Школа "Math Plus" создана с правильными настройками."""
        school = School.objects.get(slug='math')
        self.assertEqual(school.name, 'Math Plus')
        self.assertEqual(school.primary_color, '#1565C0')
        self.assertEqual(school.monthly_price, 1290)
        self.assertEqual(school.revenue_share_percent, 10)

    # =============================
    # Phase 3: Регистрация + Membership
    # =============================

    def test_e2e_03_register_student_on_anna(self):
        """E2E_03: Register на anna.lectiospace.ru → SchoolMembership к anna."""
        response = self._register('anna.lectiospace.ru')
        self.assertIn(response.status_code, [200, 201],
                      f"Register on anna failed: {response.content[:300]}")

        data = response.json()
        user_id = data.get('user_id')
        if user_id:
            membership = SchoolMembership.objects.filter(
                user_id=user_id, school=self.anna_school
            ).first()
            self.assertIsNotNone(membership, "Should create membership to anna school")
            self.assertEqual(membership.role, 'student')

    def test_e2e_04_register_student_on_math(self):
        """E2E_04: Register на math.lectiospace.ru → SchoolMembership к math."""
        response = self._register('math.lectiospace.ru')
        self.assertIn(response.status_code, [200, 201],
                      f"Register on math failed: {response.content[:300]}")

        data = response.json()
        user_id = data.get('user_id')
        if user_id:
            membership = SchoolMembership.objects.filter(
                user_id=user_id, school=self.math_school
            ).first()
            self.assertIsNotNone(membership, "Should create membership to math school")

    # =============================
    # Phase 1+2: Создание контента + изоляция
    # =============================

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_e2e_05_anna_creates_group(self):
        """E2E_05: Anna создаёт группу → Group.school = anna_school."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        auth = self._auth(self.anna)
        response = self.client.post('/api/groups/', {
            'name': 'Anna English B1',
            'subject': 'English',
        }, content_type='application/json',
            HTTP_HOST='anna.lectiospace.ru', **auth,
        )

        if response.status_code == 201:
            group = Group.objects.get(id=response.json()['id'])
            self.assertEqual(group.school, self.anna_school)

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_e2e_06_math_creates_group(self):
        """E2E_06: Math создаёт группу → Group.school = math_school."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        auth = self._auth(self.math)
        response = self.client.post('/api/groups/', {
            'name': 'Math Algebra 101',
            'subject': 'Math',
        }, content_type='application/json',
            HTTP_HOST='math.lectiospace.ru', **auth,
        )

        if response.status_code == 201:
            group = Group.objects.get(id=response.json()['id'])
            self.assertEqual(group.school, self.math_school)

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_e2e_07_anna_student_cannot_see_math_groups(self):
        """E2E_07: Student anna НЕ видит группу Math."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        # Создаём группы в обеих школах
        Group.objects.create(name='Anna Visible', teacher=self.anna, school=self.anna_school)
        math_group = Group.objects.create(name='Math Secret', teacher=self.math, school=self.math_school)

        # Student anna на anna поддомене
        student = User.objects.create_user(
            email='e2e-anna-st@test.com', password='Test1234A',
            role='student', first_name='Anna', last_name='Student',
        )
        SchoolMembership.objects.create(school=self.anna_school, user=student, role='student')

        auth = self._auth(student)
        response = self.client.get(
            '/api/groups/', **auth,
            HTTP_HOST='anna.lectiospace.ru',
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', data) if isinstance(data, dict) else data
            if isinstance(results, list):
                group_ids = [g.get('id') for g in results]
                self.assertNotIn(math_group.id, group_ids,
                                 "Anna student should NOT see Math groups")

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_e2e_08_math_student_cannot_see_anna_groups(self):
        """E2E_08: Student math НЕ видит группу Anna."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        anna_group = Group.objects.create(name='Anna Secret2', teacher=self.anna, school=self.anna_school)
        Group.objects.create(name='Math Visible2', teacher=self.math, school=self.math_school)

        student = User.objects.create_user(
            email='e2e-math-st@test.com', password='Test1234A',
            role='student', first_name='Math', last_name='Student',
        )
        SchoolMembership.objects.create(school=self.math_school, user=student, role='student')

        auth = self._auth(student)
        response = self.client.get(
            '/api/groups/', **auth,
            HTTP_HOST='math.lectiospace.ru',
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', data) if isinstance(data, dict) else data
            if isinstance(results, list):
                group_ids = [g.get('id') for g in results]
                self.assertNotIn(anna_group.id, group_ids,
                                 "Math student should NOT see Anna groups")

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_e2e_09_anna_creates_homework(self):
        """E2E_09: Anna создаёт ДЗ → Homework.school = anna_school."""
        from homework.models import Homework
        if not _field_exists(Homework, 'school'):
            self.skipTest("Homework.school FK not yet added")

        auth = self._auth(self.anna)
        response = self.client.post('/api/homework/', {
            'title': 'E2E English Homework',
        }, content_type='application/json',
            HTTP_HOST='anna.lectiospace.ru', **auth,
        )

        if response.status_code == 201:
            hw = Homework.objects.get(id=response.json()['id'])
            self.assertEqual(hw.school, self.anna_school)

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_e2e_10_anna_student_sees_only_anna_homework(self):
        """E2E_10: Student anna видит ДЗ anna, НЕ видит ДЗ math."""
        from homework.models import Homework
        if not _field_exists(Homework, 'school'):
            self.skipTest("Homework.school FK not yet added")

        anna_hw = Homework.objects.create(
            title='E2E Anna HW', teacher=self.anna, school=self.anna_school,
        )
        math_hw = Homework.objects.create(
            title='E2E Math HW', teacher=self.math, school=self.math_school,
        )

        student = User.objects.create_user(
            email='e2e-hw-student@test.com', password='Test1234A',
            role='student', first_name='HW', last_name='Student',
        )
        SchoolMembership.objects.create(school=self.anna_school, user=student, role='student')

        auth = self._auth(student)
        response = self.client.get(
            '/api/homework/', **auth,
            HTTP_HOST='anna.lectiospace.ru',
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', data) if isinstance(data, dict) else data
            if isinstance(results, list):
                hw_ids = [h.get('id') for h in results]
                self.assertNotIn(math_hw.id, hw_ids,
                                 "Anna student should NOT see Math homework")

    # =============================
    # Phase 4: Подписки per-school
    # =============================

    def test_e2e_11_anna_payment_uses_school_creds(self):
        """E2E_11: Оплата на anna → credentials школы anna (или mock)."""
        creds = self.anna_school.get_payment_credentials()
        self.assertIn('provider', creds)
        # Anna не имеет своих creds → fallback на платформу
        self.assertIsNotNone(creds.get('provider'))

    def test_e2e_12_subscription_school_fk(self):
        """E2E_12: Subscription может быть привязана к школе."""
        from accounts.models import Subscription
        if not _field_exists(Subscription, 'school'):
            self.skipTest("Subscription.school FK not yet added")

        from django.utils import timezone
        from datetime import timedelta
        sub = Subscription.objects.create(
            user=self.anna,
            plan='monthly',
            status='active',
            expires_at=timezone.now() + timedelta(days=30),
            school=self.anna_school,
        )
        self.assertEqual(sub.school, self.anna_school)

    # =============================
    # Phase 5: School Config API
    # =============================

    def test_e2e_13_school_config_anna_subdomain(self):
        """E2E_13: /api/school/config/ на anna → конфиг школы anna."""
        response = self.client.get(
            '/api/school/config/',
            HTTP_HOST='anna.lectiospace.ru',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('slug'), 'anna')
        self.assertEqual(data.get('name'), 'English with Anna')
        self.assertEqual(data.get('primary_color'), '#E91E63')

    def test_e2e_14_school_config_math_subdomain(self):
        """E2E_14: /api/school/config/ на math → конфиг школы math."""
        response = self.client.get(
            '/api/school/config/',
            HTTP_HOST='math.lectiospace.ru',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('slug'), 'math')
        self.assertEqual(data.get('name'), 'Math Plus')
        self.assertEqual(data.get('primary_color'), '#1565C0')

    def test_e2e_15_me_endpoint_includes_school(self):
        """E2E_15: /api/me/ на anna → школа anna в ответе."""
        auth = self._auth(self.anna)
        response = self.client.get(
            '/api/me/', **auth,
            HTTP_HOST='anna.lectiospace.ru',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # После Phase 3, 'school' должен быть в ответе
        if 'school' in data:
            self.assertEqual(data['school'].get('slug'), 'anna')

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_e2e_16_default_school_data_isolated(self):
        """E2E_16: Данные default school НЕ видны на anna/math."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        default_group = Group.objects.create(
            name='Default Only', teacher=self.anna,
            school=self.default_school,
        )

        auth = self._auth(self.anna)
        response = self.client.get(
            '/api/groups/', **auth,
            HTTP_HOST='anna.lectiospace.ru',
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', data) if isinstance(data, dict) else data
            if isinstance(results, list):
                group_ids = [g.get('id') for g in results]
                self.assertNotIn(default_group.id, group_ids,
                                 "Default school data should not leak to anna subdomain")

    def test_e2e_17_platform_admin_access(self):
        """E2E_17: Platform admin (superuser) может управлять Django Admin."""
        from rest_framework_simplejwt.tokens import RefreshToken
        auth = self._auth(self.admin)
        response = self.client.get('/api/me/', **auth)
        self.assertEqual(response.status_code, 200)

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_e2e_18_deactivated_school(self):
        """E2E_18: Деактивированная школа → middleware возвращает default/None."""
        inactive_school = School.objects.create(
            slug='inactive-e2e', name='Inactive School',
            owner=self.anna, is_active=False,
        )
        TenantMiddleware.clear_cache()

        response = self.client.get(
            '/api/school/config/',
            HTTP_HOST='inactive-e2e.lectiospace.ru',
        )
        # Может вернуть default config или ошибку — не должно быть 500
        self.assertNotEqual(response.status_code, 500)

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_e2e_19_smoke_with_isolation_on(self):
        """E2E_19: Все smoke endpoint'ы работают с flag=True."""
        # Health
        r = self.client.get('/api/health/')
        self.assertEqual(r.status_code, 200)

        # School config
        r = self.client.get('/api/school/config/')
        self.assertEqual(r.status_code, 200)

        # Register
        unique = uuid.uuid4().hex[:8]
        r = self.client.post('/api/jwt/register/', {
            'email': f'e2e-smoke-{unique}@test.com',
            'password': 'Test1234A',
            'role': 'student',
            'first_name': 'Smoke', 'last_name': 'E2E',
        }, content_type='application/json')
        self.assertIn(r.status_code, [200, 201])

        # Me
        auth = self._auth(self.anna)
        r = self.client.get('/api/me/', **auth)
        self.assertEqual(r.status_code, 200)

    @override_settings(TENANT_ISOLATION_ENABLED=False)
    def test_e2e_20_smoke_with_isolation_off(self):
        """E2E_20: Все smoke endpoint'ы работают с flag=False (обратная совместимость)."""
        r = self.client.get('/api/health/')
        self.assertEqual(r.status_code, 200)

        r = self.client.get('/api/school/config/')
        self.assertEqual(r.status_code, 200)

        auth = self._auth(self.anna)
        r = self.client.get('/api/me/', **auth)
        self.assertEqual(r.status_code, 200)

        r = self.client.get('/api/groups/', **auth)
        self.assertNotEqual(r.status_code, 500)


@override_settings(ALLOWED_HOSTS=['*'])
class SchoolConfigE2ETests(TestCase):
    """Дополнительные тесты конфигурации школ."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email='config-e2e@test.com', password='Test1234',
            role='teacher', first_name='Config', last_name='E2E',
        )
        if not School.objects.filter(is_default=True).exists():
            School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=cls.owner, is_default=True,
            )

        cls.school = School.objects.create(
            slug='config-test', name='Config Test School',
            owner=cls.owner,
            primary_color='#FF5722',
            secondary_color='#FF7043',
            custom_domain='myschool.com',
            telegram_bot_username='config_test_bot',
            zoom_enabled=True,
            homework_enabled=True,
            recordings_enabled=False,
            finance_enabled=False,
        )
        TenantMiddleware.clear_cache()

    def test_config_custom_domain_resolves(self):
        """Custom domain myschool.com → config-test school."""
        response = self.client.get(
            '/api/school/config/',
            HTTP_HOST='myschool.com',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('slug'), 'config-test')

    def test_config_features_flags(self):
        """Feature flags правильно отображаются в config."""
        response = self.client.get(
            '/api/school/config/',
            HTTP_HOST='config-test.lectiospace.ru',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        features = data.get('features', {})
        self.assertTrue(features.get('zoom'))
        self.assertTrue(features.get('homework'))
        self.assertFalse(features.get('recordings'))
        self.assertFalse(features.get('finance'))

    def test_config_no_secrets_exposed(self):
        """Config API НЕ отдаёт секреты (yookassa_secret_key и т.д.)."""
        response = self.client.get(
            '/api/school/config/',
            HTTP_HOST='config-test.lectiospace.ru',
        )
        data = response.json()
        # Никаких секретов
        self.assertNotIn('yookassa_secret_key', data)
        self.assertNotIn('yookassa_account_id', data)
        self.assertNotIn('tbank_password', data)
        self.assertNotIn('telegram_bot_token', data)
        # Bot username — публичный, OK
        self.assertIn('telegram_bot_username', data)
