"""
Telegram бот для поддержки

Функции для администраторов:
1. Получение уведомлений о новых тикетах
2. Просмотр тикетов и сообщений
3. Ответ на тикеты прямо из Telegram
4. Назначение тикетов себе
5. Изменение статуса тикетов

Функции для преподавателей:
1. Создание обращений в поддержку
2. Просмотр своих тикетов
3. Получение уведомлений об ответах
"""

import os
import sys
import django
import asyncio
import logging
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Настройка Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
from support.models import SupportTicket, SupportMessage, SystemStatus

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Словарь для хранения контекста {telegram_id: {'ticket_id': int, 'mode': 'admin'|'user', 'creating_ticket': {...}}}
user_context = {}


# =============================================================================
# Async-safe ORM wrappers
# =============================================================================

@sync_to_async
def get_user_by_telegram_id(telegram_id: int):
    """Получить пользователя по telegram_id (async-safe)"""
    return CustomUser.objects.get(telegram_id=telegram_id)


@sync_to_async
def get_ticket_by_id(ticket_id: int):
    """Получить тикет по ID (async-safe)"""
    return SupportTicket.objects.get(id=ticket_id)


@sync_to_async
def save_ticket(ticket):
    """Сохранить тикет (async-safe)"""
    ticket.save()


@sync_to_async
def create_support_message(ticket, author, message, is_staff_reply=False):
    """Создать сообщение в тикете (async-safe)"""
    return SupportMessage.objects.create(
        ticket=ticket,
        author=author,
        message=message,
        is_staff_reply=is_staff_reply
    )


@sync_to_async
def create_ticket(user, subject, description, category, email=None, page_url=None, priority='normal', status='new'):
    """Создать новый тикет (async-safe)"""
    return SupportTicket.objects.create(
        user=user,
        subject=subject,
        description=description,
        category=category,
        email=email or (user.email if user else None),
        page_url=page_url,
        priority=priority,
        status=status
    )


@sync_to_async
def get_open_tickets(limit=20):
    """Получить открытые тикеты (async-safe)"""
    return list(SupportTicket.objects.filter(
        status__in=['new', 'in_progress', 'waiting_user']
    ).select_related('user', 'assigned_to').order_by('-updated_at')[:limit])


@sync_to_async
def get_user_tickets(user, limit=10):
    """Получить тикеты пользователя (async-safe)"""
    return list(SupportTicket.objects.filter(
        user=user,
        status__in=['new', 'in_progress', 'waiting_user']
    ).order_by('-updated_at')[:limit])


@sync_to_async
def get_assigned_tickets(user, limit=20):
    """Получить тикеты назначенные пользователю (async-safe)"""
    return list(SupportTicket.objects.filter(
        assigned_to=user,
        status__in=['new', 'in_progress', 'waiting_user']
    ).select_related('user').order_by('-updated_at')[:limit])


@sync_to_async
def get_ticket_messages(ticket, limit=5):
    """Получить сообщения тикета (async-safe)"""
    return list(ticket.messages.order_by('-created_at')[:limit])


@sync_to_async
def mark_messages_read(ticket):
    """Отметить сообщения как прочитанные (async-safe)"""
    ticket.messages.filter(is_staff_reply=False, read_by_staff=False).update(read_by_staff=True)


@sync_to_async
def get_ticket_stats():
    """Получить статистику тикетов (async-safe)"""
    return {
        'new': SupportTicket.objects.filter(status='new').count(),
        'in_progress': SupportTicket.objects.filter(status='in_progress').count(),
        'waiting': SupportTicket.objects.filter(status='waiting_user').count(),
        'resolved': SupportTicket.objects.filter(status='resolved').count()
    }


@sync_to_async
def get_staff_admins():
    """Получить список админов с Telegram ID (async-safe)"""
    return list(CustomUser.objects.filter(is_staff=True, telegram_id__isnull=False))


@sync_to_async
def get_ticket_with_user(ticket_id):
    """Получить тикет с данными пользователя (async-safe)"""
    try:
        ticket = SupportTicket.objects.select_related('user').get(id=ticket_id)
        return {
            'id': ticket.id,
            'priority': ticket.priority,
            'priority_display': ticket.get_priority_display(),
            'category': ticket.category,
            'subject': ticket.subject,
            'description': ticket.description[:200],
            'user_name': ticket.user.get_full_name() if ticket.user else ticket.email
        }
    except SupportTicket.DoesNotExist:
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - главное меню в зависимости от роли"""
    telegram_id = update.effective_user.id
    username = update.effective_user.username
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
        
        if user.is_staff:
            # Меню для администраторов
            await update.message.reply_text(
                f"✅ Привет, {user.first_name}!\n\n"
                f"Ты подключен как администратор поддержки.\n\n"
                f"Команды:\n"
                f"/tickets - Список открытых тикетов\n"
                f"/my - Мои назначенные тикеты\n"
                f"/stats - Статистика\n"
                f"/help - Справка\n\n"
                f"Чтобы ответить на тикет, используй:\n"
                f"/reply <ticket_id> <сообщение>"
            )
            user_context[telegram_id] = {'mode': 'admin'}
        else:
            # Меню для преподавателей и учеников
            await update.message.reply_text(
                f"👋 Привет, {user.first_name}!\n\n"
                f"Команды:\n"
                f"/support_request - Создать обращение в поддержку\n"
                f"/my_tickets - Мои обращения\n"
                f"/help - Справка"
            )
            user_context[telegram_id] = {'mode': 'user'}
            
    except CustomUser.DoesNotExist:
        await update.message.reply_text(
            f"👋 Привет! Для использования этого бота:\n\n"
            f"1. Откройте Teaching Panel на платформе\n"
            f"2. Зайдите в Профиль → Безопасность\n"
            f"3. Добавьте ваш Telegram ID: `{telegram_id}`\n"
            f"4. Вернитесь и отправьте /start\n\n"
            f"Ваш Telegram: @{username}"
        )


async def support_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /support_request - создание обращения для преподов"""
    telegram_id = update.effective_user.id
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    if user.is_staff:
        await update.message.reply_text("✅ Для администраторов используйте /tickets")
        return
    
    # Инициализируем контекст создания тикета
    user_context[telegram_id] = {
        'mode': 'user',
        'creating_ticket': {
            'step': 'subject',  # subject -> category -> message
            'subject': '',
            'category': ''
        }
    }
    
    # Список категорий
    categories = SupportTicket.CATEGORY_CHOICES
    keyboard = [
        [InlineKeyboardButton(cat_name, callback_data=f'category_{cat_code}')]
        for cat_code, cat_name in categories
    ]
    
    await update.message.reply_text(
        "Сначала выберите категорию вашего обращения:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /my_tickets - мои обращения"""
    telegram_id = update.effective_user.id
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    if user.is_staff:
        await update.message.reply_text("✅ Используйте /my для просмотра назначенных тикетов")
        return
    
    # Получаем тикеты пользователя
    my_tickets_qs = await get_user_tickets(user)
    
    if not my_tickets_qs:
        await update.message.reply_text("📭 У вас нет открытых обращений")
        return
    
    message = f"📋 *Ваши обращения ({my_tickets_qs.count()}):*\n\n"
    
    for ticket in my_tickets_qs:
        status_emoji = {
            'new': '🆕',
            'in_progress': '🔄',
            'waiting_user': '⏳'
        }.get(ticket.status, '❓')
        
        category = dict(SupportTicket.CATEGORY_CHOICES).get(ticket.category, ticket.category)
        
        message += (
            f"{status_emoji} *#{ticket.id}*\n"
            f"📝 {ticket.subject}\n"
            f"🏷️ {category}\n"
            f"🕐 {ticket.updated_at.strftime('%d.%m %H:%M')}\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /tickets - список открытых тикетов"""
    telegram_id = update.effective_user.id
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    # Получаем открытые тикеты
    open_tickets = await get_open_tickets(limit=10)
    
    if not open_tickets:
        await update.message.reply_text("✅ Нет открытых тикетов!")
        return
    
    message = "📋 *Открытые тикеты:*\n\n"
    
    for ticket in open_tickets:
        status_emoji = {
            'new': '🆕',
            'in_progress': '🔄',
            'waiting_user': '⏳',
            'resolved': '✅',
            'closed': '🔒'
        }.get(ticket.status, '❓')
        
        priority_emoji = {
            'low': '🟢',
            'normal': '🟡',
            'high': '🟠',
            'urgent': '🔴'
        }.get(ticket.priority, '⚪')
        
        assigned = f"👤 {ticket.assigned_to.first_name}" if ticket.assigned_to else "👥 Не назначен"
        
        unread = ticket.messages.filter(is_staff_reply=False, read_by_staff=False).count()
        unread_badge = f" 💬 {unread}" if unread > 0 else ""
        
        message += (
            f"{status_emoji} {priority_emoji} *Тикет #{ticket.id}*{unread_badge}\n"
            f"📝 {ticket.subject}\n"
            f"{assigned}\n"
            f"🕐 {ticket.created_at.strftime('%d.%m %H:%M')}\n"
            f"/view\\_{ticket.id}\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /my - мои назначенные тикеты"""
    telegram_id = update.effective_user.id
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    my_tickets_list = await get_assigned_tickets(user)
    
    if not my_tickets_list:
        await update.message.reply_text("📭 У вас нет назначенных тикетов")
        return
    
    message = f"📌 *Ваши тикеты ({len(my_tickets_list)}):*\n\n"
    
    for ticket in my_tickets_list:
        status_emoji = {
            'new': '🆕',
            'in_progress': '🔄',
            'waiting_user': '⏳'
        }.get(ticket.status, '❓')
        
        unread = ticket.messages.filter(is_staff_reply=False, read_by_staff=False).count()
        unread_badge = f" 💬 {unread}" if unread > 0 else ""
        
        message += (
            f"{status_emoji} *Тикет #{ticket.id}*{unread_badge}\n"
            f"📝 {ticket.subject}\n"
            f"🕐 {ticket.updated_at.strftime('%d.%m %H:%M')}\n"
            f"/view\\_{ticket.id}\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def view_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр конкретного тикета /view_<ticket_id>"""
    telegram_id = update.effective_user.id
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    # Извлекаем ticket_id из команды
    command = update.message.text
    try:
        ticket_id = int(command.split('_')[1])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Неверный формат команды")
        return
    
    try:
        ticket = await get_ticket_by_id(ticket_id)
    except SupportTicket.DoesNotExist:
        await update.message.reply_text(f"❌ Тикет #{ticket_id} не найден")
        return
    
    # Сохраняем контекст для ответов
    user_context[telegram_id] = user_context.get(telegram_id, {'mode': 'admin'})
    user_context[telegram_id]['ticket_id'] = ticket_id
    
    # Формируем информацию о тикете
    status_text = {
        'new': '🆕 Новый',
        'in_progress': '🔄 В работе',
        'waiting_user': '⏳ Ожидает ответа',
        'resolved': '✅ Решён',
        'closed': '🔒 Закрыт'
    }.get(ticket.status, ticket.status)
    
    priority_text = {
        'low': '🟢 Низкий',
        'normal': '🟡 Обычный',
        'high': '🟠 Высокий',
        'urgent': '🔴 Срочный'
    }.get(ticket.priority, ticket.priority)
    
    user_info = f"👤 {ticket.user.get_full_name()}" if ticket.user else f"📧 {ticket.email}"
    assigned = f"👥 {ticket.assigned_to.first_name}" if ticket.assigned_to else "👥 Не назначен"
    
    message = (
        f"*Тикет #{ticket.id}*\n\n"
        f"📝 *Тема:* {ticket.subject}\n"
        f"📄 *Описание:*\n{ticket.description}\n\n"
        f"📊 *Статус:* {status_text}\n"
        f"⚡ *Приоритет:* {priority_text}\n"
        f"🏷️ *Категория:* {ticket.category}\n"
        f"{user_info}\n"
        f"{assigned}\n"
        f"🕐 *Создан:* {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )
    
    if ticket.page_url:
        message += f"🔗 *Страница:* {ticket.page_url}\n"
    
    # Получаем последние 5 сообщений
    messages = await get_ticket_messages(ticket, limit=5)
    
    if messages:
        message += "\n💬 *Последние сообщения:*\n\n"
        for msg in reversed(messages):
            author = "🛡️ Поддержка" if msg.is_staff_reply else "👤 Пользователь"
            msg_time = msg.created_at.strftime('%d.%m %H:%M')
            message += f"{author} ({msg_time}):\n{msg.message}\n\n"
    
    # Кнопки действий
    keyboard = [
        [
            InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{ticket_id}"),
            InlineKeyboardButton("👤 Назначить себе", callback_data=f"assign_{ticket_id}")
        ],
        [
            InlineKeyboardButton("✅ Решён", callback_data=f"resolve_{ticket_id}"),
            InlineKeyboardButton("🔄 В работе", callback_data=f"progress_{ticket_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    # Отмечаем сообщения как прочитанные
    await mark_messages_read(ticket)


async def reply_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на тикет /reply <ticket_id> <сообщение>"""
    telegram_id = update.effective_user.id
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    # Парсим команду
    parts = update.message.text.split(maxsplit=2)
    
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Неверный формат.\n"
            "Используйте: /reply <ticket_id> <сообщение>"
        )
        return
    
    try:
        ticket_id = int(parts[1])
        message_text = parts[2]
    except ValueError:
        await update.message.reply_text("❌ Ticket ID должен быть числом")
        return
    
    try:
        ticket = await get_ticket_by_id(ticket_id)
    except SupportTicket.DoesNotExist:
        await update.message.reply_text(f"❌ Тикет #{ticket_id} не найден")
        return
    
    # Создаём сообщение
    await create_support_message(ticket, user, message_text, is_staff_reply=True)
    
    # Обновляем статус тикета
    if ticket.status == 'new':
        ticket.status = 'in_progress'
    elif ticket.status in ['resolved', 'closed']:
        ticket.status = 'in_progress'
    
    await save_ticket(ticket)
    
    await update.message.reply_text(
        f"✅ Ответ отправлен на тикет #{ticket_id}\n"
        f"Пользователь получит уведомление на платформе."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений (быстрый ответ на последний просмотренный тикет)"""
    telegram_id = update.effective_user.id
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if not user.is_staff:
            return
    except CustomUser.DoesNotExist:
        return
    
    # Проверяем, есть ли активный контекст
    ctx = user_context.get(telegram_id, {})
    mode = ctx.get('mode')
    
    # Для администраторов
    if mode == 'admin':
        if telegram_id not in user_context or 'ticket_id' not in ctx:
            await update.message.reply_text(
                "💡 Сначала откройте тикет через /view_<id>\n"
                "Или используйте /reply <ticket_id> <сообщение>"
            )
            return
        
        ticket_id = ctx.get('ticket_id')
        
        try:
            ticket = await get_ticket_by_id(ticket_id)
        except SupportTicket.DoesNotExist:
            await update.message.reply_text(f"❌ Тикет #{ticket_id} не найден")
            if telegram_id in user_context:
                del user_context[telegram_id]['ticket_id']
            return
        
        # Создаём ответ
        message_text = update.message.text
        
        await create_support_message(ticket, user, message_text, is_staff_reply=True)
        
        # Обновляем статус
        if ticket.status == 'new':
            ticket.status = 'in_progress'
        elif ticket.status in ['resolved', 'closed']:
            ticket.status = 'in_progress'
        
        await save_ticket(ticket)
        
        await update.message.reply_text(
            f"✅ Ответ отправлен на тикет #{ticket_id}"
        )
    
    # Для преподавателей (создание тикета)
    elif mode == 'user':
        creating = ctx.get('creating_ticket')
        
        if not creating:
            return
        
        step = creating.get('step')
        
        if step == 'subject':
            # Собираем тему обращения
            creating['subject'] = update.message.text
            creating['step'] = 'message'
            await update.message.reply_text(
                "Опишите вашу проблему или вопрос:"
            )
        
        elif step == 'message':
            # Создаём тикет
            description = update.message.text
            category = creating.get('category', 'other')
            subject = creating.get('subject', 'Обращение из Telegram')
            
            ticket = await create_ticket(
                user=user,
                subject=subject,
                description=description,
                category=category,
                priority='normal',
                status='new'
            )
            
            # Очищаем контекст
            user_context[telegram_id] = {'mode': 'user'}
            
            await update.message.reply_text(
                f"✅ Ваше обращение #{ticket.id} создано!\\n\\n"
                f"Администраторы ответят вам в ближайшее время.\\n"
                f"Вы получите уведомление об ответе."
            )
        
        return
    
    # Если контекста нет, игнорируем
    return


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    callback_data = query.data
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
    except CustomUser.DoesNotExist:
        await query.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    # Обработка выбора категории для преподов
    if callback_data.startswith('category_'):
        ctx = user_context.get(telegram_id, {})
        if ctx.get('mode') != 'user':
            return
        
        creating = ctx.get('creating_ticket')
        if not creating:
            return
        
        category = callback_data.replace('category_', '')
        creating['category'] = category
        creating['step'] = 'subject'
        
        cat_name = dict(SupportTicket.CATEGORY_CHOICES).get(category, category)
        
        await query.edit_message_text(
            f"Вы выбрали категорию: *{cat_name}*\\n\\n"
            f"Напишите тему вашего обращения:"
        )
        return
    
    # Обработка кнопок для админов
    if not user.is_staff:
        await query.message.reply_text("❌ Доступ запрещён")
        return
    
    action, ticket_id = query.data.split('_', 1)
    try:
        ticket_id = int(ticket_id)
    except ValueError:
        return
    
    try:
        ticket = await get_ticket_by_id(ticket_id)
    except SupportTicket.DoesNotExist:
        await query.message.reply_text(f"❌ Тикет #{ticket_id} не найден")
        return
    
    if action == 'reply':
        user_context[telegram_id] = user_context.get(telegram_id, {'mode': 'admin'})
        user_context[telegram_id]['ticket_id'] = ticket_id
        await query.message.reply_text(
            f"✍️ Тикет #{ticket_id} активен.\n"
            f"Напишите ваш ответ следующим сообщением."
        )
    
    elif action == 'assign':
        ticket.assigned_to = user
        await save_ticket(ticket)
        await query.message.reply_text(f"✅ Тикет #{ticket_id} назначен вам")
    
    elif action == 'resolve':
        await sync_to_async(ticket.mark_resolved)()
        await query.message.reply_text(f"✅ Тикет #{ticket_id} отмечен как решённый")
    
    elif action == 'progress':
        ticket.status = 'in_progress'
        await save_ticket(ticket)
        await query.message.reply_text(f"🔄 Тикет #{ticket_id} взят в работу")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - статистика"""
    telegram_id = update.effective_user.id
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    # Получаем статистику через async wrapper
    stats_data = await get_ticket_stats()
    
    @sync_to_async
    def get_user_stats(u):
        my_total = SupportTicket.objects.filter(assigned_to=u).count()
        my_active = SupportTicket.objects.filter(
            assigned_to=u,
            status__in=['new', 'in_progress', 'waiting_user']
        ).count()
        return my_total, my_active
    
    my_total, my_active = await get_user_stats(user)
    total = stats_data['new'] + stats_data['in_progress'] + stats_data['waiting'] + stats_data['resolved']
    
    message = (
        f"📊 *Статистика поддержки*\n\n"
        f"*Всего тикетов:* {total}\n"
        f"🆕 Новых: {stats_data['new']}\n"
        f"🔄 В работе: {stats_data['in_progress']}\n"
        f"⏳ Ожидают ответа: {stats_data['waiting']}\n"
        f"✅ Решённых: {stats_data['resolved']}\n\n"
        f"*Ваши тикеты:*\n"
        f"📌 Всего назначено: {my_total}\n"
        f"🔥 Активных: {my_active}"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - справка"""
    message = (
        "*🤖 Справка по боту поддержки*\n\n"
        "*Основные команды:*\n"
        "/start - Регистрация/проверка доступа\n"
        "/tickets - Список открытых тикетов\n"
        "/my - Мои назначенные тикеты\n"
        "/view\\_<id> - Просмотр тикета\n"
        "/reply <id> <текст> - Ответ на тикет\n"
        "/stats - Статистика\n"
        "/help - Эта справка\n\n"
        "*Быстрые ответы:*\n"
        "После команды /view\\_<id> можно просто написать сообщение "
        "и оно автоматически отправится как ответ на этот тикет.\n\n"
        "*Кнопки управления:*\n"
        "✍️ Ответить - активировать режим быстрого ответа\n"
        "👤 Назначить себе - взять тикет в работу\n"
        "✅ Решён - закрыть тикет\n"
        "🔄 В работе - перевести в статус 'в работе'"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def notify_new_ticket(ticket_id: int, bot_token: str):
    """
    Отправка уведомления о новом тикете всем админам
    Эта функция вызывается из Django при создании тикета
    """
    bot = Application.builder().token(bot_token).build()
    
    # Используем async-safe обёртку
    ticket_data = await get_ticket_with_user(ticket_id)
    if not ticket_data:
        return
    
    # Получаем всех админов с Telegram ID через async-safe обёртку
    admins = await get_staff_admins()
    
    priority_emoji = {
        'low': '🟢',
        'normal': '🟡',
        'high': '🟠',
        'urgent': '🔴'
    }.get(ticket_data['priority'], '⚪')
    
    message = (
        f"🆕 *Новый тикет #{ticket_data['id']}*\n\n"
        f"{priority_emoji} *Приоритет:* {ticket_data['priority_display']}\n"
        f"🏷️ *Категория:* {ticket_data['category']}\n"
        f"📝 *Тема:* {ticket_data['subject']}\n"
        f"📄 *Описание:*\n{ticket_data['description']}...\n\n"
        f"👤 *От:* {ticket_data['user_name']}\n\n"
        f"Для просмотра: /view\\_{ticket_data['id']}"
    )
    
    for admin in admins:
        try:
            await bot.bot.send_message(
                chat_id=admin.telegram_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу {admin.id}: {e}")


# ============ Инцидент-режим ============

@sync_to_async
def start_incident_sync(title, user):
    """Начать инцидент (async-safe)"""
    status = SystemStatus.get_current()
    status.start_incident(title=title, user=user)
    return status.incident_started_at.strftime('%d.%m.%Y %H:%M')


@sync_to_async
def resolve_incident_sync(message, user):
    """Завершить инцидент (async-safe)"""
    status = SystemStatus.get_current()
    if status.status == 'operational':
        return None
    old_title = status.incident_title
    status.resolve_incident(message=message, user=user)
    return old_title


@sync_to_async
def get_system_status():
    """Получить текущий статус системы (async-safe)"""
    return SystemStatus.get_current()


async def incident_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /incident <название> - начать инцидент (P0)"""
    telegram_id = update.effective_user.id
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    # Получаем название инцидента
    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ Укажите название инцидента:\n"
            "/incident Проблемы с оплатой\n"
            "/incident Zoom не работает"
        )
        return
    
    title = ' '.join(args)
    incident_time = await start_incident_sync(title, user)
    
    # Уведомляем всех админов через async-safe обёртку
    admins = await get_staff_admins()
    
    message = (
        f"🔴🔴🔴 *ИНЦИДЕНТ ОБЪЯВЛЕН* 🔴🔴🔴\n\n"
        f"📛 *{title}*\n\n"
        f"Объявил: {user.first_name}\n"
        f"Время: {incident_time}\n\n"
        f"Автоответ включён для новых тикетов.\n"
        f"Закончить: /resolve <сообщение>"
    )
    
    for admin in admins:
        if admin.telegram_id != telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=admin.telegram_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception:
                pass
    
    await update.message.reply_text(
        f"🔴 Инцидент объявлен: *{title}*\n\n"
        f"• Статус системы изменён на 'Серьёзный сбой'\n"
        f"• Пользователи видят баннер в виджете поддержки\n"
        f"• Все админы уведомлены\n\n"
        f"Для завершения: /resolve Проблема решена",
        parse_mode='Markdown'
    )


async def incident_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /resolve <сообщение> - завершить инцидент"""
    telegram_id = update.effective_user.id
    
    try:
        user = CustomUser.objects.get(telegram_id=telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    status = SystemStatus.get_current()
    
    if status.status == 'operational':
        await update.message.reply_text("ℹ️ Нет активного инцидента")
        return
    
    args = context.args
    message = ' '.join(args) if args else 'Проблема решена'
    
    old_title = status.incident_title
    status.resolve_incident(message=message, user=user)
    
    # Уведомляем всех админов
    admins = CustomUser.objects.filter(is_staff=True, telegram_id__isnull=False)
    
    notification = (
        f"✅ *ИНЦИДЕНТ ЗАВЕРШЁН*\n\n"
        f"📛 {old_title}\n"
        f"💬 {message}\n\n"
        f"Завершил: {user.first_name}"
    )
    
    for admin in admins:
        if admin.telegram_id != telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=admin.telegram_id,
                    text=notification,
                    parse_mode='Markdown'
                )
            except Exception:
                pass
    
    await update.message.reply_text(
        f"✅ Инцидент завершён\n\n"
        f"• Статус системы: Всё работает\n"
        f"• Баннер убран\n"
        f"• Все админы уведомлены",
        parse_mode='Markdown'
    )


async def system_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - проверить статус системы"""
    telegram_id = update.effective_user.id
    
    try:
        user = CustomUser.objects.get(telegram_id=telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    status = SystemStatus.get_current()
    
    status_emoji = {
        'operational': '✅',
        'degraded': '⚠️',
        'major_outage': '🔴',
        'maintenance': '🔧'
    }.get(status.status, '❓')
    
    message = f"{status_emoji} *Статус системы: {status.get_status_display()}*\n\n"
    
    if status.status != 'operational':
        message += f"📛 *Инцидент:* {status.incident_title}\n"
        if status.incident_started_at:
            message += f"🕐 *Начало:* {status.incident_started_at.strftime('%d.%m.%Y %H:%M')}\n"
        if status.message:
            message += f"💬 *Сообщение:* {status.message}\n"
    
    message += f"\n🔄 *Обновлено:* {status.updated_at.strftime('%d.%m.%Y %H:%M')}"
    
    keyboard = []
    if status.status == 'operational':
        keyboard.append([InlineKeyboardButton("🔴 Объявить инцидент", callback_data="incident_start")])
    else:
        keyboard.append([InlineKeyboardButton("✅ Завершить инцидент", callback_data="incident_resolve")])
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )


async def sla_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /sla - проверить тикеты с нарушением SLA"""
    telegram_id = update.effective_user.id
    
    try:
        user = CustomUser.objects.get(telegram_id=telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    
    # Тикеты без первого ответа с просроченным SLA
    breached = []
    open_tickets = SupportTicket.objects.filter(
        status__in=['new', 'in_progress'],
        first_response_at__isnull=True
    )
    
    for ticket in open_tickets:
        if ticket.sla_breached:
            breached.append(ticket)
    
    if not breached:
        await update.message.reply_text("✅ Нет тикетов с нарушением SLA!")
        return
    
    message = f"⚠️ *Тикеты с нарушением SLA ({len(breached)}):*\n\n"
    
    for ticket in breached[:10]:
        priority_emoji = {
            'p0': '🔴🔴🔴',
            'p1': '🔴',
            'p2': '🟡',
            'p3': '🟢'
        }.get(ticket.priority, '⚪')
        
        overdue_mins = int((now - ticket.sla_deadline).total_seconds() / 60)
        
        message += (
            f"{priority_emoji} *#{ticket.id}* - {ticket.subject[:30]}\n"
            f"⏱️ Просрочен на {overdue_mins} мин\n"
            f"/view\\_{ticket.id}\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')


def main():
    """Запуск бота"""
    token = os.getenv('SUPPORT_BOT_TOKEN')
    
    if not token:
        print("❌ Не установлен SUPPORT_BOT_TOKEN")
        print("Создайте бота через @BotFather и установите переменную окружения")
        sys.exit(1)
    
    application = Application.builder().token(token).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tickets", tickets))
    application.add_handler(CommandHandler("my", my_tickets))
    application.add_handler(CommandHandler("support_request", support_request))
    application.add_handler(CommandHandler("my_tickets", my_tickets))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reply", reply_ticket))
    
    # Инцидент-команды
    application.add_handler(CommandHandler("incident", incident_start))
    application.add_handler(CommandHandler("resolve", incident_resolve))
    application.add_handler(CommandHandler("status", system_status_cmd))
    application.add_handler(CommandHandler("sla", sla_check))
    
    # Обработчик для /view_<ticket_id>
    application.add_handler(MessageHandler(
        filters.Regex(r'^/view_\d+$'),
        view_ticket
    ))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик обычных текстовых сообщений (для быстрых ответов)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    print("✅ Бот поддержки запущен!")
    print(f"Команды: /start, /tickets, /my, /view_<id>, /reply, /stats, /help")
    print(f"Инцидент: /incident, /resolve, /status, /sla")
    
    application.run_polling()


if __name__ == '__main__':
    main()
