import {
  createHomework,
  updateHomework,
  getHomework,
  createSubmission,
  apiClient,
} from '../../../apiService';

const SUPPORTED_TYPES = [
  'TEXT',
  'SINGLE_CHOICE',
  'MULTIPLE_CHOICE',
  'LISTENING',
  'MATCHING',
  'DRAG_DROP',
  'FILL_BLANKS',
  'HOTSPOT',
  'CODE',
];

const mapFrontendTypeToBackend = (type) => {
  if (type === 'MULTIPLE_CHOICE') {
    return 'MULTI_CHOICE';
  }
  return type;
};

const buildChoiceList = (question) => {
  const options = question.config?.options || [];
  if (!options.length) {
    return [];
  }
  const correctIds = new Set(question.config?.correctOptionIds || []);
  const correctSingle = question.config?.correctOptionId || null;
  return options
    .filter((option) => option?.text?.trim())
    .map((option) => ({
      text: option.text.trim(),
      is_correct:
        question.question_type === 'SINGLE_CHOICE'
          ? option.id === correctSingle
          : correctIds.has(option.id),
    }));
};

const mapQuestionToPayload = (question, order) => {
  if (!SUPPORTED_TYPES.includes(question.question_type)) {
    const error = new Error(
      `Тип вопроса "${question.question_type}" пока не поддерживается сервером`
    );
    error.userFacing = true;
    throw error;
  }

  const question_type = mapFrontendTypeToBackend(question.question_type);
  const payload = {
    prompt: question.question_text?.trim() || '',
    question_type,
    points: Number.isFinite(question.points) ? question.points : 0,
    order,
    config: (question.config && typeof question.config === 'object') ? question.config : {},
  };

  if (question.question_type === 'SINGLE_CHOICE' || question.question_type === 'MULTIPLE_CHOICE') {
    payload.choices = buildChoiceList(question);
  }

  return payload;
};

export const buildHomeworkPayload = (meta, questions) => {
  // Реверсируем массив: в UI новые вопросы добавляются в начало,
  // но для студентов они должны идти в порядке создания (старые первые)
  const orderedQuestions = [...questions].reverse();
  const payload = {
    title: meta.title?.trim() || '',
    description: meta.description?.trim() || '',
    questions: orderedQuestions.map((question, index) => mapQuestionToPayload(question, index)),
  };

  // Передаём назначения группам с опциональными ограничениями по ученикам
  if (meta.groupAssignments && meta.groupAssignments.length > 0) {
    payload.group_assignments_data = meta.groupAssignments.map(ga => ({
      group_id: Number(ga.groupId),
      student_ids: ga.allStudents ? null : ga.studentIds.map(id => Number(id)),
    }));
  } else if (meta.groupId) {
    // Совместимость со старым форматом (один groupId)
    payload.group_assignments_data = [{ group_id: Number(meta.groupId), student_ids: null }];
  }

  // Передаём дедлайн
  if (meta.deadline) {
    payload.deadline = meta.deadline;
  }

  // Передаём максимальный балл
  if (meta.maxScore) {
    payload.max_score = Number(meta.maxScore);
  }

  return payload;
};

export const homeworkService = {
  buildHomeworkPayload,
  async create(meta, questions) {
    const payload = buildHomeworkPayload(meta, questions);
    const response = await createHomework(payload);
    return response?.data;
  },
  async update(id, meta, questions) {
    const payload = buildHomeworkPayload(meta, questions);
    const response = await updateHomework(id, payload);
    return response?.data;
  },
  async fetchHomework(homeworkId) {
    const response = await getHomework(homeworkId);
    return response.data;
  },
  async fetchSubmissions(params) {
    const { getSubmissions } = require('../../../apiService');
    return getSubmissions(params);
  },
  async startSubmission(homeworkId) {
    const response = await createSubmission({ homework: homeworkId });
    return response.data;
  },
  async saveProgress(submissionId, answers) {
    return apiClient.patch(`submissions/${submissionId}/answer/`, { answers });
  },
  async submit(submissionId) {
    return apiClient.post(`submissions/${submissionId}/submit/`);
  },
};

export default homeworkService;
