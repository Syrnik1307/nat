export const validateQuestion = (question) => {
  const issues = [];
  if (!question.question_text?.trim()) {
    issues.push('Введите текст вопроса');
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
        issues.push('Укажите изображение для хотспота');
      }
      if (!hotspots.length) {
        issues.push('Добавьте хотя бы одну активную область');
      }
      break;
    }
    default:
      break;
  }

  return issues;
};

export const validateAssignmentMeta = (meta) => {
  const issues = [];
  if (!meta.title?.trim()) {
    issues.push('Название задания обязательно');
  }
  if (!meta.groupId) {
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
