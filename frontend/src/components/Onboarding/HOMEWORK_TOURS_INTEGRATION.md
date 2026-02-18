# Driver.js Homework Tours - Инструкция по интеграции

Этот документ описывает как добавить `data-tour` атрибуты к компонентам для работы детальных туров по домашним заданиям.

## Обзор новых туров

| Тур | Ключ | Описание |
|-----|------|----------|
| HomeworkConstructorDetailedOnboarding | `homework-constructor-detailed` | Детальный тур по созданию ДЗ с объяснением всех типов вопросов |
| SubmissionReviewOnboarding | `submission-review` | Тур по проверке работы ученика |
| GradedSubmissionsListOnboarding | `graded-submissions` | Тур по списку сданных работ |
| HomeworkTakeOnboarding | `homework-take` | Тур для ученика по прохождению ДЗ |
| StudentAIReportsOnboarding | `student-ai-reports` | Тур по AI-анализу результатов |

## Использование

```jsx
import { 
  HomeworkConstructorDetailedOnboarding,
  HomeworkTakeOnboarding 
} from '../components/Onboarding';

// В компоненте конструктора ДЗ (для учителя)
function HomeworkConstructor() {
  return (
    <>
      <HomeworkConstructorDetailedOnboarding userId={user.id} />
      {/* остальной контент */}
    </>
  );
}

// Для ручного запуска тура
import { OnboardingTrigger } from '../components/Onboarding';

<OnboardingTrigger tourKey="homework-constructor-detailed">
  {({ startTour }) => (
    <button onClick={startTour}>Показать тур</button>
  )}
</OnboardingTrigger>
```

---

## Список data-tour атрибутов для добавления

### 1. HomeworkConstructor.js (Конструктор ДЗ)

```jsx
// Панель метаданных
<div data-tour="hw-meta-panel" className="hc-meta-section">

// Поле названия
<input data-tour="hw-meta-title" className="form-input" />

// Панель типов вопросов
<div data-tour="hw-question-types-panel" className="hc-question-types">
```

### 2. CodeQuestion.js

```jsx
// Обёртка компонента
<div data-tour="hw-question-type-code" className="hc-question-editor">

// Стартовый код
<textarea data-tour="hw-code-starter" className="code-editor" />

// Эталонное решение  
<textarea data-tour="hw-code-solution" className="code-editor" />

// Выбор языка
<select data-tour="hw-code-language" className="form-select">

// Секция тестов
<div data-tour="hw-code-tests" className="hc-subsection">

// Кнопка запуска
<button data-tour="hw-code-run-btn" className="gm-btn-primary">
```

### 3. DragDropQuestion.js

```jsx
// Обёртка
<div data-tour="hw-question-type-dragdrop" className="hc-question-editor">

// Список элементов
<div data-tour="hw-dragdrop-items" className="hc-sublist">
```

### 4. HotspotQuestion.js

```jsx
// Обёртка
<div data-tour="hw-question-type-hotspot" className="hc-question-editor">

// Загрузчик изображения
<div data-tour="hw-hotspot-image">
  <FileUploader ... />
</div>

// Редактор зон
<div data-tour="hw-hotspot-zones" className="hc-subsection">
```

### 5. FillBlanksQuestion.js

```jsx
// Обёртка
<div data-tour="hw-question-type-fillblanks" className="hc-question-editor">

// Шаблон с пропусками
<textarea data-tour="hw-fillblanks-template" className="form-textarea" />

// Ответы
<div data-tour="hw-fillblanks-answers" className="hc-subsection">
```

### 6. ListeningQuestion.js

```jsx
// Обёртка
<div data-tour="hw-question-type-listening" className="hc-question-editor">

// Загрузчик аудио
<div data-tour="hw-listening-audio">
  <FileUploader ... />
</div>

// Подвопросы
<div data-tour="hw-listening-subquestions" className="hc-subsection">
```

### 7. FileUploadQuestion.js

```jsx
// Обёртка
<div data-tour="hw-question-type-fileupload" className="hc-question-editor">

// Выбор типов файлов
<div data-tour="hw-fileupload-types" className="gm-checkbox-group">

// Лимиты
<div data-tour="hw-fileupload-limits" className="form-group">
```

### 8. MatchingQuestion.js

```jsx
// Обёртка
<div data-tour="hw-question-type-matching" className="hc-question-editor">

// Пары
<div data-tour="hw-matching-pairs" className="hc-subsection">
```

### 9. SingleChoiceQuestion.js / MultipleChoiceQuestion.js

```jsx
// Обёртка (single)
<div data-tour="hw-question-type-single" className="hc-question-editor">

// Обёртка (multiple)
<div data-tour="hw-question-type-multiple" className="hc-question-editor">
```

### 10. TextQuestion.js

```jsx
// Обёртка
<div data-tour="hw-question-type-text" className="hc-question-editor">
```

---

## SubmissionReview.js (Проверка работ)

```jsx
// Информация об ученике
<div data-tour="review-student-info" className="submission-header">

// Список ответов
<div data-tour="review-answers-list" className="answers-container">

// Блок ответа
<div data-tour="review-answer-block" className="answer-item">

// AI-анализ
<div data-tour="review-ai-analysis" className="ai-analysis-section">

// Автооценка
<span data-tour="review-auto-score" className="auto-score">

// Поле оценки учителя
<input data-tour="review-teacher-score" className="form-input" type="number" />

// Поле комментария
<textarea data-tour="review-teacher-feedback" className="form-textarea" />

// Кнопка сохранения
<button data-tour="review-save-btn" className="gm-btn-primary">
```

---

## HomeworkTake.js (Прохождение ДЗ учеником)

```jsx
// Заголовок
<div data-tour="take-header" className="homework-header">

// Прогресс
<ProgressBar data-tour="take-progress" />

// Навигация по вопросам
<QuestionNav data-tour="take-question-nav" />

// Область вопроса
<div data-tour="take-question-area" className="question-content">

// Кнопки навигации
<div data-tour="take-nav-buttons" className="nav-buttons">

// Индикатор автосохранения
<span data-tour="take-autosave" className="autosave-indicator">

// Кнопка отправки
<button data-tour="take-submit-btn" className="gm-btn-primary">
```

---

## QuestionRenderer.js / CodeQuestionRenderer.js / FileUploadRenderer.js

```jsx
// Текстовый ответ
<textarea data-tour="take-answer-text" className="form-textarea" />

// Варианты ответа
<div data-tour="take-answer-choice" className="ht-options">

// Редактор кода
<textarea data-tour="take-code-editor" className="code-editor" />

// Кнопка запуска
<button data-tour="take-code-run" className="run-btn">

// Вкладка тестов
<div data-tour="take-code-tests" className="tests-tab">

// Вывод консоли
<div data-tour="take-code-output" className="terminal-output">

// Зона загрузки файлов
<div data-tour="take-file-dropzone" className="dropzone">

// Превью файла
<div data-tour="take-file-preview" className="file-preview">

// Интерактивная область
<div data-tour="take-interactive-area" className="interactive-question">

// Drag & Drop элементы
<div data-tour="take-dragdrop-items" className="draggable-items">

// Hotspot изображение
<div data-tour="take-hotspot-image" className="hotspot-container">

// Matching колонки
<div data-tour="take-matching-columns" className="matching-columns">

// Fill blanks поля
<div data-tour="take-fillblanks" className="fillblanks-container">

// Аудиоплеер
<audio data-tour="take-listening-player" controls />

// Вопросы к аудио
<div data-tour="take-listening-questions" className="listening-questions">
```

---

## StudentAIReports.js

```jsx
// Сводка
<div data-tour="ai-summary" className="summary-section">

// График прогресса
<div data-tour="ai-progress-chart" className="progress-chart">

// Анализ по навыкам
<div data-tour="ai-skills" className="skills-breakdown">

// Разбор ошибок
<div data-tour="ai-error-breakdown" className="error-analysis">

// Рекомендации
<div data-tour="ai-recommendations" className="recommendations-section">
```

---

## Важные заметки

1. **Фильтрация отсутствующих элементов**: Система автоматически пропускает шаги, если элемент не найден на странице. Используется функция `filterExistingSteps()`.

2. **Условные типы вопросов**: Не все типы вопросов присутствуют в каждом ДЗ. Атрибуты для типов вопросов (например `hw-question-type-code`) будут работать только когда этот тип добавлен в задание.

3. **Порядок шагов**: Шаги показываются в порядке определения в массиве. Если какие-то элементы отсутствуют — они пропускаются.

4. **Версионирование**: При изменении шагов не забудьте обновить `TOUR_VERSION` в `useOnboarding.js`.

---

## Тестирование

```javascript
// В консоли браузера
import { OnboardingTrigger } from './components/Onboarding';

// Или напрямую
import { homeworkConstructorDetailedSteps, filterExistingSteps } from './components/Onboarding/driverConfig';

const filteredSteps = filterExistingSteps(homeworkConstructorDetailedSteps);
console.log('Доступные шаги:', filteredSteps.length);
console.log('Шаги:', filteredSteps.map(s => s.element || 'intro/outro'));
```
