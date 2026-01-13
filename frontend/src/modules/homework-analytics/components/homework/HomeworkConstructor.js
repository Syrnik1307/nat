import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { apiClient, uploadHomeworkFile } from '../../../../apiService';
import { Modal, Button } from '../../../../shared/components';
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
  const [uploadingImageFor, setUploadingImageFor] = useState(null); // index вопроса

  // Обработка вставки изображения прямо в карточку вопроса
  const handleCardPaste = useCallback(async (event, questionIndex) => {
    const clipboardData = event.clipboardData || window.clipboardData;
    if (!clipboardData) return;

    const items = clipboardData.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith('image/')) {
        event.preventDefault();
        const file = item.getAsFile();
        if (file) {
          setUploadingImageFor(questionIndex);
          try {
            const response = await uploadHomeworkFile(file, 'image');
            if (response.data?.url) {
              setQuestions((prev) => {
                const updated = [...prev];
                const q = updated[questionIndex];
                updated[questionIndex] = {
                  ...q,
                  config: { ...q.config, imageUrl: response.data.url }
                };
                return updated;
              });
              setFeedback({ type: 'success', message: 'Изображение загружено' });
              setTimeout(() => setFeedback(null), 2000);
            }
          } catch (err) {
            setFeedback({ type: 'error', message: 'Ошибка загрузки: ' + (err.message || 'Попробуйте ещё раз') });
          } finally {
            setUploadingImageFor(null);
          }
        }
        break;
      }
    }
  }, []);

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

      {/* Sticky панель с действиями */}
      <div className="hc-sticky-actions">
        <div className="hc-sticky-actions-left">
          <span className="hc-stats-badge">{questionCount} вопрос{questionCount === 1 ? '' : questionCount >= 2 && questionCount <= 4 ? 'а' : 'ов'}</span>
          {assignmentMeta.title && <span className="hc-stats-badge hc-stats-title">{assignmentMeta.title.slice(0, 30)}{assignmentMeta.title.length > 30 ? '...' : ''}</span>}
        </div>
        <div className="hc-sticky-actions-right">
          <button
            type="button"
            className="gm-btn-surface hc-action-btn"
            onClick={handleSaveDraft}
            disabled={saving}
          >
            {saving ? 'Сохранение...' : 'Черновик'}
          </button>
          <button
            type="button"
            className="gm-btn-primary hc-action-btn"
            onClick={() => setShowPublishModal(true)}
            disabled={saving || questions.length === 0}
          >
            Опубликовать
          </button>
        </div>
      </div>

      <div className="hc-main-layout">
        {/* Левая колонка — параметры */}
        <div className="hc-sidebar">
          <div className="hc-card hc-params-card">
            <div className="hc-section-title">Параметры</div>
            
            <form className="gm-form hc-compact-form" onSubmit={(event) => event.preventDefault()}>
              <div className="form-group">
                <label className="form-label">Название задания</label>
                <input
                  className="form-input hc-input-large"
                  value={assignmentMeta.title}
                  onChange={(event) => handleMetaChange('title', event.target.value)}
                  placeholder="Например: Past Simple revision"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Описание (опционально)</label>
                <textarea
                  className="form-textarea"
                  rows={2}
                  value={assignmentMeta.description}
                  onChange={(event) => handleMetaChange('description', event.target.value)}
                  placeholder="Инструкции для учеников"
                />
              </div>

              <div className="hc-params-row">
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
              </div>

              <div className="hc-params-row">
                <div className="form-group" style={{ flex: 1 }}>
                  <DateTimePicker
                    value={assignmentMeta.deadline}
                    onChange={(nextValue) => handleMetaChange('deadline', nextValue)}
                  />
                </div>
                <div className="form-group hc-score-field">
                  <label className="form-label">Макс. балл</label>
                  <div className="hc-score-input-wrap">
                    <input
                      className="form-input"
                      type="number"
                      min={1}
                      value={assignmentMeta.maxScore}
                      onChange={(event) => handleMaxScoreChange(event.target.value)}
                    />
                    <button type="button" className="hc-auto-score-btn" onClick={handleAutoMaxScore} title="Рассчитать по сумме вопросов">
                      ↻
                    </button>
                  </div>
                </div>
              </div>

              <button
                type="button"
                className="hc-reset-btn"
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
                Очистить
              </button>
            </form>
          </div>
        </div>

        {/* Правая колонка — вопросы */}
        <div className="hc-questions-area">

      <div className="hc-card">
        <div className="hc-section-title">
          <span>Вопросы ({questionCount})</span>
          <button
            type="button"
            className="hc-add-button"
            onClick={() => setShowTypeMenu((value) => !value)}
          >
            {showTypeMenu ? 'Скрыть' : '+ Добавить'}
          </button>
        </div>

        {showTypeMenu && (
          <div className="hc-type-menu">
            {QUESTION_TYPES.map((type) => (
              <button key={type.value} type="button" onClick={() => handleAddQuestion(type.value)} className="hc-type-btn">
                {type.label}
              </button>
            ))}
          </div>
        )}

        {questionCount === 0 ? (
          <div className="hc-empty-state">
            Нажмите «+ Добавить» чтобы создать первый вопрос
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
                          className={`hc-question-card ${snapshot.isDragging ? 'is-dragging' : ''} ${uploadingImageFor === index ? 'is-uploading' : ''}`}
                          ref={draggableProvided.innerRef}
                          {...draggableProvided.draggableProps}
                          onPaste={(e) => handleCardPaste(e, index)}
                          tabIndex={0}
                        >
                          {uploadingImageFor === index && (
                            <div className="hc-upload-overlay">
                              <div className="hc-upload-spinner" />
                              <span>Загрузка...</span>
                            </div>
                          )}
                          
                          <div className="hc-question-toolbar">
                            <div className="hc-question-toolbar-left">
                              <span className="hc-question-index">{index + 1}</span>
                              <span className="hc-question-type-badge">
                                {getQuestionLabel(question.question_type)}
                              </span>
                            </div>
                            <div className="hc-question-actions">
                              <button
                                type="button"
                                className="hc-btn-text"
                                {...draggableProvided.dragHandleProps}
                              >
                                ⋮⋮
                              </button>
                              <button
                                type="button"
                                className="hc-btn-text"
                                onClick={() => handleDuplicateQuestion(index)}
                              >
                                Копия
                              </button>
                              <button
                                type="button"
                                className="hc-btn-text hc-btn-text-danger"
                                onClick={() => handleRemoveQuestion(index)}
                              >
                                Удалить
                              </button>
                            </div>
                          </div>

                          <div className="form-group">
                            <textarea
                              className="form-textarea"
                              rows={2}
                              value={question.question_text}
                              onChange={(event) => handleQuestionTextChange(index, event.target.value)}
                              placeholder="Текст вопроса"
                            />
                          </div>

                          {/* Кнопка добавления изображения */}
                          <div className="hc-image-section">
                            {!question.config?.imageUrl ? (
                              <div className="hc-image-actions">
                                <label className="hc-image-upload-btn">
                                  <input
                                    type="file"
                                    accept="image/*"
                                    style={{ display: 'none' }}
                                  onChange={async (e) => {
                                    const file = e.target.files?.[0];
                                    if (!file) return;
                                    setUploadingImageFor(index);
                                    try {
                                      const response = await uploadHomeworkFile(file, 'image');
                                      if (response.data?.url) {
                                        setQuestions((prev) => {
                                          const updated = [...prev];
                                          updated[index] = {
                                            ...updated[index],
                                            config: { ...updated[index].config, imageUrl: response.data.url }
                                          };
                                          return updated;
                                        });
                                      }
                                    } catch (err) {
                                      setFeedback({ type: 'error', message: 'Ошибка загрузки: ' + (err.message || '') });
                                    } finally {
                                      setUploadingImageFor(null);
                                      e.target.value = '';
                                    }
                                  }}
                                />
                                {uploadingImageFor === index ? 'Загрузка...' : '+ Выбрать файл'}
                              </label>
                                <span className="hc-paste-hint">или Ctrl+V</span>
                              </div>
                            ) : (
                              <div className="hc-image-preview-inline">
                                <img src={question.config.imageUrl} alt="" />
                                <button
                                  type="button"
                                  className="hc-image-remove-btn"
                                  onClick={() => {
                                    setQuestions((prev) => {
                                      const updated = [...prev];
                                      updated[index] = {
                                        ...updated[index],
                                        config: { ...updated[index].config, imageUrl: null }
                                      };
                                      return updated;
                                    });
                                  }}
                                >
                                  Удалить фото
                                </button>
                              </div>
                            )}
                          </div>

                          <div className="hc-question-meta">
                            <div className="form-group hc-points-field">
                              <label className="form-label">Баллы</label>
                              <input
                                className="form-input"
                                type="number"
                                min={1}
                                value={question.points}
                                onChange={(event) => handleQuestionPointsChange(index, event.target.value)}
                              />
                            </div>
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
        </div>
      </div>

      {/* Модальное окно подтверждения публикации */}
      <Modal
        isOpen={showPublishModal}
        onClose={() => setShowPublishModal(false)}
        title="Опубликовать домашнее задание?"
        size="small"
        footer={(
          <>
            <Button variant="secondary" onClick={() => setShowPublishModal(false)} disabled={saving}>
              Отмена
            </Button>
            <Button onClick={handlePublish} disabled={saving}>
              {saving ? 'Публикация...' : 'Да, опубликовать'}
            </Button>
          </>
        )}
      >
        <p style={{ margin: '0 0 0.75rem 0', color: 'var(--text-secondary)' }}>После публикации:</p>
        <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <li>✉️ Все студенты группы получат уведомление</li>
          <li>📱 Уведомления придут в Telegram (если привязан)</li>
          <li>⏰ Начнется отсчет до дедлайна</li>
          <li>🔒 Редактирование будет ограничено</li>
        </ul>
      </Modal>

      <Modal
        isOpen={confirmDialog.open}
        onClose={closeConfirmDialog}
        title={confirmDialog.title}
        size="small"
        footer={(
          <>
            <Button variant="secondary" onClick={closeConfirmDialog}>
              {confirmDialog.cancelLabel}
            </Button>
            <Button onClick={handleConfirmDialog}>
              {confirmDialog.confirmLabel}
            </Button>
          </>
        )}
      >
        {confirmDialog.message && (
          <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{confirmDialog.message}</p>
        )}
      </Modal>
    </div>
  );
};

export default HomeworkConstructor;
