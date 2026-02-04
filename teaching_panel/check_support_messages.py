#!/usr/bin/env python
"""
Скрипт для проверки и диагностики сообщений поддержки

Использование:
    python check_support_messages.py              # Показать последние тикеты
    python check_support_messages.py --stats      # Показать статистику
    python check_support_messages.py --users      # Показать пользователей с telegram_id
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Настройка Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.utils import timezone
from accounts.models import CustomUser
from support.models import SupportTicket, SupportMessage


def show_tickets(limit=20):
    """Показать последние тикеты"""
    tickets = SupportTicket.objects.all().order_by('-created_at')[:limit]
    
    if not tickets:
        print("Нет тикетов поддержки")
        return
    
    print(f"\n=== Последние {limit} тикетов ===\n")
    
    for ticket in tickets:
        user_info = f"{ticket.user.email if ticket.user else 'N/A'}"
        tg_id = ticket.user.telegram_id if ticket.user else None
        
        print(f"#{ticket.id} [{ticket.status}] {ticket.subject[:50]}")
        print(f"   Пользователь: {user_info} (TG: {tg_id})")
        print(f"   Категория: {ticket.category}, Приоритет: {ticket.priority}")
        print(f"   Создан: {ticket.created_at}")
        
        # Последние сообщения
        messages = ticket.messages.order_by('-created_at')[:3]
        for msg in messages:
            sender = "SUPPORT" if msg.is_staff_reply else "USER"
            print(f"   [{sender}] {msg.message[:60]}...")
        print()


def show_stats():
    """Показать статистику"""
    total = SupportTicket.objects.count()
    by_status = {
        'new': SupportTicket.objects.filter(status='new').count(),
        'in_progress': SupportTicket.objects.filter(status='in_progress').count(),
        'waiting_user': SupportTicket.objects.filter(status='waiting_user').count(),
        'resolved': SupportTicket.objects.filter(status='resolved').count(),
    }
    
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_tickets = SupportTicket.objects.filter(created_at__gte=today).count()
    
    total_messages = SupportMessage.objects.count()
    
    print("\n=== Статистика поддержки ===\n")
    print(f"Всего тикетов: {total}")
    print(f"  - Новых: {by_status['new']}")
    print(f"  - В работе: {by_status['in_progress']}")
    print(f"  - Ожидают ответа: {by_status['waiting_user']}")
    print(f"  - Решённых: {by_status['resolved']}")
    print(f"\nСоздано сегодня: {today_tickets}")
    print(f"Всего сообщений: {total_messages}")


def show_telegram_users():
    """Показать пользователей с telegram_id"""
    users = CustomUser.objects.filter(telegram_id__isnull=False).order_by('-id')[:30]
    
    print("\n=== Пользователи с Telegram ===\n")
    
    for user in users:
        verified = "✓" if user.telegram_verified else "✗"
        role = user.role if hasattr(user, 'role') else 'unknown'
        print(f"ID:{user.id} TG:{user.telegram_id} {verified} [{role}] {user.email}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Проверка сообщений поддержки')
    parser.add_argument('--stats', action='store_true', help='Показать статистику')
    parser.add_argument('--users', action='store_true', help='Показать пользователей с TG')
    parser.add_argument('--limit', type=int, default=20, help='Лимит тикетов')
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    elif args.users:
        show_telegram_users()
    else:
        show_tickets(args.limit)


if __name__ == '__main__':
    main()
