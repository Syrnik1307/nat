import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../../../../apiService';
import { Notification } from '../../../../shared/components';
import useNotification from '../../../../shared/hooks/useNotification';
import './SubmissionReview.css';

/**
 * Компонент для проверки работы ученика учителем
 * Позволяет просматривать ответы, выставлять оценки и оставлять комментарии
 */
const SubmissionReview = () => {
  const { notification, showNotification, closeNotification } = useNotification();
  const { submissionId } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submission, setSubmission] = useState(null);
  const [editingAnswerId, setEditingAnswerId] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [saving, setSaving] = useState(false);

  const loadSubmission = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(`submissions/${submissionId}/`);
      setSubmission(response.data);
    } catch (err) {
      console.error('Ошибка загрузки работы:', err);
      setError(err.response?.data?.error || 'Не удалось загрузить работу');
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  useEffect(() => {
    loadSubmission();
  }, [loadSubmission]);

  const startEditing = (answer) => {
    setEditingAnswerId(answer.id);
    setEditValues({
      teacher_score: answer.teacher_score ?? answer.auto_score ?? 0,
      teacher_feedback: answer.teacher_feedback || ''
    });
  };

  const cancelEditing = () => {
    setEditingAnswerId(null);
    setEditValues({});
  };

  const saveAnswer = async (answerId) => {
    try {
      setSaving(true);
      const response = await apiClient.patch(
        `submissions/${submissionId}/update_answer/`,
        {
          answer_id: answerId,
          teacher_score: editValues.teacher_score,
          teacher_feedback: editValues.teacher_feedback
        }
      );
      
      // Обновляем локальное состояние
      setSubmission(response.data);
      setEditingAnswerId(null);
      setEditValues({});
    } catch (err) {
      console.error('Ошибка сохранения оценки:', err);
      showNotification('error', 'Ошибка', err.response?.data?.error || 'Не удалось сохранить оценку');
    } finally {
      setSaving(false);
    }
  };

  const normalizeText = (value) => (value ?? '').toString().trim().toLowerCase();

  const parseJsonValue = (value, fallback) => {
    if (!value) return fallback;
    try {
      return typeof value === 'string' ? JSON.parse(value) : value;
    } catch {
      return fallback;
    }
  };

  const getChoiceTextMap = (item) => {
    const map = {};
    (item.choices || []).forEach((choice) => {
      map[String(choice.id)] = choice.text;
    });
    return map;
  };

  const getSelectedChoiceTexts = (item) => {
    const choiceMap = getChoiceTextMap(item);
    return (item.selected_choices || [])
      .map((id) => choiceMap[String(id)] || String(id))
      .filter(Boolean);
  };

  const formatComplexValue = (value) => {
    if (Array.isArray(value)) {
      return value.join(', ');
    }
    if (value && typeof value === 'object') {
      return Object.entries(value)
        .map(([key, val]) => `${key}: ${val}`)
        .join(', ');
    }
    return value ? String(value) : '(Нет ответа)';
  };

  const getAnswerDisplay = (item) => {
    if (item.question_type === 'TEXT') {
      return item.text_answer || '(Нет ответа)';
    }
    
    if (item.question_type === 'SINGLE_CHOICE' || item.question_type === 'MULTI_CHOICE' || item.question_type === 'MULTIPLE_CHOICE') {
      const selectedText = getSelectedChoiceTexts(item);
      return selectedText.length > 0 ? selectedText.join(', ') : '(Нет ответа)';
    }

    if (item.question_type === 'MATCHING' || item.question_type === 'LISTENING') {
      const parsed = parseJsonValue(item.text_answer, {});
      return formatComplexValue(parsed);
    }

    if (item.question_type === 'DRAG_DROP' || item.question_type === 'FILL_BLANKS' || item.question_type === 'HOTSPOT') {
      const parsed = parseJsonValue(item.text_answer, []);
      return formatComplexValue(parsed);
    }

    if (item.question_type === 'CODE') {
      const parsed = parseJsonValue(item.text_answer, {});
      if (parsed && typeof parsed === 'object' && parsed.code) {
        return parsed.code;
      }
      return formatComplexValue(parsed);
    }
    
    return item.text_answer || 'Ответ предоставлен';
  };

  const getCorrectChoiceIds = (item) => {
    const config = item.config || {};
    if (config.correctOptionId) {
      return [String(config.correctOptionId)];
    }
    if (Array.isArray(config.correctOptionIds) && config.correctOptionIds.length > 0) {
      return config.correctOptionIds.map((id) => String(id));
    }
    const correctFromChoices = (item.choices || [])
      .filter((choice) => choice.is_correct)
      .map((choice) => String(choice.id));
    return correctFromChoices;
  };

  const isSameSet = (a, b) => {
    if (a.length !== b.length) return false;
    const setA = new Set(a);
    return b.every((val) => setA.has(val));
  };

  const getCorrectAnswerInfo = (item) => {
    const config = item.config || {};

    if (item.question_type === 'TEXT') {
      const correct = (config.correctAnswer || '').trim();
      if (!correct) return { hasCorrect: false };
      const student = (item.text_answer || '').trim();
      return {
        hasCorrect: true,
        correctText: correct,
        isMatch: normalizeText(student) === normalizeText(correct),
      };
    }

    if (item.question_type === 'SINGLE_CHOICE' || item.question_type === 'MULTI_CHOICE' || item.question_type === 'MULTIPLE_CHOICE') {
      const correctIds = getCorrectChoiceIds(item);
      if (!correctIds.length) return { hasCorrect: false };
      const studentIds = (item.selected_choices || []).map((id) => String(id));
      const choiceMap = getChoiceTextMap(item);
      const correctText = correctIds.map((id) => choiceMap[id]).filter(Boolean).join(', ');
      return {
        hasCorrect: true,
        correctText: correctText || correctIds.join(', '),
        isMatch: isSameSet(correctIds, studentIds),
      };
    }

    if (item.question_type === 'MATCHING') {
      const pairs = Array.isArray(config.pairs) ? config.pairs : [];
      if (!pairs.length) return { hasCorrect: false };
      const studentMatches = parseJsonValue(item.text_answer, {});
      let allMatch = true;
      const correctText = pairs
        .map((pair) => {
          const left = (pair.left || '').toString();
          const right = (pair.right || '').toString();
          if (right) {
            const studentRight = (studentMatches[String(pair.id)] || '').toString();
            if (studentRight !== right) {
              allMatch = false;
            }
          }
          return right ? `${left} — ${right}` : left;
        })
        .join('\n');
      return {
        hasCorrect: true,
        correctText: correctText || '(Нет правильных ответов)',
        isMatch: allMatch,
      };
    }

    if (item.question_type === 'DRAG_DROP') {
      const correctOrder = Array.isArray(config.correctOrder) ? config.correctOrder.map(String) : [];
      if (!correctOrder.length) return { hasCorrect: false };
      const studentOrder = parseJsonValue(item.text_answer, []).map(String);
      const items = Array.isArray(config.items) ? config.items : [];
      const itemMap = items.reduce((acc, cur) => {
        acc[String(cur.id)] = cur.text || String(cur.id);
        return acc;
      }, {});
      const correctText = correctOrder.map((id) => itemMap[id] || id).join(' → ');
      return {
        hasCorrect: true,
        correctText,
        isMatch: correctOrder.join('|') === studentOrder.join('|'),
      };
    }

    if (item.question_type === 'FILL_BLANKS') {
      const correctAnswers = Array.isArray(config.answers) ? config.answers : [];
      if (!correctAnswers.length) return { hasCorrect: false };
      const studentAnswers = parseJsonValue(item.text_answer, []);
      const caseSensitive = !!config.caseSensitive;
      let allMatch = true;
      correctAnswers.forEach((correct, index) => {
        const student = studentAnswers[index];
        if (caseSensitive) {
          if ((student ?? '') !== (correct ?? '')) allMatch = false;
        } else {
          if (normalizeText(student) !== normalizeText(correct)) allMatch = false;
        }
      });
      return {
        hasCorrect: true,
        correctText: correctAnswers.join(', '),
        isMatch: allMatch,
      };
    }

    if (item.question_type === 'LISTENING') {
      const subQuestions = Array.isArray(config.subQuestions) ? config.subQuestions : [];
      if (!subQuestions.length) return { hasCorrect: false };
      const studentAnswers = parseJsonValue(item.text_answer, {});
      let allMatch = true;
      const correctText = subQuestions
        .map((sq) => {
          const expected = (sq.answer || '').toString();
          const student = (studentAnswers[String(sq.id)] || '').toString();
          if (expected && normalizeText(student) !== normalizeText(expected)) {
            allMatch = false;
          }
          return expected ? `${sq.prompt || ''}: ${expected}` : (sq.prompt || '').toString();
        })
        .join('\n');
      return {
        hasCorrect: true,
        correctText,
        isMatch: allMatch,
      };
    }

    if (item.question_type === 'HOTSPOT') {
      const hotspots = Array.isArray(config.hotspots) ? config.hotspots : [];
      const correctIds = hotspots.filter((h) => h.isCorrect).map((h) => String(h.id));
      if (!correctIds.length) return { hasCorrect: false };
      const studentSelections = parseJsonValue(item.text_answer, []).map(String);
      return {
        hasCorrect: true,
        correctText: correctIds.join(', '),
        isMatch: isSameSet(correctIds, studentSelections),
      };
    }

    if (item.question_type === 'CODE') {
      const solution = (config.solutionCode || '').trim();
      if (!solution) return { hasCorrect: false };
      const parsed = parseJsonValue(item.text_answer, {});
      const studentCode = (parsed?.code || '').trim();
      return {
        hasCorrect: true,
        correctText: solution,
        isMatch: normalizeText(studentCode) === normalizeText(solution),
      };
    }

    return { hasCorrect: false };
  };

  const getCurrentScore = (answer) => {
    return answer.teacher_score ?? answer.auto_score ?? 0;
  };

  const formatTimeSpent = (seconds) => {
    if (!seconds) return '—';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) {
      return `${hours} ч ${minutes} мин`;
    }
    if (minutes > 0) {
      return `${minutes} мин ${secs} сек`;
    }
    return `${secs} сек`;
  };

  // Объединяем answers и questions: если есть answer - берём его, иначе создаём пустой из question
  const getReviewItems = () => {
    const questions = submission.questions || [];
    const answersMap = {};
    (submission.answers || []).forEach(a => {
      answersMap[a.question] = a;
    });
    
    return questions.map((q, index) => {
      const answer = answersMap[q.id];
      return {
        id: answer?.id || `q-${q.id}`,
        questionId: q.id,
        question_text: q.prompt || '',
        question_type: q.question_type,
        question_points: q.points,
        config: q.config || {},
        choices: q.choices || [],
        text_answer: answer?.text_answer || null,
        selected_choices: answer?.selected_choices || [],
        auto_score: answer?.auto_score ?? null,
        teacher_score: answer?.teacher_score ?? null,
        teacher_feedback: answer?.teacher_feedback || '',
        attachments: answer?.attachments || [],
        hasAnswer: !!answer,
        index,
        // Telemetry data
        time_spent_seconds: answer?.time_spent_seconds ?? null,
        is_pasted: answer?.is_pasted ?? false,
        tab_switches: answer?.tab_switches ?? 0,
      };
    });
  };

  const completeReview = async () => {
    try {
      setSaving(true);
      await apiClient.post(`submissions/${submissionId}/complete_review/`);
      showNotification('success', 'Успешно', 'Проверка завершена');
      setTimeout(() => navigate(-1), 1000);
    } catch (err) {
      console.error('Ошибка завершения проверки:', err);
      showNotification('error', 'Ошибка', err.response?.data?.error || 'Не удалось завершить проверку');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="sr-container">
        <div className="sr-loading">Загрузка работы...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="sr-container">
        <div className="sr-error">{error}</div>
        <button className="sr-btn-secondary" onClick={() => navigate(-1)}>
          Назад
        </button>
      </div>
    );
  }

  if (!submission) {
    return (
      <div className="sr-container">
        <div className="sr-error">Работа не найдена</div>
      </div>
    );
  }

  // Расчёт агрегированной телеметрии
  const getTelemetrySummary = () => {
    const items = getReviewItems();
    let totalTime = 0;
    let pasteCount = 0;
    let tabSwitches = 0;
    let answersWithTelemetry = 0;
    
    items.forEach(item => {
      if (item.time_spent_seconds) {
        totalTime += item.time_spent_seconds;
        answersWithTelemetry++;
      }
      if (item.is_pasted) pasteCount++;
      if (item.tab_switches) tabSwitches += item.tab_switches;
    });
    
    return { totalTime, pasteCount, tabSwitches, answersWithTelemetry, totalAnswers: items.length };
  };

  const telemetrySummary = getTelemetrySummary();

  return (
    <div className="sr-container">
      <div className="sr-header">
        <button className="sr-back-btn" onClick={() => navigate(-1)}>
          ← Назад
        </button>
        <div className="sr-header-info">
          <h1 className="sr-title">Проверка работы</h1>
          <div className="sr-meta">
            <span className="sr-meta-item">
              <strong>Задание:</strong> {submission.homework_title}
            </span>
            <span className="sr-meta-item">
              <strong>Ученик:</strong> {submission.student_name}
            </span>
            <span className="sr-meta-item">
              <strong>Отправлено:</strong> {new Date(submission.submitted_at).toLocaleString('ru-RU')}
            </span>
            <span className="sr-meta-item">
              <strong>Время выполнения:</strong> {formatTimeSpent(submission.time_spent_seconds)}
            </span>
            <span className="sr-meta-item">
              <strong>Общий балл:</strong> {submission.total_score || 0} / {submission.max_score || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Сводка телеметрии */}
      {(telemetrySummary.totalTime > 0 || telemetrySummary.pasteCount > 0 || telemetrySummary.tabSwitches > 0) && (
        <div className="sr-telemetry-summary">
          <span className="sr-telemetry-summary-label">Аналитика работы:</span>
          <div className="sr-telemetry-summary-items">
            {telemetrySummary.totalTime > 0 && (
              <span className="sr-telemetry-summary-item">
                Суммарное время: {formatTimeSpent(telemetrySummary.totalTime)}
              </span>
            )}
            {telemetrySummary.pasteCount > 0 && (
              <span className="sr-telemetry-summary-item">
                Вставок: {telemetrySummary.pasteCount} из {telemetrySummary.totalAnswers}
              </span>
            )}
            {telemetrySummary.tabSwitches > 0 && (
              <span className="sr-telemetry-summary-item">
                Переключений вкладок: {telemetrySummary.tabSwitches}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="sr-answers-list">
        {(() => {
          const reviewItems = getReviewItems();
          if (reviewItems.length === 0) {
            return <div className="sr-empty">Нет вопросов в этом задании</div>;
          }
          return reviewItems.map((item) => {
            const correctInfo = getCorrectAnswerInfo(item);
            const answerClassName = item.hasAnswer && correctInfo.hasCorrect
              ? (correctInfo.isMatch ? 'is-correct' : 'is-incorrect')
              : '';
            return (
              <div key={item.id} className={`sr-answer-card ${!item.hasAnswer ? 'sr-no-answer' : ''}`}>
              <div className="sr-answer-header">
                <div className="sr-question-number">Вопрос {item.index + 1}</div>
                <div className="sr-question-type-badge">
                  {item.question_type === 'TEXT' && 'Текстовый ответ'}
                  {item.question_type === 'SINGLE_CHOICE' && 'Один вариант'}
                  {item.question_type === 'MULTI_CHOICE' && 'Несколько вариантов'}
                  {item.question_type === 'MULTIPLE_CHOICE' && 'Несколько вариантов'}
                  {item.question_type === 'LISTENING' && 'Аудирование'}
                  {item.question_type === 'MATCHING' && 'Сопоставление'}
                  {item.question_type === 'FILL_BLANKS' && 'Заполнение пропусков'}
                  {item.question_type === 'CODE' && 'Код'}
                </div>
                <div className="sr-points">
                  {getCurrentScore(item)} / {item.question_points} баллов
                </div>
              </div>

              <div className="sr-question-text">{item.question_text || '(Без текста вопроса)'}</div>

              {/* Изображение вопроса, если есть */}
              {item.config?.imageUrl && (
                <div className="sr-question-image">
                  <img src={item.config.imageUrl} alt="Изображение вопроса" />
                </div>
              )}

              {/* Прикреплённый документ, если есть */}
              {item.config?.attachmentUrl && (
                <div className="sr-question-attachment">
                  <a
                    href={item.config.attachmentUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="sr-attachment-link"
                  >
                    {item.config.attachmentName || 'Документ'}
                  </a>
                </div>
              )}

              <div className="sr-student-answer">
                <strong>Ответ ученика:</strong>
                <div className={`sr-answer-content ${answerClassName}`}>
                  {item.hasAnswer ? getAnswerDisplay(item) : '(Ученик не ответил на этот вопрос)'}
                </div>
              </div>

              {correctInfo.hasCorrect && (
                <div className="sr-correct-answer">
                  <strong>Правильный ответ:</strong>
                  <div className="sr-answer-content sr-correct-content">
                    {correctInfo.correctText || '(Не задан)'}
                  </div>
                </div>
              )}

              {/* Прикреплённые файлы от ученика */}
              {item.attachments?.length > 0 && (
                <div className="sr-student-attachments">
                  <strong>Прикреплённые файлы:</strong>
                  <div className="sr-attachments-list">
                    {item.attachments.map((file, idx) => (
                      <div key={file.file_id || idx} className="sr-attachment-item">
                        {file.mime_type?.startsWith('image/') ? (
                          <a href={file.url} target="_blank" rel="noopener noreferrer" className="sr-attachment-image">
                            <img src={file.url} alt={file.name} />
                          </a>
                        ) : (
                          <a href={file.url} target="_blank" rel="noopener noreferrer" className="sr-attachment-file">
                            <span className="sr-attachment-icon">
                              {file.name?.split('.').pop()?.toUpperCase() || 'FILE'}
                            </span>
                            <span className="sr-attachment-name">{file.name}</span>
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {item.auto_score !== null && (
                <div className="sr-auto-score-info">
                  Автоматическая оценка: {item.auto_score} баллов
                </div>
              )}

              {/* Телеметрия ответа */}
              {item.hasAnswer && (item.time_spent_seconds || item.is_pasted || item.tab_switches > 0) && (
                <div className="sr-telemetry">
                  <span className="sr-telemetry-label">Аналитика:</span>
                  <div className="sr-telemetry-items">
                    {item.time_spent_seconds > 0 && (
                      <span className="sr-telemetry-item">
                        {formatTimeSpent(item.time_spent_seconds)}
                      </span>
                    )}
                    {item.is_pasted && (
                      <span className="sr-telemetry-item">
                        Вставка
                      </span>
                    )}
                    {item.tab_switches > 0 && (
                      <span className="sr-telemetry-item">
                        {item.tab_switches} перекл.
                      </span>
                    )}
                  </div>
                </div>
              )}

              {item.hasAnswer && editingAnswerId === item.id ? (
                <div className="sr-edit-form">
                  <div className="sr-form-group">
                    <label className="sr-label">
                      Оценка (макс. {item.question_points}):
                    </label>
                    <input
                      type="number"
                      min="0"
                      max={item.question_points}
                      className="sr-input"
                      value={editValues.teacher_score}
                      onChange={(e) => setEditValues({
                        ...editValues,
                        teacher_score: parseInt(e.target.value) || 0
                      })}
                    />
                  </div>

                  <div className="sr-form-group">
                    <label className="sr-label">Комментарий:</label>
                    <textarea
                      className="sr-textarea"
                      rows="3"
                      value={editValues.teacher_feedback}
                      onChange={(e) => setEditValues({
                        ...editValues,
                        teacher_feedback: e.target.value
                      })}
                      placeholder="Оставьте комментарий для ученика..."
                    />
                  </div>

                  <div className="sr-edit-actions">
                    <button
                      className="sr-btn-primary"
                      onClick={() => saveAnswer(item.id)}
                      disabled={saving}
                    >
                      {saving ? 'Сохранение...' : 'Сохранить'}
                    </button>
                    <button
                      className="sr-btn-secondary"
                      onClick={cancelEditing}
                      disabled={saving}
                    >
                      Отмена
                    </button>
                  </div>
                </div>
              ) : item.hasAnswer ? (
                <div className="sr-feedback-section">
                  {item.teacher_feedback && (
                    <div className="sr-teacher-feedback">
                      <strong>Комментарий учителя:</strong>
                      <p>{item.teacher_feedback}</p>
                    </div>
                  )}
                  
                  <button
                    className="sr-btn-edit"
                    onClick={() => startEditing(item)}
                  >
                    {item.teacher_score !== null ? 'Изменить оценку' : 'Выставить оценку'}
                  </button>
                </div>
              ) : (
                <div className="sr-no-answer-hint">
                  Ответ не был сохранён (возможно, старая работа)
                </div>
              )}
            </div>
            );
          });
        })()}
      </div>

      <div className="sr-footer">
        <div className="sr-total-score">
          <strong>Итоговый балл:</strong> {submission.total_score || 0}
        </div>
        <button 
          className="sr-btn-done" 
          onClick={completeReview}
          disabled={saving}
        >
          {saving ? 'Завершение...' : 'Завершить проверку'}
        </button>
      </div>

      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />
    </div>
  );
};

export default SubmissionReview;
