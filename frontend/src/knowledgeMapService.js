/**
 * Knowledge Map API Service
 * Карта знаний ЕГЭ/ОГЭ — API вызовы
 */
import { apiClient } from './apiService';

const BASE = '/knowledge-map';

// === Справочники ===

/** Получить типы экзаменов (ЕГЭ/ОГЭ) */
export const getExamTypes = () => apiClient.get(`${BASE}/exam-types/`);

/** Получить предметы (с фильтром по типу экзамена) */
export const getSubjects = (examType) =>
  apiClient.get(`${BASE}/subjects/`, { params: examType ? { exam_type: examType } : {} });

/** Получить предмет с деревом секций и тем */
export const getSubjectDetail = (id) => apiClient.get(`${BASE}/subjects/${id}/`);

/** Получить темы (с фильтрами) */
export const getTopics = (params = {}) =>
  apiClient.get(`${BASE}/topics/`, { params });

// === Назначения экзаменов ===

/** Получить назначения экзаменов ученикам */
export const getExamAssignments = () => apiClient.get(`${BASE}/assignments/`);

/** Назначить экзамен ученику */
export const createExamAssignment = (data) =>
  apiClient.post(`${BASE}/assignments/`, data);

/** Массовое назначение: {student_ids: [...], subject_id: N} */
export const bulkAssignExam = (data) =>
  apiClient.post(`${BASE}/assignments/bulk_assign/`, data);

/** Удалить назначение */
export const deleteExamAssignment = (id) =>
  apiClient.delete(`${BASE}/assignments/${id}/`);

// === Прогресс / Карта знаний ===

/** Прогресс ученика по предмету (дерево секций → тем → mastery) */
export const getStudentProgress = (studentId, subjectId) =>
  apiClient.get(`${BASE}/progress/student/`, {
    params: { student_id: studentId, subject_id: subjectId },
  });

/** Агрегированный прогресс группы по предмету */
export const getGroupProgress = (groupId, subjectId) =>
  apiClient.get(`${BASE}/progress/group/`, {
    params: { group_id: groupId, subject_id: subjectId },
  });

/** Краткая сводка по ученику: все предметы и общий прогресс */
export const getStudentSummary = (studentId) =>
  apiClient.get(`${BASE}/progress/summary/`, {
    params: studentId ? { student_id: studentId } : {},
  });
