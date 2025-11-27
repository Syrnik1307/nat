# 🚀 Быстрый старт: Система квот хранилища

## 1. Обновление backend на сервере

```bash
ssh root@72.56.81.163

cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

# Получить изменения
git pull origin main

# Создать миграцию
python manage.py makemigrations schedule

# Применить миграцию
python manage.py migrate

# Перезапустить сервисы
sudo systemctl restart teaching_panel
sudo systemctl restart celery-worker

# Проверить статус
sudo systemctl status teaching_panel
sudo systemctl status celery-worker
```

## 2. Создание квот для существующих преподавателей

```bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell
```

```python
from accounts.models import CustomUser
from schedule.models import TeacherStorageQuota

# Создать квоты для всех преподавателей (5 ГБ каждому)
teachers = CustomUser.objects.filter(role='teacher')
for teacher in teachers:
    quota, created = TeacherStorageQuota.objects.get_or_create(
        teacher=teacher,
        defaults={'total_quota_bytes': 5 * 1024 ** 3}
    )
    if created:
        print(f"✅ Создана квота для {teacher.email}: 5 ГБ")
    else:
        print(f"⏭️  Квота для {teacher.email} уже существует: {quota.total_gb:.2f} ГБ")

exit()
```

## 3. Обновление frontend

```bash
cd /var/www/teaching_panel/teaching_panel/frontend

# Если нужно пересобрать frontend локально, иначе пропустите
# npm run build

# Если собрали локально, скопируйте build на сервер:
# scp -r build/* root@72.56.81.163:/var/www/teaching_panel/teaching_panel/frontend/build/

# Перезапустить Nginx (если нужно)
sudo systemctl restart nginx
```

## 4. Проверка работы

### Проверка API

```bash
# Получить токен админа
curl -X POST http://72.56.81.163/accounts/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your_password"}'

# Получить статистику хранилища
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://72.56.81.163/schedule/api/storage/statistics/

# Получить список квот
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://72.56.81.163/schedule/api/storage/quotas/
```

### Проверка UI

1. Войдите как админ
2. Откройте http://72.56.81.163/admin
3. Нажмите "💾 Управление хранилищем"
4. Проверьте:
   - Отображение статистики
   - Список квот преподавателей
   - Кнопка увеличения квоты

## 5. Тестирование системы

### Проверка автоматического создания квоты

1. Создайте нового преподавателя через админку
2. Создайте урок и включите запись
3. Проведите урок с записью
4. После обработки webhook проверьте:
   ```python
   python manage.py shell
   
   from schedule.models import TeacherStorageQuota
   from accounts.models import CustomUser
   
   teacher = CustomUser.objects.get(email='new_teacher@example.com')
   quota = teacher.storage_quota
   print(f"Квота: {quota.total_gb} ГБ")
   print(f"Использовано: {quota.used_gb} ГБ")
   print(f"Записей: {quota.recordings_count}")
   ```

### Проверка блокировки при превышении квоты

```python
python manage.py shell

from schedule.models import TeacherStorageQuota

# Установить маленькую квоту для теста
quota = TeacherStorageQuota.objects.get(id=1)
quota.total_quota_bytes = 100 * 1024 * 1024  # 100 МБ
quota.save()

# Попробуйте загрузить запись (автоматически через webhook)
# Запись должна получить status='failed'
```

### Проверка увеличения квоты

1. Откройте /admin/storage
2. Найдите преподавателя
3. Нажмите "➕" рядом с его квотой
4. Добавьте 10 ГБ
5. Проверьте обновление в таблице

## 6. Мониторинг

### Логи Celery

```bash
# Смотреть логи обработки записей
sudo tail -f /var/log/celery/celery-worker.service.log

# Фильтр по квотам
sudo tail -f /var/log/celery/celery-worker.service.log | grep -i quota
```

### Проверка превышений квот

```python
python manage.py shell

from schedule.models import TeacherStorageQuota

# Преподаватели с превышением
exceeded = TeacherStorageQuota.objects.filter(quota_exceeded=True)
print(f"Превышений квоты: {exceeded.count()}")

# Преподаватели с предупреждениями (>80%)
warnings = TeacherStorageQuota.objects.filter(warning_sent=True)
print(f"Предупреждений: {warnings.count()}")

# Самые большие пользователи
top_users = TeacherStorageQuota.objects.order_by('-used_bytes')[:5]
for quota in top_users:
    print(f"{quota.teacher.email}: {quota.used_gb:.2f} ГБ ({quota.usage_percent:.1f}%)")
```

## 7. Готово! ✅

Система квот полностью работает:

- ✅ Автоматическое создание квот для новых преподавателей
- ✅ Проверка квоты перед загрузкой записи
- ✅ Блокировка при превышении лимита
- ✅ Админ панель для управления
- ✅ Увеличение квот через UI
- ✅ Автоматическое освобождение при удалении записей

## 8. Команды для управления

### Django shell команды

```python
# Увеличить квоту преподавателю на 10 ГБ
from schedule.models import TeacherStorageQuota
quota = TeacherStorageQuota.objects.get(teacher_id=5)
quota.increase_quota(10)

# Сбросить предупреждения
quota.warning_sent = False
quota.save()

# Пересчитать использование (если данные рассинхронизированы)
from schedule.models import LessonRecording
recordings = LessonRecording.objects.filter(
    lesson__group__teacher=quota.teacher,
    status='ready'
)
total_size = sum([r.file_size or 0 for r in recordings])
quota.used_bytes = total_size
quota.recordings_count = recordings.count()
quota.save()
```

## 9. Troubleshooting

### Проблема: Квота не обновляется после загрузки записи

```bash
# Проверить логи Celery
sudo tail -100 /var/log/celery/celery-worker.service.log | grep -i "quota\|recording"

# Проверить статус задачи
python manage.py shell
from schedule.models import LessonRecording
rec = LessonRecording.objects.latest('id')
print(f"Status: {rec.status}")
print(f"File size: {rec.file_size}")
```

### Проблема: API возвращает 403 Forbidden

- Убедитесь, что пользователь имеет роль `admin`
- Проверьте токен авторизации
- Проверьте логи Django

### Проблема: Frontend не показывает страницу

- Проверьте сборку: `npm run build`
- Проверьте маршрут в App.js
- Проверьте консоль браузера (F12)

## 10. Полезные ссылки

- **Админ панель квот:** http://72.56.81.163/admin/storage
- **Django Admin:** http://72.56.81.163/admin
- **API документация:** См. `STORAGE_QUOTA_SYSTEM.md`
