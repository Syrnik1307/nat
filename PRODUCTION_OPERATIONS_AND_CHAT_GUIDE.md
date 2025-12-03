# Production Operations & Chat Integration Guide

Дата: 4 декабря 2025 г.
Автор: GitHub Copilot (GPT-5)
Статус: Актуальная единая инструкция для продакшна и чата

---

## Цели
- Однозначная, краткая и точная инструкция по работе с сервером.
- Пошаговое подключение нового чат-модуля без двусмысленностей.
- Минимум лишней информации, только проверенные команды и порядок.

---

## Сервер и доступ
- SSH алиас: `tp`
- Хост: `72.56.81.163`
- Аутентификация: ключ `id_ed25519` (уже настроен в `~/.ssh/config`)
- Рабочая директория проекта на сервере: `/var/www/teaching_panel/`
- Сервисы: `teaching_panel` (Gunicorn/Django), `nginx`, `redis-server`, `celery`, `celery-beat`

### Как подключаюсь и работаю
1. Подключение по SSH:
```bash
ssh tp
```
2. Обновление кода и зависимостей:
```bash
cd /var/www/teaching_panel
sudo -u www-data git pull origin main
cd teaching_panel
source ../venv/bin/activate
pip install -r requirements.txt --quiet
```
3. Миграции и статика:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```
4. Перезапуск сервисов:
```bash
sudo systemctl restart teaching_panel
sudo systemctl restart nginx
# при необходимости:
sudo systemctl restart redis-server celery celery-beat
```
5. Быстрые проверки:
```bash
sudo systemctl is-active teaching_panel nginx redis-server
curl -s -o /dev/null -w 'Homepage: %{http_code} (%{time_total}s)\n' http://127.0.0.1/
curl -s -o /dev/null -w 'API /me/: %{http_code} (%{time_total}s)\n' \
  -H 'Authorization: Bearer fake' http://127.0.0.1/api/me/
```

### Логи
```bash
# Django / Gunicorn
sudo journalctl -u teaching_panel -f

# Nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Celery
sudo journalctl -u celery -f
sudo journalctl -u celery-beat -f
```

### Безопасность (production)
Обязательно включить после первичного запуска:
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- Настроить HTTPS в nginx (Let's Encrypt) и редирект HTTP→HTTPS
- Установить реальные reCAPTCHA ключи

---

## Подключение и тестирование нового Чата

Цель: чёткие шаги, чтобы включить и проверить чат-модуль в продакшне.

### 1. Backend API (Django)
- Маршруты чата должны быть доступны под `/api/chats/*` и `/api/messages/*`.
- Авторизация: JWT `Authorization: Bearer <access>`.
- Базовые вызовы:
```bash
# Список чатов пользователя
curl -H "Authorization: Bearer <token>" http://72.56.81.163/api/chats/

# Сообщения в чате
curl -H "Authorization: Bearer <token>" \
  "http://72.56.81.163/api/messages/?chat_id=<CHAT_ID>"

# Создать приватный чат
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"user_id": <USER_ID>}' http://72.56.81.163/api/chats/create_private/

# Отправить сообщение
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"chat": <CHAT_ID>, "text": "Привет"}' http://72.56.81.163/api/messages/

# Отметить чат как прочитанный
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"chat_id": <CHAT_ID>}' http://72.56.81.163/api/messages/mark_chat_as_read/
```

### 2. Frontend (React)
- Использовать `apiService.js` для всех HTTP-запросов (авто-добавление JWT, рефреш токенов).
- Основные страницы/компоненты:
  - `ChatList` — список чатов, автоподгрузка каждые 10 секунд.
  - `ChatThread` — лента сообщений, автоподгрузка каждые 3 секунды, отметка прочтения.
  - `GroupChatModal` — создание групповых чатов: выбор группы или произвольного набора пользователей.
- Роутинг:
  - Путь: `/chat`
  - Обёртка: `<Protected allowRoles={["teacher","student"]}>`

Минимальный чек-лист фронтенда:
- Логин: токены в `localStorage` (`tp_access_token`, `tp_refresh_token`).
- Открытие `/chat`: видны чаты пользователя.
- Создание приватного чата: поиск пользователя → создать → открыт новый чат.
- Отправка сообщений: форма ввода + отправка по Enter.
- Маркировка прочитанного: при открытии треда.
- Мобильная адаптация: ширина <768px — переключение на мобильный режим.

### 3. Права и роли
- Доступ к `/chat` только для ролей `teacher` и `student`.
- Админ доступ может быть включён при необходимости через Protected.

### 4. Тестовый сценарий (однозначный)
1. Залогиниться под Teacher.
2. Открыть `/chat`.
3. Вкладка Search → найти студента → нажать "Написать" → создаётся приватный чат.
4. Отправить сообщение "Привет".
5. Переключиться на Student → залогиниться.
6. Открыть `/chat` → увидеть новый чат и сообщение.
7. Ответить сообщением, убедиться в обновлении у Teacher.
8. Проверить, что `mark_chat_as_read` вызывается при открытии треда.

### 5. Нагрузочные/стабильность
- Интервалы обновления: 3–10 секунд (баланс между свежестью и нагрузкой).
- Логи мониторить при піках: `journalctl -u teaching_panel -f`.

---

## Частые команды (шпаргалка)
```bash
# Обновление и перезапуск (полный цикл)
ssh tp \
  "cd /var/www/teaching_panel && sudo -u www-data git pull origin main && \
   cd teaching_panel && source ../venv/bin/activate && \
   pip install -r requirements.txt --quiet && \
   python manage.py migrate && python manage.py collectstatic --noinput && \
   sudo systemctl restart teaching_panel nginx"

# Smoke-тесты
ssh tp "curl -s -o /dev/null -w 'Home: %{http_code} (%{time_total}s)\n' http://127.0.0.1/"
ssh tp "curl -s -o /dev/null -w 'API /me/: %{http_code} (%{time_total}s)\n' -H 'Authorization: Bearer fake' http://127.0.0.1/api/me/"
```

---

## Резюме
Эта инструкция фиксирует реальный порядок работы на продакшн-сервере и чёткие шаги для подключения и тестирования чат-модуля. Следуя ей последовательно, новый инженер сможет без двусмысленностей поднять и проверить чат.
