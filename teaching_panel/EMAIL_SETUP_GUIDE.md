# Настройка отправки Email на реальную почту

## Быстрая настройка для Gmail

### Шаг 1: Получите пароль приложения Google

1. Перейдите в настройки аккаунта Google: https://myaccount.google.com/
2. Выберите **Безопасность** → **Двухфакторная аутентификация** (включите если не включена)
3. Внизу найдите **Пароли приложений**: https://myaccount.google.com/apppasswords
4. Создайте новый пароль для приложения:
   - Выберите приложение: **Почта**
   - Выберите устройство: **Другое** (введите "Teaching Panel")
5. Скопируйте сгенерированный 16-значный пароль (вида `xxxx xxxx xxxx xxxx`)

### Шаг 2: Настройте переменные окружения

Создайте файл `.env` в папке `teaching_panel/`:

```env
# Email настройки (Gmail)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш_email@gmail.com
EMAIL_HOST_PASSWORD=ваш_пароль_приложения_16_символов
DEFAULT_FROM_EMAIL=ваш_email@gmail.com
```

**Пример:**
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=samovar1255@gmail.com
EMAIL_HOST_PASSWORD=abcd efgh ijkl mnop
DEFAULT_FROM_EMAIL=Teaching Panel <samovar1255@gmail.com>
```

### Шаг 3: Установите python-dotenv

```bash
pip install python-dotenv
```

### Шаг 4: Обновите settings.py

Откройте `teaching_panel/settings.py` и в самом начале файла (после импортов) добавьте:

```python
from dotenv import load_dotenv
load_dotenv()
```

### Шаг 5: Перезапустите Django сервер

```bash
# Остановите текущий сервер (Ctrl+C)
python manage.py runserver
```

## Альтернатива 1: Яндекс.Почта

Если используете Яндекс почту:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш_email@yandex.ru
EMAIL_HOST_PASSWORD=ваш_пароль
DEFAULT_FROM_EMAIL=ваш_email@yandex.ru
```

**Важно для Яндекс:**
1. Перейдите в настройки почты
2. Включите "Доступ по POP3/SMTP"
3. Создайте пароль приложения (аналогично Gmail)

## Альтернатива 2: Mail.ru

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mail.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш_email@mail.ru
EMAIL_HOST_PASSWORD=ваш_пароль
DEFAULT_FROM_EMAIL=ваш_email@mail.ru
```

## Проверка отправки

После настройки зарегистрируйте нового пользователя - код должен прийти на указанный email в течение нескольких секунд.

### Отладка проблем

Если письма не приходят, проверьте:

1. **Папку "Спам"** - первые письма могут попасть туда
2. **Консоль Django** - там будут ошибки если они есть
3. **Правильность пароля приложения** - скопирован полностью без пробелов
4. **Двухфакторная аутентификация включена** (для Gmail обязательно)

### Тестовая команда

Проверьте отправку напрямую из Django shell:

```bash
python manage.py shell
```

```python
from django.core.mail import send_mail

send_mail(
    'Test Email',
    'Это тестовое письмо от Teaching Panel',
    'your_email@gmail.com',  # От кого
    ['recipient@example.com'],  # Кому
    fail_silently=False,
)
```

Если команда выполнится без ошибок - настройка работает!

## Безопасность

⚠️ **ВАЖНО:**

1. **Никогда не коммитьте `.env` файл в Git!**
2. Добавьте `.env` в `.gitignore`:
   ```
   .env
   *.env
   ```

3. Для production используйте переменные окружения сервера, а не файл `.env`

## Что изменилось в коде

✅ Убрана 2-секундная задержка при переходе на страницу верификации
✅ Кнопки на странице верификации теперь используют фирменный дизайн (компонент Button)
✅ Текст кнопки "Подождите 61с" исправлен на корректный (показывает правильный таймер)
