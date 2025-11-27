# Система учебных материалов - Полное руководство

## Обзор

Система учебных материалов позволяет преподавателям загружать теорию (для чтения перед уроком) и конспекты (после урока), а также отслеживать, какие ученики просмотрели материалы.

### Основные возможности

1. **Загрузка материалов**
   - Теория (📖) - материалы для подготовки перед уроком
   - Конспекты (📝) - материалы для повторения после урока
   - Поддержка ссылок на Google Drive, Dropbox и другие хранилища

2. **Отслеживание просмотров**
   - Автоматическая фиксация просмотра при открытии материала
   - Уникальная запись на каждого ученика (один просмотр на материал)
   - Статистика по каждому материалу и ученику

3. **Красивое отображение**
   - Разделение теории и конспектов
   - Индикаторы "Новое" и "Прочитано"
   - Адаптивный дизайн для всех устройств

---

## Backend

### Модели данных

#### LessonMaterial

```python
class LessonMaterial(models.Model):
    """Учебные материалы к уроку"""
    lesson = ForeignKey(Lesson)  # Связь с уроком
    material_type = CharField  # 'theory' или 'notes'
    title = CharField(max_length=200)
    description = TextField(blank=True)
    file_url = URLField  # Ссылка на Google Drive или другое хранилище
    file_name = CharField(max_length=200)
    file_size_bytes = BigIntegerField
    uploaded_by = ForeignKey(CustomUser)
    uploaded_at = DateTimeField(auto_now_add=True)
    views_count = IntegerField(default=0)
    
    @property
    def file_size_mb(self):
        return self.file_size_bytes / (1024 ** 2)
```

**Типы материалов:**
- `theory` - Теория (перед уроком)
- `notes` - Конспект (после урока)

#### MaterialView

```python
class MaterialView(models.Model):
    """Отслеживание просмотров"""
    material = ForeignKey(LessonMaterial)
    student = ForeignKey(CustomUser, limit_choices_to={'role': 'student'})
    viewed_at = DateTimeField(auto_now_add=True)
    duration_seconds = IntegerField(default=0)
    completed = BooleanField(default=False)
    
    class Meta:
        unique_together = [['material', 'student']]  # Один просмотр на ученика
```

### API Endpoints

#### 1. Загрузка материала (Преподаватель)

```http
POST /schedule/api/lessons/<lesson_id>/materials/upload/
Content-Type: application/json

{
    "material_type": "theory",  # или "notes"
    "title": "Введение в алгебру",
    "description": "Основные понятия и определения",
    "file_url": "https://drive.google.com/file/d/...",
    "file_name": "algebra_intro.pdf",
    "file_size_bytes": 1024000
}
```

**Ответ 201:**
```json
{
    "id": 42,
    "lesson_id": 15,
    "material_type": "theory",
    "title": "Введение в алгебру",
    "description": "Основные понятия и определения",
    "file_url": "https://drive.google.com/file/d/...",
    "file_name": "algebra_intro.pdf",
    "file_size_bytes": 1024000,
    "file_size_mb": 1.0,
    "uploaded_by": {
        "id": 3,
        "name": "Иван Петров",
        "email": "teacher@example.com"
    },
    "uploaded_at": "2025-01-22T14:30:00Z",
    "views_count": 0
}
```

#### 2. Список материалов урока

```http
GET /schedule/api/lessons/<lesson_id>/materials/?material_type=theory
```

**Параметры:**
- `material_type` (optional) - фильтр по типу: `theory` или `notes`

**Ответ 200 (для ученика):**
```json
{
    "lesson": {
        "id": 15,
        "title": "Урок математики",
        "teacher": {
            "id": 3,
            "name": "Иван Петров"
        }
    },
    "materials": [
        {
            "id": 42,
            "material_type": "theory",
            "material_type_display": "Теория (перед уроком)",
            "title": "Введение в алгебру",
            "description": "...",
            "file_url": "https://...",
            "file_name": "algebra_intro.pdf",
            "file_size_mb": 1.0,
            "views_count": 5,
            "is_viewed": true  // Только для ученика
        }
    ],
    "count": 1
}
```

#### 3. Детали материала

```http
GET /schedule/api/materials/<material_id>/
```

**Ответ 200:**
```json
{
    "id": 42,
    "lesson": {
        "id": 15,
        "title": "Урок математики",
        "start_time": "2025-01-22T15:00:00Z",
        "teacher": {
            "id": 3,
            "name": "Иван Петров"
        }
    },
    "material_type": "theory",
    "title": "Введение в алгебру",
    "file_url": "https://...",
    "views_count": 5,
    "view_info": {  // Только для ученика
        "viewed_at": "2025-01-22T14:35:00Z",
        "duration_seconds": 120,
        "completed": false
    }
}
```

#### 4. Отследить просмотр (Ученик)

```http
POST /schedule/api/materials/<material_id>/view/
Content-Type: application/json

{
    "duration_seconds": 120,  // optional
    "completed": true  // optional
}
```

**Ответ 200:**
```json
{
    "material_id": 42,
    "student_id": 10,
    "viewed_at": "2025-01-22T14:35:00Z",
    "duration_seconds": 120,
    "completed": true,
    "is_first_view": true  // true если первый просмотр, false если обновление
}
```

#### 5. Статистика просмотров материала (Преподаватель)

```http
GET /schedule/api/materials/<material_id>/views/
```

**Ответ 200:**
```json
{
    "material": {
        "id": 42,
        "title": "Введение в алгебру",
        "material_type": "theory",
        "views_count": 5
    },
    "statistics": {
        "total_students": 10,
        "viewed_count": 5,
        "not_viewed_count": 5,
        "completion_count": 2,
        "view_rate": 50.0,
        "completion_rate": 20.0
    },
    "students": [
        {
            "student_id": 10,
            "student_name": "Анна Смирнова",
            "student_email": "anna@example.com",
            "has_viewed": true,
            "viewed_at": "2025-01-22T14:35:00Z",
            "duration_seconds": 120,
            "completed": true
        },
        {
            "student_id": 11,
            "student_name": "Петр Иванов",
            "student_email": "peter@example.com",
            "has_viewed": false,
            "viewed_at": null,
            "duration_seconds": 0,
            "completed": false
        }
    ]
}
```

#### 6. Общая статистика урока (Преподаватель)

```http
GET /schedule/api/lessons/<lesson_id>/materials/statistics/
```

**Ответ 200:**
```json
{
    "lesson": {
        "id": 15,
        "title": "Урок математики",
        "start_time": "2025-01-22T15:00:00Z"
    },
    "summary": {
        "total_students": 10,
        "total_materials": 5,
        "theory_materials_count": 3,
        "notes_materials_count": 2,
        "total_views": 25,
        "avg_views_per_material": 5.0
    },
    "students": [
        {
            "student_id": 10,
            "student_name": "Анна Смирнова",
            "student_email": "anna@example.com",
            "theory_viewed": 2,
            "theory_total": 3,
            "theory_completed": 1,
            "notes_viewed": 1,
            "notes_total": 2,
            "notes_completed": 0,
            "total_views": 3
        }
    ]
}
```

#### 7. Удаление материала (Преподаватель)

```http
DELETE /schedule/api/materials/<material_id>/delete/
```

**Ответ 200:**
```json
{
    "message": "Материал \"Введение в алгебру\" успешно удален",
    "deleted_id": 42
}
```

---

## Frontend

### Компоненты

#### 1. LessonMaterialsManager (Преподаватель)

**Расположение:** `frontend/src/modules/Teacher/LessonMaterialsManager.js`

**Функциональность:**
- Общая статистика (материалы, просмотры, ученики)
- Форма загрузки нового материала
- Список материалов с разделением на теорию/конспекты
- Детальная статистика по каждому материалу (кто просмотрел)
- Удаление материалов

**Использование:**
```jsx
import LessonMaterialsManager from './modules/Teacher/LessonMaterialsManager';

<LessonMaterialsManager 
    lessonId={15}
    lessonTitle="Урок математики"
    onClose={() => setShowMaterials(false)}
/>
```

#### 2. LessonMaterialsViewer (Ученик)

**Расположение:** `frontend/src/modules/Student/LessonMaterialsViewer.js`

**Функциональность:**
- Красивое отображение теории и конспектов
- Индикаторы "Новое" и "Прочитано"
- Автоматическое отслеживание просмотров при клике
- Открытие материалов в новой вкладке

**Использование:**
```jsx
import LessonMaterialsViewer from './modules/Student/LessonMaterialsViewer';

<LessonMaterialsViewer 
    lessonId={15}
    lessonTitle="Урок математики"
    onClose={() => setShowMaterials(false)}
/>
```

---

## Интеграция в календарь/расписание

### Добавление кнопки в карточку урока

**Для преподавателя (TeacherSchedulePage):**

```jsx
// В компоненте карточки урока добавить:
const [showMaterials, setShowMaterials] = useState(false);

// Кнопка в карточке урока:
<button 
    className="btn-materials"
    onClick={() => setShowMaterials(true)}
>
    📚 Материалы ({lesson.materials_count || 0})
</button>

// Модальное окно:
{showMaterials && (
    <LessonMaterialsManager
        lessonId={lesson.id}
        lessonTitle={lesson.title}
        onClose={() => setShowMaterials(false)}
    />
)}
```

**Для ученика (StudentDashboard):**

```jsx
// Аналогично, но с LessonMaterialsViewer:
{showMaterials && (
    <LessonMaterialsViewer
        lessonId={lesson.id}
        lessonTitle={lesson.title}
        onClose={() => setShowMaterials(false)}
    />
)}
```

### Индикатор непрочитанных материалов

Добавить в API урока поле `unread_materials_count`:

```python
# В serializer урока добавить:
def get_unread_materials_count(self, obj):
    """Количество непрочитанных материалов для текущего ученика"""
    if not hasattr(self.context.get('request'), 'user'):
        return 0
    
    user = self.context['request'].user
    if user.role != 'student':
        return 0
    
    # Все материалы урока
    all_materials = LessonMaterial.objects.filter(lesson=obj)
    
    # Просмотренные материалы
    viewed_materials = MaterialView.objects.filter(
        material__lesson=obj,
        student=user
    ).values_list('material_id', flat=True)
    
    return all_materials.exclude(id__in=viewed_materials).count()
```

Затем показать бейдж:

```jsx
{lesson.unread_materials_count > 0 && (
    <span className="unread-badge">{lesson.unread_materials_count} новых</span>
)}
```

---

## Стилизация

### Цветовая схема

- **Теория:** Синий (`#3b82f6`) - для подготовки перед уроком
- **Конспекты:** Зеленый (`#10b981`) - для повторения после урока
- **Прочитано:** Зеленый с галочкой
- **Новое:** Желтый с анимацией (`#fbbf24`)

### Анимации

- Появление модального окна: `fadeIn` + `slideUp`
- Непрочитанные материалы: `pulse` (пульсация)
- Новый бейдж: `bounce` (подпрыгивание)
- Hover эффекты: `translateY` + `box-shadow`

---

## Миграция базы данных

### Применение миграций

```bash
# На сервере
cd /var/www/teaching_panel
source venv/bin/activate
python manage.py makemigrations schedule
python manage.py migrate schedule
```

### Проверка моделей

```python
# Django shell
python manage.py shell

from schedule.models import LessonMaterial, MaterialView

# Проверить таблицы
LessonMaterial.objects.count()
MaterialView.objects.count()
```

---

## Тестирование

### Создание тестовых материалов

```python
from schedule.models import Lesson, LessonMaterial, CustomUser

lesson = Lesson.objects.first()
teacher = CustomUser.objects.filter(role='teacher').first()

# Теория
LessonMaterial.objects.create(
    lesson=lesson,
    material_type='theory',
    title='Введение в тему',
    description='Базовые понятия и определения',
    file_url='https://drive.google.com/file/d/example123',
    file_name='intro.pdf',
    file_size_bytes=1024000,
    uploaded_by=teacher
)

# Конспект
LessonMaterial.objects.create(
    lesson=lesson,
    material_type='notes',
    title='Конспект урока',
    description='Основные моменты урока',
    file_url='https://drive.google.com/file/d/example456',
    file_name='notes.pdf',
    file_size_bytes=2048000,
    uploaded_by=teacher
)
```

### Тестирование API

```bash
# Загрузка материала
curl -X POST http://localhost:8000/schedule/api/lessons/15/materials/upload/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -d '{
    "material_type": "theory",
    "title": "Тестовый материал",
    "file_url": "https://example.com/file.pdf",
    "file_name": "test.pdf",
    "file_size_bytes": 1024000
  }'

# Список материалов
curl http://localhost:8000/schedule/api/lessons/15/materials/ \
  -H "Cookie: sessionid=..."

# Отследить просмотр
curl -X POST http://localhost:8000/schedule/api/materials/42/view/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -d '{}'

# Статистика
curl http://localhost:8000/schedule/api/materials/42/views/ \
  -H "Cookie: sessionid=..."
```

---

## Возможные улучшения

### 1. Загрузка файлов напрямую
Вместо ссылок на Google Drive, можно добавить прямую загрузку:
- Использовать Django FileField
- Интеграция с Google Drive API для автоматической загрузки
- Проверка типов файлов (PDF, DOCX, PPTX)

### 2. Встроенный PDF viewer
Добавить просмотр PDF прямо в модальном окне:
- Библиотека `react-pdf`
- Плеер для видео (если материал - видео)

### 3. Уведомления
Отправлять уведомления ученикам о новых материалах:
- Email при загрузке теории (за день до урока)
- Push-уведомления в браузере
- SMS через Twilio

### 4. Дедлайны
Установка дедлайнов для чтения материалов:
- "Прочитать до 20.01.2025 15:00"
- Автоматические напоминания
- Отображение просрочки в статистике

### 5. Квизы и проверка знаний
После чтения материала - мини-тест:
- 3-5 вопросов по теории
- Автоматическая проверка
- Статистика правильных ответов

---

## Troubleshooting

### Материалы не загружаются
1. Проверить права доступа к уроку (только преподаватель урока может загружать)
2. Проверить валидность URL (должен начинаться с http:// или https://)
3. Проверить формат JSON в запросе

### Просмотры не отслеживаются
1. Убедиться, что пользователь - ученик (role='student')
2. Проверить уникальность (material + student) - может быть уже записан
3. Проверить middleware аутентификации

### Статистика неверная
1. Проверить связь урока с группой или учеником
2. Убедиться, что ученики добавлены в группу
3. Проверить CASCADE при удалении материалов (views должны удаляться)

---

## Заключение

Система учебных материалов полностью интегрирована в платформу и готова к использованию. Преподаватели могут загружать материалы через удобный интерфейс, а ученики видят красиво оформленные карточки с индикаторами прочитанности. Вся статистика просмотров доступна преподавателю в реальном времени.
