# Teaching Panel LMS - AI Coding Agent Instructions

## Project Overview

Teaching Panel - это full-stack LMS (Learning Management System) для управления курсами, уроками, домашними заданиями с интеграцией Zoom и Telegram поддержкой.

**Tech Stack:**
- **Backend**: Django 5.2 + Django REST Framework + JWT authentication
- **Frontend**: React 18 + React Router v6
- **Database**: SQLite (dev) / Azure Cosmos DB (production - feature-flagged)
- **Payments**: YooKassa (Russian payment gateway) with webhook integration
- **Task Queue**: Celery + Redis
- **External APIs**: Zoom API (Server-to-Server OAuth), Telegram Bot API, Google Drive API, YooKassa API

## Architecture & Project Structure

```
nat/
├── teaching_panel/              # Django backend
│   ├── accounts/                # Authentication & user management
│   │   ├── jwt_views.py         # JWT token endpoints (login/register/logout)
│   │   ├── serializers.py       # CustomTokenObtainPairSerializer (adds role to JWT)
│   │   ├── security.py          # Rate limiting, login attempt tracking
│   │   ├── models.py            # User, Subscription, Payment models
│   │   ├── subscriptions_views.py  # Subscription CRUD, payment creation
│   │   ├── subscriptions_utils.py  # require_active_subscription decorator
│   │   ├── payments_service.py  # PaymentService (YooKassa integration)
│   │   └── payments_views.py    # yookassa_webhook endpoint
│   ├── schedule/                # Lessons, groups, recurring lessons
│   │   ├── views.py             # LessonViewSet with subscription checks
│   │   └── tasks.py             # Celery tasks (release Zoom accounts, reminders)
│   ├── homework/                # Homework assignments & submissions
│   ├── analytics/               # Gradebook, control points, teacher stats
│   ├── zoom_pool/               # Zoom account pool management
│   ├── support/                 # Telegram support tickets
│   ├── core/                    # Legacy courses module
│   ├── cosmos_db.py             # Azure Cosmos DB singleton client
│   ├── cosmos_repositories.py   # Repository pattern for Cosmos containers
│   └── teaching_panel/
│       ├── settings.py          # **CRITICAL**: Feature flags, CORS, JWT, YooKassa config
│       └── urls.py              # API route mapping
│
└── frontend/                    # React SPA
    ├── src/
    │   ├── apiService.js        # **CORE**: Axios client, token management, auto-refresh
    │   ├── auth.js              # AuthContext: login/register/logout state, subscription loading
    │   ├── App.js               # React Router v6 routes
    │   ├── components/          # Page-level components
    │   │   ├── AuthPage.js      # Unified login/register with bot protection
    │   │   ├── TeacherHomePage.js  # Teacher dashboard with SubscriptionBanner
    │   │   ├── StudentHomePage.js
    │   │   ├── AdminHomePage.js
    │   │   ├── SubscriptionPage.js  # Subscription management page
    │   │   └── SubscriptionBanner.js  # Warning banner for expired subscriptions
    │   ├── modules/             # Feature modules
    │   │   ├── core/            # Zoom integration, calendar
    │   │   ├── homework-analytics/  # Homework constructor (8 question types)
    │   │   ├── Recordings/      # Lesson recording management
    │   │   └── chat/            # (Planned) Real-time chat
    │   └── shared/components/   # Button, Input, Modal, Card, Badge
    ├── setupProxy.js            # Dev proxy: /api → http://127.0.0.1:8000
    └── package.json             # proxy: "http://127.0.0.1:8000"
```

## Critical Workflows

### 1. Starting the Development Environment

**Backend (Django):**
```powershell
cd teaching_panel
# Activate venv from project root
..\venv\Scripts\Activate.ps1
# Start Django dev server
python manage.py runserver
# Server runs on http://127.0.0.1:8000
```

**Frontend (React):**
```powershell
cd frontend
npm start
# Runs on http://localhost:3000
# API calls proxied to Django via setupProxy.js
```

**Important**: Django MUST be running before testing frontend auth - otherwise login will fail with "Invalid response: missing tokens" because React receives HTML 404 instead of JSON.

### 2. Authentication Flow (JWT)

**Login Process:**
1. User submits email + password on `AuthPage.js`
2. `auth.login()` → `apiService.login()` → `POST /api/jwt/token/`
3. Backend (`CaseInsensitiveTokenObtainPairView`) validates credentials
4. Returns `{ access, refresh }` tokens
5. Frontend stores in localStorage: `tp_access_token`, `tp_refresh_token`
6. JWT payload includes custom claim: `role` (student/teacher/admin)
7. `apiService.js` interceptor adds `Authorization: Bearer <access>` to all requests
8. On 401, auto-refresh via `POST /api/jwt/refresh/` with refresh token

**Registration Process:**
1. `AuthPage.js` → `auth.register()` → `POST /api/jwt/register/`
2. Backend creates user + immediately returns tokens
3. Frontend auto-logins after registration (no email verification required)

**Key Files:**
- Backend: `accounts/jwt_views.py` (CaseInsensitiveTokenObtainPairView, RegisterView)
- Frontend: `apiService.js` (login/logout/token refresh), `auth.js` (AuthContext)

### 3. Zoom Pool System

**Why**: Teachers share a pool of Zoom accounts to avoid "one meeting per account" limit.

**Flow**:
1. Teacher creates lesson (`schedule/models.py::Lesson`)
2. When starting lesson: `POST /api/schedule/lessons/{id}/start-new/`
3. Backend finds free Zoom account from `zoom_pool/models.py::ZoomAccount`
4. Creates meeting via Zoom API (Server-to-Server OAuth)
5. Marks account as `in_use=True`, stores `zoom_account` FK on Lesson
6. Celery task `release_stuck_zoom_accounts` auto-releases after lesson ends

**Key Files:**
- `zoom_pool/views.py::ZoomAccountViewSet`
- `schedule/views.py::LessonViewSet.start_new()`
- `schedule/tasks.py::release_stuck_zoom_accounts`

### 4. Azure Cosmos DB Integration (Optional)

**Feature Flag**: `COSMOS_DB_ENABLED=1` in environment

**Why**: Horizontal scaling, global distribution, TTL for analytics events

**Containers**:
- `lessons` (partition key: `/groupId`)
- `zoomAccounts` (partition key: `/zoomAccountId`)
- `analyticsEvents` (partition key: `/eventDate`, TTL: 30 days)

**Pattern**: Repository layer (`cosmos_repositories.py`) abstracts Cosmos SDK.

**Migration**: Run `python manage.py shell -c "import manage_cosmos_migration as m; m.run()"`

**Key Files:**
- `cosmos_db.py` (singleton client)
- `cosmos_repositories.py` (LessonRepository, ZoomAccountRepository)
- `settings.py` (COSMOS_DB_CONTAINERS config)

## Project-Specific Conventions

### Backend Patterns

**1. ViewSet Actions:**
```python
@action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
def custom_action(self, request, pk=None):
    # Custom logic
    return Response({'status': 'ok'})
```

**2. Rate Limiting:**
```python
throttle_classes = [ScopedRateThrottle]
throttle_scope = 'login'  # Defined in settings.py REST_FRAMEWORK.DEFAULT_THROTTLE_RATES
```

**3. Celery Tasks:**
```python
from celery import shared_task

@shared_task
def my_task():
    # Task logic
    pass

# Schedule in settings.py CELERY_BEAT_SCHEDULE
```

### Frontend Patterns

**1. API Calls (Always use apiService.js):**
```javascript
import { apiClient } from '../apiService';

const response = await apiClient.get('/schedule/lessons/');
const data = response.data.results; // DRF pagination
```

**2. Protected Routes:**
```javascript
import { Protected } from './auth';

<Route path="/teacher" element={
  <Protected allowRoles={['teacher', 'admin']}>
    <TeacherDashboard />
  </Protected>
} />
```

**3. Shared Components (Design System):**
```javascript
import { Button, Input, Modal, Card, Badge } from '../shared/components';

<Button variant="primary" onClick={handleSave}>Save</Button>
<Input label="Email" type="email" value={email} onChange={setEmail} />
```

## Common Issues & Solutions

### Issue: "Invalid response: missing tokens" on login

**Причина**: Django server not running or CORS blocking request

**Решение**:
1. Verify Django runs on `http://127.0.0.1:8000`
2. Check `setupProxy.js` proxies `/api` correctly
3. Inspect browser Network tab: response should be JSON, not HTML
4. Check Django logs for CORS errors

### Issue: "Failed to connect" to Zoom API

**Причина**: Wrong credentials or Server-to-Server OAuth not configured

**Решение**:
1. Check `settings.py`: `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`
2. Test token: `POST https://zoom.us/oauth/token?grant_type=account_credentials`
3. Verify webhook secret if using events

### Issue: Celery tasks not running

**Причина**: Redis not running or celery worker not started

**Решение**:
```powershell
# Start Redis (Windows via WSL or Docker)
docker run -d -p 6379:6379 redis

# Start Celery worker (from teaching_panel/)
celery -A teaching_panel worker -l info --pool=solo  # Windows requires --pool=solo

# Start Celery beat scheduler
celery -A teaching_panel beat -l info
```

### Issue: CORS errors on production

**Причина**: Frontend domain not in `CORS_ALLOWED_ORIGINS`

**Решение**:
1. Add domain to `settings.py::CORS_ALLOWED_ORIGINS`
2. Or set env var: `CORS_EXTRA=https://yourfrontend.com`
3. Ensure nginx passes CORS headers

## Testing Commands

```powershell
# Backend tests
cd teaching_panel
python manage.py test

# Specific test
python manage.py test schedule.tests.test_zoom_pool

# Frontend tests
cd frontend
npm test

# Build for production
npm run build
```

## Deployment Notes

**Backend**:
- Use Gunicorn: `gunicorn teaching_panel.wsgi:application --bind 0.0.0.0:8000`
- Set `DEBUG=False`, `SECRET_KEY=<random>`, `ALLOWED_HOSTS=yourdomain.com`
- Migrate DB: `python manage.py migrate`
- Collect static: `python manage.py collectstatic`

**Frontend**:
- Build: `npm run build`
- Serve via Nginx: `root /path/to/build; try_files $uri /index.html;`
- Proxy `/api` to Django backend

**Security**:
- Enable HTTPS: `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`
- Set `CSRF_TRUSTED_ORIGINS=https://yourdomain.com`
- Rotate JWT secret keys periodically

## Key Environment Variables

```bash
# Django
SECRET_KEY=<random-string>
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname  # Optional (defaults to SQLite)

# Cosmos DB (Optional)
COSMOS_DB_ENABLED=1
COSMOS_DB_URL=https://yourcosmosdb.documents.azure.com:443/
COSMOS_DB_KEY=<primary-key>

# Zoom
ZOOM_ACCOUNT_ID=<account-id>
ZOOM_CLIENT_ID=<client-id>
ZOOM_CLIENT_SECRET=<client-secret>

# Celery / Redis
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
REDIS_URL=redis://127.0.0.1:6379/1

# Email (Optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app-password>

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:3000
```

## Module Ownership (from MASTER_PLAN.md)

- **Core + Zoom + Schedule**: Основной backend (Ты)
- **Homework & Analytics**: Напарник Tihon (8 типов вопросов, автопроверка)
- **Chat System**: Напарник #2 (WebSocket, real-time)

## Useful Commands Reference

```powershell
# Create admin user
python manage.py createsuperuser

# Create test data
python manage.py shell -c "from create_sample_data import run; run()"

# Seed Zoom pool
python manage.py shell -c "from create_load_test_users import seed_zoom_pool; seed_zoom_pool()"

# Migrations
python manage.py makemigrations
python manage.py migrate

# Shell
python manage.py shell

# Check deployment readiness
python manage.py check --deploy
```

## When Making Changes

1. **Backend API changes**: Update serializers → views → urls → test
2. **Frontend new page**: Create component → add route in App.js → link in NavBar
3. **New Celery task**: Define in tasks.py → add to CELERY_BEAT_SCHEDULE if periodic
4. **Database changes**: Always create migrations (`makemigrations`) and run (`migrate`)
5. **Cosmos DB changes**: Update container schema in `settings.py::COSMOS_DB_CONTAINERS`

## Subscription & Payment System

**Business Logic:**
- Single subscription tier with optional storage add-ons
- Blocks access to lessons and recordings when subscription inactive
- Shows banner with payment CTA on teacher dashboard

**Plans:**
- **Monthly**: 990 RUB/month (30 days, 5 GB storage)
- **Yearly**: 9900 RUB/year (365 days, 10 GB storage, 17% discount)
- **Storage**: 20 RUB/GB (permanent addition to extra_storage_gb)

**Payment Flow:**
1. User clicks "Оплатить" on `/teacher/subscription`
2. Frontend → `POST /api/subscription/create-payment/` with `{plan: 'monthly'}`
3. Backend → PaymentService creates YooKassa payment
4. Backend → Returns `{payment_url: 'https://yookassa.ru/...'}`
5. Frontend → `window.location.href = payment_url` (redirect to YooKassa)
6. User pays on YooKassa site
7. YooKassa → `POST /api/payments/yookassa/webhook/` with `{type: 'payment.succeeded'}`
8. Backend → PaymentService activates subscription (`status='active'`, `expires_at=+30 days`)
9. User returns to site → access unblocked

**Access Control:**
- Decorator: `@require_active_subscription` in `accounts/subscriptions_utils.py`
- Applied to: `start()`, `start_new()`, `quick_start()`, `add_recording()`, `teacher_recordings_list()` in `schedule/views.py`
- Logic: Check `subscription.status == 'active'` AND `timezone.now() < subscription.expires_at`
- Response on block: `403 Forbidden` with `{'detail': 'Подписка истекла'}`

**Storage Model:**
- `base_storage_gb`: Plan-based storage (5 GB monthly, 10 GB yearly)
- `extra_storage_gb`: Purchased additional storage
- `used_storage_gb`: Current usage from recordings
- `total_storage_gb`: Property = `base_storage_gb + extra_storage_gb`

**Key Files:**
- Backend: `accounts/payments_service.py` (YooKassa integration), `accounts/payments_views.py` (webhook)
- Frontend: `components/SubscriptionPage.js` (management UI), `components/SubscriptionBanner.js` (warning banner)
- Config: `settings.py` (YOOKASSA_ACCOUNT_ID, YOOKASSA_SECRET_KEY, YOOKASSA_WEBHOOK_SECRET)

**Mock Mode:**
- When `YOOKASSA_ACCOUNT_ID` not set → PaymentService returns mock URLs
- Enables frontend development without real credentials

**Docs:** See `YOOKASSA_INTEGRATION_GUIDE.md` for full documentation, `YOOKASSA_QUICK_START.md` for setup.

## Emergency Debugging

If система полностью сломана:

1. **Check Django logs** (terminal where `runserver` runs)
2. **Check browser console** (F12) for frontend errors
3. **Verify tokens**: `localStorage.getItem('tp_access_token')` in console
4. **Test backend directly**: `curl http://127.0.0.1:8000/api/me/ -H "Authorization: Bearer <token>"`
5. **Check Celery logs** if background tasks involved
6. **Restart everything**: Kill all Python/Node processes, restart Django + React

---

**Last Updated**: November 29, 2025
