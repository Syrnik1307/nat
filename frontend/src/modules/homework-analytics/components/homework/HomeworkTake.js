import React, { useEffect, useMemo, useState } from 'react';
import Confetti from '../gamification/Confetti';
import { useNavigate, useParams } from 'react-router-dom';
import useHomeworkSession from '../../hooks/useHomeworkSession';
import QuestionRenderer from '../student/QuestionRenderer';
import QuestionAttachments from './QuestionAttachments';
import ProgressBar from '../student/ProgressBar';
import QuestionNav from '../student/QuestionNav';
import './HomeworkTake.css';

const HomeworkTake = () => {
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
    reload,
  } = useHomeworkSession(id);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [resultData, setResultData] = useState(null);

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
    if (!window.confirm('Отправить домашнее задание? После отправки редактирование будет недоступно.')) {
      return;
    }
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
    if (savingState.status === 'saving') return 'Сохранение...';
    if (savingState.status === 'saved') return 'Сохранено';
    if (savingState.status === 'error') return 'Ошибка автосохранения';
    return 'Черновик';
  }, [savingState.status]);

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
          <button type="button" className="gm-btn-primary" onClick={reload}>
            Повторить загрузку
          </button>
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

  return (
    <div className="ht-container">
      {showResult && (
        <div className="ht-modal ht-result-modal">
          {resultData?.score >= 90 && <Confetti />}
          <div className="ht-result-content">
            <h2 className="ht-result-title">Результаты</h2>
            <div className="ht-result-score">
              <span>Ваш результат:</span>
              <strong>{resultData?.score ?? '—'} баллов</strong>
            </div>
            {resultData?.percent != null && (
              <div className="ht-result-percent">{resultData.percent}% правильных ответов</div>
            )}
            <div className="ht-result-actions">
              <button className="gm-btn-primary" onClick={() => navigate('/homework')}>К списку заданий</button>
              <button className="gm-btn-surface" onClick={() => setShowResult(false)}>Закрыть</button>
              {resultData?.showAnswers && (
                <button className="gm-btn-outline" onClick={() => navigate(`/homework/${id}/answers`)}>Посмотреть правильные ответы</button>
              )}
            </div>
          </div>
        </div>
      )}
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
                <span className="ht-question-type">{currentQuestion.question_type}</span>
              </div>
              <h2 className="ht-question-text">{currentQuestion.question_text}</h2>

              {/* Вложения вопроса (только чтение для студента) */}
              {currentQuestion.id && (
                <QuestionAttachments
                  questionId={currentQuestion.id}
                  readOnly={true}
                />
              )}

              <QuestionRenderer
                question={currentQuestion}
                answer={answers[currentQuestion.id]}
                onChange={(value) => recordAnswer(currentQuestion.id, value)}
              />

              <div className="ht-controls">
                <button
                  type="button"
                  className="gm-btn-surface"
                  onClick={() => setCurrentIndex((index) => Math.max(0, index - 1))}
                  disabled={currentIndex === 0}
                >
                  ← Назад
                </button>
                <button
                  type="button"
                  className="gm-btn-surface"
                  onClick={() => setCurrentIndex((index) => Math.min(questions.length - 1, index + 1))}
                  disabled={currentIndex === questions.length - 1}
                >
                  Далее →
                </button>
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
              <button
                type="button"
                className="gm-btn-surface"
                onClick={() => navigate('/homework')}
                disabled={submitting}
              >
                Назад к списку
              </button>
              <button
                type="button"
                className="gm-btn-primary"
                onClick={handleSubmit}
                disabled={submitting}
              >
                {submitting ? 'Отправка...' : 'Завершить и отправить'}
              </button>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
};

export default HomeworkTake;
