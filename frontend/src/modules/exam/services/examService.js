/**
 * examService.js — API-обёртка для модуля симуляции экзаменов.
 * 
 * Все запросы идут через apiClient из apiService.js.
 */

import { apiClient } from '../../../apiService';

const BASE = 'exam';

// ============================================================
// Blueprints (шаблоны экзаменов)
// ============================================================

export const getBlueprints = (params = {}) =>
  apiClient.get(`${BASE}/blueprints/`, { params }).then(r => r.data);

export const getBlueprint = (id) =>
  apiClient.get(`${BASE}/blueprints/${id}/`).then(r => r.data);

export const createBlueprint = (data) =>
  apiClient.post(`${BASE}/blueprints/`, data).then(r => r.data);

export const updateBlueprint = (id, data) =>
  apiClient.put(`${BASE}/blueprints/${id}/`, data).then(r => r.data);

export const patchBlueprint = (id, data) =>
  apiClient.patch(`${BASE}/blueprints/${id}/`, data).then(r => r.data);

export const deleteBlueprint = (id) =>
  apiClient.delete(`${BASE}/blueprints/${id}/`);

export const updateBlueprintSlots = (id, slots) =>
  apiClient.post(`${BASE}/blueprints/${id}/slots/`, { slots }).then(r => r.data);

export const duplicateBlueprint = (id) =>
  apiClient.post(`${BASE}/blueprints/${id}/duplicate/`).then(r => r.data);

// ============================================================
// Tasks (банк заданий)
// ============================================================

export const getTasks = (params = {}) =>
  apiClient.get(`${BASE}/tasks/`, { params }).then(r => r.data);

export const getTask = (id) =>
  apiClient.get(`${BASE}/tasks/${id}/`).then(r => r.data);

export const createTask = (data) =>
  apiClient.post(`${BASE}/tasks/`, data).then(r => r.data);

export const updateTask = (id, data) =>
  apiClient.patch(`${BASE}/tasks/${id}/`, data).then(r => r.data);

export const deleteTask = (id) =>
  apiClient.delete(`${BASE}/tasks/${id}/`);

export const bulkImportTasks = (blueprintId, tasks) =>
  apiClient.post(`${BASE}/tasks/bulk-import/`, {
    blueprint_id: blueprintId,
    tasks,
  }).then(r => r.data);

export const getTaskStats = (blueprintId) =>
  apiClient.get(`${BASE}/tasks/stats/`, {
    params: { blueprint: blueprintId },
  }).then(r => r.data);

// ============================================================
// Variants (варианты экзамена)
// ============================================================

export const getVariants = (params = {}) =>
  apiClient.get(`${BASE}/variants/`, { params }).then(r => r.data);

export const getVariant = (id) =>
  apiClient.get(`${BASE}/variants/${id}/`).then(r => r.data);

export const generateVariants = (data) =>
  apiClient.post(`${BASE}/variants/generate/`, data).then(r => r.data);

export const createManualVariant = (data) =>
  apiClient.post(`${BASE}/variants/manual/`, data).then(r => r.data);

export const assignVariant = (id, data) =>
  apiClient.post(`${BASE}/variants/${id}/assign/`, data).then(r => r.data);

export const deleteVariant = (id) =>
  apiClient.delete(`${BASE}/variants/${id}/`);

// ============================================================
// Attempts (попытки экзаменов)
// ============================================================

export const getAttempts = (params = {}) =>
  apiClient.get(`${BASE}/attempts/`, { params }).then(r => r.data);

export const getAttempt = (id) =>
  apiClient.get(`${BASE}/attempts/${id}/`).then(r => r.data);

export const startExam = (attemptId) =>
  apiClient.post(`${BASE}/attempts/${attemptId}/start/`).then(r => r.data);

export const getTimer = (attemptId) =>
  apiClient.get(`${BASE}/attempts/${attemptId}/timer/`).then(r => r.data);

export const forceSubmit = (attemptId) =>
  apiClient.post(`${BASE}/attempts/${attemptId}/force-submit/`).then(r => r.data);

export const getResult = (attemptId) =>
  apiClient.get(`${BASE}/attempts/${attemptId}/result/`).then(r => r.data);

export const getMyAttempts = () =>
  apiClient.get(`${BASE}/attempts/my/`).then(r => r.data);

export const getAnalytics = (params = {}) =>
  apiClient.get(`${BASE}/attempts/analytics/`, { params }).then(r => r.data);

// ============================================================
// Answer type helpers
// ============================================================

/**
 * Маппинг answer_type из ExamTaskSlot → question_type в homework.
 */
export const ANSWER_TYPE_TO_QUESTION_TYPE = {
  short_number: 'TEXT',
  short_text: 'TEXT',
  digit_sequence: 'TEXT',
  letter_sequence: 'TEXT',
  decimal_number: 'TEXT',
  number_range: 'TEXT',
  multiple_numbers: 'TEXT',
  matching: 'MATCHING',
  ordered_sequence: 'DRAG_DROP',
  single_choice: 'SINGLE_CHOICE',
  multi_choice: 'MULTI_CHOICE',
  extended_text: 'TEXT',
  essay: 'TEXT',
  math_solution: 'TEXT',
  code_solution: 'CODE',
  code_file: 'FILE_UPLOAD',
};

/**
 * Человекочитаемые названия типов ответов.
 */
export const ANSWER_TYPE_LABELS = {
  short_number: 'Краткий числовой ответ',
  short_text: 'Краткий текстовый ответ',
  digit_sequence: 'Последовательность цифр',
  letter_sequence: 'Последовательность букв',
  decimal_number: 'Десятичная дробь',
  number_range: 'Диапазон чисел',
  multiple_numbers: 'Несколько чисел',
  matching: 'Соответствие',
  ordered_sequence: 'Упорядоченная последовательность',
  single_choice: 'Один вариант',
  multi_choice: 'Несколько вариантов',
  extended_text: 'Развёрнутый ответ',
  essay: 'Сочинение / эссе',
  math_solution: 'Математическое решение',
  code_solution: 'Программный код',
  code_file: 'Файл с программой',
};

/**
 * Форматировать время (секунды → "Хч Хм Хс").
 */
export const formatTime = (seconds) => {
  if (seconds == null || seconds < 0) return '--:--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}ч ${m.toString().padStart(2, '0')}м`;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
};
