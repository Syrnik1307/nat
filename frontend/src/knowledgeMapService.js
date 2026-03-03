/**
 * Knowledge Map API service.
 * Feature-flagged: only active when REACT_APP_KNOWLEDGE_MAP_ENABLED=true
 * 
 * All functions return null/empty if feature is disabled.
 */
import { apiClient } from './apiService';

const BASE = 'knowledge-map';

export const isKnowledgeMapEnabled = () => {
    return process.env.REACT_APP_KNOWLEDGE_MAP_ENABLED === 'true' ||
           process.env.REACT_APP_KNOWLEDGE_MAP_ENABLED === '1';
};

// Guard: returns resolved promise with null data if disabled
const guard = (fn) => (...args) => {
    if (!isKnowledgeMapEnabled()) return Promise.resolve({ data: null });
    return fn(...args);
};

export const getExamTypes = guard(() =>
    apiClient.get(`${BASE}/exam-types/`)
);

export const getSubjects = guard((examTypeId) =>
    apiClient.get(`${BASE}/subjects/`, { params: { exam_type: examTypeId } })
);

export const getSubjectDetail = guard((subjectId) =>
    apiClient.get(`${BASE}/subjects/${subjectId}/`)
);

export const getTopics = guard((params) =>
    apiClient.get(`${BASE}/topics/`, { params })
);

export const getExamAssignments = guard(() =>
    apiClient.get(`${BASE}/assignments/`)
);

export const createExamAssignment = guard((data) =>
    apiClient.post(`${BASE}/assignments/`, data)
);

export const bulkAssignExam = guard((data) =>
    apiClient.post(`${BASE}/assignments/bulk_assign/`, data)
);

export const deleteExamAssignment = guard((id) =>
    apiClient.delete(`${BASE}/assignments/${id}/`)
);

export const getStudentProgress = guard((studentId, subjectId) =>
    apiClient.get(`${BASE}/progress/student/`, {
        params: { student: studentId, subject: subjectId }
    })
);

export const getMyProgress = guard((subjectId) =>
    apiClient.get(`${BASE}/progress/my/`, { params: { subject: subjectId } })
);

export const getStudentSummary = guard((studentId) =>
    apiClient.get(`${BASE}/progress/summary/`, {
        params: studentId ? { student: studentId } : {}
    })
);
