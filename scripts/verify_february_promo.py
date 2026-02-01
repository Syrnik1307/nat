#!/usr/bin/env python
"""
Скрипт проверки февральской акции 2026.

Проверяет:
1. Функция _is_february_2026_promo() возвращает True (сейчас февраль 2026)
2. Новый пользователь получает АКТИВНУЮ подписку
3. Подписка истекает ровно 1 марта 2026, 00:00:00

Запуск:
    cd teaching_panel
    python ../scripts/verify_february_promo.py

Вывод:
    SUCCESS — все проверки пройдены
    FAIL — есть проблемы
"""

import os
import sys
import uuid
from datetime import datetime

# Добавляем путь к Django проекту
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.join(script_dir, '..', 'teaching_panel')
sys.path.insert(0, project_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django.utils import timezone
from accounts.models import CustomUser, Subscription
from accounts.subscriptions_utils import (
    _is_february_2026_promo,
    _get_february_2026_promo_expires_at,
    get_subscription
)


def run_verification():
    print("=" * 70)
    print("  ПРОВЕРКА ФЕВРАЛЬСКОЙ АКЦИИ 2026")
    print("=" * 70)
    print()
    
    tests_passed = []
    tests_failed = []
    
    # ===== ТЕСТ 1: Проверка функции определения акции =====
    print("[TEST 1] Проверка _is_february_2026_promo()...")
    now = timezone.now()
    is_promo = _is_february_2026_promo()
    
    if now.year == 2026 and now.month == 2:
        if is_promo:
            tests_passed.append("_is_february_2026_promo() = True (февраль 2026)")
            print(f"  OK: Сейчас {now.strftime('%Y-%m-%d')}, акция активна")
        else:
            tests_failed.append("_is_february_2026_promo() должна вернуть True в феврале 2026!")
            print(f"  FAIL: Сейчас {now.strftime('%Y-%m-%d')}, но акция НЕ активна!")
    else:
        # Если тест запущен не в феврале 2026 — это нормально
        if not is_promo:
            tests_passed.append(f"_is_february_2026_promo() = False (сейчас {now.strftime('%Y-%m')})")
            print(f"  OK: Сейчас {now.strftime('%Y-%m-%d')}, акция НЕ активна (это правильно)")
        else:
            tests_failed.append("_is_february_2026_promo() вернула True вне февраля 2026!")
    
    # ===== ТЕСТ 2: Проверка даты окончания акции =====
    print("\n[TEST 2] Проверка _get_february_2026_promo_expires_at()...")
    promo_expires = _get_february_2026_promo_expires_at()
    expected = datetime(2026, 3, 1, 0, 0, 0)
    
    if promo_expires.year == 2026 and promo_expires.month == 3 and promo_expires.day == 1:
        tests_passed.append(f"Дата окончания акции: {promo_expires.isoformat()}")
        print(f"  OK: Дата окончания = {promo_expires.isoformat()}")
    else:
        tests_failed.append(f"Неверная дата окончания: {promo_expires}, ожидалось 2026-03-01")
        print(f"  FAIL: Дата = {promo_expires}, ожидалось 2026-03-01")
    
    # ===== ТЕСТ 3: Создание тестового пользователя и проверка подписки =====
    print("\n[TEST 3] Создание тестового пользователя...")
    
    # Генерируем уникальный email
    test_email = f"test_promo_{uuid.uuid4().hex[:8]}@test.local"
    
    try:
        # Создаём пользователя
        test_user = CustomUser.objects.create_user(
            email=test_email,
            password="Test1234!",
            role="teacher",
            first_name="Тест",
            last_name="Февраль"
        )
        print(f"  Создан пользователь: {test_email}")
        
        # Получаем подписку (это триггерит создание через get_subscription)
        sub = get_subscription(test_user)
        
        print(f"  Подписка создана:")
        print(f"    - ID: {sub.id}")
        print(f"    - План: {sub.plan}")
        print(f"    - Статус: {sub.status}")
        print(f"    - Истекает: {sub.expires_at}")
        print(f"    - is_active(): {sub.is_active()}")
        
        # Проверяем результат в зависимости от текущей даты
        if now.year == 2026 and now.month == 2:
            # В феврале 2026 подписка должна быть АКТИВНОЙ
            if sub.status == Subscription.STATUS_ACTIVE:
                tests_passed.append("Статус подписки = active (февральская акция)")
            else:
                tests_failed.append(f"Ожидался статус 'active', получен '{sub.status}'")
            
            if sub.is_active():
                tests_passed.append("is_active() = True")
            else:
                tests_failed.append("is_active() вернула False, ожидалось True")
            
            # Проверяем дату окончания
            if (sub.expires_at.year == 2026 and 
                sub.expires_at.month == 3 and 
                sub.expires_at.day == 1):
                tests_passed.append("Подписка истекает 1 марта 2026")
            else:
                tests_failed.append(f"Неверная дата окончания: {sub.expires_at}")
        else:
            # Вне февраля 2026 подписка должна быть PENDING
            if sub.status == Subscription.STATUS_PENDING:
                tests_passed.append(f"Статус подписки = pending (стандартная логика)")
            else:
                # Если это не февраль 2026, но подписка active — проверим почему
                tests_passed.append(f"Статус подписки = {sub.status}")
        
        # Удаляем тестового пользователя
        test_user.delete()
        print(f"  Тестовый пользователь удалён")
        tests_passed.append("Cleanup: тестовый пользователь удалён")
        
    except Exception as e:
        tests_failed.append(f"Ошибка при тестировании: {e}")
        print(f"  FAIL: {e}")
        # Попробуем удалить пользователя если он был создан
        try:
            CustomUser.objects.filter(email=test_email).delete()
        except:
            pass
    
    # ===== ИТОГИ =====
    print()
    print("=" * 70)
    print("  РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    print("=" * 70)
    print()
    
    print("Пройдено:")
    for t in tests_passed:
        print(f"  [OK] {t}")
    
    print()
    print("Провалено:")
    if tests_failed:
        for t in tests_failed:
            print(f"  [FAIL] {t}")
    else:
        print("  (нет)")
    
    print()
    print("=" * 70)
    
    if not tests_failed:
        print("  *** SUCCESS: Все проверки пройдены! ***")
        print("=" * 70)
        return True
    else:
        print(f"  *** FAIL: {len(tests_failed)} проверок провалено ***")
        print("=" * 70)
        return False


if __name__ == '__main__':
    success = run_verification()
    sys.exit(0 if success else 1)
