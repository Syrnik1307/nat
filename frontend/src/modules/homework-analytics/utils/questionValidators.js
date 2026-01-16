export const validateQuestion = (question) => {
  const issues = [];
  // Текст вопроса не обязателен если прикреплено изображение
  const hasImage = question.config?.imageUrl?.trim();
  if (!question.question_text?.trim() && !hasImage) {
    issues.push('Введите текст вопроса или прикрепите изображение');
  }
  if (!Number.isFinite(question.points) || question.points <= 0) {
    issues.push('Баллы за вопрос должны быть больше нуля');
  }

  switch (question.question_type) {
    case 'SINGLE_CHOICE': {
      const options = question.config?.options || [];
      if (options.length < 2) {
        issues.push('Минимум два варианта ответа');
      }
      if (!options.some((item) => item.id === question.config?.correctOptionId)) {
        issues.push('Отметьте правильный вариант');
      }
      break;
    }
    case 'MULTIPLE_CHOICE': {
      const options = question.config?.options || [];
      const correct = question.config?.correctOptionIds || [];
      if (options.length < 2) {
        issues.push('Минимум два варианта ответа');
      }
      if (!correct.length) {
        issues.push('Выберите хотя бы один правильный вариант');
      }
      break;
    }
    case 'FILL_BLANKS': {
      const template = question.config?.template || '';
      const blanks = (template.match(/\[___\]/g) || []).length;
      const answers = question.config?.answers || [];
      if (!blanks) {
        issues.push('Добавьте хотя бы один пропуск вида [___]');
      }
      if (answers.length !== blanks) {
        issues.push('Количество ответов должно совпадать с количеством пропусков');
      }
      
      // Проверка, что все ответы заполнены
      if (answers.some(answer => !answer?.trim())) {
        issues.push('Все правильные ответы для пропусков должны быть заполнены');
      }
      break;
    }
    case 'LISTENING': {
      const audioUrl = question.config?.audioUrl || '';
      const subQuestions = question.config?.subQuestions || [];
      if (!audioUrl.trim()) {
        issues.push('Добавьте ссылку на аудиофайл');
      }
      if (!subQuestions.length) {
        issues.push('Создайте хотя бы один подвопрос для лисенинга');
      } else if (subQuestions.some((item) => !item.text?.trim())) {
        issues.push('Каждый подвопрос должен содержать текст');
      }
      break;
    }
    case 'MATCHING': {
      const pairs = question.config?.pairs || [];
      if (!pairs.length) {
        issues.push('Добавьте хотя бы одну пару для сопоставления');
      }
      if (pairs.some((pair) => !pair.left?.trim() || !pair.right?.trim())) {
        issues.push('Каждая пара должна содержать значения в обеих колонках');
      }
      
      // Проверка уникальности элементов
      const leftValues = pairs.map(p => p.left).filter(Boolean);
      const rightValues = pairs.map(p => p.right).filter(Boolean);
      const uniqueLeft = new Set(leftValues);
      const uniqueRight = new Set(rightValues);
      
      if (uniqueLeft.size !== leftValues.length) {
        issues.push('Дублирующиеся элементы в левой колонке');
      }
      if (uniqueRight.size !== rightValues.length) {
        issues.push('Дублирующиеся элементы в правой колонке');
      }
      break;
    }
    case 'DRAG_DROP': {
      const items = question.config?.items || [];
      const order = question.config?.correctOrder || [];
      if (items.length < 2) {
        issues.push('Добавьте минимум два элемента для сортировки');
      }
      if (order.length !== items.length) {
        issues.push('Правильный порядок должен содержать все элементы');
      }
      break;
    }
    case 'HOTSPOT': {
      const imageUrl = question.config?.imageUrl || '';
      const hotspots = question.config?.hotspots || [];
      if (!imageUrl.trim()) {
        issues.push('Загрузите изображение для хотспота');
      }
      if (!hotspots.length) {
        issues.push('Добавьте хотя бы одну кликабельную область');
      }
      
      // Проверка, что у всех хотспотов есть координаты
      const invalidHotspots = hotspots.filter(h => 
        !h.x || !h.y || !h.width || !h.height
      );
      if (invalidHotspots.length > 0) {
        issues.push('Все области должны иметь корректные координаты');
      }
      break;
    }
    case 'CODE': {
      const testCases = question.config?.testCases || [];
      if (!testCases.length) {
        issues.push('Добавьте хотя бы один тест-кейс для автопроверки');
      } else {
        // Проверяем, что у каждого теста есть ожидаемый вывод
        const emptyOutputs = testCases.filter(tc => !tc.expectedOutput?.trim());
        if (emptyOutputs.length > 0) {
          issues.push('Каждый тест должен иметь ожидаемый вывод');
        }
      }
      break;
    }
    default:
      break;
  }

  return issues;
};

export const validateAssignmentMeta = (meta, options = {}) => {
  const { requireGroup = true } = options;
  const issues = [];
  if (!meta.title?.trim()) {
    issues.push('Название задания обязательно');
  }
  if (requireGroup && !meta.groupId) {
    issues.push('Выберите группу');
  }
  if (!Number.isFinite(meta.maxScore) || meta.maxScore <= 0) {
    issues.push('Максимальный балл должен быть больше нуля');
  }
  return issues;
};

export const summarizeQuestionIssues = (questions) =>
  questions.reduce((acc, question, index) => {
    const questionIssues = validateQuestion(question);
    if (questionIssues.length) {
      acc.push({
        index,
        issues: questionIssues,
      });
    }
    return acc;
  }, []);
