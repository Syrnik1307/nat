import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { apiClient, uploadHomeworkFile, saveAsTemplate, preloadImageCompressor } from '../../../../apiService';
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
import CodeQuestion from '../questions/CodeQuestion';
import '../questions/CodeQuestion.css';
import './HomeworkConstructor.css';
import DateTimePicker from './DateTimePicker';
import StudentPicker from './StudentPicker';

const initialMeta = {
  title: '',
  description: '',
  groupId: '',
  groupAssignments: [], // [{groupId, studentIds: [], allStudents: bool}]
  deadline: '',
  maxScore: 100,
  gamificationEnabled: true,
  studentInstructions: '',
  allowViewAnswers: true,
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
  CODE: CodeQuestion,
};

// Нормализация URL для картинок (включая Google Drive)
const normalizeUrl = (url) => {
  if (!url) return '';
  
  // Конвертация Google Drive ссылок для inline отображения
  if (url.includes('drive.google.com')) {
    let fileId = null;
    
    // Формат: /uc?export=download&id=FILE_ID или /uc?id=FILE_ID
    const ucMatch = url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
    if (ucMatch) {
      fileId = ucMatch[1];
    }
    
    // Формат: /file/d/FILE_ID/view
    const fileMatch = url.match(/\/file\/d\/([a-zA-Z0-9_-]+)/);
    if (fileMatch) {
      fileId = fileMatch[1];
    }
    
    if (fileId) {
      return `https://lh3.googleusercontent.com/d/${fileId}`;
    }
  }
  
  // Blob URL или полный URL
  if (url.startsWith('blob:') || url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  
  if (url.startsWith('/media')) {
    return url;
  }
  
  return `/media/${url}`;
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

const HomeworkConstructor = ({ editingHomework = null, isDuplicating = false, onClearEditing = null }) => {
  const navigate = useNavigate();
  const {
    groups,
    loadingGroups,
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
  const [uploadProgress, setUploadProgress] = useState(0); // прогресс загрузки 0-100
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [isPublished, setIsPublished] = useState(false);
  const blobUrlsRef = useRef(new Set());

  // Предзагрузка компрессора изображений при монтировании
  useEffect(() => {
    preloadImageCompressor();
  }, []);

  // Загрузка данных из editingHomework (редактирование или дублирование)
  useEffect(() => {
    if (editingHomework) {
      // Если дублирование - создаём копию без ID
      // Если редактирование - загружаем с ID
      
      // Конвертация назначений в новый формат
      let groupAssignments = [];
      if (editingHomework.group_assignments && editingHomework.group_assignments.length > 0) {
        // Новый формат с детализацией по ученикам
        groupAssignments = editingHomework.group_assignments.map(ga => ({
          groupId: ga.group_id,
          studentIds: ga.student_ids || [],
          allStudents: ga.all_students !== false,
        }));
      } else if (editingHomework.assigned_groups && editingHomework.assigned_groups.length > 0) {
        // Старый формат - только группы
        groupAssignments = editingHomework.assigned_groups.map(g => ({
          groupId: g.id || g,
          studentIds: [],
          allStudents: true,
        }));
      }
      
      const meta = {
        title: isDuplicating ? `${editingHomework.title} (копия)` : editingHomework.title || '',
        description: editingHomework.description || '',
        groupId: editingHomework.assigned_groups?.[0]?.id || editingHomework.assigned_groups?.[0] || '',
        groupAssignments,
        deadline: editingHomework.deadline ? editingHomework.deadline.slice(0, 16) : '',
        maxScore: editingHomework.max_score || 100,
        gamificationEnabled: editingHomework.gamification_enabled !== false,
        studentInstructions: editingHomework.student_instructions || '',
        allowViewAnswers: editingHomework.allow_view_answers !== false,
      };
      
      setAssignmentMeta(meta);
      
      // Загружаем вопросы с их конфигурацией
      if (editingHomework.questions && editingHomework.questions.length > 0) {
        const loadedQuestions = editingHomework.questions.map((q, idx) => ({
          id: isDuplicating ? `q-${Date.now()}-${Math.random().toString(36).substr(2, 9)}` : (q.id || `q-${idx}`),
          question_type: q.question_type || 'TEXT',
          question_text: q.question_text || '',
          points: q.points || 1,
          order: q.order || idx,
          config: q.config || {},
          correct_answer: q.correct_answer,
        }));
        setQuestions(loadedQuestions);
      }
      
      // Устанавливаем ID для редактирования (не для дублирования)
      if (!isDuplicating && editingHomework.id) {
        setHomeworkId(editingHomework.id);
        setIsEditMode(true);
        // Проверяем статус - если опубликовано, показываем кнопку "Сохранить"
        setIsPublished(editingHomework.status === 'published');
      } else {
        setHomeworkId(null);
        setIsEditMode(false);
        setIsPublished(false);
      }
      
      // Показываем уведомление
      setFeedback({
        status: 'info',
        message: isDuplicating 
          ? 'Создание копии ДЗ. Измените название и сохраните.'
          : editingHomework.status === 'published'
            ? 'Редактирование опубликованного ДЗ. Нажмите "Сохранить" для применения изменений.'
            : 'Режим редактирования ДЗ. После изменений нажмите "Сохранить".',
      });
    }
  }, [editingHomework, isDuplicating]);

  // Сброс при размонтировании или очистке
  const handleClearEditing = useCallback(() => {
    if (onClearEditing) {
      onClearEditing();
    }
    setAssignmentMeta(initialMeta);
    setQuestions([]);
    setHomeworkId(null);
    setIsEditMode(false);
    setIsPublished(false);
    setFeedback(null);
  }, [onClearEditing]);

  useEffect(() => {
    return () => {
      blobUrlsRef.current.forEach((url) => {
        try {
          URL.revokeObjectURL(url);
        } catch (_) {
          // ignore
        }
      });
      blobUrlsRef.current.clear();
    };
  }, []);

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
          const localUrl = URL.createObjectURL(file);
          blobUrlsRef.current.add(localUrl);

          // Мгновенный preview до завершения загрузки
          setQuestions((prev) => {
            const updated = [...prev];
            const q = updated[questionIndex];
            const previousUrl = q?.config?.imageUrl;
            if (previousUrl && previousUrl.startsWith('blob:') && previousUrl !== localUrl) {
              try {
                URL.revokeObjectURL(previousUrl);
              } catch (_) {
                // ignore
              }
              blobUrlsRef.current.delete(previousUrl);
            }
            updated[questionIndex] = {
              ...q,
              config: { ...q.config, imageUrl: localUrl, imageFileId: null }
            };
            return updated;
          });

          setUploadingImageFor(questionIndex);
          setUploadProgress(0);
          try {
            const response = await uploadHomeworkFile(file, 'image', (percent) => {
              setUploadProgress(percent);
            });
            if (response.data?.url) {
              setQuestions((prev) => {
                const updated = [...prev];
                const q = updated[questionIndex];
                const previousUrl = q?.config?.imageUrl;
                if (previousUrl && previousUrl.startsWith('blob:')) {
                  try {
                    URL.revokeObjectURL(previousUrl);
                  } catch (_) {
                    // ignore
                  }
                  blobUrlsRef.current.delete(previousUrl);
                }
                updated[questionIndex] = {
                  ...q,
                  config: { ...q.config, imageUrl: response.data.url, imageFileId: response.data.file_id || null }
                };
                return updated;
              });
            }
          } catch (err) {
            setFeedback({ type: 'error', message: 'Ошибка загрузки: ' + (err.message || 'Попробуйте ещё раз') });
          } finally {
            setUploadingImageFor(null);
            setUploadProgress(0);
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
    template.order = 0; // Новый вопрос добавляется в начало UI
    // Добавляем в начало массива для удобства редактирования (не нужно скроллить вверх)
    setQuestions((previous) => [template, ...previous]);
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

  // Сохранение изменений для уже опубликованного ДЗ
  const handleSaveChanges = async () => {
    if (!assignmentMeta.title || questions.length === 0) {
      setFeedback({
        status: 'error',
        message: 'Заполните название и добавьте хотя бы один вопрос',
      });
      return;
    }

    setSaving(true);
    setFeedback(null);

    try {
      const result = await saveDraft(assignmentMeta, questions, homeworkId);
      if (!result.saved) {
        setValidationIssues(result.validation);
        setFeedback({
          status: 'warning',
          message: 'Проверьте настройки задания',
        });
        return;
      }
      
      setHomeworkId(result.homeworkId);
      setFeedback({
        status: 'success',
        message: 'Изменения сохранены!',
      });
    } catch (err) {
      setFeedback({
        status: 'error',
        message: err.response?.data?.detail || 'Ошибка сохранения',
      });
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
        message: 'ДЗ опубликовано! Студенты получат уведомления.',
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
        <h1 className="hc-header-title">
          {isEditMode ? 'Редактирование ДЗ' : isDuplicating ? 'Создание копии ДЗ' : 'Конструктор домашних заданий'}
        </h1>
        <p className="hc-header-subtitle">
          {isEditMode 
            ? 'Внесите изменения и сохраните' 
            : 'Создавайте, назначайте и проверяйте работы учеников'
          }
        </p>
      </div>

      {feedback && (
        <div
          className={`hc-feedback ${
            feedback.status === 'success'
              ? 'hc-feedback-success'
              : feedback.status === 'error'
              ? 'hc-feedback-error'
              : feedback.status === 'info'
              ? 'hc-feedback-info'
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
          {(isEditMode || isDuplicating) && (
            <button
              type="button"
              className="gm-btn-surface hc-action-btn hc-new-btn"
              onClick={handleClearEditing}
            >
              Новое ДЗ
            </button>
          )}
          <span className="hc-stats-badge">{questionCount} вопрос{questionCount === 1 ? '' : questionCount >= 2 && questionCount <= 4 ? 'а' : 'ов'}</span>
          {assignmentMeta.title && <span className="hc-stats-badge hc-stats-title">{assignmentMeta.title.slice(0, 30)}{assignmentMeta.title.length > 30 ? '...' : ''}</span>}
        </div>
        <div className="hc-sticky-actions-right">
          <button
            type="button"
            className="gm-btn-surface hc-action-btn"
            onClick={async () => {
              setSavingTemplate(true);
              setFeedback(null);
              try {
                // Сначала сохраняем как черновик, потом делаем шаблон
                  const result = await saveDraft(assignmentMeta, questions, homeworkId, { requireGroup: false });
                if (!result.saved) {
                  setValidationIssues(result.validation);
                  setFeedback({ status: 'warning', message: 'Проверьте настройки задания' });
                  return;
                }
                const savedId = result.homeworkId;
                setHomeworkId(savedId);
                await saveAsTemplate(savedId);
                setFeedback({ status: 'success', message: 'Шаблон создан! Перейдите во вкладку Шаблоны.' });
              } catch (err) {
                setFeedback({ status: 'error', message: err.response?.data?.detail || 'Ошибка сохранения шаблона' });
              } finally {
                setSavingTemplate(false);
              }
            }}
            disabled={savingTemplate || questions.length === 0}
          >
            {savingTemplate ? 'Сохранение...' : 'Создать шаблон'}
          </button>
          {isEditMode && isPublished ? (
            // Для опубликованного ДЗ показываем кнопку "Сохранить"
            <button
              type="button"
              className="gm-btn-primary hc-action-btn"
              onClick={handleSaveChanges}
              disabled={saving || questions.length === 0}
            >
              {saving ? 'Сохранение...' : 'Сохранить изменения'}
            </button>
          ) : (
            // Для нового или черновика - кнопка "Опубликовать"
            <button
              type="button"
              className="gm-btn-primary hc-action-btn"
              onClick={() => setShowPublishModal(true)}
              disabled={saving || questions.length === 0}
            >
              Опубликовать
            </button>
          )}
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

              <div className="form-group">
                <label className="form-label">Общие инструкции для ДЗ (опционально)</label>
                <textarea
                  className="form-textarea"
                  rows={2}
                  value={assignmentMeta.studentInstructions}
                  onChange={(event) => handleMetaChange('studentInstructions', event.target.value)}
                  placeholder="Общие инструкции, которые увидит ученик перед началом выполнения всего ДЗ"
                />
              </div>

              <div className="form-group hc-checkbox-group">
                <label className="hc-checkbox-label">
                  <input
                    type="checkbox"
                    checked={assignmentMeta.allowViewAnswers}
                    onChange={(event) => handleMetaChange('allowViewAnswers', event.target.checked)}
                  />
                  <span>Разрешить просмотр ответов после сдачи</span>
                </label>
                <span className="hc-checkbox-hint">Отключите для контрольных работ, чтобы ученики не могли делиться ответами</span>
              </div>

              <div className="hc-params-row">
                <StudentPicker
                  value={assignmentMeta.groupAssignments}
                  onChange={(assignments) => handleMetaChange('groupAssignments', assignments)}
                  groups={groups}
                  disabled={loadingGroups}
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
                              <div className="hc-upload-progress-container">
                                <div className="hc-upload-progress-bar" style={{ width: `${uploadProgress}%` }} />
                              </div>
                              <span>{uploadProgress > 0 ? `Загрузка ${uploadProgress}%` : 'Подготовка...'}</span>
                            </div>
                          )}
                          
                          <div className="hc-question-toolbar">
                            <div className="hc-question-toolbar-left">
                              <span className="hc-question-index">{questions.length - index}</span>
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

                                    const localUrl = URL.createObjectURL(file);
                                    blobUrlsRef.current.add(localUrl);

                                    // Мгновенный preview до завершения загрузки
                                    setQuestions((prev) => {
                                      const updated = [...prev];
                                      const q = updated[index];
                                      const previousUrl = q?.config?.imageUrl;
                                      if (previousUrl && previousUrl.startsWith('blob:') && previousUrl !== localUrl) {
                                        try {
                                          URL.revokeObjectURL(previousUrl);
                                        } catch (_) {
                                          // ignore
                                        }
                                        blobUrlsRef.current.delete(previousUrl);
                                      }
                                      updated[index] = {
                                        ...q,
                                        config: {
                                          ...q.config,
                                          imageUrl: localUrl,
                                          imageFileId: null,
                                        }
                                      };
                                      return updated;
                                    });

                                    setUploadingImageFor(index);
                                    setUploadProgress(0);
                                    try {
                                      const response = await uploadHomeworkFile(file, 'image', (percent) => {
                                        setUploadProgress(percent);
                                      });
                                      if (response.data?.url) {
                                        setQuestions((prev) => {
                                          const updated = [...prev];
                                          const q = updated[index];
                                          const previousUrl = q?.config?.imageUrl;
                                          if (previousUrl && previousUrl.startsWith('blob:')) {
                                            try {
                                              URL.revokeObjectURL(previousUrl);
                                            } catch (_) {
                                              // ignore
                                            }
                                            blobUrlsRef.current.delete(previousUrl);
                                          }
                                          updated[index] = {
                                            ...q,
                                            config: {
                                              ...q.config,
                                              imageUrl: response.data.url,
                                              imageFileId: response.data.file_id || null,
                                            }
                                          };
                                          return updated;
                                        });
                                      }
                                    } catch (err) {
                                      setFeedback({ type: 'error', message: 'Ошибка загрузки: ' + (err.message || '') });
                                    } finally {
                                      setUploadingImageFor(null);
                                      setUploadProgress(0);
                                      e.target.value = '';
                                    }
                                  }}
                                />
                                {uploadingImageFor === index ? (uploadProgress > 0 ? `${uploadProgress}%` : 'Загрузка...') : '+ Выбрать файл'}
                              </label>
                                <span className="hc-paste-hint">или Ctrl+V</span>
                              </div>
                            ) : (
                              <div className="hc-image-preview-inline">
                                <img src={normalizeUrl(question.config.imageUrl)} alt="" />
                                <button
                                  type="button"
                                  className="hc-image-remove-btn"
                                  onClick={() => {
                                    setQuestions((prev) => {
                                      const updated = [...prev];
                                      const previousUrl = updated[index]?.config?.imageUrl;
                                      if (previousUrl && previousUrl.startsWith('blob:')) {
                                        try {
                                          URL.revokeObjectURL(previousUrl);
                                        } catch (_) {
                                          // ignore
                                        }
                                        blobUrlsRef.current.delete(previousUrl);
                                      }
                                      updated[index] = {
                                        ...updated[index],
                                        config: { ...updated[index].config, imageUrl: null, imageFileId: null }
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

                          <div className="form-group hc-explanation-field">
                            <label className="form-label">Пояснение для ученика (опционально)</label>
                            <textarea
                              className="form-textarea"
                              rows={2}
                              value={question.explanation || ''}
                              onChange={(event) => {
                                const newValue = event.target.value;
                                setQuestions((prev) => {
                                  const updated = [...prev];
                                  updated[index] = { ...updated[index], explanation: newValue };
                                  return updated;
                                });
                              }}
                              placeholder="Дополнительные инструкции, которые увидит ученик под этим вопросом"
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
