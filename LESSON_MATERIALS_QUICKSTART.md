# Быстрый старт - Система учебных материалов

## Деплой на сервер за 10 минут

### Шаг 1: Коммит изменений (Локально)

```powershell
cd C:\Users\User\Desktop\nat

# Добавить все файлы
git add -A

# Коммит
git commit -m "Add lesson materials system with view tracking"

# Пуш
git push origin main
```

### Шаг 2: Обновление сервера

```bash
# Подключение к серверу
ssh root@72.56.81.163

# Переход в директорию проекта
cd /var/www/teaching_panel

# Остановка Gunicorn и Celery
sudo systemctl stop gunicorn
sudo systemctl stop celery

# Получение обновлений
git pull origin main

# Активация виртуального окружения
source venv/bin/activate

# Применение миграций
python manage.py makemigrations schedule
python manage.py migrate schedule

# Сборка статики (если нужно)
python manage.py collectstatic --noinput
```

### Шаг 3: Обновление Frontend

```bash
# На сервере в директории frontend
cd /var/www/teaching_panel/frontend

# Установка зависимостей (если добавились новые)
npm install

# Сборка
npm run build

# Копирование в статику
sudo cp -r build/* /var/www/teaching_panel/staticfiles/
```

### Шаг 4: Перезапуск сервисов

```bash
# Запуск Gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn

# Запуск Celery
sudo systemctl start celery
sudo systemctl status celery

# Перезапуск Nginx
sudo systemctl restart nginx
```

### Шаг 5: Проверка

#### Проверка миграций

```bash
cd /var/www/teaching_panel
source venv/bin/activate
python manage.py shell

# В shell:
from schedule.models import LessonMaterial, MaterialView
print(f"LessonMaterial: {LessonMaterial.objects.count()}")
print(f"MaterialView: {MaterialView.objects.count()}")
```

#### Проверка API

```bash
# Список материалов (замените session_id на реальный)
curl http://72.56.81.163/schedule/api/lessons/1/materials/ \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

#### Проверка Frontend

1. Откройте браузер: http://72.56.81.163
2. Войдите как преподаватель
3. Откройте календарь и кликните на урок
4. Должна быть кнопка "📚 Материалы"

---

## Быстрое тестирование

### Создание тестового материала через Django Shell

```python
cd /var/www/teaching_panel
source venv/bin/activate
python manage.py shell

# В shell:
from schedule.models import Lesson, LessonMaterial, CustomUser

# Получить первый урок и преподавателя
lesson = Lesson.objects.first()
teacher = lesson.teacher

# Создать теорию
theory = LessonMaterial.objects.create(
    lesson=lesson,
    material_type='theory',
    title='Введение в Python',
    description='Основы программирования на Python',
    file_url='https://drive.google.com/file/d/example123/view',
    file_name='python_intro.pdf',
    file_size_bytes=1500000,
    uploaded_by=teacher
)

print(f"Создан материал: {theory.id} - {theory.title}")

# Создать конспект
notes = LessonMaterial.objects.create(
    lesson=lesson,
    material_type='notes',
    title='Конспект урока Python',
    description='Основные команды и примеры',
    file_url='https://drive.google.com/file/d/example456/view',
    file_name='python_notes.pdf',
    file_size_bytes=800000,
    uploaded_by=teacher
)

print(f"Создан материал: {notes.id} - {notes.title}")
```

### Создание тестового просмотра

```python
# Продолжение в Django shell:
from schedule.models import MaterialView

# Получить ученика
student = CustomUser.objects.filter(role='student').first()

# Создать просмотр
view = MaterialView.objects.create(
    material=theory,
    student=student,
    duration_seconds=180,
    completed=True
)

print(f"Просмотр создан: {view.student.get_full_name()} → {view.material.title}")

# Обновить счетчик
theory.views_count += 1
theory.save()
```

---

## Интеграция в существующие компоненты

### 1. Добавление кнопки в TeacherSchedulePage

**Файл:** `frontend/src/modules/Teacher/TeacherSchedulePage.js`

Добавить в начало компонента:

```jsx
import LessonMaterialsManager from './LessonMaterialsManager';
```

В состояние компонента добавить:

```jsx
const [showMaterialsModal, setShowMaterialsModal] = useState(false);
const [selectedLesson, setSelectedLesson] = useState(null);
```

В карточку урока (внутри рендера урока) добавить кнопку:

```jsx
<button 
    className="btn-materials"
    onClick={() => {
        setSelectedLesson(lesson);
        setShowMaterialsModal(true);
    }}
    style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        border: 'none',
        padding: '8px 16px',
        borderRadius: '6px',
        cursor: 'pointer',
        fontSize: '14px',
        fontWeight: '600',
        marginTop: '8px'
    }}
>
    📚 Материалы
</button>
```

В конце компонента (перед closing tag):

```jsx
{showMaterialsModal && selectedLesson && (
    <LessonMaterialsManager
        lessonId={selectedLesson.id}
        lessonTitle={selectedLesson.title}
        onClose={() => {
            setShowMaterialsModal(false);
            setSelectedLesson(null);
        }}
    />
)}
```

### 2. Добавление кнопки в StudentDashboard

**Файл:** `frontend/src/modules/Student/StudentDashboard.js`

Аналогично, но импортировать `LessonMaterialsViewer`:

```jsx
import LessonMaterialsViewer from './LessonMaterialsViewer';

// ... состояние ...

{showMaterialsModal && selectedLesson && (
    <LessonMaterialsViewer
        lessonId={selectedLesson.id}
        lessonTitle={selectedLesson.title}
        onClose={() => {
            setShowMaterialsModal(false);
            setSelectedLesson(null);
        }}
    />
)}
```

---

## Возможные проблемы и решения

### Проблема 1: Миграции не применяются

**Симптом:** `No such table: schedule_lessonmaterial`

**Решение:**
```bash
cd /var/www/teaching_panel
source venv/bin/activate
python manage.py showmigrations schedule  # Проверить статус
python manage.py migrate schedule --fake-initial  # Если нужно
python manage.py migrate schedule
```

### Проблема 2: 403 Forbidden при загрузке

**Симптом:** API возвращает 403

**Причина:** Пользователь не преподаватель или не владеет уроком

**Решение:**
```python
# Проверить через shell:
from accounts.models import CustomUser
user = CustomUser.objects.get(email='teacher@example.com')
print(user.role)  # Должно быть 'teacher'

from schedule.models import Lesson
lesson = Lesson.objects.get(id=1)
print(lesson.teacher.email)  # Должен совпадать с пользователем
```

### Проблема 3: Компоненты не отображаются

**Симптом:** Кнопка "Материалы" не показывается

**Решение:**
1. Проверить импорты в файлах
2. Очистить кэш браузера (Ctrl+F5)
3. Проверить консоль браузера на ошибки (F12)
4. Пересобрать frontend: `npm run build`

### Проблема 4: CORS ошибки

**Симптом:** `CORS policy: No 'Access-Control-Allow-Origin'`

**Решение:**
```python
# В settings.py проверить:
CORS_ALLOWED_ORIGINS = [
    'http://72.56.81.163',
    'http://localhost:3000'
]

# Или включить для всех (НЕ для продакшена):
CORS_ALLOW_ALL_ORIGINS = True
```

---

## Мониторинг после деплоя

### Проверка логов

```bash
# Gunicorn
sudo journalctl -u gunicorn -f

# Celery
sudo journalctl -u celery -f

# Nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Проверка базы данных

```bash
cd /var/www/teaching_panel
source venv/bin/activate
python manage.py dbshell

-- В PostgreSQL:
\dt schedule_*  -- Список таблиц
SELECT COUNT(*) FROM schedule_lessonmaterial;
SELECT COUNT(*) FROM schedule_materialview;
```

### Метрики

- **Количество материалов:** Должно расти со временем
- **Количество просмотров:** Показатель вовлеченности учеников
- **% просмотренных:** Эффективность системы (цель: >70%)

---

## Быстрая откатка (если что-то пошло не так)

```bash
# На сервере
cd /var/www/teaching_panel

# Откат коммита
git log --oneline -5  # Найти предыдущий коммит
git reset --hard <commit_hash>

# Откат миграций
python manage.py migrate schedule <previous_migration_name>

# Перезапуск
sudo systemctl restart gunicorn
sudo systemctl restart celery
```

---

## Следующие шаги

1. **Добавить индикаторы "непрочитанных"** в карточках уроков
2. **Email уведомления** о новых материалах
3. **Встроенный PDF viewer** вместо открытия в новой вкладке
4. **Статистика в админ-панели** по всем материалам системы
5. **Автоматическая загрузка файлов** в Google Drive через API

---

## Контакты и поддержка

- **Документация:** `LESSON_MATERIALS_SYSTEM.md` (полная версия)
- **API схема:** См. раздел "API Endpoints" в документации
- **Тестовый аккаунт:** teacher@example.com / student@example.com

**Успешного деплоя! 🚀**
