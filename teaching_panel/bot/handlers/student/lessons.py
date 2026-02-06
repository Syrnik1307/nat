"""
Обработчики команд студента - уроки
"""
import logging
from datetime import timedelta

from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.utils import timezone

from ...utils import (
    require_linked_account,
    require_student,
    format_lesson_card,
)
from ...keyboards import (
    student_lesson_keyboard,
    section_keyboard,
)

logger = logging.getLogger(__name__)


@require_linked_account
@require_student
async def my_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать ближайшие уроки студента"""
    user = context.user_data.get('db_user')
    
    def get_lessons():
        from schedule.models import Lesson
        now = timezone.now()
        
        # Ближайшие 7 дней
        end_date = now + timedelta(days=7)
        
        lessons = list(
            Lesson.objects.filter(
                group__students=user,
                start_time__gte=now,
                start_time__lte=end_date,
            ).select_related('group', 'teacher').order_by('start_time')[:10]
        )
        
        return lessons
    
    lessons = await sync_to_async(get_lessons)()
    
    if not lessons:
        await update.effective_message.reply_text(
            "📭 На ближайшую неделю уроков нет.\n\n"
            "Когда преподаватель запланирует занятие, оно появится здесь.",
            reply_markup=section_keyboard('lessons', include_refresh=True),
        )
        return
    
    lines = ["📅 *Ваши ближайшие уроки:*\n"]
    
    for i, lesson in enumerate(lessons, 1):
        card = format_lesson_card(lesson, compact=True)
        lines.append(f"{i}. {card}")
    
    lines.append("\nОбновить: /lessons")
    
    keyboard = student_lesson_keyboard(
        lessons=lessons,
        callback_prefix='st_lesson',
    )
    
    await update.effective_message.reply_text(
        '\n'.join(lines),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def lesson_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальная информация об уроке"""
    query = update.callback_query
    await query.answer()
    
    lesson_id = int(query.data.split(':')[1])
    
    def get_lesson():
        from schedule.models import Lesson
        return Lesson.objects.select_related('group', 'teacher').get(id=lesson_id)
    
    lesson = await sync_to_async(get_lesson)()
    
    card = format_lesson_card(lesson, compact=False)
    
    # Кнопки для урока
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('◀️ Назад', callback_data='menu:lessons')],
    ])
    
    # Если урок начался и есть zoom ссылка
    if lesson.zoom_join_url:
        keyboard.inline_keyboard.insert(0, [
            InlineKeyboardButton('📹 Войти в Zoom', url=lesson.zoom_join_url)
        ])
    
    await query.edit_message_text(
        card,
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


@require_linked_account
@require_student
async def today_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Уроки на сегодня"""
    user = context.user_data.get('db_user')
    
    def get_today_lessons():
        from schedule.models import Lesson
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        lessons = list(
            Lesson.objects.filter(
                group__students=user,
                start_time__gte=today_start,
                start_time__lt=today_end,
            ).select_related('group', 'teacher').order_by('start_time')
        )
        
        return lessons
    
    lessons = await sync_to_async(get_today_lessons)()
    
    if not lessons:
        await update.effective_message.reply_text(
            "📭 На сегодня уроков нет.",
            reply_markup=section_keyboard('lessons', include_refresh=True),
        )
        return
    
    lines = ["📅 *Уроки на сегодня:*\n"]
    
    for i, lesson in enumerate(lessons, 1):
        card = format_lesson_card(lesson, compact=True)
        lines.append(f"{i}. {card}")
    
    keyboard = student_lesson_keyboard(
        lessons=lessons,
        callback_prefix='st_lesson',
    )
    
    await update.effective_message.reply_text(
        '\n'.join(lines),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )
