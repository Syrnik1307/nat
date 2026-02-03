# Чек-лист Data-Tour Атрибутов для Lectio Space

## Как использовать

1. Найдите компонент в таблице ниже
2. Добавьте `data-tour="имя-атрибута"` к соответствующему элементу
3. После добавления отметьте галочкой ✅

---

## Статус: ✅ = Готово, ⬜ = Нужно добавить

---

## 1. TEACHER DASHBOARD (TeacherHomePage.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `teacher-quick-start` | Секция быстрого старта урока | ✅ |
| `teacher-schedule` | Секция расписания на сегодня | ✅ |
| `teacher-students` | Карточка "Ученики" | ✅ |
| `teacher-stats` | Блок статистики | ✅ |

---

## 2. STUDENT DASHBOARD (StudentHomePage.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `student-next-lesson` | Карточка ближайшего урока | ✅ |
| `student-groups` | Секция "Список курсов" | ✅ |
| `student-join-group` | Кнопка "Есть промокод?" | ✅ |

---

## 3. NAVIGATION (NavBarNew.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `teacher-navbar` | `<nav>` элемент | ✅ |
| `nav-homework` | Ссылка "ДЗ" (учитель) | ✅ |
| `nav-recordings` | Ссылка "Записи" (учитель) | ✅ |
| `nav-analytics` | Ссылка "Аналитика" (учитель) | ✅ |
| `student-navbar` | Ссылка "Мои курсы" (ученик) | ✅ |
| `nav-homework-student` | Ссылка "ДЗ" (ученик) | ✅ |
| `nav-calendar-student` | Ссылка "Календарь" (ученик) | ✅ |

---

## 4. HOMEWORK CONSTRUCTOR (HomeworkConstructor.js)

| Атрибут | Элемент | Файл | Статус |
|---------|---------|------|--------|
| `hw-title` | Input названия | HomeworkConstructor.js | ✅ |
| `hw-description` | Textarea описания | HomeworkConstructor.js | ✅ |
| `hw-group-selector` | Компонент выбора группы | HomeworkConstructor.js | ✅ |
| `hw-deadline` | DateTimePicker | HomeworkConstructor.js | ✅ |
| `hw-max-score` | Input макс. балла | HomeworkConstructor.js | ✅ |
| `hw-questions-panel` | Левая панель вопросов | HomeworkConstructor.js | ✅ |
| `hw-add-question` | Кнопка "Добавить вопрос" | HomeworkConstructor.js | ✅ |
| `hw-question-editor` | Область редактора | HomeworkConstructor.js | ⬜ |
| `hw-preview` | Секция превью | HomeworkConstructor.js | ⬜ |
| `hw-actions` | Кнопки сохранения | HomeworkConstructor.js | ✅ |

---

## 5. TEXT QUESTION (TextQuestion.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `q-text-format` | Переключатель "Короткий/Развёрнутый" | ✅ |
| `q-text-answer` | Textarea эталонного ответа | ✅ |

**Пример:**
```jsx
<div className="gm-tab-switch" data-tour="q-text-format">
```

---

## 6. SINGLE CHOICE (SingleChoiceQuestion.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `q-single-options` | Контейнер `.hc-question-options` | ✅ |
| `q-single-add` | Кнопка "Добавить вариант" | ✅ |

**Пример:**
```jsx
<div className="hc-question-options" data-tour="q-single-options">
```

---

## 7. MULTIPLE CHOICE (MultipleChoiceQuestion.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `q-multi-options` | Контейнер `.hc-question-options` | ✅ |
| `q-multi-add` | Кнопка "Добавить вариант" | ✅ |

---

## 8. FILL BLANKS (FillBlanksQuestion.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `q-fillblanks-template` | Textarea шаблона | ✅ |
| `q-fillblanks-answers` | Секция `.hc-subsection` с ответами | ✅ |
| `q-fillblanks-settings` | Блок `.hc-inline-fields` с настройками | ✅ |

**Пример:**
```jsx
<textarea
  className="form-textarea"
  data-tour="q-fillblanks-template"
  ...
/>
```

---

## 9. MATCHING (MatchingQuestion.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `q-matching-pairs` | Контейнер `.hc-sublist` | ✅ |
| `q-matching-add` | Кнопка "Добавить пару" | ✅ |
| `q-matching-shuffle` | Label с чекбоксом перемешивания | ✅ |

---

## 10. DRAG & DROP (DragDropQuestion.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `q-dragdrop-items` | Контейнер `.hc-sublist` | ✅ |
| `q-dragdrop-add` | Кнопка "Добавить элемент" | ✅ |
| `q-dragdrop-reorder` | Первый `.hc-inline-actions` со стрелками | ✅ |

---

## 11. CODE (CodeQuestion.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `q-code-language` | Select языка | ✅ |
| `q-code-starter` | Textarea стартового кода | ✅ |
| `q-code-solution` | Textarea эталонного решения | ✅ |
| `q-code-tests` | Секция с тест-кейсами | ✅ |
| `q-code-add-test` | Кнопка "Добавить тест" | ✅ |
| `q-code-run` | Кнопка "Запустить" | ✅ |
| `q-code-terminal` | Терминал вывода | ✅ |

**Пример:**
```jsx
<select className="form-select" data-tour="q-code-language" ...>
```

---

## 12. FILE UPLOAD (FileUploadQuestion.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `q-file-types` | Контейнер `.gm-checkbox-group` | ✅ |
| `q-file-max-count` | Select количества | ✅ |
| `q-file-max-size` | Select размера | ✅ |
| `q-file-instructions` | Textarea инструкций | ✅ |

---

## 13. HOTSPOT (HotspotQuestion.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `q-hotspot-image` | FileUploader изображения | ✅ |
| `q-hotspot-areas` | Секция `.hc-subsection` | ✅ |
| `q-hotspot-add` | Кнопка "Добавить область" | ✅ |
| `q-hotspot-coords` | Первый блок с инпутами X/Y | ⬜ |
| `q-hotspot-attempts` | Input попыток | ✅ |

---

## 14. LISTENING (ListeningQuestion.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `q-listening-audio` | FileUploader аудио | ✅ |
| `q-listening-player` | Элемент `<audio>` | ✅ |
| `q-listening-prompt` | Textarea инструкции | ✅ |
| `q-listening-subquestions` | Секция `.hc-subsection` | ✅ |
| `q-listening-add` | Кнопка "Добавить подвопрос" | ✅ |

---

## 15. RECORDINGS (TeacherRecordingsPage.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `rec-stats` | Блок статистики (total/ready/processing) | ✅ |
| `rec-filters` | Секция с фильтрами и поиском | ✅ |
| `rec-upload` | Кнопка "Загрузить видео" | ✅ |
| `rec-card` | Первая карточка записи | ✅ |
| `rec-play` | Кнопка воспроизведения | ⬜ |
| `rec-delete` | Кнопка удаления | ⬜ |
| `rec-privacy` | Селектор приватности в модалке | ✅ |

---

## 16. MATERIALS (TeacherMaterialsPage.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `mat-tabs` | Табы Miro/Конспекты | ⬜ |
| `mat-miro-connect` | Кнопка "Подключить Miro" | ⬜ |
| `mat-add-miro` | Кнопка "Добавить доску" | ⬜ |
| `mat-add-notes` | Кнопка "Создать конспект" | ⬜ |
| `mat-card` | Первая карточка материала | ⬜ |
| `mat-visibility` | Селектор видимости | ⬜ |

---

## 17. STUDENTS MANAGE (StudentsManage.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `students-search` | Input поиска | ✅ |
| `students-filters` | Блок с фильтрами | ✅ |
| `students-table` | Таблица учеников | ✅ |
| `students-card` | Карточка выбранного ученика | ✅ |
| `students-edit` | Форма редактирования | ✅ |
| `students-archive` | Кнопка архивации | ✅ |

---

## 18. GROUP MANAGE (GroupManage.js / GroupsManage.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `group-create` | Кнопка "Создать группу" | ⬜ |
| `group-card` | Первая карточка группы | ⬜ |
| `group-invite` | Кнопка "Пригласить" | ⬜ |
| `group-individual-invites` | Кнопка персональных инвайтов | ⬜ |
| `group-students-list` | Список учеников группы | ⬜ |
| `group-delete` | Кнопка удаления группы | ⬜ |

---

## 19. CALENDAR (CalendarPage.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `cal-views` | Переключатель видов | ⬜ |
| `cal-nav` | Стрелки навигации | ⬜ |
| `cal-create` | Кнопка создания занятия | ⬜ |
| `cal-recurring` | Кнопка повторяющихся занятий | ⬜ |
| `cal-lesson` | Первое занятие в календаре | ⬜ |
| `cal-quick` | QuickLessonButton | ⬜ |

---

## 20. PROFILE (ProfilePage.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `profile-tabs` | Табы настроек | ✅ |
| `profile-avatar` | Область аватара | ✅ |
| `profile-name` | Поля имени/фамилии | ✅ |
| `profile-telegram` | Секция Telegram | ✅ |
| `profile-tg-code` | Блок с кодом привязки | ✅ |
| `profile-notifications` | Настройки уведомлений | ✅ |
| `profile-security` | Секция безопасности | ✅ |
| `profile-subscription` | Секция подписки | ⬜ |

---

## 21. ANALYTICS (AnalyticsPage.js)

| Атрибут | Элемент | Статус |
|---------|---------|--------|
| `analytics-tabs` | Табы аналитики | ✅ |
| `analytics-stats-row` | Блок ключевых метрик | ✅ |
| `analytics-alerts` | Блок оповещений | ✅ |
| `analytics-gradebook` | Журнал оценок | ⬜ |
| `analytics-export` | Кнопка экспорта | ⬜ |

---

## Быстрый поиск файлов

```powershell
# Найти все data-tour в проекте
Get-ChildItem -Recurse -Filter "*.js" | Select-String "data-tour"

# Подсчёт атрибутов
Get-ChildItem -Recurse -Filter "*.js" | Select-String "data-tour" | Measure-Object
```

---

## Пример добавления атрибута

```jsx
// До
<button className="gm-btn-surface" onClick={addOption}>
  + Добавить вариант
</button>

// После
<button 
  className="gm-btn-surface" 
  onClick={addOption}
  data-tour="q-single-add"
>
  + Добавить вариант
</button>
```

---

*Последнее обновление: Февраль 2026*
