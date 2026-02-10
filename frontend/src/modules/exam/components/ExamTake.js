/**
 * ExamTake — страница прохождения экзамена учеником.
 *
 * Включает:
 * - Строгий таймер с авто-сдачей при истечении
 * - Навигационная панель по заданиям
 * - Специализированные поля ввода по answer_type
 * - Автосохранение ответов
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../../../shared/components';
import * as examService from '../services/examService';
import { formatTime, ANSWER_TYPE_LABELS } from '../services/examService';
import ExamAnswerInput from './ExamAnswerInputs';

export default function ExamTake() {
  const { attemptId } = useParams();
  const navigate = useNavigate();

  const [attempt, setAttempt] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({}); // {taskNumber: value}
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [timeLeft, setTimeLeft] = useState(null);
  const [flagged, setFlagged] = useState(new Set());

  const timerRef = useRef(null);
  const saveTimerRef = useRef(null);
  const pendingSave = useRef(false);

  // --- Load attempt data ---
  useEffect(() => {
    (async () => {
      try {
        const data = await examService.getAttempt(attemptId);
        setAttempt(data);

        if (data.submission?.status === 'graded' || data.submission?.status === 'submitted') {
          setSubmitted(true);
          setLoading(false);
          return;
        }

        // Если ещё не начат — стартуем
        if (!data.started_at) {
          const started = await examService.startExam(attemptId);
          setAttempt(prev => ({ ...prev, ...started }));
        }

        // Загрузка заданий (из варианта)
        const variant = await examService.getVariant(data.variant?.id || data.variant);
        setTasks(variant.tasks_detail || variant.variant_tasks || []);

        // Восстановление ответов из submission
        if (data.submission?.answers) {
          const restored = {};
          data.submission.answers.forEach(a => {
            if (a.question_task_number != null) {
              restored[a.question_task_number] = a.text_answer || '';
            }
          });
          setAnswers(restored);
        }
      } catch (err) {
        console.error('Failed to load exam:', err);
      } finally {
        setLoading(false);
      }
    })();
  }, [attemptId]);

  // --- Timer ---
  useEffect(() => {
    if (!attempt?.deadline_at || submitted) return;

    const tick = () => {
      const deadline = new Date(attempt.deadline_at).getTime();
      const now = Date.now();
      const remaining = Math.max(0, Math.floor((deadline - now) / 1000));
      setTimeLeft(remaining);

      if (remaining <= 0) {
        handleAutoSubmit();
      }
    };

    tick();
    timerRef.current = setInterval(tick, 1000);

    return () => clearInterval(timerRef.current);
  }, [attempt?.deadline_at, submitted]);

  // Sync with server every 60 seconds
  useEffect(() => {
    if (!attempt?.id || submitted) return;

    const sync = setInterval(async () => {
      try {
        const timerData = await examService.getTimer(attemptId);
        if (timerData.remaining_seconds != null) {
          setTimeLeft(timerData.remaining_seconds);
        }
        if (timerData.auto_submitted) {
          setSubmitted(true);
        }
      } catch { /* ignore */ }
    }, 60000);

    return () => clearInterval(sync);
  }, [attemptId, attempt?.id, submitted]);

  // --- Auto-save ---
  const saveAnswers = useCallback(async () => {
    if (!attempt?.submission?.id || submitted) return;
    pendingSave.current = false;

    try {
      const { apiClient } = await import('../../../apiService');
      await apiClient.patch(`submissions/${attempt.submission.id}/answer/`, {
        answers: Object.entries(answers).map(([taskNumber, value]) => ({
          question_task_number: Number(taskNumber),
          text_answer: typeof value === 'string' ? value : JSON.stringify(value),
        })),
      });
    } catch (err) {
      console.error('Auto-save failed:', err);
    }
  }, [answers, attempt?.submission?.id, submitted]);

  // Debounced save
  useEffect(() => {
    pendingSave.current = true;
    clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      if (pendingSave.current) saveAnswers();
    }, 3000);

    return () => clearTimeout(saveTimerRef.current);
  }, [answers, saveAnswers]);

  // Save on unmount
  useEffect(() => {
    return () => {
      if (pendingSave.current) saveAnswers();
    };
  }, [saveAnswers]);

  // --- Handlers ---
  const handleAnswerChange = (taskNumber, value) => {
    setAnswers(prev => ({ ...prev, [taskNumber]: value }));
  };

  const handleFlag = (taskNumber) => {
    setFlagged(prev => {
      const next = new Set(prev);
      if (next.has(taskNumber)) next.delete(taskNumber);
      else next.add(taskNumber);
      return next;
    });
  };

  const handleSubmit = async () => {
    if (!window.confirm(
      'Вы уверены, что хотите завершить экзамен? После сдачи изменить ответы нельзя.'
    )) return;

    await doSubmit(false);
  };

  const handleAutoSubmit = async () => {
    await doSubmit(true);
  };

  const doSubmit = async (auto) => {
    setSubmitting(true);
    try {
      // Save pending answers first
      await saveAnswers();

      if (auto) {
        await examService.forceSubmit(attemptId);
      } else {
        const { apiClient } = await import('../../../apiService');
        await apiClient.post(`submissions/${attempt.submission.id}/submit/`);
      }

      setSubmitted(true);
      clearInterval(timerRef.current);
    } catch (err) {
      console.error('Submit failed:', err);
      alert('Ошибка при сдаче. Попробуйте ещё раз.');
    } finally {
      setSubmitting(false);
    }
  };

  // --- Rendering ---
  if (loading) {
    return (
      <div className="exam-take" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="skeleton" style={{ width: '100%', height: 400, borderRadius: 'var(--radius-md)' }} />
      </div>
    );
  }

  if (submitted) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        gap: 'var(--space-lg)',
        textAlign: 'center',
        padding: '2rem',
      }}>
        <div style={{
          width: 80,
          height: 80,
          background: 'var(--color-primary-subtle)',
          borderRadius: 'var(--radius-full)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2">
            <polyline points="20,6 9,17 4,12" />
          </svg>
        </div>
        <h2 style={{ margin: 0, color: 'var(--text-main)' }}>
          {attempt?.auto_submitted ? 'Время вышло' : 'Экзамен сдан'}
        </h2>
        <p style={{ margin: 0, color: 'var(--text-muted)', maxWidth: 400 }}>
          {attempt?.auto_submitted
            ? 'Работа сдана автоматически по истечении времени.'
            : 'Ваши ответы отправлены на проверку. Результаты появятся после проверки.'
          }
        </p>
        <Button variant="primary" onClick={() => navigate('/exams')}>
          К списку экзаменов
        </Button>
      </div>
    );
  }

  const currentTask = tasks[currentIndex];
  const totalTasks = tasks.length;
  const answeredCount = tasks.filter(t =>
    answers[t.task_number] && String(answers[t.task_number]).trim() !== ''
  ).length;

  // Timer status
  const totalDuration = attempt ? (attempt.deadline_seconds || (attempt.blueprint_duration * 60)) : 0;
  const timerProgress = totalDuration > 0 ? (timeLeft / totalDuration) * 100 : 100;
  const timerStatus = timeLeft != null
    ? timeLeft <= 300 ? 'danger' : timeLeft <= 1800 ? 'warning' : ''
    : '';

  return (
    <div className="exam-take animate-page-enter">
      <div className="exam-take-main">
        {/* Timer bar */}
        <div className="exam-timer">
          <div>
            <div className="exam-timer-label">Оставшееся время</div>
            <div className={`exam-timer-clock ${timerStatus}`}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12,6 12,12 16,14" />
              </svg>
              {formatTime(timeLeft)}
            </div>
          </div>

          <div className="exam-timer-progress">
            <div
              className={`exam-timer-progress-bar ${timerStatus}`}
              style={{ width: `${Math.max(0, timerProgress)}%` }}
            />
          </div>

          <Button
            variant="primary"
            size="sm"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? 'Сдаётся...' : 'Завершить экзамен'}
          </Button>
        </div>

        {/* Task content */}
        {currentTask && (
          <div className="exam-task-content">
            <div className="exam-task-header">
              <span className="exam-task-number-label">{currentTask.task_number}</span>
              <div className="exam-task-info">
                <div className="exam-task-info-type">
                  {ANSWER_TYPE_LABELS[currentTask.answer_type] || currentTask.answer_type}
                </div>
                <div className="exam-task-info-points">
                  {currentTask.max_points || currentTask.question?.points || 1} балл
                  {(currentTask.max_points || currentTask.question?.points || 1) > 1 ? 'а/ов' : ''}
                </div>
              </div>
              <Button
                size="sm"
                variant={flagged.has(currentTask.task_number) ? 'warning' : 'ghost'}
                onClick={() => handleFlag(currentTask.task_number)}
                title="Пометить для возврата"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill={flagged.has(currentTask.task_number) ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                  <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
                  <line x1="4" y1="22" x2="4" y2="15" />
                </svg>
              </Button>
            </div>

            <div
              className="exam-task-prompt"
              dangerouslySetInnerHTML={{
                __html: currentTask.question?.prompt || currentTask.question_prompt || ''
              }}
            />

            <ExamAnswerInput
              answerType={currentTask.answer_type}
              value={answers[currentTask.task_number] || ''}
              onChange={(val) => handleAnswerChange(currentTask.task_number, val)}
              disabled={submitting}
              config={currentTask.answer_config || currentTask.question?.config}
              choices={currentTask.question?.choices}
            />

            {/* Prev/Next */}
            <div className="exam-task-nav">
              <Button
                variant="ghost"
                onClick={() => setCurrentIndex(i => Math.max(0, i - 1))}
                disabled={currentIndex === 0}
              >
                Предыдущее
              </Button>
              <Button
                variant={currentIndex === totalTasks - 1 ? 'primary' : 'secondary'}
                onClick={() => {
                  if (currentIndex === totalTasks - 1) {
                    handleSubmit();
                  } else {
                    setCurrentIndex(i => Math.min(totalTasks - 1, i + 1));
                  }
                }}
              >
                {currentIndex === totalTasks - 1 ? 'Завершить' : 'Следующее'}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Navigation sidebar */}
      <div className="exam-nav-panel">
        <div className="exam-nav-grid">
          {tasks.map((task, idx) => {
            const isAnswered = answers[task.task_number] && String(answers[task.task_number]).trim() !== '';
            const isCurrent = idx === currentIndex;
            const isFlagged = flagged.has(task.task_number);

            let cls = 'exam-nav-btn';
            if (isCurrent) cls += ' current';
            else if (isAnswered) cls += ' answered';
            if (isFlagged) cls += ' flagged';

            return (
              <button
                key={task.task_number}
                className={cls}
                onClick={() => setCurrentIndex(idx)}
                title={`Задание ${task.task_number}`}
              >
                {task.task_number}
              </button>
            );
          })}
        </div>

        <div className="exam-nav-summary">
          <div className="exam-nav-summary-row">
            <span>Отвечено</span>
            <span>{answeredCount} / {totalTasks}</span>
          </div>
          <div className="exam-nav-summary-row">
            <span>Помечено</span>
            <span>{flagged.size}</span>
          </div>
          <div className="exam-nav-summary-row">
            <span>Осталось</span>
            <span>{totalTasks - answeredCount}</span>
          </div>
        </div>

        <Button
          variant="primary"
          onClick={handleSubmit}
          disabled={submitting}
          style={{ width: '100%' }}
        >
          {submitting ? 'Сдаётся...' : 'Завершить экзамен'}
        </Button>
      </div>
    </div>
  );
}
