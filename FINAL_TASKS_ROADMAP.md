# 🎯 План Закрытия Финальных Задач Teaching Panel

**Дата создания**: 30 ноября 2025  
**Статус**: Готов к реализации  
**Приоритет**: Критический для запуска

---

## 📋 Общая Сводка Задач

### Критически важные (Must Have)
1. ✅ **Система подписок и оплаты** - монетизация продукта
2. ✅ **Безопасность домашних заданий** - защита от читеров
3. ✅ **Сброс пароля через Telegram** - улучшение UX

### Высокий приоритет (Should Have)
4. ✅ **Push-уведомления в Telegram** - вовлечение пользователей
5. ✅ **Обновление конструктора ДЗ** - core функционал
6. ✅ **Нагрузочное тестирование** - стабильность

### Средний приоритет (Nice to Have)
7. ✅ **Доработка дерева прогресса учителя** - аналитика
8. ✅ **Домен + HTTPS** - профессиональный вид

---

## 🗺️ Roadmap с Правильной Последовательностью

**КРИТИЧНО**: Дедлайн - 5 декабря 2025 (осталось 5 дней!)

### 🔵 Этап 1: Безопасность и Core (1 декабря)
**Цель**: Закрыть критичные дыры в безопасности

#### 1.1 Безопасность Домашних Заданий (День 1 - ПРИОРИТЕТ #1)
**Почему первым**: Ученики могут читерить ПРЯМО СЕЙЧАС

**Задачи**:
- [ ] Купить домен (например: `teachingpanel.com`)
- [ ] Настроить DNS записи (A/AAAA на 72.56.81.163)
- [ ] Получить SSL сертификат (Let's Encrypt через Certbot)
- [ ] Обновить nginx конфигурацию для HTTPS
- [ ] Обновить CORS/ALLOWED_HOSTS в Django settings
- [ ] Обновить переменные окружения (WEBAPP_URL, FRONTEND_URL)
- [ ] Проверить работу всех API через HTTPS

**Файлы для изменения**:
```
teaching_panel/teaching_panel/settings.py
nginx_teaching_panel.conf
frontend/src/apiService.js (обновить baseURL если нужно)
.env (на сервере)
```

**Команды**:
```bash
# На сервере
sudo certbot --nginx -d teachingpanel.com -d www.teachingpanel.com
sudo systemctl restart nginx
```

**Критерии готовности**:

**Проблема**: Ученик может открыть DevTools → Network/Sources и увидеть правильные ответы из JSON

**Решение**:
1. **Backend**: Никогда не отправлять `is_correct` и правильные ответы ученику
2. **Frontend**: Убрать client-side валидацию ответов
3. **API**: Разделить эндпоинты для учеников и учителей

**Задачи**:
- [ ] Создать два сериализатора: `QuestionStudentSerializer` (без `is_correct`) и `QuestionTeacherSerializer` (полный)
- [ ] Обновить `HomeworkViewSet` с permission-based сериализацией
- [ ] Убрать все клиентские проверки правильности ответов во frontend
- [ ] Добавить rate limiting на submit эндпоинт (защита от брутфорса)
- [ ] Логировать подозрительные действия (много быстрых сабмитов)

**Файлы для изменения**:
```
teaching_panel/homework/serializers.py
teaching_panel/homework/views.py
teaching_panel/homework/permissions.py
frontend/src/modules/homework-analytics/HomeworkStudent.js
frontend/src/modules/homework-analytics/HomeworkAnswering.js
```

**Пример кода (Backend)**:
```python
# homework/serializers.py
class ChoiceStudentSerializer(serializers.ModelSerializer):
    """Для учеников - БЕЗ is_correct"""
    class Meta:
        model = Choice
        fields = ['id', 'text']  # НЕТ is_correct!

class QuestionStudentSerializer(serializers.ModelSerializer):
    choices = ChoiceStudentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'prompt', 'question_type', 'choices', 'order']
        # НЕТ points! Ученик не должен знать вес вопроса

class HomeworkStudentSerializer(serializers.ModelSerializer):
    questions = QuestionStudentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Homework
        fields = ['id', 'title', 'description', 'questions', 'created_at']
```

**Критерии готовности**:
- ✅ В Network tab нет JSON с `is_correct: true/false`
- ✅ Ученик не видит баллы за вопрос до проверки
- ✅ Rate limiting работает (429 при спаме)
- ✅ Учитель видит полную информацию в конструкторе

---

### 🟢 Этап 2: Монетизация (2 декабря - НАЧАЛО)

#### 2.1 Система Подписок и Оплаты (День 2 - ПРИОРИТЕТ #2)
**Почему вторым**: Критична для монетизации, работает без HTTPS локально (HTTPS отложим)

**Архитектура**:
- **База данных**: Новая модель `Subscription` в `accounts`
- **Процессинг**: Интеграция с ЮKassa (или Stripe для РФ)
- **Автопродление**: Celery задача для проверки истечения
- **Admin панель**: Контроль всех подписок

**Модель данных**:
```python
# accounts/models.py
class Subscription(models.Model):
    PLAN_CHOICES = (
        ('trial', 'Пробный (7 дней)'),
        ('monthly', 'Месячный'),
        ('yearly', 'Годовой'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Активна'),
        ('cancelled', 'Отменена'),
        ('expired', 'Истекла'),
        ('pending', 'Ожидает оплаты'),
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='trial')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Даты
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Оплата
    payment_method = models.CharField(max_length=50, blank=True)  # card_last4, etc
    auto_renew = models.BooleanField(default=True)
    next_billing_date = models.DateField(null=True, blank=True)
    
    # История платежей
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_active(self):
        return self.status == 'active' and self.expires_at > timezone.now()
    
    def days_until_expiry(self):
        if self.expires_at:
            delta = self.expires_at - timezone.now()
            return max(0, delta.days)
        return 0


class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Ожидает'),
        ('succeeded', 'Успешно'),
        ('failed', 'Ошибка'),
        ('refunded', 'Возврат'),
    )
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='RUB')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Интеграция с процессингом
    payment_system = models.CharField(max_length=50, default='yookassa')  # или 'stripe'
    payment_id = models.CharField(max_length=255, unique=True)  # ID в системе оплаты
    payment_url = models.URLField(blank=True)  # Ссылка для оплаты
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Метаданные
    metadata = models.JSONField(default=dict, blank=True)
```

**Задачи**:
- [ ] Создать модели `Subscription` и `Payment`
- [ ] Миграции БД
- [ ] Интегрировать ЮKassa API (или Stripe)
- [ ] API endpoints:
  - `POST /api/subscriptions/create/` - создание подписки
  - `POST /api/subscriptions/cancel/` - отмена автопродления
  - `GET /api/subscriptions/my/` - текущая подписка
  - `POST /api/payments/create/` - инициация платежа
  - `POST /api/payments/webhook/` - webhook от платежной системы
- [ ] Frontend: страница управления подпиской
- [ ] Middleware/Decorator для проверки активной подписки
- [ ] Celery задачи:
  - `check_expiring_subscriptions` (каждый день): уведомления за 3/1 дня до истечения
  - `process_expired_subscriptions` (каждый час): деактивация истекших
  - `retry_failed_payments` (раз в 3 дня): повторная попытка списания
- [ ] Admin панель: просмотр, фильтрация, активация/деактивация подписок
- [ ] Email/Telegram уведомления об оплате/истечении

**Файлы для создания/изменения**:
```
teaching_panel/accounts/models.py (добавить Subscription, Payment)
teaching_panel/accounts/serializers.py
teaching_panel/accounts/views.py (SubscriptionViewSet, PaymentViewSet)
teaching_panel/accounts/urls.py
teaching_panel/accounts/permissions.py (RequireActiveSubscription)
teaching_panel/accounts/tasks.py (Celery задачи)
teaching_panel/accounts/admin.py (админка для подписок)
teaching_panel/accounts/middleware.py (проверка подписки)
frontend/src/components/SubscriptionPage.js
frontend/src/components/PaymentModal.js
```

**Интеграция ЮKassa**:
```bash
pip install yookassa
```

```python
# accounts/payments.py
from yookassa import Configuration, Payment as YooPayment

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

def create_payment(subscription, amount, description):
    payment = YooPayment.create({
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"{settings.FRONTEND_URL}/subscription/success"
        },
        "capture": True,
        "description": description,
        "metadata": {
            "subscription_id": subscription.id,
            "user_id": subscription.user.id
        }
    })
    return payment
```

**Критерии готовности**:
- ✅ Учитель может оформить подписку и оплатить
- ✅ Webhook от ЮKassa обрабатывается корректно
- ✅ Истекшие подписки автоматически деактивируются
- ✅ Уведомления работают (Email + Telegram)
- ✅ Админ видит все подписки и может управлять ими
- ✅ Middleware блокирует неоплативших учителей

---

### 🟡 Этап 3: UX и Функционал (3 декабря)

#### 3.1 Сброс Пароля через Telegram (День 3)
**Почему третьим**: Уже есть база (telegram_bot.py), нужно быстро доработать

**Текущее состояние**: Базовый функционал есть, нужно улучшить UX

**Задачи**:
- [ ] **Обязательная привязка Telegram при регистрации** (или опциональная с бонусом)
- [ ] Добавить поле `telegram_verified` в `CustomUser`
- [ ] Процесс верификации Telegram:
  1. Учитель регистрируется → получает код
  2. Отправляет `/start <code>` боту
  3. Бот проверяет код и привязывает telegram_id
- [ ] Улучшить UI в профиле для привязки/отвязки Telegram
- [ ] Добавить QR-код для быстрой привязки
- [ ] Тестирование всех флоу восстановления пароля

**Файлы для изменения**:
```
teaching_panel/accounts/models.py (добавить telegram_verified)
teaching_panel/accounts/views.py (эндпоинты для генерации кода, проверки)
teaching_panel/telegram_bot.py (обработка /start <code>)
frontend/src/components/ProfileSettings.js (UI привязки Telegram)
```

**Пример кода (Генерация кода привязки)**:
```python
# accounts/views.py
@action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
def generate_telegram_link_code(self, request):
    """Генерирует одноразовый код для привязки Telegram"""
    user = request.user
    
    # Генерируем 6-значный код
    code = ''.join(random.choices(string.digits, k=6))
    
    # Сохраняем в кэше на 10 минут
    cache.set(f'tg_link_code:{code}', user.id, timeout=600)
    
    return Response({
        'code': code,
        'bot_username': settings.TELEGRAM_BOT_USERNAME,
        'expires_in': 600
    })
```

**Критерии готовности**:
- ✅ Новый пользователь может легко привязать Telegram
- ✅ QR-код работает для быстрой привязки
- ✅ Восстановление пароля через бота работает стабильно
---

#### 3.2 Обновление Конструктора ДЗ (День 3 - параллельно)
**Почему вместе с Telegram**: Можно делать параллельно, если два человека
#### 3.1 Push-уведомления в Telegram (День 12-14)
**Почему пятым**: Требует готовой системы подписок и Telegram-интеграции

**Архитектура**:
- **Настройки уведомлений**: модель `NotificationSettings` с флагами для каждого типа
- **Отправка**: Celery задачи для асинхронной рассылки
- **Типы уведомлений**:
  - **Для учителя**:
    - Новое ДЗ сдано учеником
    - Ученик присоединился к занятию
    - Истекает подписка (3/1 день)
    - Платеж прошел успешно
    - Ученик пропустил занятие
  - **Для ученика**:
    - ДЗ проверено учителем
    - Начало занятия (за 30 минут)
    - Новое ДЗ назначено
    - Дедлайн ДЗ приближается (за 24 часа)
    - Учитель отменил занятие

**Модель данных**:
```python
# accounts/models.py
class NotificationSettings(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_settings')
    
    # Telegram уведомления
    telegram_enabled = models.BooleanField(default=True)
    
    # Для учителя
    notify_homework_submitted = models.BooleanField(default=True, verbose_name='ДЗ сдано')
    notify_student_joined_lesson = models.BooleanField(default=True, verbose_name='Ученик на занятии')
    notify_student_missed_lesson = models.BooleanField(default=True, verbose_name='Ученик пропустил')
    notify_subscription_expiring = models.BooleanField(default=True, verbose_name='Истекает подписка')
    notify_payment_success = models.BooleanField(default=True, verbose_name='Платеж успешен')
    
    # Для ученика
    notify_homework_graded = models.BooleanField(default=True, verbose_name='ДЗ проверено')
    notify_lesson_starting = models.BooleanField(default=True, verbose_name='Занятие начинается')
    notify_homework_assigned = models.BooleanField(default=True, verbose_name='Новое ДЗ')
    notify_homework_deadline = models.BooleanField(default=True, verbose_name='Дедлайн ДЗ')
    notify_lesson_cancelled = models.BooleanField(default=True, verbose_name='Занятие отменено')
    
    # Email (опционально)
    email_enabled = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Настройки уведомлений: {self.user.email}"


class NotificationLog(models.Model):
    """Логирование отправленных уведомлений для отладки и аналитики"""
    TYPE_CHOICES = (
        ('homework_submitted', 'ДЗ сдано'),
        ('homework_graded', 'ДЗ проверено'),
        ('lesson_starting', 'Занятие начинается'),
        ('subscription_expiring', 'Истекает подписка'),
        # ... другие типы
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notification_logs')
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    channel = models.CharField(max_length=20, choices=(('telegram', 'Telegram'), ('email', 'Email')))
    status = models.CharField(max_length=20, choices=(('sent', 'Отправлено'), ('failed', 'Ошибка')))
    message = models.TextField()
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Задачи**:
- [ ] Создать модели `NotificationSettings` и `NotificationLog`
- [ ] Миграции БД
- [ ] Создать `notifications.py` с helper-функциями отправки
- [ ] Интегрировать отправку во все триггерные точки:
  - `homework/views.py::SubmitHomework` → уведомление учителю
  - `homework/views.py::GradeAnswer` → уведомление ученику
  - `schedule/views.py::StartLesson` → уведомление ученикам за 30 мин (Celery)
  - `accounts/tasks.py::check_expiring_subscriptions` → уведомление учителю
- [ ] API endpoints:
  - `GET /api/notifications/settings/` - текущие настройки
  - `PATCH /api/notifications/settings/` - обновление настроек
  - `GET /api/notifications/history/` - история уведомлений
- [ ] Frontend: страница настроек уведомлений с переключателями
- [ ] Тестирование всех типов уведомлений

**Файлы для создания/изменения**:
```
teaching_panel/accounts/models.py (NotificationSettings, NotificationLog)
teaching_panel/accounts/notifications.py (новый файл с логикой отправки)
teaching_panel/accounts/views.py (NotificationSettingsViewSet)
teaching_panel/accounts/urls.py
teaching_panel/homework/views.py (триггеры уведомлений)
teaching_panel/schedule/views.py (триггеры уведомлений)
teaching_panel/schedule/tasks.py (Celery задачи для отложенных уведомлений)
teaching_panel/telegram_bot.py (функции send_notification)
frontend/src/components/NotificationSettings.js (UI настроек)
```

**Пример кода (Отправка уведомления)**:
```python
# accounts/notifications.py
import requests
from django.conf import settings
from .models import NotificationSettings, NotificationLog

def send_telegram_notification(user, notification_type, message):
    """Отправка Telegram уведомления"""
    
    # Проверяем настройки пользователя
    settings_obj = user.notification_settings
    if not settings_obj.telegram_enabled:
        return False
    
    # Проверяем конкретный тип уведомления
    type_mapping = {
        'homework_submitted': settings_obj.notify_homework_submitted,
        'homework_graded': settings_obj.notify_homework_graded,
        'lesson_starting': settings_obj.notify_lesson_starting,
        # ... другие типы
    }
    
    if not type_mapping.get(notification_type, True):
        return False  # Пользователь отключил этот тип
    
    # Отправляем через Telegram Bot API
    if not user.telegram_chat_id:
        return False  # Нет chat_id
    
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            'chat_id': user.telegram_chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        })
        
        # Логируем
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='sent' if response.ok else 'failed',
            message=message,
            error_message='' if response.ok else response.text
        )
        
        return response.ok
    except Exception as e:
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='failed',
            message=message,
            error_message=str(e)
        )
        return False


# Использование в views:
# from accounts.notifications import send_telegram_notification
# send_telegram_notification(
#     teacher,
#     'homework_submitted',
#     f"📝 Ученик {student.get_full_name()} сдал ДЗ: {homework.title}"
# )
```

**Критерии готовности**:
- ✅ Все типы уведомлений работают корректно
- ✅ Настройки сохраняются и применяются
- ✅ UI настроек интуитивен
- ✅ Логирование работает для отладки

---

---

### 🔴 Этап 4: Доработки (4 декабря)

#### 4.1 Push-уведомления в Telegram (День 4)
**Задачи** (упрощенная версия для дедлайна):

**3.2.1 Добавить недостающие типы вопросов**:
- [ ] `MATCHING` - сопоставление (пары элементов)
- [ ] `ORDERING` - упорядочивание (правильная последовательность)
- [ ] `SHORT_ANSWER` - короткий ответ (авто-проверка по ключевым словам)
- [ ] `FILE_UPLOAD` - загрузка файла
- [ ] `CODE` - ввод кода с подсветкой синтаксиса

**3.2.2 Backend изменения**:
```python
# homework/models.py
class Question(models.Model):
    QUESTION_TYPES = (
        ('TEXT', 'Текстовый ответ'),
        ('SINGLE_CHOICE', 'Один вариант'),
        ('MULTI_CHOICE', 'Несколько вариантов'),
        ('MATCHING', 'Сопоставление'),  # новый
        ('ORDERING', 'Упорядочивание'),  # новый
        ('SHORT_ANSWER', 'Короткий ответ'),  # новый
        ('FILE_UPLOAD', 'Загрузка файла'),  # новый
        ('CODE', 'Код'),  # новый
    )
    
    # Для MATCHING
    matching_pairs = models.JSONField(default=list, blank=True)
    # [{"left": "Python", "right": "Язык программирования"}, ...]
    
    # Для ORDERING
    ordering_items = models.JSONField(default=list, blank=True)
    # ["Шаг 1", "Шаг 2", "Шаг 3"]
    
    # Для SHORT_ANSWER
    keywords = models.JSONField(default=list, blank=True)
    # ["ключевое слово 1", "ключевое слово 2"]
    case_sensitive = models.BooleanField(default=False)
    
    # Для CODE
    programming_language = models.CharField(max_length=50, blank=True)
    # "python", "javascript", etc.
    test_cases = models.JSONField(default=list, blank=True)
    # [{"input": "5", "expected_output": "120"}]  # для автопроверки


class Answer(models.Model):
    # Дополнительные поля для новых типов
    matching_answer = models.JSONField(default=dict, blank=True)
    # {"Python": "Язык программирования", ...}
    
    ordering_answer = models.JSONField(default=list, blank=True)
    # ["Шаг 1", "Шаг 2", "Шаг 3"]
    
    file_upload = models.FileField(upload_to='homework_files/', blank=True, null=True)
    
    # История редактирований
    edit_count = models.IntegerField(default=0)
    last_edited_at = models.DateTimeField(null=True, blank=True)
```

**3.2.3 Повторные ответы и редактирование**:
- [ ] Добавить поле `allow_retries` в модель `Homework`
- [ ] Добавить поле `max_retries` (количество попыток, 0 = бесконечно)
- [ ] Создать модель `SubmissionAttempt` для хранения истории попыток
- [ ] API endpoint: `POST /api/homework/{id}/retry/` - начать новую попытку
- [ ] Frontend: кнопка "Попробовать еще раз" если `allow_retries=True`
- [ ] Логика: при retry создается новый `StudentSubmission` с `attempt_number`

**3.2.4 Frontend обновления**:
- [ ] Переработать `HomeworkConstructor.js` под новый дизайн
- [ ] Использовать компоненты из `shared/components/`
- [ ] Добавить drag-and-drop для упорядочивания вопросов
- [ ] Компоненты для каждого типа вопроса:
  - `MatchingQuestion.js`
  - `OrderingQuestion.js`
  - `ShortAnswerQuestion.js`
  - `FileUploadQuestion.js`
  - `CodeQuestion.js` (с Monaco Editor или CodeMirror)
- [ ] Preview режим для предпросмотра ДЗ перед публикацией
- [ ] Обновить `HomeworkStudent.js` для отображения новых типов
- [ ] Добавить кнопку "Редактировать ответ" если submission.status == 'in_progress'

**Файлы для изменения**:
```
teaching_panel/homework/models.py (расширение типов вопросов)
teaching_panel/homework/serializers.py
teaching_panel/homework/views.py (retry logic)
teaching_panel/homework/admin.py
frontend/src/modules/homework-analytics/HomeworkConstructor.js (полная переработка)
frontend/src/modules/homework-analytics/components/ (новые компоненты)
frontend/src/modules/homework-analytics/HomeworkStudent.js
frontend/src/modules/homework-analytics/HomeworkAnswering.js
```

**Критерии готовности**:
- ✅ Все 8 типов вопросов работают
- ✅ Конструктор интуитивен и красив
- ✅ Ученик может повторно отвечать (если разрешено)
- ✅ Ученик может редактировать ответ до отправки
- ✅ Учитель видит историю попыток
- ✅ Автопроверка работает для всех типов (кроме TEXT и FILE_UPLOAD)

---

#### 3.3 Дерево Прогресса Учителя (День 18-19)
**Почему седьмым**: Требует готовых аналитических данных
---

#### 4.2 Дерево Прогресса Учителя (День 4 - если останется время)
**Можно отложить**: Не критично для запуска
- [ ] Создать API endpoint `GET /api/analytics/teacher-stats/`
- [ ] Подтянуть реальные данные:
  - Количество проведенных занятий (из `Lesson` где `status='completed'`)
  - Количество активных учеников (уникальные ученики на занятиях за последние 30 дней)
  - Средний балл за ДЗ (из `StudentSubmission.total_score`)
  - Количество проверенных ДЗ за неделю
  - Статистика по группам
- [ ] Визуализировать "дерево":
  - Корень = учитель
  - Ветви = группы
  - Листья = ученики
  - Цвет листьев = успеваемость (зеленый >80%, желтый 50-80%, красный <50%)
- [ ] Использовать библиотеку для визуализации дерева (react-d3-tree или recharts)
- [ ] Интерактивность: клик по ученику → детальная статистика

**Файлы для создания/изменения**:
```
teaching_panel/analytics/views.py (TeacherStatsViewSet)
teaching_panel/analytics/serializers.py
teaching_panel/analytics/urls.py
frontend/src/components/TeacherHomePage.js
frontend/src/modules/analytics/TeacherTree.js (новый компонент)
```

**Пример API response**:
```json
{
  "teacher": {
    "id": 1,
    "name": "Иван Иванов",
    "total_lessons": 45,
    "active_students": 12,
    "average_homework_score": 78.5
  },
  "groups": [
    {
      "id": 1,
      "name": "Математика 10А",
      "students_count": 8,
      "average_score": 82.3,
      "students": [
        {
          "id": 5,
          "name": "Петя Петров",
          "average_score": 90.0,
          "attendance_rate": 0.95,
          "homeworks_completed": 10
        }
      ]
    }
  ]
}
```

**Критерии готовности**:
- ✅ Дерево отображается корректно
- ✅ Данные реальные, не заглушки
- ✅ Клик по элементу показывает детали
- ✅ Дизайн привлекательный

---

### 🔴 Этап 4: Тестирование и Запуск (Неделя 4)

---

### ⚡ Этап 5: Критичное (5 декабря - ДЕДЛАЙН)

#### 5.1 Базовое Тестирование (День 5 утро)
**Экспресс-версия**: Только критичные флоу
1. **Регистрация и вход**: 100 одновременных пользователей
2. **Создание занятий**: 50 учителей создают занятия
3. **Сдача ДЗ**: 200 учеников отправляют ответы
**Цель**: Убедиться, что основное работает (МИНИМУМ)

**Сценарии** (упрощенные):
**Задачи** (ручное тестирование):
- [ ] Проверить регистрацию/вход
- [ ] Проверить создание занятия + Zoom
- [ ] Проверить создание и сдачу ДЗ
- [ ] Проверить оплату подписки (тестовая карта)
- [ ] Проверить Telegram уведомления
- [ ] Проверить сброс пароля через Telegram

**Пример Locust файла**:
```python
# load_tests/locustfile.py
from locust import HttpUser, task, between
import random

class TeachingPanelUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login при старте"""
        response = self.client.post("/api/jwt/token/", json={
            "email": f"student{random.randint(1, 100)}@test.com",
            "password": "testpass123"
        })
        if response.ok:
            self.token = response.json()['access']
            self.client.headers = {'Authorization': f'Bearer {self.token}'}
    
    @task(3)
    def view_lessons(self):
        self.client.get("/api/schedule/lessons/")
    
    @task(2)
    def view_homework(self):
        self.client.get("/api/homework/")
    
    @task(1)
    def submit_homework(self):
        # Логика сдачи ДЗ
        pass
```

**Команды**:
```bash
# Запуск локально
locust -f load_tests/locustfile.py

# Запуск с параметрами
locust -f load_tests/locustfile.py --host=https://teachingpanel.com --users=100 --spawn-rate=10
```

**Критерии готовности**:
- ✅ Система стабильна при 100 одновременных пользователях
- ✅ Latency p95 < 500ms для основных API
- ✅ Нет memory leaks
- ✅ Database не перегружена
- ✅ Оптимизации применены

---

#### 4.2 Полное User Тестирование (День 23-25)
**Почему последним**: Все должно работать

**Методология**: User Acceptance Testing (UAT)

**Тестовые группы**:
1. **Реальные учителя** (3-5 человек) - beta тестеры
2. **Реальные ученики** (10-15 человек) - разные возраста
3. **Админ панель** - ты сам

**Чек-лист для учителей**:
---

#### 5.2 Домен и HTTPS (День 5 вечер - ЕСЛИ УСПЕЕМ)
**Отложено**: Можно запуститься на IP, домен потом
**Чек-лист для учеников**:
- [ ] Регистрация
- [ ] Вход в личный кабинет
- [ ] Просмотр расписания
- [ ] Присоединение к Zoom занятию
- [ ] Просмотр ДЗ → выполнение всех типов вопросов
- [ ] Отправка ДЗ → редактирование → повторная попытка
- [ ] Просмотр оценок
**Задачи**:
- [ ] Купить домен (когда определишься с названием)
- [ ] Настроить DNS
- [ ] Получить SSL (Let's Encrypt)
- [ ] Обновить nginx
- [ ] Обновить settings.py (ALLOWED_HOSTS, CORS)

**Можно отложить на неделю после запуска!**
🚀 ЗАПУСК
```

---

## 🕐 Временная Оценка

| Этап | Задачи | Дни | Начало | Конец |
|------|--------|-----|--------|-------|
| **Этап 1** | Инфраструктура | 4 | 01.12 | 04.12 |
| **Этап 2** | Ядро функционала | 7 | 05.12 | 11.12 |
| **Этап 3** | Улучшение UX | 8 | 12.12 | 19.12 |
| **Этап 4** | Тестирование | 6 | 20.12 | 25.12 |
| **Буфер** | Исправления | 5 | 26.12 | 30.12 |
| **ИТОГО** | | **30 дней** | 01.12 | 30.12 |

**Запуск**: 31 декабря 2025 🎉

---

## 🎯 Метрики Успеха

### Технические
- [ ] Uptime > 99.5%
- [ ] API latency p95 < 500ms
- [ ] Page load time < 2s
- [ ] Mobile PageSpeed Score > 80
- [ ] Zero critical security issues

### Бизнес
- [ ] 10+ активных учителей в первую неделю
- [ ] 50+ учеников зарегистрировались
- [ ] Conversion trial → paid > 20%
- [ ] Churn rate < 10% в первый месяц
## 📊 Зависимости Между Задачами (ОБНОВЛЕНО)

```
День 1 (1 дек):
    1.1 Безопасность ДЗ (критично!)
            ↓
День 2 (2 дек):
    2.1 Система Подписок (монетизация)
            ↓
## 🕐 Временная Оценка (РЕАЛЬНАЯ)

| День | Дата | Задачи | Часов | Статус |
|------|------|--------|-------|--------|
| **День 1** | 01.12 | Безопасность ДЗ | 8-10 | 🔴 Критично |
| **День 2** | 02.12 | Подписки + Оплата | 10-12 | 🔴 Критично |
| **День 3** | 03.12 | Telegram + ДЗ (параллельно) | 10-12 | 🟡 Важно |
| **День 4** | 04.12 | Push + Дерево | 8-10 | 🟡 Важно |
| **День 5** | 05.12 | Тестирование + Фиксы | 12-14 | 🔴 Дедлайн |
| **ИТОГО** | | | **5 дней** | |

**Запуск**: 5 декабря 2025 вечер 🚀

**Домен/HTTPS**: Можно сделать на следующей неделе, не блокирует запуск!
```
---

## 📝 Следующие Шаги

1. **Прямо сейчас**:
   - [ ] Review этого плана
   - [ ] Купить домен
   - [ ] Создать отдельные ветки в Git для каждой задачи

2. **Завтра (01.12)**:
   - [ ] Начать Этап 1.1: Настройка домена и HTTPS
   - [ ] Создать migrations для новых моделей (Subscription, NotificationSettings)

3. **Еженедельно**:
   - [ ] Демо для stakeholders (если есть)
   - [ ] Ретроспектива: что пошло не так, как улучшить

---

## 📚 Полезные Ресурсы

**Документация**:
- [ЮKassa API Docs](https://yookassa.ru/developers/api)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Let's Encrypt Certbot](https://certbot.eff.org/)
- [Locust Docs](https://docs.locust.io/)

**Библиотеки**:
## 📝 Следующие Шаги

### 🔥 Прямо сейчас (30.11 вечер):
- [ ] Review этого плана
- [ ] Создать ветки в Git: `feature/homework-security`, `feature/subscriptions`
- [ ] Подготовить тестовые карты для ЮKassa

### ⚡ Завтра утро (01.12 - День 1):
- [ ] **09:00**: Начать этап 1.1 - Безопасность ДЗ
- [ ] Создать `QuestionStudentSerializer` (без `is_correct`)
- [ ] Обновить `HomeworkViewSet` с permission-based сериализацией
- [ ] Убрать клиентские проверки во frontend
- [ ] **Цель дня**: Ученики НЕ видят правильные ответы

### 📅 2 декабря (День 2):
- [ ] Создать модели `Subscription` и `Payment`
- [ ] Интеграция ЮKassa
- [ ] API endpoints для подписок
- [ ] Frontend страница оплаты
- [ ] **Цель дня**: Можно оформить и оплатить подписку
Этот план структурирован с учетом:
- **Зависимостей**: каждая задача опирается на предыдущие
- **Рисков**: критичные задачи (HTTPS, оплата) в начале
- **UX**: функционал сначала, полировка потом
- **Тестирования**: достаточно времени на нагрузку и UAT

**Порядок логичен с точки зрения программирования**:
1. Инфраструктура → без HTTPS нельзя делать оплату
2. Монетизация → без подписок нет бизнеса
3. Core функционал → ДЗ и уведомления - сердце продукта
4. Аналитика → cherry on top
5. Тестирование → проверка всего сразу

**Удачи в реализации! 🚀**

---

*Последнее обновление: 30 ноября 2025*
## 🎉 Заключение

### Что изменилось:
- ❌ ~~30 дней~~ → ✅ **5 дней** (жесткий дедлайн!)
- ❌ ~~Домен первым~~ → ✅ **Домен в конце** (не блокирует запуск)
- ✅ **Приоритет**: Безопасность ДЗ → Подписки → Telegram → Уведомления
- ✅ **Минимальное тестирование**: только ручное, без Locust
- ✅ **Параллелизация**: День 3 можно делать 2 задачи одновременно

### Что можно отложить ПОСЛЕ 5 декабря:
1. 🟢 Домен + HTTPS (неделя 2)
2. 🟢 Полноценное нагрузочное тестирование (неделя 2)
3. 🟢 Дерево прогресса (nice to have)
4. 🟢 Дополнительные типы вопросов в ДЗ (оставить 3 базовых)

### Что ОБЯЗАТЕЛЬНО к 5 декабря:
1. 🔴 Безопасность ДЗ (без этого система скомпрометирована)
2. 🔴 Система подписок (без этого нет бизнеса)
3. 🟡 Telegram reset (улучшает UX)
4. 🟡 Push-уведомления (вовлечение)
5. 🔴 Базовое тестирование (проверка критичных флоу)

**Порядок оптимален для 5-дневного спринта!**

**Завтра начинаем с Безопасности ДЗ! 🚀**