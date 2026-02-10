# Multi-Tenant Architecture Analysis Report

**Дата**: 7 февраля 2026  
**Проект**: Teaching Panel LMS → SaaS-платформа для штамповки онлайн-школ  
**Цель**: Превратить единый продукт в движок, на котором за 1-2 дня создаётся новая школа для любого репетитора  

---

## Executive Summary

| Параметр | Значение |
|----------|----------|
| **Текущая готовность к multi-tenant** | **~15%** |
| **Общее количество моделей** | **80** (в 11 Django apps) |
| **Моделей, требующих `school` FK** | **~55** |
| **Хардкодов бренда в frontend** | **~90+** мест |
| **Celery задач для переписывания** | **44 из 48** |
| **Времени до MVP (1 пилотная школа)** | **4-6 недель** (1 разработчик) |
| **Времени до production SaaS** | **10-14 недель** |
| **Рекомендуемый подход** | **Shared DB + Tenant FK** (не schema-per-tenant) |
| **Критический блокер** | **SQLite → PostgreSQL** обязательна |

---

## 1. Текущая архитектура (что есть)

### 1.1 Backend: 80 моделей в 11 Django apps

| App | Модели | Ключевые |
|-----|--------|----------|
| **accounts** | 28 | CustomUser, Subscription, Payment, Chat, NotificationSettings, ReferralLink |
| **schedule** | 16 | Group, Lesson, LessonRecording, RecurringLesson, Attendance, LessonMaterial |
| **homework** | 9 | Homework, Question, Choice, StudentSubmission, Answer |
| **analytics** | 4 | ControlPoint, ControlPointResult, StudentAIReport, StudentBehaviorReport |
| **zoom_pool** | 2 | ZoomAccount, ZoomPoolUsageMetrics |
| **support** | 4 | SupportTicket, SupportMessage, SystemStatus, QuickSupportResponse |
| **core** | 2 | Course (legacy), AuditLog |
| **bot** | 4 | ScheduledMessage, BroadcastLog, MessageTemplate, BroadcastRateLimit |
| **finance** | 2 | StudentFinancialProfile, Transaction |
| **market** | 2 | Product, MarketOrder |
| **concierge** | 7 | Conversation, Message, KnowledgeDocument, KnowledgeChunk, ActionDefinition, ActionExecution, ConversationMetrics |

### 1.2 Связи

- **CustomUser** — центральный хаб, на него ссылаются **60+** FK и M2M из всех apps
- **9 OneToOne** связей к User (Subscription, NotificationSettings, IndividualStudent, TeacherStorageQuota, MiroUserToken...)
- **32 unique constraints** (unique_together + UniqueConstraint) — часть из них потребует добавления `school_id`
- **3 модели-синглтона** (SystemSettings, SystemStatus, ZoomPoolUsageMetrics) — needs per-tenant

### 1.3 Дублирующиеся модели (техдолг)

| Дубликат | Где | Действие |
|----------|-----|---------|
| ZoomAccount | schedule + zoom_pool | Удалить legacy из schedule |
| AuditLog | schedule + core | Объединить |
| Message | accounts + support + concierge | Оставить (разный контекст) |
| Attendance vs AttendanceRecord | schedule + accounts | Объединить |

### 1.4 Frontend хардкоды

| Категория | Количество мест | Приоритет |
|-----------|----------------|-----------|
| Бренд "Lectio Space" в UI текстах | ~25 | **P0** |
| Бренд в meta/PWA (title, manifest) | ~8 | **P0** |
| Логотип (Logo.js, SVG, favicon) | ~5 файлов | **P0** |
| Хардкод URL (lectiospace.ru, t.me боты) | ~12 | **P0** |
| Бренд-цвета мимо CSS-переменных | ~40+ мест | **P1** |
| localStorage с prefix tp_/lectio_ | ~15 ключей | **P1** |
| Google Fonts хардкод | ~10 мест | **P2** |
| Русские тексты (нужна i18n) | **Сотни** | **P3** (позже) |
| Telegram bot ссылки | ~5 | **P1** |
| Feature flags с хардкод конфигами | 4 окружения | **P1** |

### 1.5 Инфраструктура

| Компонент | Текущее состояние | Для multi-tenant |
|-----------|-------------------|-----------------|
| **Database** | SQLite (production!) | PostgreSQL **обязательно** |
| **CORS/Hosts** | Хардкод в env vars | Динамический через TenantMiddleware |
| **YooKassa** | Глобальный singleton | Per-tenant credentials через модель |
| **Telegram боты** | 1 бот на всех | Per-tenant боты |
| **GDrive** | 1 аккаунт | Per-tenant OAuth |
| **Zoom** | Pool ZoomAccounts | Per-tenant credentials (уже есть per-teacher!) |
| **Celery tasks** | 48 задач, все глобальные | 44 нужно сделать tenant-aware |
| **Django signals** | 12 signals, все глобальные | Все нужен tenant контекст |
| **Deploy** | SSH PowerShell script | Docker/K8s или shared instance |

---

## 2. Что нужно создать (Gap Analysis)

### 2.1 Новые модели (P0)

```python
# teaching_panel/tenants/models.py (НОВОЕ APP)

class School(models.Model):
    """Tenant/школа — главная модель multi-tenant"""
    # === Идентификация ===
    slug = CharField(max_length=50, unique=True, db_index=True)  # "english-anna"
    name = CharField(max_length=200)  # "Английский с Анной"
    
    # === Владелец ===
    owner = OneToOneField('accounts.CustomUser', CASCADE, related_name='owned_school')
    
    # === Брендинг ===
    logo_url = URLField(blank=True)
    favicon_url = URLField(blank=True)
    primary_color = CharField(max_length=7, default='#4F46E5')
    secondary_color = CharField(max_length=7, default='#7C3AED')
    font_family = CharField(max_length=100, default='Plus Jakarta Sans')
    
    # === Домены ===
    subdomain = CharField(max_length=50, unique=True)  # "anna" → anna.lectiospace.ru
    custom_domain = CharField(max_length=200, blank=True, unique=True, null=True)  # anna-english.com
    
    # === Интеграции ===
    yookassa_account_id = CharField(max_length=100, blank=True)
    yookassa_secret_key = CharField(max_length=200, blank=True)  # encrypted!
    tbank_terminal_key = CharField(max_length=100, blank=True)
    tbank_password = CharField(max_length=100, blank=True)  # encrypted!
    telegram_bot_token = CharField(max_length=200, blank=True)  # encrypted!
    telegram_bot_username = CharField(max_length=100, blank=True)
    gdrive_credentials_json = TextField(blank=True)  # encrypted JSON
    gdrive_root_folder_id = CharField(max_length=100, blank=True)
    
    # === Тарифы для учеников этой школы ===
    monthly_price = DecimalField(max_digits=10, decimal_places=2, default=990)
    yearly_price = DecimalField(max_digits=10, decimal_places=2, default=9900)
    currency = CharField(max_length=3, default='RUB')
    
    # === Revenue Share ===
    revenue_share_percent = IntegerField(default=15)  # % владельцу школы
    
    # === Feature Flags (per-tenant) ===
    zoom_enabled = BooleanField(default=True)
    google_meet_enabled = BooleanField(default=False)
    gdrive_enabled = BooleanField(default=False)
    homework_enabled = BooleanField(default=True)
    recordings_enabled = BooleanField(default=True)
    finance_enabled = BooleanField(default=False)
    concierge_enabled = BooleanField(default=False)
    telegram_bot_enabled = BooleanField(default=False)
    
    # === Лимиты ===
    max_students = IntegerField(default=100)
    max_groups = IntegerField(default=20)
    max_teachers = IntegerField(default=5)
    max_storage_gb = IntegerField(default=50)
    
    # === Статус ===
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    trial_expires_at = DateTimeField(null=True)
    
    class Meta:
        ordering = ['name']


class SchoolMembership(models.Model):
    """Связь User ↔ School (user может быть в нескольких школах)"""
    user = ForeignKey('accounts.CustomUser', CASCADE, related_name='school_memberships')
    school = ForeignKey(School, CASCADE, related_name='memberships')
    role = CharField(max_length=20, choices=[
        ('owner', 'Владелец'),
        ('admin', 'Администратор'),
        ('teacher', 'Учитель'),
        ('student', 'Ученик'),
    ])
    joined_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'school']
```

### 2.2 Новый Middleware (P0)

```python
# teaching_panel/tenants/middleware.py

import threading

_thread_local = threading.local()

def get_current_school():
    return getattr(_thread_local, 'school', None)

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        host = request.get_host().split(':')[0]  # убираем порт
        
        if host.endswith('.lectiospace.ru'):
            slug = host.split('.')[0]
            school = School.objects.filter(slug=slug, is_active=True).first()
        elif School.objects.filter(custom_domain=host).exists():
            school = School.objects.get(custom_domain=host)
        else:
            school = None  # platform admin / API
        
        request.school = school
        _thread_local.school = school
        
        response = self.get_response(request)
        return response
```

### 2.3 TenantManager для автофильтрации (P0)

```python
# teaching_panel/tenants/managers.py

from tenants.middleware import get_current_school

class TenantManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        school = get_current_school()
        if school:
            return qs.filter(school=school)
        return qs


class TenantViewSetMixin:
    """Подмешивать во все ViewSets"""
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request, 'school') and self.request.school:
            return qs.filter(school=self.request.school)
        return qs
    
    def perform_create(self, serializer):
        if hasattr(self.request, 'school') and self.request.school:
            serializer.save(school=self.request.school)
        else:
            super().perform_create(serializer)
```

### 2.4 Модели требующие `school` FK

**P0 — Критичные (без них data leak):**
| Модель | App | Примечание |
|--------|-----|-----------|
| CustomUser | accounts | Через SchoolMembership (M2M) |
| Group | schedule | `school = FK(School)` |
| Lesson | schedule | Наследует через Group → школа |
| LessonRecording | schedule | Наследует через Lesson |
| RecurringLesson | schedule | `school = FK(School)` |
| Homework | homework | `school = FK(School)` |
| Subscription | accounts | `school = FK(School)` |
| Chat | accounts | `school = FK(School)` |
| ZoomAccount (zoom_pool) | zoom_pool | `school = FK(School, null=True)` — shared pool |

**P1 — Важные:**
| Модель | App |
|--------|-----|
| Payment | accounts |
| ControlPoint | analytics |
| SupportTicket | support |
| StudentFinancialProfile | finance |
| Product | market |
| Conversation | concierge |
| ScheduledMessage | bot |

**P2 — Можно отложить (наследуют через FK):**
| Модель | App | Наследует через |
|--------|-----|----------------|
| Attendance | schedule | Lesson → Group → School |
| Answer | homework | Submission → Homework → School |
| Question | homework | Homework → School |
| StudentSubmission | homework | Homework → School |
| Message | accounts | Chat → School |
| NotificationLog | accounts | User → SchoolMembership |

**Синглтоны → Per-Tenant:**
| Модель | Решение |
|--------|---------|
| SystemSettings | Добавить `school = FK(School, unique=True)` |
| SystemStatus | Добавить `school = FK(School)` |
| ZoomPoolUsageMetrics | Добавить `school = FK(School)` |

### 2.5 Frontend: Tenant Config Provider

```javascript
// frontend/src/contexts/TenantContext.js (НОВЫЙ)

const TenantContext = createContext(null);

export function TenantProvider({ children }) {
  const [config, setConfig] = useState(null);
  
  useEffect(() => {
    // Загружаем конфиг школы из API
    fetch('/api/school/config/')
      .then(r => r.json())
      .then(data => {
        setConfig(data);
        // Устанавливаем CSS переменные
        document.documentElement.style.setProperty('--color-primary', data.primary_color);
        document.documentElement.style.setProperty('--color-primary-dark', data.secondary_color);
        document.title = data.name;
        // Favicon
        const link = document.querySelector("link[rel~='icon']");
        if (link && data.favicon_url) link.href = data.favicon_url;
      });
  }, []);
  
  if (!config) return <LoadingScreen />;
  
  return (
    <TenantContext.Provider value={config}>
      {children}
    </TenantContext.Provider>
  );
}

export const useTenant = () => useContext(TenantContext);
```

### 2.6 API endpoint для конфига школы

```python
# teaching_panel/tenants/views.py (НОВЫЙ)

class SchoolConfigView(APIView):
    """Публичный endpoint — конфиг школы для frontend"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        school = request.school
        if not school:
            return Response({
                'name': 'Lectio Space',  # default platform
                'primary_color': '#4F46E5',
                'logo_url': '/static/logo.svg',
            })
        return Response({
            'name': school.name,
            'slug': school.slug,
            'logo_url': school.logo_url,
            'favicon_url': school.favicon_url,
            'primary_color': school.primary_color,
            'secondary_color': school.secondary_color,
            'font_family': school.font_family,
            'owner_name': school.owner.get_full_name(),
            'telegram_bot_username': school.telegram_bot_username,
            'features': {
                'zoom': school.zoom_enabled,
                'google_meet': school.google_meet_enabled,
                'homework': school.homework_enabled,
                'recordings': school.recordings_enabled,
                'finance': school.finance_enabled,
            }
        })
```

---

## 3. Оценка времени (Task → Hours)

### Фаза 1: Фундамент (Недели 1-2)

| # | Задача | Opt | Real | Pess | Зависимости |
|---|--------|-----|------|------|-------------|
| 1.1 | **SQLite → PostgreSQL миграция** | 4h | 8h | 16h | — |
| 1.2 | Создать app `tenants` + модели School, SchoolMembership | 4h | 6h | 8h | — |
| 1.3 | TenantMiddleware + thread-local | 3h | 5h | 8h | 1.2 |
| 1.4 | Добавить `school` FK к Group, Lesson, Homework | 4h | 8h | 12h | 1.2 |
| 1.5 | Добавить `school` FK к Subscription, Payment, Chat | 3h | 6h | 10h | 1.2 |
| 1.6 | Data migration: создать Default School + привязать данные | 4h | 6h | 10h | 1.4, 1.5 |
| 1.7 | TenantViewSetMixin + применить на все ViewSets | 6h | 10h | 16h | 1.3, 1.4 |
| 1.8 | Тестирование изоляции данных | 4h | 8h | 12h | 1.7 |
| | **Итого Фаза 1** | **32h** | **57h** | **92h** | |

### Фаза 2: Интеграции (Недели 3-4)

| # | Задача | Opt | Real | Pess | Зависимости |
|---|--------|-----|------|------|-------------|
| 2.1 | Per-tenant YooKassa credentials | 8h | 16h | 24h | 1.2 |
| 2.2 | Per-tenant T-Bank credentials | 4h | 8h | 12h | 2.1 |
| 2.3 | Webhook handlers с tenant detection | 6h | 10h | 16h | 2.1 |
| 2.4 | Per-tenant Telegram bot creation flow | 8h | 16h | 24h | 1.2 |
| 2.5 | Celery tasks → tenant-aware (44 задачи) | 12h | 20h | 32h | 1.3 |
| 2.6 | Django signals → tenant context (12 signals) | 4h | 6h | 10h | 1.3 |
| 2.7 | Subdomain routing + dynamic CORS/CSRF | 6h | 10h | 16h | 1.3 |
| 2.8 | Тестирование интеграций | 6h | 10h | 16h | All |
| | **Итого Фаза 2** | **54h** | **96h** | **150h** | |

### Фаза 3: White-Label Frontend (Недели 5-6)

| # | Задача | Opt | Real | Pess | Зависимости |
|---|--------|-----|------|------|-------------|
| 3.1 | TenantContext + `/api/school/config/` | 3h | 5h | 8h | 1.2 |
| 3.2 | Logo.js → динамический из TenantContext | 2h | 3h | 5h | 3.1 |
| 3.3 | NavBar → динамический бренд | 2h | 4h | 6h | 3.1 |
| 3.4 | Заменить 25 хардкодов "Lectio Space" | 4h | 6h | 10h | 3.1 |
| 3.5 | Заменить 12 хардкод URL | 3h | 5h | 8h | 3.1 |
| 3.6 | CSS переменные: перевести ~40 мест на var() | 6h | 10h | 16h | 3.1 |
| 3.7 | Dynamic favicon + manifest.json | 2h | 4h | 6h | 3.1 |
| 3.8 | Per-tenant localStorage keys | 3h | 5h | 8h | 3.1 |
| 3.9 | index.html → динамический title/meta | 1h | 2h | 3h | 3.1 |
| 3.10 | Тестирование 2 разных школы в UI | 4h | 6h | 10h | All |
| | **Итого Фаза 3** | **30h** | **50h** | **80h** | |

### Фаза 4: Admin + Онбординг (Неделя 7)

| # | Задача | Opt | Real | Pess | Зависимости |
|---|--------|-----|------|------|-------------|
| 4.1 | Admin Panel: создание школы | 6h | 10h | 16h | 1.2 |
| 4.2 | API: self-service регистрация школы | 8h | 12h | 20h | 4.1 |
| 4.3 | Cloudflare API: авто-создание DNS записей | 4h | 8h | 12h | 4.2 |
| 4.4 | Let's Encrypt wildcard SSL | 3h | 6h | 10h | 4.3 |
| 4.5 | Welcome email + onboarding wizard | 4h | 6h | 10h | 4.2 |
| | **Итого Фаза 4** | **25h** | **42h** | **68h** | |

### Фаза 5: Revenue Share + Billing (Неделя 8)

| # | Задача | Opt | Real | Pess | Зависимости |
|---|--------|-----|------|------|-------------|
| 5.1 | RevenueShare модель + автоматический расчёт | 6h | 10h | 16h | 2.1 |
| 5.2 | Payout API (автовыплата репетитору) | 8h | 16h | 24h | 5.1 |
| 5.3 | Billing dashboard для platform admin | 8h | 12h | 20h | 5.1 |
| 5.4 | Revenue dashboard для owner школы | 6h | 10h | 16h | 5.1 |
| | **Итого Фаза 5** | **28h** | **48h** | **76h** | |

### ИТОГО

| Фаза | Оптимист | Реалист | Пессимист |
|------|----------|---------|-----------|
| 1. Фундамент | 32h (4 дня) | 57h (7 дней) | 92h (12 дней) |
| 2. Интеграции | 54h (7 дней) | 96h (12 дней) | 150h (19 дней) |
| 3. Frontend | 30h (4 дня) | 50h (6 дней) | 80h (10 дней) |
| 4. Онбординг | 25h (3 дня) | 42h (5 дней) | 68h (9 дней) |
| 5. Revenue | 28h (4 дня) | 48h (6 дней) | 76h (10 дней) |
| **TOTAL** | **169h (21 день)** | **293h (37 дней)** | **466h (58 дней)** |

**Реалистичная оценка при полной занятости: ~8-10 недель (1 разработчик).**

---

## 4. Граф зависимостей (Implementation Order)

```
╔══════════════════════════════════════════════════════════╗
║  НЕДЕЛЯ 1: ФУНДАМЕНТ                                    ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  [1.1] SQLite → PostgreSQL                               ║
║     │                                                    ║
║     ▼                                                    ║
║  [1.2] School model + migrations ─────────┐              ║
║     │                                     │              ║
║     ├──▶ [1.3] TenantMiddleware           │              ║
║     │       │                             │              ║
║     ▼       ▼                             │              ║
║  [1.4] school FK на Group/Lesson    [1.5] FK Payment     ║
║     │       │                             │              ║
║     └───────┴────────┐                    │              ║
║                      ▼                    ▼              ║
║              [1.6] Data Migration ◀───────┘              ║
║                      │                                   ║
║                      ▼                                   ║
║              [1.7] TenantViewSetMixin                    ║
║                      │                                   ║
║                      ▼                                   ║
║              [1.8] Тесты изоляции                        ║
╠══════════════════════════════════════════════════════════╣
║  НЕДЕЛЯ 3-4: ИНТЕГРАЦИИ (параллельно)                    ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  [2.1] Per-tenant YooKassa ──▶ [2.3] Webhooks            ║
║  [2.2] Per-tenant T-Bank  ───┘                           ║
║                                                          ║
║  [2.4] Per-tenant Telegram    (параллельно)               ║
║  [2.5] Celery tenant-aware    (параллельно)               ║
║  [2.6] Signals                (параллельно)               ║
║  [2.7] Subdomain routing      (параллельно)               ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║  НЕДЕЛЯ 5-6: WHITE-LABEL FRONTEND                        ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  [3.1] TenantContext ──┬──▶ [3.2] Logo                   ║
║                        ├──▶ [3.3] NavBar                 ║
║                        ├──▶ [3.4] Тексты                 ║
║                        ├──▶ [3.5] URLs                   ║
║                        ├──▶ [3.6] CSS                    ║
║                        └──▶ [3.7-3.9] Meta               ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║  НЕДЕЛЯ 7-8: АВТОМАТИЗАЦИЯ + БИЗНЕС-ЛОГИКА               ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  [4.1-4.5] Онбординг школ                               ║
║  [5.1-5.4] Revenue Share + Billing                       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

---

## 5. MVP Scope (Минимум для первой школы)

### Что НУЖНО для пилота (4-5 недель):

- [x] School model + TenantMiddleware
- [x] school FK на 10 ключевых моделей (Group, Lesson, Homework, Subscription, Chat)
- [x] TenantViewSetMixin на все ViewSets
- [x] Frontend: TenantContext + динамический бренд (лого, цвета, название)
- [x] Per-tenant YooKassa (или единый аккаунт с metadata routing)
- [x] Admin: ручное создание школы через Django Admin
- [x] PostgreSQL миграция

### Что МОЖНО делать вручную на первых 5 школах:

- DNS записи — создавать руками в Cloudflare
- SSL — wildcard cert один раз настроить  
- Telegram бот — создавать через @BotFather руками
- GDrive — пока оставить глобальный
- Onboarding — лично звонить репетитору, настраивать

### Что ОТЛОЖИТЬ до 20+ школ:

- Self-service регистрация школ
- Автоматическое создание DNS + SSL
- Per-tenant GDrive OAuth
- Revenue Share автовыплаты
- i18n (мультиязычность)
- Docker/K8s (пока bare-metal OK)

---

## 6. Риски и их митигация

| # | Риск | Вероятность | Impact | Митигация |
|---|------|-------------|--------|-----------|
| R1 | **Data leak**: ученики видят данные другой школы | High | **Critical** | TenantManager + e2e тесты изоляции + code review каждого `.objects.` call |
| R2 | **Circular imports** при добавлении school FK в 55 моделей | High | Medium | Использовать string references `'tenants.School'` |
| R3 | **YooKassa singleton** не поддерживает per-request credentials | Medium | High | Использовать raw HTTP API вместо SDK singleton |
| R4 | **Celery tasks**: 44 задачи нужно переписать | Medium | High | Обернуть в `@tenant_task` декоратор, итерирующий по школам |
| R5 | **SQLite → PostgreSQL**: потеря данных при миграции | Low | **Critical** | Тройной backup, pgloader, проверка row counts |
| R6 | **Performance**: 200 школ × 500 учеников = 100K users в одной БД | Medium | Medium | PostgreSQL indexes + connection pooling + query optimization |
| R7 | **Unique constraints**: `Group.invite_code` может совпасть между школами | High | Medium | Добавить `school` в unique_together |
| R8 | **Frontend**: сотни мест с хардкодом → пропустить при замене | High | Medium | grep + CI check на "Lectio" в новых коммитах |
| R9 | **Webhook routing**: YooKassa шлёт на 1 URL, как определить tenant? | Medium | High | Передавать `tenant_id` в metadata платежа |
| R10 | **Telegram**: 1 webhook URL per bot → нужен динамический routing | Medium | Medium | `/{school_slug}/webhook/telegram/` URL pattern |

---

## 7. Стоимость инфраструктуры

### Текущая (1 школа):

| Ресурс | Стоимость |
|--------|-----------|
| VPS (2 CPU, 4GB RAM) | ~2000 руб/мес |
| Домен | ~1000 руб/год |
| SSL (Let's Encrypt) | Бесплатно |
| **Итого** | **~2500 руб/мес** |

### На 10 школ (shared instance):

| Ресурс | Стоимость |
|--------|-----------|
| VPS (4 CPU, 8GB RAM) | ~4000 руб/мес |
| PostgreSQL managed | ~3000 руб/мес |
| Redis managed | ~1500 руб/мес |
| Wildcard SSL | Бесплатно |
| Мониторинг (Sentry) | ~2000 руб/мес |
| **Итого** | **~10,500 руб/мес** |
| **Per school** | **~1,050 руб/мес** |

### На 100 школ:

| Ресурс | Стоимость |
|--------|-----------|
| 2× VPS (8 CPU, 16GB RAM, load balanced) | ~16,000 руб/мес |
| PostgreSQL (8GB RAM, 100GB SSD) | ~8,000 руб/мес |
| Redis (4GB) | ~3,000 руб/мес |
| CDN (статика + записи) | ~5,000 руб/мес |
| Backup / S3 storage | ~3,000 руб/мес |
| Мониторинг | ~3,000 руб/мес |
| **Итого** | **~38,000 руб/мес** |
| **Per school** | **~380 руб/мес** |

### На 200 школ:

| Ресурс | Стоимость |
|--------|-----------|
| Kubernetes cluster (3 nodes) | ~30,000 руб/мес |
| PostgreSQL HA (2 replicas) | ~15,000 руб/мес |
| Redis cluster | ~5,000 руб/мес |
| CDN + S3 | ~10,000 руб/мес |
| Monitoring stack | ~5,000 руб/мес |
| **Итого** | **~65,000 руб/мес** |
| **Per school** | **~325 руб/мес** |

### ROI при 100 школах:

```
Доход: 100 школ × 20 учеников × 990 руб × 85% = 1,683,000 руб/мес
Расходы: 38,000 руб/мес (инфра) + 50,000 (поддержка)
Прибыль: ~1,595,000 руб/мес = ~19 млн/год
```

---

## 8. Migration Strategy (SQLite → PostgreSQL → Multi-Tenant)

### Шаг 1: PostgreSQL setup (День 1)

```bash
# На сервере
sudo apt install postgresql-15
sudo -u postgres createdb teaching_panel
sudo -u postgres createuser tp_user -P

# Django settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'teaching_panel',
        'USER': 'tp_user',
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Шаг 2: Миграция данных (День 1)

```bash
# Backup SQLite
cp db.sqlite3 /tmp/backup_before_pg.sqlite3

# Экспорт данных
python manage.py dumpdata --natural-primary --natural-foreign > full_dump.json

# Переключить на PostgreSQL
# (изменить settings.py)

# Создать таблицы
python manage.py migrate

# Импорт
python manage.py loaddata full_dump.json

# Проверить row counts
python manage.py shell -c "
from django.apps import apps
for model in apps.get_models():
    print(f'{model.__name__}: {model.objects.count()}')
"
```

### Шаг 3: Добавить School + миграции (День 2-3)

```python
# 1. Создать Default School
class Migration(migrations.Migration):
    def create_default_school(apps, schema_editor):
        School = apps.get_model('tenants', 'School')
        School.objects.create(
            slug='lectiospace',
            name='Lectio Space',
            # ... defaults
        )
    
    operations = [
        migrations.RunPython(create_default_school),
    ]

# 2. Добавить school FK на Group (nullable сначала)
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='group',
            name='school',
            field=models.ForeignKey('tenants.School', null=True, ...),
        ),
    ]

# 3. Data migration: привязать все группы к Default School
class Migration(migrations.Migration):
    def assign_school(apps, schema_editor):
        Group = apps.get_model('schedule', 'Group')
        School = apps.get_model('tenants', 'School')
        default = School.objects.get(slug='lectiospace')
        Group.objects.filter(school__isnull=True).update(school=default)
    
    operations = [
        migrations.RunPython(assign_school),
    ]

# 4. Сделать school NOT NULL
class Migration(migrations.Migration):
    operations = [
        migrations.AlterField(
            model_name='group',
            name='school',
            field=models.ForeignKey('tenants.School', on_delete=CASCADE),
        ),
    ]
```

### Rollback Plan

```bash
# Если что-то пошло не так на PostgreSQL:
# 1. Вернуть SQLite в settings.py
# 2. Восстановить бэкап
cp /tmp/backup_before_pg.sqlite3 db.sqlite3
sudo systemctl restart teaching_panel
```

---

## 9. Production Readiness Checklist

### Must Have (до первого пилота):

- [ ] PostgreSQL с connection pooling (pgBouncer)
- [ ] TenantMiddleware с тестами
- [ ] Data isolation тесты (e2e: создать 2 школы, проверить что данные не пересекаются)
- [ ] Wildcard SSL (*.lectiospace.ru)
- [ ] Per-tenant YooKassa credentials
- [ ] Frontend white-label (логотип + цвета + название)
- [ ] Django Admin: создание School
- [ ] Monitoring: per-tenant error tracking (Sentry tags)

### Should Have (до 10 школ):

- [ ] Per-tenant Telegram bot
- [ ] Celery tasks tenant-aware
- [ ] Revenue Share dashboard
- [ ] Self-service school creation
- [ ] Automated DNS creation (Cloudflare API)
- [ ] Per-tenant GDrive

### Nice to Have (до 100 школ):

- [ ] Docker контейнеризация
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Load balancer (nginx upstream)
- [ ] Database connection pooling
- [ ] CDN для static + recordings
- [ ] Automated backups per-tenant
- [ ] i18n (мультиязычность)
- [ ] Custom domain support

---

## 10. Рекомендуемый Action Plan

### Прямо сейчас (эта неделя):

1. **Создай `tenants` Django app** с моделью `School`
2. **Создай `TenantMiddleware`** (определение школы по subdomain)
3. **Добавь `school` FK на `Group`** (главная модель расписания) — nullable для обратной совместимости
4. **Создай Default School** через data migration для всех текущих данных

### На следующей неделе:

5. **PostgreSQL миграция** (dumpdata/loaddata)
6. **Добавь `school` FK** на остальные 10 ключевых моделей
7. **TenantViewSetMixin** на все ViewSets

### Через 2 недели:

8. **Frontend TenantContext** + замена хардкодов бренда
9. **Per-tenant YooKassa** (самый сложный кусок)

### Через 4 недели:

10. **Пилот с первым репетитором!**

---

## Ответы на ключевые вопросы

**1. Сколько ТОЧНО часов/дней нужно?**
→ **Реалистично 37 рабочих дней** (8-10 недель при одном разработчике). MVP для первой школы — 4-5 недель.

**2. Какие КОНКРЕТНЫЕ файлы менять?**
→ Backend: 11 models.py, 11 views.py, settings.py, urls.py + новый app `tenants/`
→ Frontend: ~30 компонентов (хардкоды), конфиг файлы, index.html, manifest.json

**3. В каком ПОРЯДКЕ?**
→ PostgreSQL → School model → TenantMiddleware → FK на модели → ViewSetMixin → Frontend white-label → Интеграции → Онбординг

**4. Какие РИСКИ?**
→ #1 Data leak (критический), #2 YooKassa singleton (высокий), #3 44 Celery задачи (средний)

**5. Сколько СТОИТ инфраструктура?**
→ 10 школ: ~10,500 руб/мес. 100 школ: ~38,000 руб/мес. 200 школ: ~65,000 руб/мес.

**6. Можно ли запустить ПИЛОТ за неделю?**
→ **Нет.** Минимум 4 недели для безопасного MVP. Но можно сделать "фейковый пилот" за 2 дня — отдельная инсталляция с ребрендингом (clone repo + change configs), без multi-tenant.

---

*Документ создан автоматически на основе полного анализа кодовой базы Teaching Panel LMS.*
