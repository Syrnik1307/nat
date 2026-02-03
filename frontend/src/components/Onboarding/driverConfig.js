/**
 * driverConfig.js - Расширенная конфигурация Driver.js для Lectio Space
 * 
 * Включает детальные шаги для каждого типа вопроса в домашних заданиях:
 * - Code, DragDrop, FileUpload, FillBlanks, Hotspot
 * - Listening, Matching, MultipleChoice, SingleChoice, Text
 * 
 * Версионирование: При изменении шагов обновите TOUR_VERSION в useOnboarding.js
 */

// =====================================================
// УТИЛИТЫ ДЛЯ УСЛОВНОГО ДОБАВЛЕНИЯ ШАГОВ
// =====================================================

/**
 * Проверяет существование элемента на странице
 * @param {string} selector - CSS-селектор
 * @returns {boolean}
 */
export const elementExists = (selector) => {
  return document.querySelector(selector) !== null;
};

/**
 * Фильтрует шаги, оставляя только те, у которых элемент существует
 * @param {Array} steps - Массив шагов Driver.js
 * @returns {Array} - Отфильтрованные шаги
 */
export const filterExistingSteps = (steps) => {
  return steps.filter(step => {
    // Шаги без element (intro/outro) всегда показываем
    if (!step.element) return true;
    return elementExists(step.element);
  });
};

// =====================================================
// СЦЕНАРИЙ 1: УЧИТЕЛЬ - КОНСТРУКТОР ДЗ (ДЕТАЛЬНЫЙ)
// =====================================================
export const homeworkConstructorDetailedSteps = [
  // --- ВВОДНЫЙ ШАГ ---
  {
    popover: {
      title: 'Добро пожаловать в Конструктор ДЗ!',
      description: 'Здесь вы создаёте интерактивные задания для учеников. Давайте изучим все возможности — от простых тестов до заданий на код!',
    },
  },

  // --- ПАНЕЛЬ МЕТАДАННЫХ ---
  {
    element: '[data-tour="hw-meta-panel"]',
    // TODO: Developer needs to add className="driver-hw-meta-panel" or data-tour="hw-meta-panel" to the metadata section wrapper
    popover: {
      title: 'Настройки задания',
      description: 'Начните с заполнения основной информации: название, описание, группы и дедлайн.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-meta-title"]',
    popover: {
      title: 'Название задания',
      description: 'Придумайте понятное название. Например: "Контрольная по Present Perfect" или "ДЗ №5 — Алгоритмы".',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-meta-description"]',
    popover: {
      title: 'Описание и инструкции',
      description: 'Объясните ученикам что от них требуется. Можно добавить советы, ограничения или критерии оценки.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-meta-groups"]',
    popover: {
      title: 'Назначение группам',
      description: 'Выберите группы и конкретных учеников. Можно назначить всей группе сразу или выборочно отдельным студентам.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-meta-deadline"]',
    popover: {
      title: 'Дедлайн',
      description: 'Установите срок сдачи. После этого времени ученики не смогут отправить работу. Планируйте с запасом!',
      side: 'left',
    },
  },
  {
    element: '[data-tour="hw-meta-score"]',
    popover: {
      title: 'Максимальный балл',
      description: 'Общий балл за задание. Система распределит его между вопросами автоматически, но вы можете настроить веса вручную.',
      side: 'left',
    },
  },

  // --- ПАНЕЛЬ ИНСТРУМЕНТОВ (ТИПЫ ВОПРОСОВ) ---
  {
    element: '[data-tour="hw-question-types-panel"]',
    // TODO: Developer needs to add data-tour="hw-question-types-panel" to the question type toolbar/panel
    popover: {
      title: 'Панель инструментов',
      description: 'Здесь живут ваши инструменты! 10 типов вопросов на все случаи жизни. Выберите нужный, чтобы добавить в задание.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="hw-add-question"]',
    popover: {
      title: 'Добавить вопрос',
      description: 'Нажмите, чтобы выбрать тип: текст, тест, код, аудирование, сопоставление и другие. Каждый тип имеет свои настройки.',
      side: 'top',
    },
  },

  // --- ТИП: ТЕКСТОВЫЙ ВОПРОС ---
  {
    element: '[data-tour="hw-question-type-text"]',
    // TODO: Developer needs to add data-tour="hw-question-type-text" to TextQuestion wrapper or add button
    popover: {
      title: 'Тип: Текстовый ответ',
      description: 'Классический открытый вопрос. Ученик пишет развёрнутый ответ. Идеально для эссе, объяснений и творческих заданий.',
      side: 'right',
    },
  },

  // --- ТИП: ОДИНОЧНЫЙ ВЫБОР ---
  {
    element: '[data-tour="hw-question-type-single"]',
    // TODO: Developer needs to add data-tour="hw-question-type-single" to SingleChoiceQuestion wrapper
    popover: {
      title: 'Тип: Один правильный ответ',
      description: 'Классический тест. Ученик выбирает ОДИН вариант из нескольких. Автопроверка работает мгновенно!',
      side: 'right',
    },
  },

  // --- ТИП: МНОЖЕСТВЕННЫЙ ВЫБОР ---
  {
    element: '[data-tour="hw-question-type-multiple"]',
    // TODO: Developer needs to add data-tour="hw-question-type-multiple" to MultipleChoiceQuestion wrapper
    popover: {
      title: 'Тип: Несколько правильных ответов',
      description: 'Ученик выбирает НЕСКОЛЬКО верных вариантов. Укажите все правильные ответы — система проверит автоматически.',
      side: 'right',
    },
  },

  // --- ТИП: КОД ---
  {
    element: '[data-tour="hw-question-type-code"]',
    // TODO: Developer needs to add data-tour="hw-question-type-code" to CodeQuestion wrapper in HomeworkConstructor
    popover: {
      title: 'Тип: Задание на код',
      description: 'Мощный инструмент для программирования! Ученики пишут код прямо в браузере с подсветкой синтаксиса.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="hw-code-starter"]',
    // TODO: Developer needs to add data-tour="hw-code-starter" to starter code textarea in CodeQuestion
    popover: {
      title: 'Стартовый код (шаблон)',
      description: 'Напишите начальный код, который увидит ученик. Можно оставить комментарии-подсказки или заготовку функции.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-code-solution"]',
    // TODO: Developer needs to add data-tour="hw-code-solution" to solution code textarea in CodeQuestion
    popover: {
      title: 'Эталонное решение',
      description: 'Ваше правильное решение. Используется для автотестов и как образец при ручной проверке.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-code-language"]',
    // TODO: Developer needs to add data-tour="hw-code-language" to language selector in CodeQuestion
    popover: {
      title: 'Язык программирования',
      description: 'Выберите язык: Python или JavaScript. Код выполняется безопасно в браузере ученика.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="hw-code-tests"]',
    // TODO: Developer needs to add data-tour="hw-code-tests" to test cases section in CodeQuestion
    popover: {
      title: 'Автотесты',
      description: 'Добавьте тест-кейсы: входные данные и ожидаемый вывод. Система автоматически проверит код ученика!',
      side: 'top',
    },
  },
  {
    element: '[data-tour="hw-code-run-btn"]',
    // TODO: Developer needs to add data-tour="hw-code-run-btn" to Run button in CodeQuestion
    popover: {
      title: 'Проверить решение',
      description: 'Запустите эталонный код, чтобы убедиться в его корректности. Результат появится в терминале ниже.',
      side: 'left',
    },
  },

  // --- ТИП: DRAG & DROP ---
  {
    element: '[data-tour="hw-question-type-dragdrop"]',
    // TODO: Developer needs to add data-tour="hw-question-type-dragdrop" to DragDropQuestion wrapper
    popover: {
      title: 'Тип: Drag & Drop (Перетаскивание)',
      description: 'Ученик расставляет элементы в правильном порядке. Отлично для хронологий, алгоритмов и последовательностей!',
      side: 'right',
    },
  },
  {
    element: '[data-tour="hw-dragdrop-items"]',
    // TODO: Developer needs to add data-tour="hw-dragdrop-items" to items list in DragDropQuestion
    popover: {
      title: 'Элементы для сортировки',
      description: 'Добавьте элементы и расположите их в ПРАВИЛЬНОМ порядке. Ученик получит их перемешанными и должен восстановить порядок.',
      side: 'bottom',
    },
  },

  // --- ТИП: HOTSPOT (ИНТЕРАКТИВНАЯ КАРТА) ---
  {
    element: '[data-tour="hw-question-type-hotspot"]',
    // TODO: Developer needs to add data-tour="hw-question-type-hotspot" to HotspotQuestion wrapper
    popover: {
      title: 'Тип: Hotspot (Интерактивная карта)',
      description: 'Ученик кликает на правильные области изображения. Идеально для географии, анатомии, схем!',
      side: 'right',
    },
  },
  {
    element: '[data-tour="hw-hotspot-image"]',
    // TODO: Developer needs to add data-tour="hw-hotspot-image" to image uploader in HotspotQuestion
    popover: {
      title: 'Загрузите изображение',
      description: 'Загрузите карту, схему или диаграмму. Поддерживаются JPG, PNG, GIF, WebP до 50 МБ.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-hotspot-zones"]',
    // TODO: Developer needs to add data-tour="hw-hotspot-zones" to hotspot zones editor in HotspotQuestion
    popover: {
      title: 'Определите зоны',
      description: 'Выделите правильные области, на которые ученик должен кликнуть. Задайте координаты и размеры каждой зоны.',
      side: 'top',
    },
  },

  // --- ТИП: FILL BLANKS (ПРОПУСКИ) ---
  {
    element: '[data-tour="hw-question-type-fillblanks"]',
    // TODO: Developer needs to add data-tour="hw-question-type-fillblanks" to FillBlanksQuestion wrapper
    popover: {
      title: 'Тип: Заполнение пропусков',
      description: 'Ученик вписывает слова в пропуски в тексте. Классика для грамматики и лексики!',
      side: 'right',
    },
  },
  {
    element: '[data-tour="hw-fillblanks-template"]',
    // TODO: Developer needs to add data-tour="hw-fillblanks-template" to template textarea in FillBlanksQuestion
    popover: {
      title: 'Текст с пропусками',
      description: 'Используйте [___] для обозначения пропусков. Например: "The capital of France is [___]." — Система автоматически создаст поля ввода.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-fillblanks-answers"]',
    // TODO: Developer needs to add data-tour="hw-fillblanks-answers" to answers section in FillBlanksQuestion
    popover: {
      title: 'Правильные ответы',
      description: 'Укажите правильные ответы для каждого пропуска. Можно настроить чувствительность к регистру.',
      side: 'top',
    },
  },

  // --- ТИП: LISTENING (АУДИРОВАНИЕ) ---
  {
    element: '[data-tour="hw-question-type-listening"]',
    // TODO: Developer needs to add data-tour="hw-question-type-listening" to ListeningQuestion wrapper
    popover: {
      title: 'Тип: Аудирование',
      description: 'Ученик прослушивает аудио и отвечает на вопросы. Незаменимо для языковых курсов!',
      side: 'right',
    },
  },
  {
    element: '[data-tour="hw-listening-audio"]',
    // TODO: Developer needs to add data-tour="hw-listening-audio" to audio uploader in ListeningQuestion
    popover: {
      title: 'Загрузите аудиофайл',
      description: 'Загрузите MP3, WAV или OGG до 50 МБ. Ученик сможет прослушать запись перед ответом.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-listening-subquestions"]',
    // TODO: Developer needs to add data-tour="hw-listening-subquestions" to subquestions list in ListeningQuestion
    popover: {
      title: 'Подвопросы к аудио',
      description: 'Добавьте вопросы по содержанию аудио. Каждый подвопрос — отдельное поле для ответа ученика.',
      side: 'top',
    },
  },

  // --- ТИП: FILE UPLOAD (ЗАГРУЗКА ФАЙЛОВ) ---
  {
    element: '[data-tour="hw-question-type-fileupload"]',
    // TODO: Developer needs to add data-tour="hw-question-type-fileupload" to FileUploadQuestion wrapper
    popover: {
      title: 'Тип: Загрузка файла',
      description: 'Ученик загружает файл как ответ. Идеально для творческих заданий, эссе, проектов!',
      side: 'right',
    },
  },
  {
    element: '[data-tour="hw-fileupload-types"]',
    // TODO: Developer needs to add data-tour="hw-fileupload-types" to file types selector in FileUploadQuestion
    popover: {
      title: 'Разрешённые типы',
      description: 'Выберите какие файлы принимать: изображения (скриншоты, фото), документы (PDF, Word) или и то, и другое.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-fileupload-limits"]',
    // TODO: Developer needs to add data-tour="hw-fileupload-limits" to limits section in FileUploadQuestion
    popover: {
      title: 'Лимиты',
      description: 'Настройте максимальный размер файла и количество загрузок. Защитите себя от гигантских файлов!',
      side: 'top',
    },
  },

  // --- ТИП: MATCHING (СОПОСТАВЛЕНИЕ) ---
  {
    element: '[data-tour="hw-question-type-matching"]',
    // TODO: Developer needs to add data-tour="hw-question-type-matching" to MatchingQuestion wrapper
    popover: {
      title: 'Тип: Сопоставление',
      description: 'Ученик соединяет пары понятий. Отлично для "слово-перевод", "термин-определение", "дата-событие"!',
      side: 'right',
    },
  },
  {
    element: '[data-tour="hw-matching-pairs"]',
    // TODO: Developer needs to add data-tour="hw-matching-pairs" to pairs editor in MatchingQuestion
    popover: {
      title: 'Создайте пары',
      description: 'Добавьте пары элементов: левая колонка — правая колонка. Ученик увидит их перемешанными.',
      side: 'bottom',
    },
  },

  // --- ПРЕВЬЮ ---
  {
    element: '[data-tour="hw-preview"]',
    popover: {
      title: 'Превью для ученика',
      description: 'Посмотрите как задание выглядит глазами ученика. Переключайтесь между вопросами и проверяйте интерактивность.',
      side: 'left',
    },
  },

  // --- ПУБЛИКАЦИЯ ---
  {
    element: '[data-tour="hw-actions"]',
    popover: {
      title: 'Сохранить и опубликовать',
      description: '"Черновик" — сохранить без публикации (только вы видите). "Опубликовать" — ученики сразу увидят задание и смогут приступить!',
      side: 'top',
    },
  },

  // --- ФИНАЛЬНЫЙ ШАГ ---
  {
    popover: {
      title: 'Вы готовы создавать!',
      description: 'Попробуйте добавить первый вопрос. Начните с простого теста, а затем экспериментируйте с кодом и интерактивом. Автопроверка сэкономит вам часы!',
    },
  },
];

// =====================================================
// СЦЕНАРИЙ 1: УЧИТЕЛЬ - ПРОВЕРКА РАБОТ
// =====================================================
export const submissionReviewSteps = [
  {
    popover: {
      title: 'Проверка работ учеников',
      description: 'Здесь вы оцениваете ответы, читаете AI-анализ и оставляете комментарии. Давайте разберёмся!',
    },
  },
  {
    element: '[data-tour="review-student-info"]',
    // TODO: Developer needs to add data-tour="review-student-info" to student info section in SubmissionReview
    popover: {
      title: 'Информация об ученике',
      description: 'Имя, группа, время сдачи. Видно сразу — никаких поисков.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="review-answers-list"]',
    // TODO: Developer needs to add data-tour="review-answers-list" to answers container in SubmissionReview
    popover: {
      title: 'Список ответов',
      description: 'Все ответы ученика по порядку. Каждый вопрос — отдельный блок с ответом и оценкой.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="review-answer-block"]',
    // TODO: Developer needs to add data-tour="review-answer-block" to individual answer block in SubmissionReview
    popover: {
      title: 'Блок с ответом',
      description: 'Текст вопроса, ответ ученика и правильный ответ (если есть). Всё в одном месте для быстрой проверки.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="review-ai-analysis"]',
    // TODO: Developer needs to add data-tour="review-ai-analysis" to AI analysis section in SubmissionReview
    popover: {
      title: 'AI-анализ ответа',
      description: 'Наш ИИ уже проанализировал ответ! Показывает ошибки, сильные стороны и предлагает оценку. Экономит ваше время.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="review-auto-score"]',
    // TODO: Developer needs to add data-tour="review-auto-score" to auto score display in SubmissionReview
    popover: {
      title: 'Автоматическая оценка',
      description: 'Баллы, выставленные автопроверкой. Для тестов и кода — точный расчёт. Для текстов — рекомендация AI.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="review-teacher-score"]',
    // TODO: Developer needs to add data-tour="review-teacher-score" to teacher score input in SubmissionReview
    popover: {
      title: 'Ваша оценка',
      description: 'Переопределите оценку AI или оставьте как есть. Вы — финальный арбитр!',
      side: 'left',
    },
  },
  {
    element: '[data-tour="review-teacher-feedback"]',
    // TODO: Developer needs to add data-tour="review-teacher-feedback" to feedback textarea in SubmissionReview
    popover: {
      title: 'Комментарий для ученика',
      description: 'Напишите персональный фидбэк. Ученик увидит его вместе с оценкой. Мотивируйте и направляйте!',
      side: 'top',
    },
  },
  {
    element: '[data-tour="review-save-btn"]',
    // TODO: Developer needs to add data-tour="review-save-btn" to save button in SubmissionReview
    popover: {
      title: 'Сохранить оценку',
      description: 'Нажмите для сохранения. Оценка и комментарий станут видны ученику немедленно.',
      side: 'left',
    },
  },
  {
    popover: {
      title: 'Проверка — это легко!',
      description: 'AI делает 80% работы, вы корректируете и добавляете личный touch. Следующий ученик ждёт!',
    },
  },
];

// =====================================================
// СЦЕНАРИЙ 1: УЧИТЕЛЬ - СПИСОК СДАННЫХ РАБОТ
// =====================================================
export const gradedSubmissionsListSteps = [
  {
    popover: {
      title: 'Работы на проверку',
      description: 'Все сданные работы в одном списке. Статусы, фильтры, быстрый доступ к проверке.',
    },
  },
  {
    element: '[data-tour="graded-filters"]',
    // TODO: Developer needs to add data-tour="graded-filters" to filters section
    popover: {
      title: 'Фильтры',
      description: 'Отфильтруйте по статусу: "На проверке", "Проверено", "Все". Сфокусируйтесь на непроверенных.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="graded-status-pending"]',
    // TODO: Developer needs to add data-tour="graded-status-pending" to pending status badge
    popover: {
      title: 'Статус: На проверке',
      description: 'Эти работы ждут вашей оценки. Жёлтый бейдж = требуется внимание.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="graded-status-graded"]',
    // TODO: Developer needs to add data-tour="graded-status-graded" to graded status badge
    popover: {
      title: 'Статус: Проверено',
      description: 'Работа оценена. Зелёный бейдж = всё готово. Можно пересмотреть при необходимости.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="graded-review-btn"]',
    // TODO: Developer needs to add data-tour="graded-review-btn" to review button
    popover: {
      title: 'Открыть проверку',
      description: 'Нажмите для детального просмотра ответов и выставления оценки.',
      side: 'left',
    },
  },
  {
    popover: {
      title: 'Всё под контролем!',
      description: 'Проверяйте работы по мере поступления или пачками — как удобнее. Бейдж в меню покажет количество непроверенных.',
    },
  },
];

// =====================================================
// СЦЕНАРИЙ 2: УЧЕНИК - ПРОХОЖДЕНИЕ ДЗ
// =====================================================
export const homeworkTakeSteps = [
  {
    popover: {
      title: 'Время выполнять задание!',
      description: 'Отвечайте на вопросы, сохраняйте прогресс и отправляйте работу до дедлайна. Удачи!',
    },
  },
  {
    element: '[data-tour="take-header"]',
    // TODO: Developer needs to add data-tour="take-header" to homework header in HomeworkTake
    popover: {
      title: 'Информация о задании',
      description: 'Название, дедлайн, инструкции от преподавателя. Прочитайте внимательно!',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="take-progress"]',
    // TODO: Developer needs to add data-tour="take-progress" to ProgressBar in HomeworkTake
    popover: {
      title: 'Прогресс выполнения',
      description: 'Прогресс-бар показывает сколько вопросов вы уже ответили. Стремитесь к 100%!',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="take-question-nav"]',
    // TODO: Developer needs to add data-tour="take-question-nav" to QuestionNav in HomeworkTake
    popover: {
      title: 'Навигация по вопросам',
      description: 'Переключайтесь между вопросами. Зелёные = отвечено, серые = ещё нет. Можно прыгать в любой вопрос!',
      side: 'right',
    },
  },
  {
    element: '[data-tour="take-question-area"]',
    // TODO: Developer needs to add data-tour="take-question-area" to question content area in HomeworkTake
    popover: {
      title: 'Область вопроса',
      description: 'Здесь отображается текущий вопрос. Читайте условие и давайте ответ ниже.',
      side: 'top',
    },
  },

  // --- ТИПЫ ВОПРОСОВ ДЛЯ УЧЕНИКА ---
  {
    element: '[data-tour="take-answer-text"]',
    // TODO: Developer needs to add data-tour="take-answer-text" to text answer input in QuestionRenderer
    popover: {
      title: 'Текстовый ответ',
      description: 'Напишите развёрнутый ответ своими словами. Не бойтесь — можно редактировать до отправки!',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="take-answer-choice"]',
    // TODO: Developer needs to add data-tour="take-answer-choice" to choice options in QuestionRenderer
    popover: {
      title: 'Выбор ответа',
      description: 'Кликните на правильный вариант. Один или несколько — зависит от типа вопроса.',
      side: 'bottom',
    },
  },

  // --- ВОПРОС: КОД ---
  {
    element: '[data-tour="take-code-editor"]',
    // TODO: Developer needs to add data-tour="take-code-editor" to code textarea in CodeQuestionRenderer
    popover: {
      title: 'Редактор кода',
      description: 'Пишите код прямо в браузере! Подсветка синтаксиса поможет не запутаться. Попробуйте написать свой первый код!',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="take-code-run"]',
    // TODO: Developer needs to add data-tour="take-code-run" to Run button in CodeQuestionRenderer
    popover: {
      title: 'Запустить код',
      description: 'Нажмите, чтобы выполнить код и увидеть результат в консоли. Тестируйте решение перед отправкой!',
      side: 'left',
    },
  },
  {
    element: '[data-tour="take-code-tests"]',
    // TODO: Developer needs to add data-tour="take-code-tests" to tests tab/section in CodeQuestionRenderer
    popover: {
      title: 'Результаты тестов',
      description: 'Если преподаватель добавил тесты — вы увидите какие проходят, а какие нет. Зелёные галочки = успех!',
      side: 'left',
    },
  },
  {
    element: '[data-tour="take-code-output"]',
    // TODO: Developer needs to add data-tour="take-code-output" to output terminal in CodeQuestionRenderer
    popover: {
      title: 'Консоль вывода',
      description: 'Результат выполнения кода. Ошибки тоже покажутся здесь — читайте и исправляйте.',
      side: 'top',
    },
  },

  // --- ВОПРОС: ЗАГРУЗКА ФАЙЛА ---
  {
    element: '[data-tour="take-file-dropzone"]',
    // TODO: Developer needs to add data-tour="take-file-dropzone" to drop zone in FileUploadRenderer
    popover: {
      title: 'Загрузка файла',
      description: 'Перетащите файл сюда или кликните для выбора. Поддерживаются изображения и документы. Отличная работа!',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="take-file-preview"]',
    // TODO: Developer needs to add data-tour="take-file-preview" to file preview in FileUploadRenderer
    popover: {
      title: 'Превью файла',
      description: 'Загруженный файл отобразится здесь. Можно удалить и загрузить другой.',
      side: 'top',
    },
  },

  // --- ИНТЕРАКТИВНЫЕ ВОПРОСЫ ---
  {
    element: '[data-tour="take-interactive-area"]',
    // TODO: Developer needs to add data-tour="take-interactive-area" to interactive question area
    popover: {
      title: 'Интерактивное задание',
      description: 'Перетаскивайте карточки, кликайте на области карты или соединяйте пары. Взаимодействуйте с элементами!',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="take-dragdrop-items"]',
    // TODO: Developer needs to add data-tour="take-dragdrop-items" to draggable items in QuestionRenderer
    popover: {
      title: 'Перетаскивание элементов',
      description: 'Расположите элементы в правильном порядке. Хватайте и тащите!',
      side: 'right',
    },
  },
  {
    element: '[data-tour="take-hotspot-image"]',
    // TODO: Developer needs to add data-tour="take-hotspot-image" to hotspot image in QuestionRenderer
    popover: {
      title: 'Интерактивная карта',
      description: 'Кликните на правильные области изображения. Внимательно читайте условие!',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="take-matching-columns"]',
    // TODO: Developer needs to add data-tour="take-matching-columns" to matching columns in QuestionRenderer
    popover: {
      title: 'Сопоставление',
      description: 'Соедините элементы левой колонки с правой. Drag & Drop или клик-клик.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="take-fillblanks"]',
    // TODO: Developer needs to add data-tour="take-fillblanks" to fill blanks inputs in QuestionRenderer
    popover: {
      title: 'Заполните пропуски',
      description: 'Впишите правильные слова в пустые поля. Будьте внимательны с орфографией!',
      side: 'bottom',
    },
  },

  // --- АУДИРОВАНИЕ ---
  {
    element: '[data-tour="take-listening-player"]',
    // TODO: Developer needs to add data-tour="take-listening-player" to audio player in QuestionRenderer
    popover: {
      title: 'Аудиоплеер',
      description: 'Прослушайте запись перед ответом. Можно перематывать и слушать повторно.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="take-listening-questions"]',
    // TODO: Developer needs to add data-tour="take-listening-questions" to listening sub-questions
    popover: {
      title: 'Вопросы к аудио',
      description: 'Ответьте на вопросы по содержанию записи. Слушайте внимательно!',
      side: 'top',
    },
  },

  // --- НАВИГАЦИЯ И СОХРАНЕНИЕ ---
  {
    element: '[data-tour="take-nav-buttons"]',
    // TODO: Developer needs to add data-tour="take-nav-buttons" to prev/next buttons in HomeworkTake
    popover: {
      title: 'Навигация',
      description: 'Кнопки "Назад" и "Далее" для последовательного прохождения. Или используйте навигатор справа.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="take-autosave"]',
    // TODO: Developer needs to add data-tour="take-autosave" to autosave indicator in HomeworkTake
    popover: {
      title: 'Автосохранение',
      description: 'Ваши ответы сохраняются автоматически! Даже если закроете вкладку — прогресс не потеряется.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="take-submit-btn"]',
    // TODO: Developer needs to add data-tour="take-submit-btn" to submit button in HomeworkTake
    popover: {
      title: 'Отправить работу',
      description: 'Готовы? Нажмите "Сдать задание". Важно: после отправки изменить ответы будет нельзя!',
      side: 'top',
    },
  },
  {
    popover: {
      title: 'Успехов!',
      description: 'Внимательно читайте вопросы, не торопитесь и проверяйте ответы перед отправкой. Вы справитесь!',
    },
  },
];

// =====================================================
// СЦЕНАРИЙ 2: УЧЕНИК - РЕЗУЛЬТАТЫ И AI-АНАЛИЗ
// =====================================================
export const studentAIReportsSteps = [
  {
    popover: {
      title: 'Ваша аналитика',
      description: 'Здесь AI показывает ваш прогресс, сильные стороны и области для улучшения. Давайте разберёмся!',
    },
  },
  {
    element: '[data-tour="ai-summary"]',
    // TODO: Developer needs to add data-tour="ai-summary" to summary section in StudentAIReports
    popover: {
      title: 'Общая сводка',
      description: 'Средний балл, количество сданных работ и тренд прогресса. Быстрый взгляд на ваши достижения.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="ai-progress-chart"]',
    // TODO: Developer needs to add data-tour="ai-progress-chart" to progress chart in StudentAIReports
    popover: {
      title: 'График прогресса',
      description: 'Смотрите как меняются ваши навыки от урока к уроку. Рост — это отлично! Падение — сигнал уделить больше внимания.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="ai-skills"]',
    // TODO: Developer needs to add data-tour="ai-skills" to skills breakdown in StudentAIReports
    popover: {
      title: 'Анализ по навыкам',
      description: 'AI разбивает результаты по категориям: грамматика, лексика, понимание текста и т.д. Видно где вы сильны, а где стоит поработать.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="ai-error-breakdown"]',
    // TODO: Developer needs to add data-tour="ai-error-breakdown" to error analysis in StudentAIReports
    popover: {
      title: 'Разбор ошибок',
      description: 'AI объясняет почему ваш ответ был неверным и даёт правило. Учитесь на ошибках — это нормально!',
      side: 'top',
    },
  },
  {
    element: '[data-tour="ai-recommendations"]',
    // TODO: Developer needs to add data-tour="ai-recommendations" to recommendations section
    popover: {
      title: 'Рекомендации',
      description: 'Персональные советы от AI: что повторить, на что обратить внимание. Следуйте им для быстрого прогресса!',
      side: 'top',
    },
  },
  {
    popover: {
      title: 'Вы на пути к успеху!',
      description: 'Регулярно проверяйте аналитику, работайте над слабыми местами и отмечайте свои победы. AI — ваш помощник в обучении!',
    },
  },
];

// =====================================================
// ЭКСПОРТ ВСЕХ КОНФИГУРАЦИЙ
// =====================================================
export default {
  // Учитель: Конструктор ДЗ (детальный с типами вопросов)
  homeworkConstructorDetailedSteps,
  
  // Учитель: Проверка работ
  submissionReviewSteps,
  
  // Учитель: Список сданных работ
  gradedSubmissionsListSteps,
  
  // Ученик: Прохождение ДЗ
  homeworkTakeSteps,
  
  // Ученик: AI-анализ результатов
  studentAIReportsSteps,
  
  // Утилиты
  elementExists,
  filterExistingSteps,
};
