"""
Telegram Bot Command Center

Модуль для управления командами Telegram бота.
Предоставляет учителям и ученикам интерактивные команды для:
- Напоминаний об уроках и ДЗ
- Проверки сдачи домашних заданий
- Отложенных рассылок
- Просмотра расписания и прогресса

Интеграция с существующим telegram_bot.py:
    from bot.main import setup_handlers
    setup_handlers(application)
"""

default_app_config = 'bot.apps.BotConfig'