"""
Telegram бот для восстановления пароля и привязки аккаунта
"""
import os
import django
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import PasswordResetToken
from django.utils import timezone

User = get_user_model()

# Получите токен от @BotFather в Telegram
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
WEBAPP_URL = os.environ.get('WEBAPP_URL', 'http://localhost:3000')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    telegram_id = str(user.id)
    
    # Проверяем, привязан ли уже аккаунт
    try:
        db_user = User.objects.get(telegram_id=telegram_id)
        await update.message.reply_text(
            f"👋 Привет, {db_user.first_name}!\n\n"
            f"✅ Ваш аккаунт уже привязан к системе.\n"
            f"📧 Email: {db_user.email}\n\n"
            f"Доступные команды:\n"
            f"/reset - Сбросить пароль\n"
            f"/unlink - Отвязать аккаунт\n"
            f"/profile - Показать профиль"
        )
    except User.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("🔗 Привязать аккаунт", callback_data='link_account')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"Я бот для восстановления пароля учебной платформы.\n\n"
            f"Чтобы использовать меня, сначала привяжите свой аккаунт:\n"
            f"1. Войдите в личный кабинет на сайте\n"
            f"2. Перейдите в настройки профиля\n"
            f"3. Привяжите Telegram аккаунт\n\n"
            f"Или нажмите кнопку ниже:",
            reply_markup=reply_markup
        )


async def link_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки привязки аккаунта"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = str(query.from_user.id)
    telegram_username = query.from_user.username or ''
    
    await query.edit_message_text(
        f"🔗 Для привязки аккаунта:\n\n"
        f"1. Войдите на платформу: {WEBAPP_URL}\n"
        f"2. Перейдите в Настройки → Безопасность\n"
        f"3. В разделе 'Telegram' введите ваш ID:\n\n"
        f"📱 Ваш Telegram ID: `{telegram_id}`\n"
        f"👤 Username: @{telegram_username}\n\n"
        f"После привязки отправьте /start еще раз",
        parse_mode='Markdown'
    )


async def reset_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /reset - восстановление пароля"""
    telegram_id = str(update.effective_user.id)
    
    try:
        db_user = User.objects.get(telegram_id=telegram_id)
    except User.DoesNotExist:
        await update.message.reply_text(
            "❌ Ваш Telegram не привязан ни к одному аккаунту.\n"
            "Используйте /start для привязки."
        )
        return
    
    # Генерируем токен восстановления
    reset_token = PasswordResetToken.generate_token(db_user, expires_in_minutes=15)
    reset_url = f"{WEBAPP_URL}/reset-password?token={reset_token.token}"
    
    keyboard = [
        [InlineKeyboardButton("🔐 Сбросить пароль", url=reset_url)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔐 Восстановление пароля для {db_user.email}\n\n"
        f"Нажмите кнопку ниже для сброса пароля.\n"
        f"⏱ Ссылка действительна 15 минут.\n\n"
        f"Если вы не запрашивали сброс пароля, просто проигнорируйте это сообщение.",
        reply_markup=reply_markup
    )


async def unlink_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /unlink - отвязка аккаунта"""
    telegram_id = str(update.effective_user.id)
    
    try:
        db_user = User.objects.get(telegram_id=telegram_id)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, отвязать", callback_data='confirm_unlink'),
                InlineKeyboardButton("❌ Отмена", callback_data='cancel_unlink')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ Вы уверены, что хотите отвязать аккаунт?\n\n"
            f"📧 Email: {db_user.email}\n\n"
            f"После отвязки вы не сможете восстанавливать пароль через Telegram.",
            reply_markup=reply_markup
        )
    except User.DoesNotExist:
        await update.message.reply_text(
            "❌ Ваш Telegram не привязан ни к одному аккаунту."
        )


async def confirm_unlink_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение отвязки аккаунта"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = str(query.from_user.id)
    
    try:
        db_user = User.objects.get(telegram_id=telegram_id)
        db_user.telegram_id = None
        db_user.telegram_username = ''
        db_user.save()
        
        await query.edit_message_text(
            "✅ Аккаунт успешно отвязан от Telegram.\n\n"
            "Вы можете привязать его снова в любое время через /start"
        )
    except User.DoesNotExist:
        await query.edit_message_text("❌ Аккаунт не найден.")


async def cancel_unlink_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена отвязки аккаунта"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Отвязка отменена. Ваш аккаунт остаётся привязанным.")


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о профиле"""
    telegram_id = str(update.effective_user.id)
    
    try:
        db_user = User.objects.get(telegram_id=telegram_id)
        
        role_emoji = {
            'student': '🎓',
            'teacher': '👨‍🏫',
            'admin': '⚙️'
        }
        
        role_name = {
            'student': 'Ученик',
            'teacher': 'Учитель',
            'admin': 'Администратор'
        }
        
        await update.message.reply_text(
            f"👤 **Ваш профиль**\n\n"
            f"📧 Email: {db_user.email}\n"
            f"{role_emoji.get(db_user.role, '👤')} Роль: {role_name.get(db_user.role, db_user.role)}\n"
            f"👤 Имя: {db_user.first_name} {db_user.last_name}\n"
            f"📱 Telegram ID: `{telegram_id}`\n"
            f"📅 Дата регистрации: {db_user.created_at.strftime('%d.%m.%Y')}\n\n"
            f"Доступные команды:\n"
            f"/reset - Сбросить пароль\n"
            f"/unlink - Отвязать аккаунт",
            parse_mode='Markdown'
        )
    except User.DoesNotExist:
        await update.message.reply_text(
            "❌ Ваш Telegram не привязан ни к одному аккаунту.\n"
            "Используйте /start для привязки."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📚 **Доступные команды:**\n\n"
        "/start - Начать работу с ботом\n"
        "/reset - Сбросить пароль\n"
        "/profile - Показать профиль\n"
        "/unlink - Отвязать аккаунт\n"
        "/help - Показать эту справку\n\n"
        "❓ **Как это работает:**\n\n"
        "1. Привяжите Telegram к аккаунту в настройках профиля\n"
        "2. Если забыли пароль, отправьте /reset\n"
        "3. Получите ссылку для сброса пароля\n"
        "4. Установите новый пароль\n\n"
        "🔐 Это безопасно - токены действительны только 15 минут!",
        parse_mode='Markdown'
    )


def main():
    """Запуск бота"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Ошибка: не установлен TELEGRAM_BOT_TOKEN")
        print("Получите токен у @BotFather в Telegram и установите переменную окружения:")
        print("  set TELEGRAM_BOT_TOKEN=your_token_here  (Windows)")
        print("  export TELEGRAM_BOT_TOKEN=your_token_here  (Linux/Mac)")
        return
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_password))
    application.add_handler(CommandHandler("unlink", unlink_account))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("help", help_command))
    
    # Регистрируем обработчики кнопок
    application.add_handler(CallbackQueryHandler(link_account_callback, pattern='^link_account$'))
    application.add_handler(CallbackQueryHandler(confirm_unlink_callback, pattern='^confirm_unlink$'))
    application.add_handler(CallbackQueryHandler(cancel_unlink_callback, pattern='^cancel_unlink$'))
    
    # Запускаем бота
    print("🤖 Telegram бот запущен!")
    print(f"🌐 Web приложение: {WEBAPP_URL}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
