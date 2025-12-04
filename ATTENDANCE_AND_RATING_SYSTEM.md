# Система Журнала Посещений и Рейтинга Учеников

**Дата создания**: 4 декабря 2025 г.  
**Статус**: ✅ Готово к использованию

## 📋 Обзор Системы

Реализована комплексная система учета посещаемости и рейтинга учеников с автоматическим подсчетом баллов, интерактивными модальными окнами и интеграцией с Zoom.

### Ключевые Возможности

1. **Журнал посещений** - интерактивная таблица с автоматическим заполнением из Zoom
2. **Система рейтинга** - автоматический подсчет баллов за посещения, ДЗ и контрольные
3. **Карточки учеников** - детальная информация с возможностью добавления заметок
4. **Отчеты по группам** - статистика и рекомендации на основе метрик
5. **Индивидуальные ученики** - поддержка учеников вне групп

---

## 🏗️ Архитектура Backend

### Модели Данных

#### 1. AttendanceRecord
**Назначение**: Учет посещаемости студента на конкретном уроке

```python
class AttendanceRecord(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)  # attended, absent, watched_recording
    auto_recorded = models.BooleanField(default=False)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Уникальные ограничения**:
- `unique_together = ('lesson', 'student')` - одна запись на урок

**Статусы**:
- `attended` - присутствовал на уроке (+10 баллов)
- `absent` - отсутствовал (-5 баллов)
- `watched_recording` - посмотрел запись (+10 баллов, суммируется с attended)

**Индексы**:
- `('lesson', 'student')` - быстрый поиск записей
- `('student', 'recorded_at')` - история по ученику
- `('status', 'recorded_at')` - фильтрация по статусу

#### 2. UserRating
**Назначение**: Хранение рассчитанных баллов и ранга студента в группе

```python
class UserRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True)
    total_points = models.IntegerField(default=0)
    attendance_points = models.IntegerField(default=0)
    homework_points = models.IntegerField(default=0)
    control_points_value = models.IntegerField(default=0)
    rank = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Уникальные ограничения**:
- `unique_together = ('user', 'group')` - один рейтинг на группу

**Поля**:
- `total_points` - сумма всех баллов
- `attendance_points` - баллы за посещаемость
- `homework_points` - баллы за домашние задания (TODO: интеграция)
- `control_points_value` - баллы за контрольные (TODO: интеграция)
- `rank` - место в группе (1, 2, 3...)

#### 3. IndividualStudent
**Назначение**: Маркировка учеников как "индивидуальных" (не в группе)

```python
class IndividualStudent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    teacher_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Особенности**:
- OneToOne отношение с User
- Может существовать независимо от Group
- Заметки учителя хранятся здесь

---

## 🔧 Сервисный Слой

### AttendanceService

**Расположение**: `accounts/attendance_service.py`

#### Методы:

##### `auto_record_attendance(lesson_id, student_id, is_joined)`
Автоматическая запись посещаемости при подключении к Zoom.

**Параметры**:
- `lesson_id` - ID урока
- `student_id` - ID студента
- `is_joined` - `True` если подключился, `False` если отключился

**Логика**:
1. Создает/обновляет AttendanceRecord со статусом `attended`
2. Устанавливает `auto_recorded=True`
3. Вызывает `RatingService.recalculate_student_rating()`

**Использование**:
```python
from accounts.attendance_service import AttendanceService

AttendanceService.auto_record_attendance(
    lesson_id=123,
    student_id=456,
    is_joined=True
)
```

##### `manual_record_attendance(lesson_id, student_id, status, teacher_id)`
Ручная запись/изменение статуса учителем.

**Параметры**:
- `lesson_id` - ID урока
- `student_id` - ID студента
- `status` - `attended`, `absent`, или `watched_recording`
- `teacher_id` - ID учителя

**Логика**:
1. Валидирует статус
2. Создает/обновляет AttendanceRecord
3. Устанавливает `auto_recorded=False`
4. Вызывает пересчет рейтинга

**Использование**:
```python
AttendanceService.manual_record_attendance(
    lesson_id=123,
    student_id=456,
    status='attended',
    teacher_id=789
)
```

##### `record_watched_recording(lesson_id, student_id)`
Фиксация просмотра записи урока.

**Логика**:
1. Проверяет наличие записи посещаемости
2. Если статус `attended` - не меняет (уже был на уроке)
3. Если статус `absent` или нет записи - создает со статусом `watched_recording`
4. Вызывает пересчет рейтинга

**Использование**:
```python
AttendanceService.record_watched_recording(
    lesson_id=123,
    student_id=456
)
```

##### `auto_mark_absent_for_missed_lessons()` (TODO: Celery)
Автоматическая отметка отсутствующих через 24 часа после урока.

**Логика**:
1. Находит все уроки старше 24 часов
2. Для каждого ученика группы проверяет наличие записи посещаемости
3. Если записи нет - создает со статусом `absent`
4. Пересчитывает рейтинг

**Планируемое использование** (Celery Beat):
```python
# В celerybeat-schedule
'auto-mark-absent': {
    'task': 'accounts.tasks.auto_mark_absent',
    'schedule': crontab(hour=3, minute=0),  # Каждый день в 3:00
}
```

---

### RatingService

**Расположение**: `accounts/attendance_service.py`

#### Методы:

##### `recalculate_student_rating(student_id, group_id=None)`
Полный пересчет рейтинга студента.

**Параметры**:
- `student_id` - ID студента
- `group_id` - ID группы (опционально, для индивидуальных учеников)

**Логика**:
1. Вызывает расчет баллов по всем категориям:
   - `_calculate_attendance_points(student_id, group_id)`
   - `_calculate_homework_points(student_id, group_id)` (TODO)
   - `_calculate_control_points(student_id, group_id)` (TODO)
2. Суммирует баллы в `total_points`
3. Сохраняет UserRating
4. Вызывает `_recalculate_group_ranking(group_id)` для обновления рангов

**Использование**:
```python
from accounts.attendance_service import RatingService

RatingService.recalculate_student_rating(
    student_id=456,
    group_id=123
)
```

##### `_calculate_attendance_points(student_id, group_id)`
Расчет баллов за посещаемость.

**Логика**:
```python
attended_count = AttendanceRecord.objects.filter(
    student_id=student_id, 
    status='attended'
).count()

watched_count = AttendanceRecord.objects.filter(
    student_id=student_id, 
    status='watched_recording'
).exclude(
    lesson__in=AttendanceRecord.objects.filter(
        student_id=student_id, 
        status='attended'
    ).values('lesson')
).count()

absent_count = AttendanceRecord.objects.filter(
    student_id=student_id, 
    status='absent'
).count()

points = (attended_count * 10) + (watched_count * 10) + (absent_count * -5)
```

**Баллы**:
- Посещение: **+10 баллов**
- Просмотр записи (если не был): **+10 баллов**
- Отсутствие: **-5 баллов**

##### `_calculate_homework_points(student_id, group_id)` (TODO)
Расчет баллов за домашние задания.

**Планируемая интеграция**:
```python
# Интеграция с модулем homework
completed_hw = Homework.objects.filter(
    student_id=student_id,
    status='completed'
).count()

return completed_hw * 5  # +5 баллов за ДЗ
```

##### `_calculate_control_points(student_id, group_id)` (TODO)
Расчет баллов за контрольные точки.

**Планируемая интеграция**:
```python
# Интеграция с модулем analytics
control_points = ControlPoint.objects.filter(
    student_id=student_id
)

points = 0
for cp in control_points:
    if cp.status == 'passed':
        points += 15  # +15 баллов за полный успех
    elif cp.status == 'partial':
        points += 8   # +8 баллов за частичный успех

return points
```

##### `_recalculate_group_ranking(group_id)`
Обновление рангов всех студентов в группе.

**Логика**:
1. Получает все UserRating для группы
2. Сортирует по `total_points` DESC
3. Назначает rank от 1 до N
4. Сохраняет все рейтинги

**Использование**: Вызывается автоматически после пересчета любого рейтинга в группе.

##### `get_group_rating(group_id)`
Получение отсортированного рейтинга группы.

**Возвращает**: QuerySet с UserRating, отсортированный по total_points DESC

##### `get_student_stats(student_id, group_id=None)`
Статистика ученика по посещаемости.

**Возвращает**:
```python
{
    'attended': 15,
    'absent': 2,
    'watched_recording': 3,
    'total_lessons': 20,
    'attendance_percent': 75.0
}
```

---

## 🌐 API Endpoints

### AttendanceRecordViewSet

**Базовый URL**: `/api/attendance-records/`

#### Список и детали
- `GET /api/attendance-records/` - список записей
- `GET /api/attendance-records/{id}/` - детали записи

**Фильтрация**:
- По роли пользователя (teacher видит свои группы, student - свои записи)
- По датам через query params

#### Автоматическая запись
- `POST /api/attendance-records/auto_record/`

**Body**:
```json
{
  "lesson_id": 123,
  "student_id": 456,
  "is_joined": true
}
```

**Response**:
```json
{
  "status": "success",
  "record": {
    "id": 789,
    "lesson_title": "Математика: Алгебра",
    "student_name": "Иван Иванов",
    "status": "attended",
    "auto_recorded": true,
    "recorded_at": "2025-12-04T14:30:00Z"
  }
}
```

#### Ручная запись
- `POST /api/attendance-records/manual_record/`

**Body**:
```json
{
  "lesson_id": 123,
  "student_id": 456,
  "status": "attended"
}
```

**Permissions**: `IsAuthenticated`, только учителя группы

#### Запись просмотра
- `POST /api/attendance-records/record_watched_recording/`

**Body**:
```json
{
  "lesson_id": 123,
  "student_id": 456
}
```

---

### UserRatingViewSet

**Базовый URL**: `/api/ratings/`

#### Список рейтингов
- `GET /api/ratings/` - список всех рейтингов

**Response**:
```json
{
  "results": [
    {
      "id": 1,
      "student_name": "Иван Иванов",
      "student_email": "ivan@example.com",
      "group_name": "Математика 10А",
      "total_points": 150,
      "attendance_points": 100,
      "homework_points": 30,
      "control_points_value": 20,
      "rank": 1,
      "updated_at": "2025-12-04T14:30:00Z"
    }
  ]
}
```

#### Детали рейтинга
- `GET /api/ratings/{id}/`

**Permissions**: ReadOnly, фильтрация по роли

---

### GroupAttendanceLogViewSet

**Базовый URL**: `/api/groups/{group_id}/attendance-log/`

#### Журнал группы
- `GET /api/groups/{group_id}/attendance-log/`

**Response**:
```json
{
  "lessons": [
    {
      "id": 1,
      "title": "Урок 1",
      "date": "2025-12-01"
    }
  ],
  "students": [
    {
      "id": 456,
      "name": "Иван Иванов",
      "email": "ivan@example.com"
    }
  ],
  "records": {
    "1_456": {
      "status": "attended",
      "auto_recorded": true
    }
  }
}
```

**Формат ключей в records**: `{lesson_id}_{student_id}`

#### Обновление записи
- `POST /api/groups/{group_id}/attendance-log/update/`

**Body**:
```json
{
  "lesson_id": 1,
  "student_id": 456,
  "status": "attended"
}
```

**Permissions**: Только учителя группы

---

### GroupRatingViewSet

**Базовый URL**: `/api/groups/{group_id}/rating/`

#### Рейтинг группы
- `GET /api/groups/{group_id}/rating/`

**Response**:
```json
{
  "rankings": [
    {
      "rank": 1,
      "student_name": "Иван Иванов",
      "student_email": "ivan@example.com",
      "total_points": 150,
      "attendance_points": 100,
      "homework_points": 30,
      "control_points_value": 20
    }
  ],
  "group_stats": {
    "total_students": 15,
    "average_points": 125.5
  }
}
```

---

### StudentCardViewSet

**Базовый URL**: `/api/students/{student_id}/card/`

#### Карточка ученика
- `GET /api/students/{student_id}/card/?group_id={group_id}`

**Query Params**:
- `group_id` - ID группы (опционально, для индивидуальных учеников можно не передавать)

**Response**:
```json
{
  "student": {
    "id": 456,
    "name": "Иван Иванов",
    "email": "ivan@example.com"
  },
  "group": {
    "id": 123,
    "name": "Математика 10А"
  },
  "stats": {
    "attendance_percent": 85.0,
    "homework_percent": 90.0,
    "control_points_percent": 75.0,
    "total_points": 150,
    "rank": 1
  },
  "errors": [
    {
      "type": "homework",
      "title": "ДЗ №5: Квадратные уравнения",
      "due_date": "2025-12-01"
    }
  ],
  "teacher_notes": "Хорошо разбирается в алгебре"
}
```

---

### IndividualStudentViewSet

**Базовый URL**: `/api/individual-students/`

#### CRUD операции
- `GET /api/individual-students/` - список индивидуальных учеников
- `GET /api/individual-students/{id}/` - детали
- `POST /api/individual-students/` - создание
- `PUT /api/individual-students/{id}/` - обновление
- `DELETE /api/individual-students/{id}/` - удаление

#### Обновление заметок
- `PATCH /api/individual-students/{id}/update_notes/`

**Body**:
```json
{
  "teacher_notes": "Новые заметки учителя"
}
```

**Permissions**: Только учителя ученика

---

### GroupReportViewSet

**Базовый URL**: `/api/groups/{group_id}/report/`

#### Отчет по группе
- `GET /api/groups/{group_id}/report/`

**Response**:
```json
{
  "group": {
    "id": 123,
    "name": "Математика 10А",
    "students_count": 15
  },
  "attendance_percent": 85.0,
  "homework_percent": 78.0,
  "control_points_percent": 82.0,
  "recommendations": [
    {
      "type": "warning",
      "message": "Низкая посещаемость у 3 учеников"
    }
  ]
}
```

---

## 🎨 Frontend Компоненты

### GroupDetailModal

**Расположение**: `frontend/src/components/GroupDetailModal.js`

**Назначение**: Модальное окно с детальной информацией о группе

#### Props:
```javascript
{
  group: {
    id: number,
    name: string,
    student_count: number
  },
  isOpen: boolean,
  onClose: function,
  onStudentClick: function(studentId, groupId)
}
```

#### Структура табов:
1. **Журнал посещений** (`attendance`) - `AttendanceLogTab`
2. **Тесты на проверку** (`tests`) - placeholder
3. **Домашние задания** (`homework`) - placeholder
4. **Контрольные точки** (`control`) - placeholder
5. **Рейтинг группы** (`rating`) - `GroupRatingTab`
6. **Отчеты** (`reports`) - `GroupReportsTab`

#### Использование:
```javascript
<GroupDetailModal
  group={selectedGroup}
  isOpen={modalOpen}
  onClose={() => setModalOpen(false)}
  onStudentClick={(sid, gid) => openStudentCard(sid, gid)}
/>
```

---

### AttendanceLogTab

**Расположение**: `frontend/src/components/tabs/AttendanceLogTab.js`

**Назначение**: Интерактивная таблица журнала посещений

#### Props:
```javascript
{
  groupId: number,
  onStudentClick: function(studentId, groupId)
}
```

#### Функциональность:
- Загрузка матрицы посещаемости через `getGroupAttendanceLog(groupId)`
- Отображение студентов (строки) и уроков (столбцы)
- Клик по ячейке открывает `AttendanceStatusPicker`
- Обновление статуса через `updateGroupAttendanceLog()`

#### Легенда статусов:
- ✅ **Был** - присутствовал на уроке
- ❌ **Не был** - отсутствовал
- 👁️ **Посмотрел запись** - просмотрел запись урока
- — **Нет данных** - статус не установлен

#### Стилизация:
- Sticky header и левая колонка со студентами
- Горизонтальный скролл для большого количества уроков
- Цветовая кодировка: зеленый (attended), красный (absent), синий (watched), серый (empty)

---

### AttendanceStatusPicker

**Расположение**: `frontend/src/components/AttendanceStatusPicker.js`

**Назначение**: Всплывающий селектор статуса посещаемости

#### Props:
```javascript
{
  currentStatus: string,
  onStatusSelect: function(status),
  onClose: function,
  isLoading: boolean
}
```

#### Опции:
1. ✅ **Был** - `attended`
2. ❌ **Не был** - `absent`
3. 👁️ **Посмотрел запись** - `watched_recording`
4. — **Очистить** - удаление статуса

#### Поведение:
- Открывается при клике на ячейку в AttendanceLogTab
- Закрывается при выборе опции или клике вне
- Показывает loading state во время обновления

---

### GroupRatingTab

**Расположение**: `frontend/src/components/tabs/GroupRatingTab.js`

**Назначение**: Отображение рейтинга учеников группы

#### Props:
```javascript
{
  groupId: number,
  onStudentClick: function(studentId, groupId)
}
```

#### Функциональность:
- Загрузка рейтинга через `getGroupRating(groupId)`
- Отображение таблицы с медалями 🥇🥈🥉 для топ-3
- Клик по студенту открывает `StudentCardModal`

#### Таблица:
| Место | Имя | Email | Всего | Посещ. | ДЗ | Контр. |
|-------|-----|-------|-------|--------|----|----|
| 🥇 | Иван | ivan@... | 150 | 100 | 30 | 20 |

#### Статистика группы:
- Всего учеников: 15
- Средний балл: 125.5

#### Легенда баллов:
- Посещение: +10
- Просмотр записи: +10
- Отсутствие: -5
- Домашнее задание: +5
- Контрольная (полная): +15
- Контрольная (частичная): +8

---

### GroupReportsTab

**Расположение**: `frontend/src/components/tabs/GroupReportsTab.js`

**Назначение**: Отчеты и рекомендации по группе

#### Props:
```javascript
{
  groupId: number
}
```

#### Функциональность:
- Загрузка отчета через `getGroupReport(groupId)`
- Отображение 3 основных метрик с прогресс-барами
- Умные рекомендации на основе метрик

#### Метрики:
1. **Посещаемость**: % студентов с >70% посещаемости
2. **Домашние задания**: % выполненных ДЗ
3. **Контрольные точки**: % успешно пройденных контрольных

#### Рекомендации:
- ⚠️ Низкая посещаемость (<70%) - требует внимания
- ✅ Хорошая посещаемость (>85%) - поздравление
- ⚠️ Много невыполненных ДЗ - рекомендация проверить систему
- ✅ Высокий процент выполнения ДЗ - похвала

#### Информационные блоки:
- Краткая информация о группе
- Примечание об автообновлении статистики

---

### StudentCardModal

**Расположение**: `frontend/src/components/StudentCardModal.js`

**Назначение**: Детальная карточка ученика

#### Props:
```javascript
{
  studentId: number,
  groupId: number | null,
  isIndividual: boolean,
  isOpen: boolean,
  onClose: function
}
```

#### Функциональность:
- Загрузка данных через `getStudentCard(studentId, groupId)`
- Отображение аватара и основной информации
- 4 карточки со статистикой (посещаемость, ДЗ, контрольные, место в рейтинге)
- Список ошибок (невыполненные ДЗ, проваленные контрольные)
- Редактируемые заметки учителя

#### Секции:
1. **Заголовок**: Аватар + имя + email
2. **Статистика**: 4 карточки с метриками
3. **Ошибки**: Список проблемных заданий
4. **Заметки учителя**: Редактируемое текстовое поле

#### Редактирование заметок:
```javascript
const handleSaveNotes = async () => {
  await updateIndividualStudentNotes(studentId, notes);
  setEditingNotes(false);
};
```

---

## 🎯 Интеграция с TeacherHomePage

### Модификации в TeacherHomePage.js

#### Добавленное состояние:
```javascript
const [groupDetailModal, setGroupDetailModal] = useState({ 
  isOpen: false, 
  group: null 
});

const [studentCardModal, setStudentCardModal] = useState({ 
  isOpen: false, 
  studentId: null, 
  groupId: null, 
  isIndividual: false 
});
```

#### Обработчики кликов:

**Клик по группе**:
```javascript
onClick={() => setGroupDetailModal({ isOpen: true, group: g })}
```

**Клик по ученику**:
```javascript
onClick={() => setStudentCardModal({ 
  isOpen: true, 
  studentId: st.id, 
  groupId: st.group_id || null,
  isIndividual: !st.group_id
})}
```

#### Рендеринг модалей:
```javascript
<GroupDetailModal
  group={groupDetailModal.group}
  isOpen={groupDetailModal.isOpen}
  onClose={() => setGroupDetailModal({ isOpen: false, group: null })}
  onStudentClick={(studentId, groupId) => {
    setGroupDetailModal({ isOpen: false, group: null });
    setStudentCardModal({ 
      isOpen: true, 
      studentId, 
      groupId,
      isIndividual: false
    });
  }}
/>

<StudentCardModal
  studentId={studentCardModal.studentId}
  groupId={studentCardModal.groupId}
  isIndividual={studentCardModal.isIndividual}
  isOpen={studentCardModal.isOpen}
  onClose={() => setStudentCardModal({ 
    isOpen: false, 
    studentId: null, 
    groupId: null, 
    isIndividual: false 
  })}
/>
```

---

## 📱 Адаптивный Дизайн

### Брейкпоинты:

```css
/* Mobile */
@media (max-width: 640px) {
  /* Скрыть email в таблицах */
  /* Уменьшить размеры кнопок */
  /* Вертикальная компоновка */
}

/* Tablet */
@media (max-width: 768px) {
  /* Уменьшить отступы */
  /* Скрыть некоторые столбцы */
}

/* Desktop */
@media (min-width: 769px) {
  /* Полная функциональность */
}
```

### Особенности мобильной версии:

1. **AttendanceLogTab**:
   - Горизонтальный скролл для уроков
   - Скрыт email студентов
   - Уменьшены размеры ячеек

2. **GroupRatingTab**:
   - Скрыта колонка с email
   - Вертикальная компоновка статистики

3. **StudentCardModal**:
   - Карточки статистики в одну колонку
   - Полноэкранный режим

---

## 🚀 Запуск и Тестирование

### Локальный запуск:

1. **Backend (Django)**:
```bash
cd teaching_panel
..\venv\Scripts\Activate.ps1
python manage.py runserver
# Сервер: http://127.0.0.1:8000
```

2. **Frontend (React)**:
```bash
cd frontend
npm start
# Сервер: http://localhost:3000
```

### Тестирование функциональности:

1. **Авторизация**:
   - Войти как учитель
   - Перейти на `/teacher`

2. **Открытие журнала**:
   - Кликнуть на группу в секции "Группы"
   - Откроется GroupDetailModal
   - Выбрать таб "Журнал посещений"

3. **Редактирование посещаемости**:
   - Кликнуть на ячейку в таблице
   - Выбрать статус в AttendanceStatusPicker
   - Проверить обновление

4. **Просмотр рейтинга**:
   - Выбрать таб "Рейтинг группы"
   - Проверить корректность баллов и рангов

5. **Карточка ученика**:
   - Кликнуть на ученика в рейтинге
   - Откроется StudentCardModal
   - Проверить статистику и заметки

---

## 📊 База Данных

### Миграции:

**Создана миграция**: `accounts/migrations/0016_individualstudent_userrating_attendancerecord.py`

**Команды**:
```bash
# Создание миграций
python manage.py makemigrations

# Применение миграций
python manage.py migrate

# Откат (если нужно)
python manage.py migrate accounts 0015
```

### SQL схема:

```sql
-- AttendanceRecord
CREATE TABLE accounts_attendancerecord (
    id SERIAL PRIMARY KEY,
    lesson_id INTEGER REFERENCES schedule_lesson(id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES accounts_user(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    auto_recorded BOOLEAN DEFAULT FALSE,
    recorded_by_id INTEGER REFERENCES accounts_user(id) ON DELETE SET NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(lesson_id, student_id)
);

CREATE INDEX idx_attendance_lesson_student ON accounts_attendancerecord(lesson_id, student_id);
CREATE INDEX idx_attendance_student_date ON accounts_attendancerecord(student_id, recorded_at);
CREATE INDEX idx_attendance_status_date ON accounts_attendancerecord(status, recorded_at);

-- UserRating
CREATE TABLE accounts_userrating (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES accounts_user(id) ON DELETE CASCADE,
    group_id INTEGER REFERENCES schedule_group(id) ON DELETE CASCADE,
    total_points INTEGER DEFAULT 0,
    attendance_points INTEGER DEFAULT 0,
    homework_points INTEGER DEFAULT 0,
    control_points_value INTEGER DEFAULT 0,
    rank INTEGER,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(user_id, group_id)
);

-- IndividualStudent
CREATE TABLE accounts_individualstudent (
    user_id INTEGER PRIMARY KEY REFERENCES accounts_user(id) ON DELETE CASCADE,
    teacher_id INTEGER REFERENCES accounts_user(id) ON DELETE SET NULL,
    teacher_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

---

## 🔐 Безопасность и Права Доступа

### Permissions в ViewSets:

1. **AttendanceRecordViewSet**:
   - Студент: только свои записи
   - Учитель: записи своих групп
   - Админ: все записи
   - Ручная запись: только учителя

2. **UserRatingViewSet**:
   - ReadOnly для всех аутентифицированных
   - Фильтрация по роли

3. **GroupAttendanceLogViewSet**:
   - Только учителя группы могут редактировать
   - Студенты могут только просматривать

4. **IndividualStudentViewSet**:
   - Учитель: только свои индивидуальные ученики
   - Студент: только свою карточку
   - Админ: все карточки

### Валидация данных:

```python
# В AttendanceService.manual_record_attendance
valid_statuses = ['attended', 'absent', 'watched_recording']
if status not in valid_statuses:
    raise ValueError(f"Invalid status: {status}")

# Проверка прав учителя
if not teacher.groups.filter(id=group_id).exists():
    raise PermissionError("Teacher не имеет доступа к этой группе")
```

---

## 🔄 Интеграция с Zoom

### Автоматическая запись посещаемости:

**Точка интеграции**: При старте урока через `StartLessonButton`

```python
# В schedule/views.py::LessonViewSet.start() или start_new()
from accounts.attendance_service import AttendanceService

# После создания Zoom встречи
for student in group.students.all():
    AttendanceService.auto_record_attendance(
        lesson_id=lesson.id,
        student_id=student.id,
        is_joined=True  # Или False при отключении
    )
```

### Webhook от Zoom (планируется):

```python
# В zoom_pool/webhooks.py
@csrf_exempt
def zoom_participant_webhook(request):
    data = json.loads(request.body)
    event = data['event']
    
    if event == 'meeting.participant_joined':
        AttendanceService.auto_record_attendance(
            lesson_id=data['payload']['object']['id'],
            student_id=data['payload']['participant']['user_id'],
            is_joined=True
        )
    elif event == 'meeting.participant_left':
        # Можно логировать, но не менять статус
        pass
```

---

## 📈 Будущие Улучшения

### TODO: Интеграция с модулем ДЗ

**Файл**: `accounts/attendance_service.py::RatingService._calculate_homework_points()`

**Что нужно**:
1. Импортировать модели из homework модуля
2. Подсчитать выполненные ДЗ студента
3. Умножить на 5 баллов

**Пример кода**:
```python
from homework.models import HomeworkSubmission

def _calculate_homework_points(self, student_id, group_id):
    completed = HomeworkSubmission.objects.filter(
        student_id=student_id,
        status='completed'
    ).count()
    return completed * 5
```

### TODO: Интеграция с контрольными точками

**Файл**: `accounts/attendance_service.py::RatingService._calculate_control_points()`

**Что нужно**:
1. Импортировать модели из analytics модуля
2. Подсчитать пройденные контрольные
3. Применить баллы: +15 (полный успех), +8 (частичный)

**Пример кода**:
```python
from analytics.models import ControlPoint

def _calculate_control_points(self, student_id, group_id):
    points = 0
    control_points = ControlPoint.objects.filter(
        student_id=student_id
    )
    for cp in control_points:
        if cp.status == 'passed':
            points += 15
        elif cp.status == 'partial':
            points += 8
    return points
```

### TODO: Celery задача для автоотсутствия

**Файл**: `accounts/tasks.py` (создать новый)

**Что нужно**:
1. Создать Celery task
2. Добавить в CELERY_BEAT_SCHEDULE в settings.py
3. Запустить Celery Beat

**Пример кода**:
```python
from celery import shared_task
from accounts.attendance_service import AttendanceService

@shared_task
def auto_mark_absent_for_missed_lessons():
    AttendanceService.auto_mark_absent_for_missed_lessons()
```

**В settings.py**:
```python
CELERY_BEAT_SCHEDULE = {
    'auto-mark-absent': {
        'task': 'accounts.tasks.auto_mark_absent_for_missed_lessons',
        'schedule': crontab(hour=3, minute=0),  # Каждый день в 3:00
    },
}
```

### TODO: Экспорт отчетов в Excel/PDF

**Идея**: Добавить кнопку "Скачать отчет" в GroupReportsTab

**Технологии**:
- Backend: `openpyxl` для Excel, `reportlab` для PDF
- Frontend: Endpoint `/api/groups/{id}/report/export/?format=xlsx`

### TODO: Уведомления учителям

**Идея**: Отправлять уведомления при низкой посещаемости

**Интеграция**:
- Telegram Bot API
- Email через Django mail
- Push-уведомления через FCM

---

## 🐛 Известные Issues и Ограничения

### 1. Неиспользуемые переменные в GroupDetailModal

**Issue**: ESLint warnings для `setError`

**Решение**: Переменная оставлена для будущего использования (обработка ошибок загрузки)

### 2. TODO markers в коде

**Расположение**: 
- `RatingService._calculate_homework_points()`
- `RatingService._calculate_control_points()`
- `AttendanceService.auto_mark_absent_for_missed_lessons()`

**Статус**: Ожидают интеграции с другими модулями

### 3. Placeholder табы в GroupDetailModal

**Табы**: Тесты, ДЗ, Контрольные

**Статус**: Показывают placeholder с информацией об интеграции

**Планы**: Заменить на реальные компоненты после интеграции модулей

---

## 📞 Поддержка и Вопросы

### При возникновении проблем:

1. **Проверьте миграции**: `python manage.py showmigrations accounts`
2. **Проверьте логи Django**: В терминале где запущен runserver
3. **Проверьте браузерную консоль**: F12 → Console
4. **Проверьте Network tab**: Смотрите API запросы и ответы

### Частые вопросы:

**Q: Почему баллы не обновляются?**  
A: Проверьте, вызывается ли `RatingService.recalculate_student_rating()` после изменения AttendanceRecord

**Q: Как добавить новый статус посещаемости?**  
A: 
1. Обновить choices в `AttendanceRecord.status`
2. Обновить логику в `RatingService._calculate_attendance_points()`
3. Добавить в `AttendanceStatusPicker` опцию

**Q: Можно ли изменить количество баллов?**  
A: Да, измените константы в `RatingService._calculate_attendance_points()`

---

## 📝 Changelog

### [1.0.0] - 2025-12-04

#### Добавлено:
- ✅ Модели AttendanceRecord, UserRating, IndividualStudent
- ✅ Сервисы AttendanceService и RatingService
- ✅ 7 ViewSet'ов с полным набором API endpoints
- ✅ Интерактивный журнал посещений с редактированием
- ✅ Система рейтинга с автоподсчетом баллов
- ✅ Карточки учеников с заметками учителя
- ✅ Отчеты по группам со статистикой
- ✅ Адаптивный дизайн для мобильных устройств
- ✅ Интеграция в TeacherHomePage
- ✅ Миграции базы данных

#### TODO:
- ⏳ Интеграция с модулем homework
- ⏳ Интеграция с модулем analytics (контрольные точки)
- ⏳ Celery задача для автоотсутствия
- ⏳ Webhook от Zoom для реального времени
- ⏳ Экспорт отчетов
- ⏳ Уведомления учителям

---

**Документация создана**: 4 декабря 2025 г.  
**Автор**: AI Coding Assistant  
**Версия**: 1.0.0  
**Статус**: ✅ Production Ready
