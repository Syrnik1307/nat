# Data-Tour Атрибуты для Lectio Space

Этот документ содержит полный список `data-tour` атрибутов, используемых в системе онбординга.

## Статус: Реализовано

### Teacher Dashboard (TeacherHomePage.js)

| Атрибут | Элемент | Описание |
|---------|---------|----------|
| `teacher-quick-start` | Quick Start секция | Блок быстрого запуска урока |
| `teacher-schedule` | Расписание на сегодня | Список уроков на текущий день |
| `teacher-students` | Карточка "Ученики" | Быстрый доступ к управлению учениками |
| `teacher-stats` | Статистика | Метрики: уроков, учеников, ДЗ на проверку |

### Student Dashboard (StudentHomePage.js)

| Атрибут | Элемент | Описание |
|---------|---------|----------|
| `student-next-lesson` | Ближайший урок | Карточка следующего занятия |
| `student-groups` | Секция "Список курсов" | Блок с группами ученика |
| `student-join-group` | Кнопка "Есть промокод?" | Ссылка для ввода кода группы |

### Navigation Bar (NavBarNew.js)

| Атрибут | Элемент | Описание |
|---------|---------|----------|
| `teacher-navbar` | `<nav>` элемент | Весь навбар (для учителя) |
| `nav-homework` | Ссылка "ДЗ" (учитель) | Переход в конструктор ДЗ |
| `nav-recordings` | Ссылка "Записи" (учитель) | Переход к записям уроков |
| `nav-analytics` | Ссылка "Аналитика" (учитель) | Переход в аналитику |
| `student-navbar` | Ссылка "Мои курсы" | Первый пункт меню ученика |
| `nav-homework-student` | Ссылка "Домашние задания" (ученик) | Переход к ДЗ |
| `nav-calendar-student` | Ссылка "Календарь" (ученик) | Переход в календарь |

### Analytics (AnalyticsPage.js)

| Атрибут | Элемент | Описание |
|---------|---------|----------|
| `analytics-tabs` | Табы аналитики | Переключение между разделами |
| `analytics-stats-row` | Блок статистики | Основные метрики |
| `analytics-alerts` | Оповещения | Уведомления о рисках |

## Конфигурация туров

Туры настраиваются в файле `src/tourConfig.js`:

```javascript
import { 
  teacherSteps, 
  studentSteps, 
  homeworkConstructorSteps,
  // ...другие туры
} from './tourConfig';
```

## Автозапуск тура

Тур автоматически запускается при первом входе пользователя. Логика в хуке `useAppTour`:

```javascript
import { useAppTour } from '../hooks/useAppTour';

function TeacherHomePage() {
  const { user } = useAuth();
  useAppTour('teacher', user?.id);
  // ...
}
```

## Сброс тура

Для повторного просмотра тура очистите localStorage:

```javascript
// В консоли браузера
localStorage.removeItem('lectio_tour_completed_teacher_123_v2');
```

Или добавьте кнопку в профиль:

```javascript
import { useManualTour } from '../hooks/useAppTour';

function ProfilePage() {
  const { startTour, resetTour } = useManualTour('teacher', user?.id);
  
  return (
    <button onClick={resetTour}>Повторить обучение</button>
  );
}
```

## Добавление нового атрибута

1. Добавьте `data-tour="your-attribute"` к элементу в React-компоненте
2. Добавьте шаг в соответствующий массив в `tourConfig.js`
3. Обновите этот документ

---

*Версия: 2.0 | Последнее обновление: Январь 2026*
