"""
Finance business logic service.

Handles all financial operations: charging lessons, deposits, adjustments, refunds.
Uses atomic transactions to ensure data integrity.
"""
from decimal import Decimal
from typing import Optional
import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import StudentFinancialProfile, Transaction, TransactionType

logger = logging.getLogger(__name__)


class FinanceServiceError(Exception):
    """Base exception for finance service errors."""
    pass


class DuplicateChargeError(FinanceServiceError):
    """Raised when trying to charge for a lesson that was already charged."""
    pass


class WalletNotFoundError(FinanceServiceError):
    """Raised when wallet doesn't exist for student-teacher pair."""
    pass


class FinanceService:
    """
    Сервис для работы с финансами учеников.

    Все операции атомарны и используют блокировки для предотвращения race conditions.
    """

    @staticmethod
    @transaction.atomic
    def charge_lesson(
        wallet: StudentFinancialProfile,
        lesson,  # schedule.Lesson
        created_by,  # User
        override_price: Optional[Decimal] = None,
        description: str = '',
        auto_created: bool = False
    ) -> Transaction:
        """
        Списать деньги за урок.

        Args:
            wallet: Кошелёк ученика
            lesson: Урок (schedule.Lesson)
            created_by: Кто инициировал списание (обычно учитель)
            override_price: Кастомная цена (None = использовать default_lesson_price)
            description: Комментарий к транзакции
            auto_created: True если создано автоматически (signal)

        Returns:
            Transaction: Созданная транзакция

        Raises:
            DuplicateChargeError: Урок уже оплачен
            ValueError: Некорректные данные
        """
        # Блокируем кошелёк для атомарного обновления
        wallet = StudentFinancialProfile.objects.select_for_update().get(pk=wallet.pk)

        # Проверка на дубликат
        if Transaction.objects.filter(
            wallet=wallet,
            lesson=lesson,
            transaction_type=TransactionType.LESSON_CHARGE
        ).exists():
            raise DuplicateChargeError(f'Урок #{lesson.id} уже оплачен этим учеником')

        # Определяем цену
        price = override_price if override_price is not None else wallet.default_lesson_price

        if price <= 0:
            logger.warning(f'Попытка списания с нулевой ценой: wallet={wallet.id}, lesson={lesson.id}')
            # Не создаём транзакцию с нулевой суммой
            return None

        # Определяем тип урока (групповой если >1 ученика)
        is_group = lesson.group.students.count() > 1

        # Формируем описание
        if not description:
            lesson_date = lesson.start_time.strftime('%d.%m.%Y')
            description = f'{lesson.display_name} ({lesson_date})'

        # Создаём транзакцию
        txn = Transaction.objects.create(
            wallet=wallet,
            amount=-price,  # Отрицательное = списание
            transaction_type=TransactionType.LESSON_CHARGE,
            lesson=lesson,
            is_group_lesson=is_group,
            override_price=override_price,
            description=description,
            created_by=created_by,
            auto_created=auto_created
        )

        # Атомарно обновляем баланс
        wallet.balance = F('balance') - price
        wallet.save(update_fields=['balance', 'updated_at'])
        wallet.refresh_from_db()

        logger.info(
            f'Списание за урок: wallet={wallet.id}, lesson={lesson.id}, '
            f'amount={price}, new_balance={wallet.balance}'
        )

        return txn

    @staticmethod
    @transaction.atomic
    def deposit(
        wallet: StudentFinancialProfile,
        amount: Decimal,
        created_by,  # User
        description: str = ''
    ) -> Transaction:
        """
        Внести оплату от ученика (пополнение баланса).

        Args:
            wallet: Кошелёк ученика
            amount: Сумма пополнения (должна быть положительной)
            created_by: Кто внёс запись (учитель)
            description: Комментарий

        Returns:
            Transaction: Созданная транзакция
        """
        if amount <= 0:
            raise ValueError('Сумма пополнения должна быть положительной')

        # Блокируем кошелёк
        wallet = StudentFinancialProfile.objects.select_for_update().get(pk=wallet.pk)

        txn = Transaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=TransactionType.DEPOSIT,
            description=description or 'Пополнение баланса',
            created_by=created_by,
            auto_created=False
        )

        wallet.balance = F('balance') + amount
        wallet.save(update_fields=['balance', 'updated_at'])
        wallet.refresh_from_db()

        logger.info(
            f'Пополнение: wallet={wallet.id}, amount={amount}, new_balance={wallet.balance}'
        )

        return txn

    @staticmethod
    @transaction.atomic
    def adjust(
        wallet: StudentFinancialProfile,
        amount: Decimal,
        created_by,  # User
        description: str
    ) -> Transaction:
        """
        Ручная корректировка баланса.

        Args:
            wallet: Кошелёк ученика
            amount: Сумма корректировки (+ добавить, - убрать)
            created_by: Кто сделал корректировку
            description: Обязательное описание причины

        Returns:
            Transaction: Созданная транзакция
        """
        if not description:
            raise ValueError('Описание обязательно для корректировки')

        if amount == 0:
            raise ValueError('Сумма корректировки не может быть нулевой')

        # Блокируем кошелёк
        wallet = StudentFinancialProfile.objects.select_for_update().get(pk=wallet.pk)

        txn = Transaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=TransactionType.ADJUSTMENT,
            description=description,
            created_by=created_by,
            auto_created=False
        )

        wallet.balance = F('balance') + amount
        wallet.save(update_fields=['balance', 'updated_at'])
        wallet.refresh_from_db()

        logger.info(
            f'Корректировка: wallet={wallet.id}, amount={amount}, '
            f'reason="{description}", new_balance={wallet.balance}'
        )

        return txn

    @staticmethod
    @transaction.atomic
    def refund_lesson(
        wallet: StudentFinancialProfile,
        lesson,  # schedule.Lesson
        created_by,  # User
        description: str = ''
    ) -> Transaction:
        """
        Вернуть деньги за отменённый урок.

        Находит оригинальную транзакцию списания и создаёт возврат.

        Args:
            wallet: Кошелёк ученика
            lesson: Урок для возврата
            created_by: Кто сделал возврат
            description: Комментарий

        Returns:
            Transaction: Созданная транзакция возврата
        """
        # Блокируем кошелёк
        wallet = StudentFinancialProfile.objects.select_for_update().get(pk=wallet.pk)

        # Находим оригинальную транзакцию списания
        original = Transaction.objects.filter(
            wallet=wallet,
            lesson=lesson,
            transaction_type=TransactionType.LESSON_CHARGE
        ).first()

        if not original:
            raise ValueError(f'Транзакция списания за урок #{lesson.id} не найдена')

        # Проверяем, не было ли уже возврата
        if Transaction.objects.filter(
            wallet=wallet,
            lesson=lesson,
            transaction_type=TransactionType.REFUND
        ).exists():
            raise ValueError(f'Возврат за урок #{lesson.id} уже сделан')

        refund_amount = abs(original.amount)

        if not description:
            lesson_date = lesson.start_time.strftime('%d.%m.%Y')
            description = f'Возврат: {lesson.display_name} ({lesson_date})'

        txn = Transaction.objects.create(
            wallet=wallet,
            amount=refund_amount,  # Положительное = возврат
            transaction_type=TransactionType.REFUND,
            lesson=lesson,
            is_group_lesson=original.is_group_lesson,
            description=description,
            created_by=created_by,
            auto_created=False
        )

        wallet.balance = F('balance') + refund_amount
        wallet.save(update_fields=['balance', 'updated_at'])
        wallet.refresh_from_db()

        logger.info(
            f'Возврат: wallet={wallet.id}, lesson={lesson.id}, '
            f'amount={refund_amount}, new_balance={wallet.balance}'
        )

        return txn

    @staticmethod
    def get_or_create_wallet(student, teacher, tenant=None) -> StudentFinancialProfile:
        """
        Получить или создать кошелёк для пары ученик-учитель.

        Новый кошелёк создаётся с нулевым балансом и нулевой ценой урока.
        Учитель должен сам установить цену.
        """
        defaults = {
            'balance': Decimal('0.00'),
            'default_lesson_price': Decimal('0.00'),
        }
        if tenant:
            defaults['tenant'] = tenant
        
        wallet, created = StudentFinancialProfile.objects.get_or_create(
            student=student,
            teacher=teacher,
            defaults=defaults,
        )

        if created:
            logger.info(
                f'Создан кошелёк: student={student.id} ({student.email}), '
                f'teacher={teacher.id} ({teacher.email})'
            )

        return wallet

    @staticmethod
    def get_wallet(student, teacher) -> Optional[StudentFinancialProfile]:
        """
        Получить кошелёк для пары ученик-учитель.

        Returns:
            StudentFinancialProfile или None если не найден
        """
        try:
            return StudentFinancialProfile.objects.get(
                student=student,
                teacher=teacher
            )
        except StudentFinancialProfile.DoesNotExist:
            return None

    @staticmethod
    def is_lesson_charged(wallet: StudentFinancialProfile, lesson) -> bool:
        """Проверить, списаны ли деньги за урок."""
        return Transaction.objects.filter(
            wallet=wallet,
            lesson=lesson,
            transaction_type=TransactionType.LESSON_CHARGE
        ).exists()
