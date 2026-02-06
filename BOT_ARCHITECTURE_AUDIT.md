# Аудит архитектуры Telegram бота (`teaching_panel/bot/`)

**Дата**: 2026-02-05  
**Автор**: AI Audit Agent  
**Статус**: Завершён  

---

## 1. State Management (FSM)

### Текущая реализация

Состояние хранится через Django Cache API (`django.core.cache`):

```
bot/utils/state.py → get_dialog_state() / set_dialog_state()
↓
django.core.cache.cache.get() / cache.set()
↓
Production: django_redis.cache.RedisCache (REDIS_URL)
Development: django.core.cache.backends.locmem.LocMemCache
```

**Формат состояния** — JSON в Redis/LocMem по ключу `bot:dialog:{telegram_id}`:
```json
{
  "action": "remind_lesson",
  "step": "select_groups",
  "selected_groups": [1, 3],
  "teacher_id": 42
}
```

**TTL**: `DIALOG_STATE_TTL = 300` (5 минут), настраивается в `config.py`.

### Проблема: Потеря состояния при деплое

| Сценарий | Production (Redis) | Development (LocMem) |
|----------|--------------------|-----------------------|
| Рестарт Gunicorn | Состояние **сохраняется** (Redis персистентный) | Состояние **теряется** (в памяти процесса) |
| Рестарт Redis | Состояние **теряется** (если нет RDB/AOF) | N/A |
| TTL 5 минут | Wizard сбросится, если учитель отвлёкся >5 мин | То же |

**Вердикт**: В **production с Redis** состояние переживает деплой Django. Но:

### Найденные проблемы

#### CRITICAL: `get_dialog_state()` / `set_dialog_state()` — СИНХРОННЫЕ вызовы в async контексте

```python
# bot/utils/state.py — строки 25-53
def get_dialog_state(telegram_id: int) -> Optional[Dict[str, Any]]:   # ← SYNC!
    key = _make_dialog_key(telegram_id)
    data = cache.get(key)         # ← Блокирующий I/O (Redis TCP)
    ...

def set_dialog_state(telegram_id: int, state: ...) -> bool:           # ← SYNC!
    cache.set(key, ...)           # ← Блокирующий I/O (Redis TCP)
```

Эти функции вызываются напрямую из async хендлеров **без `sync_to_async`**:

```python
# bot/handlers/teacher/lessons.py:66
set_dialog_state(telegram_id, { ... })           # ← SYNC в async!

# bot/handlers/teacher/lessons.py:90
state = get_dialog_state(telegram_id)            # ← SYNC в async!
```

**Последствия**: При использовании `django_redis` это TCP-вызов к Redis, который **блокирует event loop** и замораживает бота для ВСЕХ пользователей на время вызова (~1-5ms на вызов, но может быть больше при сетевых проблемах).

С `LocMemCache` проблемы нет (in-memory), но в production это баг.

#### MEDIUM: TTL 5 минут — слишком мало для сложных wizard'ов

Учитель выбирает группы → выбирает урок → редактирует текст → preview → отправка. Если между шагами проходит >5 минут, wizard сбрасывается с невнятным "Сессия истекла".

**Рекомендация**: Увеличить до `900` (15 минут) или `1800` (30 минут).

---

## 2. Handler Isolation (разделение ролей)

### Архитектура

```
handlers/
├── common.py         ← /start, /menu, /help, /profile (все роли)
├── callbacks.py       ← Роутер callback_query по префиксам
├── teacher/
│   ├── lessons.py     ← @require_teacher: remind_lesson_*
│   └── homework.py    ← @require_teacher: check_hw_*, remind_hw_*
└── student/
    ├── lessons.py     ← @require_student: my_lessons, today_lessons
    ├── homework.py    ← @require_student: my_homework, pending_homework
    └── progress.py    ← @require_student: my_progress
```

### Результат проверки

**Команды (CommandHandler)** — **защищены корректно**:

| Команда | Декоратор | Проверка |
|---------|-----------|----------|
| `/remind_lesson` | `@require_linked_account` + `@require_teacher` | OK |
| `/remind_hw` | `@require_linked_account` + `@require_teacher` | OK |
| `/check_hw` | `@require_linked_account` + `@require_teacher` | OK |
| `/lessons` | `@require_linked_account` + `@require_student` | OK |
| `/today` | `@require_linked_account` + `@require_student` | OK |
| `/homework` | `@require_linked_account` + `@require_student` | OK |
| `/pending` | `@require_linked_account` + `@require_student` | OK |
| `/progress` | `@require_linked_account` + `@require_student` | OK |

**Один декоратор `@require_teacher`** на самом деле разрешает `['teacher', 'admin']`:
```python
def require_teacher(func):
    return require_role('teacher', 'admin')(func)
```

### CRITICAL: Callback'и НЕ защищены проверкой роли!

В `callbacks.py` роутер по префиксам **не проверяет роль**:

```python
async def callback_query_handler(update, context):
    data = query.data

    if data.startswith('rl_'):                              # ← remind_lesson
        await handle_remind_lesson_callback(update, context, data)  # ← НЕТ @require_teacher!
        return

    if data.startswith('rh_'):                              # ← remind_hw
        await handle_remind_hw_callback(update, context, data)      # ← НЕТ @require_teacher!
        return

    if data.startswith('check_hw:'):
        await check_hw_selected(update, context)            # ← НЕТ @require_teacher!
        return

    # Student callbacks тоже без проверки роли
    if data.startswith('st_lesson:'):
        await lesson_details(update, context)               # ← НЕТ @require_student!
        return
```

**Атака**: Студент, зная формат callback_data, может подделать inline-кнопку (через Telegram Bot API или модифицированный клиент) и вызвать:
- `rl_send_now` — отправить рассылку от имени учителя
- `check_hw:123` — увидеть статистику ДЗ учителя
- `ping:123` — пингануть студентов

**Смягчающий фактор**: Callback'и типа `remind_lesson_send_now` проверяют `get_dialog_state(telegram_id)`, которое привязано к telegram_id отправителя. Если у студента нет активного wizard'а — ответ "Сессия истекла". **Но** `check_hw_selected` и `list_not_submitted` не проверяют state, только парсят homework_id из callback_data.

**Рекомендация**: Добавить проверку роли в callback router.

### MEDIUM: `lesson_details` не проверяет принадлежность урока студенту

```python
async def lesson_details(update, context):
    lesson_id = int(query.data.split(':')[1])
    lesson = await sync_to_async(get_lesson)()     # ← Любой lesson_id!
```

Студент может подсмотреть детали чужого урока, если знает ID.

---

## 3. Асинхронность и блокирующие вызовы

### Общая картина

| Компонент | Статус |
|-----------|--------|
| Хендлеры (async def) | Все `async` |
| DB запросы | Обёрнуты в `sync_to_async()` — **OK** |
| BroadcastService | Полностью `async` — **OK** |
| Telegram API calls | `await bot.send_message()` — **OK** |
| `get_dialog_state` / `set_dialog_state` | **SYNC в async контексте — ПРОБЛЕМА** |

### Детальный разбор проблемных мест

#### CRITICAL: Синхронный cache.get/set в event loop

**Файлы**: Все файлы в `handlers/teacher/` и косвенно `handlers/student/` через `callbacks.py`.

**Масштаб**: ~40 прямых вызовов `get_dialog_state()` и `set_dialog_state()` в async хендлерах.

**Решение** через обёртку:
```python
# bot/utils/state.py — исправление
from asgiref.sync import sync_to_async

async def aget_dialog_state(telegram_id: int) -> Optional[Dict[str, Any]]:
    return await sync_to_async(get_dialog_state)(telegram_id)

async def aset_dialog_state(telegram_id: int, state: Dict[str, Any], ttl: int = None) -> bool:
    return await sync_to_async(set_dialog_state)(telegram_id, state, ttl)

async def aclear_dialog_state(telegram_id: int) -> bool:
    return await sync_to_async(clear_dialog_state)(telegram_id)
```

#### LOW: redis import в cleanup task

```python
# bot/tasks.py:102
import redis                      # ← Прямой redis, минуя django_redis
r = redis.from_url(REDIS_URL)    # ← Создаёт новое подключение каждый вызов
```

Не критично (Celery синхронный), но лучше использовать `cache` API.

### Нет блокирующих вызовов к внешним API

BroadcastService корректно использует `await self.bot.send_message()` — это уже async в python-telegram-bot v20+.

---

## 4. Integration: Бот ↔ Django

### Паттерн взаимодействия

```
telegram handler (async)
    ↓
    sync_to_async(lambda: Model.objects.filter(...))  ← ORM запрос
    ↓
    результат (в async контексте)
```

Используется паттерн **inline closure**:
```python
def get_groups():
    from schedule.models import Group
    return list(Group.objects.filter(teacher=user).order_by('name'))

groups = await sync_to_async(get_groups)()
```

### Оценка корректности

**sync_to_async** применяется **правильно** для всех ORM-вызовов:
- `User.objects.get()` — через `sync_to_async`
- `Group.objects.filter()` — через `sync_to_async`
- `Lesson.objects.filter()` — через `sync_to_async`
- `Homework.objects.filter()` — через `sync_to_async`
- `msg.mark_sending()` / `msg.mark_sent()` — через `sync_to_async`
- `msg.save()` — через `sync_to_async`

### Lazy imports внутри closures

```python
def get_lessons():
    from schedule.models import Lesson    # ← Импорт ВНУТРИ closure
    return list(Lesson.objects.filter(...))
```

Это **корректно** и даже правильно — избегает проблем с circular imports. Но первый вызов будет чуть медленнее (загрузка модуля).

### Celery tasks используют `async_to_sync` — корректно

```python
# bot/tasks.py
result = async_to_sync(service.send_to_groups)(...)
```

Celery worker синхронный, поэтому `async_to_sync` — правильный способ вызвать async-сервис.

### Проблема: `tasks.py` использует поля, которых может не быть в модели

```python
# bot/tasks.py:43
msg.target_type      # ← Нет в модели ScheduledMessage!
msg.target_ids       # ← Нет в модели ScheduledMessage!
```

Модель `ScheduledMessage` использует `M2M` поля (`target_groups`, `target_students`), но `tasks.py` ожидает `target_type` и `target_ids`. Это **мёртвый код** или **несогласованность** — задача `process_scheduled_messages` из `tasks.py` упадёт с `AttributeError`.

Параллельная реализация в `services/broadcast.py::process_scheduled_messages()` — async-версия, которая корректно работает с M2M полями.

---

## 5. Сводка найденных проблем

| # | Severity | Проблема | Файл |
|---|----------|----------|------|
| 1 | **CRITICAL** | `get_dialog_state`/`set_dialog_state` синхронно блокируют event loop | `utils/state.py` |
| 2 | **CRITICAL** | Callback'и не проверяют роль пользователя | `handlers/callbacks.py` |
| 3 | **HIGH** | `tasks.py::process_scheduled_messages` обращается к несуществующим полям `target_type`/`target_ids` | `tasks.py:43-56` |
| 4 | **MEDIUM** | TTL 5 минут слишком мал для wizard'ов | `config.py:21` |
| 5 | **MEDIUM** | `lesson_details` не проверяет принадлежность урока студенту | `handlers/student/lessons.py:82` |
| 6 | **LOW** | Прямой `import redis` вместо Django cache API в cleanup task | `tasks.py:102` |

---

## 6. План тестирования бота (E2E + Unit)

### 6.1 Unit-тесты

#### A. State Management

```python
# bot/tests/test_state.py
class TestDialogState(TestCase):
    """Тесты FSM состояний"""
    
    def test_set_and_get_state(self):
        """set → get возвращает то же значение"""
        
    def test_state_ttl_expiry(self):
        """Через TTL состояние = None"""
        
    def test_update_partial_state(self):
        """update_dialog_state обновляет часть ключей"""
        
    def test_clear_state(self):
        """clear → get = None"""
        
    def test_concurrent_updates(self):
        """Два set подряд — второй побеждает"""
        
    def test_json_serialization_edge_cases(self):
        """Состояние с datetime, None, unicode"""
```

#### B. Permissions

```python
# bot/tests/test_permissions.py  
class TestRoleDecorators(TestCase):
    """Проверка декораторов ролей"""
    
    async def test_require_teacher_blocks_student(self):
        """Студент не может вызвать @require_teacher хендлер"""
        
    async def test_require_student_blocks_teacher(self):
        """Учитель не может вызвать @require_student хендлер"""
        
    async def test_require_linked_account_unlinked(self):
        """Незарегистрированный пользователь блокируется"""
    
    async def test_admin_passes_require_teacher(self):
        """Admin проходит @require_teacher"""

    async def test_broadcast_rate_limiting(self):
        """check_broadcast_permission отклоняет при превышении лимита"""
        
    async def test_broadcast_cooldown(self):
        """Нельзя отправить рассылку чаще cooldown_seconds"""
```

#### C. Services

```python
# bot/tests/test_broadcast.py
class TestBroadcastService(TestCase):
    """Тесты рассылки"""
    
    async def test_send_to_empty_list(self):
        """Пустой список → 0 sent, 0 failed"""
        
    async def test_truncation_at_limit(self):
        """>500 получателей обрезается до 500"""
        
    async def test_blocked_user_counted_as_failed(self):
        """Forbidden → failed_count += 1"""
        
    async def test_delay_between_messages(self):
        """Задержка TELEGRAM_LIMITS['bulk_delay_ms'] между сообщениями"""


# bot/tests/test_homework_service.py
class TestHomeworkService(TestCase):
    """Тесты сервиса ДЗ"""
    
    async def test_get_homework_stats_no_students(self):
        """ДЗ без назначенных студентов → all zeros"""
        
    async def test_not_submitted_excludes_submitted(self):
        """Сдавшие не попадают в not_submitted"""
        
    async def test_overdue_when_past_deadline(self):
        """После дедлайна pending → overdue"""
```

### 6.2 E2E тесты (Integration)

#### D. Wizard: Напоминание об уроке (полный цикл)

```python
# bot/tests/test_e2e_remind_lesson.py
class TestRemindLessonWizard(TestCase):
    """E2E: /remind_lesson → выбор групп → выбор урока → preview → отправка"""
    
    async def test_full_happy_path(self):
        """
        1. /remind_lesson
        2. Callback rl_group:1 (выбрать группу)
        3. Callback rl_groups_done
        4. Callback rl_lesson:42
        5. Callback rl_send_now
        6. Проверить: BroadcastLog создан, состояние очищено
        """
        
    async def test_session_expired_mid_wizard(self):
        """
        1. /remind_lesson → state saved
        2. Ждём TTL
        3. Callback rl_lesson:42 → "Сессия истекла"
        """
        
    async def test_no_groups(self):
        """Учитель без групп → "У вас нет групп" """
        
    async def test_no_upcoming_lessons(self):
        """Нет уроков в будущем → пустой список"""
        
    async def test_schedule_for_later(self):
        """
        ... → rl_schedule → rl_time:1hour
        → ScheduledMessage создан со scheduled_at = now + 1h
        """
        
    async def test_custom_text_flow(self):
        """
        ... → rl_custom_text → отправка текста → preview → send
        """
```

#### E. Wizard: Проверка ДЗ

```python
# bot/tests/test_e2e_check_hw.py
class TestCheckHwWizard(TestCase):
    
    async def test_check_hw_shows_stats(self):
        """check_hw:42 → показывает submitted/pending/overdue"""
        
    async def test_list_not_submitted(self):
        """not_submitted:42 → список студентов"""
        
    async def test_ping_not_submitted_sends_messages(self):
        """ping:42 → ping_send_now → messages sent to students with TG"""
        
    async def test_ping_no_telegram_students(self):
        """Все без Telegram → "нет учеников с Telegram" """
```

#### F. Student commands

```python
# bot/tests/test_e2e_student.py
class TestStudentCommands(TestCase):
    
    async def test_my_lessons_shows_within_7_days(self):
        """/lessons показывает уроки на 7 дней"""
        
    async def test_today_lessons_only_today(self):
        """/today показывает только сегодняшние"""
        
    async def test_my_homework_with_submissions(self):
        """/homework показывает статусы: не начато, на проверке, проверено"""
        
    async def test_pending_homework_excludes_submitted(self):
        """/pending не показывает сданные"""
        
    async def test_progress_correct_calculations(self):
        """/progress считает среднюю оценку и % сдачи корректно"""
    
    async def test_student_cannot_see_other_student_lessons(self):
        """Студент видит только свои уроки (по группам)"""
```

#### G. Security (Role isolation)

```python
# bot/tests/test_e2e_security.py
class TestRoleIsolation(TestCase):
    """Тесты изоляции ролей"""
    
    async def test_student_cannot_call_remind_lesson(self):
        """/remind_lesson от студента → "только для преподавателей" """
        
    async def test_student_callback_rl_send_now(self):
        """Студент отправляет callback rl_send_now → "Сессия истекла" (нет state)"""
        
    async def test_student_callback_check_hw(self):
        """Студент отправляет callback check_hw:123 → ДОЛЖЕН быть заблокирован"""
        
    async def test_teacher_cannot_call_lessons(self):
        """/lessons от учителя → "только для учеников" """
        
    async def test_unlinked_user_blocked_everywhere(self):
        """Все @require_linked_account хендлеры блокируют непривязанного"""
```

#### H. Edge cases и устойчивость

```python
# bot/tests/test_e2e_resilience.py
class TestResilience(TestCase):
    """Тесты устойчивости"""
    
    async def test_deploy_preserves_redis_state(self):
        """Состояние в Redis сохраняется после рестарта"""
        
    async def test_invalid_callback_data(self):
        """Невалидный callback → "Неизвестная команда", не crash"""
        
    async def test_callback_with_deleted_entity(self):
        """check_hw:999 (удалённое ДЗ) → корректная ошибка, не 500"""
        
    async def test_concurrent_wizards(self):
        """Два wizard'а от одного пользователя — второй перезаписывает первый"""
        
    async def test_broadcast_to_blocked_users(self):
        """Рассылка пользователям, заблокировавшим бота → failed, не crash"""
```

### 6.3 Как запускать

```bash
# Unit-тесты
python manage.py test bot.tests --verbosity=2

# С mock Telegram API (для E2E без реального бота)
# Используем python-telegram-bot test utilities или unittest.mock
```

---

## 7. План рефакторинга: Улучшение обработки ошибок

### 7.1 Глобальный error handler для бота

Сейчас бот **молча игнорирует** необработанные исключения — пользователь видит просто "зависание". Нужен глобальный обработчик:

```python
# bot/main.py — добавить в setup_handlers()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок бота"""
    logger.error(f"Bot error: {context.error}", exc_info=context.error)
    
    # Уведомляем пользователя
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка. Попробуйте позже или используйте /menu."
            )
        elif update and update.callback_query:
            await update.callback_query.answer(
                "Произошла ошибка. Попробуйте /menu.",
                show_alert=True,
            )
    except Exception:
        pass  # Не можем уведомить — хотя бы залогировали

application.add_error_handler(error_handler)
```

### 7.2 Async state с обработкой ошибок

```python
# bot/utils/state.py — async-обёртки

async def aget_dialog_state(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Async-обёртка для get_dialog_state"""
    try:
        return await sync_to_async(get_dialog_state)(telegram_id)
    except Exception as e:
        logger.error(f"Failed to get dialog state for {telegram_id}: {e}")
        return None

async def aset_dialog_state(telegram_id: int, state: Dict[str, Any], ttl: int = None) -> bool:
    """Async-обёртка для set_dialog_state"""
    try:
        return await sync_to_async(set_dialog_state)(telegram_id, state, ttl)
    except Exception as e:
        logger.error(f"Failed to set dialog state for {telegram_id}: {e}")
        return False

async def aclear_dialog_state(telegram_id: int) -> bool:
    """Async-обёртка для clear_dialog_state"""
    try:
        return await sync_to_async(clear_dialog_state)(telegram_id)
    except Exception as e:
        logger.error(f"Failed to clear dialog state for {telegram_id}: {e}")
        return False
```

### 7.3 Защита callback'ов проверкой роли

```python
# bot/handlers/callbacks.py — добавить role check

async def callback_query_handler(update, context):
    query = update.callback_query
    data = query.data
    
    # === TEACHER-ONLY callbacks ===
    teacher_prefixes = ('rl_', 'rh_', 'check_hw:', 'not_submitted:', 'ping:',
                        'ping_send_now', 'action:remind_', 'action:check_hw')
    
    if any(data.startswith(p) for p in teacher_prefixes) or data in ('ping_send_now',):
        user = context.user_data.get('db_user')
        if not user:
            user = await get_user_by_telegram_id(str(update.effective_user.id))
        if not user or user.role not in ('teacher', 'admin'):
            await query.answer("Эта функция доступна только преподавателям.", show_alert=True)
            return
        context.user_data['db_user'] = user
    
    # === STUDENT-ONLY callbacks ===
    student_prefixes = ('st_lesson:', 'st_hw:', 'st_grades')
    if any(data.startswith(p) for p in student_prefixes) or data in ('st_grades',):
        user = context.user_data.get('db_user')
        if not user:
            user = await get_user_by_telegram_id(str(update.effective_user.id))
        if not user or user.role != 'student':
            await query.answer("Эта функция доступна только ученикам.", show_alert=True)
            return
        context.user_data['db_user'] = user
    
    # ... далее существующий роутинг
```

### 7.4 Безопасный парсинг callback_data

```python
# bot/utils/helpers.py — новый файл

def safe_parse_id(callback_data: str, prefix: str) -> Optional[int]:
    """
    Безопасно извлекает ID из callback_data.
    'check_hw:42' → 42
    'check_hw:abc' → None
    """
    try:
        raw = callback_data.removeprefix(prefix)
        return int(raw)
    except (ValueError, AttributeError):
        return None
```

### 7.5 Обработка удалённых сущностей

```python
# Пример для check_hw_selected:
async def check_hw_selected(update, context):
    query = update.callback_query
    await query.answer()
    
    homework_id = safe_parse_id(query.data, 'check_hw:')
    if homework_id is None:
        await query.edit_message_text("Некорректные данные.")
        return
    
    try:
        stats = await HomeworkService.get_homework_stats(homework_id)
    except Homework.DoesNotExist:
        await query.edit_message_text("Домашнее задание не найдено или удалено.")
        return
    except Exception as e:
        logger.error(f"Error getting HW stats for {homework_id}: {e}")
        await query.edit_message_text("Ошибка при загрузке данных. Попробуйте позже.")
        return
```

### 7.6 Исправить `tasks.py::process_scheduled_messages`

Задача обращается к полям `target_type` и `target_ids`, которых нет в модели. Заменить на работу с M2M полями (`target_groups`, `target_students`):

```python
# Исправленная версия
for msg in messages:
    try:
        msg.status = 'sending'
        msg.save(update_fields=['status'])
        
        # Собираем получателей из M2M
        telegram_ids = set()
        for group in msg.target_groups.all():
            for student in group.students.filter(
                is_active=True, notification_consent=True,
                telegram_id__isnull=False
            ).exclude(telegram_id=''):
                telegram_ids.add(student.telegram_id)
        
        for student in msg.target_students.filter(
            is_active=True, notification_consent=True,
            telegram_id__isnull=False
        ).exclude(telegram_id=''):
            telegram_ids.add(student.telegram_id)
        
        if not telegram_ids:
            msg.mark_sent(0, 0)
            continue
        
        result = async_to_sync(service.broadcast_to_users)(
            telegram_ids=list(telegram_ids),
            text=msg.content,
            teacher_id=msg.teacher_id,
            message_type=msg.message_type,
        )
        
        msg.mark_sent(result['sent_count'], result['failed_count'])
        sent_count += 1
    except Exception as e:
        ...
```

---

## 8. Приоритет исправлений

| Приоритет | Задача | Сложность | Риск на проде |
|-----------|--------|-----------|---------------|
| P0 | Async state wrappers (aget/aset/aclear) | Низкая | Нулевой (новые функции) |
| P0 | Error handler в main.py | Низкая | Нулевой (additive) |
| P1 | Role check в callback router | Средняя | Низкий |
| P1 | Fix tasks.py target_type/target_ids | Средняя | Нулевой (исправление бага) |
| P2 | Увеличить TTL wizard'ов | Тривиальная | Нулевой |
| P2 | Safe parse callback_data | Низкая | Нулевой |
| P3 | Проверка принадлежности урока студенту | Низкая | Низкий |

---

## 9. Реализованные исправления (2026-02-05)

### Исправлено в этом аудите:

| # | Файл | Что сделано | Статус |
|---|------|-------------|--------|
| 1 | `bot/utils/state.py` | Добавлены async-обёртки `aget_dialog_state`, `aset_dialog_state`, `aupdate_dialog_state`, `aclear_dialog_state` через `sync_to_async`. Исправлен импорт `from .config` → `from ..config` | DONE |
| 2 | `bot/utils/__init__.py` | Добавлены экспорты 4 async state-функций | DONE |
| 3 | `bot/main.py` | Добавлен глобальный `error_handler` — ловит все исключения, логирует, отвечает пользователю | DONE |
| 4 | `bot/handlers/callbacks.py` | Добавлена проверка ролей перед маршрутизацией callback'ов (teacher/student) | DONE |
| 5 | `bot/tasks.py` | Исправлен `process_scheduled_messages` — заменены несуществующие `target_type`/`target_ids` на корректные M2M поля (`target_groups.all()`, `target_students.filter()`) | DONE |
| 6 | `bot/tasks.py` | Исправлен `cleanup_old_broadcast_logs` — `hour_start` → `hour_key` | DONE |
| 7 | `bot/config.py` | TTL wizard'ов: 5 мин → 15 мин | DONE |
| 8 | `bot/handlers/teacher/lessons.py` | Исправлен импорт: `from ..utils` → `from ...utils`, `from ..keyboards` → `from ...keyboards`, `from ..services` → `from ...services` | DONE |
| 9 | `bot/handlers/teacher/homework.py` | Аналогичное исправление импортов (3 точки вместо 2) | DONE |
| 10 | `bot/handlers/student/lessons.py` | Аналогичное исправление импортов | DONE |
| 11 | `bot/handlers/student/homework.py` | Аналогичное исправление импортов | DONE |
| 12 | `bot/handlers/student/progress.py` | Аналогичное исправление импортов | DONE |

### Проблема импортов (подробно):

Все handler-файлы в подпакетах `bot/handlers/teacher/` и `bot/handlers/student/` использовали `from ..utils import ...`. Python разрешал `..` как "на 2 уровня вверх в пакете":
- `bot.handlers.teacher.lessons` → `..` = `bot.handlers` → `bot.handlers.utils` (НЕ СУЩЕСТВУЕТ)

Правильно: `from ...utils` (3 точки) → `bot.utils`.

Бот работал в продакшене потому что handler-модули загружались лениво (только при вызове команды), но `python manage.py test bot` падал с `ModuleNotFoundError` при попытке обнаружить тесты.

### Верификация:

```
manage.py check:               System check identified no issues (0 silenced)
homework.tests + analytics.tests: OK (12 tests)
Bot handler imports:            All imports OK (verified via python -c)
schedule.tests:                 2 pre-existing failures (subscription check)
```
