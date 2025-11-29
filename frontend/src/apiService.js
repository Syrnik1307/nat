import axios from 'axios';

// =====================
// Auth token utilities
// =====================
const ACCESS_TOKEN_KEY = 'tp_access_token';
const REFRESH_TOKEN_KEY = 'tp_refresh_token';

export const getAccessToken = () => localStorage.getItem(ACCESS_TOKEN_KEY);
export const getRefreshToken = () => localStorage.getItem(REFRESH_TOKEN_KEY);

export const setTokens = ({ access, refresh }) => {
    if (access) localStorage.setItem(ACCESS_TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
};

export const clearTokens = (force = false) => {
    // Если force=true — всегда чистим токены независимо от remember
    const rememberSession = localStorage.getItem('tp_remember_session') === 'true';
    if (force || !rememberSession) {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
};

// Use relative path for API calls
// In development: proxied to http://127.0.0.1:8000 via package.json proxy
// In production: handled by nginx proxy_pass
const FIXED_API_BASE_URL = '/api/';

const apiClient = axios.create({
    baseURL: FIXED_API_BASE_URL,
    timeout: 15000,
    headers: { 'Content-Type': 'application/json' }
});
// Debug log (remove later)
if (typeof window !== 'undefined') {
    // eslint-disable-next-line no-console
    console.log('[apiService] Using FIXED base URL:', apiClient.defaults.baseURL);
}

// Export apiClient for direct use when needed
export { apiClient };

// Attach access token on each request
apiClient.interceptors.request.use(
    (config) => {
        const token = getAccessToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Refresh logic & error handling
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};

apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        if (error.response && error.response.status === 401 && !originalRequest._retry) {
            const refresh = getRefreshToken();
            if (!refresh) {
                clearTokens();
                return Promise.reject(error);
            }
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                }).then((token) => {
                    originalRequest.headers.Authorization = 'Bearer ' + token;
                    return apiClient(originalRequest);
                }).catch(err => Promise.reject(err));
            }
            originalRequest._retry = true;
            isRefreshing = true;
            try {
                const refreshUrl = apiClient.defaults.baseURL + 'jwt/refresh/';
                const res = await axios.post(refreshUrl, { refresh });
                const newAccess = res.data.access;
                setTokens({ access: newAccess });
                processQueue(null, newAccess);
                originalRequest.headers.Authorization = 'Bearer ' + newAccess;
                return apiClient(originalRequest);
            } catch (refreshErr) {
                processQueue(refreshErr, null);
                clearTokens();
                return Promise.reject(refreshErr);
            } finally {
                isRefreshing = false;
            }
        }
        if (error.response) {
            console.error('API Error:', error.response.data);
        } else if (error.request) {
            console.error('Network Error:', error.message);
        } else {
            console.error('Error:', error.message);
        }
        return Promise.reject(error);
    }
);

// =====================
// Auth endpoints
// =====================
export const login = async (email, password) => {
    try {
        const res = await apiClient.post('jwt/token/', { email, password });

        // Дополнительная защита: если бэкенд вместо JSON вернул HTML/текст без токенов
        const data = res && res.data ? res.data : {};
        const hasAccess = typeof data.access === 'string' && data.access.length > 0;
        const hasRefresh = typeof data.refresh === 'string' && data.refresh.length > 0;

        if (!hasAccess || !hasRefresh) {
            // Логируем для диагностики, но считаем это ошибкой авторизации
            // eslint-disable-next-line no-console
            console.warn('[apiService.login] Invalid auth response, expected tokens, got:', data);
            throw new Error('Invalid auth response');
        }

        setTokens({ access: data.access, refresh: data.refresh });
        return data;
    } catch (error) {
        // Очищаем токены при любой ошибке логина безусловно
        clearTokens(true);
        // Пробрасываем ошибку дальше для обработки в UI
        throw error;
    }
};

export const logout = async () => {
    const refresh = getRefreshToken();
    try {
        if (refresh) {
            await apiClient.post('jwt/logout/', { refresh });
        }
    } catch (_) {
        // ignore logout errors
    }
    clearTokens();
};

export const verifyToken = () => {
    const access = getAccessToken();
    if (!access) return Promise.resolve(false);
    return apiClient.post('jwt/verify/', { token: access })
        .then(() => true)
        .catch(() => false);
};

// =====================
// User profile
// =====================

export const getCurrentUser = () => apiClient.get('me/');
export const updateCurrentUser = (payload) => apiClient.put('me/', payload);
export const changePassword = (oldPassword, newPassword) => 
    apiClient.post('change-password/', { 
        old_password: oldPassword, 
        new_password: newPassword 
    });

// =====================
// Helper for calendar feed
// =====================
export const getCalendarFeed = (params = {}) => {
    return apiClient.get('schedule/lessons/calendar_feed/', { params });
};

// =============== COURSES ===============

// Function to get all courses
export const getCourses = () => {
    return apiClient.get('courses/');
};

// Function to get a single course by ID
export const getCourse = (id) => {
    return apiClient.get(`courses/${id}/`);
};

// Function to create a course
export const createCourse = (courseData) => {
    return apiClient.post('courses/', courseData);
};

// Function to update a course
export const updateCourse = (id, courseData) => {
    return apiClient.put(`courses/${id}/`, courseData);
};

// Function to delete a course
export const deleteCourse = (id) => {
    return apiClient.delete(`courses/${id}/`);
};

// Function to add student to course
export const addStudentToCourse = (courseId, studentId) => {
    return apiClient.post(`courses/${courseId}/add_student/`, { student_id: studentId });
};

// Function to remove student from course
export const removeStudentFromCourse = (courseId, studentId) => {
    return apiClient.post(`courses/${courseId}/remove_student/`, { student_id: studentId });
};

// =============== LESSONS ===============

// Lessons under schedule namespace
export const getLessons = (filters = {}) => apiClient.get('schedule/lessons/', { params: filters });
export const getLesson = (id) => apiClient.get(`schedule/lessons/${id}/`);
export const createLesson = (data) => apiClient.post('schedule/lessons/', data);
export const updateLesson = (id, data) => apiClient.put(`schedule/lessons/${id}/`, data);
export const deleteLesson = (id) => apiClient.delete(`schedule/lessons/${id}/`);
export const startLesson = (id) => apiClient.post(`schedule/lessons/${id}/start/`);
export const startLessonNew = (id) => apiClient.post(`schedule/lessons/${id}/start-new/`);
export const startQuickLesson = (payload = {}) => apiClient.post('schedule/lessons/quick-start/', payload);
export const addLessonRecording = (id, url) => apiClient.post(`schedule/lessons/${id}/add_recording/`, { url });

// Groups
export const getGroups = () => apiClient.get('groups/');
export const getGroup = (id) => apiClient.get(`groups/${id}/`);
export const createGroup = (data) => apiClient.post('groups/', data);
export const updateGroup = (id, data) => apiClient.put(`groups/${id}/`, data);
export const deleteGroup = (id) => apiClient.delete(`groups/${id}/`);
export const addStudentsToGroup = (groupId, studentIds) => apiClient.post(`groups/${groupId}/add_students/`, { student_ids: studentIds });
export const removeStudentsFromGroup = (groupId, studentIds) => apiClient.post(`groups/${groupId}/remove_students/`, { student_ids: studentIds });
export const regenerateGroupInviteCode = (groupId) => apiClient.post(`groups/${groupId}/regenerate_code/`);
export const joinGroupByCode = (inviteCode) => apiClient.post('groups/join_by_code/', { invite_code: inviteCode });

// Attendance
export const getAttendance = (params = {}) => apiClient.get('attendance/', { params });
export const markLessonAttendance = (lessonId, attendances) => apiClient.post(`schedule/lessons/${lessonId}/mark_attendance/`, { attendances });

// Recurring lessons
export const getRecurringLessons = (params = {}) => apiClient.get('recurring-lessons/', { params });
export const createRecurringLesson = (data) => apiClient.post('recurring-lessons/', data);
export const updateRecurringLesson = (id, data) => apiClient.put(`recurring-lessons/${id}/`, data);
export const deleteRecurringLesson = (id) => apiClient.delete(`recurring-lessons/${id}/`);
export const generateLessonsFromRecurring = (id, payload) => apiClient.post(`recurring-lessons/${id}/generate_lessons/`, payload);

// =============== ASSIGNMENTS ===============

// Homework (renamed endpoints)
export const getHomeworkList = (params = {}) => apiClient.get('homework/', { params });
export const getHomework = (id) => apiClient.get(`homework/${id}/`);
export const createHomework = (data) => apiClient.post('homework/', data);
export const updateHomework = (id, data) => apiClient.put(`homework/${id}/`, data);
export const deleteHomework = (id) => apiClient.delete(`homework/${id}/`);

// Submissions
export const getSubmissions = (params = {}) => apiClient.get('submissions/', { params });
export const getSubmission = (id) => apiClient.get(`submissions/${id}/`);
export const createSubmission = (data) => apiClient.post('submissions/', data);
export const updateSubmission = (id, data) => apiClient.put(`submissions/${id}/`, data);
export const deleteSubmission = (id) => apiClient.delete(`submissions/${id}/`);

// Gradebook & Teacher stats
export const getGradebookForGroup = (groupId) => apiClient.get('gradebook/', { params: { group: groupId } });
export const getTeacherStatsSummary = () => apiClient.get('teacher-stats/summary/');
export const getTeacherStatsBreakdown = () => apiClient.get('teacher-stats/breakdown/');

// Control points
export const getControlPoints = (params = {}) => apiClient.get('control-points/', { params });
export const createControlPoint = (data) => apiClient.post('control-points/', data);
export const getControlPointResults = (params = {}) => apiClient.get('control-point-results/', { params });
export const createControlPointResult = (data) => apiClient.post('control-point-results/', data);

// Zoom Pool Stats (Admin only)
export const getZoomPoolStats = () => apiClient.get('zoom-pool/zoom-accounts/stats/');

// =============== SUBMISSIONS ===============

export const gradeSubmission = (submissionId, grade, feedback = '') => apiClient.post(`submissions/${submissionId}/grade/`, { grade, feedback });

export default apiClient;
