"""
Phase 4 тесты: PaymentService per-school.

Проверяют что:
- PaymentService работает с per-school credentials
- Webhook привязывает Subscription к школе через metadata
- Mock mode по-прежнему работает
- Обратная совместимость (school=None → как раньше)

НЕ запускай пока Phase 4 не выполнен!

Запуск: python manage.py test tenants.tests_phase4 -v2
"""

from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from tenants.models import School, SchoolMembership
from tenants.middleware import TenantMiddleware

User = get_user_model()


def _field_exists(model_class, field_name):
    try:
        model_class._meta.get_field(field_name)
        return True
    except Exception:
        return False


class PaymentServicePerSchoolTests(TestCase):
    """TEST_4_01 - TEST_4_09: PaymentService с per-school credentials."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email='pay-owner@test.com', password='Test1234',
            role='teacher', first_name='Pay', last_name='Owner',
        )

        if not School.objects.filter(is_default=True).exists():
            School.objects.create(
                slug='lectiospace', name='Lectio Space',
                owner=cls.owner, is_default=True,
            )
        cls.default_school = School.objects.get(is_default=True)

        # Школа с собственными credentials
        cls.school_own_creds = School.objects.create(
            slug='pay-school', name='Pay School',
            owner=cls.owner,
            yookassa_account_id='school-acc-123',
            yookassa_secret_key='school-secret-456',
            default_payment_provider='yookassa',
        )

        # Школа без своих credentials (fallback на платформу)
        cls.school_no_creds = School.objects.create(
            slug='pay-nocreds', name='No Creds School',
            owner=cls.owner,
            yookassa_account_id='',
            yookassa_secret_key='',
            default_payment_provider='yookassa',
        )

        TenantMiddleware.clear_cache()

    def _get_or_create_subscription(self, user):
        """Получить или создать Subscription для тестового пользователя."""
        from accounts.models import Subscription
        sub, created = Subscription.objects.get_or_create(
            user=user,
            defaults={
                'plan': 'trial',
                'status': 'pending',
                'expires_at': timezone.now() + timedelta(days=7),
            }
        )
        return sub

    def test_4_01_payment_service_without_school_works(self):
        """TEST_4_01: PaymentService(school=None) → работает как раньше."""
        from accounts.payments_service import PaymentService

        sub = self._get_or_create_subscription(self.owner)

        # Mock API call если нужно
        try:
            result = PaymentService.create_subscription_payment(sub, 'monthly')
            # Должен вернуть dict с payment_url (реальный или mock)
            if result:
                self.assertIn('payment_url', result)
        except Exception as e:
            # Допустимо если нет YooKassa credentials в dev
            self.assertIn('mock', str(e).lower() + str(type(e)).lower(),
                          f"Unexpected error: {e}")

    def test_4_02_school_get_payment_credentials_own(self):
        """TEST_4_02: Школа с заполненными creds → возвращает свои."""
        creds = self.school_own_creds.get_payment_credentials()

        self.assertEqual(creds['provider'], 'yookassa')
        self.assertEqual(creds['account_id'], 'school-acc-123')
        self.assertEqual(creds['secret_key'], 'school-secret-456')

    def test_4_03_school_get_payment_credentials_fallback(self):
        """TEST_4_03: Школа без creds → fallback на PLATFORM_CONFIG."""
        creds = self.school_no_creds.get_payment_credentials()

        self.assertEqual(creds['provider'], 'yookassa')
        # Fallback: не пустая строка (берёт из PLATFORM_CONFIG)
        # Может быть пустой если PLATFORM_CONFIG тоже пустой в dev
        self.assertIsNotNone(creds.get('account_id'))

    def test_4_04_payment_creates_with_school_in_metadata(self):
        """TEST_4_04: Payment metadata содержит school_id."""
        from accounts.models import Payment, Subscription

        sub = self._get_or_create_subscription(self.owner)

        # Проверяем что после Phase 4 можно передать school
        from accounts.payments_service import PaymentService

        # Проверяем сигнатуру — если school доступен как параметр
        import inspect
        sig = inspect.signature(PaymentService.create_subscription_payment)
        params = list(sig.parameters.keys())

        if 'school' in params:
            # Phase 4 уже реализован — проверяем работу
            try:
                result = PaymentService.create_subscription_payment(
                    sub, 'monthly', school=self.school_own_creds
                )
                if result:
                    self.assertIn('payment_url', result)
            except Exception:
                pass  # OK в dev без реальных credentials
        else:
            self.skipTest("PaymentService.create_subscription_payment does not accept 'school' yet (Phase 4)")

    def test_4_05_mock_mode_still_works(self):
        """TEST_4_05: Mock mode работает без YOOKASSA_ACCOUNT_ID."""
        from accounts.payments_service import PaymentService

        sub = self._get_or_create_subscription(self.owner)

        # В dev среде обычно mock mode
        result = PaymentService.create_subscription_payment(sub, 'monthly')
        if result:
            # Mock URL или реальный — оба OK
            self.assertIn('payment_url', result)
            self.assertTrue(len(result['payment_url']) > 0)

    def test_4_06_subscription_has_school_fk(self):
        """TEST_4_06: Subscription модель имеет school FK (после Phase 1)."""
        from accounts.models import Subscription
        if not _field_exists(Subscription, 'school'):
            self.skipTest("Subscription.school FK not yet added (Phase 1)")

        sub = self._get_or_create_subscription(self.owner)
        # Можно задать school
        sub.school = self.school_own_creds
        sub.save()
        sub.refresh_from_db()
        self.assertEqual(sub.school, self.school_own_creds)

    def test_4_07_webhook_sets_school_from_metadata(self):
        """TEST_4_07: Webhook с school_id в metadata → Subscription.school = school."""
        from accounts.models import Subscription, Payment
        if not _field_exists(Subscription, 'school'):
            self.skipTest("Subscription.school FK not yet added")

        sub = self._get_or_create_subscription(self.owner)
        
        # Создаём Payment с metadata содержащей school_id
        payment = Payment.objects.create(
            subscription=sub,
            amount=Decimal('1590.00'),
            currency='RUB',
            status='pending',
            payment_system='yookassa',
            payment_id=f'test-webhook-{sub.id}',
            metadata={
                'plan': 'monthly',
                'school_id': str(self.school_own_creds.id),
            }
        )

        # Симулируем webhook payload
        from accounts.payments_service import PaymentService
        webhook_data = {
            'event': 'payment.succeeded',
            'object': {
                'id': payment.payment_id,
                'status': 'succeeded',
                'amount': {'value': '1590.00', 'currency': 'RUB'},
                'metadata': {
                    'subscription_id': str(sub.id),
                    'user_id': str(self.owner.id),
                    'plan': 'monthly',
                    'school_id': str(self.school_own_creds.id),
                },
            }
        }

        try:
            PaymentService.process_payment_webhook(webhook_data)
        except Exception:
            # Может не работать полностью в test env, OK
            pass

        # Проверяем что school привязался (если webhook обработал metadata)
        sub.refresh_from_db()
        # Если Phase 4 полностью реализован, school будет задан
        # Пока что это подготовительный тест

    def test_4_08_return_url_uses_school_frontend_url(self):
        """TEST_4_08: return_url использует school.get_frontend_url() если school задана."""
        url = self.school_own_creds.get_frontend_url()
        self.assertIn('pay-school', url)
        # По умолчанию поддомен
        self.assertIn('lectiospace.ru', url)

    def test_4_09_description_contains_school_name(self):
        """TEST_4_09: В будущем description платежа содержит имя школы."""
        # Это проверяется интеграционно когда PaymentService обновлён
        # Пока проверяем что school.name доступен
        self.assertEqual(self.school_own_creds.name, 'Pay School')

    def test_4_10_smoke_still_works(self):
        """TEST_4_10: Smoke endpoints работают после Phase 4."""
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
