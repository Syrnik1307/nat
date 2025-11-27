"""
Telegram бот для администраторов поддержки

Функции:
1. Получение уведомлений о новых тикетах
2. Просмотр тикетов и сообщений
3. Ответ на тикеты прямо из Telegram
4. Назначение тикетов себе
5. Изменение статуса тикетов
"""

import os
import sys
import django
import asyncio
import logging
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
from support.models import SupportTicket, SupportMessage

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Словарь для хранения контекста админов {telegram_id: {'ticket_id': int}}
admin_context = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - регистрация админа"""
    telegram_id = update.effective_user.id
    username = update.effective_user.username
    
    # Проверяем, есть ли пользователь с этим telegram_id
    try:
        user = CustomUser.objects.get(telegram_id=telegram_id)
        if not user.is_staff:
            await update.message.reply_text(
                "❌ Этот бот доступен только для администраторов поддержки.\n"
                "Обратитесь к главному администратору для получения доступа."
            )
            return
        
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
    except CustomUser.DoesNotExist:
        await update.message.reply_text(
            f"👋 Привет! Для регистрации как админ поддержки:\n\n"
            f"1. Зайдите в Django Admin\n"
            f"2. Найдите свой аккаунт в разделе 'Пользователи'\n"
            f"3. Добавьте ваш Telegram ID: `{telegram_id}`\n"
            f"4. Убедитесь что у вас есть права staff/superuser\n"
            f"5. Вернитесь и отправьте /start снова\n\n"
            f"Ваш Telegram username: @{username}"
        )


async def tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /tickets - список открытых тикетов"""
    telegram_id = update.effective_user.id
    
    try:
        user = CustomUser.objects.get(telegram_id=telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    # Получаем открытые тикеты
    open_tickets = SupportTicket.objects.filter(
        status__in=['new', 'in_progress', 'waiting_user']
    ).order_by('-created_at')[:10]
    
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
        user = CustomUser.objects.get(telegram_id=telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    my_tickets = SupportTicket.objects.filter(
        assigned_to=user,
        status__in=['new', 'in_progress', 'waiting_user']
    ).order_by('-updated_at')
    
    if not my_tickets:
        await update.message.reply_text("📭 У вас нет назначенных тикетов")
        return
    
    message = f"📌 *Ваши тикеты ({my_tickets.count()}):*\n\n"
    
    for ticket in my_tickets:
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
        user = CustomUser.objects.get(telegram_id=telegram_id)
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
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        await update.message.reply_text(f"❌ Тикет #{ticket_id} не найден")
        return
    
    # Сохраняем контекст для ответов
    admin_context[telegram_id] = {'ticket_id': ticket_id}
    
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
    messages = ticket.messages.order_by('-created_at')[:5]
    
    if messages:
        message += "\n💬 *Последние сообщения:*\n\n"
        for msg in reversed(list(messages)):
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
    ticket.messages.filter(is_staff_reply=False, read_by_staff=False).update(read_by_staff=True)


async def reply_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на тикет /reply <ticket_id> <сообщение>"""
    telegram_id = update.effective_user.id
    
    try:
        user = CustomUser.objects.get(telegram_id=telegram_id)
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
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        await update.message.reply_text(f"❌ Тикет #{ticket_id} не найден")
        return
    
    # Создаём сообщение
    msg = SupportMessage.objects.create(
        ticket=ticket,
        author=user,
        message=message_text,
        is_staff_reply=True
    )
    
    # Обновляем статус тикета
    if ticket.status == 'new':
        ticket.status = 'in_progress'
    elif ticket.status in ['resolved', 'closed']:
        ticket.status = 'in_progress'
    
    ticket.save()
    
    await update.message.reply_text(
        f"✅ Ответ отправлен на тикет #{ticket_id}\n"
        f"Пользователь получит уведомление на платформе."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений (быстрый ответ на последний просмотренный тикет)"""
    telegram_id = update.effective_user.id
    
    try:
        user = CustomUser.objects.get(telegram_id=telegram_id)
        if not user.is_staff:
            return
    except CustomUser.DoesNotExist:
        return
    
    # Проверяем, есть ли активный контекст
    if telegram_id not in admin_context:
        await update.message.reply_text(
            "💡 Сначала откройте тикет через /view_<id>\n"
            "Или используйте /reply <ticket_id> <сообщение>"
        )
        return
    
    ticket_id = admin_context[telegram_id].get('ticket_id')
    
    if not ticket_id:
        return
    
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        await update.message.reply_text(f"❌ Тикет #{ticket_id} не найден")
        del admin_context[telegram_id]
        return
    
    # Создаём ответ
    message_text = update.message.text
    
    msg = SupportMessage.objects.create(
        ticket=ticket,
        author=user,
        message=message_text,
        is_staff_reply=True
    )
    
    # Обновляем статус
    if ticket.status == 'new':
        ticket.status = 'in_progress'
    elif ticket.status in ['resolved', 'closed']:
        ticket.status = 'in_progress'
    
    ticket.save()
    
    await update.message.reply_text(
        f"✅ Ответ отправлен на тикет #{ticket_id}"
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    try:
        user = CustomUser.objects.get(telegram_id=telegram_id)
        if not user.is_staff:
            await query.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await query.message.reply_text("❌ Сначала зарегистрируйтесь")
        return
    
    action, ticket_id = query.data.split('_')
    ticket_id = int(ticket_id)
    
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        await query.message.reply_text(f"❌ Тикет #{ticket_id} не найден")
        return
    
    if action == 'reply':
        admin_context[telegram_id] = {'ticket_id': ticket_id}
        await query.message.reply_text(
            f"✍️ Тикет #{ticket_id} активен.\n"
            f"Напишите ваш ответ следующим сообщением."
        )
    
    elif action == 'assign':
        ticket.assigned_to = user
        ticket.save()
        await query.message.reply_text(f"✅ Тикет #{ticket_id} назначен вам")
    
    elif action == 'resolve':
        ticket.mark_resolved()
        await query.message.reply_text(f"✅ Тикет #{ticket_id} отмечен как решённый")
    
    elif action == 'progress':
        ticket.status = 'in_progress'
        ticket.save()
        await query.message.reply_text(f"🔄 Тикет #{ticket_id} взят в работу")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - статистика"""
    telegram_id = update.effective_user.id
    
    try:
        user = CustomUser.objects.get(telegram_id=telegram_id)
        if not user.is_staff:
            await update.message.reply_text("❌ Доступ запрещён")
            return
    except CustomUser.DoesNotExist:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")
        return
    
    from django.db.models import Count
    
    total = SupportTicket.objects.count()
    new = SupportTicket.objects.filter(status='new').count()
    in_progress = SupportTicket.objects.filter(status='in_progress').count()
    waiting = SupportTicket.objects.filter(status='waiting_user').count()
    resolved = SupportTicket.objects.filter(status='resolved').count()
    
    my_total = SupportTicket.objects.filter(assigned_to=user).count()
    my_active = SupportTicket.objects.filter(
        assigned_to=user,
        status__in=['new', 'in_progress', 'waiting_user']
    ).count()
    
    message = (
        f"📊 *Статистика поддержки*\n\n"
        f"*Всего тикетов:* {total}\n"
        f"🆕 Новых: {new}\n"
        f"🔄 В работе: {in_progress}\n"
        f"⏳ Ожидают ответа: {waiting}\n"
        f"✅ Решённых: {resolved}\n\n"
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
    
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return
    
    # Получаем всех админов с Telegram ID
    admins = CustomUser.objects.filter(is_staff=True, telegram_id__isnull=False)
    
    priority_emoji = {
        'low': '🟢',
        'normal': '🟡',
        'high': '🟠',
        'urgent': '🔴'
    }.get(ticket.priority, '⚪')
    
    message = (
        f"🆕 *Новый тикет #{ticket.id}*\n\n"
        f"{priority_emoji} *Приоритет:* {ticket.get_priority_display()}\n"
        f"🏷️ *Категория:* {ticket.category}\n"
        f"📝 *Тема:* {ticket.subject}\n"
        f"📄 *Описание:*\n{ticket.description[:200]}...\n\n"
        f"👤 *От:* {ticket.user.get_full_name() if ticket.user else ticket.email}\n\n"
        f"Для просмотра: /view\\_{ticket.id}"
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
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reply", reply_ticket))
    
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
    
    application.run_polling()


if __name__ == '__main__':
    main()
