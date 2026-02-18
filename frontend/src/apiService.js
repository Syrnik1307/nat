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

export const clearTokens = () => {
    // Токены хранятся в localStorage и автоматически истекают через 12ч (JWT exp)
    // При явном logout или ошибке refresh — очищаем
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
};

// Определяем корректный baseURL в зависимости от среды
// - Prod (served by nginx on :80): используем относительный '/api/'
// - Dev (CRA on :3000 на сервере без proxy): используем абсолютный URL к :80
let FIXED_API_BASE_URL = '/api/';
let FIXED_ROOT_ORIGIN = '';
if (typeof window !== 'undefined') {
    const { origin } = window.location;
    const url = new URL(origin);
  const isLocalDevHost = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
  if (url.port === '3000' && !isLocalDevHost) {
    // Если фронт запущен на :3000 на сервере без CRA-proxy,
    // отправляем запросы на :80 (nginx)
    const targetOrigin = `${url.protocol}//${url.hostname}`; // без порта → :80
    FIXED_ROOT_ORIGIN = targetOrigin;
    FIXED_API_BASE_URL = `${targetOrigin}/api/`;
  } else {
    // Локальный dev: оставляем относительный /api/ (setupProxy.js)
    FIXED_ROOT_ORIGIN = origin;
  }
}

const SCHEDULE_API_BASE_URL = FIXED_ROOT_ORIGIN
    ? `${FIXED_ROOT_ORIGIN}/schedule/api/`
    : '/schedule/api/';

const apiClient = axios.create({
  baseURL: FIXED_API_BASE_URL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' }
});
// Debug log (remove later)
if (typeof window !== 'undefined' && process.env.NODE_ENV !== 'production') {
  // eslint-disable-next-line no-console
  console.log('[apiService] Using FIXED base URL:', apiClient.defaults.baseURL);
}

// Export apiClient for direct use when needed
export { apiClient };

export const withScheduleApiBase = (config = {}) => ({
    baseURL: SCHEDULE_API_BASE_URL,
    ...config
});

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
                if (typeof window !== 'undefined') {
                    window.location.href = '/auth-new';
                }
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
export const login = async (email, password, rememberMe = false) => {
    try {
        const res = await apiClient.post('jwt/token/', { email, password, remember_me: rememberMe });

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
        clearTokens();
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
    
    // Быстрая проверка: декодируем JWT и проверяем exp локально
    try {
        const part = access.split('.')[1];
        if (part) {
            const base64 = part.replace(/-/g, '+').replace(/_/g, '/');
            const padded = base64 + '='.repeat((4 - base64.length % 4) % 4);
            const payload = JSON.parse(atob(padded));
            // Если токен истёк менее чем 5 секунд назад - всё ещё валиден на сервере
            if (payload.exp && (payload.exp * 1000) > (Date.now() - 5000)) {
                return Promise.resolve(true);
            }
        }
    } catch (_) {
        // Если не удалось декодировать - проверяем на сервере
    }
    
    return apiClient.post('jwt/verify/', { token: access })
        .then(() => true)
        .catch(() => false);
};

  // =====================
  // Token helper for non-Axios consumers (e.g., <video> src)
  // =====================
  const isJwtExpiringSoon = (token, minTtlSeconds = 60) => {
    if (!token) return true;
    try {
      const part = token.split('.')[1];
      if (!part) return true;
      const base64 = part.replace(/-/g, '+').replace(/_/g, '/');
      const padded = base64 + '='.repeat((4 - base64.length % 4) % 4);
      const payload = JSON.parse(atob(padded));
      if (!payload.exp) return true;
      const nowSec = Date.now() / 1000;
      return payload.exp <= (nowSec + minTtlSeconds);
    } catch (_) {
      return true;
    }
  };

  export const ensureFreshAccessToken = async (minTtlSeconds = 60) => {
    const access = getAccessToken();
    if (access && !isJwtExpiringSoon(access, minTtlSeconds)) {
      return access;
    }

    const refresh = getRefreshToken();
    if (!refresh) {
      return null;
    }

    try {
      const refreshUrl = apiClient.defaults.baseURL + 'jwt/refresh/';
      const res = await axios.post(refreshUrl, { refresh });
      const newAccess = res?.data?.access;
      if (typeof newAccess === 'string' && newAccess.length > 0) {
        setTokens({ access: newAccess });
        return newAccess;
      }
    } catch (_) {
      // ignore; caller will handle null
    }
    return null;
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
export const changeEmail = (password, newEmail) => 
    apiClient.post('change-email/', { 
        password: password, 
        new_email: newEmail 
    });
export const getTelegramStatus = () => apiClient.get('telegram/status/');
export const generateTelegramCode = () => apiClient.post('accounts/generate-telegram-code/');
export const unlinkTelegramAccount = () => apiClient.post('telegram/unlink/');

// =====================
// Notification settings
// =====================
export const getNotificationSettings = () => apiClient.get('notifications/settings/');
export const patchNotificationSettings = (payload) => apiClient.patch('notifications/settings/', payload);

// Notification mutes (заглушки по группам/ученикам)
export const getNotificationMutes = () => apiClient.get('notifications/mutes/');
export const createNotificationMute = (payload) => apiClient.post('notifications/mutes/', payload);
export const deleteNotificationMute = (id) => apiClient.delete(`notifications/mutes/${id}/`);

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
// === Course Modules ===
export const getCourseModules = (courseId) => {
    return apiClient.get(`courses/${courseId}/modules/`);
};

export const createCourseModule = (courseId, data) => {
    return apiClient.post(`courses/${courseId}/modules/`, data);
};

export const updateCourseModule = (courseId, moduleId, data) => {
    return apiClient.put(`courses/${courseId}/modules/${moduleId}/`, data);
};

export const deleteCourseModule = (courseId, moduleId) => {
    return apiClient.delete(`courses/${courseId}/modules/${moduleId}/`);
};

export const reorderCourseModules = (courseId, orderedIds) => {
    return apiClient.post(`courses/${courseId}/modules/reorder/`, { ordered_ids: orderedIds });
};

// === Course Lessons ===
export const getCourseLessons = (courseId) => {
    return apiClient.get(`courses/${courseId}/lessons/`);
};

export const createCourseLesson = (courseId, data) => {
    return apiClient.post(`courses/${courseId}/lessons/`, data);
};

export const updateCourseLesson = (courseId, lessonId, data) => {
    return apiClient.put(`courses/${courseId}/lessons/${lessonId}/`, data);
};

export const deleteCourseLesson = (courseId, lessonId) => {
    return apiClient.delete(`courses/${courseId}/lessons/${lessonId}/`);
};

export const reorderCourseLessons = (courseId, orderedIds) => {
    return apiClient.post(`courses/${courseId}/lessons/reorder/`, { ordered_ids: orderedIds });
};

// === Course Media ===
export const uploadCourseCover = (courseId, file) => {
    const formData = new FormData();
    formData.append('cover', file);
    return apiClient.post(`courses/${courseId}/upload-cover/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
};

export const uploadCourseLessonMaterial = (courseId, lessonId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`courses/${courseId}/lessons/${lessonId}/materials/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
};

export const deleteCourseLessonMaterial = (courseId, lessonId, materialId) => {
    return apiClient.delete(`courses/${courseId}/lessons/${lessonId}/materials/${materialId}/`);
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
export const updateLesson = (id, data) => apiClient.patch(`schedule/lessons/${id}/`, data);
export const deleteLesson = (id) => apiClient.delete(`schedule/lessons/${id}/`);
export const startLesson = (id) => apiClient.post(`schedule/lessons/${id}/start/`);
export const startLessonNew = (id, data = {}) => apiClient.post(
  `schedule/lessons/${id}/start-new/`,
  data,
  { timeout: 120000 }
);
export const endLesson = (id) => apiClient.post(`schedule/lessons/${id}/end/`);
export const joinLesson = (id) => apiClient.post(`schedule/lessons/${id}/join/`);
export const logLessonJoin = (id, platform) => apiClient.post(`schedule/lessons/${id}/log_join/`, { platform });
export const startQuickLesson = (payload = {}) => apiClient.post(
  'schedule/lessons/quick-start/',
  payload,
  { timeout: 120000 }
);
export const addLessonRecording = (id, url) => apiClient.post(`schedule/lessons/${id}/add_recording/`, { url });
export const getLessonAnalytics = (id) => apiClient.get(`schedule/lessons/${id}/analytics/`);

// Groups
export const getGroups = (params = {}) => apiClient.get('groups/', { params });
export const getGroup = (id) => apiClient.get(`groups/${id}/`);
export const createGroup = (data) => apiClient.post('groups/', data);
export const updateGroup = (id, data) => apiClient.put(`groups/${id}/`, data);
export const deleteGroup = (id) => apiClient.delete(`groups/${id}/`);
export const addStudentsToGroup = (groupId, studentIds) => apiClient.post(`groups/${groupId}/add_students/`, { student_ids: studentIds });
export const removeStudentsFromGroup = (groupId, studentIds) => apiClient.post(`groups/${groupId}/remove_students/`, { student_ids: studentIds });
export const regenerateGroupInviteCode = (groupId) => apiClient.post(`groups/${groupId}/regenerate_code/`);
export const getGroupByInviteCode = (inviteCode) => apiClient.get(`groups/preview_by_code/?code=${inviteCode}`);
export const joinGroupByCode = (inviteCode) => apiClient.post('groups/join_by_code/', { invite_code: inviteCode });
export const transferStudent = (fromGroupId, studentId, toGroupId) => 
  apiClient.post(`groups/${fromGroupId}/transfer_student/`, { student_id: studentId, to_group_id: toGroupId });

// Individual invite codes
export const getIndividualInviteCodes = (params = {}) => apiClient.get('individual-invite-codes/', { params });
export const createIndividualInviteCode = (data) => apiClient.post('individual-invite-codes/', data);
export const updateIndividualInviteCode = (id, data) => apiClient.put(`individual-invite-codes/${id}/`, data);
export const deleteIndividualInviteCode = (id) => apiClient.delete(`individual-invite-codes/${id}/`);
export const regenerateIndividualInviteCode = (id) => apiClient.post('individual-invite-codes/regenerate/', { id });
export const getIndividualInviteCodeByCode = (inviteCode) => apiClient.get(`individual-invite-codes/preview_by_code/?code=${inviteCode}`);
export const joinIndividualByCode = (inviteCode) => apiClient.post('individual-invite-codes/join_by_code/', { invite_code: inviteCode });

// Attendance
export const getAttendance = (params = {}) => apiClient.get('attendance/', { params });
export const markLessonAttendance = (lessonId, attendances) => apiClient.post(`schedule/lessons/${lessonId}/mark_attendance/`, { attendances });

// Recurring lessons
export const getRecurringLessons = (params = {}) => apiClient.get('recurring-lessons/', { params });
export const createRecurringLesson = (data) => apiClient.post('recurring-lessons/', data);
export const updateRecurringLesson = (id, data) => apiClient.put(`recurring-lessons/${id}/`, data);
export const deleteRecurringLesson = (id) => apiClient.delete(`recurring-lessons/${id}/`);
export const createRecurringLessonTelegramBindCode = (id) => apiClient.post(`recurring-lessons/${id}/telegram_bind_code/`, {});
export const generateLessonsFromRecurring = (id, payload) => apiClient.post(`recurring-lessons/${id}/generate_lessons/`, payload);

// =============== ASSIGNMENTS ===============

// Homework (renamed endpoints)
export const getHomeworkList = (params = {}) => apiClient.get('homework/', { params });
export const getHomework = (id) => apiClient.get(`homework/${id}/`);
export const createHomework = (data) => apiClient.post('homework/', data);
export const updateHomework = (id, data) => apiClient.put(`homework/${id}/`, data);
export const deleteHomework = (id) => apiClient.delete(`homework/${id}/`);

// Homework Assignment (duplicate/move, get assignment details)
/**
 * Дублировать или перенести ДЗ в другие группы/ученикам
 * @param {number} homeworkId - ID домашнего задания
 * @param {Object} data - Данные для назначения:
 *   - mode: 'duplicate' | 'move'
 *   - group_assignments: [{group_id, student_ids[], deadline?}]
 *   - individual_student_ids: number[]
 *   - deadline: string (ISO)
 *   - publish: boolean
 */
export const duplicateAndAssignHomework = (homeworkId, data) => 
  apiClient.post(`homework/${homeworkId}/duplicate-and-assign/`, data);

/**
 * Получить детали назначений ДЗ (группы + ученики)
 */
export const getHomeworkAssignmentDetails = (homeworkId) => 
  apiClient.get(`homework/${homeworkId}/assignment-details/`);

/**
 * Получить учеников группы
 */
export const getGroupStudents = (groupId) => 
  apiClient.get(`schedule/groups/${groupId}/students/`);

// Импорт компрессора для изображений (lazy)
let _compressImage = null;
const getCompressor = async () => {
  if (!_compressImage) {
    const mod = await import('./utils/imageCompressor');
    _compressImage = mod.compressImage || mod.default;
  }
  return _compressImage;
};

/**
 * Предзагрузка компрессора изображений
 * Вызывайте при монтировании компонентов с загрузкой изображений
 * чтобы избежать задержки при первой загрузке
 */
export const preloadImageCompressor = () => {
  getCompressor().catch(() => {});
};

/**
 * Загрузка файла для домашки.
 * Быстрое клиентское сжатие + мгновенная отправка на сервер.
 * Сервер сохраняет локально и возвращает URL сразу,
 * а в фоне мигрирует на Google Drive.
 * 
 * @param {File} file - Файл для загрузки
 * @param {string} fileType - Тип файла ('image' или 'audio')
 * @param {Function} onProgress - Callback для прогресса загрузки (0-100)
 */
export const uploadHomeworkFile = async (file, fileType, onProgress) => {
  let fileToUpload = file;
  
  // Быстрое сжатие только для больших изображений (>2MB)
  if (fileType === 'image' && file.type.startsWith('image/') && file.size > 2 * 1024 * 1024) {
    try {
      const compress = await getCompressor();
      fileToUpload = await compress(file);
    } catch (e) {
      console.warn('[uploadHomeworkFile] Compression failed, using original:', e);
    }
  }
  
  const formData = new FormData();
  formData.append('file', fileToUpload);
  formData.append('file_type', fileType);
  
  // Переопределяем Content-Type как undefined чтобы axios установил multipart/form-data с boundary
  // Увеличиваем timeout для больших файлов
  return apiClient.post('homework/upload-file/', formData, {
    headers: { 'Content-Type': undefined },
    timeout: 120000, // 2 минуты для загрузки
    onUploadProgress: onProgress ? (progressEvent) => {
      const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      onProgress(percent);
    } : undefined,
  });
};

/**
 * Загрузка документа напрямую на Google Drive
 * Используется для PDF, Word, Excel и других документов
 * 
 * @param {File} file - Файл для загрузки
 * @param {Function} onProgress - Callback для прогресса загрузки (0-100)
 */
export const uploadHomeworkDocument = async (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  
  // Документы загружаются напрямую на GDrive (дольше, но не нагружает сервер)
  return apiClient.post('homework/upload-document-direct/', formData, {
    headers: { 'Content-Type': undefined },
    timeout: 300000, // 5 минут для больших документов
    onUploadProgress: onProgress ? (progressEvent) => {
      const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      onProgress(percent);
    } : undefined,
  });
};

/**
 * Загрузка файла студентом в качестве ответа на вопрос
 * (отдельный эндпоинт от учительского upload-file)
 * 
 * @param {File} file - Файл для загрузки
 * @param {string|number} homeworkId - ID домашки (для определения учителя/папки на GDrive)
 * @param {Function} onProgress - Callback для прогресса загрузки (0-100)
 */
export const uploadStudentAnswerFile = async (file, homeworkId, onProgress) => {
  let fileToUpload = file;
  
  // Быстрое сжатие только для больших изображений (>2MB)
  if (file.type.startsWith('image/') && file.size > 2 * 1024 * 1024) {
    try {
      const compress = await getCompressor();
      fileToUpload = await compress(file);
    } catch (e) {
      console.warn('[uploadStudentAnswerFile] Compression failed, using original:', e);
    }
  }
  
  const formData = new FormData();
  formData.append('file', fileToUpload);
  if (homeworkId) {
    formData.append('homework_id', homeworkId);
  }
  
  return apiClient.post('homework/upload-student-answer/', formData, {
    headers: { 'Content-Type': undefined },
    timeout: 120000, // 2 минуты для загрузки
    onUploadProgress: onProgress ? (progressEvent) => {
      const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      onProgress(percent);
    } : undefined,
  });
};

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
export const getTeacherSlaDetails = () => apiClient.get('teacher-stats/sla_details/');
export const getTeacherStudentRisks = () => apiClient.get('teacher-stats/student_risks/');
export const getTeacherEarlyWarnings = (params = {}) => apiClient.get('teacher-stats/early_warnings/', { params });
export const getTeacherMonthlyDynamics = (params = {}) => apiClient.get('teacher-stats/monthly_dynamics/', { params });
export const getTeacherWeeklyDynamics = (params = {}) => apiClient.get('teacher-stats/weekly_dynamics/', { params });

// Student stats
export const getStudentStatsSummary = () => apiClient.get('student-stats/summary/');

// Control points
export const getControlPoints = (params = {}) => apiClient.get('control-points/', { params });
export const createControlPoint = (data) => apiClient.post('control-points/', data);
export const getControlPointResults = (params = {}) => apiClient.get('control-point-results/', { params });
export const createControlPointResult = (data) => apiClient.post('control-point-results/', data);

// Zoom Pool Stats (Admin only)
export const getZoomPoolStats = () => apiClient.get('zoom-pool/zoom-accounts/stats/');

// =============== SUBMISSIONS ===============

export const gradeSubmission = (submissionId, grade, feedback = '') => apiClient.post(`submissions/${submissionId}/grade/`, { grade, feedback });

// =============== BILLING / SUBSCRIPTIONS ===============
export const getSubscription = () => apiClient.get('subscription/');
export const cancelSubscription = () => apiClient.post('subscription/cancel/');
export const createSubscriptionPayment = (plan) => apiClient.post('subscription/create-payment/', { plan });
export const addStoragePayment = (gb) => apiClient.post('subscription/add-storage/', { gb });

// =============== ATTENDANCE & RATING ===============

// Attendance records
export const getAttendanceRecords = (params = {}) => apiClient.get('attendance-records/', { params });
export const getAttendanceRecord = (id) => apiClient.get(`attendance-records/${id}/`);
export const autoRecordAttendance = (lessonId, studentId, isJoined = true) => 
  apiClient.post('attendance-records/auto_record/', { lesson_id: lessonId, student_id: studentId, is_joined: isJoined });
export const manualRecordAttendance = (lessonId, studentId, status) =>
  apiClient.post('attendance-records/manual_record/', { lesson_id: lessonId, student_id: studentId, status });
export const recordWatchedRecording = (lessonId, studentId) =>
  apiClient.post('attendance-records/record_watched_recording/', { lesson_id: lessonId, student_id: studentId });

// Group attendance log
export const getGroupAttendanceLog = (groupId) =>
  apiClient.get(`groups/${groupId}/attendance-log/`);
export const updateGroupAttendanceLog = (groupId, lessonId, studentId, status) =>
  apiClient.post(`groups/${groupId}/attendance-log/update/`, { lesson_id: lessonId, student_id: studentId, status });

// User ratings
export const getRatings = (params = {}) => apiClient.get('ratings/', { params });
export const getRating = (id) => apiClient.get(`ratings/${id}/`);

// Group rating
export const getGroupRating = (groupId) =>
  apiClient.get(`groups/${groupId}/rating/`);

// Group report
export const getGroupReport = (groupId) =>
  apiClient.get(`groups/${groupId}/report/`);

// Student card
export const getStudentCard = (studentId, groupId = null) => {
  const params = groupId ? { group_id: groupId } : {};
  return apiClient.get(`students/${studentId}/card/`, { params });
};

// Individual students
export const getIndividualStudents = () =>
  apiClient.get('individual-students/');
export const getIndividualStudent = (id) =>
  apiClient.get(`individual-students/${id}/`);
export const createIndividualStudent = (data) =>
  apiClient.post('individual-students/', data);
export const updateIndividualStudent = (id, data) =>
  apiClient.put(`individual-students/${id}/`, data);
export const updateIndividualStudentNotes = (id, notes) =>
  apiClient.patch(`individual-students/${id}/update_notes/`, { teacher_notes: notes });

// =============== CALENDAR EXPORT (iCal) ===============

// Get calendar subscription links for Google, Apple, Yandex
// Note: schedule endpoints are under /schedule/api/, so we use withScheduleApiBase
export const getCalendarSubscribeLinks = () => apiClient.get('calendar/subscribe-links/', withScheduleApiBase());

// Download .ics file for all lessons
export const downloadCalendarIcs = (params = {}) => {
  return apiClient.get('calendar/export/ics/', { 
    ...withScheduleApiBase(),
    params,
    responseType: 'blob' 
  });
};

// Download .ics file for a single lesson
export const downloadLessonIcs = (lessonId) => {
  return apiClient.get(`calendar/lesson/${lessonId}/ics/`, { 
    ...withScheduleApiBase(),
    responseType: 'blob' 
  });
};

// Regenerate calendar token (invalidates old subscription links)
export const regenerateCalendarToken = () => apiClient.post('calendar/regenerate-token/', {}, withScheduleApiBase());

export default apiClient;

