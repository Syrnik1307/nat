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
from accounts.models import PasswordResetToken, NotificationSettings
from accounts.telegram_utils import (
    link_account_with_code,
    TelegramVerificationError,
    unlink_user_telegram,
)
from django.utils import timezone

User = get_user_model()

# Получите токен от @BotFather в Telegram
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
WEBAPP_URL = os.environ.get('WEBAPP_URL', 'http://localhost:3000')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start с поддержкой deep-link кода."""
    user = update.effective_user
    telegram_id = str(user.id)
    args = context.args if context.args else []

    if args:
        code = args[0].strip().upper()
        try:
            link_account_with_code(
                code=code,
                telegram_id=telegram_id,
                telegram_username=user.username or '',
                telegram_chat_id=str(update.effective_chat.id),
            )
            await update.message.reply_text(
                "✅ Аккаунт успешно привязан!\n"
                "Теперь вы можете сбрасывать пароль через /reset и получать уведомления."
            )
        except TelegramVerificationError as exc:
            await update.message.reply_text(f"❌ Не удалось привязать аккаунт: {exc}")
        return

    # Проверяем, привязан ли уже аккаунт
    try:
        db_user = User.objects.get(telegram_id=telegram_id)
        await update.message.reply_text(
            f"👋 Привет, {db_user.first_name or user.first_name}!\n\n"
            f"✅ Аккаунт уже привязан.\n"
            f"📧 Email: {db_user.email}\n\n"
            f"Команды:\n"
            f"/reset — сбросить пароль\n"
            f"/profile — профиль\n"
            f"/notifications — узнать настройки\n"
            f"/unlink — отвязать Telegram"
        )
    except User.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("🔗 Как привязать аккаунт", callback_data='link_account')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"Я бот Teaching Panel. Чтобы пользоваться мной:\n\n"
            f"1. Откройте Teaching Panel → Профиль → вкладка 'Безопасность'\n"
            f"2. Создайте код привязки Telegram\n"
            f"3. Вернитесь в Telegram и отправьте /start <код>\n\n"
            f"Нажмите кнопку ниже, чтобы получить инструкцию ещё раз.",
            reply_markup=reply_markup
        )


async def link_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки привязки аккаунта"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = str(query.from_user.id)
    telegram_username = query.from_user.username or ''
    
    await query.edit_message_text(
        f"🔗 Новая инструкция по привязке:\n\n"
        f"1. Зайдите на {WEBAPP_URL}\n"
        f"2. Откройте Профиль → вкладку 'Безопасность'\n"
        f"3. Нажмите 'Получить код' в блоке Telegram\n"
        f"4. Вернитесь в этот чат и отправьте команду /start <код>\n\n"
        f"Ваш Telegram ID: `{telegram_id}`\n"
        f"Username: @{telegram_username}\n\n"
        f"После успешной привязки /start покажет статус",
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

    if not db_user.telegram_verified:
        await update.message.reply_text(
            "❌ Telegram ещё не подтверждён. Создайте код в профиле и отправьте /start <код>."
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
        unlink_user_telegram(db_user)
        
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


async def notifications_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает текущие настройки уведомлений пользователя."""
    telegram_id = str(update.effective_user.id)

    try:
        db_user = User.objects.get(telegram_id=telegram_id)
    except User.DoesNotExist:
        await update.message.reply_text(
            "❌ Telegram ещё не привязан. Используйте /start для привязки."
        )
        return

    try:
        settings_obj = db_user.notification_settings
    except NotificationSettings.DoesNotExist:
        settings_obj = NotificationSettings.objects.create(user=db_user)

    message = (
        "🔔 *Настройки уведомлений*\n\n"
        f"Telegram включён: {'✅' if settings_obj.telegram_enabled else '❌'}\n"
        f"ДЗ сдано (учителю): {'✅' if settings_obj.notify_homework_submitted else '❌'}\n"
        f"ДЗ проверено (ученику): {'✅' if settings_obj.notify_homework_graded else '❌'}\n"
        f"Дедлайны ДЗ: {'✅' if settings_obj.notify_homework_deadline else '❌'}\n"
        f"Напоминания об уроках: {'✅' if settings_obj.notify_lesson_reminders else '❌'}\n"
        f"Новое ДЗ: {'✅' if settings_obj.notify_new_homework else '❌'}\n"
        f"Подписка истекает: {'✅' if settings_obj.notify_subscription_expiring else '❌'}\n"
        f"Платежи: {'✅' if settings_obj.notify_payment_success else '❌'}\n\n"
        "Изменить можно в веб-версии: Профиль → вкладка 'Уведомления'."
    )

    await update.message.reply_text(message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📚 **Доступные команды:**\n\n"
        "/start - Начать работу с ботом\n"
        "/reset - Сбросить пароль\n"
        "/profile - Показать профиль\n"
        "/unlink - Отвязать аккаунт\n"
        "/notifications - Показать настройки уведомлений\n"
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
    application.add_handler(CommandHandler("notifications", notifications_info))
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
