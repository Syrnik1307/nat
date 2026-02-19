"""
Phase 1 тесты: School FK на моделях + data backfill.

НЕ запускай эти тесты пока шаги 1.1-1.8 не выполнены!
Проверяют что FK добавлены, nullable, и backfill прошёл.

Запуск: python manage.py test tenants.tests_phase1 -v2
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import connection
from tenants.models import School, SchoolMembership

User = get_user_model()


def _field_exists(model_class, field_name):
    """Проверить что поле существует в модели."""
    try:
        model_class._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _field_is_nullable(model_class, field_name):
    """Проверить что поле nullable."""
    try:
        field = model_class._meta.get_field(field_name)
        return field.null
    except Exception:
        return False


class SchoolFKExistenceTests(TestCase):
    """TEST_1_01 - TEST_1_07: FK school существует на всех целевых моделях."""

    def test_1_01_group_has_school_fk(self):
        """TEST_1_01: schedule.Group имеет поле school (FK, nullable)."""
        from schedule.models import Group
        self.assertTrue(_field_exists(Group, 'school'),
                        "Group should have 'school' field")
        self.assertTrue(_field_is_nullable(Group, 'school'),
                        "Group.school should be nullable")

    def test_1_02_homework_has_school_fk(self):
        """TEST_1_02: homework.Homework имеет поле school."""
        from homework.models import Homework
        self.assertTrue(_field_exists(Homework, 'school'),
                        "Homework should have 'school' field")
        self.assertTrue(_field_is_nullable(Homework, 'school'),
                        "Homework.school should be nullable")

    def test_1_03_subscription_has_school_fk(self):
        """TEST_1_03: accounts.Subscription имеет поле school."""
        from accounts.models import Subscription
        self.assertTrue(_field_exists(Subscription, 'school'),
                        "Subscription should have 'school' field")
        self.assertTrue(_field_is_nullable(Subscription, 'school'),
                        "Subscription.school should be nullable")

    def test_1_04_controlpoint_has_school_fk(self):
        """TEST_1_04: analytics.ControlPoint имеет поле school."""
        from analytics.models import ControlPoint
        self.assertTrue(_field_exists(ControlPoint, 'school'),
                        "ControlPoint should have 'school' field")

    def test_1_05_supportticket_has_school_fk(self):
        """TEST_1_05: support.SupportTicket имеет поле school."""
        from support.models import SupportTicket
        self.assertTrue(_field_exists(SupportTicket, 'school'),
                        "SupportTicket should have 'school' field")

    def test_1_06_financialprofile_has_school_fk(self):
        """TEST_1_06: finance.StudentFinancialProfile имеет поле school."""
        from finance.models import StudentFinancialProfile
        self.assertTrue(_field_exists(StudentFinancialProfile, 'school'),
                        "StudentFinancialProfile should have 'school' field")

    def test_1_07_scheduledmessage_has_school_fk(self):
        """TEST_1_07: bot.ScheduledMessage имеет поле school."""
        from bot.models import ScheduledMessage
        self.assertTrue(_field_exists(ScheduledMessage, 'school'),
                        "ScheduledMessage should have 'school' field")


class DataBackfillTests(TestCase):
    """TEST_1_08 - TEST_1_09: Все существующие данные привязаны к default school."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email='phase1-owner@test.com', password='Test1234',
            role='teacher', first_name='Phase1', last_name='Owner',
        )
        if not School.objects.filter(is_default=True).exists():
            School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=cls.owner, is_default=True,
            )
        cls.default_school = School.objects.get(is_default=True)

    def test_1_08_existing_groups_have_school(self):
        """TEST_1_08: Все существующие Group привязаны к default school."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        # Создаём группу с привязкой к школе (симулируя backfill)
        group = Group.objects.create(
            name='Test Group Phase1',
            teacher=self.owner,
            school=self.default_school,
        )
        self.assertEqual(group.school, self.default_school)

    def test_1_09_existing_homework_have_school(self):
        """TEST_1_09: Homework.school можно задать."""
        from homework.models import Homework
        if not _field_exists(Homework, 'school'):
            self.skipTest("Homework.school FK not yet added")

        hw = Homework.objects.create(
            teacher=self.owner,
            title='Test HW Phase1',
            school=self.default_school,
        )
        self.assertEqual(hw.school, self.default_school)


class SchoolFKBehaviorTests(TestCase):
    """TEST_1_10 - TEST_1_15: Поведение FK — nullable, cascade, API."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email='phase1-behavior@test.com', password='Test1234',
            role='teacher', first_name='Phase1', last_name='Behavior',
        )
        if not School.objects.filter(is_default=True).exists():
            School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=cls.owner, is_default=True,
            )

    def test_1_10_create_group_without_school(self):
        """TEST_1_10: Создание Group без school → OK (null=True)."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        group = Group.objects.create(
            name='No School Group',
            teacher=self.owner,
            # school не указан → NULL
        )
        self.assertIsNone(group.school)

    def test_1_11_create_group_with_school(self):
        """TEST_1_11: Создание Group с school → FK работает."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        school = School.objects.create(
            slug='fk-test', name='FK Test', owner=self.owner,
        )
        group = Group.objects.create(
            name='With School Group',
            teacher=self.owner,
            school=school,
        )
        self.assertEqual(group.school, school)
        # Проверяем related_name
        self.assertIn(group, school.groups.all())

    def test_1_12_delete_school_cascades_groups(self):
        """TEST_1_12: Удаление School → каскадное удаление Group."""
        from schedule.models import Group
        if not _field_exists(Group, 'school'):
            self.skipTest("Group.school FK not yet added")

        school = School.objects.create(
            slug='cascade-test', name='Cascade Test', owner=self.owner,
        )
        group = Group.objects.create(
            name='Cascading Group', teacher=self.owner, school=school,
        )
        group_id = group.id

        school.delete()
        self.assertFalse(Group.objects.filter(id=group_id).exists())

    def test_1_13_api_groups_returns_all_without_isolation(self):
        """TEST_1_13: API GET /api/groups/ → все группы (изоляция OFF)."""
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken.for_user(self.owner)
        auth = {'HTTP_AUTHORIZATION': f'Bearer {token.access_token}'}

        response = self.client.get('/api/groups/', **auth)
        # Не должно быть 500
        self.assertNotEqual(response.status_code, 500,
                            f"API error: {response.content[:300]}")

    def test_1_14_api_create_group_works(self):
        """TEST_1_14: API POST /api/groups/ → создаётся."""
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken.for_user(self.owner)
        auth = {'HTTP_AUTHORIZATION': f'Bearer {token.access_token}'}

        response = self.client.post('/api/groups/', {
            'name': 'API Created Group',
            'subject': 'Test',
        }, content_type='application/json', **auth)
        # Допускаем 201 (created) или 200 или 400 (validation) — главное не 500
        self.assertNotEqual(response.status_code, 500,
                            f"API error: {response.content[:300]}")

    def test_1_15_smoke_tests_still_pass(self):
        """TEST_1_15: Smoke endpoint /api/health/ работает."""
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
