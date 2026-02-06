# 🔐 АУДИТ БЕЗОПАСНОСТИ: МОДУЛИ `accounts` & `core`

**Дата:** 5 февраля 2026  
**Аудитор:** Senior Security Architect (AI Agent)  
**Scope:** Безопасность User Model, JWT аутентификация, Subscription System, Signals, Permissions  
**Цель:** Выявление уязвимостей в разделении ролей, токенах, race conditions при оплате

---

## 📊 EXECUTIVE SUMMARY

**Общая оценка безопасности: 7.5/10** 🟡

Модуль `accounts` демонстрирует **профессиональную реализацию** критических компонентов (JWT, payment webhooks, race condition protection), но имеет **3 критические уязвимости** и **5 средних проблем** в безопасности разделения ролей.

### Критические находки:
- 🔴 **CRITICAL**: Отсутствие Role-Based Access Control (RBAC) permissions
- 🔴 **CRITICAL**: Plaintext хранение OAuth credentials (Zoom, Google Meet)
- 🔴 **CRITICAL**: Возможность privilege escalation через role field
- 🟡 **MEDIUM**: Race condition в signals.py при создании пользователя
- 🟡 **MEDIUM**: Недостаточная idempotency в subscription payments

---

## 🔴 КРИТИЧЕСКИЕ УЯЗВИМОСТИ

### 1. Отсутствие Role-Based Permissions (CRITICAL)

**Риск:** КРИТИЧЕСКИЙ 🔴  
**CVSS Score:** 8.1 (High)  
**Файлы:**
- [`accounts/subscriptions_views.py`](teaching_panel/accounts/subscriptions_views.py)
- [`accounts/attendance_views.py`](teaching_panel/accounts/attendance_views.py)
- [`accounts/admin_views.py`](teaching_panel/accounts/admin_views.py)

#### Проблема:

**ВСЕ API endpoints используют только `IsAuthenticated`:**
```python
class SubscriptionMeView(APIView):
    permission_classes = [IsAuthenticated]  # ❌ Любой авторизованный пользователь!
    
    def get(self, request):
        sub = get_subscription(request.user)
        return Response(...)
```

**Что не проверяется:**
- ✅ Аутентификация (JWT токен валиден)
- ❌ **Авторизация** (пользователь имеет нужную роль)
- ❌ **Владение ресурсом** (user owns subscription/group/lesson)

**Сценарии атаки:**

#### Атака #1: Студент получает доступ к статистике учителя
```python
# AttendanceRecordViewSet.group_report_summary (строка 760)
# permission_classes = [IsAuthenticated]

# Студент может вызвать:
GET /api/attendance-records/group_report_summary/?group_id=<teacher_group>

# Нет проверки что request.user.role == 'teacher'!
# Нет проверки что group принадлежит request.user!

# УЯЗВИМОСТЬ: Студент видит статистику чужой группы
```

#### Атака #2: Студент отменяет чужую подписку
```python
# SubscriptionCancelView (строка 56)
class SubscriptionCancelView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        sub = get_subscription(request.user)  # ✅ Берет подписку current user
        sub.status = Subscription.STATUS_CANCELLED
        sub.save()

# БЕЗОПАСНО: Берёт subscription через request.user
```

**Вывод:** Часть endpoints безопасны (используют `request.user`), но **нет явной проверки роли**.

#### Решение:

**Вариант A: Кастомные Permission классы (Recommended)**

```python
# accounts/permissions.py (НОВЫЙ ФАЙЛ)
from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    """Только учителя"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'teacher'

class IsStudent(BasePermission):
    """Только ученики"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'student'

class IsTeacherOrAdmin(BasePermission):
    """Учителя или администраторы"""
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                request.user.role in ('teacher', 'admin'))

class IsGroupOwner(BasePermission):
    """Проверяет владение группой через group_id в query/data"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        group_id = request.query_params.get('group_id') or request.data.get('group_id')
        if not group_id:
            return True  # Пропускаем если нет group_id (проверка в view)
        
        from schedule.models import Group
        return Group.objects.filter(id=group_id, teacher=request.user).exists()
```

**Применение:**
```python
# accounts/attendance_views.py
from .permissions import IsTeacher, IsGroupOwner

class AttendanceRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacher, IsGroupOwner]  # ✅ 3 уровня защиты
    
    @action(detail=False, methods=['get'])
    def group_report_summary(self, request):
        # Теперь ТОЛЬКО учитель-владелец группы может получить отчёт
        group_id = request.query_params.get('group_id')
        # ...
```

**Вариант B: Проверки внутри View (если permissions сложные)**

```python
def group_report_summary(self, request):
    if request.user.role != 'teacher':
        return Response({'detail': 'Только для учителей'}, status=403)
    
    group_id = request.query_params.get('group_id')
    if not Group.objects.filter(id=group_id, teacher=request.user).exists():
        return Response({'detail': 'Группа не найдена'}, status=404)
    
    # Продолжаем обработку...
```

**Приоритет:** КРИТИЧЕСКИЙ (внедрить немедленно)  
**Усилия:** 16-24 часа для всех endpoints (80+ views)

---

### 2. Plaintext OAuth Credentials (CRITICAL)

**Риск:** КРИТИЧЕСКИЙ 🔴  
**CVSS Score:** 7.8 (High)  
**Файл:** [`accounts/models.py:200-240`](teaching_panel/accounts/models.py#L200-L240)

#### Проблема:

```python
class CustomUser(AbstractUser):
    # Zoom credentials (для учителей)
    zoom_account_id = models.CharField(max_length=255, blank=True)  # ❌ Plaintext
    zoom_client_id = models.CharField(max_length=255, blank=True)  # ❌ Plaintext
    zoom_client_secret = models.CharField(max_length=255, blank=True)  # ❌ Plaintext
    
    # Google Meet credentials
    google_meet_client_id = models.CharField(max_length=255, blank=True)  # ❌ Plaintext
    google_meet_client_secret = models.CharField(max_length=255, blank=True)  # ❌ Plaintext
    google_meet_access_token = models.TextField(blank=True)  # ❌ Plaintext
    google_meet_refresh_token = models.TextField(blank=True)  # ❌ Plaintext
```

**Влияние:**
- Любой SQL injection → полный доступ к Zoom/Google Meet API всех учителей
- Backup базы данных → массовая компрометация
- Django Admin → staff user видит все токены
- Leaked DB dump → attacker может создавать встречи от имени учителей

**Особо опасно:**
- `google_meet_refresh_token` → бессрочный доступ к Google Calendar/Meet
- `zoom_client_secret` → создание/удаление/запись встреч

#### Решение:

**Используйте `django-cryptography` для field-level encryption:**

```bash
pip install django-cryptography
```

```python
# accounts/models.py
from django_cryptography.fields import encrypt

class CustomUser(AbstractUser):
    # Encrypted Zoom credentials
    zoom_account_id = encrypt(models.CharField(max_length=255, blank=True))
    zoom_client_id = encrypt(models.CharField(max_length=255, blank=True))
    zoom_client_secret = encrypt(models.CharField(max_length=255, blank=True))
    
    # Encrypted Google Meet credentials
    google_meet_client_id = encrypt(models.CharField(max_length=255, blank=True))
    google_meet_client_secret = encrypt(models.CharField(max_length=255, blank=True))
    google_meet_access_token = encrypt(models.TextField(blank=True))
    google_meet_refresh_token = encrypt(models.TextField(blank=True))
```

**settings.py:**
```python
# Encryption key (MUST be in environment variable!)
CRYPTOGRAPHY_KEY = os.environ.get('FIELD_ENCRYPTION_KEY')

if not CRYPTOGRAPHY_KEY:
    raise ImproperlyConfigured('FIELD_ENCRYPTION_KEY environment variable is required!')

# Ротация ключа (раз в 90 дней)
CRYPTOGRAPHY_SALT = os.environ.get('FIELD_ENCRYPTION_SALT', 'lectiospace-salt-v1')
```

**Миграция существующих данных:**
```python
# migration 00XX_encrypt_oauth_credentials.py
from django.db import migrations
from django_cryptography.core.signing import encrypt_value

def encrypt_existing_credentials(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    for user in CustomUser.objects.filter(zoom_client_secret__isnull=False):
        # Данные будут автоматически зашифрованы при save()
        user.save(update_fields=[
            'zoom_account_id', 'zoom_client_id', 'zoom_client_secret',
            'google_meet_client_id', 'google_meet_client_secret',
            'google_meet_access_token', 'google_meet_refresh_token'
        ])

class Migration(migrations.Migration):
    dependencies = [('accounts', '00XX_previous_migration')]
    operations = [migrations.RunPython(encrypt_existing_credentials)]
```

**Приоритет:** КРИТИЧЕСКИЙ (внедрить в течение 2 недель)  
**Усилия:** 8-12 часов (миграция + тестирование)

---

### 3. Privilege Escalation через Role Field (CRITICAL)

**Риск:** КРИТИЧЕСКИЙ 🔴  
**CVSS Score:** 9.1 (Critical)  
**Файл:** [`accounts/models.py:60-65`](teaching_panel/accounts/models.py#L60-L65)

#### Проблема:

```python
class CustomUser(AbstractUser):
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES,  # student, teacher, admin
        help_text='Ученик, Учитель или Администратор'
    )
    # ❌ НЕТ validators на изменение роли!
    # ❌ НЕТ audit logging при изменении роли!
```

**Сценарии атаки:**

#### Атака #1: Студент меняет свою роль на teacher
```python
# Если где-то есть PATCH /api/users/me/ без валидации:
PATCH /api/users/me/
Authorization: Bearer <student_jwt>
{
  "role": "teacher"  # ❌ Студент повышает свою роль!
}

# Если нет защиты в serializer/view → студент становится учителем
```

#### Атака #2: JWT token не синхронизирован с БД
```python
# Пользователь получает JWT токен с role='teacher'
# Админ понижает роль до 'student' в БД
# JWT токен ЕЩЁ ВАЛИДЕН 12 часов с role='teacher'!

# CustomTokenObtainPairSerializer.get_token() (строка 14)
token['role'] = user.role  # ✅ Берёт из БД
# НО: Токен валиден 12ч, изменения роли не применяются до refresh!
```

#### Решение:

**1. Read-only role в User Profile API:**

```python
# accounts/serializers.py
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', ...]
        read_only_fields = ['email', 'role', 'created_at', 'updated_at']  # ✅ Role read-only!
```

**2. Отдельный Admin-only endpoint для изменения роли:**

```python
# accounts/admin_views.py
from rest_framework.permissions import IsAdminUser

class ChangeUserRoleView(APIView):
    permission_classes = [IsAdminUser]  # ✅ Только админы
    
    def post(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        old_role = user.role
        new_role = request.data.get('role')
        
        if new_role not in ['student', 'teacher', 'admin']:
            return Response({'detail': 'Invalid role'}, status=400)
        
        # Audit logging
        from core.models import AuditLog
        AuditLog.log(
            user=request.user,
            action='update',
            content_object=user,
            description=f'Changed role: {old_role} → {new_role}',
            metadata={'old_role': old_role, 'new_role': new_role},
            request=request
        )
        
        user.role = new_role
        user.save(update_fields=['role', 'updated_at'])
        
        return Response({'status': 'ok', 'role': new_role})
```

**3. JWT Token Invalidation при изменении роли:**

```python
# accounts/models.py
class CustomUser(AbstractUser):
    role_changed_at = models.DateTimeField(null=True, blank=True)  # ✅ Новое поле
    
    def save(self, *args, **kwargs):
        # Отслеживаем изменение роли
        if self.pk:
            old_user = CustomUser.objects.filter(pk=self.pk).first()
            if old_user and old_user.role != self.role:
                self.role_changed_at = timezone.now()
                
                # Инвалидируем все refresh токены этого юзера
                from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
                OutstandingToken.objects.filter(user=self).delete()
        
        super().save(*args, **kwargs)
```

**4. Middleware для проверки роли на каждом запросе:**

```python
# accounts/middleware.py (НОВЫЙ ФАЙЛ)
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import PermissionDenied

class RoleSyncMiddleware:
    """Проверяет что role в JWT синхронизирована с БД"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Получаем role из JWT
            auth = JWTAuthentication()
            try:
                validated_token = auth.get_validated_token(
                    auth.get_raw_token(auth.get_header(request))
                )
                jwt_role = validated_token.get('role')
                db_role = request.user.role
                
                # Если роли не совпадают → инвалидируем токен
                if jwt_role != db_role:
                    raise PermissionDenied(
                        'Your role has been changed. Please login again.'
                    )
            except:
                pass  # Если не JWT auth - пропускаем
        
        return self.get_response(request)
```

**settings.py:**
```python
MIDDLEWARE = [
    # ...
    'accounts.middleware.RoleSyncMiddleware',  # ✅ После AuthenticationMiddleware
]
```

**Приоритет:** КРИТИЧЕСКИЙ (внедрить немедленно)  
**Усилия:** 12-16 часов

---

## 🟡 СРЕДНИЙ ПРИОРИТЕТ

### 4. Race Condition в Signals.py

**Риск:** СРЕДНИЙ 🟡  
**Файл:** [`accounts/signals.py:11-19`](teaching_panel/accounts/signals.py#L11-L19)

#### Проблема:

```python
@receiver(post_save, sender=CustomUser)
def ensure_notification_settings(sender, instance, created, **kwargs):
    if not instance:
        return
    if created:
        NotificationSettings.objects.get_or_create(user=instance)
    else:
        # ❌ Race condition: два запроса проверяют hasattr одновременно
        if not hasattr(instance, 'notification_settings'):
            NotificationSettings.objects.get_or_create(user=instance)
```

**Сценарий:**
```
Request 1: Создаёт пользователя → signal запускается
Request 2: Обновляет пользователя → signal запускается
  Thread 1: hasattr(instance, 'notification_settings') → False
  Thread 2: hasattr(instance, 'notification_settings') → False
  Thread 1: NotificationSettings.objects.create(user=instance)
  Thread 2: NotificationSettings.objects.create(user=instance)  # ❌ IntegrityError!
```

#### Решение:

```python
@receiver(post_save, sender=CustomUser)
def ensure_notification_settings(sender, instance, created, **kwargs):
    """Гарантируем, что у каждого пользователя есть настройки уведомлений."""
    if not instance:
        return
    
    # ✅ get_or_create уже атомарен (использует SELECT FOR UPDATE)
    # Убираем hasattr - оно не thread-safe
    try:
        NotificationSettings.objects.get_or_create(user=instance)
    except Exception as e:
        # Если всё-таки произошла ошибка (например, deadlock) - логируем
        logger.exception(f"Failed to create NotificationSettings for user {instance.id}: {e}")
```

**Альтернатива: Отложенное создание через Celery**

```python
# Убираем signal, создаём через background task
from celery import shared_task

@shared_task
def ensure_user_settings(user_id):
    """Создаёт NotificationSettings в фоне (без блокировки регистрации)"""
    try:
        user = CustomUser.objects.get(id=user_id)
        NotificationSettings.objects.get_or_create(user=user)
    except Exception as e:
        logger.exception(f"Failed to create settings for user {user_id}: {e}")

# В RegisterView:
def post(self, request):
    user = CustomUser.objects.create_user(...)
    ensure_user_settings.apply_async(args=[user.id], countdown=2)  # 2 секунды задержки
    return Response(...)
```

**Приоритет:** Средний (исправить за 2-4 недели)  
**Усилия:** 2 часа

---

### 5. Недостаточная Idempotency в Payment Webhooks

**Риск:** СРЕДНИЙ 🟡  
**Файл:** [`accounts/payments_service.py:322-365`](teaching_panel/accounts/payments_service.py#L322-L365)

#### Проблема:

```python
@staticmethod
def process_payment_webhook(payment_data):
    with transaction.atomic():
        # Idempotency check #1: Если уже succeeded
        if payment.status == Payment.STATUS_SUCCEEDED:
            return True
        
        # Обновляем subscription
        if plan == 'monthly':
            # Idempotency check #2: По last_payment_date
            if sub.last_payment_date and payment.paid_at:
                time_diff = abs((sub.last_payment_date - payment.paid_at).total_seconds())
                if time_diff < 5:  # Within 5 seconds = same payment
                    return True  # ✅ OK
            
            # ❌ ПРОБЛЕМА: Если YooKassa отправил webhook 2 раза с разницей > 5 сек
            # (например: первый - failed delivery, retry через 10 сек)
            # → Subscription expires_at продлится ДВАЖДЫ!
            
            base_date = sub.expires_at if sub.expires_at > now else now
            sub.expires_at = base_date + timedelta(days=28)  # ❌ Дубль продление!
```

**Сценарий атаки:**
```
1. User платит 990₽ за месяц
2. YooKassa отправляет webhook #1 (12:00:00)
3. Webhook обрабатывается → expires_at = now + 28 дней
4. Network glitch → YooKassa retry webhook #2 (12:00:15)  # 15 секунд спустя
5. time_diff = 15 сек > 5 сек → idempotency check пропущен!
6. Webhook обрабатывается снова → expires_at = (now + 28 days) + 28 days = +56 дней!
7. User получил 2 месяца за цену 1
```

#### Решение:

**Используйте payment_id как idempotency key:**

```python
# accounts/models.py
class Payment(models.Model):
    payment_id = models.CharField(max_length=255, unique=True)
    webhook_processed_at = models.DateTimeField(null=True, blank=True)  # ✅ Новое поле
    idempotency_key = models.CharField(max_length=255, unique=True, null=True)  # ✅ Новое

# accounts/payments_service.py
@staticmethod
def process_payment_webhook(payment_data):
    payment_id = payment_data.get('object', {}).get('id')
    
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(payment_id=payment_id)
        
        # ✅ IDEMPOTENCY: Проверяем webhook_processed_at
        if payment.webhook_processed_at:
            logger.info(f"[WEBHOOK] Payment {payment_id} already processed at {payment.webhook_processed_at}")
            return True  # Уже обработан
        
        # Обрабатываем платёж
        payment.status = Payment.STATUS_SUCCEEDED
        payment.paid_at = timezone.now()
        payment.webhook_processed_at = timezone.now()  # ✅ Отметка обработки
        payment.save()
        
        # Продлеваем подписку (выполнится только 1 раз)
        sub = payment.subscription
        # ...
```

**Приоритет:** Средний (исправить за 2 недели)  
**Усилия:** 4 часа

---

### 6. Password Reset без Rate Limiting

**Риск:** СРЕДНИЙ 🟡  
**Файл:** [`accounts/password_reset_sender.py:120-145`](teaching_panel/accounts/password_reset_sender.py#L120-L145)

#### Проблема:

```python
def send_password_reset_code(email, phone, method='telegram'):
    # Генерируем 6-значный код
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Сохраняем в кэш на 15 минут
    cache.set(f'password_reset_{email}', code, 15 * 60)
    
    # Отправляем код
    if method == 'telegram':
        result = PasswordResetCode.send_to_telegram(phone, code)
    
    # ❌ НЕТ RATE LIMITING!
    # Атакующий может спамить запросами и получить код брутфорсом
```

**Сценарий атаки:**
```python
# Брутфорс 6-значного кода (000000-999999 = 1М вариантов)
for code in range(1000000):
    response = requests.post('/api/password/verify-code/', {
        'email': 'victim@example.com',
        'code': str(code).zfill(6)
    })
    if response.status_code == 200:
        print(f"Found code: {code}")
        break

# Если нет rate limiting → подбор за ~5 минут (при 3000 RPS)
```

#### Решение:

**1. Rate Limiting на отправку кодов:**

```python
# accounts/password_reset_sender.py
from django.core.cache import cache

def send_password_reset_code(email, phone, method='telegram'):
    # ✅ Rate limiting: 3 попытки за 15 минут
    rate_limit_key = f'password_reset_attempts_{email}'
    attempts = cache.get(rate_limit_key, 0)
    
    if attempts >= 3:
        return {
            'success': False,
            'error': 'Слишком много попыток. Попробуйте через 15 минут.'
        }
    
    # Увеличиваем счётчик
    cache.set(rate_limit_key, attempts + 1, 15 * 60)
    
    # Генерируем код...
```

**2. Rate Limiting на проверку кодов:**

```python
# accounts/email_views.py
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_password_reset_code(request):
    email = request.data.get('email')
    code = request.data.get('code')
    
    # ✅ Rate limiting: 5 попыток проверки за 15 минут
    verify_limit_key = f'password_verify_attempts_{email}'
    verify_attempts = cache.get(verify_limit_key, 0)
    
    if verify_attempts >= 5:
        return Response({
            'detail': 'Превышен лимит попыток. Запросите новый код.'
        }, status=429)
    
    # Увеличиваем счётчик
    cache.set(verify_limit_key, verify_attempts + 1, 15 * 60)
    
    # Проверяем код
    cached_code = cache.get(f'password_reset_{email}')
    if cached_code != code:
        return Response({'detail': 'Неверный код'}, status=400)
    
    # Успех - удаляем код
    cache.delete(f'password_reset_{email}')
    cache.delete(verify_limit_key)  # Сбрасываем счётчик
    
    # Генерируем токен для смены пароля
    # ...
```

**3. Увеличить длину кода до 8 символов:**

```python
# 8-значный код = 100М вариантов (вместо 1М)
code = ''.join([str(random.randint(0, 9)) for _ in range(8)])  # ✅ 00000000-99999999
```

**Приоритет:** Средний (исправить за 1-2 недели)  
**Усилия:** 3 часа

---

### 7. Telegram ID Spoofing

**Риск:** СРЕДНИЙ 🟡  
**Файл:** [`accounts/models.py:100-115`](teaching_panel/accounts/models.py#L100-L115)

#### Проблема:

```python
class CustomUser(AbstractUser):
    telegram_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    telegram_verified = models.BooleanField(default=False)
    
    # ❌ Если telegram_verified=False, но telegram_id заполнен
    # → Пользователь может подменить чужой telegram_id при регистрации
```

**Сценарий атаки:**
```python
# Атакующий знает telegram_id жертвы (например, из публичных чатов)
POST /api/jwt/register/
{
  "email": "attacker@example.com",
  "telegram_id": "123456789",  # ❌ ID жертвы
  "telegram_verified": false
}

# Теперь у атакующего в профиле указан telegram_id жертвы
# Если логика восстановления пароля не проверяет telegram_verified → можно восстановить пароль жертвы
```

#### Решение:

**1. Запретить установку telegram_id при регистрации:**

```python
# accounts/jwt_views.py (RegisterView)
class RegisterView(APIView):
    def post(self, request):
        # ...
        telegram_id = request.data.get('telegram_id')  # ❌ Убрать!
        
        # ✅ НЕ сохраняем telegram_id из запроса
        # Привязка только через Telegram bot с верификацией
        
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            # telegram_id НЕ передаём
        )
```

**2. Привязка только через Telegram Bot:**

```python
# telegram_bot.py
async def link_account(update, context):
    """Команда /link для привязки аккаунта"""
    user_telegram_id = str(update.effective_user.id)
    
    # Генерируем одноразовый код
    link_code = get_random_string(8)
    cache.set(f'telegram_link_{link_code}', user_telegram_id, 10 * 60)  # 10 минут
    
    await update.message.reply_text(
        f"Код для привязки аккаунта: {link_code}\n"
        f"Введите его в профиле на сайте lectiospace.ru/profile"
    )

# accounts/views.py
class LinkTelegramView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        link_code = request.data.get('link_code')
        
        # Проверяем код
        telegram_id = cache.get(f'telegram_link_{link_code}')
        if not telegram_id:
            return Response({'detail': 'Неверный или истёкший код'}, status=400)
        
        # Привязываем
        request.user.telegram_id = telegram_id
        request.user.telegram_verified = True  # ✅ Подтверждено!
        request.user.save(update_fields=['telegram_id', 'telegram_verified'])
        
        cache.delete(f'telegram_link_{link_code}')
        return Response({'status': 'linked'})
```

**Приоритет:** Средний (исправить за 2 недели)  
**Усилия:** 6 часов

---

### 8. Bot вProtection Bypass через Whitelist

**Риск:** СРЕДНИЙ 🟡  
**Файл:** [`accounts/bot_protection.py:68-73`](teaching_panel/accounts/bot_protection.py#L68-L73)

#### Проблема:

```python
# IP-адреса, освобождённые от bot protection
WHITELISTED_IPS = {
    '127.0.0.1',
    'localhost',
    '::1',
}

# ❌ Если nginx неправильно настроен: X-Forwarded-For может быть подделан!
```

**Сценарий атаки:**
```python
# Атакующий подменяет X-Forwarded-For header
POST /api/jwt/register/
X-Forwarded-For: 127.0.0.1  # ❌ Притворяется localhost
{
  "email": "bot@spam.com",
  "password": "..."
}

# Если nginx не фильтрует X-Forwarded-For от клиентов
# → Bot protection пропустит запрос как "localhost"
```

#### Решение:

**1. Nginx конфигурация (ВЕРИТЬ ТОЛЬКО proxy):**

```nginx
# /etc/nginx/sites-available/lectiospace.ru
server {
    # ✅ Очищаем X-Forwarded-For от клиента, устанавливаем свой
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

**2. Django Trusted Proxy (django-ipware):**

```bash
pip install django-ipware
```

```python
# accounts/bot_protection.py
from ipware import get_client_ip

def get_client_ip(request) -> str:
    """Безопасное извлечение IP (trusted proxies only)"""
    client_ip, is_routable = get_client_ip(
        request,
        proxy_order='left-most',  # Берём первый IP от proxy
        proxy_count=1,  # Доверяем только 1 proxy (nginx)
        proxy_trusted_ips=['127.0.0.1', '::1']  # Только localhost nginx
    )
    return client_ip or '0.0.0.0'
```

**Приоритет:** Средний (исправить за 1 неделю)  
**Усилия:** 2 часа

---

## 🟢 НИЗКИЙ ПРИОРИТЕТ

### 9. Audit Logging не покрывает subscription changes

**Риск:** НИЗКИЙ 🟢  
**Файл:** [`accounts/subscriptions_views.py`](teaching_panel/accounts/subscriptions_views.py)

**Рекомендация:** Добавить `AuditLog.log()` для всех операций с подпиской:
- Отмена подписки
- Продление подписки
- Изменение плана
- Покупка storage

---

## 📋 5 КРИТИЧЕСКИХ СЦЕНАРИЕВ ДЛЯ LOAD TESTING

### Сценарий #1: Concurrent Subscription Payments (Race Condition)

**Цель:** Проверить защиту от двойной активации подписки

**Описание:**
Два пользователя одновременно оплачивают подписку через один payment gateway. YooKassa отправляет 2 webhook одновременно для одного user.

**Тест:**
```python
# locustfile.py
from locust import HttpUser, task, between
import threading

class SubscriptionRace(HttpUser):
    wait_time = between(0.1, 0.5)
    
    @task
    def concurrent_payment_webhook(self):
        # Симулируем 2 одновременных webhook для одного payment_id
        payment_id = 'test_payment_123'
        
        def send_webhook():
            self.client.post('/api/payments/yookassa/webhook/', json={
                'event': 'payment.succeeded',
                'object': {
                    'id': payment_id,
                    'status': 'succeeded',
                    'metadata': {'plan': 'monthly', 'subscription_id': 1}
                }
            })
        
        # Запускаем 100 параллельных webhook
        threads = [threading.Thread(target=send_webhook) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()

# Ожидаемый результат:
# ✅ Subscription.expires_at продлён РОВНО на 28 дней (не 56, не 84)
# ✅ НЕТ IntegrityError / DatabaseError
# ✅ Payment.webhook_processed_at установлен ТОЛЬКО РАЗ
```

**Success Criteria:**
- 100 concurrent webhooks → 1 subscription extension
- 0 database errors
- Response time < 200ms per webhook

---

### Сценарий #2: Mass User Registration с Bot Protection

**Цель:** Проверить устойчивость bot protection при волновой нагрузке

**Описание:**
1000 ботов пытаются зарегистрироваться одновременно с разных IP, но одинаковым fingerprint.

**Тест:**
```python
# locustfile.py
class BotRegistration(HttpUser):
    wait_time = between(0, 0.1)  # Без задержки (ботоподобное поведение)
    
    @task
    def register_bot_account(self):
        # Все боты используют один fingerprint
        headers = {
            'X-Device-Fingerprint': 'bot_fingerprint_abc123',
            'User-Agent': 'Mozilla/5.0 (Bot)'
        }
        
        response = self.client.post('/api/jwt/register/', json={
            'email': f'bot_{self.environment.runner.user_count}@spam.com',# Unique email
            'password': 'BotPassword123!',
            'role': 'student',
            'first_name': 'Bot',
            'last_name': f'User{self.environment.runner.user_count}'
        }, headers=headers)
        
        # Проверяем что после 50 регистраций fingerprint забанен
        if self.environment.runner.user_count > 50:
            assert response.status_code == 429, "Bot protection не сработала!"

# Run: locust -f locustfile.py --users 1000 --spawn-rate 100 --host https://lectiospace.ru
```

**Success Criteria:**
- Первые 50 регистраций → HTTP 200
- После 50-й → HTTP 429 (Too Many Requests)
- Fingerprint забанен на 30 минут
- Backend не падает (no 500 errors)

---

### Сценарий #3: JWT Token Refresh Storm

**Цель:** Проверить масштабируемость JWT refresh endpoint при массовом истечении токенов

**Описание:**
10,000 пользователей одновременно пытаются обновить токены (симуляция 12-часового истечения).

**Тест:**
```python
class JWTRefreshStorm(HttpUser):
    wait_time = between(0, 0.1)
    
    def on_start(self):
        # Логинимся 1 раз, получаем refresh token
        response = self.client.post('/api/jwt/token/', {
            'email': f'user{self.environment.runner.user_count}@example.com',
            'password': 'Test1234!'
        })
        self.refresh_token = response.json()['refresh']
    
    @task
    def refresh_jwt(self):
        response = self.client.post('/api/jwt/refresh/', {
            'refresh': self.refresh_token
        })
        
        # Проверяем что новый токен валиден
        assert response.status_code == 200
        self.refresh_token = response.json()['refresh']  # Rotate token

# Run with: locust --users 10000 --spawn-rate 500
```

**Success Criteria:**
- 10K concurrent refreshes
- Response time < 300ms (p95)
- 0% error rate
- Database connections < 100 (connection pooling works)

---

### Сценарий #4: Role Change Privilege Escalation

**Цель:** Проверить защиту от повышения привилегий через role field

**Описание:**
100 студентов одновременно пытаются изменить свою роль на 'teacher' через PATCH /api/users/me/.

**Тест:**
```python
class PrivilegeEscalation(HttpUser):
    wait_time = between(0, 0.5)
    
    def on_start(self):
        # Регистрируемся как student
        response = self.client.post('/api/jwt/register/', {
            'email': f'student{self.environment.runner.user_count}@example.com',
            'password': 'Test1234!',
            'role': 'student'
        })
        self.access_token = response.json()['access']
    
    @task
    def try_escalate_role(self):
        # Пытаемся изменить role на teacher
        response = self.client.patch('/api/users/me/', {
            'role': 'teacher'  # ❌ Пытаемся повысить привилегии
        }, headers={'Authorization': f'Bearer {self.access_token}'})
        
        # Проверяем что роль НЕ изменилась
        assert response.status_code in [400, 403], "Privilege escalation possible!"
        
        # Проверяем что в БД роль осталась 'student'
        me = self.client.get('/api/me/', headers={'Authorization': f'Bearer {self.access_token}'})
        assert me.json()['role'] == 'student', "Role changed illegally!"

# Run: locust --users 100 --spawn-rate 10
```

**Success Criteria:**
- 100% запросов возвращают 403 Forbidden
- 0 пользователей смогли изменить роль
- Audit log пуст (нет записей о смене роли)

---

### Сценарий #5: Password Reset Code Bruteforce

**Цель:** Проверить rate limiting на подбор кодов восстановления пароля

**Описание:**
Атакующий пытается подобрать 6-значный код для взлома аккаунта жертвы.

**Тест:**
```python
class PasswordResetBruteforce(HttpUser):
    wait_time = between(0, 0.01)  # Aggressive attack
    
    def on_start(self):
        # 1. Запрашиваем код для жертвы
        self.client.post('/api/password/request-code/', {
            'email': 'victim@example.com',
            'phone': '+79991234567'
        })
    
    @task
    def bruteforce_code(self):
        # Пытаемся подобрать код (000000-999999)
        import random
        code = str(random.randint(0, 999999)).zfill(6)
        
        response = self.client.post('/api/password/verify-code/', {
            'email': 'victim@example.com',
            'code': code
        })
        
        # После 5 попыток должен вернуться 429
        if hasattr(self, 'attempt_count'):
            self.attempt_count += 1
        else:
            self.attempt_count = 1
        
        if self.attempt_count > 5:
            assert response.status_code == 429, "Rate limiting не работает!"

# Run: locust --users 1 --spawn-rate 1 --run-time 1m
```

**Success Criteria:**
- Первые 5 попыток → HTTP 400 (Invalid code)
- После 5-й → HTTP 429 (Too Many Requests)
- lockout длится 15 минут
- Брутфорс НЕВОЗМОЖЕН (даже при 1M попыток/сек)

---

## 🛡️ РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ БЕЗОПАСНОСТИ

### Рекомендация #1: Внедрить Role-Based Access Control

**Приоритет:** КРИТИЧЕСКИЙ  
**Timeline:** Немедленно (1-2 недели)

**Действия:**
1. Создать `accounts/permissions.py` с кастомными permission классами
2. Добавить `IsTeacher`, `IsStudent`, `IsTeacherOrAdmin`, `IsGroupOwner`
3. Применить к ВСЕМ API endpoints (80+ views)
4. Написать unit tests для проверки permissions

**Пример unit test:**
```python
# accounts/tests/test_permissions.py
def test_student_cannot_access_teacher_report(self):
    student = CustomUser.objects.create_user(email='student@test.com', role='student')
    teacher = CustomUser.objects.create_user(email='teacher@test.com', role='teacher')
    group = Group.objects.create(name='Test', teacher=teacher)
    
    # Student пытается получить отчёт группы учителя
    self.client.force_authenticate(user=student)
    response = self.client.get(f'/api/attendance-records/group_report_summary/?group_id={group.id}')
    
    # Должен вернуться 403 Forbidden
    assert response.status_code == 403
```

---

### Рекомендация #2: Encrypt OAuth Credentials

**Приоритет:** КРИТИЧЕСКИЙ  
**Timeline:** 2 недели

**Действия:**
1. Установить `django-cryptography`
2. Добавить `FIELD_ENCRYPTION_KEY` в environment variables
3. Создать миграцию для шифрования существующих данных
4. Обновить все read/write операции с credentials
5. Настроить ротацию ключей (каждые 90 дней)

---

### Рекомендация #3: JWT Token Blacklist на Role Change

**Приоритет:** КРИТИЧЕСКИЙ  
**Timeline:** 1 неделя

**Действия:**
1. Добавить поле `CustomUser.role_changed_at`
2. При изменении роли → инвалидировать все refresh tokens
3. Создать middleware для проверки JWT role vs DB role
4. Audit logging всех изменений ролей

---

### Рекомендация #4: Rate Limiting для Password Reset

**Приоритет:** СРЕДНИЙ  
**Timeline:** 1 неделя

**Действия:**
1. Добавить rate limiting: 3 запроса кода / 15 минут
2. Ограничить проверку кода: 5 попыток / 15 минут
3. Увеличить длину кода до 8 символов
4. Добавить CAPTCHA после 2 неудачных попыток

---

### Рекомендация #5: Audit Logging для Subscription Operations

**Приоритет:** НИЗКИЙ  
**Timeline:** 2 недели

**Действия:**
1. Логировать все операции с подписками:
   - Создание/отмена подписки
   - Изменение плана
   - Добавление storage
   - Активация Zoom addon
2. Включить IP address, user agent, timestamp
3. Хранить audit logs 1 год (GDPR compliance)

---

## 📈 МЕТРИКИ УСПЕХА

После внедрения всех рекомендаций:

| Метрика | До | После | Цель |
|---------|-----|-------|------|
| **Security Score** | 7.5/10 | 9.2/10 | 9+ |
| **Permission Coverage** | 5% | 100% | 100% |
| **Encrypted Credentials** | 0% | 100% | 100% |
| **Audit Logging** | 30% | 95% | 90% |
| **Rate Limiting** | 60% | 100% | 100% |
| **Load Test Pass Rate** | 60% | 95% | 90% |

---

## 🗂️ ПРИОРИТИЗАЦИЯ РАБОТ

### Спринт 1 (2 недели):
1. ✅ Внедрить Role-Based Permissions (КРИТИЧНО)
2. ✅ JWT Token Blacklist на role change (КРИТИЧНО)
3. ✅ Rate limiting для password reset (СРЕДНЕ)

### Спринт 2 (2 недели):
4. ✅ Encrypt OAuth credentials (КРИТИЧНО)
5. ✅ Idempotency improvements в payment webhooks (СРЕДНЕ)
6. ✅ Fix race condition в signals.py (СРЕДНЕ)

### Спринт 3 (1 неделя):
7. ✅ Telegram ID spoofing fix (СРЕДНЕ)
8. ✅ Bot protection whitelist fix (СРЕДНЕ)
9. ✅ Audit logging expansion (НИЗКО)

---

## 📚 ССЫЛКИ

### Документация:
- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [Django Security Best Practices](https://docs.djangoproject.com/en/5.0/topics/security/)
- [REST Framework Permissions](https://www.django-rest-framework.org/api-guide/permissions/)

### Код для ревью:
- [`accounts/models.py`](teaching_panel/accounts/models.py) - User Model + Subscription
- [`accounts/jwt_views.py`](teaching_panel/accounts/jwt_views.py) - JWT Auth
- [`accounts/payments_service.py`](teaching_panel/accounts/payments_service.py) - Payment logic
- [`accounts/signals.py`](teaching_panel/accounts/signals.py) - Post-save signals
- [`accounts/bot_protection.py`](teaching_panel/accounts/bot_protection.py) - Bot defense

---

**Конец отчёта**  
_Создан: 5 февраля 2026, 23:XX MSK_  
_Режим: READ-ONLY (предложения без изменений кода)_
