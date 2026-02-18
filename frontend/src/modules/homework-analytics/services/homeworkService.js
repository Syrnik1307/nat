import {
  createHomework,
  updateHomework,
  getHomework,
  createSubmission,
  apiClient,
} from '../../../apiService';

// =====================
// Attachment API helpers
// =====================

/**
 * Получить список вложений вопроса.
 * GET /api/homework/questions/{questionId}/attachments/
 */
export const getQuestionAttachments = async (questionId) => {
  const response = await apiClient.get(`homework/questions/${questionId}/attachments/`);
  return response.data;
};

/**
 * Загрузить файл к вопросу.
 * POST /api/homework/questions/{questionId}/attachments/
 * @param {number} questionId
 * @param {File} file
 * @param {function} onProgress — callback(percent)
 */
export const uploadQuestionAttachment = async (questionId, file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post(
    `homework/questions/${questionId}/attachments/`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000, // 2 min for large files
      onUploadProgress: (event) => {
        if (onProgress && event.total) {
          onProgress(Math.round((event.loaded * 100) / event.total));
        }
      },
    }
  );
  return response.data;
};

/**
 * Удалить вложение.
 * DELETE /api/homework/attachments/{attachmentId}/
 */
export const deleteQuestionAttachment = async (attachmentId) => {
  const response = await apiClient.delete(`homework/attachments/${attachmentId}/`);
  return response.data;
};

/**
 * URL для скачивания вложения через бэкенд-прокси.
 */
export const getAttachmentDownloadUrl = (attachmentId) =>
  `/api/homework/attachments/${attachmentId}/download/`;

const mapQuestionToPayload = (question, order) => {
  const basePayload = {
    question_type: question.question_type,
    question_text: question.question_text?.trim() || '',
    points: Number.isFinite(question.points) ? question.points : 0,
    order,
    config: question.config ?? {},
    correct_answer: question.correct_answer ?? null,
  };

  if (question.question_type === 'TEXT') {
    basePayload.correct_answer = question.config?.correctAnswer || null;
  }

  if (question.question_type === 'SINGLE_CHOICE') {
    basePayload.correct_answer = question.config?.correctOptionId || null;
  }

  if (question.question_type === 'MULTIPLE_CHOICE') {
    basePayload.correct_answer = question.config?.correctOptionIds || [];
  }

  if (question.question_type === 'FILL_BLANKS') {
    basePayload.correct_answer = question.config?.answers || [];
  }

  if (question.question_type === 'MATCHING') {
    const pairs = question.config?.pairs || [];
    basePayload.correct_answer = pairs.map((pair) => ({ left: pair.left, right: pair.right }));
  }

  if (question.question_type === 'DRAG_DROP') {
    basePayload.correct_answer = question.config?.correctOrder || [];
  }

  if (question.question_type === 'LISTENING') {
    basePayload.correct_answer = (question.config?.subQuestions || []).map((item) => ({
      id: item.id,
      answer: item.answer,
    }));
  }

  if (question.question_type === 'HOTSPOT') {
    basePayload.correct_answer = question.config?.hotspots || [];
  }

  return basePayload;
};

export const buildHomeworkPayload = (meta, questions) => {
  const deadlineIso = meta.deadline ? new Date(meta.deadline).toISOString() : null;

  const groupId = meta.groupId ? Number(meta.groupId) : null;

  const payload = {
    title: meta.title?.trim() || '',
    description: meta.description?.trim() || '',
    group: Number.isFinite(groupId) ? groupId : null,
    deadline: deadlineIso,
    max_score: Number(meta.maxScore) || 0,
    gamification_enabled: Boolean(meta.gamificationEnabled),
    questions: questions.map((question, index) => mapQuestionToPayload(question, index)),
  };

  if (!payload.deadline) {
    delete payload.deadline;
  }

  return payload;
};

export const homeworkService = {
  buildHomeworkPayload,
  async create(meta, questions) {
    const payload = buildHomeworkPayload(meta, questions);
    return createHomework(payload);
  },
  async update(id, meta, questions) {
    const payload = buildHomeworkPayload(meta, questions);
    return updateHomework(id, payload);
  },
  async fetchHomework(homeworkId) {
    const response = await getHomework(homeworkId);
    return response.data;
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
