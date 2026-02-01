# Ошибка: FieldError - Cannot resolve keyword 'is_active' into field

## Симптомы

В Sentry/логах появляется ошибка:
```
FieldError: Cannot resolve keyword 'is_active' into field. 
Choices are: ai_reports, attendance_alert_reads, behavior_reports, chats, 
control_points, created_at, description, homework_assignments, homeworks, id, 
invite_code, lessons, material_access, name, notification_mutes, recording_access, 
recurring_lessons, scheduled_messages, student_activity_logs, student_chat_analytics, 
student_questions, student_ratings, students, teacher, teacher_id, telegram_chat_id, 
updated_at
```

**Источник**: Celery task `accounts.tasks.send_top_rating_notifications`

## Причина

Код пытается фильтровать модель `Group` по полю `is_active`, которое **не существует** в этой модели:

```python
# ✗ НЕПРАВИЛЬНО - Group не имеет поля is_active
groups = Group.objects.filter(is_active=True).prefetch_related('students')
```

### Какие модели ИМЕЮТ поле `is_active`:

| Модель | Поле `is_active` | Примечание |
|--------|------------------|------------|
| `CustomUser` | ✓ Да | Наследуется от Django AbstractUser |
| `Group` | ✗ Нет | Группы всегда активны |
| `Lesson` | ✗ Нет | Используется `status` вместо этого |
| `Subscription` | ✗ Нет | Используется `status='active'` |

## Решение

### Для модели Group:

```python
# ✓ ПРАВИЛЬНО - получаем все группы
groups = Group.objects.all().prefetch_related('students')

# Или фильтруем по учителю
groups = Group.objects.filter(teacher=teacher)
```

### Для модели User:

```python
# ✓ ПРАВИЛЬНО - у CustomUser есть is_active
students = group.students.filter(is_active=True)
teachers = User.objects.filter(role='teacher', is_active=True)
```

## Исправленные файлы

- [accounts/tasks.py](../../teaching_panel/accounts/tasks.py) — строки 979, 1089:
  - `send_top_rating_notifications()` — исправлено
  - `send_season_top_rating_notifications()` — исправлено

## Профилактика

### 1. Проверка полей модели:

```python
# В Django shell
from schedule.models import Group
print([f.name for f in Group._meta.get_fields()])
```

### 2. Добавление поля is_active в Group (опционально):

Если нужна логика "архивирования" групп:

```python
# В schedule/models.py
class Group(models.Model):
    # ... существующие поля ...
    is_active = models.BooleanField(
        _('активна'),
        default=True,
        help_text=_('Неактивные группы не отображаются в списках')
    )
```

Затем:
```bash
python manage.py makemigrations schedule
python manage.py migrate
```

## Тестирование

```bash
# Проверить синтаксис
cd teaching_panel
python -c "from accounts.tasks import send_top_rating_notifications; print('OK')"

# Запустить задачу вручную (в Django shell)
from accounts.tasks import send_top_rating_notifications
result = send_top_rating_notifications()
print(result)
```

## FAQ

**Q: Почему ошибка происходит только сейчас?**
A: Задача `send_top_rating_notifications` запускается 1 числа каждого месяца. Ошибка была добавлена при рефакторинге и проявилась только в день выполнения.

**Q: Нужно ли перезапускать Celery?**
A: Да, после деплоя изменений:
```bash
sudo systemctl restart celery celery-beat
```

**Q: Как проверить, что исправление работает?**
A: Вызовите задачу вручную через Django shell или дождитесь следующего 1-го числа.
