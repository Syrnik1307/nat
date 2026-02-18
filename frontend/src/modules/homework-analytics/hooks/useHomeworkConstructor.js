import { useCallback, useEffect, useMemo, useState } from 'react';
import { getGroups } from '../../../apiService';
import { validateAssignmentMeta, summarizeQuestionIssues } from '../utils/questionValidators';
import { homeworkService } from '../services/homeworkService';

export const useHomeworkConstructor = () => {
  const [groups, setGroups] = useState([]);
  const [loadingGroups, setLoadingGroups] = useState(true);
  const [groupError, setGroupError] = useState(null);

  const loadGroups = useCallback(async () => {
    setLoadingGroups(true);
    try {
      const response = await getGroups();
      const data = Array.isArray(response.data)
        ? response.data
        : response.data?.results || [];
      setGroups(Array.isArray(data) ? data : []);
      setGroupError(null);
    } catch (error) {
      console.error('[HomeworkConstructor] Failed to load groups:', error);
      setGroupError('Не удалось загрузить группы. Попробуйте обновить страницу.');
    } finally {
      setLoadingGroups(false);
    }
  }, []);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  const groupOptions = useMemo(
    () =>
      groups.map((group) => ({
        value: group.id,
        label: group.name,
      })),
    [groups]
  );

  const checkBeforeSave = useCallback((meta, questions) => {
    const metaIssues = validateAssignmentMeta(meta);
    if (metaIssues.length) {
      return { ok: false, metaIssues, questionIssues: [] };
    }

    const questionIssues = summarizeQuestionIssues(questions);
    if (questionIssues.length) {
      return { ok: false, metaIssues: [], questionIssues };
    }

    return { ok: true, metaIssues: [], questionIssues: [] };
  }, []);

  const computeSuggestedMaxScore = useCallback(
    (questions) =>
      questions.reduce((total, question) => {
        const points = Number(question.points);
        if (Number.isFinite(points) && points > 0) {
          return total + points;
        }
        return total;
      }, 0),
    []
  );

  const saveDraft = useCallback(
    async (meta, questions, existingId = null) => {
      const validation = checkBeforeSave(meta, questions);
      if (!validation.ok) {
        return { saved: false, validation, homeworkData: null };
      }

      let homeworkData = null;
      if (existingId) {
        const response = await homeworkService.update(existingId, meta, questions);
        homeworkData = response?.data || response;
      } else {
        const response = await homeworkService.create(meta, questions);
        homeworkData = response?.data || response;
      }
      return { saved: true, validation, homeworkData };
    },
    [checkBeforeSave]
  );

  return {
    groups,
    groupOptions,
    loadingGroups,
    groupError,
    reloadGroups: loadGroups,
    checkBeforeSave,
    computeSuggestedMaxScore,
    saveDraft,
  };
};

export default useHomeworkConstructor;
