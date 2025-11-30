# 🚀 5-Дневный Спринт - Инструкции для AI Agent

**Дедлайн**: 5 декабря 2025  
**Текущий статус**: День 0 (30 ноября) - подготовка

---

## 📋 Быстрый Старт для Нового Чата

При открытии нового чата скажи:
> "Ознакомься с `SPRINT_INSTRUCTIONS.md` и `FINAL_TASKS_ROADMAP.md`. Продолжаем с [указать текущий день/задачу]"

---

## 🎯 План на 5 Дней

### День 1 (01.12) - Безопасность ДЗ
**Приоритет**: 🔴 КРИТИЧНО  
**Цель**: Ученики НЕ видят правильные ответы через DevTools

**Задачи**:
1. Создать `QuestionStudentSerializer` без поля `is_correct`
2. Создать `ChoiceStudentSerializer` без `is_correct`
3. Обновить `HomeworkViewSet` с permission-based сериализацией
4. Убрать все клиентские проверки правильности во frontend
5. Добавить rate limiting на submit endpoint
6. Тестирование: открыть DevTools → Network → проверить отсутствие `is_correct`

**Файлы**:
```
teaching_panel/homework/serializers.py
teaching_panel/homework/views.py
teaching_panel/homework/permissions.py
frontend/src/modules/homework-analytics/HomeworkStudent.js
frontend/src/modules/homework-analytics/HomeworkAnswering.js
```

**Критерий готовности**: В Network tab JSON ответов НЕТ `is_correct: true/false`

---

### День 2 (02.12) - Система Подписок
**Приоритет**: 🔴 КРИТИЧНО  
**Цель**: Учитель может оформить и оплатить подписку

**Задачи**:
1. Создать модели `Subscription` и `Payment` в `accounts/models.py`
2. Миграции: `python manage.py makemigrations && python manage.py migrate`
3. Установить ЮKassa SDK: `pip install yookassa`
4. Создать `accounts/payments.py` с функциями интеграции
5. Создать `SubscriptionViewSet` и `PaymentViewSet`
6. API endpoints:
   - `POST /api/subscriptions/create/`
   - `POST /api/subscriptions/cancel/`
   - `GET /api/subscriptions/my/`
   - `POST /api/payments/create/`
   - `POST /api/payments/webhook/` (для ЮKassa)
7. Frontend: `SubscriptionPage.js` + `PaymentModal.js`
8. Middleware для проверки активной подписки
9. Celery задачи:
   - `check_expiring_subscriptions` (ежедневно)
   - `process_expired_subscriptions` (каждый час)
10. Admin панель для управления подписками
11. Тестирование с тестовой картой ЮKassa

**Файлы**:
```
teaching_panel/accounts/models.py (добавить Subscription, Payment)
teaching_panel/accounts/payments.py (новый)
teaching_panel/accounts/serializers.py
teaching_panel/accounts/views.py
teaching_panel/accounts/middleware.py (новый)
teaching_panel/accounts/tasks.py (Celery)
teaching_panel/accounts/admin.py
frontend/src/components/SubscriptionPage.js (новый)
frontend/src/components/PaymentModal.js (новый)
```

**Настройки ЮKassa**:
```python
# settings.py
YOOKASSA_SHOP_ID = os.environ.get('YOOKASSA_SHOP_ID', 'your_shop_id')
YOOKASSA_SECRET_KEY = os.environ.get('YOOKASSA_SECRET_KEY', 'your_secret')
```

**Критерий готовности**: Можно оформить подписку → оплатить тестовой картой → webhook активирует подписку

---

### День 3 (03.12) - Telegram + ДЗ (параллельно)
**Приоритет**: 🟡 ВАЖНО  
**Цель**: Сброс пароля через бота + улучшение конструктора

#### 3.1 Сброс Пароля через Telegram

**Задачи**:
1. Добавить `telegram_verified` в модель `CustomUser`
2. Создать систему кодов привязки (генерация + проверка)
3. API endpoints:
   - `POST /api/accounts/generate-telegram-code/`
   - `POST /api/accounts/verify-telegram/`
4. Обновить `telegram_bot.py`:
   - Обработка `/start <code>` для привязки
   - Улучшить UI в боте
5. Frontend: UI привязки Telegram в профиле (с QR-кодом)
6. Тестирование полного флоу восстановления

**Файлы**:
```
teaching_panel/accounts/models.py (telegram_verified)
teaching_panel/accounts/views.py
teaching_panel/telegram_bot.py
frontend/src/components/ProfileSettings.js
```

#### 3.2 Обновление Конструктора ДЗ (упрощенная версия)

**Задачи**:
1. Добавить поля `allow_retries` и `max_retries` в модель `Homework`
2. API endpoint: `POST /api/homework/{id}/retry/`
3. Обновить дизайн `HomeworkConstructor.js` (использовать shared components)
4. Добавить кнопку "Попробовать еще раз" в `HomeworkStudent.js`
5. Кнопка "Редактировать ответ" если `status='in_progress'`
6. Простой preview режим перед публикацией ДЗ

**Файлы**:
```
teaching_panel/homework/models.py
teaching_panel/homework/views.py
frontend/src/modules/homework-analytics/HomeworkConstructor.js
frontend/src/modules/homework-analytics/HomeworkStudent.js
frontend/src/modules/homework-analytics/HomeworkAnswering.js
```

**Критерий готовности**: 
- Telegram привязка работает + сброс пароля через бота
- Ученик может повторно пройти ДЗ (если разрешено)

---

### День 4 (04.12) - Push-уведомления
**Приоритет**: 🟡 ВАЖНО  
**Цель**: Уведомления в Telegram работают

**Задачи**:
1. Создать модели `NotificationSettings` и `NotificationLog`
2. Миграции
3. Создать `accounts/notifications.py` с функцией `send_telegram_notification()`
4. Интегрировать отправку в триггерные точки:
   - `homework/views.py` → сдано ДЗ → уведомление учителю
   - `homework/views.py` → проверено ДЗ → уведомление ученику
   - `schedule/views.py` → начало занятия → уведомление ученикам (Celery)
   - `accounts/tasks.py` → истекает подписка → уведомление учителю
5. API endpoints:
   - `GET /api/notifications/settings/`
   - `PATCH /api/notifications/settings/`
6. Frontend: `NotificationSettings.js` с переключателями
7. Обновить `telegram_bot.py` для отправки уведомлений
8. Тестирование всех типов уведомлений

**Типы уведомлений**:
- **Учителю**: ДЗ сдано, ученик на занятии, истекает подписка, платеж успешен
- **Ученику**: ДЗ проверено, занятие через 30 мин, новое ДЗ, дедлайн ДЗ

**Файлы**:
```
teaching_panel/accounts/models.py (NotificationSettings, NotificationLog)
teaching_panel/accounts/notifications.py (новый)
teaching_panel/accounts/views.py
teaching_panel/homework/views.py (триггеры)
teaching_panel/schedule/views.py (триггеры)
teaching_panel/schedule/tasks.py (Celery)
teaching_panel/telegram_bot.py
frontend/src/components/NotificationSettings.js (новый)
```

**Критерий готовности**: Все типы уведомлений доходят в Telegram

---

### День 5 (05.12) - Тестирование + Запуск
**Приоритет**: 🔴 ДЕДЛАЙН  
**Цель**: Проверить критичные флоу → запустить

#### Утро: Ручное Тестирование

**Чек-лист**:
- [ ] Регистрация учителя → вход
- [ ] Оформление подписки → тестовая оплата
- [ ] Webhook ЮKassa активирует подписку
- [ ] Создание группы → добавление учеников
- [ ] Создание занятия → запуск Zoom
- [ ] Создание ДЗ (3 типа вопросов)
- [ ] Ученик НЕ видит ответы в DevTools ✅
- [ ] Сдача ДЗ → уведомление учителю
- [ ] Проверка ДЗ → уведомление ученику
- [ ] Повторная попытка ДЗ работает
- [ ] Привязка Telegram → сброс пароля через бота
- [ ] Настройки уведомлений сохраняются

**Если нашли баг**:
1. Оценить критичность (блокирующий/не блокирующий)
2. Зафиксировать в список
3. Исправить блокирующие немедленно
4. Не блокирующие → отложить на неделю 2

#### Вечер: Опционально - Домен/HTTPS

**Если успеем и выбрано название**:
- [ ] Купить домен
- [ ] Настроить DNS (A record → 72.56.81.163)
- [ ] Получить SSL: `sudo certbot --nginx -d domain.com`
- [ ] Обновить `settings.py`: `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`
- [ ] Обновить `.env` на сервере: `WEBAPP_URL`, `FRONTEND_URL`
- [ ] Проверить HTTPS работает

**Если не успели**: Отложить на следующую неделю, запускаемся на IP!

**🚀 ЗАПУСК К КОНЦУ ДНЯ**

---

## 🛠️ Технические Детали

### Структура Проекта
```
teaching_panel/
├── accounts/          # Пользователи, подписки, уведомления
├── schedule/          # Занятия, группы, Zoom
├── homework/          # ДЗ, вопросы, ответы
├── analytics/         # Статистика, прогресс
├── zoom_pool/         # Пул Zoom аккаунтов
└── telegram_bot.py    # Telegram бот

frontend/
├── src/
│   ├── apiService.js      # Axios client + JWT
│   ├── auth.js            # AuthContext
│   ├── components/        # Страницы
│   ├── modules/           # Модули (homework, zoom, etc)
│   └── shared/components/ # UI компоненты
```

### Команды Запуска (Windows PowerShell)

**Backend**:
```powershell
cd teaching_panel
..\venv\Scripts\Activate.ps1
python manage.py runserver
```

**Frontend**:
```powershell
cd frontend
npm start
```

**Celery Worker** (для уведомлений и задач):
```powershell
# Терминал 1: Redis (Docker)
docker run -d -p 6379:6379 redis

# Терминал 2: Celery Worker
cd teaching_panel
..\venv\Scripts\Activate.ps1
celery -A teaching_panel worker -l info --pool=solo

# Терминал 3: Celery Beat (планировщик)
cd teaching_panel
..\venv\Scripts\Activate.ps1
celery -A teaching_panel beat -l info
```

**Telegram Bot**:
```powershell
cd teaching_panel
..\venv\Scripts\Activate.ps1
# Установить переменные окружения
$env:TELEGRAM_BOT_TOKEN="your_bot_token"
$env:WEBAPP_URL="http://localhost:3000"
python telegram_bot.py
```

### Миграции БД
```powershell
cd teaching_panel
..\venv\Scripts\Activate.ps1
python manage.py makemigrations
python manage.py migrate
```

### Создание Superuser
```powershell
python manage.py createsuperuser
# Email: admin@test.com
# Password: admin123
# Role: admin
```

---

## 📚 Ключевые Файлы

### Backend
- `teaching_panel/teaching_panel/settings.py` - конфигурация, feature flags
- `teaching_panel/accounts/models.py` - User, Subscription, Payment, NotificationSettings
- `teaching_panel/homework/models.py` - Homework, Question, Answer
- `teaching_panel/schedule/models.py` - Lesson, Group
- `teaching_panel/telegram_bot.py` - Telegram бот

### Frontend
- `frontend/src/apiService.js` - HTTP клиент, JWT токены
- `frontend/src/auth.js` - AuthContext (login/logout)
- `frontend/src/App.js` - React Router routes
- `frontend/setupProxy.js` - Dev proxy /api → Django

---

## 🚨 Критичные Моменты

### Безопасность ДЗ (День 1)
**ВАЖНО**: Никогда не отправлять `is_correct` ученику!
```python
# ✅ ПРАВИЛЬНО (для ученика)
class ChoiceStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text']  # БЕЗ is_correct

# ❌ НЕПРАВИЛЬНО
class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = '__all__'  # включает is_correct - ученик увидит ответы!
```

### ЮKassa Webhook (День 2)
**ВАЖНО**: Webhook URL должен быть доступен из интернета
- Локально: используй ngrok (`ngrok http 8000`)
- На сервере: `https://your-server-ip/api/payments/webhook/`

**Проверка webhook**:
```python
# accounts/views.py
@api_view(['POST'])
@permission_classes([AllowAny])  # Webhook приходит без токена!
def payment_webhook(request):
    # Проверить подпись от ЮKassa
    # Обновить статус Payment
    # Активировать Subscription
    pass
```

### Celery Задачи (День 2, 4)
**ВАЖНО**: Redis ДОЛЖЕН быть запущен, иначе Celery не работает

**Проверка**:
```powershell
# Тест Redis
docker ps | Select-String redis
# Должен показать running контейнер

# Тест Celery
celery -A teaching_panel inspect active
# Должен показать активные задачи
```

### Telegram Bot (День 3, 4)
**ВАЖНО**: Получить `telegram_chat_id` при первом `/start`
```python
# telegram_bot.py
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    telegram_chat_id = str(update.effective_chat.id)  # ← СОХРАНИТЬ ЭТО!
    
    # Сохранить в БД при привязке
    user.telegram_chat_id = telegram_chat_id
    user.save()
```

---

## 🎯 Метрики Успеха

### К концу Дня 1:
- ✅ Нет `is_correct` в Network tab для ученика
- ✅ Учитель видит правильные ответы в конструкторе

### К концу Дня 2:
- ✅ Можно оформить подписку
- ✅ Тестовая оплата проходит
- ✅ Webhook активирует подписку
- ✅ Middleware блокирует неоплативших

### К концу Дня 3:
- ✅ Telegram привязка работает
- ✅ Сброс пароля через бота работает
- ✅ Ученик может повторно пройти ДЗ

### К концу Дня 4:
- ✅ Уведомления доходят в Telegram
- ✅ Настройки уведомлений работают

### К концу Дня 5:
- ✅ Все критичные флоу протестированы
- ✅ Нет блокирующих багов
- ✅ Система готова к запуску

---

## 🔄 Что Делать При Блокере

### Если застрял на задаче:
1. **Проверь логи**: Django terminal, Browser console, Celery logs
2. **Упрости scope**: может быть MVP версия?
3. **Спроси AI**: опиши проблему детально
4. **Skip и вернись**: если не критично, отложи на день 5

### Если нет времени:
**Можно отложить ПОСЛЕ 5 декабря**:
- Дерево прогресса учителя (nice to have)
- Дополнительные типы вопросов в ДЗ
- Домен + HTTPS (если не успели)
- Нагрузочное тестирование

**НЕЛЬЗЯ пропустить**:
- Безопасность ДЗ (иначе читеры)
- Подписки (иначе нет бизнеса)
- Базовое тестирование (иначе не знаем, работает ли)

---

## 📞 Контакты и Ресурсы

**Документация**:
- [ЮKassa API](https://yookassa.ru/developers/api)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery](https://docs.celeryproject.org/)

**Тестовые карты ЮKassa**:
- Успешная оплата: `5555 5555 5555 4477`, `12/24`, `123`
- Отклонение: `5555 5555 5555 4444`, `12/24`, `123`

**Полный план**: см. `FINAL_TASKS_ROADMAP.md`

---

**Последнее обновление**: 30 ноября 2025, 23:00  
**Следующий шаг**: День 1 (01.12) - Безопасность ДЗ 🛡️

**ПОЕХАЛИ! 🚀**
