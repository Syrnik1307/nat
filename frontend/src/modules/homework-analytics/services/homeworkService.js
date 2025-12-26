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

export const buildHomeworkPayload = (meta, questions) => ({
  title: meta.title?.trim() || '',
  description: meta.description?.trim() || '',
  questions: questions.map((question, index) => mapQuestionToPayload(question, index)),
  // AI grading settings
  ai_grading_enabled: Boolean(meta.aiGradingEnabled),
  ai_provider: meta.aiProvider || 'deepseek',
  ai_grading_prompt: meta.aiGradingPrompt?.trim() || '',
});

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
