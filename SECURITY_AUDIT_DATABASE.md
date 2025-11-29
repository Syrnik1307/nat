# 🔒 ОТЧЁТ ПО БЕЗОПАСНОСТИ Teaching Panel

**Дата**: 29 ноября 2025  
**Аудит**: Полная проверка системы безопасности и БД

---

## ❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### 1. Отсутствие резервного копирования БД
**Риск**: Потеря всех данных при сбое диска/системы

**Решение**:
- ✅ Создан скрипт `backup_db.sh` - автоматическое резервное копирование
- ✅ Создан скрипт `restore_db.sh` - восстановление из бэкапа
- 📋 TODO: Настроить cron для ежедневного бэкапа в 3:00

### 2. Неправильные права на БД
**Текущее**: `root:root 644`  
**Проблема**: Django работает от `www-data`, возможны конфликты записи

**Решение**:
```bash
chown www-data:www-data /var/www/teaching_panel/teaching_panel/db.sqlite3
chmod 664 /var/www/teaching_panel/teaching_panel/db.sqlite3
```

### 3. Слетание ролей пользователей
**Причина**: JWT токен перезаписывает роль для superuser

**Проблема в коде** (`accounts/serializers.py:14`):
```python
effective_role = 'admin' if getattr(user, 'is_superuser', False) else user.role
```

**Решение**: Роль должна храниться ТОЛЬКО в БД, токен просто её передаёт

---

## 🛡️ ПЛАН ЗАЩИТЫ ОТ УДАЛЕНИЯ БД

### Уровень 1: Автоматические бэкапы
```bash
# Установка cron задачи
0 3 * * * /var/www/teaching_panel/teaching_panel/backup_db.sh
```
- Ежедневно в 3:00 ночи
- Хранение 30 дней
- Сжатие gzip
- Проверка целостности

### Уровень 2: Права доступа
```bash
# Только www-data может писать в БД
chown www-data:www-data db.sqlite3
chmod 664 db.sqlite3

# Директория с правами
chown www-data:www-data /var/www/teaching_panel/teaching_panel/
chmod 775 /var/www/teaching_panel/teaching_panel/
```

### Уровень 3: Аудит изменений
**Django Admin**:
- Включить `django-simple-history` для отслеживания изменений
- Логирование всех действий с моделью User

**Настройка логов**:
```python
LOGGING = {
    'handlers': {
        'db_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/teaching_panel/db_operations.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'django.db': {
            'handlers': ['db_file'],
            'level': 'INFO',
        },
    },
}
```

### Уровень 4: READ-ONLY режим (аварийный)
В критической ситуации:
```bash
# Сделать БД read-only
chmod 444 db.sqlite3

# Django будет работать, но без записи
# Восстановление: chmod 664 db.sqlite3
```

---

## 🔧 ИСПРАВЛЕНИЯ КОДА

### 1. Фикс JWT роли
**Файл**: `teaching_panel/accounts/serializers.py`

**Было**:
```python
effective_role = 'admin' if getattr(user, 'is_superuser', False) else user.role
token['role'] = effective_role
```

**Должно быть**:
```python
# Роль берем ТОЛЬКО из БД, не переопределяем
token['role'] = user.role
token['is_superuser'] = getattr(user, 'is_superuser', False)
token['email'] = user.email
```

### 2. Миграция для индекса на role
**Файл**: `teaching_panel/accounts/migrations/0XXX_add_role_index.py`

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),  # Замените на последнюю миграцию
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                max_length=20,
                choices=[('student', 'Ученик'), ('teacher', 'Учитель'), ('admin', 'Администратор')],
                db_index=True,  # Индекс для быстрого поиска
            ),
        ),
    ]
```

### 3. Защита от случайного изменения роли в Admin
**Файл**: `teaching_panel/accounts/admin.py`

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser

class CustomUserAdmin(BaseUserAdmin):
    # Логирование изменений роли
    def save_model(self, request, obj, form, change):
        if change and 'role' in form.changed_data:
            old_role = CustomUser.objects.get(pk=obj.pk).role
            # Логируем изменение
            import logging
            logger = logging.getLogger('django.db')
            logger.warning(
                f"ROLE CHANGE: User {obj.email} (ID:{obj.id}) "
                f"role changed from '{old_role}' to '{obj.role}' "
                f"by {request.user.email}"
            )
        super().save_model(request, obj, form, change)
    
    # Только superuser может менять роли
    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser and obj:
            return ['role'] + list(super().get_readonly_fields(request, obj))
        return super().get_readonly_fields(request, obj)

admin.site.unregister(CustomUser)
admin.site.register(CustomUser, CustomUserAdmin)
```

---

## 📋 ЧЕКЛИСТ ВНЕДРЕНИЯ

### Немедленно (сейчас):
- [ ] Исправить права на БД: `chown www-data:www-data db.sqlite3`
- [ ] Создать директорию бэкапов: `mkdir -p /var/backups/teaching_panel`
- [ ] Скопировать скрипты на сервер
- [ ] Сделать первый ручной бэкап
- [ ] Исправить JWT serializer (роль из БД)

### Сегодня:
- [ ] Настроить cron для автобэкапов
- [ ] Добавить миграцию с индексом на role
- [ ] Обновить Django Admin с логированием
- [ ] Протестировать восстановление из бэкапа

### На неделе:
- [ ] Установить `django-simple-history`
- [ ] Настроить ротацию логов
- [ ] Добавить мониторинг размера БД
- [ ] Настроить alerts на критические операции

### Долгосрочно:
- [ ] Миграция на PostgreSQL (для production)
- [ ] Настроить репликацию БД
- [ ] Внедрить централизованное логирование (ELK)

---

## 🚨 ПРОЦЕДУРЫ АВАРИЙНОГО ВОССТАНОВЛЕНИЯ

### Если БД удалена/повреждена:
```bash
# 1. Остановить Django
sudo systemctl stop teaching_panel

# 2. Восстановить из последнего бэкапа
sudo /var/www/teaching_panel/teaching_panel/restore_db.sh

# 3. Проверить целостность
sqlite3 /var/www/teaching_panel/teaching_panel/db.sqlite3 "PRAGMA integrity_check;"

# 4. Запустить Django
sudo systemctl start teaching_panel
```

### Если роли слетели массово:
```bash
# 1. Подключиться к Django shell
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell

# 2. Восстановить роли из бэкапа (Python)
from accounts.models import CustomUser
import sqlite3

# Подключаемся к бэкапу
backup_conn = sqlite3.connect('/var/backups/teaching_panel/db_backup_YYYYMMDD_HHMMSS.sqlite3')
backup_cursor = backup_conn.cursor()

# Восстанавливаем роли
backup_cursor.execute("SELECT id, role FROM accounts_customuser")
for user_id, role in backup_cursor.fetchall():
    user = CustomUser.objects.filter(id=user_id).first()
    if user and user.role != role:
        print(f"Fixing: {user.email} {user.role} -> {role}")
        user.role = role
        user.save()

backup_conn.close()
```

---

## 📊 МОНИТОРИНГ

### Ключевые метрики:
- Размер БД (мониторинг роста)
- Количество успешных бэкапов за 7 дней
- Изменения ролей пользователей (alert при > 5/день)
- Ошибки записи в БД

### Команды проверки:
```bash
# Размер БД
du -h /var/www/teaching_panel/teaching_panel/db.sqlite3

# Последний бэкап
ls -lht /var/backups/teaching_panel/ | head -3

# Логи изменений ролей
grep "ROLE CHANGE" /var/log/teaching_panel/db_operations.log

# Целостность БД
sqlite3 /var/www/teaching_panel/teaching_panel/db.sqlite3 "PRAGMA integrity_check;"
```

---

**Статус**: 🔴 ТРЕБУЕТСЯ НЕМЕДЛЕННОЕ ДЕЙСТВИЕ  
**Приоритет**: КРИТИЧЕСКИЙ  
**Ответственный**: DevOps + Backend Team
