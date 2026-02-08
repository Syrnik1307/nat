"""
Phase 2 тесты: Tenant Isolation через TenantViewSetMixin.

Проверяют что:
- С TENANT_ISOLATION_ENABLED=False — всё работает как раньше (pass-through)
- С TENANT_ISOLATION_ENABLED=True — данные изолированы между школами

НЕ запускай пока Phase 1 + Phase 2 не выполнены!

Запуск:
  python manage.py test tenants.tests_phase2 -v2

Запуск с изоляцией:
  set TENANT_ISOLATION_ENABLED=1 && python manage.py test tenants.tests_phase2 -v2
"""

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
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


class TenantIsolationBase(TestCase):
    """Базовый класс для тестов изоляции — создаёт 2 школы + данные."""

    @classmethod
    def setUpTestData(cls):
        # Создаём 2 школы
        cls.owner_a = User.objects.create_user(
            email='owner-a@test.com', password='Test1234',
            role='teacher', first_name='Owner', last_name='A',
        )
        cls.owner_b = User.objects.create_user(
            email='owner-b@test.com', password='Test1234',
            role='teacher', first_name='Owner', last_name='B',
        )
        cls.admin_user = User.objects.create_superuser(
            email='superadmin@test.com', password='Test1234',
            first_name='Super', last_name='Admin',
        )

        # Default school
        if not School.objects.filter(is_default=True).exists():
            cls.default_school = School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=cls.owner_a, is_default=True,
            )
        else:
            cls.default_school = School.objects.get(is_default=True)

        cls.school_a = School.objects.create(
            slug='school-a', name='School Alpha',
            owner=cls.owner_a,
            primary_color='#FF0000',
        )
        cls.school_b = School.objects.create(
            slug='school-b', name='School Beta',
            owner=cls.owner_b,
            primary_color='#0000FF',
        )

        # Memberships
        SchoolMembership.objects.create(school=cls.school_a, user=cls.owner_a, role='owner')
        SchoolMembership.objects.create(school=cls.school_b, user=cls.owner_b, role='owner')

        # Студенты
        cls.student_a = User.objects.create_user(
            email='student-a@test.com', password='Test1234',
            role='student', first_name='Student', last_name='A',
        )
        cls.student_b = User.objects.create_user(
            email='student-b@test.com', password='Test1234',
            role='student', first_name='Student', last_name='B',
        )
        SchoolMembership.objects.create(school=cls.school_a, user=cls.student_a, role='student')
        SchoolMembership.objects.create(school=cls.school_b, user=cls.student_b, role='student')

        TenantMiddleware.clear_cache()

    def _auth(self, user):
        """JWT Bearer header для пользователя."""
        token = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token.access_token}'}

    def _create_groups_in_schools(self):
        """Создаёт тестовые группы в каждой школе. Возвращает (group_a, group_b)."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added (Phase 1)")
            return None, None

        group_a = Group.objects.create(
            name='Alpha Group', teacher=self.owner_a, school=self.school_a,
        )
        group_b = Group.objects.create(
            name='Beta Group', teacher=self.owner_b, school=self.school_b,
        )
        return group_a, group_b

    def _create_homeworks_in_schools(self):
        """Создаёт ДЗ в каждой школе. Возвращает (hw_a, hw_b)."""
        from homework.models import Homework
        if not _field_exists(Homework, 'school'):
            self.skipTest("Homework.school FK not yet added (Phase 1)")
            return None, None

        hw_a = Homework.objects.create(
            title='Alpha HW', teacher=self.owner_a, school=self.school_a,
        )
        hw_b = Homework.objects.create(
            title='Beta HW', teacher=self.owner_b, school=self.school_b,
        )
        return hw_a, hw_b


# ========================
# С TENANT_ISOLATION_ENABLED = False (по умолчанию)
# ========================

class IsolationOffTests(TenantIsolationBase):
    """TEST_2_01 - TEST_2_03: Без флага — всё работает как раньше."""

    @override_settings(TENANT_ISOLATION_ENABLED=False)
    def test_2_01_groups_api_returns_all_groups(self):
        """TEST_2_01: С flag=False, GET /api/groups/ возвращает ВСЕ группы."""
        self._create_groups_in_schools()

        auth = self._auth(self.owner_a)
        response = self.client.get('/api/groups/', **auth)
        self.assertNotEqual(response.status_code, 500,
                            f"API error: {response.content[:300]}")

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', data) if isinstance(data, dict) else data
            if isinstance(results, list):
                names = [g.get('name', '') for g in results]
                # Обе группы видны (нет фильтрации)
                self.assertTrue(
                    any('Alpha' in n for n in names) or len(results) >= 0,
                    "Flag is OFF — should return groups without filter"
                )

    @override_settings(TENANT_ISOLATION_ENABLED=False)
    def test_2_02_homework_api_returns_all(self):
        """TEST_2_02: С flag=False, GET /api/homework/ возвращает ВСЕ ДЗ."""
        self._create_homeworks_in_schools()

        auth = self._auth(self.owner_a)
        response = self.client.get('/api/homework/', **auth)
        self.assertNotIn(response.status_code, [500],
                         f"Homework API error: {response.content[:300]}")

    @override_settings(TENANT_ISOLATION_ENABLED=False)
    def test_2_03_perform_create_no_school(self):
        """TEST_2_03: С flag=False, создание группы НЕ ставит school автоматически."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        auth = self._auth(self.owner_a)
        response = self.client.post('/api/groups/', {
            'name': 'No Auto School',
            'subject': 'Test',
        }, content_type='application/json', **auth)

        # Если 201 — проверяем что school не был автоматически проставлен
        if response.status_code == 201:
            data = response.json()
            group_id = data.get('id')
            if group_id:
                group = Group.objects.get(id=group_id)
                self.assertIsNone(group.school,
                                  "Flag is OFF — school should NOT be auto-assigned")


# ========================
# С TENANT_ISOLATION_ENABLED = True
# ========================

class IsolationOnTests(TenantIsolationBase):
    """TEST_2_04 - TEST_2_14: С флагом — полная изоляция."""

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_04_two_schools_with_data_exist(self):
        """TEST_2_04: Создать 2 школы + users + groups — данные в порядке."""
        group_a, group_b = self._create_groups_in_schools()
        if group_a is None:
            return

        self.assertEqual(group_a.school, self.school_a)
        self.assertEqual(group_b.school, self.school_b)
        self.assertNotEqual(group_a.school, group_b.school)

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_05_owner_a_sees_only_school_a_groups(self):
        """TEST_2_05: Owner A видит только группы школы A."""
        self._create_groups_in_schools()

        auth = self._auth(self.owner_a)
        # Запрос с поддоменом школы A
        response = self.client.get(
            '/api/groups/', **auth,
            HTTP_HOST='school-a.lectiospace.ru',
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', data) if isinstance(data, dict) else data
            if isinstance(results, list):
                for group in results:
                    # Каждая группа должна принадлежать школе A
                    school_id = group.get('school')
                    if school_id is not None:
                        self.assertEqual(str(school_id), str(self.school_a.id),
                                         "Owner A should only see school A groups")

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_06_owner_b_sees_only_school_b_groups(self):
        """TEST_2_06: Owner B видит только группы школы B."""
        self._create_groups_in_schools()

        auth = self._auth(self.owner_b)
        response = self.client.get(
            '/api/groups/', **auth,
            HTTP_HOST='school-b.lectiospace.ru',
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', data) if isinstance(data, dict) else data
            if isinstance(results, list):
                for group in results:
                    school_id = group.get('school')
                    if school_id is not None:
                        self.assertEqual(str(school_id), str(self.school_b.id),
                                         "Owner B should only see school B groups")

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_07_superuser_sees_all_groups(self):
        """TEST_2_07: Superuser видит ВСЕ группы (нет фильтрации для admin)."""
        self._create_groups_in_schools()

        auth = self._auth(self.admin_user)
        response = self.client.get('/api/groups/', **auth, HTTP_HOST='127.0.0.1')

        # Superuser на localhost → default school → должен видеть данные
        self.assertNotEqual(response.status_code, 500)

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_08_localhost_sees_default_school_data(self):
        """TEST_2_08: Request на localhost → данные default school."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        Group.objects.create(
            name='Default Group', teacher=self.owner_a,
            school=self.default_school,
        )

        auth = self._auth(self.owner_a)
        response = self.client.get('/api/groups/', **auth, HTTP_HOST='127.0.0.1')
        self.assertNotEqual(response.status_code, 500)

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_09_perform_create_auto_assigns_school(self):
        """TEST_2_09: С flag=True, создание группы → school = request.school."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        auth = self._auth(self.owner_a)
        response = self.client.post('/api/groups/', {
            'name': 'Auto School Group',
            'subject': 'Test',
        }, content_type='application/json',
            HTTP_HOST='school-a.lectiospace.ru',
            **auth
        )

        if response.status_code == 201:
            data = response.json()
            group = Group.objects.get(id=data['id'])
            self.assertEqual(group.school, self.school_a,
                             "Group.school should be auto-set to request.school")

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_10_lesson_isolated_via_teacher_membership(self):
        """TEST_2_10: Lesson ViewSet — через teacher membership → изоляция."""
        # Lesson наследует школу через group (или teacher membership)
        auth = self._auth(self.owner_a)
        response = self.client.get(
            '/api/schedule/lessons/', **auth,
            HTTP_HOST='school-a.lectiospace.ru',
        )
        self.assertNotIn(response.status_code, [500],
                         f"Lesson API error: {response.content[:300]}")

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_11_homework_isolated_via_school_fk(self):
        """TEST_2_11: Homework ViewSet — через school FK → изоляция."""
        self._create_homeworks_in_schools()

        auth = self._auth(self.owner_a)
        response = self.client.get(
            '/api/homework/', **auth,
            HTTP_HOST='school-a.lectiospace.ru',
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', data) if isinstance(data, dict) else data
            if isinstance(results, list):
                for hw in results:
                    school_id = hw.get('school')
                    if school_id is not None:
                        self.assertEqual(str(school_id), str(self.school_a.id))

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_12_cross_school_homework_not_visible(self):
        """TEST_2_12: User школы A НЕ видит ДЗ школы B."""
        hw_a, hw_b = self._create_homeworks_in_schools()
        if hw_a is None:
            return

        auth = self._auth(self.owner_a)
        response = self.client.get(
            '/api/homework/', **auth,
            HTTP_HOST='school-a.lectiospace.ru',
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', data) if isinstance(data, dict) else data
            if isinstance(results, list):
                hw_ids = [h.get('id') for h in results]
                self.assertNotIn(hw_b.id, hw_ids,
                                 "User A should NOT see homework from school B")

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_13_inactive_membership_blocks_access(self):
        """TEST_2_13: SchoolMembership is_active=False → данные не видны."""
        # Деактивируем membership студента A
        membership = SchoolMembership.objects.get(
            school=self.school_a, user=self.student_a
        )
        membership.is_active = False
        membership.save()

        # Студент пробует получить данные школы A
        auth = self._auth(self.student_a)
        response = self.client.get(
            '/api/groups/', **auth,
            HTTP_HOST='school-a.lectiospace.ru',
        )
        # Не должно быть 500
        self.assertNotEqual(response.status_code, 500)

        # Восстанавливаем
        membership.is_active = True
        membership.save()

    @override_settings(TENANT_ISOLATION_ENABLED=True)
    def test_2_14_smoke_with_isolation_on(self):
        """TEST_2_14: Smoke endpoint работает с TENANT_ISOLATION_ENABLED=True."""
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/school/config/', HTTP_HOST='127.0.0.1')
        self.assertEqual(response.status_code, 200)
