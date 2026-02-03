/**
 * tourConfig.js - ПОЛНАЯ конфигурация Driver.js туров для Lectio Space LMS
 * 
 * ВНИМАНИЕ: Все элементы используют data-tour атрибуты.
 * Разработчик ДОЛЖЕН добавить эти атрибуты в соответствующие компоненты.
 * 
 * Чек-лист атрибутов находится в конце файла.
 * 
 * Версия: 3.0 (Полная реализация)
 * Дата: Февраль 2026
 */

// =====================================================
// РАЗДЕЛ 1: TEACHER DASHBOARD
// =====================================================
export const teacherDashboardSteps = [
  // INTRO
  {
    popover: {
      title: 'Добро пожаловать в Lectio Space!',
      description: 'Покажем как работает платформа за 2 минуты. Вы сможете проводить уроки, создавать ДЗ и следить за прогрессом учеников.',
    },
  },

  // QUICK START
  {
    element: '[data-tour="teacher-quick-start"]',
    popover: {
      title: 'Быстрый старт урока',
      description: 'Нажмите, чтобы мгновенно создать видеоконференцию. Zoom или Google Meet — на выбор. Ученики получат ссылку автоматически.',
      side: 'bottom',
      align: 'start',
    },
  },

  // SCHEDULE
  {
    element: '[data-tour="teacher-schedule"]',
    popover: {
      title: 'Расписание на сегодня',
      description: 'Все ваши уроки на сегодня. Можно запустить, завершить или изменить тему прямо здесь. Активные уроки подсвечены зелёным.',
      side: 'bottom',
    },
  },

  // STUDENTS CARD
  {
    element: '[data-tour="teacher-students"]',
    popover: {
      title: 'Ученики и группы',
      description: 'Быстрый доступ к управлению учениками. Нажмите "Управление" чтобы добавить учеников или создать новую группу.',
      side: 'left',
    },
  },

  // STATS
  {
    element: '[data-tour="teacher-stats"]',
    popover: {
      title: 'Статистика и метрики',
      description: 'Уроков проведено, учеников, ДЗ на проверку — всё в одном месте. Следите за своим прогрессом!',
      side: 'top',
    },
  },

  // NAVBAR
  {
    element: '[data-tour="teacher-navbar"]',
    popover: {
      title: 'Главное меню',
      description: 'Записи уроков, аналитика, домашние задания, подписка — все разделы доступны в верхнем меню.',
      side: 'bottom',
    },
  },

  // NAV: ДЗ
  {
    element: '[data-tour="nav-homework"]',
    popover: {
      title: 'Конструктор ДЗ',
      description: 'Создавайте интерактивные задания с автопроверкой. 10 типов вопросов: от теста до программирования!',
      side: 'bottom',
    },
  },

  // NAV: Записи
  {
    element: '[data-tour="nav-recordings"]',
    popover: {
      title: 'Записи уроков',
      description: 'Все видеозаписи ваших уроков. Загружайте свои видео, делитесь с учениками.',
      side: 'bottom',
    },
  },

  // NAV: Аналитика
  {
    element: '[data-tour="nav-analytics"]',
    popover: {
      title: 'Аналитика',
      description: 'Подробная статистика по урокам, ДЗ и успеваемости учеников. Журнал оценок.',
      side: 'bottom',
    },
  },

  // OUTRO
  {
    popover: {
      title: 'Готово! Вы знаете основы.',
      description: 'Начните с создания группы и добавления учеников. Кнопка "Повторить тур" есть в профиле. Удачных занятий!',
    },
  },
];

// =====================================================
// РАЗДЕЛ 2: STUDENT DASHBOARD
// =====================================================
export const studentDashboardSteps = [
  // INTRO
  {
    popover: {
      title: 'Добро пожаловать в Lectio Space!',
      description: 'Покажем как пользоваться платформой. Это займёт 30 секунд.',
    },
  },

  // NEXT LESSON
  {
    element: '[data-tour="student-next-lesson"]',
    popover: {
      title: 'Ближайший урок',
      description: 'Карточка следующего урока. Когда преподаватель запустит занятие — появится кнопка "Присоединиться".',
      side: 'bottom',
    },
  },

  // GROUPS
  {
    element: '[data-tour="student-groups"]',
    popover: {
      title: 'Ваши курсы',
      description: 'Список курсов, на которых вы учитесь. Здесь видно имя преподавателя и количество участников.',
      side: 'top',
    },
  },

  // JOIN GROUP
  {
    element: '[data-tour="student-join-group"]',
    popover: {
      title: 'Присоединиться к группе',
      description: 'Получили код от преподавателя? Нажмите сюда и введите его, чтобы попасть в группу.',
      side: 'left',
    },
  },

  // NAVBAR
  {
    element: '[data-tour="student-navbar"]',
    popover: {
      title: 'Навигация',
      description: 'Домашние задания, расписание, записи — всё в верхнем меню.',
      side: 'bottom',
    },
  },

  // NAV: ДЗ (student)
  {
    element: '[data-tour="nav-homework-student"]',
    popover: {
      title: 'Домашние задания',
      description: 'Здесь вы выполняете и сдаёте ДЗ. Следите за дедлайнами — они подсвечены!',
      side: 'bottom',
    },
  },

  // NAV: Календарь (student)
  {
    element: '[data-tour="nav-calendar-student"]',
    popover: {
      title: 'Расписание',
      description: 'Календарь с вашими занятиями. Удобно планировать неделю.',
      side: 'bottom',
    },
  },

  // OUTRO
  {
    popover: {
      title: 'Всё готово!',
      description: 'Повторить тур можно в профиле. Успехов в учёбе!',
    },
  },
];

// =====================================================
// РАЗДЕЛ 3: HOMEWORK CONSTRUCTOR (Учитель)
// =====================================================
export const homeworkConstructorSteps = [
  // INTRO
  {
    popover: {
      title: 'Конструктор домашних заданий',
      description: 'Создавайте интерактивные задания за минуты. 10 типов вопросов с автопроверкой! Рассмотрим каждый элемент.',
    },
  },

  // META: Title
  {
    element: '[data-tour="hw-title"]',
    popover: {
      title: 'Название задания',
      description: 'Понятное название для учеников. Например: "ДЗ №5 — Present Perfect". Это первое, что увидит ученик.',
      side: 'bottom',
    },
  },

  // META: Description
  {
    element: '[data-tour="hw-description"]',
    popover: {
      title: 'Описание',
      description: 'Подробные инструкции для учеников. Можете добавить ссылки на материалы или объяснения.',
      side: 'bottom',
    },
  },

  // META: Group selector
  {
    element: '[data-tour="hw-group-selector"]',
    popover: {
      title: 'Выбор группы',
      description: 'Выберите группу или конкретных учеников, которым назначить задание. Можно выбрать несколько групп!',
      side: 'bottom',
    },
  },

  // META: Deadline
  {
    element: '[data-tour="hw-deadline"]',
    popover: {
      title: 'Дедлайн',
      description: 'Установите крайний срок сдачи. Ученики увидят обратный отсчёт. После дедлайна задание будет отмечено как просроченное.',
      side: 'bottom',
    },
  },

  // META: Max score
  {
    element: '[data-tour="hw-max-score"]',
    popover: {
      title: 'Максимальный балл',
      description: 'Баллы распределяются автоматически между вопросами. Например, 100 баллов на 10 вопросов = 10 баллов за вопрос.',
      side: 'left',
    },
  },

  // QUESTIONS PANEL
  {
    element: '[data-tour="hw-questions-panel"]',
    popover: {
      title: 'Панель вопросов',
      description: 'Здесь отображаются все добавленные вопросы. Перетаскивайте для изменения порядка, кликайте для редактирования.',
      side: 'right',
    },
  },

  // ADD QUESTION BUTTON
  {
    element: '[data-tour="hw-add-question"]',
    popover: {
      title: 'Добавить вопрос',
      description: 'Нажмите, чтобы выбрать тип вопроса из списка. Доступно 10 типов — от простого теста до программирования!',
      side: 'top',
    },
  },

  // QUESTION EDITOR AREA
  {
    element: '[data-tour="hw-question-editor"]',
    popover: {
      title: 'Редактор вопроса',
      description: 'Здесь настраиваются параметры выбранного вопроса. Каждый тип имеет свои уникальные настройки.',
      side: 'left',
    },
  },

  // PREVIEW
  {
    element: '[data-tour="hw-preview"]',
    popover: {
      title: 'Предпросмотр',
      description: 'Так задание увидит ученик. Проверьте, что всё отображается корректно перед публикацией.',
      side: 'left',
    },
  },

  // SAVE/PUBLISH
  {
    element: '[data-tour="hw-actions"]',
    popover: {
      title: 'Сохранение и публикация',
      description: '"Сохранить черновик" — для работы позже. "Опубликовать" — задание станет доступно ученикам немедленно.',
      side: 'top',
    },
  },

  // OUTRO
  {
    popover: {
      title: 'Конструктор готов к работе!',
      description: 'Далее рассмотрим каждый тип вопроса подробнее. Или можете начать создавать задание прямо сейчас!',
    },
  },
];

// =====================================================
// РАЗДЕЛ 4: ТИПЫ ВОПРОСОВ (Детальные туры)
// =====================================================

// 4.1 TEXT QUESTION
export const textQuestionSteps = [
  {
    popover: {
      title: 'Текстовый ответ',
      description: 'Ученик вводит свой ответ текстом. Подходит для эссе, определений, коротких ответов.',
    },
  },
  {
    element: '[data-tour="q-text-format"]',
    popover: {
      title: 'Формат ответа',
      description: '"Короткий" — одна строка (для определений). "Развёрнутый" — многострочное поле (для эссе).',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="q-text-answer"]',
    popover: {
      title: 'Эталонный ответ',
      description: 'Укажите правильный ответ для автопроверки. Оставьте пустым для ручной проверки учителем.',
      side: 'bottom',
    },
  },
];

// 4.2 SINGLE CHOICE QUESTION
export const singleChoiceSteps = [
  {
    popover: {
      title: 'Один правильный ответ',
      description: 'Классический тест с радио-кнопками. Ученик выбирает ровно один вариант.',
    },
  },
  {
    element: '[data-tour="q-single-options"]',
    popover: {
      title: 'Варианты ответов',
      description: 'Добавьте минимум 2 варианта. Отметьте радио-кнопку рядом с правильным вариантом.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="q-single-add"]',
    popover: {
      title: 'Добавить вариант',
      description: 'Нажмите, чтобы добавить ещё один вариант ответа. Рекомендуем 4-5 вариантов.',
      side: 'top',
    },
  },
];

// 4.3 MULTIPLE CHOICE QUESTION
export const multipleChoiceSteps = [
  {
    popover: {
      title: 'Несколько правильных ответов',
      description: 'Ученик выбирает все правильные варианты (чекбоксы). Может быть 2+ правильных ответа.',
    },
  },
  {
    element: '[data-tour="q-multi-options"]',
    popover: {
      title: 'Варианты ответов',
      description: 'Добавьте варианты и отметьте ВСЕ правильные галочками. Неотмеченные считаются неверными.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="q-multi-add"]',
    popover: {
      title: 'Добавить вариант',
      description: 'Добавляйте столько вариантов, сколько нужно. Можете отметить сразу несколько правильных.',
      side: 'top',
    },
  },
];

// 4.4 FILL BLANKS QUESTION
export const fillBlanksSteps = [
  {
    popover: {
      title: 'Заполнение пропусков',
      description: 'Ученик вписывает слова в пропуски. Идеально для грамматики, формул, определений.',
    },
  },
  {
    element: '[data-tour="q-fillblanks-template"]',
    popover: {
      title: 'Текст с пропусками',
      description: 'Введите текст, используя [___] для пропусков. Пример: "Столица России — [___]." Каждый [___] создаёт поле ввода.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="q-fillblanks-answers"]',
    popover: {
      title: 'Правильные ответы',
      description: 'Для каждого пропуска укажите правильный ответ. Порядок соответствует позиции в тексте.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="q-fillblanks-settings"]',
    popover: {
      title: 'Настройки проверки',
      description: '"Учитывать регистр" — Moscow ≠ moscow. "Допускать близкие варианты" — прощает опечатки.',
      side: 'left',
    },
  },
];

// 4.5 MATCHING QUESTION
export const matchingSteps = [
  {
    popover: {
      title: 'Сопоставление пар',
      description: 'Ученик соединяет элементы из левой колонки с правой. Отлично для терминов, переводов.',
    },
  },
  {
    element: '[data-tour="q-matching-pairs"]',
    popover: {
      title: 'Пары элементов',
      description: 'Добавьте пары: слева — термин/вопрос, справа — определение/ответ. Минимум 2 пары.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="q-matching-add"]',
    popover: {
      title: 'Добавить пару',
      description: 'Нажмите, чтобы добавить новую пару. Рекомендуем 4-6 пар для удобства.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="q-matching-shuffle"]',
    popover: {
      title: 'Перемешивание',
      description: 'Включите, чтобы правая колонка перемешивалась для каждого ученика. Защита от списывания!',
      side: 'left',
    },
  },
];

// 4.6 DRAG & DROP QUESTION
export const dragDropSteps = [
  {
    popover: {
      title: 'Перетаскивание (Drag & Drop)',
      description: 'Ученик перетаскивает элементы в правильном порядке. Подходит для хронологии, алгоритмов.',
    },
  },
  {
    element: '[data-tour="q-dragdrop-items"]',
    popover: {
      title: 'Элементы для сортировки',
      description: 'Добавьте элементы в ПРАВИЛЬНОМ порядке. При показе ученику они будут перемешаны автоматически.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="q-dragdrop-add"]',
    popover: {
      title: 'Добавить элемент',
      description: 'Добавляйте элементы. Используйте стрелки для изменения эталонного порядка.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="q-dragdrop-reorder"]',
    popover: {
      title: 'Изменение порядка',
      description: 'Стрелки перемещают элемент вверх/вниз. Этот порядок — правильный ответ.',
      side: 'left',
    },
  },
];

// 4.7 CODE QUESTION
export const codeQuestionSteps = [
  {
    popover: {
      title: 'Программирование',
      description: 'Ученик пишет код. Поддержка Python и JavaScript с автоматической проверкой тестами!',
    },
  },
  {
    element: '[data-tour="q-code-language"]',
    popover: {
      title: 'Язык программирования',
      description: 'Выберите Python или JavaScript. Код выполняется прямо в браузере (безопасно).',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="q-code-starter"]',
    popover: {
      title: 'Стартовый код',
      description: 'Заготовка кода для ученика. Можете добавить сигнатуру функции или подсказки в комментариях.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="q-code-solution"]',
    popover: {
      title: 'Эталонное решение',
      description: 'Напишите правильное решение. Оно используется для проверки тестов и не показывается ученику.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="q-code-tests"]',
    popover: {
      title: 'Тест-кейсы',
      description: 'Добавьте тесты: входные данные и ожидаемый вывод. Код ученика будет проверен автоматически.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="q-code-add-test"]',
    popover: {
      title: 'Добавить тест',
      description: 'Добавляйте несколько тестов для надёжной проверки. Рекомендуем 3-5 тестов разной сложности.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="q-code-run"]',
    popover: {
      title: 'Запустить решение',
      description: 'Проверьте своё эталонное решение перед публикацией. Убедитесь, что все тесты проходят.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="q-code-terminal"]',
    popover: {
      title: 'Терминал',
      description: 'Результаты выполнения кода. Вкладка "Тесты" показывает, какие тесты прошли/упали.',
      side: 'top',
    },
  },
];

// 4.8 FILE UPLOAD QUESTION
export const fileUploadSteps = [
  {
    popover: {
      title: 'Загрузка файла',
      description: 'Ученик загружает файл: фото работы, документ, проект. Проверка только ручная.',
    },
  },
  {
    element: '[data-tour="q-file-types"]',
    popover: {
      title: 'Типы файлов',
      description: 'Ограничьте загрузку: только изображения (JPG, PNG) или документы (PDF, Word, Excel).',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="q-file-max-count"]',
    popover: {
      title: 'Количество файлов',
      description: 'Сколько файлов может загрузить ученик. От 1 до 5.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="q-file-max-size"]',
    popover: {
      title: 'Максимальный размер',
      description: 'Лимит на один файл: 5, 10, 25 или 50 MB. Большие файлы дольше загружаются.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="q-file-instructions"]',
    popover: {
      title: 'Инструкции',
      description: 'Подсказка для ученика. Например: "Загрузите фото решения в тетради".',
      side: 'bottom',
    },
  },
];

// 4.9 HOTSPOT QUESTION
export const hotspotSteps = [
  {
    popover: {
      title: 'Клик на изображении',
      description: 'Ученик должен кликнуть на правильную область изображения. Отлично для анатомии, карт, схем.',
    },
  },
  {
    element: '[data-tour="q-hotspot-image"]',
    popover: {
      title: 'Изображение',
      description: 'Загрузите картинку, на которой нужно выделить области. Поддерживаются JPG, PNG, GIF, WebP.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="q-hotspot-areas"]',
    popover: {
      title: 'Области',
      description: 'Список кликабельных зон. Каждая область — прямоугольник с координатами в процентах.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="q-hotspot-add"]',
    popover: {
      title: 'Добавить область',
      description: 'Создайте новую зону. Задайте X, Y (позиция) и ширину/высоту в процентах от изображения.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="q-hotspot-coords"]',
    popover: {
      title: 'Координаты области',
      description: 'X и Y — левый верхний угол в %. Ширина и высота — размеры. Например: X=10%, Y=20%, W=30%, H=25%.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="q-hotspot-attempts"]',
    popover: {
      title: 'Попытки',
      description: 'Сколько раз ученик может попробовать кликнуть. По умолчанию — 1 попытка.',
      side: 'left',
    },
  },
];

// 4.10 LISTENING QUESTION
export const listeningSteps = [
  {
    popover: {
      title: 'Аудирование',
      description: 'Ученик слушает аудио и отвечает на вопросы. Идеально для изучения языков.',
    },
  },
  {
    element: '[data-tour="q-listening-audio"]',
    popover: {
      title: 'Аудиофайл',
      description: 'Загрузите MP3, WAV или OGG файл. Максимум 50 MB. Аудио будет проигрываться в браузере.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="q-listening-player"]',
    popover: {
      title: 'Предпросмотр',
      description: 'Проверьте, что аудио загрузилось и проигрывается корректно.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="q-listening-prompt"]',
    popover: {
      title: 'Инструкция',
      description: 'Что делать ученику. Например: "Послушайте диалог и ответьте на вопросы."',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="q-listening-subquestions"]',
    popover: {
      title: 'Подвопросы',
      description: 'Добавьте вопросы по аудио. Для каждого укажите формулировку и правильный ответ.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="q-listening-add"]',
    popover: {
      title: 'Добавить подвопрос',
      description: 'Создайте новый вопрос к аудио. Рекомендуем 3-5 вопросов разной сложности.',
      side: 'top',
    },
  },
];

// =====================================================
// РАЗДЕЛ 5: RECORDINGS (Записи уроков)
// =====================================================
export const recordingsSteps = [
  // INTRO
  {
    popover: {
      title: 'Записи уроков',
      description: 'Здесь хранятся все видеозаписи ваших занятий. Можете загружать свои видео и делиться с учениками.',
    },
  },

  // STATS
  {
    element: '[data-tour="rec-stats"]',
    popover: {
      title: 'Статистика',
      description: 'Общее количество записей, готовые к просмотру, в обработке и с ошибками.',
      side: 'bottom',
    },
  },

  // FILTERS
  {
    element: '[data-tour="rec-filters"]',
    popover: {
      title: 'Фильтры',
      description: 'Фильтруйте записи по группе, статусу. Поиск по названию урока.',
      side: 'bottom',
    },
  },

  // UPLOAD BUTTON
  {
    element: '[data-tour="rec-upload"]',
    popover: {
      title: 'Загрузить видео',
      description: 'Загрузите своё видео. Можно привязать к уроку или сделать самостоятельным материалом.',
      side: 'left',
    },
  },

  // RECORDING CARD
  {
    element: '[data-tour="rec-card"]',
    popover: {
      title: 'Карточка записи',
      description: 'Кликните для просмотра видео. Видны название, длительность, дата и количество просмотров.',
      side: 'right',
    },
  },

  // PLAY BUTTON
  {
    element: '[data-tour="rec-play"]',
    popover: {
      title: 'Воспроизведение',
      description: 'Нажмите для открытия видеоплеера. Поддерживается перемотка и полноэкранный режим.',
      side: 'bottom',
    },
  },

  // DELETE
  {
    element: '[data-tour="rec-delete"]',
    popover: {
      title: 'Удаление',
      description: 'Удалите ненужные записи. Внимание: действие необратимо!',
      side: 'left',
    },
  },

  // PRIVACY
  {
    element: '[data-tour="rec-privacy"]',
    popover: {
      title: 'Приватность',
      description: 'Выберите, кто видит запись: все ученики, конкретные группы или отдельные ученики.',
      side: 'left',
    },
  },
];

// =====================================================
// РАЗДЕЛ 6: MATERIALS (Материалы)
// =====================================================
export const materialsSteps = [
  // INTRO
  {
    popover: {
      title: 'Материалы урока',
      description: 'Доски Miro и конспекты для ваших уроков. Делитесь материалами с учениками!',
    },
  },

  // TABS
  {
    element: '[data-tour="mat-tabs"]',
    popover: {
      title: 'Вкладки',
      description: 'Переключение между досками Miro и текстовыми конспектами.',
      side: 'bottom',
    },
  },

  // MIRO CONNECT
  {
    element: '[data-tour="mat-miro-connect"]',
    popover: {
      title: 'Подключить Miro',
      description: 'Авторизуйтесь в Miro, чтобы добавлять доски из вашего аккаунта.',
      side: 'bottom',
    },
  },

  // ADD MIRO
  {
    element: '[data-tour="mat-add-miro"]',
    popover: {
      title: 'Добавить доску',
      description: 'Вставьте ссылку на Miro-доску или выберите из ваших досок.',
      side: 'left',
    },
  },

  // ADD NOTES
  {
    element: '[data-tour="mat-add-notes"]',
    popover: {
      title: 'Создать конспект',
      description: 'Создайте текстовый конспект с форматированием или загрузите PDF.',
      side: 'left',
    },
  },

  // MATERIAL CARD
  {
    element: '[data-tour="mat-card"]',
    popover: {
      title: 'Карточка материала',
      description: 'Кликните для просмотра. Видны название, тип и к какому уроку привязан.',
      side: 'right',
    },
  },

  // VISIBILITY
  {
    element: '[data-tour="mat-visibility"]',
    popover: {
      title: 'Видимость',
      description: 'Настройте доступ: все ученики, определённые группы или отдельные ученики.',
      side: 'left',
    },
  },
];

// =====================================================
// РАЗДЕЛ 7: STUDENTS MANAGE (Управление учениками)
// =====================================================
export const studentsManageSteps = [
  // INTRO
  {
    popover: {
      title: 'Управление учениками',
      description: 'Просмотр всех учеников, их статус, активность и привязка к группам.',
    },
  },

  // SEARCH
  {
    element: '[data-tour="students-search"]',
    popover: {
      title: 'Поиск',
      description: 'Ищите ученика по имени, email или номеру телефона.',
      side: 'bottom',
    },
  },

  // FILTERS
  {
    element: '[data-tour="students-filters"]',
    popover: {
      title: 'Фильтры',
      description: 'Фильтруйте по статусу (активные/архивные) и по преподавателю.',
      side: 'bottom',
    },
  },

  // TABLE
  {
    element: '[data-tour="students-table"]',
    popover: {
      title: 'Таблица учеников',
      description: 'Список всех учеников. Кликните на строку для просмотра деталей. Сортировка по заголовкам.',
      side: 'top',
    },
  },

  // STUDENT CARD
  {
    element: '[data-tour="students-card"]',
    popover: {
      title: 'Карточка ученика',
      description: 'Детали выбранного ученика: ФИО, группы, последняя активность.',
      side: 'left',
    },
  },

  // EDIT
  {
    element: '[data-tour="students-edit"]',
    popover: {
      title: 'Редактирование',
      description: 'Измените ФИО ученика. Данные сохраняются автоматически.',
      side: 'left',
    },
  },

  // ARCHIVE
  {
    element: '[data-tour="students-archive"]',
    popover: {
      title: 'Архивация',
      description: 'Архивируйте неактивных учеников. Они не будут видны в обычном списке.',
      side: 'top',
    },
  },
];

// =====================================================
// РАЗДЕЛ 8: GROUP MANAGEMENT (Управление группами)
// =====================================================
export const groupManageSteps = [
  // INTRO
  {
    popover: {
      title: 'Управление группами',
      description: 'Создавайте группы, добавляйте учеников, генерируйте пригласительные ссылки.',
    },
  },

  // CREATE GROUP
  {
    element: '[data-tour="group-create"]',
    popover: {
      title: 'Создать группу',
      description: 'Нажмите для создания новой группы. Укажите название и описание.',
      side: 'left',
    },
  },

  // GROUP CARD
  {
    element: '[data-tour="group-card"]',
    popover: {
      title: 'Карточка группы',
      description: 'Кликните для просмотра учеников и настроек. Количество участников указано.',
      side: 'right',
    },
  },

  // INVITE BUTTON
  {
    element: '[data-tour="group-invite"]',
    popover: {
      title: 'Пригласить учеников',
      description: 'Сгенерируйте ссылку-приглашение или код. Отправьте ученикам — они присоединятся автоматически.',
      side: 'bottom',
    },
  },

  // INDIVIDUAL INVITES
  {
    element: '[data-tour="group-individual-invites"]',
    popover: {
      title: 'Персональные приглашения',
      description: 'Создайте приглашение для конкретного ученика по email. Можно установить срок действия.',
      side: 'bottom',
    },
  },

  // STUDENTS LIST
  {
    element: '[data-tour="group-students-list"]',
    popover: {
      title: 'Список учеников',
      description: 'Участники группы. Можно удалить ученика из группы или перенести в другую.',
      side: 'left',
    },
  },

  // DELETE GROUP
  {
    element: '[data-tour="group-delete"]',
    popover: {
      title: 'Удалить группу',
      description: 'Удаление группы. Ученики НЕ удаляются — только связь с группой.',
      side: 'top',
    },
  },
];

// =====================================================
// РАЗДЕЛ 9: CALENDAR & SCHEDULE (Расписание)
// =====================================================
export const calendarSteps = [
  // INTRO
  {
    popover: {
      title: 'Расписание занятий',
      description: 'Календарь ваших уроков. Создавайте одиночные и повторяющиеся занятия.',
    },
  },

  // VIEWS
  {
    element: '[data-tour="cal-views"]',
    popover: {
      title: 'Режим просмотра',
      description: 'Переключайте между неделей, месяцем и списком занятий.',
      side: 'bottom',
    },
  },

  // NAV
  {
    element: '[data-tour="cal-nav"]',
    popover: {
      title: 'Навигация',
      description: 'Стрелки для перехода к предыдущей/следующей неделе или месяцу.',
      side: 'bottom',
    },
  },

  // CREATE LESSON
  {
    element: '[data-tour="cal-create"]',
    popover: {
      title: 'Создать занятие',
      description: 'Кликните на ячейку календаря или используйте кнопку. Укажите группу, время и тему.',
      side: 'left',
    },
  },

  // RECURRING
  {
    element: '[data-tour="cal-recurring"]',
    popover: {
      title: 'Повторяющиеся занятия',
      description: 'Создайте занятие, которое повторяется каждую неделю. Укажите дни и время.',
      side: 'left',
    },
  },

  // LESSON CARD
  {
    element: '[data-tour="cal-lesson"]',
    popover: {
      title: 'Занятие в календаре',
      description: 'Кликните для просмотра деталей. Цвет соответствует группе.',
      side: 'right',
    },
  },

  // QUICK LESSON
  {
    element: '[data-tour="cal-quick"]',
    popover: {
      title: 'Быстрый урок',
      description: 'Создайте видеоконференцию мгновенно, без привязки к расписанию.',
      side: 'bottom',
    },
  },
];

// =====================================================
// РАЗДЕЛ 10: PROFILE & SETTINGS (Профиль)
// =====================================================
export const profileSteps = [
  // INTRO
  {
    popover: {
      title: 'Настройки профиля',
      description: 'Личные данные, безопасность, уведомления и подписка.',
    },
  },

  // TABS
  {
    element: '[data-tour="profile-tabs"]',
    popover: {
      title: 'Разделы настроек',
      description: 'Профиль, уведомления, безопасность, платформы и подписка.',
      side: 'bottom',
    },
  },

  // AVATAR
  {
    element: '[data-tour="profile-avatar"]',
    popover: {
      title: 'Фото профиля',
      description: 'Кликните для загрузки аватара. Поддерживаются JPG, PNG до 2 MB.',
      side: 'right',
    },
  },

  // NAME
  {
    element: '[data-tour="profile-name"]',
    popover: {
      title: 'Имя и фамилия',
      description: 'Как вас видят ученики. Заполните все поля.',
      side: 'right',
    },
  },

  // TELEGRAM
  {
    element: '[data-tour="profile-telegram"]',
    popover: {
      title: 'Telegram уведомления',
      description: 'Подключите Telegram для получения уведомлений о новых ДЗ, уроках и сообщениях.',
      side: 'bottom',
    },
  },

  // TELEGRAM CODE
  {
    element: '[data-tour="profile-tg-code"]',
    popover: {
      title: 'Код привязки',
      description: 'Скопируйте код и отправьте боту @LectioSpaceBot. Аккаунт привяжется автоматически.',
      side: 'left',
    },
  },

  // NOTIFICATION SETTINGS
  {
    element: '[data-tour="profile-notifications"]',
    popover: {
      title: 'Настройки уведомлений',
      description: 'Выберите, о чём получать уведомления: новые ДЗ, напоминания, оценки.',
      side: 'right',
    },
  },

  // SECURITY
  {
    element: '[data-tour="profile-security"]',
    popover: {
      title: 'Безопасность',
      description: 'Смена пароля и email. Рекомендуем использовать надёжный пароль.',
      side: 'bottom',
    },
  },

  // SUBSCRIPTION
  {
    element: '[data-tour="profile-subscription"]',
    popover: {
      title: 'Подписка',
      description: 'Статус подписки, доступное хранилище и история платежей.',
      side: 'left',
    },
  },
];

// =====================================================
// РАЗДЕЛ 11: ANALYTICS (Аналитика)
// =====================================================
export const analyticsSteps = [
  // INTRO
  {
    popover: {
      title: 'Аналитика',
      description: 'Подробная статистика по урокам, ДЗ и успеваемости учеников.',
    },
  },

  // TABS
  {
    element: '[data-tour="analytics-tabs"]',
    popover: {
      title: 'Разделы аналитики',
      description: 'Обзор, журнал оценок, посещаемость, прогресс по ДЗ.',
      side: 'bottom',
    },
  },

  // STATS ROW
  {
    element: '[data-tour="analytics-stats-row"]',
    popover: {
      title: 'Ключевые метрики',
      description: 'Проведено уроков, средняя посещаемость, выполнение ДЗ.',
      side: 'bottom',
    },
  },

  // ALERTS
  {
    element: '[data-tour="analytics-alerts"]',
    popover: {
      title: 'Оповещения',
      description: 'Ученики в зоне риска: пропускают уроки или не сдают ДЗ. Требуют внимания!',
      side: 'right',
    },
  },

  // GRADEBOOK
  {
    element: '[data-tour="analytics-gradebook"]',
    popover: {
      title: 'Журнал оценок',
      description: 'Таблица с оценками всех учеников по всем ДЗ. Можно редактировать вручную.',
      side: 'top',
    },
  },

  // EXPORT
  {
    element: '[data-tour="analytics-export"]',
    popover: {
      title: 'Экспорт',
      description: 'Скачайте данные в Excel для отчётности или анализа.',
      side: 'left',
    },
  },
];

// =====================================================
// РАЗДЕЛ 12: SUBMISSION REVIEW (Проверка ДЗ)
// =====================================================
export const submissionReviewSteps = [
  // INTRO
  {
    popover: {
      title: 'Проверка домашней работы',
      description: 'Просмотрите ответы ученика, поставьте оценку и напишите комментарий.',
    },
  },

  // STUDENT INFO
  {
    element: '[data-tour="review-student"]',
    popover: {
      title: 'Информация об ученике',
      description: 'Имя ученика, время сдачи и статус работы.',
      side: 'bottom',
    },
  },

  // ANSWERS
  {
    element: '[data-tour="review-answers"]',
    popover: {
      title: 'Ответы ученика',
      description: 'Все ответы с указанием правильности. Автопроверенные вопросы отмечены галочкой.',
      side: 'right',
    },
  },

  // SCORE INPUT
  {
    element: '[data-tour="review-score"]',
    popover: {
      title: 'Оценка',
      description: 'Введите балл вручную или используйте автоматически рассчитанный.',
      side: 'left',
    },
  },

  // COMMENT
  {
    element: '[data-tour="review-comment"]',
    popover: {
      title: 'Комментарий',
      description: 'Напишите обратную связь для ученика. Он увидит комментарий в своём профиле.',
      side: 'bottom',
    },
  },

  // AI GRADING
  {
    element: '[data-tour="review-ai"]',
    popover: {
      title: 'AI-оценка',
      description: 'Используйте ИИ для автоматической проверки развёрнутых ответов. Экономит время!',
      side: 'left',
    },
  },

  // SUBMIT
  {
    element: '[data-tour="review-submit"]',
    popover: {
      title: 'Сохранить оценку',
      description: 'Нажмите для сохранения. Ученик получит уведомление о проверке.',
      side: 'top',
    },
  },
];

// =====================================================
// РАЗДЕЛ 13: STUDENT HOMEWORK (Выполнение ДЗ)
// =====================================================
export const studentHomeworkSteps = [
  // INTRO
  {
    popover: {
      title: 'Выполнение домашнего задания',
      description: 'Отвечайте на вопросы и отправьте работу на проверку.',
    },
  },

  // PROGRESS
  {
    element: '[data-tour="hw-student-progress"]',
    popover: {
      title: 'Прогресс',
      description: 'Сколько вопросов осталось. Отвеченные отмечаются галочкой.',
      side: 'bottom',
    },
  },

  // TIMER
  {
    element: '[data-tour="hw-student-timer"]',
    popover: {
      title: 'Время до дедлайна',
      description: 'Сколько осталось до крайнего срока. Не опаздывайте!',
      side: 'left',
    },
  },

  // QUESTION
  {
    element: '[data-tour="hw-student-question"]',
    popover: {
      title: 'Вопрос',
      description: 'Читайте внимательно и отвечайте. Некоторые вопросы проверяются автоматически.',
      side: 'bottom',
    },
  },

  // NAVIGATION
  {
    element: '[data-tour="hw-student-nav"]',
    popover: {
      title: 'Навигация',
      description: 'Переключайтесь между вопросами. Можно вернуться к любому.',
      side: 'top',
    },
  },

  // SUBMIT
  {
    element: '[data-tour="hw-student-submit"]',
    popover: {
      title: 'Отправить на проверку',
      description: 'Когда всё готово — нажмите для отправки. После отправки изменить ответы нельзя!',
      side: 'top',
    },
  },
];

// =====================================================
// ОБЪЕДИНЁННЫЕ ТУРЫ ПО РОЛЯМ
// =====================================================

// Полный тур для учителя (Dashboard)
export const teacherSteps = teacherDashboardSteps;

// Полный тур для ученика (Dashboard)
export const studentSteps = studentDashboardSteps;

// =====================================================
// ЭКСПОРТ ВСЕХ КОНФИГУРАЦИЙ
// =====================================================
export default {
  // По ролям
  teacher: teacherDashboardSteps,
  student: studentDashboardSteps,
  
  // По страницам
  teacherDashboard: teacherDashboardSteps,
  studentDashboard: studentDashboardSteps,
  homeworkConstructor: homeworkConstructorSteps,
  recordings: recordingsSteps,
  materials: materialsSteps,
  studentsManage: studentsManageSteps,
  groupManage: groupManageSteps,
  calendar: calendarSteps,
  profile: profileSteps,
  analytics: analyticsSteps,
  submissionReview: submissionReviewSteps,
  studentHomework: studentHomeworkSteps,
  
  // По типам вопросов
  questionText: textQuestionSteps,
  questionSingleChoice: singleChoiceSteps,
  questionMultipleChoice: multipleChoiceSteps,
  questionFillBlanks: fillBlanksSteps,
  questionMatching: matchingSteps,
  questionDragDrop: dragDropSteps,
  questionCode: codeQuestionSteps,
  questionFileUpload: fileUploadSteps,
  questionHotspot: hotspotSteps,
  questionListening: listeningSteps,
};
