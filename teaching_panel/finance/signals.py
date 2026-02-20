"""
Django signals for automatic financial operations.

Triggers:
1. Individual lesson (1 student in group): charge on Attendance status='present'
2. Group lesson (>1 students): charge ALL students when Lesson.ended_at is set
3. Auto-create wallet when student joins a group
"""
import logging
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from .models import StudentFinancialProfile
from .services import FinanceService, DuplicateChargeError

logger = logging.getLogger(__name__)


@receiver(post_save, sender='schedule.Attendance')
def charge_on_individual_attendance(sender, instance, created, **kwargs):
    """
    Для ИНДИВИДУАЛЬНЫХ уроков: списание при отметке PRESENT.

    Индивидуальный урок = группа с 1 учеником.
    """
    # Импортируем здесь чтобы избежать circular imports
    from schedule.models import Attendance

    lesson = instance.lesson
    student = instance.student
    teacher = lesson.teacher

    # Только при статусе PRESENT
    if instance.status != 'present':
        return

    # Проверяем: это индивидуальный урок?
    students_count = lesson.group.students.count()
    if students_count > 1:
        # Групповой урок — списание происходит при ended_at
        return

    # Получаем кошелёк
    wallet = FinanceService.get_wallet(student=student, teacher=teacher)
    if not wallet:
        logger.debug(
            f'Кошелёк не найден для индивид. урока: '
            f'student={student.id}, teacher={teacher.id}, lesson={lesson.id}'
        )
        return

    # Проверяем, установлена ли цена
    if wallet.default_lesson_price <= 0:
        logger.debug(
            f'Пропуск авто-списания (цена=0): wallet={wallet.id}, lesson={lesson.id}'
        )
        return

    # Пробуем списать
    try:
        FinanceService.charge_lesson(
            wallet=wallet,
            lesson=lesson,
            created_by=teacher,
            auto_created=True
        )
        logger.info(
            f'Авто-списание (индивид.): student={student.id}, lesson={lesson.id}'
        )
    except DuplicateChargeError:
        # Уже списано — это нормально (idempotent)
        pass
    except Exception as e:
        logger.error(
            f'Ошибка авто-списания: student={student.id}, lesson={lesson.id}, error={e}'
        )


@receiver(post_save, sender='schedule.Lesson')
def charge_group_on_lesson_end(sender, instance, **kwargs):
    """
    Для ГРУППОВЫХ уроков: списание при ended_at.

    Списываем со ВСЕХ учеников группы, даже если они отсутствовали.
    Групповой урок = группа с >1 учеником.
    """
    lesson = instance

    # Только если урок завершён
    if not lesson.ended_at:
        return

    # Проверяем: это групповой урок?
    students_count = lesson.group.students.count()
    if students_count <= 1:
        # Индивидуальный — обрабатывается при Attendance
        return

    teacher = lesson.teacher

    # Списываем со ВСЕХ учеников группы
    for student in lesson.group.students.all():
        wallet = FinanceService.get_wallet(student=student, teacher=teacher)
        if not wallet:
            logger.debug(
                f'Кошелёк не найден для группового урока: '
                f'student={student.id}, teacher={teacher.id}'
            )
            continue

        # Проверяем, установлена ли цена
        if wallet.default_lesson_price <= 0:
            logger.debug(
                f'Пропуск авто-списания (цена=0): wallet={wallet.id}, lesson={lesson.id}'
            )
            continue

        try:
            FinanceService.charge_lesson(
                wallet=wallet,
                lesson=lesson,
                created_by=teacher,
                auto_created=True
            )
            logger.info(
                f'Авто-списание (групп.): student={student.id}, lesson={lesson.id}'
            )
        except DuplicateChargeError:
            # Уже списано
            pass
        except Exception as e:
            logger.error(
                f'Ошибка авто-списания: student={student.id}, lesson={lesson.id}, error={e}'
            )


def create_wallet_on_group_join(sender, instance, action, pk_set, **kwargs):
    """
    Автоматически создать кошелёк когда ученик добавляется в группу.

    Кошелёк создаётся с balance=0 и price=0. Учитель должен сам установить цену.
    """
    if action != 'post_add':
        return

    # instance — это Group
    group = instance
    teacher = group.teacher

    # pk_set — это ID добавленных учеников
    from accounts.models import CustomUser

    for student_id in pk_set:
        try:
            student = CustomUser.objects.get(pk=student_id)
            wallet = FinanceService.get_or_create_wallet(
                student=student,
                teacher=teacher,
                tenant=getattr(group, 'tenant', None),
            )
            logger.info(
                f'Кошелёк при добавлении в группу: '
                f'student={student.id}, teacher={teacher.id}, group={group.id}'
            )
        except CustomUser.DoesNotExist:
            logger.warning(f'Ученик с ID={student_id} не найден')
        except Exception as e:
            logger.error(
                f'Ошибка создания кошелька: student_id={student_id}, error={e}'
            )
