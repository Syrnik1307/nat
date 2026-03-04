# FieldError: Group.is_active не существует

- **Дата**: 2026-01
- **Severity**: HIGH
- **Компонент**: accounts/tasks.py (Celery task)
- **Источник**: @backend-api

## Симптомы
```
FieldError: Cannot resolve keyword 'is_active' into field.
```
Проявлялась 1-го числа каждого месяца (когда запускалась задача send_top_rating_notifications).

## Причина
Код фильтрует `Group.objects.filter(is_active=True)`, но у модели `Group` нет поля `is_active`.
Поле `is_active` есть у `CustomUser` (от AbstractUser), но НЕ у Group, Lesson, Subscription.

## Решение
```python
# НЕПРАВИЛЬНО
groups = Group.objects.filter(is_active=True)

# ПРАВИЛЬНО
groups = Group.objects.all().prefetch_related('students')
# Или
groups = Group.objects.filter(teacher=teacher)
```
Исправлено в `accounts/tasks.py` — строки 979, 1089.

## Урок
Всегда проверять наличие поля в модели перед фильтрацией. Использовать `Model._meta.get_fields()` при сомнениях.
