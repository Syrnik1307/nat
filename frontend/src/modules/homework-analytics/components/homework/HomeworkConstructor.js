import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { apiClient } from '../../../../apiService';
import useHomeworkConstructor from '../../hooks/useHomeworkConstructor';
import {
  QUESTION_TYPES,
  createQuestionTemplate,
  getQuestionLabel,
  getQuestionIcon,
} from '../../utils/questionTemplates';
import TextQuestion from '../questions/TextQuestion';
import SingleChoiceQuestion from '../questions/SingleChoiceQuestion';
import MultipleChoiceQuestion from '../questions/MultipleChoiceQuestion';
import ListeningQuestion from '../questions/ListeningQuestion';
import MatchingQuestion from '../questions/MatchingQuestion';
import DragDropQuestion from '../questions/DragDropQuestion';
import FillBlanksQuestion from '../questions/FillBlanksQuestion';
import HotspotQuestion from '../questions/HotspotQuestion';
import './HomeworkConstructor.css';
import DateTimePicker from './DateTimePicker';
import GroupSelect from './GroupSelect';

const initialMeta = {
  title: '',
  description: '',
  groupId: '',
  deadline: '',
  maxScore: 100,
  gamificationEnabled: true,
};

const QUESTION_COMPONENTS = {
  TEXT: TextQuestion,
  SINGLE_CHOICE: SingleChoiceQuestion,
  MULTIPLE_CHOICE: MultipleChoiceQuestion,
  LISTENING: ListeningQuestion,
  MATCHING: MatchingQuestion,
  DRAG_DROP: DragDropQuestion,
  FILL_BLANKS: FillBlanksQuestion,
  HOTSPOT: HotspotQuestion,
};

const HomeworkPreviewSection = ({ questions, previewQuestion, onChangePreviewQuestion }) => {
  if (!questions || questions.length === 0) {
    return <div className="hc-preview-placeholder">Добавьте вопросы для превью</div>;
  }

  const currentQuestion = questions[previewQuestion];
  if (!currentQuestion) {
    return <div className="hc-preview-placeholder">Выберите вопрос для превью</div>;
  }

  const renderPreviewContent = () => {
    switch (currentQuestion.question_type) {
      case 'TEXT':
        return (
          <div className="preview-question">
            <p>{currentQuestion.question_text || 'Текст вопроса не заполнен'}</p>
            <textarea className="form-textarea" placeholder="Ответ студента..." disabled rows={4} />
          </div>
        );

      case 'SINGLE_CHOICE':
        return (
          <div className="preview-question">
            <p>{currentQuestion.question_text || 'Текст вопроса не заполнен'}</p>
            {(currentQuestion.config?.options || []).map((option, idx) => (
              <div key={idx} className="preview-option">
                <input type="radio" name="preview-radio" disabled />
                <label>{option.text || `Вариант ${idx + 1}`}</label>
              </div>
            ))}
          </div>
        );

      case 'MULTIPLE_CHOICE':
        return (
          <div className="preview-question">
            <p>{currentQuestion.question_text || 'Текст вопроса не заполнен'}</p>
            {(currentQuestion.config?.options || []).map((option, idx) => (
              <div key={idx} className="preview-option">
                <input type="checkbox" disabled />
                <label>{option.text || `Вариант ${idx + 1}`}</label>
              </div>
            ))}
          </div>
        );

      default:
        return (
          <div className="preview-question">
            <p>{currentQuestion.question_text || 'Текст вопроса не заполнен'}</p>
            <p className="preview-note">Тип: {getQuestionLabel(currentQuestion.question_type)}</p>
          </div>
        );
    }
  };

  return (
    <div className="hc-preview-live">
      <div className="hc-preview-nav">
        <span>
          Вопрос {previewQuestion + 1} из {questions.length}
        </span>
        <div>
          <button
            type="button"
            className="gm-btn-surface"
            onClick={() => onChangePreviewQuestion(Math.max(0, previewQuestion - 1))}
            disabled={previewQuestion === 0}
          >
            ← Пред.
          </button>
          <button
            type="button"
            className="gm-btn-surface"
            onClick={() => onChangePreviewQuestion(Math.min(questions.length - 1, previewQuestion + 1))}
            disabled={previewQuestion === questions.length - 1}
          >
            След. →
          </button>
        </div>
      </div>
      {renderPreviewContent()}
    </div>
  );
};

const HomeworkQuestionEditor = ({ question, index, onUpdateQuestion }) => {
  const TypeComponent = QUESTION_COMPONENTS[question.question_type];

  if (!TypeComponent) {
    return (
      <div className="hc-preview-placeholder">
        Тип вопроса в разработке. Он появится в следующей итерации.
      </div>
    );
  }

  return (
    <TypeComponent
      question={question}
      onChange={(next) => onUpdateQuestion(index, next)}
    />
  );
};

const HomeworkConstructor = () => {
  const navigate = useNavigate();
  const {
    groupOptions,
    loadingGroups,
    groupError,
    reloadGroups,
    computeSuggestedMaxScore,
    saveDraft,
  } = useHomeworkConstructor();

  const [assignmentMeta, setAssignmentMeta] = useState(initialMeta);
  const [questions, setQuestions] = useState([]);
  const [showTypeMenu, setShowTypeMenu] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [validationIssues, setValidationIssues] = useState(null);
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [homeworkId, setHomeworkId] = useState(null);
  const [previewQuestion, setPreviewQuestion] = useState(0);
  const [confirmDialog, setConfirmDialog] = useState({ open: false });

  const openConfirmDialog = (config) => {
    setConfirmDialog({
      open: true,
      title: 'Подтверждение',
      message: '',
      confirmLabel: 'Подтвердить',
      cancelLabel: 'Отмена',
      onConfirm: null,
      ...config,
    });
  };

  const closeConfirmDialog = () => {
    setConfirmDialog((previous) => ({ ...previous, open: false }));
  };

  const handleConfirmDialog = () => {
    const action = confirmDialog.onConfirm;
    closeConfirmDialog();
    if (typeof action === 'function') {
      action();
    }
  };

  const handleMetaChange = (field, value) => {
    setAssignmentMeta((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  const handleMaxScoreChange = (value) => {
    const numeric = Number(value);
    handleMetaChange('maxScore', Number.isFinite(numeric) ? numeric : value);
  };

  const handleAutoMaxScore = () => {
    const suggested = computeSuggestedMaxScore(questions);
    if (!suggested) return;
    handleMetaChange('maxScore', suggested);
  };

  const handleAddQuestion = (type) => {
    const template = createQuestionTemplate(type);
    // Генерируем СТАБИЛЬНЫЙ уникальный ID один раз при создании
    template.id = `q-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    template.order = questions.length;
    setQuestions((previous) => [...previous, template]);
    setShowTypeMenu(false);
  };

  const handleUpdateQuestion = (index, nextQuestion) => {
    setQuestions((previous) => {
      const updated = [...previous];
      // Обновляем ТОЛЬКО нужный вопрос, остальные остаются теми же объектами
      updated[index] = { ...nextQuestion, order: index };
      return updated;
    });
  };

  const handleQuestionTextChange = (index, text) => {
    setQuestions((previous) =>
      previous.map((question, questionIndex) =>
        questionIndex === index
          ? { ...question, question_text: text }
          : question
      )
    );
  };

  const handleQuestionPointsChange = (index, value) => {
    const numeric = Number(value);
    setQuestions((previous) =>
      previous.map((question, questionIndex) =>
        questionIndex === index
          ? {
              ...question,
              points: Number.isFinite(numeric) ? numeric : question.points,
            }
          : question
      )
    );
  };

  const handleRemoveQuestion = (index) => {
    openConfirmDialog({
      title: 'Удалить вопрос?',
      message: 'После удаления восстановить вопрос будет нельзя.',
      confirmLabel: 'Удалить',
      onConfirm: () => {
        setQuestions((previous) =>
          previous
            .filter((_, questionIndex) => questionIndex !== index)
            .map((question, order) => ({ ...question, order }))
        );
      },
    });
  };

  const handleDuplicateQuestion = (index) => {
    const source = questions[index];
    if (!source) return;
    const duplicate = {
      ...createQuestionTemplate(source.question_type),
      question_text: source.question_text,
      points: source.points,
      config: JSON.parse(JSON.stringify(source.config || {})),
      correct_answer: Array.isArray(source.correct_answer)
        ? [...source.correct_answer]
        : source.correct_answer,
    };
    setQuestions((previous) => {
      const next = [...previous];
      next.splice(index + 1, 0, duplicate);
      return next.map((question, order) => ({ ...question, order }));
    });
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;
    const reordered = Array.from(questions);
    const [moved] = reordered.splice(result.source.index, 1);
    reordered.splice(result.destination.index, 0, moved);
    setQuestions(reordered.map((question, order) => ({ ...question, order })));
  };

  const questionCount = questions.length;

  const handleSaveDraft = async () => {
    setSaving(true);
    setFeedback(null);
    setValidationIssues(null);
    try {
      const result = await saveDraft(assignmentMeta, questions, homeworkId);
      if (!result.saved) {
        setValidationIssues(result.validation);
        setFeedback({
          status: 'warning',
          message: 'Проверьте настройки — найдено несколько моментов, требующих внимания.',
        });
        return;
      }

      // Сохраняем ID для последующей публикации
      if (result.homeworkId) {
        setHomeworkId(result.homeworkId);
      }

      setFeedback({ status: 'success', message: 'Черновик успешно сохранен.' });
      setValidationIssues(result.validation);
    } catch (error) {
      console.error('[HomeworkConstructor] Save draft failed:', error);
      const backendMessage = error.response?.data?.detail || error.message;
      setFeedback({ status: 'error', message: backendMessage || 'Не удалось сохранить задание.' });
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    // Валидация перед публикацией
    if (!assignmentMeta.title || !assignmentMeta.groupId || questions.length === 0) {
      setFeedback({
        status: 'error',
        message: 'Заполните название, выберите группу и добавьте хотя бы один вопрос',
      });
      setShowPublishModal(false);
      return;
    }

    setSaving(true);
    setFeedback(null);

    try {
      // Сначала сохраняем черновик, если нужно
      let currentHomeworkId = homeworkId;
      
      if (!currentHomeworkId) {
        const saveResult = await saveDraft(assignmentMeta, questions, null);
        if (!saveResult.saved) {
          setValidationIssues(saveResult.validation);
          setFeedback({
            status: 'error',
            message: 'Исправьте ошибки перед публикацией',
          });
          setSaving(false);
          setShowPublishModal(false);
          return;
        }
        currentHomeworkId = saveResult.homeworkId;
        setHomeworkId(currentHomeworkId);
      }

      // Затем публикуем
      await apiClient.post(`/homework/${currentHomeworkId}/publish/`);

      setFeedback({
        status: 'success',
        message: '🎉 ДЗ опубликовано! Студенты получат уведомления.',
      });

      // Redirect через 2 секунды
      setTimeout(() => {
        navigate('/teacher');
      }, 2000);

    } catch (error) {
      console.error('Publish error:', error);
      setFeedback({
        status: 'error',
        message: error.response?.data?.detail || 'Ошибка при публикации ДЗ',
      });
    } finally {
      setSaving(false);
      setShowPublishModal(false);
    }
  };

  const renderValidationDetails = () => {
    if (!validationIssues || validationIssues.ok) {
      return null;
    }

    const { metaIssues = [], questionIssues = [] } = validationIssues;
    if (!metaIssues.length && !questionIssues.length) {
      return null;
    }

    return (
      <ul className="hc-validation-list">
        {metaIssues.map((issue) => (
          <li key={`meta-${issue}`}>{issue}</li>
        ))}
        {questionIssues.map(({ index, issues }) => (
          <li key={`question-${index}`}>
            Вопрос {index + 1}: {issues.join('; ')}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="homework-constructor-page">
      <div className="hc-header">
        <h1 className="hc-header-title">Конструктор домашних заданий</h1>
        <p className="hc-header-subtitle">
          Создавайте, назначайте и проверяйте работы учеников
        </p>
      </div>

      {feedback && (
        <div
          className={`hc-feedback ${
            feedback.status === 'success'
              ? 'hc-feedback-success'
              : feedback.status === 'error'
              ? 'hc-feedback-error'
              : 'hc-feedback-warning'
          }`}
        >
          {feedback.message}
        </div>
      )}

      {renderValidationDetails()}

      <div className="hc-grid">
        <div className="hc-card">
          <div className="hc-section-title">
            <span>Параметры задания</span>
            <div className="hc-inline-fields" style={{ maxWidth: '240px' }}>
              <label className="form-label" style={{ fontSize: '0.75rem' }}>Вопросов: {questionCount}</label>
            </div>
          </div>

          <form className="gm-form" onSubmit={(event) => event.preventDefault()}>
            <div className="form-group">
              <label className="form-label">Название</label>
              <input
                className="form-input"
                value={assignmentMeta.title}
                onChange={(event) => handleMetaChange('title', event.target.value)}
                placeholder="Например: Past Simple revision"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Описание</label>
              <textarea
                className="form-textarea"
                rows={3}
                value={assignmentMeta.description}
                onChange={(event) => handleMetaChange('description', event.target.value)}
                placeholder="Дайте ученикам контекст и пояснение к заданию"
              />
            </div>

            <div className="hc-inline-fields">
              <GroupSelect
                value={assignmentMeta.groupId}
                options={groupOptions}
                onChange={(nextValue) => handleMetaChange('groupId', nextValue)}
                disabled={loadingGroups}
                loading={loadingGroups}
                error={groupError}
                onRetry={reloadGroups}
                placeholder="Выберите группу"
              />

              <div className="form-group">
                <DateTimePicker
                  value={assignmentMeta.deadline}
                  onChange={(nextValue) => handleMetaChange('deadline', nextValue)}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Максимальный балл</label>
              <input
                className="form-input"
                type="number"
                min={1}
                value={assignmentMeta.maxScore}
                onChange={(event) => handleMaxScoreChange(event.target.value)}
              />
              <button type="button" className="gm-btn-surface" onClick={handleAutoMaxScore}>
                Рассчитать по сумме вопросов
              </button>
            </div>

            <div className="gm-actions hc-action-buttons">
              <button
                type="button"
                className="gm-btn-primary"
                onClick={() => setShowPublishModal(true)}
                disabled={saving || questions.length === 0}
              >
                Опубликовать
              </button>
              <button
                type="button"
                className="gm-btn-surface"
                onClick={handleSaveDraft}
                disabled={saving}
              >
                {saving ? 'Сохранение...' : 'Сохранить черновик'}
              </button>
              <button
                type="button"
                className="gm-btn-surface"
                onClick={() => {
                  openConfirmDialog({
                    title: 'Сбросить задание?',
                    message: 'Все текущие настройки будут очищены.',
                    confirmLabel: 'Сбросить',
                    onConfirm: () => {
                      setAssignmentMeta({ ...initialMeta });
                      setQuestions([]);
                      setHomeworkId(null);
                    },
                  });
                }}
                disabled={saving}
              >
                Очистить форму
              </button>
            </div>
          </form>
        </div>

        <div className="hc-card hc-preview-card">
          <div className="hc-section-title">Превью для студентов</div>
          <HomeworkPreviewSection
            questions={questions}
            previewQuestion={previewQuestion}
            onChangePreviewQuestion={setPreviewQuestion}
          />
        </div>
      </div>

      <div className="hc-card">
        <div className="hc-section-title">
          <span>Вопросы ({questionCount})</span>
          <button
            type="button"
            className="hc-add-button"
            onClick={() => setShowTypeMenu((value) => !value)}
          >
            {showTypeMenu ? 'Закрыть меню типов' : '+ Добавить вопрос'}
          </button>
        </div>

        {showTypeMenu && (
          <div className="hc-type-menu">
            {QUESTION_TYPES.map((type) => (
              <button key={type.value} type="button" onClick={() => handleAddQuestion(type.value)}>
                <span>{type.label}</span>
                <span>{type.description}</span>
              </button>
            ))}
          </div>
        )}

        {questionCount === 0 ? (
          <div className="hc-empty-state">
            <strong>Пока вопросов нет.</strong>
            <span>Добавьте первый вопрос, чтобы начать собирать задание.</span>
          </div>
        ) : (
          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="homework-questions">
              {(droppableProvided) => (
                <div
                  className="hc-question-list"
                  ref={droppableProvided.innerRef}
                  {...droppableProvided.droppableProps}
                >
                  {questions.map((question, index) => (
                    <Draggable key={question.id} draggableId={question.id} index={index}>
                      {(draggableProvided, snapshot) => (
                        <div
                          className={`hc-question-card ${snapshot.isDragging ? 'is-dragging' : ''}`}
                          ref={draggableProvided.innerRef}
                          {...draggableProvided.draggableProps}
                        >
                          <div className="hc-question-toolbar">
                            <div className="hc-question-toolbar-left">
                              <span className="hc-question-index">{index + 1}</span>
                              <span className={`hc-question-type-badge ${question.question_type}`}>
                                {getQuestionIcon(question.question_type)} {getQuestionLabel(question.question_type).replace(/^[^\s]+\s/, '')}
                              </span>
                            </div>
                            <div className="hc-question-actions">
                              <button
                                type="button"
                                className="gm-btn-icon"
                                {...draggableProvided.dragHandleProps}
                                aria-label="Переместить вопрос"
                              >
                                ⋮⋮
                              </button>
                              <button
                                type="button"
                                className="gm-btn-surface"
                                onClick={() => handleDuplicateQuestion(index)}
                              >
                                Дублировать
                              </button>
                              <button
                                type="button"
                                className="gm-btn-danger"
                                onClick={() => handleRemoveQuestion(index)}
                              >
                                Удалить
                              </button>
                            </div>
                          </div>

                          <div className="form-group">
                            <label className="form-label">Формулировка вопроса</label>
                            <textarea
                              className="form-textarea"
                              rows={3}
                              value={question.question_text}
                              onChange={(event) => handleQuestionTextChange(index, event.target.value)}
                              placeholder="Опишите задание для ученика"
                            />
                          </div>

                          <div className="form-group" style={{ maxWidth: '160px' }}>
                            <label className="form-label">Баллы</label>
                            <input
                              className="form-input"
                              type="number"
                              min={1}
                              value={question.points}
                              onChange={(event) => handleQuestionPointsChange(index, event.target.value)}
                            />
                          </div>

                          <HomeworkQuestionEditor
                            question={question}
                            index={index}
                            onUpdateQuestion={handleUpdateQuestion}
                          />
                        </div>
                      )}
                    </Draggable>
                  ))}
                  {droppableProvided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>
        )}
      </div>

      {/* Модальное окно подтверждения публикации */}
      {showPublishModal && (
        <div className="hc-modal-overlay" onClick={() => setShowPublishModal(false)}>
          <div className="hc-modal-content" onClick={e => e.stopPropagation()}>
            <h3>Опубликовать домашнее задание?</h3>
            <p>После публикации:</p>
            <ul>
              <li>✉️ Все студенты группы получат уведомление</li>
              <li>📱 Уведомления придут в Telegram (если привязан)</li>
              <li>⏰ Начнется отсчет до дедлайна</li>
              <li>🔒 Редактирование будет ограничено</li>
            </ul>
            <div className="hc-modal-buttons">
              <button className="gm-btn-primary" onClick={handlePublish} disabled={saving}>
                {saving ? 'Публикация...' : 'Да, опубликовать'}
              </button>
              <button className="gm-btn-surface" onClick={() => setShowPublishModal(false)} disabled={saving}>
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmDialog.open && (
        <div className="hc-modal-overlay" onClick={closeConfirmDialog}>
          <div className="hc-modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>{confirmDialog.title}</h3>
            {confirmDialog.message && <p>{confirmDialog.message}</p>}
            <div className="hc-modal-buttons">
              <button type="button" className="gm-btn-surface" onClick={closeConfirmDialog}>
                {confirmDialog.cancelLabel}
              </button>
              <button type="button" className="gm-btn-primary" onClick={handleConfirmDialog}>
                {confirmDialog.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HomeworkConstructor;
