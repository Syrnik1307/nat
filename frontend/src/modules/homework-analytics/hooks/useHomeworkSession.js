import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

// ============================================================================
// MOBILE-OPTIMIZED HOMEWORK SESSION HOOK
// Полностью переписан для надёжной работы на iOS/Safari/мобильных сетях
// ============================================================================

// Lazy-load service to avoid circular deps during tests/builds
let cachedHomeworkService;
const getHomeworkService = () => {
  if (!cachedHomeworkService) {
    const mod = require('../services/homeworkService');
    cachedHomeworkService = mod.default || mod;
  }
  return cachedHomeworkService;
};

// ============================================================================
// SAFE STORAGE UTILS - работают в Safari Private Mode
// ============================================================================
const safeStorage = {
  isAvailable: () => {
    try {
      if (typeof localStorage === 'undefined') return false;
      const testKey = '__storage_test__';
      localStorage.setItem(testKey, testKey);
      localStorage.removeItem(testKey);
      return true;
    } catch {
      return false;
    }
  },
  
  get: (key) => {
    try {
      if (!safeStorage.isAvailable()) return null;
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : null;
    } catch {
      return null;
    }
  },
  
  set: (key, value) => {
    try {
      if (!safeStorage.isAvailable()) return false;
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },
  
  remove: (key) => {
    try {
      if (!safeStorage.isAvailable()) return;
      localStorage.removeItem(key);
    } catch {
      // Ignore
    }
  }
};

// ============================================================================
// NETWORK UTILS - retry с exponential backoff для мобильных сетей
// ============================================================================
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const isRetryableError = (error) => {
  if (!error) return false;
  // Нет response = сетевая ошибка
  if (!error.response) return true;
  // Таймаут
  if (error.code === 'ECONNABORTED') return true;
  // 5xx ошибки сервера
  if (error.response?.status >= 500) return true;
  // 429 Too Many Requests
  if (error.response?.status === 429) return true;
  // Сообщение содержит network
  if (error.message?.toLowerCase().includes('network')) return true;
  // Fetch API errors
  if (error.name === 'TypeError' && error.message?.includes('fetch')) return true;
  return false;
};

const withRetry = async (fn, options = {}) => {
  const { maxRetries = 3, baseDelay = 1000, maxDelay = 10000 } = options;
  let lastError = null;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      // Не повторяем для 4xx (кроме 429) - это валидационные ошибки
      if (error.response?.status >= 400 && error.response?.status < 500 && error.response?.status !== 429) {
        throw error;
      }
      
      // Последняя попытка - выбрасываем ошибку
      if (attempt === maxRetries) {
        throw error;
      }
      
      // Повторяем только для retryable ошибок
      if (!isRetryableError(error)) {
        throw error;
      }
      
      // Exponential backoff с jitter
      const delay = Math.min(baseDelay * Math.pow(2, attempt - 1) + Math.random() * 500, maxDelay);
      console.warn(`[useHomeworkSession] Attempt ${attempt}/${maxRetries} failed, retrying in ${Math.round(delay)}ms...`);
      await sleep(delay);
    }
  }
  
  throw lastError;
};

// ============================================================================
// CONSTANTS
// ============================================================================
const AUTO_SAVE_INTERVAL = 30000; // 30 сек
const HOMEWORK_CACHE_TTL_MS = 60000; // 1 мин
const homeworkCache = new Map();

// ============================================================================
// HELPERS
// ============================================================================
const buildInitialAnswers = (homework) => {
  if (!homework?.questions) return {};
  return homework.questions.reduce((acc, q) => {
    acc[q.id] = null;
    
    switch (q.question_type) {
      case 'LISTENING':
        acc[q.id] = (q.config?.subQuestions || []).reduce((subAcc, sub) => {
          subAcc[sub.id] = '';
          return subAcc;
        }, {});
        break;
      case 'MATCHING':
        acc[q.id] = {};
        break;
      case 'DRAG_DROP':
        acc[q.id] = (q.config?.items || []).map(item => item.id);
        break;
      case 'FILL_BLANKS':
        acc[q.id] = (q.config?.answers || []).map(() => '');
        break;
      case 'HOTSPOT':
        acc[q.id] = [];
        break;
      case 'CODE':
        acc[q.id] = { code: q.config?.starterCode || '', testResults: [] };
        break;
      default:
        break;
    }
    
    return acc;
  }, {});
};

const convertAnswersArrayToMap = (answersArray, questions) => {
  if (!Array.isArray(answersArray) || answersArray.length === 0) return {};
  
  const typeById = {};
  questions?.forEach(q => { typeById[q.id] = q.question_type; });
  
  return answersArray.reduce((acc, answer) => {
    const qId = answer.question;
    const qType = typeById[qId];
    
    // Attachments
    if (Array.isArray(answer.attachments) && answer.attachments.length > 0) {
      acc[`${qId}_attachments`] = answer.attachments;
    }
    
    // Value по типу
    switch (qType) {
      case 'TEXT':
      case 'ESSAY':
        acc[qId] = answer.text_answer || '';
        break;
      case 'SINGLE_CHOICE':
        acc[qId] = answer.selected_choices?.[0] ?? null;
        break;
      case 'MULTI_CHOICE':
        acc[qId] = answer.selected_choices || [];
        break;
      case 'MATCHING':
      case 'LISTENING':
        try {
          acc[qId] = answer.text_answer ? JSON.parse(answer.text_answer) : {};
        } catch { acc[qId] = {}; }
        break;
      case 'DRAG_DROP':
      case 'FILL_BLANKS':
      case 'HOTSPOT':
        try {
          acc[qId] = answer.text_answer ? JSON.parse(answer.text_answer) : [];
        } catch { acc[qId] = []; }
        break;
      case 'CODE':
        try {
          acc[qId] = answer.text_answer ? JSON.parse(answer.text_answer) : { code: '', testResults: [] };
        } catch { acc[qId] = { code: '', testResults: [] }; }
        break;
      default:
        acc[qId] = answer.text_answer || (answer.selected_choices?.length ? answer.selected_choices : null);
    }
    
    return acc;
  }, {});
};

// ============================================================================
// MAIN HOOK
// ============================================================================
const useHomeworkSession = (homeworkId, injectedService) => {
  const localDraftKey = homeworkId ? `hw_draft_${homeworkId}` : null;
  const submissionHintKey = homeworkId ? `hw_sub_${homeworkId}` : null;
  const svc = injectedService || getHomeworkService();
  
  // State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [homework, setHomework] = useState(null);
  const [submission, setSubmission] = useState(null);
  const [answers, setAnswers] = useState(() => safeStorage.get(localDraftKey) || {});
  const [savingState, setSavingState] = useState({ status: 'idle', timestamp: null });
  
  // Telemetry state: { questionId: { time_spent_seconds, is_pasted, tab_switches } }
  const [telemetry, setTelemetry] = useState({});
  
  // Refs
  const dirtyRef = useRef(false);
  const mountedRef = useRef(true);
  const submittingRef = useRef(false); // Предотвращаем двойную отправку
  const questionStartTimeRef = useRef({}); // { questionId: timestamp } - когда начали отвечать
  const currentQuestionIdRef = useRef(null); // Текущий вопрос для отслеживания времени
  
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);
  
  // ============================================================================
  // LOAD HOMEWORK
  // ============================================================================
  const loadHomework = useCallback(async () => {
    if (!homeworkId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const hwIdNum = Number(homeworkId);
      
      // 1) Проверяем кеш
      const cached = homeworkCache.get(hwIdNum);
      if (cached && Date.now() - cached.ts < HOMEWORK_CACHE_TTL_MS) {
        setHomework(cached.data);
      }
      
      // 2) Загружаем homework с retry
      const rawHomework = await withRetry(() => svc.fetchHomework(homeworkId), { maxRetries: 3 });
      const homeworkData = rawHomework?.data || rawHomework;
      
      if (!mountedRef.current) return;
      
      setHomework(homeworkData);
      homeworkCache.set(hwIdNum, { ts: Date.now(), data: homeworkData });
      
      // 3) Инициализируем answers
      let initialAnswers = buildInitialAnswers(homeworkData);
      
      // Восстанавливаем черновик
      const savedDraft = safeStorage.get(localDraftKey);
      if (savedDraft) {
        initialAnswers = { ...initialAnswers, ...savedDraft };
      }
      
      // 4) Ищем существующий submission
      let submissionData = null;
      
      // Сначала по hint
      const hintedId = safeStorage.get(submissionHintKey);
      if (hintedId) {
        try {
          const resp = await svc.fetchSubmission(hintedId);
          const sub = resp?.data || resp;
          if (sub && Number(sub.homework) === hwIdNum) {
            submissionData = sub;
          }
        } catch {
          // Hint устарел - игнорируем
        }
      }
      
      // Fallback: листинг
      if (!submissionData) {
        try {
          const listResp = await svc.fetchSubmissions({ homework: homeworkId });
          const list = listResp?.data?.results || listResp?.data || [];
          submissionData = list.find(s => Number(s.homework) === hwIdNum) || null;
        } catch (e) {
          console.warn('[useHomeworkSession] fetchSubmissions failed:', e);
        }
      }
      
      // Восстанавливаем answers из submission
      if (submissionData?.answers?.length > 0) {
        const restored = convertAnswersArrayToMap(submissionData.answers, homeworkData?.questions);
        initialAnswers = { ...initialAnswers, ...restored };
      }
      
      // 5) Создаём submission если нет
      if (!submissionData) {
        console.log('[useHomeworkSession] Creating new submission for homework:', homeworkId);
        const rawSub = await withRetry(() => svc.startSubmission(homeworkId), { maxRetries: 2 });
        submissionData = rawSub?.data || rawSub;
        console.log('[useHomeworkSession] Created submission:', submissionData);
      } else {
        console.log('[useHomeworkSession] Found existing submission:', {
          id: submissionData.id,
          status: submissionData.status,
          homework: submissionData.homework
        });
      }
      
      if (!mountedRef.current) return;
      
      // Сохраняем hint
      if (submissionData?.id) {
        safeStorage.set(submissionHintKey, submissionData.id);
      }
      
      setAnswers(initialAnswers);
      setSubmission(submissionData);
      
    } catch (err) {
      console.error('[useHomeworkSession] load failed:', err);
      if (mountedRef.current) {
        setError('Не удалось загрузить задание. Проверьте интернет-соединение и обновите страницу.');
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [homeworkId, localDraftKey, submissionHintKey, svc]);
  
  useEffect(() => {
    loadHomework();
  }, [loadHomework]);
  
  // ============================================================================
  // RECORD ANSWER
  // ============================================================================
  const recordAnswer = useCallback((questionId, value) => {
    setAnswers(prev => {
      const next = { ...prev, [questionId]: value };
      // Сохраняем черновик локально (для восстановления при перезагрузке)
      safeStorage.set(localDraftKey, next);
      return next;
    });
    dirtyRef.current = true;
  }, [localDraftKey]);
  
  // ============================================================================
  // TELEMETRY FUNCTIONS
  // ============================================================================
  
  /**
   * Вызывать при переключении на вопрос (начинает отсчёт времени)
   */
  const startQuestionTimer = useCallback((questionId) => {
    // Финализируем время предыдущего вопроса
    const prevQid = currentQuestionIdRef.current;
    if (prevQid && prevQid !== questionId && questionStartTimeRef.current[prevQid]) {
      const elapsed = Math.round((Date.now() - questionStartTimeRef.current[prevQid]) / 1000);
      if (elapsed > 0) {
        setTelemetry(prev => ({
          ...prev,
          [prevQid]: {
            ...prev[prevQid],
            time_spent_seconds: (prev[prevQid]?.time_spent_seconds || 0) + elapsed,
          }
        }));
      }
      delete questionStartTimeRef.current[prevQid];
    }
    
    // Начинаем таймер для нового вопроса
    currentQuestionIdRef.current = questionId;
    questionStartTimeRef.current[questionId] = Date.now();
  }, []);
  
  /**
   * Финализировать время для текущего вопроса (при submit)
   */
  const finalizeCurrentQuestionTime = useCallback(() => {
    const qid = currentQuestionIdRef.current;
    if (qid && questionStartTimeRef.current[qid]) {
      const elapsed = Math.round((Date.now() - questionStartTimeRef.current[qid]) / 1000);
      if (elapsed > 0) {
        setTelemetry(prev => ({
          ...prev,
          [qid]: {
            ...prev[qid],
            time_spent_seconds: (prev[qid]?.time_spent_seconds || 0) + elapsed,
          }
        }));
      }
      delete questionStartTimeRef.current[qid];
      currentQuestionIdRef.current = null;
    }
  }, []);
  
  /**
   * Записать событие paste для вопроса
   */
  const recordPaste = useCallback((questionId) => {
    setTelemetry(prev => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        is_pasted: true,
      }
    }));
    dirtyRef.current = true;
  }, []);
  
  /**
   * Записать переключение вкладки для текущего вопроса
   */
  const recordTabSwitch = useCallback(() => {
    const qid = currentQuestionIdRef.current;
    if (qid) {
      setTelemetry(prev => ({
        ...prev,
        [qid]: {
          ...prev[qid],
          tab_switches: (prev[qid]?.tab_switches || 0) + 1,
        }
      }));
      dirtyRef.current = true;
    }
  }, []);
  
  // ============================================================================
  // SAVE PROGRESS (автосохранение на сервер)
  // ============================================================================
  const saveProgress = useCallback(async () => {
    // Не сохраняем если уже отправлено
    if (submission?.status && submission.status !== 'in_progress') return;
    if (!submission?.id) return;
    if (!dirtyRef.current) return;
    
    try {
      setSavingState({ status: 'saving', timestamp: Date.now() });
      
      // Объединяем answers с telemetry (формат: "123_telemetry": {...})
      const payloadWithTelemetry = { ...answers };
      Object.entries(telemetry).forEach(([qid, data]) => {
        if (data && Object.keys(data).length > 0) {
          payloadWithTelemetry[`${qid}_telemetry`] = data;
        }
      });
      
      await withRetry(() => svc.saveProgress(submission.id, payloadWithTelemetry), { maxRetries: 2, baseDelay: 2000 });
      
      // После успешной отправки очищаем отправленную телеметрию
      setTelemetry({});
      dirtyRef.current = false;
      
      if (mountedRef.current) {
        setSavingState({ status: 'saved', timestamp: Date.now() });
      }
      
      // Удаляем локальный черновик после успешного сохранения на сервер
      safeStorage.remove(localDraftKey);
      
    } catch (err) {
      console.error('[useHomeworkSession] saveProgress failed:', err);
      if (mountedRef.current) {
        setSavingState({ status: 'error', timestamp: Date.now() });
      }
      throw err; // Пробрасываем для обработки в submitHomework
    }
  }, [answers, telemetry, localDraftKey, submission?.id, submission?.status, svc]);
  
  // Автосохранение каждые 30 сек
  useEffect(() => {
    if (!submission?.id) return;
    if (submission?.status !== 'in_progress') return;
    
    const interval = setInterval(() => {
      saveProgress().catch(() => {}); // Ошибки автосохранения не критичны
    }, AUTO_SAVE_INTERVAL);
    
    return () => clearInterval(interval);
  }, [submission?.id, submission?.status, saveProgress]);
  
  // ============================================================================
  // SUBMIT HOMEWORK - главная функция отправки
  // ============================================================================
  const submitHomework = useCallback(async () => {
    if (!submission?.id) {
      throw new Error('Нет активной попытки');
    }
    
    // Защита от двойной отправки (особенно важно на мобильных)
    if (submittingRef.current) {
      console.warn('[useHomeworkSession] Submit already in progress, ignoring');
      return null;
    }
    
    submittingRef.current = true;
    
    try {
      // 0) Финализируем время текущего вопроса
      finalizeCurrentQuestionTime();
      
      // 1) Сначала сохраняем ответы с телеметрией (с retry)
      if (dirtyRef.current) {
        try {
          // Объединяем answers с телеметрией
          const payloadWithTelemetry = { ...answers };
          Object.entries(telemetry).forEach(([qid, data]) => {
            if (data && Object.keys(data).length > 0) {
              payloadWithTelemetry[`${qid}_telemetry`] = data;
            }
          });
          
          await withRetry(() => svc.saveProgress(submission.id, payloadWithTelemetry), { maxRetries: 2 });
          dirtyRef.current = false;
        } catch (saveErr) {
          console.warn('[useHomeworkSession] Pre-submit save failed, continuing anyway:', saveErr);
          // Продолжаем submit даже если save упал - ответы могли уже быть на сервере
        }
      }
      
      // 2) Отправляем submission с aggressive retry
      const resp = await withRetry(
        () => svc.submit(submission.id),
        { maxRetries: 5, baseDelay: 1500, maxDelay: 15000 }
      );
      
      const data = resp?.data || resp;
      
      if (mountedRef.current) {
        setSubmission(data);
      }
      
      // 3) Очищаем локальные данные
      safeStorage.remove(localDraftKey);
      safeStorage.remove(submissionHintKey);
      
      return resp;
      
    } finally {
      submittingRef.current = false;
    }
  }, [answers, telemetry, finalizeCurrentQuestionTime, localDraftKey, submission?.id, submissionHintKey, svc]);
  
  // ============================================================================
  // PROGRESS CALCULATION
  // ============================================================================
  const progress = useMemo(() => {
    if (!homework?.questions?.length) return 0;
    
    const total = homework.questions.length;
    let answered = 0;
    
    for (const q of homework.questions) {
      const value = answers[q.id];
      if (value == null) continue;
      
      switch (q.question_type) {
        case 'TEXT':
        case 'ESSAY':
          if (value?.trim?.()) answered++;
          break;
        case 'SINGLE_CHOICE':
          if (value) answered++;
          break;
        case 'MULTIPLE_CHOICE':
        case 'MULTI_CHOICE':
          if (Array.isArray(value) && value.length > 0) answered++;
          break;
        case 'LISTENING':
          if (Object.values(value || {}).some(v => v?.trim?.())) answered++;
          break;
        case 'MATCHING':
          if (Object.keys(value || {}).length === (q.config?.pairs?.length || 0)) answered++;
          break;
        case 'DRAG_DROP':
          if ((value || []).length > 0) answered++;
          break;
        case 'FILL_BLANKS':
          if ((value || []).every(v => v?.trim?.())) answered++;
          break;
        case 'HOTSPOT':
          if (Array.isArray(value) && value.length > 0) answered++;
          break;
        case 'CODE':
          if (value?.code?.trim() && value?.testResults?.length > 0) answered++;
          break;
        default:
          if (value) answered++;
      }
    }
    
    return Math.round((answered / total) * 100);
  }, [answers, homework]);
  
  // ============================================================================
  // RETURN
  // ============================================================================
  return {
    loading,
    error,
    homework,
    submission,
    answers,
    recordAnswer,
    saveProgress,
    submitHomework,
    savingState,
    progress,
    isLocked: submission?.status && submission.status !== 'in_progress',
    reload: loadHomework,
    // Telemetry functions
    startQuestionTimer,
    recordPaste,
    recordTabSwitch,
  };
};

export default useHomeworkSession;
