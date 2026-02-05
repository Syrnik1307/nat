"""
Tests for finance app.

Covers:
- Models (StudentFinancialProfile, Transaction)
- Services (FinanceService)
- API endpoints
- Signals (auto-charging)
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from schedule.models import Group, Lesson
from .models import StudentFinancialProfile, Transaction, TransactionType
from .services import FinanceService, DuplicateChargeError

User = get_user_model()


class StudentFinancialProfileModelTest(TestCase):
    """Tests for StudentFinancialProfile model."""
    
    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher',
            first_name='Иван',
            last_name='Учитель'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student',
            first_name='Петя',
            last_name='Ученик'
        )
    
    def test_create_wallet(self):
        """Test wallet creation."""
        wallet = StudentFinancialProfile.objects.create(
            student=self.student,
            teacher=self.teacher,
            balance=Decimal('5000.00'),
            default_lesson_price=Decimal('1500.00')
        )
        
        self.assertEqual(wallet.balance, Decimal('5000.00'))
        self.assertEqual(wallet.currency, 'RUB')
        self.assertFalse(wallet.is_debtor)
    
    def test_lessons_left_calculation(self):
        """Test lessons_left property calculation."""
        wallet = StudentFinancialProfile.objects.create(
            student=self.student,
            teacher=self.teacher,
            balance=Decimal('4500.00'),
            default_lesson_price=Decimal('1500.00')
        )
        
        self.assertEqual(wallet.lessons_left, 3.0)
    
    def test_lessons_left_fractional(self):
        """Test fractional lessons remaining."""
        wallet = StudentFinancialProfile.objects.create(
            student=self.student,
            teacher=self.teacher,
            balance=Decimal('2000.00'),
            default_lesson_price=Decimal('1500.00')
        )
        
        self.assertAlmostEqual(wallet.lessons_left, 1.333, places=2)
    
    def test_is_debtor(self):
        """Test debtor detection."""
        wallet = StudentFinancialProfile.objects.create(
            student=self.student,
            teacher=self.teacher,
            balance=Decimal('-500.00'),
            default_lesson_price=Decimal('1500.00')
        )
        
        self.assertTrue(wallet.is_debtor)
    
    def test_debt_limit_exceeded(self):
        """Test debt limit exceeded detection."""
        wallet = StudentFinancialProfile.objects.create(
            student=self.student,
            teacher=self.teacher,
            balance=Decimal('-5000.00'),
            default_lesson_price=Decimal('1500.00'),
            debt_limit=Decimal('3000.00')
        )
        
        self.assertTrue(wallet.debt_limit_exceeded)
    
    def test_balance_status(self):
        """Test balance status calculation."""
        # OK status
        wallet = StudentFinancialProfile.objects.create(
            student=self.student,
            teacher=self.teacher,
            balance=Decimal('5000.00'),
            default_lesson_price=Decimal('1500.00')
        )
        self.assertEqual(wallet.balance_status, 'ok')
        
        # Low status
        wallet.balance = Decimal('2000.00')
        self.assertEqual(wallet.balance_status, 'low')
        
        # Debt status
        wallet.balance = Decimal('-100.00')
        self.assertEqual(wallet.balance_status, 'debt')


class FinanceServiceTest(TestCase):
    """Tests for FinanceService."""
    
    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        self.group = Group.objects.create(
            name='Тестовая группа',
            teacher=self.teacher
        )
        # Signal создаёт wallet при добавлении student в group
        self.group.students.add(self.student)
        
        # Используем созданный wallet и обновляем его
        self.wallet = StudentFinancialProfile.objects.get(
            student=self.student,
            teacher=self.teacher
        )
        self.wallet.balance = Decimal('5000.00')
        self.wallet.default_lesson_price = Decimal('1500.00')
        self.wallet.save()
        
        self.lesson = Lesson.objects.create(
            title='Тестовый урок',
            group=self.group,
            teacher=self.teacher,
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )
    
    def test_charge_lesson(self):
        """Test charging for a lesson."""
        txn = FinanceService.charge_lesson(
            wallet=self.wallet,
            lesson=self.lesson,
            created_by=self.teacher
        )
        
        self.wallet.refresh_from_db()
        
        self.assertIsNotNone(txn)
        self.assertEqual(txn.amount, Decimal('-1500.00'))
        self.assertEqual(txn.transaction_type, TransactionType.LESSON_CHARGE)
        self.assertEqual(self.wallet.balance, Decimal('3500.00'))
    
    def test_charge_lesson_with_override(self):
        """Test charging with override price (trial lesson)."""
        txn = FinanceService.charge_lesson(
            wallet=self.wallet,
            lesson=self.lesson,
            created_by=self.teacher,
            override_price=Decimal('500.00'),
            description='Пробный урок'
        )
        
        self.wallet.refresh_from_db()
        
        self.assertEqual(txn.amount, Decimal('-500.00'))
        self.assertEqual(txn.override_price, Decimal('500.00'))
        self.assertEqual(self.wallet.balance, Decimal('4500.00'))
    
    def test_duplicate_charge_prevention(self):
        """Test that duplicate charges are prevented."""
        FinanceService.charge_lesson(
            wallet=self.wallet,
            lesson=self.lesson,
            created_by=self.teacher
        )
        
        with self.assertRaises(DuplicateChargeError):
            FinanceService.charge_lesson(
                wallet=self.wallet,
                lesson=self.lesson,
                created_by=self.teacher
            )
    
    def test_deposit(self):
        """Test deposit (payment from student)."""
        txn = FinanceService.deposit(
            wallet=self.wallet,
            amount=Decimal('3000.00'),
            created_by=self.teacher,
            description='Оплата за ноябрь'
        )
        
        self.wallet.refresh_from_db()
        
        self.assertEqual(txn.amount, Decimal('3000.00'))
        self.assertEqual(txn.transaction_type, TransactionType.DEPOSIT)
        self.assertEqual(self.wallet.balance, Decimal('8000.00'))
    
    def test_adjust(self):
        """Test balance adjustment."""
        txn = FinanceService.adjust(
            wallet=self.wallet,
            amount=Decimal('-1000.00'),
            created_by=self.teacher,
            description='Корректировка за пропущенный урок'
        )
        
        self.wallet.refresh_from_db()
        
        self.assertEqual(txn.amount, Decimal('-1000.00'))
        self.assertEqual(txn.transaction_type, TransactionType.ADJUSTMENT)
        self.assertEqual(self.wallet.balance, Decimal('4000.00'))
    
    def test_refund_lesson(self):
        """Test refund for cancelled lesson."""
        # First charge
        FinanceService.charge_lesson(
            wallet=self.wallet,
            lesson=self.lesson,
            created_by=self.teacher
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('3500.00'))
        
        # Then refund
        txn = FinanceService.refund_lesson(
            wallet=self.wallet,
            lesson=self.lesson,
            created_by=self.teacher,
            description='Урок отменён'
        )
        
        self.wallet.refresh_from_db()
        
        self.assertEqual(txn.amount, Decimal('1500.00'))
        self.assertEqual(txn.transaction_type, TransactionType.REFUND)
        self.assertEqual(self.wallet.balance, Decimal('5000.00'))
    
    def test_get_or_create_wallet(self):
        """Test wallet auto-creation."""
        new_student = User.objects.create_user(
            email='newstudent@test.com',
            password='testpass123',
            role='student'
        )
        
        wallet = FinanceService.get_or_create_wallet(
            student=new_student,
            teacher=self.teacher
        )
        
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.balance, Decimal('0.00'))
        self.assertEqual(wallet.default_lesson_price, Decimal('0.00'))


class TransactionImmutabilityTest(TestCase):
    """Test that transactions cannot be modified or deleted."""
    
    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com', password='test', role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com', password='test', role='student'
        )
        self.wallet = StudentFinancialProfile.objects.create(
            student=self.student,
            teacher=self.teacher,
            balance=Decimal('1000.00'),
            default_lesson_price=Decimal('500.00')
        )
    
    def test_transaction_cannot_be_edited(self):
        """Test that saving existing transaction raises error."""
        txn = Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal('500.00'),
            transaction_type=TransactionType.DEPOSIT,
            description='Test'
        )
        
        txn.amount = Decimal('1000.00')
        with self.assertRaises(ValueError):
            txn.save()
    
    def test_transaction_cannot_be_deleted(self):
        """Test that deleting transaction raises error."""
        txn = Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal('500.00'),
            transaction_type=TransactionType.DEPOSIT,
            description='Test'
        )
        
        with self.assertRaises(ValueError):
            txn.delete()


class WalletAPITest(APITestCase):
    """Tests for finance API endpoints."""
    
    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        self.group = Group.objects.create(
            name='Test Group',
            teacher=self.teacher
        )
        # Signal создаёт wallet при добавлении student в group
        self.group.students.add(self.student)
        
        # Используем созданный wallet и обновляем его
        self.wallet = StudentFinancialProfile.objects.get(
            student=self.student,
            teacher=self.teacher
        )
        self.wallet.balance = Decimal('5000.00')
        self.wallet.default_lesson_price = Decimal('1500.00')
        self.wallet.save()
    
    def test_list_wallets_as_teacher(self):
        """Test listing wallets as teacher."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/finance/wallets/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # DRF может возвращать paginated response или список
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            data = data['results']
        # Проверяем что есть хотя бы один кошелёк
        self.assertGreaterEqual(len(data), 1)
    
    def test_list_wallets_as_student_forbidden(self):
        """Test that students cannot list wallets."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/finance/wallets/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_deposit_action(self):
        """Test deposit action."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            f'/api/finance/wallets/{self.wallet.id}/deposit/',
            {'amount': '3000.00', 'description': 'Оплата'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('8000.00'))
    
    def test_student_balance_view(self):
        """Test student balance endpoint."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/finance/my-balance/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['balances']), 1)
        self.assertAlmostEqual(
            response.data['balances'][0]['lessons_remaining'],
            3.33, places=1
        )
