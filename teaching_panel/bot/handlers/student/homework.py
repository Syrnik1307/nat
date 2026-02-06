"""
Обработчики команд студента - домашние задания
"""
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.utils import timezone

from ...utils import (
    require_linked_account,
    require_student,
    format_datetime,
    format_time_remaining,
)
from ...keyboards import (
    student_homework_keyboard,
    section_keyboard,
)

logger = logging.getLogger(__name__)


@require_linked_account
@require_student
async def my_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активные ДЗ студента"""
    user = context.user_data.get('db_user')
    
    def get_homeworks():
        from homework.models import Homework, StudentSubmission
        now = timezone.now()
        
        # Получаем ДЗ для групп ученика + персональные
        homeworks = list(
            Homework.objects.filter(
                assigned_groups__students=user,
                is_published=True,
            ).distinct().prefetch_related('assigned_groups').order_by('-deadline')[:20]
        )
        
        # Добавляем персональные
        personal = list(
            Homework.objects.filter(
                assigned_students=user,
                is_published=True,
            ).prefetch_related('assigned_groups').order_by('-deadline')[:10]
        )
        
        all_hw = {hw.id: hw for hw in homeworks + personal}
        
        # Получаем статусы сдачи
        submissions = StudentSubmission.objects.filter(
            student=user,
            homework_id__in=all_hw.keys(),
        )
        submission_status = {s.homework_id: s.status for s in submissions}
        
        result = []
        for hw_id, hw in all_hw.items():
            status = submission_status.get(hw_id)
            result.append((hw, status))
        
        # Сортируем: сначала не сданные, потом по дедлайну
        result.sort(key=lambda x: (
            x[1] in ['submitted', 'graded'],  # Несданные первыми
            x[0].deadline or timezone.now() + timezone.timedelta(days=365),
        ))
        
        return result
    
    homeworks = await sync_to_async(get_homeworks)()
    
    if not homeworks:
        await update.effective_message.reply_text(
            "📭 Активных домашних заданий нет.",
            reply_markup=section_keyboard('homework', include_refresh=True),
        )
        return
    
    lines = ["📝 *Ваши домашние задания:*\n"]
    
    for i, (hw, status) in enumerate(homeworks[:10], 1):
        status_emoji = {
            None: '⏳',           # Не начато
            'in_progress': '✏️',  # В работе
            'submitted': '📤',    # Отправлено
            'graded': '✅',       # Проверено
        }.get(status, '⏳')
        
        deadline_str = ''
        if hw.deadline:
            if hw.deadline < timezone.now():
                deadline_str = ' (просрочено!)'
            else:
                deadline_str = f' ({format_time_remaining(hw.deadline)})'
        
        lines.append(f"{i}. {status_emoji} *{hw.title}*{deadline_str}")
    
    if len(homeworks) > 10:
        lines.append(f"\n_...и ещё {len(homeworks) - 10} заданий_")
    
    lines.append("\n⏳ Не начато | ✏️ В работе | 📤 На проверке | ✅ Проверено")
    
    keyboard = student_homework_keyboard(
        homeworks=[hw for hw, _ in homeworks[:10]],
        callback_prefix='st_hw',
    )
    
    await update.effective_message.reply_text(
        '\n'.join(lines),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def homework_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальная информация о ДЗ"""
    query = update.callback_query
    await query.answer()
    
    user = context.user_data.get('db_user')
    homework_id = int(query.data.split(':')[1])
    
    def get_hw_details():
        from homework.models import Homework, StudentSubmission
        
        hw = Homework.objects.get(id=homework_id)
        
        try:
            submission = StudentSubmission.objects.get(
                student=user,
                homework=hw,
            )
        except StudentSubmission.DoesNotExist:
            submission = None
        
        return hw, submission
    
    hw, submission = await sync_to_async(get_hw_details)()
    
    lines = [f"📝 *{hw.title}*\n"]
    
    if hw.description:
        lines.append(hw.description[:200])
        if len(hw.description) > 200:
            lines.append("...")
        lines.append("")
    
    if hw.deadline:
        lines.append(f"⏰ Дедлайн: {format_datetime(hw.deadline)}")
        if hw.deadline > timezone.now():
            lines.append(f"⏳ Осталось: {format_time_remaining(hw.deadline)}")
        else:
            lines.append("❗ *Срок сдачи истёк*")
    
    lines.append("")
    
    if submission:
        status_text = {
            'in_progress': '✏️ В работе',
            'submitted': '📤 Отправлено на проверку',
            'graded': '✅ Проверено',
        }.get(submission.status, '⏳ Не начато')
        
        lines.append(f"Статус: {status_text}")
        
        if submission.status == 'graded' and submission.grade:
            lines.append(f"Оценка: *{submission.grade}*")
    else:
        lines.append("Статус: ⏳ Не начато")
    
    # Кнопки
    buttons = [[InlineKeyboardButton('◀️ Назад', callback_data='menu:homework')]]
    
    # Ссылка на ДЗ в веб-версии
    from ..config import WEBAPP_URL
    if WEBAPP_URL:
        hw_url = f"{WEBAPP_URL}/homework/{homework_id}"
        buttons.insert(0, [InlineKeyboardButton('🌐 Открыть в браузере', url=hw_url)])
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(
        '\n'.join(lines),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


@require_linked_account
@require_student
async def pending_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать только несданные ДЗ"""
    user = context.user_data.get('db_user')
    
    def get_pending():
        from homework.models import Homework, StudentSubmission
        now = timezone.now()
        
        # ДЗ групп
        group_hw_ids = set(
            Homework.objects.filter(
                assigned_groups__students=user,
                is_published=True,
            ).values_list('id', flat=True)
        )
        
        # Персональные
        personal_hw_ids = set(
            Homework.objects.filter(
                assigned_students=user,
                is_published=True,
            ).values_list('id', flat=True)
        )
        
        all_hw_ids = group_hw_ids | personal_hw_ids
        
        # Сданные
        submitted_ids = set(
            StudentSubmission.objects.filter(
                student=user,
                homework_id__in=all_hw_ids,
                status__in=['submitted', 'graded'],
            ).values_list('homework_id', flat=True)
        )
        
        pending_ids = all_hw_ids - submitted_ids
        
        homeworks = list(
            Homework.objects.filter(id__in=pending_ids).order_by('deadline')
        )
        
        return homeworks
    
    homeworks = await sync_to_async(get_pending)()
    
    if not homeworks:
        await update.effective_message.reply_text(
            "🎉 *Все домашние задания сданы!*\n\n"
            "Молодец! Продолжай в том же духе.",
            parse_mode='Markdown',
            reply_markup=section_keyboard('homework', include_refresh=True),
        )
        return
    
    lines = ["⏳ *Несданные домашние задания:*\n"]
    
    now = timezone.now()
    overdue = []
    upcoming = []
    
    for hw in homeworks:
        if hw.deadline and hw.deadline < now:
            overdue.append(hw)
        else:
            upcoming.append(hw)
    
    if overdue:
        lines.append("❗ *Просрочено:*")
        for hw in overdue[:5]:
            lines.append(f"  • {hw.title}")
        lines.append("")
    
    if upcoming:
        lines.append("📝 *К сдаче:*")
        for hw in upcoming[:10]:
            deadline_str = ''
            if hw.deadline:
                deadline_str = f" ({format_time_remaining(hw.deadline)})"
            lines.append(f"  • {hw.title}{deadline_str}")
    
    keyboard = student_homework_keyboard(
        homeworks=(overdue[:3] + upcoming[:7]),
        callback_prefix='st_hw',
    )
    
    await update.effective_message.reply_text(
        '\n'.join(lines),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )
