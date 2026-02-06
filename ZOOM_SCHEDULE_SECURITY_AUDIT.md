# 🔒 АУДИТ БЕЗОПАСНОСТИ: МОДУЛИ `zoom_pool` & `schedule`

**Дата:** 5 февраля 2026  
**Аудитор:** Senior Backend Architect (AI Agent)  
**Scope:** Zoom Pool Management, Timezones, Recurring Lessons, Celery Tasks  
**Цель:** Выявление race conditions, уязвимостей конкурентного доступа, проблем с таймзонами

---

## 📊 EXECUTIVE SUMMARY

**Общая оценка безопасности: 8.0/10** 🟢

Модули `zoom_pool` и `schedule` демонстрируют **хорошую реализацию** механизмов блокировки и обработки ошибок, но имеют **несколько потенциальных проблем**:

### Ключевые находки:

| # | Проблема | Критичность | Статус |
|---|----------|-------------|--------|
| 1 | **Zoom Pool НЕ используется** - код переключён на personal credentials | INFO | ✅ Безопасно |
| 2 | **DST Transition Bug** в `datetime.combine()` | СРЕДНЯЯ 🟡 | Требует фикса |
| 3 | **Нет rate limit на генерацию RecurringLesson** | НИЗКАЯ 🟢 | Мониторинг |
| 4 | **Часть Celery tasks без timeouts** | СРЕДНЯЯ 🟡 | Требует фикса |
| 5 | **Slack в idempotency для release_stuck_zoom_accounts** | НИЗКАЯ 🟢 | Мониторинг |

---

## 1. ZOOM POOL MANAGEMENT

### 1.1 Текущее состояние

**ВАЖНО:** Zoom Pool (`zoom_pool.ZoomAccount`) **НЕ ИСПОЛЬЗУЕТСЯ** в текущей кодовой базе!

```python
# schedule/views.py:1215 - _start_zoom_via_pool()
def _start_zoom_via_pool(self, lesson, user, request):
    """
    Создать Zoom встречу используя личные credentials учителя.
    Если credentials не настроены - возвращаем ошибку.
    """
    # Проверяем наличие личных Zoom credentials у учителя
    if not user.zoom_account_id or not user.zoom_client_id or not user.zoom_client_secret:
        return None, Response({
            'code': 'no_zoom_configured',
            'detail': 'У вас не настроен Zoom аккаунт...'
        })
    
    # Используем ЛИЧНЫЕ credentials учителя, НЕ ПУЛ!
    payload, error_response = self._start_zoom_with_teacher_credentials(lesson, user, request)
```

**Вывод:** Вопрос о 500 одновременных уроках **не актуален** для текущей архитектуры - каждый учитель использует свои личные Zoom credentials.

### 1.2 Анализ кода zoom_pool.ZoomAccount (для справки)

Код пула **готов к использованию** и имеет правильную реализацию:

```python
# zoom_pool/models.py:100-125
def acquire(self):
    """Занять аккаунт для новой встречи."""
    # Block mock accounts in production
    self.validate_for_production()
    
    with transaction.atomic():
        # ✅ Row-level locking предотвращает race conditions
        locked_account = (
            ZoomAccount.objects
            .select_for_update(nowait=False)  # Ждём освобождения lock
            .get(pk=self.pk)
        )
        
        if not locked_account.is_available():
            raise ValueError(f'Zoom account {self.email} недоступен')
        
        # ✅ F() expression для атомарного инкремента
        locked_account.current_meetings = F('current_meetings') + 1
        locked_account.last_used_at = timezone.now()
        locked_account.save(update_fields=['current_meetings', 'last_used_at'])
```

**Оценка реализации пула:**

| Аспект | Реализация | Оценка |
|--------|------------|--------|
| Row-level locking | `select_for_update(nowait=False)` | ✅ Отлично |
| Atomic increment | `F('current_meetings') + 1` | ✅ Отлично |
| Idempotent release | Проверка `current_meetings > 0` | ✅ Отлично |
| Mock credentials check | `validate_for_production()` | ✅ Отлично |
| Teacher affinity | `preferred_teachers` M2M | ✅ Отлично |

**Если бы пул использовался для 500 одновременных уроков:**

1. **Первые N запросов** (N = кол-во аккаунтов × max_concurrent_meetings) успешно получают аккаунты
2. **Остальные запросы** получают `ValueError` (аккаунт недоступен)
3. **Race condition защита** работает - `select_for_update` гарантирует что каждый аккаунт выдаётся только одному учителю

---

## 2. TIMEZONES

### 2.1 Потенциальная проблема: DST Transition Bug

**Риск:** СРЕДНИЙ 🟡  
**Файлы:**
- [`schedule/calendar_helpers.py:74-85`](teaching_panel/schedule/calendar_helpers.py#L74-L85)
- [`schedule/views.py:538-547`](teaching_panel/schedule/views.py#L538-L547)
- [`schedule/tasks.py:329-333`](teaching_panel/schedule/tasks.py#L329-L333)

**Проблемный код:**

```python
# calendar_helpers.py:74
virtual_lesson = {
    'start_time': datetime.combine(
        current_date,
        recurring.start_time,
        tzinfo=timezone.get_current_timezone()  # ❌ Проблема!
    ),
}

# views.py:538
start_local = timezone.make_aware(
    datetime.combine(current_date, rl.start_time),
    timezone.get_current_timezone()
)
```

**В чём проблема:**

При переходе на летнее/зимнее время (DST) `datetime.combine()` с `tzinfo` может создать **несуществующее** или **неоднозначное** время:

```python
# Пример: Переход на летнее время (Москва, 31 марта 2026, 02:00 → 03:00)
# Время 02:30 НЕ СУЩЕСТВУЕТ в этот день!

from datetime import datetime, time, date
from pytz import timezone as pytz_tz

msk = pytz_tz('Europe/Moscow')
dt = datetime.combine(date(2026, 3, 31), time(2, 30), tzinfo=msk)
# Результат: datetime(2026, 3, 31, 2, 30, tzinfo=<DstTzInfo 'Europe/Moscow' MSK+3:00:00 STD>)
# ❌ Время 02:30 сдвинется или вызовет ошибку!
```

**Правильный подход:**

```python
# ✅ Используем localize() от pytz или fold от Python 3.6+
from pytz import timezone as pytz_tz

def safe_combine_datetime(date_part, time_part, tz):
    """Безопасное объединение даты и времени с учётом DST."""
    naive_dt = datetime.combine(date_part, time_part)
    
    try:
        # Пробуем localize (pytz) - правильно обрабатывает DST
        return tz.localize(naive_dt, is_dst=None)
    except Exception:
        # Если время неоднозначно - выбираем стандартное (не летнее)
        return tz.localize(naive_dt, is_dst=False)
```

**Влияние:**
- Урок, запланированный на 02:30, может отобразиться как 03:30 или 01:30
- Студенты могут пропустить урок из-за неправильного времени

**Рекомендация:**
1. Хранить времена в UTC (`USE_TZ = True` уже включён)
2. Использовать `tz.localize()` вместо `datetime.combine(..., tzinfo=tz)`
3. Добавить тесты для граничных случаев DST

---

## 3. RECURRING LESSONS

### 3.1 Защита от бесконечных циклов

**Риск:** НИЗКИЙ 🟢

**Анализ кода:**

```python
# views.py:524-575 - _build_recurring_virtual_lessons()
def _build_recurring_virtual_lessons(self, request, start_dt, end_dt, existing_queryset):
    # ...
    current_date = start_dt.date()
    while current_date <= end_dt.date():  # ✅ Ограничение по end_dt
        for rl in recurring_qs:
            if not (rl.start_date <= current_date <= rl.end_date):  # ✅ Ограничение по rl.end_date
                continue
        current_date += timedelta(days=1)  # ✅ Гарантированный инкремент
```

**Защитные механизмы:**

| Механизм | Реализация | Статус |
|----------|------------|--------|
| Ограничение диапазона | `start_dt ≤ current_date ≤ end_dt` | ✅ |
| Ограничение по RecurringLesson | `rl.start_date ≤ current_date ≤ rl.end_date` | ✅ |
| Инкремент даты | `current_date += timedelta(days=1)` | ✅ |
| Default диапазон | 30 дней от текущей даты | ✅ |

**НО! Потенциальная DoS атака:**

```python
# Если клиент запросит:
GET /api/schedule/lessons/?include_recurring=1&start=2020-01-01&end=2030-12-31

# Генерация 10+ лет уроков (3650+ дней × N recurring lessons)
# → Timeout или OOM
```

**Рекомендация:**

```python
def _resolve_list_range(self, request):
    # ...
    # ✅ Ограничить максимальный диапазон
    MAX_RANGE_DAYS = 365
    if (end_dt - start_dt).days > MAX_RANGE_DAYS:
        end_dt = start_dt + timedelta(days=MAX_RANGE_DAYS)
        logger.warning(f"Recurring lessons range capped to {MAX_RANGE_DAYS} days")
    
    return start_dt, end_dt
```

### 3.2 Защита от переполнения базы

**RecurringLesson НЕ создаёт записи в БД** - виртуальные уроки генерируются на лету. 

Это **правильный подход** - избегает:
- Переполнения таблицы Lesson
- N+1 проблем при обновлении RegularLesson
- Проблем с каскадным удалением

---

## 4. CELERY TASKS

### 4.1 Анализ обработки ошибок

| Task | autoretry | time_limit | soft_time_limit | Оценка |
|------|-----------|------------|-----------------|--------|
| `warmup_zoom_oauth_tokens` | ✅ Exception | ✅ 180s | ✅ 120s | ⭐ Отлично |
| `release_stuck_zoom_accounts` | ❌ | ❌ | ❌ | 🟡 Требует улучшения |
| `release_finished_zoom_accounts` | ❌ | ❌ | ❌ | 🟡 Требует улучшения |
| `send_lesson_reminder` | ❌ | ❌ | ❌ | 🟡 Требует улучшения |
| `schedule_upcoming_lesson_reminders` | ❌ | ❌ | ❌ | 🟡 Требует улучшения |
| `send_recurring_lesson_reminders` | ❌ | ❌ | ❌ | 🟡 Требует улучшения |

### 4.2 Проблемный код

```python
# tasks.py:110-150 - release_stuck_zoom_accounts
@shared_task(name='schedule.tasks.release_stuck_zoom_accounts')
def release_stuck_zoom_accounts():
    # ❌ НЕТ autoretry_for
    # ❌ НЕТ time_limit
    # ❌ НЕТ soft_time_limit
    
    # Если Zoom API таймаутится - task зависнет навсегда
    for account in stuck_accounts:
        lesson = account.current_lesson
        # ❌ Нет try/except вокруг account.save()
```

### 4.3 Рекомендуемые исправления

```python
@shared_task(
    name='schedule.tasks.release_stuck_zoom_accounts',
    autoretry_for=(Exception,),
    retry_backoff=60,
    max_retries=3,
    soft_time_limit=60,   # 1 минута
    time_limit=120,       # 2 минуты
)
def release_stuck_zoom_accounts():
    """Освобождение зависших Zoom-аккаунтов с proper error handling."""
    from celery.exceptions import SoftTimeLimitExceeded
    
    now = timezone.now()
    released_count = 0
    
    try:
        stuck_accounts = ZoomAccount.objects.filter(
            is_busy=True,
            current_lesson__isnull=False
        ).select_related('current_lesson')
        
        for account in stuck_accounts:
            try:
                lesson = account.current_lesson
                grace_period = timedelta(minutes=15)
                
                if lesson.end_time and lesson.end_time + grace_period < now:
                    account.is_busy = False
                    account.current_lesson = None
                    account.save(update_fields=['is_busy', 'current_lesson'])
                    released_count += 1
                    
            except Exception as e:
                logger.exception(f"Failed to release account {account.id}: {e}")
                continue  # Продолжаем с другими аккаунтами
                
    except SoftTimeLimitExceeded:
        logger.warning("release_stuck_zoom_accounts: soft time limit exceeded")
        raise  # Позволяем Celery корректно завершить task
    
    return {'released': released_count, 'timestamp': now.isoformat()}
```

---

## 5. СТРУКТУРА UNIT-ТЕСТОВ ДЛЯ CONCURRENCY

### 5.1 Тестовый фреймворк

```python
# zoom_pool/tests/test_concurrency.py
"""
Тесты конкурентного доступа к Zoom Pool.

Требования:
- pytest
- pytest-django
- pytest-asyncio (опционально)

Запуск:
    pytest zoom_pool/tests/test_concurrency.py -v -s
"""
import pytest
from django.test import TransactionTestCase
from django.db import connection
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Barrier
import time

from zoom_pool.models import ZoomAccount
from accounts.models import CustomUser


class ZoomPoolConcurrencyTests(TransactionTestCase):
    """
    Тесты на race conditions в Zoom Pool.
    
    Используем TransactionTestCase вместо TestCase для:
    - Реальных транзакций (не обёрнутых в savepoint)
    - Возможности тестировать SELECT FOR UPDATE
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаём тестового учителя
        cls.teacher = CustomUser.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )
    
    def setUp(self):
        # Создаём пул из 3 аккаунтов с max_concurrent_meetings=1
        self.accounts = []
        for i in range(3):
            acc = ZoomAccount.objects.create(
                email=f'zoom{i}@test.com',
                zoom_account_id=f'acc_{i}',
                api_key=f'key_{i}',
                api_secret=f'secret_{i}',
                max_concurrent_meetings=1,
                current_meetings=0,
                is_active=True
            )
            self.accounts.append(acc)
    
    def tearDown(self):
        ZoomAccount.objects.all().delete()


class TestAcquireRaceCondition(ZoomPoolConcurrencyTests):
    """Тест: 10 потоков пытаются захватить 3 аккаунта одновременно."""
    
    def test_concurrent_acquire_respects_limits(self):
        """
        Сценарий:
        - 3 Zoom аккаунта с max_concurrent_meetings=1
        - 10 потоков одновременно вызывают acquire()
        - Ожидание: ровно 3 успешных acquire, 7 ValueError
        """
        num_threads = 10
        num_accounts = 3
        
        # Барьер для синхронизации старта всех потоков
        barrier = Barrier(num_threads)
        results = {'success': 0, 'error': 0, 'errors': []}
        
        def try_acquire(account_id):
            """Попытка захватить аккаунт."""
            # Ждём пока все потоки будут готовы
            barrier.wait()
            
            try:
                account = ZoomAccount.objects.get(pk=account_id)
                account.acquire()
                return ('success', account_id)
            except ValueError as e:
                return ('error', str(e))
        
        # Распределяем потоки по аккаунтам (round-robin)
        account_ids = [self.accounts[i % num_accounts].pk for i in range(num_threads)]
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(try_acquire, acc_id) for acc_id in account_ids]
            
            for future in as_completed(futures):
                result_type, result_data = future.result()
                if result_type == 'success':
                    results['success'] += 1
                else:
                    results['error'] += 1
                    results['errors'].append(result_data)
        
        # Проверяем результаты
        self.assertEqual(results['success'], num_accounts, 
            f"Expected {num_accounts} successful acquires, got {results['success']}")
        self.assertEqual(results['error'], num_threads - num_accounts,
            f"Expected {num_threads - num_accounts} errors, got {results['error']}")
        
        # Проверяем состояние БД
        for account in ZoomAccount.objects.all():
            self.assertLessEqual(account.current_meetings, account.max_concurrent_meetings,
                f"Account {account.email} exceeds max: {account.current_meetings}/{account.max_concurrent_meetings}")


class TestReleaseIdempotency(ZoomPoolConcurrencyTests):
    """Тест: release() идемпотентен (повторные вызовы безопасны)."""
    
    def test_double_release_safe(self):
        """
        Сценарий:
        - Один аккаунт захвачен
        - 5 потоков одновременно вызывают release()
        - Ожидание: current_meetings = 0, без ошибок
        """
        account = self.accounts[0]
        account.acquire()
        
        self.assertEqual(account.current_meetings, 1)
        
        num_threads = 5
        barrier = Barrier(num_threads)
        errors = []
        
        def try_release():
            barrier.wait()
            try:
                account.release()
                return 'ok'
            except Exception as e:
                return str(e)
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(try_release) for _ in range(num_threads)]
            for future in as_completed(futures):
                result = future.result()
                if result != 'ok':
                    errors.append(result)
        
        # Проверяем
        account.refresh_from_db()
        self.assertEqual(account.current_meetings, 0, "current_meetings should be 0 after releases")
        self.assertEqual(len(errors), 0, f"Release errors: {errors}")


class TestAcquireAfterRelease(ZoomPoolConcurrencyTests):
    """Тест: аккаунт становится доступен сразу после release()."""
    
    def test_acquire_after_release_works(self):
        """
        Сценарий:
        - Thread 1: acquire → держит 100ms → release
        - Thread 2: пытается acquire, ждёт, получает после release
        """
        account = self.accounts[0]
        results = {'thread1': None, 'thread2': None}
        
        barrier = Barrier(2)
        
        def thread1_job():
            barrier.wait()
            account.acquire()
            results['thread1'] = 'acquired'
            time.sleep(0.1)  # Держим 100ms
            account.release()
            results['thread1'] = 'released'
        
        def thread2_job():
            barrier.wait()
            time.sleep(0.05)  # Стартуем чуть позже
            try:
                account.acquire()  # Должен подождать release от thread1
                results['thread2'] = 'acquired'
            except Exception as e:
                results['thread2'] = f'error: {e}'
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(thread1_job)
            f2 = executor.submit(thread2_job)
            f1.result()
            f2.result()
        
        self.assertEqual(results['thread1'], 'released')
        self.assertEqual(results['thread2'], 'acquired')


class TestDeadlockPrevention(ZoomPoolConcurrencyTests):
    """Тест: нет deadlock при конкурентном доступе к нескольким аккаунтам."""
    
    def test_no_deadlock_on_multiple_accounts(self):
        """
        Сценарий потенциального deadlock:
        - Thread 1: acquire(account1) → acquire(account2)
        - Thread 2: acquire(account2) → acquire(account1)
        
        При неправильной реализации → deadlock.
        При правильной (nowait=False + одинаковый порядок) → один поток ждёт.
        """
        account1 = self.accounts[0]
        account2 = self.accounts[1]
        
        barrier = Barrier(2)
        results = {'thread1': [], 'thread2': []}
        
        def thread1_job():
            barrier.wait()
            try:
                account1.acquire()
                results['thread1'].append('got_acc1')
                time.sleep(0.05)
                account2.acquire()
                results['thread1'].append('got_acc2')
            except Exception as e:
                results['thread1'].append(f'error: {e}')
            finally:
                try:
                    account1.release()
                    account2.release()
                except:
                    pass
        
        def thread2_job():
            barrier.wait()
            try:
                account2.acquire()
                results['thread2'].append('got_acc2')
                time.sleep(0.05)
                account1.acquire()
                results['thread2'].append('got_acc1')
            except Exception as e:
                results['thread2'].append(f'error: {e}')
            finally:
                try:
                    account2.release()
                    account1.release()
                except:
                    pass
        
        # Таймаут на тест - если deadlock, тест провалится по timeout
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Deadlock detected!")
        
        # signal.alarm не работает на Windows, используем threading.Timer
        from threading import Timer
        
        timeout_occurred = [False]
        def set_timeout():
            timeout_occurred[0] = True
        
        timer = Timer(5.0, set_timeout)  # 5 секунд timeout
        timer.start()
        
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(thread1_job)
                f2 = executor.submit(thread2_job)
                f1.result(timeout=5)
                f2.result(timeout=5)
        finally:
            timer.cancel()
        
        self.assertFalse(timeout_occurred[0], "Deadlock detected - test timed out")
        
        # При правильной реализации оба потока должны завершиться
        # (один подожёт другого благодаря select_for_update(nowait=False))
        print(f"Thread1 results: {results['thread1']}")
        print(f"Thread2 results: {results['thread2']}")
```

### 5.2 Псевдокод для теста Race Condition (эмуляция 500 одновременных уроков)

```python
# schedule/tests/test_500_concurrent_lessons.py
"""
Нагрузочный тест: 500 учителей одновременно запускают уроки.

ВАЖНО: Этот тест НЕ использует Zoom Pool (он отключён в текущей версии).
Тест проверяет:
1. Rate limiting работает (3 попытки/мин на учителя)
2. Zoom API timeouts обрабатываются корректно
3. БД выдерживает нагрузку
"""
import pytest
from django.test import TransactionTestCase
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Barrier
from unittest.mock import patch, MagicMock
import time

from schedule.views import LessonViewSet
from schedule.models import Lesson, Group
from accounts.models import CustomUser, Subscription


class Test500ConcurrentLessons(TransactionTestCase):
    """Симуляция 500 одновременных запусков уроков."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.num_teachers = 500
        cls.teachers = []
        cls.lessons = []
        
        # Создаём 500 учителей с Zoom credentials
        for i in range(cls.num_teachers):
            teacher = CustomUser.objects.create_user(
                email=f'teacher{i}@test.com',
                password='test123',
                role='teacher',
                zoom_account_id=f'acc_{i}',
                zoom_client_id=f'client_{i}',
                zoom_client_secret=f'secret_{i}'
            )
            cls.teachers.append(teacher)
            
            # Создаём подписку
            Subscription.objects.create(
                user=teacher,
                status='active',
                expires_at=timezone.now() + timedelta(days=30)
            )
            
            # Создаём группу и урок
            group = Group.objects.create(
                name=f'Group {i}',
                teacher=teacher
            )
            lesson = Lesson.objects.create(
                title=f'Lesson {i}',
                group=group,
                teacher=teacher,
                start_time=timezone.now() + timedelta(minutes=5),
                end_time=timezone.now() + timedelta(hours=1)
            )
            cls.lessons.append(lesson)
    
    @patch('schedule.zoom_client.ZoomAPIClient.create_meeting')
    def test_500_concurrent_starts(self, mock_zoom):
        """
        Псевдокод теста 500 одновременных запусков.
        
        Ожидаемое поведение:
        - Все 500 уроков запускаются (каждый учитель использует свои credentials)
        - Zoom API вызывается 500 раз (параллельно)
        - Нет race conditions в БД
        """
        # Mock Zoom API response
        mock_zoom.return_value = {
            'id': '123456789',
            'start_url': 'https://zoom.us/start/123',
            'join_url': 'https://zoom.us/join/123',
            'password': 'abc123'
        }
        
        num_threads = 50  # Реально используем 50 потоков (симулируя 500 пакетами)
        barrier = Barrier(num_threads)
        results = {'success': 0, 'error': 0, 'rate_limited': 0, 'errors': []}
        
        def start_lesson(teacher_idx):
            """Симуляция запуска урока учителем."""
            barrier.wait()  # Синхронизация старта
            
            teacher = self.teachers[teacher_idx]
            lesson = self.lessons[teacher_idx]
            
            # Создаём mock request
            from rest_framework.test import APIRequestFactory
            factory = APIRequestFactory()
            request = factory.post(f'/api/schedule/lessons/{lesson.id}/start-new/')
            request.user = teacher
            request.data = {'provider': 'zoom_pool'}
            
            # Вызываем view
            view = LessonViewSet.as_view({'post': 'start_new'})
            response = view(request, pk=lesson.id)
            
            return {
                'teacher_idx': teacher_idx,
                'status_code': response.status_code,
                'data': response.data if hasattr(response, 'data') else None
            }
        
        # Запускаем в 10 пакетах по 50 учителей
        for batch in range(10):
            batch_start = batch * 50
            batch_indices = range(batch_start, min(batch_start + 50, self.num_teachers))
            
            with ThreadPoolExecutor(max_workers=50) as executor:
                futures = [executor.submit(start_lesson, idx) for idx in batch_indices]
                
                for future in as_completed(futures):
                    result = future.result()
                    if result['status_code'] == 200:
                        results['success'] += 1
                    elif result['status_code'] == 429:
                        results['rate_limited'] += 1
                    else:
                        results['error'] += 1
                        results['errors'].append(result)
        
        # Проверки
        print(f"Results: {results['success']} success, {results['error']} errors, {results['rate_limited']} rate limited")
        
        # Большинство должны быть успешными
        self.assertGreater(results['success'], 400, "Too few successful lesson starts")
        
        # Проверяем БД
        lessons_with_zoom = Lesson.objects.filter(zoom_meeting_id__isnull=False).count()
        self.assertGreater(lessons_with_zoom, 400, "Too few lessons got Zoom meetings")
        
        # Проверяем что Zoom API был вызван N раз
        self.assertEqual(mock_zoom.call_count, results['success'])
    
    def test_rate_limit_enforced(self):
        """
        Тест: учитель не может запустить урок более 3 раз в минуту.
        """
        teacher = self.teachers[0]
        lesson = self.lessons[0]
        
        from rest_framework.test import APIRequestFactory
        from django.core.cache import cache
        
        # Очищаем кэш rate limit
        cache.delete(f"start_lesson_rate_limit:{teacher.id}")
        
        factory = APIRequestFactory()
        view = LessonViewSet.as_view({'post': 'start_new'})
        
        responses = []
        for i in range(5):
            request = factory.post(f'/api/schedule/lessons/{lesson.id}/start-new/')
            request.user = teacher
            request.data = {}
            response = view(request, pk=lesson.id)
            responses.append(response.status_code)
        
        # Первые 3 должны пройти, 4-й и 5-й — 429
        self.assertEqual(responses[3], 429, "4th request should be rate limited")
        self.assertEqual(responses[4], 429, "5th request should be rate limited")
```

---

## 6. РЕКОМЕНДАЦИИ

### 6.1 Приоритет ВЫСОКИЙ

1. **Добавить time_limit ко всем Celery tasks:**
   ```python
   @shared_task(
       soft_time_limit=60,
       time_limit=120,
       autoretry_for=(Exception,),
       max_retries=3
   )
   ```

2. **Ограничить диапазон генерации RecurringLesson:**
   ```python
   MAX_RANGE_DAYS = 365
   if (end_dt - start_dt).days > MAX_RANGE_DAYS:
       end_dt = start_dt + timedelta(days=MAX_RANGE_DAYS)
   ```

### 6.2 Приоритет СРЕДНИЙ

3. **Исправить DST bug в datetime.combine:**
   ```python
   # Использовать tz.localize() вместо tzinfo=
   naive_dt = datetime.combine(date_part, time_part)
   aware_dt = tz.localize(naive_dt, is_dst=False)
   ```

4. **Добавить unit-тесты на concurrency** (см. раздел 5)

### 6.3 Приоритет НИЗКИЙ

5. **Рассмотреть удаление zoom_pool** если не планируется использовать
6. **Добавить метрики для Celery tasks** (prometheus/grafana)

---

## 7. ЗАКЛЮЧЕНИЕ

Модули `zoom_pool` и `schedule` **хорошо спроектированы** с учётом конкурентного доступа:

- ✅ Zoom Pool имеет правильную реализацию `select_for_update`
- ✅ Recurring Lessons не создают лишних записей в БД
- ✅ Есть rate limiting на запуск уроков
- 🟡 Требуется улучшение обработки DST
- 🟡 Требуется добавление timeouts к Celery tasks

**Общий риск:** НИЗКИЙ при условии внедрения рекомендаций.

---

**Конец отчёта**  
_Создан: 5 февраля 2026_  
_Режим: READ-ONLY анализ_
