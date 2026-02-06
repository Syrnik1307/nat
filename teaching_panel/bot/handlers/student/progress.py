"""
Обработчики команд студента - прогресс и статистика
"""
import logging
from datetime import timedelta

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.utils import timezone

from ...utils import (
    require_linked_account,
    require_student,
)
from ...keyboards import (
    student_progress_keyboard,
    section_keyboard,
)

logger = logging.getLogger(__name__)


@require_linked_account
@require_student
async def my_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать прогресс ученика"""
    user = context.user_data.get('db_user')
    
    def get_progress():
        from homework.models import Homework, StudentSubmission
        from schedule.models import Lesson
        
        now = timezone.now()
        month_ago = now - timedelta(days=30)
        
        # Общие ДЗ
        group_hw_ids = set(
            Homework.objects.filter(
                assigned_groups__students=user,
                is_published=True,
                deadline__gte=month_ago,
            ).values_list('id', flat=True)
        )
        
        personal_hw_ids = set(
            Homework.objects.filter(
                assigned_students=user,
                is_published=True,
                deadline__gte=month_ago,
            ).values_list('id', flat=True)
        )
        
        all_hw_ids = group_hw_ids | personal_hw_ids
        
        # Статусы сдачи
        submissions = StudentSubmission.objects.filter(
            student=user,
            homework_id__in=all_hw_ids,
        )
        
        submitted = submissions.filter(status='submitted').count()
        graded = submissions.filter(status='graded').count()
        in_progress = submissions.filter(status='in_progress').count()
        not_started = len(all_hw_ids) - submitted - graded - in_progress
        
        # Оценки
        grades = submissions.filter(
            status='graded',
            grade__isnull=False,
        ).values_list('grade', flat=True)
        
        grades_list = list(grades)
        avg_grade = sum(grades_list) / len(grades_list) if grades_list else None
        
        # Уроки за месяц
        lessons_count = Lesson.objects.filter(
            group__students=user,
            start_time__gte=month_ago,
            start_time__lte=now,
        ).count()
        
        return {
            'total_hw': len(all_hw_ids),
            'submitted': submitted,
            'graded': graded,
            'in_progress': in_progress,
            'not_started': not_started,
            'avg_grade': avg_grade,
            'grades_count': len(grades_list),
            'lessons_count': lessons_count,
        }
    
    stats = await sync_to_async(get_progress)()
    
    lines = ["📊 *Ваш прогресс за месяц*\n"]
    
    # Статистика ДЗ
    lines.append("📝 *Домашние задания:*")
    
    total = stats['total_hw']
    if total > 0:
        completed = stats['submitted'] + stats['graded']
        percentage = int(completed / total * 100)
        progress_bar = '▓' * (percentage // 10) + '░' * (10 - percentage // 10)
        lines.append(f"  [{progress_bar}] {percentage}%")
        lines.append(f"  ✅ Сдано: {completed}/{total}")
        if stats['in_progress'] > 0:
            lines.append(f"  ✏️ В работе: {stats['in_progress']}")
        if stats['not_started'] > 0:
            lines.append(f"  ⏳ Не начато: {stats['not_started']}")
    else:
        lines.append("  Нет активных заданий")
    
    lines.append("")
    
    # Средняя оценка
    if stats['avg_grade'] is not None:
        lines.append("⭐ *Средняя оценка:*")
        lines.append(f"  {stats['avg_grade']:.1f} (из {stats['grades_count']} оценок)")
        lines.append("")
    
    # Уроки
    lines.append("📅 *Посещено уроков:*")
    lines.append(f"  {stats['lessons_count']}")
    
    keyboard = student_progress_keyboard()
    
    await update.effective_message.reply_text(
        '\n'.join(lines),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def detailed_grades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальный список оценок"""
    query = update.callback_query
    await query.answer()
    
    user = context.user_data.get('db_user')
    
    def get_grades():
        from homework.models import StudentSubmission
        
        submissions = list(
            StudentSubmission.objects.filter(
                student=user,
                status='graded',
            ).select_related('homework').order_by('-graded_at')[:20]
        )
        
        return submissions
    
    submissions = await sync_to_async(get_grades)()
    
    if not submissions:
        await query.edit_message_text(
            "📋 Оценок пока нет.\n\n"
            "Когда преподаватель проверит ваши работы, оценки появятся здесь.",
            reply_markup=section_keyboard('progress', include_refresh=True),
        )
        return
    
    lines = ["📋 *Ваши оценки:*\n"]
    
    for sub in submissions:
        grade = sub.grade if sub.grade else '—'
        title = sub.homework.title[:30]
        lines.append(f"  • {title}: *{grade}*")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('◀️ Назад', callback_data='menu:progress')],
    ])
    
    await query.edit_message_text(
        '\n'.join(lines),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )
