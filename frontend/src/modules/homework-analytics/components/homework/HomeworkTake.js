import React, { useEffect, useMemo, useState } from 'react';
import Confetti from '../gamification/Confetti';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Modal, Notification, ConfirmModal } from '../../../../shared/components';
import useNotification from '../../../../shared/hooks/useNotification';
import useHomeworkSession from '../../hooks/useHomeworkSession';
import QuestionRenderer from '../student/QuestionRenderer';
import ProgressBar from '../student/ProgressBar';
import QuestionNav from '../student/QuestionNav';
import MediaPreview from '../shared/MediaPreview';
import AnswerAttachment from '../student/AnswerAttachment';
import { preloadAdjacentQuestionImages } from '../../../../utils/imagePreloader';
import './HomeworkTake.css';

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
  
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  // Абсолютные пути на нашем сервере — возвращаем как есть
  if (url.startsWith('/')) {
    return url;
  }
  return `/media/${url}`;
};

// Иконка для типа файла
const getFileIcon = (filename) => {
  if (!filename) return 'FILE';
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

const HomeworkTake = () => {
  const { notification, confirm, closeNotification, showConfirm, closeConfirm } = useNotification();
  const { id } = useParams();
  const navigate = useNavigate();
  const {
    loading,
    error,
    homework,
    answers,
    recordAnswer,
    submitHomework,
    savingState,
    progress,
    isLocked,
    submission,
    reload,
  } = useHomeworkSession(id);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [resultData, setResultData] = useState(null);
  const [imagePreview, setImagePreview] = useState({ open: false, url: '' });

  const questions = useMemo(() => homework?.questions || [], [homework?.questions]);
  const currentQuestion = questions[currentIndex];

  // Preload соседних изображений при переключении вопроса
  useEffect(() => {
    if (questions.length > 0) {
      preloadAdjacentQuestionImages(questions, currentIndex);
    }
  }, [currentIndex, questions]);

  useEffect(() => {
    if (currentIndex >= questions.length) {
      setCurrentIndex(Math.max(0, questions.length - 1));
    }
  }, [currentIndex, questions.length]);

  useEffect(() => {
    const handleBeforeUnload = (event) => {
      if (savingState.status === 'saving') {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [savingState.status]);

  // ============================================================================
  // SUBMIT HANDLER - оптимизирован для мобильных устройств
  // ============================================================================
  const handleSubmit = async () => {
    // Предотвращаем двойной клик
    if (submitting) {
      return;
    }
    
    if (isLocked) {
      return;
    }
    
    const confirmed = await showConfirm({
      title: 'Отправить домашнее задание?',
      message: 'После отправки редактирование будет недоступно.',
      variant: 'warning',
      confirmText: 'Отправить',
      cancelText: 'Отмена'
    });
    
    if (!confirmed) return;
    
    try {
      setSubmitting(true);
      setSubmitMessage('Отправляем...');
      
      const result = await submitHomework();
      
      // Проверяем что результат валидный
      if (result === null) {
        // submitHomework вернул null = уже идёт отправка, игнорируем
        return;
      }
      
      setResultData(result?.data || result || null);
      setShowResult(true);
      setSubmitMessage('Задание успешно отправлено!');
      
    } catch (submitError) {
      console.error('[HomeworkTake] submit error:', submitError);
      
      // Детальные сообщения для разных типов ошибок
      let errorMessage;
      
      // Сетевые ошибки (нет response)
      if (!submitError.response) {
        if (submitError.code === 'ECONNABORTED') {
          errorMessage = 'Время ожидания истекло. Проверьте интернет и попробуйте снова.';
        } else if (submitError.message?.toLowerCase().includes('network')) {
          errorMessage = 'Нет подключения к интернету. Проверьте сеть и попробуйте снова.';
        } else {
          errorMessage = 'Не удалось связаться с сервером. Проверьте интернет-соединение.';
        }
      }
      // HTTP ошибки
      else {
        const status = submitError.response.status;
        const serverError = submitError.response.data?.error || submitError.response.data?.detail;
        
        switch (status) {
          case 400:
            errorMessage = serverError || 'Работа уже была отправлена ранее.';
            break;
          case 401:
            errorMessage = 'Сессия истекла. Обновите страницу и войдите снова.';
            break;
          case 403:
            errorMessage = serverError || 'Нет доступа к этому заданию.';
            break;
          case 404:
            errorMessage = 'Задание не найдено. Возможно, оно было удалено.';
            break;
          case 429:
            errorMessage = 'Слишком много запросов. Подождите минуту и попробуйте снова.';
            break;
          case 500:
          case 502:
          case 503:
          case 504:
            errorMessage = 'Ошибка сервера. Попробуйте через несколько минут.';
            break;
          default:
            errorMessage = serverError || 'Произошла ошибка. Попробуйте снова.';
        }
      }
      
      setSubmitMessage(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const savingLabel = useMemo(() => {
    if (submission?.status === 'submitted') return 'Отправлено';
    if (submission?.status === 'graded') return 'Проверено';
    if (savingState.status === 'saving') return 'Сохранение...';
    if (savingState.status === 'saved') return 'Сохранено';
    if (savingState.status === 'error') return 'Ошибка автосохранения';
    return 'Черновик';
  }, [savingState.status, submission?.status]);

  if (loading) {
    return (
      <div className="ht-container">
        <div className="ht-state ht-loading">Загружаем домашнее задание...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ht-container">
        <div className="ht-state ht-error">
          <p>{error}</p>
          <Button onClick={reload}>Повторить загрузку</Button>
        </div>
      </div>
    );
  }

  if (!homework) {
    return (
      <div className="ht-container">
        <div className="ht-state ht-error">Нет данных о задании. Попробуйте обновить страницу.</div>
      </div>
    );
  }

  // Calculate percentage for confetti
  const resultPercent = resultData?.max_score > 0 
    ? Math.round((resultData.total_score / resultData.max_score) * 100) 
    : 0;

  return (
    <div className="ht-container">
      
      {showResult && resultData?.status === 'graded' && resultPercent >= 90 && <Confetti />}
      <Modal
        isOpen={showResult}
        onClose={() => setShowResult(false)}
        title="Результаты"
        size="small"
        closeOnBackdrop
        footer={(
          <>
            <Button variant="secondary" onClick={() => setShowResult(false)}>
              Закрыть
            </Button>
            {resultData?.showAnswers ? (
              <Button variant="secondary" onClick={() => navigate(`/homework/${id}/answers`)}>
                Посмотреть ответы
              </Button>
            ) : null}
            <Button onClick={() => navigate('/homework')}>К списку заданий</Button>
          </>
        )}
      >
        <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
          {resultData?.status === 'submitted' ? (
            <>Ваша работа <strong>отправлена на проверку</strong>. Баллы появятся после проверки учителем.</>
          ) : resultData?.status === 'graded' ? (
            <>
              Ваш результат: <strong>{resultData?.total_score ?? 0} из {resultData?.max_score ?? '?'} баллов</strong>
              {resultData?.max_score > 0 && (
                <>
                  <br />
                  {Math.round((resultData.total_score / resultData.max_score) * 100)}% правильных ответов
                </>
              )}
            </>
          ) : (
            <>Ваш результат: <strong>{resultData?.total_score ?? '—'} баллов</strong></>
          )}
        </p>
      </Modal>

      <Modal
        isOpen={imagePreview.open}
        onClose={() => setImagePreview({ open: false, url: '' })}
        title="Изображение"
        size="large"
        closeOnBackdrop
        footer={(
          <>
            <Button variant="secondary" onClick={() => setImagePreview({ open: false, url: '' })}>
              Закрыть
            </Button>
            {imagePreview.url ? (
              <a
                className="gm-btn-primary"
                href={normalizeUrl(imagePreview.url)}
                target="_blank"
                rel="noreferrer"
              >
                Открыть в новой вкладке
              </a>
            ) : null}
          </>
        )}
      >
        {imagePreview.url ? (
          <div className="ht-image-modal">
            <img className="ht-image-modal-img" src={normalizeUrl(imagePreview.url)} alt="Изображение" />
          </div>
        ) : null}
      </Modal>
      <header className="ht-header">
        <div className="ht-header-primary">
          <h1 className="ht-title">{homework.title}</h1>
          <p className="ht-subtitle">{homework.description || 'Выполните все вопросы, затем отправьте работу.'}</p>
          {homework.student_instructions && (
            <div className="ht-instructions">
              <strong>Пояснение от преподавателя:</strong>
              <p>{homework.student_instructions}</p>
            </div>
          )}
        </div>
        <div className="ht-header-meta">
          <ProgressBar percent={progress} />
          <span className={`ht-saving-indicator ${savingState.status}`}>{savingLabel}</span>
        </div>
      </header>

      <div className="ht-layout">
        <aside className="ht-sidebar">
          <QuestionNav
            questions={questions}
            currentIndex={currentIndex}
            answers={answers}
            onSelect={(index) => setCurrentIndex(index)}
          />
          <div className="ht-sidebar-hint">
            <span>Навигация по вопросам:</span>
            <ul>
              <li><span className="ht-nav-dot current" /> — текущий</li>
              <li><span className="ht-nav-dot answered" /> — выполнен</li>
              <li><span className="ht-nav-dot pending" /> — не выполнен</li>
            </ul>
          </div>
        </aside>

        <main className="ht-main">
          {questions.length === 0 ? (
            <div className="ht-state ht-empty">Нет вопросов в этом задании.</div>
          ) : currentQuestion ? (
            <div className="ht-question-card">
              <div className="ht-question-header">
                <span className="ht-question-index">Вопрос {currentIndex + 1} из {questions.length}</span>
                {currentQuestion.points > 0 && (
                  <span className="ht-question-points">Баллы: {currentQuestion.points}</span>
                )}
              </div>

              {/* Текст вопроса (если есть) - показываем ПЕРЕД картинкой */}
              {(currentQuestion.question_text || currentQuestion.prompt) && (
                <h2 className="ht-question-text">{currentQuestion.question_text || currentQuestion.prompt}</h2>
              )}

              {/* Пояснение с правильным ответом - показываем ТОЛЬКО после сдачи */}
              {isLocked && (currentQuestion.explanation || currentQuestion.config?.explanationImageUrl) && (
                <div className="ht-question-explanation">
                  <span className="ht-explanation-label">Пояснение:</span>
                  {currentQuestion.explanation && <p>{currentQuestion.explanation}</p>}
                  {currentQuestion.config?.explanationImageUrl && (
                    <div className="ht-explanation-image">
                      <img src={currentQuestion.config.explanationImageUrl} alt="Пояснение" />
                    </div>
                  )}
                </div>
              )}

              {/* Изображение вопроса (если есть) */}
              {currentQuestion.config?.imageUrl && (
                <div 
                  className="ht-question-image"
                  onClick={() => setImagePreview({ open: true, url: currentQuestion.config.imageUrl })}
                >
                  <MediaPreview 
                    key={`img-${currentQuestion.id}`}
                    type="image"
                    src={currentQuestion.config.imageUrl} 
                    alt="Изображение к вопросу"
                  />
                </div>
              )}

              {/* Прикреплённый документ (если есть) */}
              {currentQuestion.config?.attachmentUrl && (
                <div className="ht-question-attachment">
                  <a
                    href={currentQuestion.config.attachmentUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ht-attachment-link"
                  >
                    <span className="ht-attachment-icon">
                      {getFileIcon(currentQuestion.config.attachmentName)}
                    </span>
                    <span className="ht-attachment-name">
                      {currentQuestion.config.attachmentName || 'Документ'}
                    </span>
                    {currentQuestion.config.attachmentSize && (
                      <span className="ht-attachment-size">
                        ({formatFileSize(currentQuestion.config.attachmentSize)})
                      </span>
                    )}
                  </a>
                </div>
              )}

              <QuestionRenderer
                question={currentQuestion}
                answer={answers[currentQuestion.id]}
                onChange={(value) => {
                  if (!isLocked) {
                    recordAnswer(currentQuestion.id, value);
                  }
                }}
                disabled={isLocked}
                homeworkId={id}
              />

              {/* Прикрепление файлов к ответу (для всех типов кроме FILE_UPLOAD) */}
              {currentQuestion.question_type !== 'FILE_UPLOAD' && (
                <AnswerAttachment
                  attachments={answers[`${currentQuestion.id}_attachments`] || []}
                  onChange={(files) => {
                    if (!isLocked) {
                      recordAnswer(`${currentQuestion.id}_attachments`, files);
                    }
                  }}
                  disabled={isLocked}
                  homeworkId={id}
                  maxFiles={3}
                  maxSizeMB={10}
                />
              )}

              <div className="ht-controls">
                <Button
                  variant="secondary"
                  onClick={() => setCurrentIndex((index) => Math.max(0, index - 1))}
                  disabled={currentIndex === 0 || isLocked}
                >
                  ← Назад
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setCurrentIndex((index) => Math.min(questions.length - 1, index + 1))}
                  disabled={currentIndex === questions.length - 1 || isLocked}
                >
                  Далее →
                </Button>
              </div>
            </div>
          ) : (
            <div className="ht-state ht-empty">Вопрос не найден.</div>
          )}

          <footer className="ht-footer">
            <div className="ht-footer-info">
              {submitMessage && <span className="ht-submit-message">{submitMessage}</span>}
              {isLocked && submission?.status === 'submitted' && (
                <span className="ht-submit-message ht-locked-info">
                  Работа уже отправлена и ожидает проверки
                </span>
              )}
              {isLocked && submission?.status === 'graded' && (
                <span className="ht-submit-message ht-locked-info">
                  Работа проверена. Посмотрите результаты ниже
                </span>
              )}
            </div>
            <div className="ht-footer-actions">
              <Button
                variant="secondary"
                onClick={() => navigate('/homework')}
                disabled={submitting}
              >
                Назад к списку
              </Button>
              {isLocked ? (
                <Button
                  variant="secondary"
                  onClick={() => navigate(`/homework/${id}/result`)}
                >
                  Посмотреть результаты
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="ht-submit-btn"
                >
                  {submitting ? 'Отправка...' : 'Завершить и отправить'}
                </Button>
              )}
            </div>
          </footer>
        </main>
      </div>

      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />

      <ConfirmModal
        isOpen={confirm.isOpen}
        onClose={closeConfirm}
        onConfirm={confirm.onConfirm}
        title={confirm.title}
        message={confirm.message}
        variant={confirm.variant}
        confirmText={confirm.confirmText}
        cancelText={confirm.cancelText}
      />
    </div>
  );
};

export default HomeworkTake;
