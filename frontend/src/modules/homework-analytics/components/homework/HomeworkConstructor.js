import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { apiClient, uploadHomeworkFile, uploadHomeworkDocument, preloadImageCompressor } from '../../../../apiService';
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
import FileUploadQuestion from '../questions/FileUploadQuestion';
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
  FILE_UPLOAD: FileUploadQuestion,
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
  
  // Абсолютные пути на нашем домене (включая /api/... и /media/...)
  if (url.startsWith('/')) {
    return url;
  }
  
  // Относительные пути без слэша добавляем /media/
  return `/media/${url}`;
};

// Иконка для типа файла
const getFileIcon = (filename) => {
  if (!filename) return 'file';
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return 'PDF';
    case 'doc':
    case 'docx':
      return 'DOC';
    case 'xls':
    case 'xlsx':
      return 'XLS';
    case 'ppt':
    case 'pptx':
      return 'PPT';
    case 'zip':
    case 'rar':
    case '7z':
      return 'ZIP';
    case 'txt':
      return 'TXT';
    case 'csv':
      return 'CSV';
    default:
      return 'FILE';
  }
};

// Форматирование размера файла
const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
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

      case 'FILE_UPLOAD':
        return (
          <div className="preview-question">
            <p>{currentQuestion.question_text || 'Текст вопроса не заполнен'}</p>
            {currentQuestion.config?.instructions && (
              <p className="preview-note">{currentQuestion.config.instructions}</p>
            )}
            <div style={{ 
              padding: '24px', 
              border: '2px dashed var(--border-color, #e5e7eb)', 
              borderRadius: '8px',
              textAlign: 'center',
              color: 'var(--text-muted, #9ca3af)'
            }}>
              Зона загрузки файла (до {currentQuestion.config?.maxSizeMB || 10} MB)
            </div>
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
    setQuestions((previous) => {
      const newQuestions = [template, ...previous];
      // Автообновление суммы баллов
      const newMaxScore = computeSuggestedMaxScore(newQuestions);
      if (newMaxScore > 0) {
        setAssignmentMeta((prevMeta) => ({ ...prevMeta, maxScore: newMaxScore }));
      }
      return newQuestions;
    });
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
    setQuestions((previous) => {
      const updated = previous.map((question, questionIndex) =>
        questionIndex === index
          ? {
              ...question,
              points: Number.isFinite(numeric) ? numeric : question.points,
            }
          : question
      );
      // Автообновление суммы баллов
      const newMaxScore = computeSuggestedMaxScore(updated);
      if (newMaxScore > 0) {
        setAssignmentMeta((prevMeta) => ({ ...prevMeta, maxScore: newMaxScore }));
      }
      return updated;
    });
  };

  const handleRemoveQuestion = (index) => {
    openConfirmDialog({
      title: 'Удалить вопрос?',
      message: 'После удаления восстановить вопрос будет нельзя.',
      confirmLabel: 'Удалить',
      onConfirm: () => {
        setQuestions((previous) => {
          const filtered = previous
            .filter((_, questionIndex) => questionIndex !== index)
            .map((question, order) => ({ ...question, order }));
          // Автообновление суммы баллов
          const newMaxScore = computeSuggestedMaxScore(filtered);
          setAssignmentMeta((prevMeta) => ({ ...prevMeta, maxScore: newMaxScore > 0 ? newMaxScore : 100 }));
          return filtered;
        });
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
      const reordered = next.map((question, order) => ({ ...question, order }));
      // Автообновление суммы баллов
      const newMaxScore = computeSuggestedMaxScore(reordered);
      if (newMaxScore > 0) {
        setAssignmentMeta((prevMeta) => ({ ...prevMeta, maxScore: newMaxScore }));
      }
      return reordered;
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
    const hasGroupAssignments = assignmentMeta.groupAssignments && assignmentMeta.groupAssignments.length > 0;
    const hasLegacyGroupId = !!assignmentMeta.groupId;
    
    if (!assignmentMeta.title || (!hasGroupAssignments && !hasLegacyGroupId) || questions.length === 0) {
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
        <div className="hc-sticky-actions-right" data-tour="hw-actions">
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
              <div className="form-group" data-tour="hw-title">
                <label className="form-label">Название задания</label>
                <input
                  className="form-input hc-input-large"
                  value={assignmentMeta.title}
                  onChange={(event) => handleMetaChange('title', event.target.value)}
                  placeholder="Например: Past Simple revision"
                />
              </div>

              <div className="form-group" data-tour="hw-description">
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

              <div className="hc-params-row hc-params-row--picker" data-tour="hw-group-selector">
                <div className="hc-params-row-fill">
                  <StudentPicker
                    value={assignmentMeta.groupAssignments}
                    onChange={(assignments) => handleMetaChange('groupAssignments', assignments)}
                    groups={groups}
                    disabled={loadingGroups}
                  />
                </div>
              </div>

              <div className="hc-params-row">
                <div className="form-group" style={{ flex: 1 }} data-tour="hw-deadline">
                  <DateTimePicker
                    value={assignmentMeta.deadline}
                    onChange={(nextValue) => handleMetaChange('deadline', nextValue)}
                  />
                </div>
                <div className="form-group hc-score-field" data-tour="hw-max-score">
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

      <div className="hc-card" data-tour="hw-questions-panel">
        <div className="hc-section-title">
          <span>Вопросы ({questionCount})</span>
          <button
            type="button"
            className="hc-add-button"
            onClick={() => setShowTypeMenu((value) => !value)}
            data-tour="hw-add-question"
          >
            {showTypeMenu ? 'Скрыть' : '+ Добавить'}
          </button>
        </div>

        {showTypeMenu && (
          <div className="hc-type-menu" data-tour="hw-type-menu">
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

                          {/* Секция загрузки файлов (изображения + документы) */}
                          <div className="hc-attachment-section" data-tour="hw-question-attachments">
                            {/* Изображение */}
                            {!question.config?.imageUrl ? (
                              <div className="hc-attachment-actions">
                                <label className="hc-attachment-upload-btn hc-attachment-image">
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
                                  {uploadingImageFor === index ? (uploadProgress > 0 ? `${uploadProgress}%` : 'Загрузка...') : '+ Фото'}
                                </label>
                                
                                {/* Документ */}
                                {!question.config?.attachmentUrl && (
                                  <label className="hc-attachment-upload-btn hc-attachment-document">
                                    <input
                                      type="file"
                                      accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip,.rar,.7z"
                                      style={{ display: 'none' }}
                                      onChange={async (e) => {
                                        const file = e.target.files?.[0];
                                        if (!file) return;
                                        
                                        // Проверка размера (100 MB max)
                                        if (file.size > 100 * 1024 * 1024) {
                                          setFeedback({ type: 'error', message: 'Файл слишком большой. Максимум: 100 MB' });
                                          e.target.value = '';
                                          return;
                                        }

                                        setUploadingImageFor(index);
                                        setUploadProgress(0);
                                        try {
                                          const response = await uploadHomeworkDocument(file, (percent) => {
                                            setUploadProgress(percent);
                                          });
                                          if (response.data?.url) {
                                            setQuestions((prev) => {
                                              const updated = [...prev];
                                              updated[index] = {
                                                ...updated[index],
                                                config: {
                                                  ...updated[index].config,
                                                  attachmentUrl: response.data.url,
                                                  attachmentFileId: response.data.file_id || null,
                                                  attachmentName: response.data.file_name || file.name,
                                                  attachmentSize: response.data.size || file.size,
                                                }
                                              };
                                              return updated;
                                            });
                                            setFeedback({ type: 'success', message: `Файл "${file.name}" загружен` });
                                          }
                                        } catch (err) {
                                          const errMsg = err.response?.data?.detail || err.message || 'Попробуйте ещё раз';
                                          setFeedback({ type: 'error', message: 'Ошибка загрузки: ' + errMsg });
                                        } finally {
                                          setUploadingImageFor(null);
                                          setUploadProgress(0);
                                          e.target.value = '';
                                        }
                                      }}
                                    />
                                    {uploadingImageFor === index ? (uploadProgress > 0 ? `${uploadProgress}%` : 'Загрузка...') : '+ Файл'}
                                  </label>
                                )}
                                <span className="hc-paste-hint">или Ctrl+V для фото</span>
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
                            
                            {/* Прикреплённый документ */}
                            {question.config?.attachmentUrl && (
                              <div className="hc-attachment-preview">
                                <div className="hc-attachment-info">
                                  <span className="hc-attachment-icon">
                                    {getFileIcon(question.config.attachmentName)}
                                  </span>
                                  <a
                                    href={question.config.attachmentUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="hc-attachment-link"
                                  >
                                    {question.config.attachmentName || 'Документ'}
                                  </a>
                                  <span className="hc-attachment-size">
                                    {formatFileSize(question.config.attachmentSize)}
                                  </span>
                                </div>
                                <button
                                  type="button"
                                  className="hc-attachment-remove-btn"
                                  onClick={() => {
                                    setQuestions((prev) => {
                                      const updated = [...prev];
                                      updated[index] = {
                                        ...updated[index],
                                        config: {
                                          ...updated[index].config,
                                          attachmentUrl: null,
                                          attachmentFileId: null,
                                          attachmentName: null,
                                          attachmentSize: null,
                                        }
                                      };
                                      return updated;
                                    });
                                  }}
                                >
                                  Удалить
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
                            <label className="form-label">Пояснение / правильный ответ (опционально)</label>
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
                              placeholder="Ученик увидит это после проверки (например: Правильный ответ: went, т.к. Past Simple...)"
                            />
                            
                            {/* Изображение для пояснения */}
                            <div className="hc-explanation-image">
                              {!question.config?.explanationImageUrl ? (
                                <label className="hc-explanation-image-btn">
                                  <input
                                    type="file"
                                    accept="image/*"
                                    style={{ display: 'none' }}
                                    onChange={async (e) => {
                                      const file = e.target.files?.[0];
                                      if (!file) return;
                                      
                                      const localUrl = URL.createObjectURL(file);
                                      blobUrlsRef.current.add(localUrl);
                                      
                                      // Мгновенный preview
                                      setQuestions((prev) => {
                                        const updated = [...prev];
                                        updated[index] = {
                                          ...updated[index],
                                          config: {
                                            ...updated[index].config,
                                            explanationImageUrl: localUrl,
                                            explanationImageFileId: null,
                                          }
                                        };
                                        return updated;
                                      });
                                      
                                      try {
                                        const response = await uploadHomeworkFile(file, 'image');
                                        if (response.data?.url) {
                                          setQuestions((prev) => {
                                            const updated = [...prev];
                                            const previousUrl = updated[index]?.config?.explanationImageUrl;
                                            if (previousUrl?.startsWith('blob:')) {
                                              URL.revokeObjectURL(previousUrl);
                                              blobUrlsRef.current.delete(previousUrl);
                                            }
                                            updated[index] = {
                                              ...updated[index],
                                              config: {
                                                ...updated[index].config,
                                                explanationImageUrl: response.data.url,
                                                explanationImageFileId: response.data.file_id || null,
                                              }
                                            };
                                            return updated;
                                          });
                                        }
                                      } catch (err) {
                                        setFeedback({ type: 'error', message: 'Ошибка загрузки: ' + (err.message || '') });
                                      }
                                      e.target.value = '';
                                    }}
                                  />
                                  Добавить изображение
                                </label>
                              ) : (
                                <div className="hc-explanation-image-preview">
                                  <img src={normalizeUrl(question.config.explanationImageUrl)} alt="Пояснение" />
                                  <button
                                    type="button"
                                    className="hc-explanation-image-remove"
                                    onClick={() => {
                                      setQuestions((prev) => {
                                        const updated = [...prev];
                                        const previousUrl = updated[index]?.config?.explanationImageUrl;
                                        if (previousUrl?.startsWith('blob:')) {
                                          URL.revokeObjectURL(previousUrl);
                                          blobUrlsRef.current.delete(previousUrl);
                                        }
                                        updated[index] = {
                                          ...updated[index],
                                          config: {
                                            ...updated[index].config,
                                            explanationImageUrl: null,
                                            explanationImageFileId: null,
                                          }
                                        };
                                        return updated;
                                      });
                                    }}
                                  >
                                    Удалить
                                  </button>
                                </div>
                              )}
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
          <li>Все студенты группы получат уведомление</li>
          <li>Уведомления придут в Telegram (если привязан)</li>
          <li>Начнется отсчет до дедлайна</li>
          <li>Редактирование будет ограничено</li>
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
