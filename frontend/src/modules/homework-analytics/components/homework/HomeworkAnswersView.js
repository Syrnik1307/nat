import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Modal } from '../../../../shared/components';
import { apiClient } from '../../../../apiService';
import MediaPreview from '../shared/MediaPreview';
import './HomeworkAnswersView.css';

// Нормализация URL для картинок (включая Google Drive)
const normalizeUrl = (url) => {
  if (!url) return '';
  
  if (url.includes('drive.google.com')) {
    let fileId = null;
    const ucMatch = url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
    if (ucMatch) fileId = ucMatch[1];
    const fileMatch = url.match(/\/file\/d\/([a-zA-Z0-9_-]+)/);
    if (fileMatch) fileId = fileMatch[1];
    if (fileId) return `https://lh3.googleusercontent.com/d/${fileId}`;
  }
  
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  if (url.startsWith('/media')) return url;
  return `/media/${url}`;
};

const HomeworkAnswersView = () => {
  const { id } = useParams(); // homework ID
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [imagePreview, setImagePreview] = useState({ open: false, url: '' });

  useEffect(() => {
    const fetchAnswers = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.get(`/homework/${id}/my-answers/`);
        setData(response.data);
      } catch (err) {
        const msg = err.response?.data?.error || err.response?.data?.detail || 'Не удалось загрузить ответы';
        setError(msg);
      } finally {
        setLoading(false);
      }
    };
    fetchAnswers();
  }, [id]);

  const questions = useMemo(() => data?.questions || [], [data]);
  const answers = useMemo(() => {
    if (!data?.answers) return {};
    // Convert array to map by question_id
    const map = {};
    data.answers.forEach(a => {
      map[a.question_id] = a;
    });
    return map;
  }, [data]);

  const currentQuestion = questions[currentIndex];
  const currentAnswer = currentQuestion ? answers[currentQuestion.id] : null;

  const formatTimeSpent = (seconds) => {
    if (!seconds) return null;
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    const parts = [];
    if (hours > 0) parts.push(`${hours} ч`);
    if (minutes > 0) parts.push(`${minutes} мин`);
    if (secs > 0 && hours === 0) parts.push(`${secs} сек`);
    
    return parts.join(' ') || '< 1 сек';
  };

  const getAnswerDisplay = (question, answer) => {
    if (!answer) {
      return { text: 'Нет ответа', isCorrect: null };
    }

    const qType = question.question_type;

    if (qType === 'TEXT') {
      return { 
        text: answer.text_answer || 'Пустой ответ',
        isCorrect: answer.is_correct,
        score: answer.score,
        maxScore: question.points,
      };
    }

    if (qType === 'SINGLE_CHOICE' || qType === 'MULTIPLE_CHOICE') {
      const selectedText = answer.selected_choices_text?.join(', ') || 'Нет ответа';
      return { 
        text: selectedText, 
        isCorrect: answer.is_correct,
        score: answer.score,
        maxScore: question.points,
      };
    }

    if (qType === 'FILL_BLANKS' || qType === 'MATCHING' || qType === 'DRAG_DROP' || qType === 'LISTENING' || qType === 'HOTSPOT' || qType === 'CODE') {
      // For complex types, show JSON or formatted text
      try {
        const parsed = typeof answer.text_answer === 'string' 
          ? JSON.parse(answer.text_answer)
          : answer.text_answer;
        return { 
          text: Array.isArray(parsed) ? parsed.join(', ') : JSON.stringify(parsed, null, 2),
          isCorrect: answer.is_correct,
          score: answer.score,
          maxScore: question.points,
        };
      } catch {
        return { 
          text: answer.text_answer || 'Нет ответа',
          isCorrect: answer.is_correct,
          score: answer.score,
          maxScore: question.points,
        };
      }
    }

    return { text: answer.text_answer || 'Нет ответа', isCorrect: answer.is_correct };
  };

  if (loading) {
    return (
      <div className="hav-container">
        <div className="hav-state">Загрузка ответов...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="hav-container">
        <div className="hav-state hav-error">
          <p>{error}</p>
          <Button onClick={() => navigate('/homework')}>К списку заданий</Button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="hav-container">
        <div className="hav-state">Нет данных</div>
      </div>
    );
  }

  const answerInfo = currentQuestion ? getAnswerDisplay(currentQuestion, currentAnswer) : null;

  return (
    <div className="hav-container">
      <Modal
        isOpen={imagePreview.open}
        onClose={() => setImagePreview({ open: false, url: '' })}
        title="Изображение"
        size="large"
        closeOnBackdrop
        footer={<Button variant="secondary" onClick={() => setImagePreview({ open: false, url: '' })}>Закрыть</Button>}
      >
        {imagePreview.url && (
          <div className="hav-image-modal">
            <img src={normalizeUrl(imagePreview.url)} alt="Изображение" />
          </div>
        )}
      </Modal>

      <header className="hav-header">
        <div className="hav-header-primary">
          <h1 className="hav-title">{data.homework_title}</h1>
          <p className="hav-subtitle">Просмотр ваших ответов</p>
        </div>
        <div className="hav-header-meta">
          <div className="hav-score">
            <span className="hav-score-value">{data.total_score ?? 0}</span>
            <span className="hav-score-divider">/</span>
            <span className="hav-score-max">{data.max_score ?? 0}</span>
            <span className="hav-score-label">баллов</span>
          </div>
          {data.time_spent_seconds && (
            <div className="hav-time">
              Время: {formatTimeSpent(data.time_spent_seconds)}
            </div>
          )}
        </div>
      </header>

      <div className="hav-layout">
        <aside className="hav-sidebar">
          <div className="hav-nav">
            {questions.map((q, idx) => {
              const answer = answers[q.id];
              const isCorrect = answer?.is_correct;
              let dotClass = 'hav-nav-dot';
              if (isCorrect === true) dotClass += ' correct';
              else if (isCorrect === false) dotClass += ' incorrect';
              else dotClass += ' pending';
              if (idx === currentIndex) dotClass += ' current';
              
              return (
                <button
                  key={q.id}
                  className={dotClass}
                  onClick={() => setCurrentIndex(idx)}
                  title={`Вопрос ${idx + 1}`}
                >
                  {idx + 1}
                </button>
              );
            })}
          </div>
          <div className="hav-legend">
            <span><span className="hav-legend-dot correct" /> Правильно</span>
            <span><span className="hav-legend-dot incorrect" /> Неправильно</span>
            <span><span className="hav-legend-dot pending" /> На проверке</span>
          </div>
        </aside>

        <main className="hav-main">
          {questions.length === 0 ? (
            <div className="hav-state">Нет вопросов в этом задании.</div>
          ) : currentQuestion ? (
            <div className="hav-question-card">
              <div className="hav-question-header">
                <span className="hav-question-index">Вопрос {currentIndex + 1} из {questions.length}</span>
                {currentQuestion.points > 0 && (
                  <span className="hav-question-points">
                    {answerInfo?.score ?? 0} / {currentQuestion.points} баллов
                  </span>
                )}
              </div>

              {/* Текст вопроса */}
              {currentQuestion.prompt && (
                <h2 className="hav-question-text">{currentQuestion.prompt}</h2>
              )}

              {/* Изображение вопроса */}
              {currentQuestion.config?.imageUrl && (
                <div 
                  className="hav-question-image"
                  onClick={() => setImagePreview({ open: true, url: currentQuestion.config.imageUrl })}
                >
                  <MediaPreview 
                    type="image"
                    src={currentQuestion.config.imageUrl} 
                    alt="Изображение к вопросу"
                  />
                </div>
              )}

              {/* Ваш ответ */}
              <div className={`hav-answer-block ${answerInfo?.isCorrect === true ? 'correct' : answerInfo?.isCorrect === false ? 'incorrect' : ''}`}>
                <div className="hav-answer-label">Ваш ответ:</div>
                <div className="hav-answer-text">{answerInfo?.text}</div>
                {answerInfo?.isCorrect === true && (
                  <div className="hav-answer-badge correct">Правильно</div>
                )}
                {answerInfo?.isCorrect === false && (
                  <div className="hav-answer-badge incorrect">Неправильно</div>
                )}
              </div>

              {/* Комментарий учителя */}
              {currentAnswer?.teacher_feedback && (
                <div className="hav-feedback">
                  <div className="hav-feedback-label">Комментарий преподавателя:</div>
                  <div className="hav-feedback-text">{currentAnswer.teacher_feedback}</div>
                </div>
              )}

              {/* Пояснение с правильным ответом */}
              {(currentQuestion.explanation || currentQuestion.config?.explanationImageUrl) && (
                <div className="hav-explanation">
                  <div className="hav-explanation-label">Пояснение:</div>
                  {currentQuestion.explanation && (
                    <div className="hav-explanation-text">{currentQuestion.explanation}</div>
                  )}
                  {currentQuestion.config?.explanationImageUrl && (
                    <div className="hav-explanation-image">
                      <img src={currentQuestion.config.explanationImageUrl} alt="Пояснение" />
                    </div>
                  )}
                </div>
              )}

              <div className="hav-controls">
                <Button
                  variant="secondary"
                  onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
                  disabled={currentIndex === 0}
                >
                  Назад
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setCurrentIndex(Math.min(questions.length - 1, currentIndex + 1))}
                  disabled={currentIndex === questions.length - 1}
                >
                  Далее
                </Button>
              </div>
            </div>
          ) : (
            <div className="hav-state">Вопрос не найден.</div>
          )}

          <footer className="hav-footer">
            <Button onClick={() => navigate('/homework')}>Назад к списку заданий</Button>
          </footer>
        </main>
      </div>
    </div>
  );
};

export default HomeworkAnswersView;
