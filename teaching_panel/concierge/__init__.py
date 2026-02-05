"""
Lectio Concierge — AI-powered Support System

Гибридная система поддержки:
1. AI-агент отвечает на типовые вопросы (RAG по Knowledge Base)
2. Автоматические действия (проверка статусов, диагностика)
3. Эскалация к человеку через Telegram при необходимости
4. Real-time синхронизация Web <-> Telegram

Статус: В разработке (Stage)
"""

default_app_config = 'concierge.apps.ConciergeConfig'
