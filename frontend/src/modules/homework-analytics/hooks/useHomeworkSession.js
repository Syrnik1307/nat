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
    return accumulator;
  }, {});
};

/**
 * Convert backend Answer array to {questionId: value} map for frontend state.
 * Backend returns: [{question: 87, text_answer: "...", selected_choices: [1,2], ...}, ...]
 * Frontend expects: {87: "..." or [1,2] or {...}}
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
  const svc = injectedService || getHomeworkService();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [homework, setHomework] = useState(null);
  const [submission, setSubmission] = useState(null);
  const [answers, setAnswers] = useState(() => {
    if (localDraftKey) {
      try {
        const saved = localStorage.getItem(localDraftKey);
        if (saved) return JSON.parse(saved);
      } catch {}
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
      // debug: log that we're calling fetchHomework
      // eslint-disable-next-line no-console
      console.log('[useHomeworkSession] calling fetchHomework', homeworkId, 'svc.fetchHomework type:', typeof (svc && svc.fetchHomework));
      // eslint-disable-next-line no-console
      try { console.log('isMockFunction:', typeof jest !== 'undefined' && jest.isMockFunction && jest.isMockFunction(svc.fetchHomework)); } catch (e) {}
      const rawHomework = await svc.fetchHomework(homeworkId);
      // eslint-disable-next-line no-console
      console.log('[useHomeworkSession] rawHomework response:', rawHomework);
      const homeworkData = rawHomework && rawHomework.data ? rawHomework.data : rawHomework;
      // eslint-disable-next-line no-console
      console.log('[useHomeworkSession] fetched homework', homeworkData && homeworkData.questions ? homeworkData.questions.length : typeof homeworkData);
      setHomework(homeworkData);
      // Восстановить черновик из localStorage, если есть
      let initialAnswers = buildInitialAnswers(homeworkData);
      // eslint-disable-next-line no-console
      console.log('[useHomeworkSession] initialAnswers built', initialAnswers);
      if (localDraftKey) {
        try {
          const saved = localStorage.getItem(localDraftKey);
          if (saved) initialAnswers = { ...initialAnswers, ...JSON.parse(saved) };
        } catch {}
      }
      
      setError(null);
      // Сначала проверяем, есть ли уже submission для этого ДЗ
      let submissionData = null;
      try {
        const existingSubmissions = await svc.fetchSubmissions({ homework: homeworkId });
        const submissions = existingSubmissions?.data?.results || existingSubmissions?.data || [];
        const hwId = Number(homeworkId);
        const matchingSubmissions = submissions.filter((sub) => Number(sub.homework) === hwId);
        if (matchingSubmissions.length > 0) {
          submissionData = matchingSubmissions[0];
          // eslint-disable-next-line no-console
          console.log('[useHomeworkSession] found existing submission:', submissionData.status);
          // Восстановим answers из submission (для любого статуса)
          // Backend возвращает answers как массив объектов [{question: id, text_answer, selected_choices, ...}]
          if (Array.isArray(submissionData.answers) && submissionData.answers.length > 0) {
            const restoredAnswers = convertAnswersArrayToMap(submissionData.answers, homeworkData?.questions);
            // eslint-disable-next-line no-console
            console.log('[useHomeworkSession] restored answers from submission:', restoredAnswers);
            initialAnswers = { ...initialAnswers, ...restoredAnswers };
          }
        }
      } catch (e) {
        console.error('[useHomeworkSession] failed to fetch existing submissions:', e);
      }

      // Если submission нет или она in_progress, создаем/используем её
      if (!submissionData) {
        const rawSubmission = await svc.startSubmission(homeworkId);
        submissionData = rawSubmission && rawSubmission.data ? rawSubmission.data : rawSubmission;
        // eslint-disable-next-line no-console
        console.log('[useHomeworkSession] created new submission');
      }
      
      setAnswers(initialAnswers);
      // eslint-disable-next-line no-console
      console.log('[useHomeworkSession] answers set');
      setSubmission(submissionData);
    } catch (requestError) {
      console.error('[useHomeworkSession] load failed:', requestError);
      setError('Не удалось загрузить задание. Попробуйте обновить страницу.');
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [homeworkId, localDraftKey, svc]);

  useEffect(() => {
    loadHomework();
  }, [loadHomework]);

  const recordAnswer = useCallback((questionId, value) => {
    setAnswers((previous) => {
      const next = { ...previous, [questionId]: value };
      if (localDraftKey) {
        try {
          localStorage.setItem(localDraftKey, JSON.stringify(next));
        } catch {}
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
      // После успешного сохранения — удалить локальный черновик
      if (localDraftKey) {
        try { localStorage.removeItem(localDraftKey); } catch {}
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
    await saveProgress();
    const resp = await svc.submit(submission.id);
    const data = resp && resp.data ? resp.data : resp;
    setSubmission(data);
    // После отправки удалим локальный черновик
    if (localDraftKey) {
      try { localStorage.removeItem(localDraftKey); } catch {}
    }
    return resp;
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
