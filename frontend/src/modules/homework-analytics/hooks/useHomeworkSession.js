import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

// Lazy-load service to avoid circular deps during tests/builds
let cachedHomeworkService;
const getHomeworkService = () => {
  if (!cachedHomeworkService) {
    const mod = require('../services/homeworkService');
    cachedHomeworkService = mod.default || mod;
  }
  return cachedHomeworkService;
};

const AUTO_SAVE_INTERVAL = 30000;

const HOMEWORK_CACHE_TTL_MS = 60000;
const homeworkCache = new Map(); // homeworkId -> { ts, data }

const buildInitialAnswers = (homework) => {
  if (!homework?.questions) return {};
  return homework.questions.reduce((accumulator, question) => {
    accumulator[question.id] = null;
    if (question.question_type === 'LISTENING') {
      accumulator[question.id] = (question.config?.subQuestions || []).reduce(
        (subAcc, subQuestion) => {
          subAcc[subQuestion.id] = '';
          return subAcc;
        },
        {}
      );
    }
    if (question.question_type === 'MATCHING') {
      accumulator[question.id] = {};
    }
    if (question.question_type === 'DRAG_DROP') {
      accumulator[question.id] = (question.config?.items || []).map((item) => item.id);
    }
    if (question.question_type === 'FILL_BLANKS') {
      const blanks = question.config?.answers || [];
      accumulator[question.id] = blanks.map(() => '');
    }
    if (question.question_type === 'HOTSPOT') {
      accumulator[question.id] = [];
    }
    if (question.question_type === 'CODE') {
      accumulator[question.id] = {
        code: question.config?.starterCode || '',
        testResults: [],
      };
    }
    return accumulator;
  }, {});
};

/**
 * Convert backend Answer array to {questionId: value} map for frontend state.
 * Backend returns: [{question: 87, text_answer: "...", selected_choices: [1,2], attachments: [...], ...}, ...]
 * Frontend expects: {87: "..." or [1,2] or {...}, "87_attachments": [...]}
 */
const convertAnswersArrayToMap = (answersArray, questions) => {
  if (!Array.isArray(answersArray) || answersArray.length === 0) return {};
  
  const questionTypesById = {};
  if (questions) {
    questions.forEach((q) => { questionTypesById[q.id] = q.question_type; });
  }
  
  return answersArray.reduce((acc, answer) => {
    const qId = answer.question;
    const qType = questionTypesById[qId];
    
    // Восстанавливаем attachments если есть
    if (Array.isArray(answer.attachments) && answer.attachments.length > 0) {
      acc[`${qId}_attachments`] = answer.attachments;
    }
    
    // Determine value based on question type
    if (qType === 'TEXT' || qType === 'ESSAY') {
      acc[qId] = answer.text_answer || '';
    } else if (qType === 'SINGLE_CHOICE') {
      // Single choice: first selected choice or null
      acc[qId] = answer.selected_choices?.[0] ?? null;
    } else if (qType === 'MULTI_CHOICE') {
      acc[qId] = answer.selected_choices || [];
    } else if (qType === 'MATCHING' || qType === 'LISTENING') {
      // These store structured data in text_answer as JSON
      try {
        acc[qId] = answer.text_answer ? JSON.parse(answer.text_answer) : {};
      } catch {
        acc[qId] = {};
      }
    } else if (qType === 'DRAG_DROP' || qType === 'FILL_BLANKS') {
      // These also store array in text_answer as JSON
      try {
        acc[qId] = answer.text_answer ? JSON.parse(answer.text_answer) : [];
      } catch {
        acc[qId] = [];
      }
    } else if (qType === 'HOTSPOT') {
      try {
        acc[qId] = answer.text_answer ? JSON.parse(answer.text_answer) : [];
      } catch {
        acc[qId] = [];
      }
    } else if (qType === 'CODE') {
      try {
        acc[qId] = answer.text_answer ? JSON.parse(answer.text_answer) : { code: '', testResults: [] };
      } catch {
        acc[qId] = { code: '', testResults: [] };
      }
    } else {
      // Fallback: prefer text_answer, then selected_choices
      if (answer.text_answer) {
        acc[qId] = answer.text_answer;
      } else if (answer.selected_choices?.length) {
        acc[qId] = answer.selected_choices;
      } else {
        acc[qId] = null;
      }
    }
    return acc;
  }, {});
};

const useHomeworkSession = (homeworkId, injectedService) => {
  const localDraftKey = homeworkId ? `hw_draft_${homeworkId}` : null;
  const submissionHintKey = homeworkId ? `hw_submission_id_${homeworkId}` : null;
  const svc = injectedService || getHomeworkService();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [homework, setHomework] = useState(null);
  const [submission, setSubmission] = useState(null);
  const [answers, setAnswers] = useState(() => {
    // Безопасная проверка localStorage для iOS Private Mode
    if (localDraftKey && typeof localStorage !== 'undefined') {
      try {
        const saved = localStorage.getItem(localDraftKey);
        if (saved) return JSON.parse(saved);
      } catch (storageErr) {
        // localStorage недоступен в Safari Private Mode - продолжаем без черновика
      }
    }
    return {};
  });
  const [savingState, setSavingState] = useState({ status: 'idle', timestamp: null });
  const dirtyRef = useRef(false);
  const mountedRef = useRef(true);

  useEffect(() => () => {
    mountedRef.current = false;
  }, []);

  const loadHomework = useCallback(async () => {
    if (!homeworkId) return;
    setLoading(true);
    try {
      const hwIdNum = Number(homeworkId);

      // 1) Быстрый in-memory кеш для возврата назад/вперед без повторной загрузки
      const cacheEntry = homeworkCache.get(hwIdNum);
      const now = Date.now();
      if (cacheEntry && now - cacheEntry.ts < HOMEWORK_CACHE_TTL_MS) {
        setHomework(cacheEntry.data);
      }

      // 2) Параллельно грузим homework и (если есть) подсказку submissionId
      const homeworkPromise = svc.fetchHomework(homeworkId);

      let hintedSubmissionId = null;
      if (submissionHintKey && typeof localStorage !== 'undefined') {
        try {
          const raw = localStorage.getItem(submissionHintKey);
          const parsed = raw ? Number(raw) : null;
          if (Number.isFinite(parsed) && parsed > 0) hintedSubmissionId = parsed;
        } catch {
          // localStorage недоступен в Safari Private Mode
        }
      }
      const hintedSubmissionPromise = hintedSubmissionId
        ? svc.fetchSubmission(hintedSubmissionId).catch(() => null)
        : Promise.resolve(null);

      const [rawHomework, hintedSubmissionResp] = await Promise.all([
        homeworkPromise,
        hintedSubmissionPromise,
      ]);

      const homeworkData = rawHomework && rawHomework.data ? rawHomework.data : rawHomework;
      setHomework(homeworkData);
      homeworkCache.set(hwIdNum, { ts: Date.now(), data: homeworkData });

      // Восстановить черновик из localStorage, если есть
      let initialAnswers = buildInitialAnswers(homeworkData);
      if (localDraftKey && typeof localStorage !== 'undefined') {
        try {
          const saved = localStorage.getItem(localDraftKey);
          if (saved) initialAnswers = { ...initialAnswers, ...JSON.parse(saved) };
        } catch {
          // localStorage недоступен в Safari Private Mode
        }
      }
      
      setError(null);
      // 3) Сначала пытаемся использовать ранее найденный submission по id (быстрее, чем листинг)
      let submissionData = null;
      const hintedSubmission = hintedSubmissionResp?.data ? hintedSubmissionResp.data : hintedSubmissionResp;
      if (hintedSubmission && Number(hintedSubmission.homework) === hwIdNum) {
        submissionData = hintedSubmission;
      }

      // 4) Если подсказка не сработала, делаем листинг как fallback
      if (!submissionData) {
        try {
          const existingSubmissions = await svc.fetchSubmissions({ homework: homeworkId });
          const submissions = existingSubmissions?.data?.results || existingSubmissions?.data || [];
          const matchingSubmissions = submissions.filter((sub) => Number(sub.homework) === hwIdNum);
          if (matchingSubmissions.length > 0) {
            submissionData = matchingSubmissions[0];
          }
        } catch (e) {
          console.error('[useHomeworkSession] failed to fetch existing submissions:', e);
        }
      }

      // Восстановим answers из submission (для любого статуса)
      if (submissionData && Array.isArray(submissionData.answers) && submissionData.answers.length > 0) {
        const restoredAnswers = convertAnswersArrayToMap(submissionData.answers, homeworkData?.questions);
        initialAnswers = { ...initialAnswers, ...restoredAnswers };
      }

      // Если submission нет или она in_progress, создаем/используем её
      if (!submissionData) {
        const rawSubmission = await svc.startSubmission(homeworkId);
        submissionData = rawSubmission && rawSubmission.data ? rawSubmission.data : rawSubmission;
      }

      // Сохраняем подсказку для следующего входа (безопасно для iOS Private Mode)
      if (submissionHintKey && submissionData?.id && typeof localStorage !== 'undefined') {
        try {
          localStorage.setItem(submissionHintKey, String(submissionData.id));
        } catch {
          // localStorage недоступен - игнорируем
        }
      }
      
      setAnswers(initialAnswers);
      setSubmission(submissionData);
    } catch (requestError) {
      console.error('[useHomeworkSession] load failed:', requestError);
      setError('Не удалось загрузить задание. Попробуйте обновить страницу.');
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [homeworkId, localDraftKey, submissionHintKey, svc]);

  useEffect(() => {
    loadHomework();
  }, [loadHomework]);

  const recordAnswer = useCallback((questionId, value) => {
    setAnswers((previous) => {
      const next = { ...previous, [questionId]: value };
      if (localDraftKey) {
        try {
          // Безопасная проверка доступности localStorage для iOS Private Mode
          if (typeof localStorage !== 'undefined') {
            localStorage.setItem(localDraftKey, JSON.stringify(next));
          }
        } catch (storageErr) {
          // localStorage недоступен в Safari Private Mode - игнорируем
          // Черновик не сохранится локально, но ответы всё равно отправятся на сервер
        }
      }
      return next;
    });
    dirtyRef.current = true;
  }, [localDraftKey]);

  const saveProgress = useCallback(async () => {
    if (submission?.status && submission.status !== 'in_progress') return;
    if (!submission?.id) return;
    if (!dirtyRef.current) return;
    try {
      setSavingState({ status: 'saving', timestamp: Date.now() });
      await svc.saveProgress(submission.id, answers);
      dirtyRef.current = false;
      setSavingState({ status: 'saved', timestamp: Date.now() });
      // После успешного сохранения — удалить локальный черновик (безопасно для iOS)
      if (localDraftKey && typeof localStorage !== 'undefined') {
        try { 
          localStorage.removeItem(localDraftKey); 
        } catch {
          // localStorage недоступен в Safari Private Mode
        }
      }
    } catch (saveError) {
      console.error('[useHomeworkSession] save failed:', saveError);
      setSavingState({ status: 'error', timestamp: Date.now() });
    }
  }, [answers, localDraftKey, submission?.id, submission?.status, svc]);

  useEffect(() => {
    if (!submission?.id) return undefined;
    const interval = setInterval(() => {
      saveProgress();
    }, AUTO_SAVE_INTERVAL);
    return () => clearInterval(interval);
  }, [submission?.id, saveProgress]);

  const submitHomework = useCallback(async () => {
    if (!submission?.id) return;
    
    // Сохраняем прогресс перед отправкой (с retry для iOS)
    try {
      await saveProgress();
    } catch (saveErr) {
      console.warn('[useHomeworkSession] saveProgress failed before submit, continuing:', saveErr);
      // Продолжаем отправку даже если сохранение не удалось
    }
    
    // Retry логика для iOS/мобильных сетей
    const MAX_RETRIES = 3;
    let lastError = null;
    
    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        const resp = await svc.submit(submission.id);
        const data = resp && resp.data ? resp.data : resp;
        setSubmission(data);
        
        // После отправки удалим локальный черновик (с безопасной обработкой для iOS Private Mode)
        if (localDraftKey) {
          try { 
            localStorage.removeItem(localDraftKey); 
          } catch (storageErr) {
            // localStorage может быть недоступен в Safari Private Mode
            console.warn('[useHomeworkSession] localStorage cleanup failed:', storageErr);
          }
        }
        
        return resp;
      } catch (submitErr) {
        lastError = submitErr;
        const isNetworkError = !submitErr.response && (submitErr.code === 'ECONNABORTED' || submitErr.message?.includes('Network'));
        const isTimeout = submitErr.code === 'ECONNABORTED';
        
        console.warn(`[useHomeworkSession] submit attempt ${attempt}/${MAX_RETRIES} failed:`, submitErr.message);
        
        // Если это 400/403 - не повторяем (валидационная ошибка)
        if (submitErr.response?.status === 400 || submitErr.response?.status === 403) {
          throw submitErr;
        }
        
        // Повторяем только при сетевых ошибках и таймаутах
        if ((isNetworkError || isTimeout) && attempt < MAX_RETRIES) {
          // Экспоненциальная задержка: 1с, 2с, 4с
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt - 1) * 1000));
          continue;
        }
        
        throw submitErr;
      }
    }
    
    throw lastError;
  }, [localDraftKey, saveProgress, submission?.id, svc]);

  const progress = useMemo(() => {
    if (!homework?.questions?.length) return 0;
    const total = homework.questions.length;
    const answered = homework.questions.filter((question) => {
      const value = answers[question.id];
      if (value == null) return false;
      if (question.question_type === 'TEXT') {
        return Boolean(value?.trim?.());
      }
      if (question.question_type === 'SINGLE_CHOICE') {
        return Boolean(value);
      }
      if (question.question_type === 'MULTIPLE_CHOICE' || question.question_type === 'MULTI_CHOICE') {
        return Array.isArray(value) && value.length > 0;
      }
      if (question.question_type === 'LISTENING') {
        return Object.values(value || {}).some((answer) => Boolean(answer?.trim?.())) || false;
      }
      if (question.question_type === 'MATCHING') {
        return Object.keys(value || {}).length === (question.config?.pairs?.length || 0);
      }
      if (question.question_type === 'DRAG_DROP') {
        return (value || []).length > 0;
      }
      if (question.question_type === 'FILL_BLANKS') {
        return (value || []).every((answer) => Boolean(answer?.trim?.()));
      }
      if (question.question_type === 'HOTSPOT') {
        return Array.isArray(value) && value.length > 0;
      }
      if (question.question_type === 'CODE') {
        // CODE считается отвеченным если есть код (не пустой) и хотя бы один тест запущен
        const codeValue = typeof value === 'object' ? value : {};
        return Boolean(codeValue.code?.trim()) && (codeValue.testResults?.length > 0);
      }
      return false;
    }).length;
    return Math.round((answered / total) * 100);
  }, [answers, homework]);

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
  };
};

export default useHomeworkSession;
