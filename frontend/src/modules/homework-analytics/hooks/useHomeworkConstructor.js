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

  const checkBeforeSave = useCallback((meta, questions, options = {}) => {
    const metaIssues = validateAssignmentMeta(meta, options);
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
    async (meta, questions, existingId = null, options = {}) => {
      const validation = checkBeforeSave(meta, questions, options);
      if (!validation.ok) {
        return { saved: false, validation };
      }

      if (existingId) {
        await homeworkService.update(existingId, meta, questions);
        return { saved: true, validation, homeworkId: existingId };
      }
      const created = await homeworkService.create(meta, questions);
      return { saved: true, validation, homeworkId: created?.id };
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
