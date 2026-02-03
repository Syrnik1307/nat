/**
 * Конфигурация шагов онбординг-туров для Lectio Space
 * 
 * Формат шага:
 * {
 *   element: '[data-tour="..."]', // CSS-селектор элемента
 *   popover: {
 *     title: 'Заголовок',
 *     description: 'Описание',
 *     side: 'top' | 'bottom' | 'left' | 'right',
 *     align: 'start' | 'center' | 'end',
 *   }
 * }
 * 
 * Версионирование: При изменении шагов обновите TOUR_VERSION в useOnboarding.js
 */

// =====================================================
// TEACHER HOME PAGE TOUR (главная страница преподавателя)
// =====================================================
export const teacherTourSteps = [
  {
    popover: {
      title: 'Добро пожаловать в Lectio Space!',
      description: 'Краткий тур по платформе. Покажем основные функции за 1 минуту.',
    },
  },
  {
    element: '[data-tour="teacher-hero"]',
    popover: {
      title: 'Быстрый старт урока',
      description: 'Нажмите, чтобы мгновенно создать видеоконференцию. Zoom или Google Meet — на выбор.',
      side: 'bottom',
      align: 'start',
    },
  },
  {
    element: '[data-tour="teacher-schedule"]',
    popover: {
      title: 'Расписание на сегодня',
      description: 'Все ваши уроки на сегодня. Можно запустить, завершить или изменить тему прямо здесь.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="teacher-students"]',
    popover: {
      title: 'Ученики и группы',
      description: 'Список групп с количеством учеников. Нажмите "Управление" для добавления новых.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="teacher-stats"]',
    popover: {
      title: 'Статистика и аналитика',
      description: 'Уроков проведено, учеников, ДЗ на проверку, автопроверка — всё в одном месте.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="teacher-navbar"]',
    popover: {
      title: 'Навигация',
      description: 'Записи уроков, аналитика, домашние задания, подписка — в верхнем меню.',
      side: 'bottom',
    },
  },
  {
    popover: {
      title: 'Готово!',
      description: 'Вы знаете основы. Кнопка "Повторить тур" есть в профиле. Удачных занятий!',
    },
  },
];

// =====================================================
// STUDENT HOME PAGE TOUR (главная страница ученика)
// =====================================================
export const studentTourSteps = [
  {
    popover: {
      title: 'Добро пожаловать в Lectio Space!',
      description: 'Покажем основные разделы платформы. Займёт 30 секунд.',
    },
  },
  {
    element: '[data-tour="student-next-lesson"]',
    popover: {
      title: 'Ближайший урок',
      description: 'Карточка следующего урока. Когда преподаватель запустит — появится кнопка "Присоединиться".',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="student-groups"]',
    popover: {
      title: 'Ваши группы',
      description: 'Список курсов, на которых вы учитесь. Нажмите на группу для подробностей.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="student-join-group"]',
    popover: {
      title: 'Присоединиться к группе',
      description: 'Получили код от преподавателя? Нажмите сюда и введите его.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="student-navbar"]',
    popover: {
      title: 'Навигация',
      description: 'Домашние задания, записи уроков, статистика — в верхнем меню.',
      side: 'bottom',
    },
  },
  {
    popover: {
      title: 'Всё готово!',
      description: 'Повторить тур можно в профиле. Успехов в учёбе!',
    },
  },
];

// =====================================================
// SUBSCRIPTION PAGE TOUR (страница подписки и оплаты)
// =====================================================
export const subscriptionTourSteps = [
  {
    popover: {
      title: 'Управление подпиской',
      description: 'Здесь вы управляете своей подпиской, хранилищем и Zoom-аккаунтом. Давайте разберёмся!',
    },
  },
  {
    element: '[data-tour="subscription-status"]',
    popover: {
      title: 'Статус подписки',
      description: 'Текущий статус, когда начата и когда истекает подписка. Красный бейдж = требуется оплата.',
      side: 'bottom',
      align: 'start',
    },
  },
  {
    element: '[data-tour="subscription-storage-bar"]',
    popover: {
      title: 'Использование хранилища',
      description: 'Прогресс-бар показывает сколько из вашего лимита занято записями уроков. Желтый = близко к лимиту.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="subscription-cycle"]',
    popover: {
      title: 'Оставшиеся дни',
      description: 'Сколько дней осталось до окончания текущего цикла подписки (28 дней).',
      side: 'top',
    },
  },
  {
    element: '[data-tour="subscription-pay-btn"]',
    popover: {
      title: 'Оплата подписки',
      description: 'Нажмите для оплаты. Перейдёте на страницу T-Bank для безопасной оплаты картой.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="subscription-autorenew"]',
    popover: {
      title: 'Автопродление',
      description: 'Включите, чтобы подписка продлевалась автоматически. Отключить можно в любой момент.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="subscription-extra-storage"]',
    popover: {
      title: 'Дополнительное хранилище',
      description: 'Нужно больше места для записей? Докупите гигабайты. 20₽/GB — без срока действия.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="subscription-zoom"]',
    popover: {
      title: 'Zoom-аккаунт',
      description: 'Используйте общий пул Zoom-аккаунтов (бесплатно) или подключите свой личный аккаунт.',
      side: 'top',
    },
  },
  {
    popover: {
      title: 'Готово!',
      description: 'Теперь вы знаете все возможности страницы подписки. При вопросах — напишите в поддержку.',
    },
  },
];

// =====================================================
// HOMEWORK PAGE TOUR (страница домашних заданий)
// =====================================================
export const homeworkTourSteps = [
  {
    popover: {
      title: 'Домашние задания',
      description: 'Мощный инструмент для создания и проверки ДЗ. Давайте изучим все разделы!',
    },
  },
  {
    element: '[data-tour="homework-tabs"]',
    popover: {
      title: 'Навигация по разделам',
      description: '4 вкладки: Конструктор — создание ДЗ, Мои ДЗ — управление, На проверку — работы учеников, Проверенные — архив.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="homework-tab-constructor"]',
    popover: {
      title: 'Конструктор ДЗ',
      description: 'Создавайте интерактивные задания: тесты, заполнение пропусков, сопоставления, код — 10 типов вопросов!',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="homework-tab-my"]',
    popover: {
      title: 'Мои ДЗ',
      description: 'Все созданные вами задания. Редактируйте, дублируйте, назначайте группам или удаляйте.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="homework-tab-review"]',
    popover: {
      title: 'На проверку',
      description: 'Работы учеников, ожидающие вашей проверки. Бейдж показывает количество непроверенных.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="homework-tab-graded"]',
    popover: {
      title: 'Проверенные',
      description: 'Архив проверенных работ. Можно пересмотреть оценки и комментарии.',
      side: 'bottom',
    },
  },
  {
    popover: {
      title: 'Супер!',
      description: 'Теперь вы знаете все разделы. Начните с вкладки "Конструктор" для создания первого ДЗ!',
    },
  },
];

// =====================================================
// HOMEWORK CONSTRUCTOR TOUR (конструктор ДЗ - детальный)
// =====================================================
export const homeworkConstructorTourSteps = [
  {
    popover: {
      title: 'Конструктор домашних заданий',
      description: 'Создавайте интерактивные задания за минуты. Покажем все возможности!',
    },
  },
  {
    element: '[data-tour="hw-meta-title"]',
    popover: {
      title: 'Название задания',
      description: 'Введите понятное название. Например: "Контрольная по теме 5" или "Домашка 12 ноября".',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-meta-description"]',
    popover: {
      title: 'Описание и инструкции',
      description: 'Опционально. Объясните ученикам что от них требуется, ограничения, советы.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-meta-groups"]',
    popover: {
      title: 'Назначение группам',
      description: 'Выберите группы и конкретных учеников. Можно назначить всей группе или выборочно.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="hw-meta-deadline"]',
    popover: {
      title: 'Дедлайн',
      description: 'Установите срок сдачи. После дедлайна ученики не смогут отправить работу.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="hw-meta-score"]',
    popover: {
      title: 'Максимальный балл',
      description: 'Система автоматически рассчитает на основе весов вопросов. Можно изменить вручную.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="hw-questions-list"]',
    popover: {
      title: 'Список вопросов',
      description: 'Ваши вопросы отображаются здесь. Drag & Drop для изменения порядка.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="hw-add-question"]',
    popover: {
      title: 'Добавить вопрос',
      description: '10 типов: текст, один/несколько ответов, аудирование, сопоставление, перетаскивание, пропуски, hotspot, код, загрузка файла.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="hw-preview"]',
    popover: {
      title: 'Превью',
      description: 'Посмотрите как задание выглядит для ученика. Переключайтесь между вопросами.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="hw-actions"]',
    popover: {
      title: 'Сохранить и опубликовать',
      description: 'Черновик — сохранить без публикации. Опубликовать — ученики сразу увидят задание.',
      side: 'top',
    },
  },
  {
    popover: {
      title: 'Вы готовы!',
      description: 'Создайте первый вопрос, настройте параметры и опубликуйте. Автопроверка работает для большинства типов!',
    },
  },
];

// =====================================================
// RECORDINGS PAGE TOUR (страница записей уроков)
// =====================================================
export const recordingsTourSteps = [
  {
    popover: {
      title: 'Записи уроков',
      description: 'Все ваши видеозаписи занятий в одном месте. Удобный поиск и просмотр.',
    },
  },
  {
    element: '[data-tour="recordings-header"]',
    popover: {
      title: 'Ваша библиотека',
      description: 'Записи автоматически сохраняются после каждого Zoom-урока с активной подпиской.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="recordings-search"]',
    popover: {
      title: 'Поиск',
      description: 'Найдите запись по названию урока, предмету или группе. Поиск работает мгновенно.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="recordings-filter"]',
    popover: {
      title: 'Фильтр по группе',
      description: 'Отфильтруйте записи по конкретной группе или курсу.',
      side: 'left',
    },
  },
  {
    element: '[data-tour="recordings-card"]',
    popover: {
      title: 'Карточка записи',
      description: 'Нажмите для просмотра. Видны: название, дата, длительность, группа. Встроенный плеер откроется в модалке.',
      side: 'top',
    },
  },
  {
    popover: {
      title: 'Готово!',
      description: 'Теперь вы знаете как находить и смотреть записи. Хранилище зависит от вашей подписки.',
    },
  },
];

// =====================================================
// ANALYTICS PAGE TOUR (страница аналитики - расширенный)
// =====================================================
export const analyticsTourSteps = [
  {
    popover: {
      title: 'Аналитика и статистика',
      description: 'Детальная информация о ваших учениках, группах и динамике обучения.',
    },
  },
  {
    element: '[data-tour="analytics-tabs"]',
    popover: {
      title: 'Разделы аналитики',
      description: 'Обзор — ключевые метрики, Ученики — по каждому, Группы — статистика групп, Оповещения — важные уведомления.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="analytics-stats-row"]',
    popover: {
      title: 'Ключевые показатели',
      description: 'Количество групп, учеников, уроков, средний балл. Обновляются в реальном времени.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="analytics-charts"]',
    popover: {
      title: 'Графики динамики',
      description: 'Визуализация: количество уроков по неделям, посещаемость, выполнение ДЗ.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="analytics-search"]',
    popover: {
      title: 'Поиск ученика',
      description: 'Быстрый поиск по имени, email или группе для детальной статистики.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="analytics-alerts"]',
    popover: {
      title: 'Оповещения',
      description: 'Автоматические уведомления о рисках: пропуски подряд, снижение успеваемости, несданные ДЗ.',
      side: 'left',
    },
  },
  {
    popover: {
      title: 'Отлично!',
      description: 'Используйте аналитику для раннего выявления проблем и улучшения качества обучения.',
    },
  },
];

// =====================================================
// MARKET PAGE TOUR (маркет / магазин услуг)
// =====================================================
export const marketTourSteps = [
  {
    popover: {
      title: 'Маркет',
      description: 'Магазин цифровых услуг для ученика. Дополнительные возможности за разумные цены.',
    },
  },
  {
    element: '[data-tour="market-header"]',
    popover: {
      title: 'Каталог услуг',
      description: 'Здесь представлены доступные для покупки услуги и подписки.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="market-custom-banner"]',
    popover: {
      title: 'Индивидуальные услуги',
      description: 'Нужна оплата зарубежного сервиса? ChatGPT, Midjourney, Notion — поможем по ценам ниже рынка.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="market-products"]',
    popover: {
      title: 'Товары и подписки',
      description: 'Карточки товаров. Нажмите для покупки — откроется модалка с деталями.',
      side: 'top',
    },
  },
  {
    element: '[data-tour="market-product-card"]',
    popover: {
      title: 'Карточка товара',
      description: 'Название, описание, цена и кнопка покупки. Оплата через T-Bank.',
      side: 'top',
    },
  },
  {
    popover: {
      title: 'Готово!',
      description: 'Выбирайте нужные услуги. При проблемах с оплатой — напишите в поддержку.',
    },
  },
];

// =====================================================
// STUDENT HOMEWORK TOUR (страница ДЗ для ученика)
// =====================================================
export const studentHomeworkTourSteps = [
  {
    popover: {
      title: 'Ваши домашние задания',
      description: 'Здесь вы выполняете и отправляете ДЗ. Давайте разберёмся!',
    },
  },
  {
    element: '[data-tour="student-hw-list"]',
    popover: {
      title: 'Список заданий',
      description: 'Все назначенные вам ДЗ. Цветом выделены: зелёный — выполнено, красный — просрочено.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="student-hw-card"]',
    popover: {
      title: 'Карточка задания',
      description: 'Название, дедлайн, статус. Нажмите чтобы открыть и начать выполнение.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="student-hw-deadline"]',
    popover: {
      title: 'Дедлайн',
      description: 'Срок сдачи. После этой даты отправить работу будет нельзя — следите за временем!',
      side: 'left',
    },
  },
  {
    popover: {
      title: 'Успехов!',
      description: 'Выполняйте задания вовремя. Автопроверка покажет результат сразу после отправки.',
    },
  },
];

// =====================================================
// STUDENT RECORDINGS TOUR (записи для ученика)
// =====================================================
export const studentRecordingsTourSteps = [
  {
    popover: {
      title: 'Записи уроков',
      description: 'Пропустили занятие? Здесь можно пересмотреть запись.',
    },
  },
  {
    element: '[data-tour="recordings-header"]',
    popover: {
      title: 'Ваши записи',
      description: 'Записи уроков из групп, в которых вы состоите. Преподаватель решает какие записи открыть.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="recordings-search"]',
    popover: {
      title: 'Поиск',
      description: 'Ищите по названию или дате. Полезно если много записей.',
      side: 'bottom',
    },
  },
  {
    element: '[data-tour="recordings-card"]',
    popover: {
      title: 'Карточка записи',
      description: 'Нажмите для просмотра. Встроенный плеер с регулировкой скорости и перемоткой.',
      side: 'top',
    },
  },
  {
    popover: {
      title: 'Готово!',
      description: 'Пересматривайте уроки для закрепления материала. Полезно перед экзаменами!',
    },
  },
];

export default { 
  teacherTourSteps, 
  studentTourSteps, 
  subscriptionTourSteps,
  analyticsTourSteps,
  homeworkTourSteps,
  homeworkConstructorTourSteps,
  recordingsTourSteps,
  marketTourSteps,
  studentHomeworkTourSteps,
  studentRecordingsTourSteps,
};
