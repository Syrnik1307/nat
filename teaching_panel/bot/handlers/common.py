"""
Общие обработчики команд (start, menu, help)
"""
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async

from ..utils import require_linked_account
from ..keyboards import main_menu_keyboard
from ..config import WEBAPP_URL

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    telegram_id = update.effective_user.id
    
    # Проверяем привязку аккаунта
    def check_user():
        from accounts.models import CustomUser
        try:
            user = CustomUser.objects.get(telegram_id=str(telegram_id))
            return user
        except CustomUser.DoesNotExist:
            return None
    
    user = await sync_to_async(check_user)()
    
    if user:
        context.user_data['db_user'] = user
        
        role = user.role
        name = user.get_full_name() or user.email.split('@')[0]
        
        role_text = {
            'teacher': 'Преподаватель',
            'student': 'Ученик',
            'admin': 'Администратор',
        }.get(role, 'Пользователь')
        
        await update.message.reply_text(
            f"👋 Добро пожаловать, *{name}*!\n\n"
            f"Ваша роль: {role_text}\n\n"
            f"Используйте меню ниже для навигации:",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard(role),
        )
    else:
        # Неавторизованный пользователь
        buttons = []
        if WEBAPP_URL:
            buttons.append([InlineKeyboardButton('🌐 Войти на сайте', url=WEBAPP_URL)])
        buttons.append([InlineKeyboardButton('🔗 Привязать аккаунт', callback_data='link_account')])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await update.message.reply_text(
            "👋 Добро пожаловать в Teaching Panel!\n\n"
            "Для использования бота привяжите свой аккаунт.\n\n"
            "Если у вас ещё нет аккаунта - зарегистрируйтесь на сайте.",
            reply_markup=keyboard,
        )


@require_linked_account
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /menu"""
    user = context.user_data.get('db_user')
    role = user.role if user else 'student'
    
    await update.message.reply_text(
        "📱 *Главное меню*\n\n"
        "Выберите раздел:",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard(role),
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик возврата в меню через inline кнопку"""
    query = update.callback_query
    await query.answer()
    
    user = context.user_data.get('db_user')
    
    if not user:
        telegram_id = update.effective_user.id
        
        def get_user():
            from accounts.models import CustomUser
            try:
                return CustomUser.objects.get(telegram_id=str(telegram_id))
            except CustomUser.DoesNotExist:
                return None
        
        user = await sync_to_async(get_user)()
        if user:
            context.user_data['db_user'] = user
    
    if not user:
        await query.edit_message_text(
            "❌ Аккаунт не привязан. Используйте /start"
        )
        return
    
    role = user.role
    section = query.data.split(':')[1] if ':' in query.data else None
    
    if section == 'main' or not section:
        await query.edit_message_text(
            "📱 *Главное меню*\n\n"
            "Выберите раздел:",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard(role),
        )
    elif section == 'lessons':
        # Переход в раздел уроков
        if role == 'teacher':
            await query.edit_message_text(
                "📅 *Уроки*\n\n"
                "Выберите действие:",
                parse_mode='Markdown',
                reply_markup=_teacher_lessons_keyboard(),
            )
        else:
            # Для студента вызываем my_lessons
            from .student import my_lessons
            # Передаём управление
            context.user_data['db_user'] = user
            await my_lessons(update, context)
    elif section == 'homework':
        if role == 'teacher':
            await query.edit_message_text(
                "📝 *Домашние задания*\n\n"
                "Выберите действие:",
                parse_mode='Markdown',
                reply_markup=_teacher_homework_keyboard(),
            )
        else:
            from .student import my_homework
            context.user_data['db_user'] = user
            await my_homework(update, context)
    elif section == 'broadcast':
        if role in ['teacher', 'admin']:
            await query.edit_message_text(
                "📣 *Рассылки*\n\n"
                "Выберите тип рассылки:",
                parse_mode='Markdown',
                reply_markup=_broadcast_menu_keyboard(),
            )
        else:
            await query.answer("Недоступно для учеников", show_alert=True)
    elif section == 'progress':
        if role == 'student':
            from .student import my_progress
            context.user_data['db_user'] = user
            await my_progress(update, context)


@require_linked_account
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    user = context.user_data.get('db_user')
    role = user.role if user else 'student'
    
    if role == 'teacher':
        text = (
            "📚 *Справка для преподавателей*\n\n"
            "*Команды:*\n"
            "/menu - Главное меню\n"
            "/remind\\_lesson - Напомнить об уроке\n"
            "/remind\\_hw - Напомнить о ДЗ\n"
            "/check\\_hw - Проверить сдачу ДЗ\n"
            "/scheduled - Запланированные сообщения\n"
            "/profile - Ваш профиль\n\n"
            "*Возможности:*\n"
            "• Отправка напоминаний ученикам\n"
            "• Проверка кто сдал ДЗ\n"
            "• Пинг не сдавших\n"
            "• Отложенные рассылки\n"
        )
    elif role == 'admin':
        text = (
            "📚 *Справка для администраторов*\n\n"
            "*Команды:*\n"
            "/menu - Главное меню\n"
            "/stats - Статистика системы\n"
            "/broadcast - Массовая рассылка\n"
            "/profile - Ваш профиль\n"
        )
    else:
        text = (
            "📚 *Справка для учеников*\n\n"
            "*Команды:*\n"
            "/menu - Главное меню\n"
            "/lessons - Мои уроки\n"
            "/homework - Мои ДЗ\n"
            "/pending - Несданные ДЗ\n"
            "/progress - Мой прогресс\n"
            "/profile - Мой профиль\n\n"
            "*Возможности:*\n"
            "• Просмотр расписания\n"
            "• Список домашних заданий\n"
            "• Отслеживание прогресса\n"
        )
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard(role),
    )


@require_linked_account
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /profile"""
    user = context.user_data.get('db_user')
    
    role_text = {
        'teacher': 'Преподаватель',
        'student': 'Ученик',
        'admin': 'Администратор',
    }.get(user.role, 'Пользователь')
    
    consent_text = "Да" if user.notification_consent else "Нет"
    
    lines = [
        "👤 *Ваш профиль*\n",
        f"📧 Email: {user.email}",
        f"👤 Имя: {user.get_full_name() or '—'}",
        f"🎭 Роль: {role_text}",
        f"📱 Telegram: привязан",
        f"🔔 Уведомления: {consent_text}",
    ]
    
    buttons = [
        [InlineKeyboardButton('◀️ Меню', callback_data='menu:main')],
    ]
    
    if WEBAPP_URL:
        buttons.insert(0, [InlineKeyboardButton('🌐 Открыть профиль', url=f"{WEBAPP_URL}/profile")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    await update.message.reply_text(
        '\n'.join(lines),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


def _teacher_lessons_keyboard():
    """Клавиатура раздела уроков для учителя"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📅 Напомнить об уроке', callback_data='action:remind_lesson')],
        [InlineKeyboardButton('📋 Мои группы', callback_data='action:my_groups')],
        [InlineKeyboardButton('◀️ Назад', callback_data='menu:main')],
    ])


def _teacher_homework_keyboard():
    """Клавиатура раздела ДЗ для учителя"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('✓ Проверить сдачу', callback_data='action:check_hw')],
        [InlineKeyboardButton('📝 Напомнить о ДЗ', callback_data='action:remind_hw')],
        [InlineKeyboardButton('◀️ Назад', callback_data='menu:main')],
    ])


def _broadcast_menu_keyboard():
    """Клавиатура раздела рассылок"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📅 Напомнить об уроке', callback_data='action:remind_lesson')],
        [InlineKeyboardButton('📝 Напомнить о ДЗ', callback_data='action:remind_hw')],
        [InlineKeyboardButton('📋 Запланированные', callback_data='action:scheduled')],
        [InlineKeyboardButton('◀️ Назад', callback_data='menu:main')],
    ])
