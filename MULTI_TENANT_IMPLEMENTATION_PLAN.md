# Multi-Tenant Implementation Plan v1.0
# Супер-подробный план для AI-агента: шаг за шагом, с тестами, без поломки прода

---

## ОБЩИЕ ПРАВИЛА ДЛЯ АГЕНТА

### Перед КАЖДЫМ шагом:
1. **Прочитай** целевые файлы полностью (read_file)
2. **Убедись** что Django стартует: `python manage.py check`
3. **Запусти** существующие тесты: `python manage.py test <app> --verbosity=2`
4. **Коммить** после каждого завершённого шага

### Перед КАЖДОЙ миграцией:
1. `python manage.py makemigrations --dry-run` — посмотри что создастся
2. `python manage.py makemigrations` — создай
3. `python manage.py migrate --plan` — покажи план
4. `python manage.py migrate` — накати
5. `python manage.py test tenants --verbosity=2` — зелёный?

### Принципы безопасности:
- **ВСЕ новые FK = null=True, blank=True** — никогда не NOT NULL сразу
- **Data migration отдельно** от schema migration
- **Обратная совместимость**: старый код работает без school FK = NULL
- **Feature flag**: `TENANT_ISOLATION_ENABLED = False` в settings.py — включаем ТОЛЬКО когда все тесты зелёные
- **Никогда не удалять поля/таблицы** на этом этапе

---

## ФАЗА 0: ПОДГОТОВКА (30 мин)
> Цель: Feature flag + базовые тесты которые гарантируют что ничего не сломано

### Шаг 0.1: Добавить feature flag в settings.py

**Файл**: `teaching_panel/teaching_panel/settings.py`
**Где**: после `PLATFORM_CONFIG` блока (конец файла)

```python
# === Multi-Tenant Feature Flags ===
# НЕ включать пока ВСЕ шаги Phase 1-3 не завершены и тесты не зелёные!
TENANT_ISOLATION_ENABLED = os.environ.get('TENANT_ISOLATION_ENABLED', '0') == '1'
```

**Проверка**: `python manage.py check` — должно быть 0 issues

### Шаг 0.2: Создать baseline тест-suite для tenants

**Файл**: `teaching_panel/tenants/tests.py` (создать)

Тесты из этого файла будут расти по мере реализации. Начальные тесты:

```
TEST_0_01: School и SchoolMembership модели существуют и мигрированы
TEST_0_02: Default School "lectiospace" существует, is_default=True
TEST_0_03: Все пользователи имеют SchoolMembership к default school
TEST_0_04: TenantMiddleware не ломает обычные запросы (127.0.0.1 → default school)
TEST_0_05: API /api/school/config/ возвращает конфиг default school
TEST_0_06: API /api/school/detail/ требует аутентификацию
TEST_0_07: to_frontend_config() возвращает правильную структуру
TEST_0_08: get_payment_credentials() fallback на PLATFORM_CONFIG
```

**Запуск**: `python manage.py test tenants -v2`
**Критерий**: ВСЕ 8 тестов зелёные

### Шаг 0.3: Создать smoke-тест для существующих views

**Файл**: `teaching_panel/tenants/tests_smoke.py` (создать)

```
SMOKE_01: GET /api/health/ → 200
SMOKE_02: POST /api/jwt/register/ с валидными данными → 201, получить tokens
SMOKE_03: GET /api/me/ с токеном → 200, вернуть user
SMOKE_04: GET /api/schedule/groups/ с учительским токеном → 200
SMOKE_05: GET /api/homework/ с учительским токеном → 200
SMOKE_06: Admin panel /admin/ → 200 (or redirect to login)
```

Эти тесты прогоняются ПОСЛЕ КАЖДОГО шага чтобы убедиться что ничего не сломано.

**Запуск**: `python manage.py test tenants.tests_smoke -v2`
**Критерий**: ВСЕ 6 тестов зелёные

---

## ФАЗА 1: SCHOOL FK НА МОДЕЛЯХ (2-3 часа)
> Цель: Добавить nullable school FK к ключевым моделям + data migration

### Стратегия: "Сверху вниз по FK-дереву"

Добавляем FK только к **корневым** моделям (родителям). Дочерние наследуют школу через parent.

```
УРОВЕНЬ 1 (прямой school FK):
  schedule.Group          — корень для Lesson, Attendance, RecurringLesson
  homework.Homework       — корень для Question, Choice, Submission, Answer
  accounts.Subscription   — платёжная изоляция
  analytics.ControlPoint  — аналитика привязана к teacher+group
  support.SupportTicket   — тикеты поддержки
  finance.StudentFinancialProfile — финансы
  bot.ScheduledMessage    — рассылки

УРОВЕНЬ 2 (наследуют через parent, FK НЕ нужен):
  schedule.Lesson         → наследует от Group
  schedule.LessonRecording → наследует от Lesson (indirect)
  schedule.Attendance     → наследует от Lesson
  homework.Question       → наследует от Homework
  homework.StudentSubmission → наследует от Homework
  analytics.ControlPointResult → наследует от ControlPoint
  finance.Transaction     → наследует от StudentFinancialProfile
```

### Шаг 1.1: Добавить school FK к schedule.Group

**Файл**: `teaching_panel/schedule/models.py`
**Класс**: `Group`
**Добавить поле**:

```python
school = models.ForeignKey(
    'tenants.School',
    on_delete=models.CASCADE,
    null=True, blank=True,
    related_name='groups',
    help_text='Школа, которой принадлежит группа'
)
```

**Команды**:
```bash
python manage.py makemigrations schedule --name add_school_fk_to_group
python manage.py migrate schedule
python manage.py test tenants -v2        # baseline тесты
python manage.py test tenants.tests_smoke -v2  # smoke тесты
python manage.py test schedule -v2       # не сломали schedule
```

**Проверка**: ВСЕ тесты зелёные

### Шаг 1.2: Добавить school FK к homework.Homework

**Файл**: `teaching_panel/homework/models.py`
**Класс**: `Homework`
**Добавить поле**:

```python
school = models.ForeignKey(
    'tenants.School',
    on_delete=models.CASCADE,
    null=True, blank=True,
    related_name='homeworks',
    help_text='Школа, которой принадлежит ДЗ'
)
```

**Команды**:
```bash
python manage.py makemigrations homework --name add_school_fk_to_homework
python manage.py migrate homework
python manage.py test tenants.tests_smoke -v2
python manage.py test homework -v2
```

### Шаг 1.3: Добавить school FK к accounts.Subscription

**Файл**: `teaching_panel/accounts/models.py`
**Класс**: `Subscription`
**Добавить поле**:

```python
school = models.ForeignKey(
    'tenants.School',
    on_delete=models.CASCADE,
    null=True, blank=True,
    related_name='subscriptions',
    help_text='Школа, в рамках которой подписка'
)
```

**Команды**:
```bash
python manage.py makemigrations accounts --name add_school_fk_to_subscription
python manage.py migrate accounts
python manage.py test tenants.tests_smoke -v2
```

### Шаг 1.4: Добавить school FK к analytics.ControlPoint

**Файл**: `teaching_panel/analytics/models.py`
**Класс**: `ControlPoint`

```python
school = models.ForeignKey(
    'tenants.School',
    on_delete=models.CASCADE,
    null=True, blank=True,
    related_name='control_points',
    help_text='Школа'
)
```

**Команды**:
```bash
python manage.py makemigrations analytics --name add_school_fk_to_controlpoint
python manage.py migrate analytics
python manage.py test tenants.tests_smoke -v2
```

### Шаг 1.5: Добавить school FK к support.SupportTicket

**Файл**: `teaching_panel/support/models.py`
**Класс**: `SupportTicket`

```python
school = models.ForeignKey(
    'tenants.School',
    on_delete=models.CASCADE,
    null=True, blank=True,
    related_name='support_tickets',
    help_text='Школа отправителя тикета'
)
```

**Команды**:
```bash
python manage.py makemigrations support --name add_school_fk_to_ticket
python manage.py migrate support
python manage.py test tenants.tests_smoke -v2
```

### Шаг 1.6: Добавить school FK к finance.StudentFinancialProfile

**Файл**: `teaching_panel/finance/models.py`
**Класс**: `StudentFinancialProfile`

```python
school = models.ForeignKey(
    'tenants.School',
    on_delete=models.CASCADE,
    null=True, blank=True,
    related_name='financial_profiles',
    help_text='Школа'
)
```

**Команды**:
```bash
python manage.py makemigrations finance --name add_school_fk_to_profile
python manage.py migrate finance
python manage.py test tenants.tests_smoke -v2
```

### Шаг 1.7: Добавить school FK к bot.ScheduledMessage

**Файл**: `teaching_panel/bot/models.py`
**Класс**: `ScheduledMessage`

```python
school = models.ForeignKey(
    'tenants.School',
    on_delete=models.CASCADE,
    null=True, blank=True,
    related_name='scheduled_messages',
    help_text='Школа'
)
```

**Команды**:
```bash
python manage.py makemigrations bot --name add_school_fk_to_scheduled_message
python manage.py migrate bot
python manage.py test tenants.tests_smoke -v2
```

### Шаг 1.8: Data Migration — привязать существующие данные к Default School

**КРИТИЧЕСКИ ВАЖНЫЙ ШАГ! Без него все FK = NULL → фильтрация сломает всё.**

**Файл**: `teaching_panel/tenants/migrations/0003_backfill_school_fk.py` (создать)

```python
"""
Data migration: привязка ВСЕХ существующих записей к Default School.

Безопасность:
- Только UPDATE, никаких DELETE/DROP
- Обратимая: reverse ставит school=NULL
- Работает с NULL FK (не ломает записи без школы)
"""
from django.db import migrations

def backfill_school_fk(apps, schema_editor):
    School = apps.get_model('tenants', 'School')
    default_school = School.objects.filter(is_default=True).first()
    if not default_school:
        return

    models_to_update = [
        ('schedule', 'Group'),
        ('homework', 'Homework'),
        ('accounts', 'Subscription'),
        ('analytics', 'ControlPoint'),
        ('support', 'SupportTicket'),
        ('finance', 'StudentFinancialProfile'),
        ('bot', 'ScheduledMessage'),
    ]

    for app_label, model_name in models_to_update:
        try:
            Model = apps.get_model(app_label, model_name)
            updated = Model.objects.filter(school__isnull=True).update(school=default_school)
            print(f'  → {app_label}.{model_name}: обновлено {updated} записей')
        except Exception as e:
            print(f'  ⚠ {app_label}.{model_name}: {e}')

def reverse_backfill(apps, schema_editor):
    """Обратная миграция: убрать school FK (поставить NULL)."""
    models_to_update = [
        ('schedule', 'Group'),
        ('homework', 'Homework'),
        ('accounts', 'Subscription'),
        ('analytics', 'ControlPoint'),
        ('support', 'SupportTicket'),
        ('finance', 'StudentFinancialProfile'),
        ('bot', 'ScheduledMessage'),
    ]
    for app_label, model_name in models_to_update:
        try:
            Model = apps.get_model(app_label, model_name)
            Model.objects.all().update(school=None)
        except Exception:
            pass

class Migration(migrations.Migration):
    dependencies = [
        ('tenants', '0002_create_default_school'),
        # Зависимости от миграций добавления FK:
        ('schedule', 'XXXX_add_school_fk_to_group'),  # ← подставить реальный номер
        ('homework', 'XXXX_add_school_fk_to_homework'),
        ('accounts', 'XXXX_add_school_fk_to_subscription'),
        ('analytics', 'XXXX_add_school_fk_to_controlpoint'),
        ('support', 'XXXX_add_school_fk_to_ticket'),
        ('finance', 'XXXX_add_school_fk_to_profile'),
        ('bot', 'XXXX_add_school_fk_to_scheduled_message'),
    ]
    operations = [
        migrations.RunPython(backfill_school_fk, reverse_backfill),
    ]
```

**ВАЖНО**: Подставить реальные номера миграций (0029, 0030 и т.д.) — зависит от текущего состояния.

**Команды**:
```bash
python manage.py migrate tenants
python manage.py test tenants -v2
python manage.py test tenants.tests_smoke -v2
```

### Шаг 1.9: Тесты Phase 1

**Файл**: `teaching_panel/tenants/tests_phase1.py` (создать)

```
TEST_1_01: Group.school поле существует, nullable, FK на School
TEST_1_02: Homework.school поле существует, nullable, FK на School
TEST_1_03: Subscription.school поле существует
TEST_1_04: ControlPoint.school поле существует
TEST_1_05: SupportTicket.school поле существует
TEST_1_06: StudentFinancialProfile.school поле существует
TEST_1_07: ScheduledMessage.school поле существует
TEST_1_08: Все существующие Group привязаны к default school (school != NULL)
TEST_1_09: Все существующие Homework привязаны к default school
TEST_1_10: Создание новой Group без school → OK (null=True работает)
TEST_1_11: Создание новой Group с school → OK, FK работает
TEST_1_12: Удаление School → каскадное удаление Group (on_delete=CASCADE)
TEST_1_13: API GET /api/schedule/groups/ → ВСЕ группы возвращаются (изоляция выключена)
TEST_1_14: API POST /api/schedule/groups/ → группа создаётся (без school)
TEST_1_15: Smoke тесты всё ещё проходят
```

**Запуск**: `python manage.py test tenants.tests_phase1 -v2`
**Критерий**: ВСЕ 15 тестов зелёные

### Шаг 1.10: Финальная проверка Phase 1

```bash
python manage.py test tenants tenants.tests_smoke tenants.tests_phase1 -v2
python manage.py test schedule homework accounts analytics finance support bot -v2
python manage.py check --deploy
```

**Коммит**: `git commit -m "Phase 1: Add school FK to 7 core models + data backfill"`

---

## ФАЗА 2: TENANT ISOLATION В VIEWSETS (2-3 часа)
> Цель: Активировать фильтрацию — данные школы A не видны школе B

### Стратегия: guard через feature flag

```python
# В tenant_mixins.py:
if not settings.TENANT_ISOLATION_ENABLED:
    return qs  # Pass-through, ничего не фильтрует
```

### Шаг 2.1: Обновить TenantViewSetMixin с feature flag

**Файл**: `teaching_panel/core/tenant_mixins.py`

Раскомментировать логику фильтрации, обернув в `if settings.TENANT_ISOLATION_ENABLED`.

```python
def get_queryset(self):
    qs = super().get_queryset()

    if not settings.TENANT_ISOLATION_ENABLED:
        return qs

    school = getattr(self.request, 'school', None)
    if not school:
        return qs

    if hasattr(qs.model, 'school'):
        qs = qs.filter(school=school)
    elif hasattr(qs.model, 'teacher'):
        from tenants.models import SchoolMembership
        teacher_ids = SchoolMembership.objects.filter(
            school=school, role__in=['owner', 'admin', 'teacher'], is_active=True,
        ).values_list('user_id', flat=True)
        qs = qs.filter(teacher_id__in=teacher_ids)

    return qs

def perform_create(self, serializer):
    if settings.TENANT_ISOLATION_ENABLED:
        school = getattr(self.request, 'school', None)
        if school and hasattr(serializer.Meta.model, 'school'):
            serializer.save(school=school)
            return

    super().perform_create(serializer)
```

**Проверка**: `python manage.py test tenants.tests_smoke -v2` — smoke тесты зелёные (flag=False)

### Шаг 2.2: Подключить TenantViewSetMixin к schedule ViewSets

**Файл**: `teaching_panel/schedule/views.py`

Для КАЖДОГО ViewSet:
1. Добавить import: `from core.tenant_mixins import TenantViewSetMixin`
2. Добавить mixin **первым** в цепочке наследования:

```python
# БЫЛО:
class GroupViewSet(viewsets.ModelViewSet):

# СТАЛО:
class GroupViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
```

**Список ViewSets для обновления**:
- `GroupViewSet` (line ~174)
- `LessonViewSet` (line ~423) — у Lesson нет school FK, но есть teacher → membership фильтрация
- `AttendanceViewSet` (line ~2095) — через teacher
- `ZoomAccountViewSet` (line ~2138) — **НЕ добавлять** (глобальный пул)
- `RecurringLessonViewSet` (line ~2182) — через teacher
- `IndividualInviteCodeViewSet` (line ~3464) — через teacher
- `LessonMaterialViewSet` (line ~3712) — через teacher

**Проверка ПОСЛЕ каждого ViewSet**:
```bash
python manage.py test tenants.tests_smoke -v2
python manage.py test schedule -v2
```

### Шаг 2.3: Подключить TenantViewSetMixin к homework ViewSets

**Файл**: `teaching_panel/homework/views.py`

- `HomeworkViewSet` (line ~17)
- `StudentSubmissionViewSet` (line ~1215)

```bash
python manage.py test tenants.tests_smoke -v2
python manage.py test homework -v2
```

### Шаг 2.4: Подключить TenantViewSetMixin к accounts ViewSets

**Файл**: `teaching_panel/accounts/*.py` (найти все ViewSets)

Кандидаты: `ChatViewSet`, `MessageViewSet`, `AttendanceRecordViewSet`

```bash
python manage.py test tenants.tests_smoke -v2
```

### Шаг 2.5: Подключить к analytics, finance, support, bot ViewSets

Каждый app — отдельный подшаг с тестированием.

### Шаг 2.6: Тесты Phase 2

**Файл**: `teaching_panel/tenants/tests_phase2.py` (создать)

```
--- С TENANT_ISOLATION_ENABLED = False (текущее) ---
TEST_2_01: GroupViewSet.get_queryset() возвращает ВСЕ группы (flag off)
TEST_2_02: HomeworkViewSet.get_queryset() возвращает ВСЕ ДЗ (flag off)
TEST_2_03: perform_create() НЕ ставит school (flag off)

--- С TENANT_ISOLATION_ENABLED = True ---
TEST_2_04: Создать 2 школы (A и B) + по user + по группе в каждой
TEST_2_05: Request от user школы A → видит только группы школы A
TEST_2_06: Request от user школы B → видит только группы школы B
TEST_2_07: Superuser → видит ВСЕ группы (нет фильтрации для admin)
TEST_2_08: Request без school (localhost) → видит всё (default school)
TEST_2_09: perform_create с school → Group.school автоматически = request.school
TEST_2_10: Lesson ViewSet → через teacher membership → изоляция работает
TEST_2_11: Homework ViewSet → через school FK → изоляция работает
TEST_2_12: Перекрёстная проверка: user A не видит ДЗ школы B
TEST_2_13: SchoolMembership с is_active=False → пользователь не видит данные
TEST_2_14: Smoke тесты проходят с flag=True на default school
```

**Запуск**: `python manage.py test tenants.tests_phase2 -v2`
**Критерий**: ВСЕ 14 тестов зелёные

### Шаг 2.7: Финальная проверка Phase 2

```bash
# С flag=False (production-safe):
python manage.py test -v2

# С flag=True (tenant isolation):
TENANT_ISOLATION_ENABLED=1 python manage.py test tenants.tests_phase2 -v2
```

**Коммит**: `git commit -m "Phase 2: TenantViewSetMixin active with feature flag"`

---

## ФАЗА 3: REGISTRATION + MEMBERSHIP (1-2 часа)
> Цель: Новые пользователи автоматически привязываются к школе

### Шаг 3.1: Обновить RegisterView

**Файл**: `teaching_panel/accounts/jwt_views.py`
**Класс**: `RegisterView.post()`

**Добавить ПОСЛЕ создания пользователя** (после `user = User.objects.create_user(...)`:

```python
# === Multi-Tenant: привязка к школе ===
school = getattr(request, 'school', None)
if school:
    from tenants.models import SchoolMembership
    # Проверка лимита
    if role == 'student':
        current_count = SchoolMembership.objects.filter(
            school=school, role='student', is_active=True
        ).count()
        if current_count >= school.max_students:
            # НЕ блокируем регистрацию — но логируем
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'School {school.slug} exceeded max_students limit')
    
    membership_role = role  # student/teacher → as-is
    SchoolMembership.objects.get_or_create(
        school=school,
        user=user,
        defaults={'role': membership_role}
    )
```

**Проверка**:
```bash
python manage.py test tenants.tests_smoke -v2
```

### Шаг 3.2: Тесты Phase 3

**Файл**: `teaching_panel/tenants/tests_phase3.py` (создать)

```
TEST_3_01: Register на 127.0.0.1 → user создан, SchoolMembership к default school
TEST_3_02: Register на school-A поддомен → SchoolMembership к school A
TEST_3_03: Register как student → role='student' в membership
TEST_3_04: Register как teacher → role='teacher' в membership
TEST_3_05: Register дважды на одну школу → unique_together не ломается (get_or_create)
TEST_3_06: Register на школу с max_students=0 → user создан (не блокируем), лог warning
TEST_3_07: Login существующего пользователя → membership НЕ создаётся повторно
TEST_3_08: Smoke тесты проходят
```

**Запуск**: `python manage.py test tenants.tests_phase3 -v2`

### Шаг 3.3: Обновить MeView — включить school info

**Файл**: `teaching_panel/accounts/api_views.py` (или где MeView)

В response `GET /api/me/` добавить:

```python
# Текущая школа
school = getattr(request, 'school', None)
data['school'] = school.to_frontend_config() if school else None
data['school_membership'] = None
if school:
    membership = SchoolMembership.objects.filter(
        school=school, user=request.user
    ).first()
    if membership:
        data['school_membership'] = {
            'role': membership.role,
            'joined_at': membership.joined_at.isoformat(),
        }
```

**Проверка**: `python manage.py test tenants.tests_smoke -v2`

**Коммит**: `git commit -m "Phase 3: Registration creates SchoolMembership, /me/ returns school info"`

---

## ФАЗА 4: PAYMENT SERVICE PER-SCHOOL (2-3 часа)
> Цель: Платежи идут на аккаунт школы, а не глобальный

### Шаг 4.1: Рефакторинг PaymentService — принимать school

**Файл**: `teaching_panel/accounts/payments_service.py`

**Стратегия**: НЕ ломать существующий API. Добавить опциональный параметр `school=None`.

```python
class PaymentService:
    @staticmethod
    def create_subscription_payment(user, plan, school=None):
        # Если school передан и у него свои credentials:
        if school:
            creds = school.get_payment_credentials()
        else:
            creds = {
                'provider': 'yookassa',
                'account_id': settings.YOOKASSA_ACCOUNT_ID,
                'secret_key': settings.YOOKASSA_SECRET_KEY,
            }
        
        # Для YooKassa: использовать HTTP API напрямую вместо SDK singleton
        # SDK .configure() меняет глобальное состояние — нельзя для per-school
        
        if creds['provider'] == 'yookassa':
            return PaymentService._create_yookassa_payment(user, plan, creds, school)
        else:
            return PaymentService._create_tbank_payment(user, plan, creds, school)
    
    @staticmethod
    def _create_yookassa_payment(user, plan, creds, school=None):
        import requests
        import json

        # return_url: школа или платформа
        return_url = school.get_frontend_url() + '/teacher/subscription' if school else settings.FRONTEND_URL + '/teacher/subscription'
        
        # description: имя школы
        school_name = school.name if school else 'Lectio Space'
        
        payload = {
            'amount': {'value': str(plan['price']), 'currency': 'RUB'},
            'confirmation': {'type': 'redirect', 'return_url': return_url},
            'description': f'Подписка {school_name} — {plan["name"]}',
            'metadata': {
                'user_id': str(user.id),
                'plan': plan['key'],
                'school_id': str(school.id) if school else '',
            },
            'capture': True,
        }
        
        response = requests.post(
            'https://api.yookassa.ru/v3/payments',
            json=payload,
            auth=(creds['account_id'], creds['secret_key']),
            headers={'Idempotence-Key': str(uuid.uuid4()), 'Content-Type': 'application/json'},
        )
        # ... обработка response
```

**ВАЖНО**: Оставить работающий mock-mode для development.

### Шаг 4.2: Обновить webhook — определять школу из metadata

**Файл**: `teaching_panel/accounts/payments_views.py`

```python
def yookassa_webhook(request):
    # ... парсинг payload ...
    
    metadata = payment_data.get('metadata', {})
    school_id = metadata.get('school_id')
    
    if school_id:
        from tenants.models import School
        school = School.objects.filter(id=school_id).first()
    else:
        school = None
    
    # Привязать Subscription к школе
    subscription.school = school
    subscription.save()
```

### Шаг 4.3: Обновить SubscriptionView — передавать school

**Файл**: `teaching_panel/accounts/subscriptions_views.py`

```python
def create_payment(request):
    school = getattr(request, 'school', None)
    result = PaymentService.create_subscription_payment(
        user=request.user,
        plan=plan_data,
        school=school,  # ← НОВЫЙ параметр
    )
```

### Шаг 4.4: Тесты Phase 4

**Файл**: `teaching_panel/tenants/tests_phase4.py` (создать)

```
TEST_4_01: PaymentService.create_subscription_payment(school=None) → работает как раньше
TEST_4_02: PaymentService.create_subscription_payment(school=school_A) → использует creds школы A
TEST_4_03: get_payment_credentials() с пустыми creds → fallback на PLATFORM_CONFIG
TEST_4_04: get_payment_credentials() с заполненными creds → использует школьные
TEST_4_05: Mock mode по-прежнему работает без YOOKASSA_ACCOUNT_ID
TEST_4_06: Webhook с school_id в metadata → Subscription.school = school
TEST_4_07: Webhook без school_id → Subscription.school = None (обратная совместимость)
TEST_4_08: return_url использует school.get_frontend_url() если school
TEST_4_09: description содержит имя школы
TEST_4_10: Smoke тесты проходят
```

**Коммит**: `git commit -m "Phase 4: PaymentService per-school with HTTP API"`

---

## ФАЗА 5: FRONTEND DYNAMIC BRANDING (2-3 часа)
> Цель: Frontend загружает конфиг школы из API и применяет брендинг

### Шаг 5.1: Создать SchoolConfigContext

**Файл**: `frontend/src/contexts/SchoolConfigContext.js` (создать)

```javascript
import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient } from '../apiService';
import brandConfig from '../config/brandConfig'; // fallback

const SchoolConfigContext = createContext(null);

export function SchoolConfigProvider({ children }) {
    const [config, setConfig] = useState(brandConfig); // default = static config
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        apiClient.get('/school/config/')
            .then(res => {
                setConfig(mergeWithDefaults(res.data, brandConfig));
            })
            .catch(() => {
                // Fallback: использовать статический brandConfig
            })
            .finally(() => setLoading(false));
    }, []);

    return (
        <SchoolConfigContext.Provider value={{ config, loading }}>
            {children}
        </SchoolConfigContext.Provider>
    );
}

export function useSchoolConfig() {
    const ctx = useContext(SchoolConfigContext);
    return ctx?.config || brandConfig;
}

function mergeWithDefaults(apiConfig, defaults) {
    return {
        ...defaults,
        name: apiConfig.name || defaults.name,
        // ... merge логика
        colors: {
            primary: apiConfig.primary_color || defaults.colors.primary,
            secondary: apiConfig.secondary_color || defaults.colors.secondary,
        },
        logo: apiConfig.logo_url || defaults.logo,
        favicon: apiConfig.favicon_url || defaults.favicon,
        telegram: {
            ...defaults.telegram,
            botUsername: apiConfig.telegram_bot_username || defaults.telegram.botUsername,
        },
        features: apiConfig.features || defaults.features || {},
    };
}
```

### Шаг 5.2: Обернуть App.js в SchoolConfigProvider

**Файл**: `frontend/src/App.js`

```javascript
import { SchoolConfigProvider } from './contexts/SchoolConfigContext';

function App() {
    return (
        <SchoolConfigProvider>
            {/* ... existing routes ... */}
        </SchoolConfigProvider>
    );
}
```

### Шаг 5.3: Обновить Logo.js — использовать useSchoolConfig()

**Файл**: `frontend/src/components/Logo.js`

```javascript
import { useSchoolConfig } from '../contexts/SchoolConfigContext';

function Logo({ size = 40 }) {
    const config = useSchoolConfig();
    // Использовать config.name, config.colors.primary вместо brandConfig
}
```

### Шаг 5.4: Применять CSS переменные из конфига

```javascript
// В SchoolConfigProvider useEffect:
document.documentElement.style.setProperty('--color-primary', config.colors.primary);
document.documentElement.style.setProperty('--color-secondary', config.colors.secondary);

// Favicon
if (config.favicon) {
    const link = document.querySelector("link[rel='icon']") || document.createElement('link');
    link.rel = 'icon';
    link.href = config.favicon;
    document.head.appendChild(link);
}
```

### Шаг 5.5: Тесты Phase 5

Фронтенд тесты (если есть Jest/RTL):

```
TEST_5_01: SchoolConfigProvider рендерится без ошибок
TEST_5_02: useSchoolConfig() возвращает default config если API недоступен
TEST_5_03: useSchoolConfig() возвращает API config после успешной загрузки
TEST_5_04: CSS переменные обновляются после загрузки конфига
TEST_5_05: Logo показывает имя школы из config
TEST_5_06: npm run build — успешно собирается
```

Ручная проверка:
```
MANUAL_01: Открыть localhost:3000 → логотип "Lectio Space"
MANUAL_02: Network tab → GET /api/school/config/ → 200
MANUAL_03: Цвета соответствуют primary_color из default school
```

**Коммит**: `git commit -m "Phase 5: Frontend dynamic branding from API"`

---

## ФАЗА 6: NGINX + DNS + SSL (1-2 часа, сервер)
> Цель: Поддомены *.lectiospace.ru маршрутизируются на наш сервер

### Шаг 6.1: DNS (Cloudflare / регистратор)

```
*.lectiospace.ru → A → <IP сервера>
```

**Проверка**: `nslookup test.lectiospace.ru` → резолвится на IP сервера

### Шаг 6.2: Wildcard SSL через Certbot

```bash
# На сервере:
sudo certbot certonly --manual --preferred-challenges dns \
    -d "*.lectiospace.ru" -d "lectiospace.ru"
```

Или через Cloudflare DNS plugin:
```bash
sudo certbot certonly --dns-cloudflare \
    --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
    -d "*.lectiospace.ru" -d "lectiospace.ru"
```

### Шаг 6.3: Обновить nginx config

**Файл**: на сервере `/etc/nginx/sites-available/lectiospace`

```nginx
server {
    listen 443 ssl http2;
    server_name *.lectiospace.ru lectiospace.ru;

    ssl_certificate /etc/letsencrypt/live/lectiospace.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lectiospace.ru/privkey.pem;

    # ... остальная конфигурация без изменений ...
}
```

**Проверка**:
```bash
sudo nginx -t
sudo systemctl reload nginx
curl -I https://test.lectiospace.ru/api/health/  # → 200
curl -I https://anna.lectiospace.ru/api/school/config/  # → 200, конфиг школы anna
```

### Шаг 6.4: Тесты Phase 6

```
TEST_6_01: curl https://lectiospace.ru/api/health/ → 200
TEST_6_02: curl https://test.lectiospace.ru/api/health/ → 200 (wildcard работает)
TEST_6_03: curl https://anna.lectiospace.ru/api/school/config/ → config школы anna
TEST_6_04: curl https://nonexistent.lectiospace.ru/api/school/config/ → default config
TEST_6_05: SSL сертификат валиден для *.lectiospace.ru
```

**Коммит**: в отдельный деплой через deploy_unified.ps1

---

## ФАЗА 7: SCHOOL OWNER API (2-3 часа)
> Цель: Владелец школы может управлять своей школой через API

### Шаг 7.1: SchoolManagementViewSet

**Файл**: `teaching_panel/tenants/views.py` (дополнить)

Endpoints:
```
PATCH /api/school/          → обновить брендинг (name, colors, logo)
GET   /api/school/members/  → список участников школы
POST  /api/school/members/  → добавить участника (invite)
DELETE /api/school/members/<id>/ → удалить участника
GET   /api/school/stats/    → статистика (students_count, groups_count, revenue)
```

Permission: `school.owner == request.user` или `membership.role in ['owner', 'admin']`

### Шаг 7.2: SchoolOnboarding endpoint

```
POST /api/school/create/ → создать новую школу (только для platform admin или через invite)
```

Поля: `slug`, `name`, `owner_email`, `primary_color`

### Шаг 7.3: Тесты Phase 7

```
TEST_7_01: Owner может PATCH свою школу (name, colors)
TEST_7_02: Non-owner получает 403 на PATCH
TEST_7_03: Owner видит список members своей школы
TEST_7_04: Owner может добавить teacher в школу
TEST_7_05: Owner НЕ может превысить max_teachers
TEST_7_06: Owner видит статистику (count students, groups)
TEST_7_07: Admin platform может создать новую школу через API
TEST_7_08: Smoke тесты проходят
```

**Коммит**: `git commit -m "Phase 7: School Owner management API"`

---

## ФАЗА 8: CELERY + TELEGRAM TENANT-AWARE (2 часа)
> Цель: Фоновые задачи и уведомления учитывают школу

### Шаг 8.1: Utility для tenant-aware tasks

**Файл**: `teaching_panel/tenants/task_utils.py` (создать)

```python
from tenants.middleware import set_current_school, clear_current_school, get_current_school
from tenants.models import School
from functools import wraps

def tenant_task(func):
    """Декоратор: устанавливает school context для Celery task."""
    @wraps(func)
    def wrapper(*args, school_id=None, **kwargs):
        if school_id:
            try:
                school = School.objects.get(id=school_id)
                set_current_school(school)
            except School.DoesNotExist:
                pass
        try:
            return func(*args, **kwargs)
        finally:
            clear_current_school()
    return wrapper
```

### Шаг 8.2: Обновить ключевые tasks

**Приоритетные** (отправляют уведомления):
- `send_lesson_reminder` — добавить `school_id` параметр, использовать `school.telegram_bot_token`
- `schedule_upcoming_lesson_reminders` — фильтровать по school
- `send_recurring_lesson_reminders` — фильтровать по school

**Можно позже** (инфраструктурные):
- `release_stuck_zoom_accounts` — глобальный, OK
- `warmup_zoom_oauth_tokens` — глобальный, OK
- `archive_zoom_recordings` — привязать к school если нужно

### Шаг 8.3: Тесты Phase 8

```
TEST_8_01: tenant_task декоратор устанавливает school context
TEST_8_02: tenant_task декоратор очищает school context после завершения
TEST_8_03: send_lesson_reminder с school_id → использует bot token школы
TEST_8_04: send_lesson_reminder без school_id → использует глобальный bot token
TEST_8_05: Smoke тесты проходят
```

**Коммит**: `git commit -m "Phase 8: Tenant-aware Celery tasks + Telegram"`

---

## ФАЗА 9: ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ (2 часа)
> Цель: End-to-end проверка всей multi-tenant системы

### Шаг 9.1: Полный E2E тест

**Файл**: `teaching_panel/tenants/tests_e2e.py` (создать)

```
TEST_E2E_01: Создать школу "English Anna" (slug=anna, owner=anna_user)
TEST_E2E_02: Создать школу "Math Plus" (slug=math, owner=math_user)
TEST_E2E_03: Register student на anna.lectiospace.ru → SchoolMembership к anna
TEST_E2E_04: Register student на math.lectiospace.ru → SchoolMembership к math
TEST_E2E_05: Anna создаёт группу → Group.school = anna_school
TEST_E2E_06: Math создаёт группу → Group.school = math_school
TEST_E2E_07: Student anna НЕ видит группу Math (с TENANT_ISOLATION_ENABLED=True)
TEST_E2E_08: Student math НЕ видит группу Anna
TEST_E2E_09: Anna создаёт ДЗ → Homework.school = anna_school
TEST_E2E_10: Student anna видит ДЗ anna, НЕ видит ДЗ math
TEST_E2E_11: Anna оплачивает подписку → payment с creds школы anna (mock)
TEST_E2E_12: Webhook обрабатывает платёж → Subscription.school = anna_school
TEST_E2E_13: /api/school/config/ на anna.lectiospace.ru → конфиг школы anna
TEST_E2E_14: /api/school/config/ на math.lectiospace.ru → конфиг школы math
TEST_E2E_15: /api/me/ на anna.lectiospace.ru → включает school info
TEST_E2E_16: Default school (lectiospace) данные НЕ видны на anna/math
TEST_E2E_17: Platform admin (superuser) видит ВСЕ данные
TEST_E2E_18: Деактивация школы (is_active=False) → middleware возвращает None/error
TEST_E2E_19: Все smoke тесты проходят с flag=True
TEST_E2E_20: Все smoke тесты проходят с flag=False (обратная совместимость)
```

### Шаг 9.2: Нагрузочный smoke-тест

```bash
# 1000 запросов к /api/school/config/ с разными поддоменами
ab -n 1000 -c 10 https://lectiospace.ru/api/school/config/
# Latency < 200ms? Cache hit?
```

### Шаг 9.3: Финальная проверка

```bash
# ВСЕ тесты в одном прогоне:
python manage.py test tenants -v2
python manage.py test schedule homework accounts analytics finance support bot -v2

# С включённой изоляцией:
TENANT_ISOLATION_ENABLED=1 python manage.py test tenants -v2
```

---

## ФАЗА 10: ДЕПЛОЙ НА STAGING (1 час)
> Цель: Проверить на staging перед production

### Шаг 10.1: Деплой на staging

```powershell
.\deploy_unified.ps1 -Environment staging -Action full
```

### Шаг 10.2: Ручная проверка на staging

```
STAGING_01: https://stage.lectiospace.ru → работает как раньше
STAGING_02: /api/school/config/ → конфиг default school
STAGING_03: Django Admin → "Школы" → видна Lectio Space
STAGING_04: Создать тестовую школу "Test Anna" (slug=testanna)
STAGING_05: curl https://testanna.stage.lectiospace.ru/api/school/config/ → конфиг testanna
STAGING_06: Регистрация на testanna → SchoolMembership создаётся
STAGING_07: Всё основное работает без регрессий
```

### Шаг 10.3: Включить TENANT_ISOLATION_ENABLED на staging

```bash
# На staging сервере:
echo "TENANT_ISOLATION_ENABLED=1" >> /var/www/teaching-panel-stage/.env
sudo systemctl restart teaching-panel-stage
```

Проверить что изоляция работает.

### Шаг 10.4: Деплой на production

```powershell
# ТОЛЬКО после успешного staging!
.\deploy_unified.ps1 -Environment production -Action full
```

**НЕ включать** `TENANT_ISOLATION_ENABLED=1` на production пока первый амбассадор не готов!

---

## ФАЗА 11: ЗАПУСК ПЕРВОГО АМБАССАДОРА (1 час)
> Цель: Создать реальную школу для первого partner

### Шаг 11.1: Подготовка

1. **DNS**: Добавить A-запись для поддомена (или wildcard уже есть)
2. **Django Admin**: Создать School:
   - slug: `anna` (→ anna.lectiospace.ru)
   - name: "English with Anna"
   - owner: ← создать нового user с role=teacher
   - primary_color: #E91E63 (розовый)
   - telegram_bot_token: (опционально, свой бот)
   - monthly_price: 990
   - revenue_share_percent: 15
3. **SchoolMembership**: owner=anna_user, role=owner

### Шаг 11.2: Включить изоляцию

```bash
echo "TENANT_ISOLATION_ENABLED=1" >> /var/www/teaching_panel/.env
sudo systemctl restart teaching_panel
```

### Шаг 11.3: Пост-запуск мониторинг

```bash
# 15 минут мониторинга:
ssh tp 'sudo tail -f /var/log/teaching_panel/error.log'

# Проверить что lectiospace.ru работает:
curl https://lectiospace.ru/api/health/
curl https://anna.lectiospace.ru/api/school/config/
```

---

## СВОДКА: Файлы для создания/изменения

### Создать (новые файлы):
| # | Файл | Фаза |
|---|------|------|
| 1 | `tenants/tests.py` | 0 |
| 2 | `tenants/tests_smoke.py` | 0 |
| 3 | `tenants/tests_phase1.py` | 1 |
| 4 | `tenants/migrations/0003_backfill_school_fk.py` | 1 |
| 5 | `tenants/tests_phase2.py` | 2 |
| 6 | `tenants/tests_phase3.py` | 3 |
| 7 | `tenants/tests_phase4.py` | 4 |
| 8 | `frontend/src/contexts/SchoolConfigContext.js` | 5 |
| 9 | `tenants/task_utils.py` | 8 |
| 10 | `tenants/tests_e2e.py` | 9 |

### Изменить (существующие файлы):
| # | Файл | Что менять | Фаза |
|---|------|-----------|------|
| 1 | `settings.py` | + TENANT_ISOLATION_ENABLED flag | 0 |
| 2 | `schedule/models.py` | + school FK к Group | 1 |
| 3 | `homework/models.py` | + school FK к Homework | 1 |
| 4 | `accounts/models.py` | + school FK к Subscription | 1 |
| 5 | `analytics/models.py` | + school FK к ControlPoint | 1 |
| 6 | `support/models.py` | + school FK к SupportTicket | 1 |
| 7 | `finance/models.py` | + school FK к StudentFinancialProfile | 1 |
| 8 | `bot/models.py` | + school FK к ScheduledMessage | 1 |
| 9 | `core/tenant_mixins.py` | Раскомментировать + feature flag guard | 2 |
| 10 | `schedule/views.py` | + TenantViewSetMixin к 6 ViewSets | 2 |
| 11 | `homework/views.py` | + TenantViewSetMixin к 2 ViewSets | 2 |
| 12 | `accounts/jwt_views.py` | RegisterView → SchoolMembership | 3 |
| 13 | `accounts/api_views.py` | MeView → school info | 3 |
| 14 | `accounts/payments_service.py` | Per-school credentials | 4 |
| 15 | `accounts/payments_views.py` | Webhook → school_id из metadata | 4 |
| 16 | `accounts/subscriptions_views.py` | Передавать school | 4 |
| 17 | `frontend/src/App.js` | + SchoolConfigProvider wrapper | 5 |
| 18 | `frontend/src/components/Logo.js` | useSchoolConfig() вместо brandConfig | 5 |
| 19 | nginx config (на сервере) | *.lectiospace.ru wildcard | 6 |
| 20 | `tenants/views.py` | + CRUD endpoints для school owner | 7 |
| 21 | `schedule/tasks.py` | Tenant-aware reminders | 8 |

### Общий порядок коммитов:
```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 10 → Phase 11
```

Каждая фаза — отдельный коммит. Каждая фаза заканчивается прогоном ВСЕХ тестов.
Если тесты красные — НЕ переходить к следующей фазе.

---

## ОЦЕНКА ВРЕМЕНИ

| Фаза | Описание | Время |
|------|----------|-------|
| 0 | Подготовка + baseline тесты | 30 мин |
| 1 | School FK + data migration | 2-3 часа |
| 2 | TenantViewSetMixin + ViewSets | 2-3 часа |
| 3 | Registration + Membership | 1-2 часа |
| 4 | PaymentService per-school | 2-3 часа |
| 5 | Frontend dynamic branding | 2-3 часа |
| 6 | Nginx + DNS + SSL | 1-2 часа |
| 7 | School Owner API | 2-3 часа |
| 8 | Celery + Telegram | 2 часа |
| 9 | E2E тестирование | 2 часа |
| 10 | Staging деплой | 1 час |
| 11 | Первый амбассадор | 1 час |
| **ИТОГО** | | **18-26 часов** |
