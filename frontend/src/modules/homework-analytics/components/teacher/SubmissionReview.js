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

  const getAnswerDisplay = (answer) => {
    if (answer.question_type === 'TEXT') {
      return answer.text_answer || '(Нет ответа)';
    }
    
    if (answer.question_type === 'SINGLE_CHOICE' || answer.question_type === 'MULTI_CHOICE') {
      return `Выбранные варианты: ${answer.selected_choices?.length || 0}`;
    }
    
    return 'Ответ предоставлен';
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
        text_answer: answer?.text_answer || null,
        selected_choices: answer?.selected_choices || [],
        auto_score: answer?.auto_score ?? null,
        teacher_score: answer?.teacher_score ?? null,
        teacher_feedback: answer?.teacher_feedback || '',
        hasAnswer: !!answer,
        index,
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

      <div className="sr-answers-list">
        {(() => {
          const reviewItems = getReviewItems();
          if (reviewItems.length === 0) {
            return <div className="sr-empty">Нет вопросов в этом задании</div>;
          }
          return reviewItems.map((item) => (
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
                <div className="sr-answer-content">
                  {item.hasAnswer ? getAnswerDisplay(item) : '(Ученик не ответил на этот вопрос)'}
                </div>
              </div>

              {item.auto_score !== null && (
                <div className="sr-auto-score-info">
                  Автоматическая оценка: {item.auto_score} баллов
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
          ));
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
