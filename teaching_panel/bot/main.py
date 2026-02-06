"""
Главная точка входа модуля bot

Содержит функцию setup_bot() для интеграции с существующим telegram_bot.py
"""
import logging

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from .config import BOT_TOKEN
from .handlers import (
    start_command,
    menu_command,
    help_command,
    profile_command,
    callback_query_handler,
    # Teacher commands
    remind_lesson_start,
    remind_lesson_handle_text,
    check_hw_start,
    remind_hw_start,
    # Student commands
    my_lessons,
    today_lessons,
    my_homework,
    pending_homework,
    my_progress,
)

logger = logging.getLogger(__name__)


def setup_handlers(application: Application):
    """
    Регистрирует все обработчики команд.
    
    Вызывается из telegram_bot.py для добавления новых команд к боту.
    """
    # Базовые команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", profile_command))
    
    # Команды учителя
    application.add_handler(CommandHandler("remind_lesson", remind_lesson_start))
    application.add_handler(CommandHandler("remind_hw", remind_hw_start))
    application.add_handler(CommandHandler("check_hw", check_hw_start))
    
    # Команды ученика
    application.add_handler(CommandHandler("lessons", my_lessons))
    application.add_handler(CommandHandler("today", today_lessons))
    application.add_handler(CommandHandler("homework", my_homework))
    application.add_handler(CommandHandler("pending", pending_homework))
    application.add_handler(CommandHandler("progress", my_progress))
    
    # Универсальный обработчик callback'ов
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Обработчик текстовых сообщений для wizard'ов
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_message_handler,
        )
    )
    
    # Глобальный обработчик ошибок — бот не падает молча
    application.add_error_handler(error_handler)
    
    logger.info("Bot handlers registered successfully")


async def error_handler(update, context):
    """
    Глобальный обработчик ошибок бота.
    Логирует ошибку и уведомляет пользователя вместо молчаливого падения.
    """
    logger.error(f"Bot error: {context.error}", exc_info=context.error)
    
    try:
        if update and update.callback_query:
            await update.callback_query.answer(
                "Произошла ошибка. Попробуйте /menu.",
                show_alert=True,
            )
        elif update and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка. Попробуйте позже или используйте /menu."
            )
    except Exception:
        pass  # Не можем уведомить — хотя бы залогировали


async def text_message_handler(update, context):
    """
    Роутер для текстовых сообщений.
    Проверяет состояние диалога и направляет к нужному обработчику.
    """
    from .handlers import remind_lesson_handle_text
    
    # Пробуем обработать как часть wizard'а напоминания об уроке
    handled = await remind_lesson_handle_text(update, context)
    if handled:
        return
    
    # Другие wizard'ы можно добавить здесь
    
    # Если никакой wizard не активен - просто игнорируем или показываем меню
    # await update.message.reply_text(
    #     "Используйте /menu для навигации.",
    # )


def create_application() -> Application:
    """
    Создаёт новый экземпляр Application с настроенными обработчиками.
    
    Используется для standalone запуска бота.
    """
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не настроен в settings.py или .env")
    
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    
    return application


async def run_bot():
    """
    Запускает бота в режиме polling.
    
    Используется для standalone запуска:
        python -m bot.main
    """
    application = create_application()
    
    logger.info("Starting bot in polling mode...")
    await application.run_polling(drop_pending_updates=True)
