const QUESTION_TYPES = [
  {
    value: 'TEXT',
    label: '📝 Текстовый ответ',
    description: 'Короткие или развернутые письменные ответы.',
  },
  {
    value: 'SINGLE_CHOICE',
    label: '⭕ Одиночный выбор',
    description: 'Один правильный вариант из нескольких.',
  },
  {
    value: 'MULTIPLE_CHOICE',
    label: '☑️ Множественный выбор',
    description: 'Несколько корректных вариантов ответа.',
  },
  {
    value: 'LISTENING',
    label: '🎧 Лисенинг',
    description: 'Вопросы на основе аудио дорожки.',
  },
  {
    value: 'MATCHING',
    label: '🔗 Соединяющие блоки',
    description: 'Сопоставление элементов двух списков.',
  },
  {
    value: 'DRAG_DROP',
    label: '↕️ Перетаскивание',
    description: 'Упорядочивание элементов перетаскиванием.',
  },
  {
    value: 'FILL_BLANKS',
    label: '✍️ Заполнить пропуски',
    description: 'Ответы встраиваются в текстовые пропуски.',
  },
  {
    value: 'HOTSPOT',
    label: '🎯 Хотспот на изображении',
    description: 'Выбор областей на изображении.',
  },
];

const defaultConfigByType = {
  TEXT: {
    answerLength: 'short',
    correctAnswer: '',
  },
  SINGLE_CHOICE: {
    options: [
      { id: 'opt-1', text: 'Вариант 1' },
      { id: 'opt-2', text: 'Вариант 2' },
    ],
    correctOptionId: 'opt-1',
  },
  MULTIPLE_CHOICE: {
    options: [
      { id: 'opt-1', text: 'Вариант 1' },
      { id: 'opt-2', text: 'Вариант 2' },
      { id: 'opt-3', text: 'Вариант 3' },
    ],
    correctOptionIds: ['opt-1'],
  },
  LISTENING: {
    audioUrl: '',
    prompt: '',
    subQuestions: [],
  },
  MATCHING: {
    pairs: [
      { id: 'pair-1', left: 'A', right: '1' },
      { id: 'pair-2', left: 'B', right: '2' },
    ],
    shuffleRightColumn: true,
  },
  DRAG_DROP: {
    items: [
      { id: 'item-1', text: 'Шаг 1' },
      { id: 'item-2', text: 'Шаг 2' },
    ],
    correctOrder: ['item-1', 'item-2'],
  },
  FILL_BLANKS: {
    template: 'Пример текста с [___] пропуском.',
    answers: [''],
    caseSensitive: false,
    matchingStrategy: 'exact',
  },
  HOTSPOT: {
    imageUrl: '',
    hotspots: [],
    maxAttempts: 1,
  },
};

const createQuestionTemplate = (type) => {
  const now = Date.now();
  const random = Math.random().toString(16).slice(2, 8);
  const id = `q-${now}-${random}`;
  return {
    id,
    question_type: type,
    question_text: '',
    points: 10,
    order: 0,
    config: JSON.parse(JSON.stringify(defaultConfigByType[type] || {})),
    correct_answer: null,
  };
};

const getQuestionLabel = (type) => {
  const meta = QUESTION_TYPES.find((item) => item.value === type);
  return meta ? meta.label : type;
};

const getQuestionIcon = (type) => {
  const icons = {
    TEXT: '📝',
    SINGLE_CHOICE: '⭕',
    MULTIPLE_CHOICE: '☑️',
    LISTENING: '🎧',
    MATCHING: '🔗',
    DRAG_DROP: '↕️',
    FILL_BLANKS: '✍️',
    HOTSPOT: '🎯',
  };
  return icons[type] || '❓';
};

export { QUESTION_TYPES, createQuestionTemplate, getQuestionLabel, getQuestionIcon };
