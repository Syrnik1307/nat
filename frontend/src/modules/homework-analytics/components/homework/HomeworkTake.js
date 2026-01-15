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
import './HomeworkTake.css';

// Нормализация URL для картинок
const normalizeUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  if (url.startsWith('/media')) {
    return url;
  }
  return `/media/${url}`;
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

  const questions = homework?.questions || [];
  const currentQuestion = questions[currentIndex];

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

  const handleSubmit = async () => {
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
      setSubmitMessage(null);
      const result = await submitHomework();
      setResultData(result?.data || null);
      setShowResult(true);
      setSubmitMessage('Задание отправлено!');
    } catch (submitError) {
      console.error('[HomeworkTake] submit error:', submitError);
      setSubmitMessage('Не удалось отправить задание. Попробуйте снова.');
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
              {/* Изображение вопроса (если есть) */}
              {currentQuestion.config?.imageUrl && (
                <div 
                  className="ht-question-image"
                  onClick={() => setImagePreview({ open: true, url: currentQuestion.config.imageUrl })}
                >
                  <MediaPreview 
                    type="image"
                    src={currentQuestion.config.imageUrl} 
                    alt="Изображение к вопросу"
                  />
                </div>
              )}

              {currentQuestion.question_text && (
                <h2 className="ht-question-text">{currentQuestion.question_text}</h2>
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
              />

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
            </div>
            <div className="ht-footer-actions">
              <Button
                variant="secondary"
                onClick={() => navigate('/homework')}
                disabled={submitting}
              >
                Назад к списку
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={submitting || isLocked}
              >
                {submitting ? 'Отправка...' : 'Завершить и отправить'}
              </Button>
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
