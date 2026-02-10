/**
 * ExamResults — результаты экзаменов.
 *
 * Учитель: аналитика по группе, список попыток.
 * Ученик: свои результаты с разбивкой по заданиям.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Badge } from '../../../shared/components';
import * as examService from '../services/examService';
import { ANSWER_TYPE_LABELS, formatTime } from '../services/examService';

export default function ExamResults({ blueprintId, isTeacher }) {
  const navigate = useNavigate();
  const [attempts, setAttempts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAttempt, setSelectedAttempt] = useState(null);
  const [result, setResult] = useState(null);
  const [analytics, setAnalytics] = useState(null);

  // Загрузка попыток
  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        if (isTeacher) {
          const params = {};
          if (blueprintId) params.blueprint = blueprintId;
          const data = await examService.getAttempts(params);
          setAttempts(data.results || data);

          // Аналитика для учителя
          if (blueprintId) {
            const anal = await examService.getAnalytics({ blueprint: blueprintId });
            setAnalytics(anal);
          }
        } else {
          const data = await examService.getMyAttempts();
          setAttempts(data.results || data);
        }
      } catch (err) {
        console.error('Failed to load results:', err);
      } finally {
        setLoading(false);
      }
    })();
  }, [blueprintId, isTeacher]);

  // Загрузка детального результата
  const openResult = useCallback(async (attemptId) => {
    try {
      const data = await examService.getResult(attemptId);
      setResult(data);
      setSelectedAttempt(attemptId);
    } catch (err) {
      console.error('Failed to load result:', err);
    }
  }, []);

  if (loading) {
    return (
      <div className="exam-skeleton-cards">
        {[1, 2, 3].map(i => (
          <div key={i} className="exam-skeleton-card skeleton" />
        ))}
      </div>
    );
  }

  // Детальный результат
  if (result && selectedAttempt) {
    return (
      <div className="exam-results animate-content">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-md)' }}>
          <Button variant="ghost" onClick={() => { setResult(null); setSelectedAttempt(null); }}>
            Назад к списку
          </Button>
          <h2 style={{ margin: 0, fontSize: 'var(--text-xl)', fontWeight: 600 }}>
            {result.blueprint_title || 'Результат экзамена'}
          </h2>
        </div>

        {/* Сводка баллов */}
        <div className="exam-results-summary">
          <div className={`exam-result-stat ${result.grade ? `grade-${result.grade}` : ''}`}>
            <div className="exam-result-stat-value">
              {result.primary_score ?? '—'} / {result.max_primary_score ?? '—'}
            </div>
            <div className="exam-result-stat-label">Первичный балл</div>
          </div>

          <div className={`exam-result-stat ${result.grade ? `grade-${result.grade}` : ''}`}>
            <div className="exam-result-stat-value">
              {result.test_score ?? '—'}
            </div>
            <div className="exam-result-stat-label">Тестовый балл</div>
          </div>

          {result.grade && (
            <div className={`exam-result-stat grade-${result.grade}`}>
              <div className="exam-result-stat-value">{result.grade}</div>
              <div className="exam-result-stat-label">Оценка</div>
            </div>
          )}

          <div className="exam-result-stat">
            <div className="exam-result-stat-value">
              {result.time_spent_seconds ? formatTime(result.time_spent_seconds) : '—'}
            </div>
            <div className="exam-result-stat-label">Затрачено времени</div>
          </div>

          {result.auto_submitted && (
            <div className="exam-result-stat">
              <div className="exam-result-stat-value" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-warning)' }}>
                Авто-сдача
              </div>
              <div className="exam-result-stat-label">Время истекло</div>
            </div>
          )}
        </div>

        {/* Разбивка по заданиям */}
        <div className="exam-results-breakdown">
          <div className="exam-results-breakdown-header">
            Разбивка по заданиям
          </div>
          {(result.task_scores || []).map(ts => {
            const status = ts.score >= ts.max ? 'correct'
              : ts.score > 0 ? 'partial'
              : 'wrong';
            return (
              <div key={ts.task_number} className="exam-results-task-row">
                <span className={`exam-results-task-num ${status}`}>
                  {ts.task_number}
                </span>
                <span className="exam-results-task-prompt">
                  {ANSWER_TYPE_LABELS[ts.answer_type] || ts.answer_type}
                </span>
                <span className="exam-results-task-score">
                  {ts.score} / {ts.max}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Список попыток
  return (
    <div className="exam-results animate-content">
      {/* Аналитика учителя */}
      {isTeacher && analytics && (
        <div className="exam-results-summary" style={{ marginBottom: 'var(--space-lg)' }}>
          <div className="exam-result-stat">
            <div className="exam-result-stat-value">{analytics.total_attempts || 0}</div>
            <div className="exam-result-stat-label">Всего попыток</div>
          </div>
          <div className="exam-result-stat">
            <div className="exam-result-stat-value">
              {analytics.avg_primary_score != null ? analytics.avg_primary_score.toFixed(1) : '—'}
            </div>
            <div className="exam-result-stat-label">Средний первичный балл</div>
          </div>
          <div className="exam-result-stat">
            <div className="exam-result-stat-value">
              {analytics.avg_test_score != null ? analytics.avg_test_score.toFixed(1) : '—'}
            </div>
            <div className="exam-result-stat-label">Средний тестовый балл</div>
          </div>
          <div className="exam-result-stat">
            <div className="exam-result-stat-value">
              {analytics.completion_rate != null ? `${(analytics.completion_rate * 100).toFixed(0)}%` : '—'}
            </div>
            <div className="exam-result-stat-label">Завершили</div>
          </div>
        </div>
      )}

      {attempts.length === 0 ? (
        <div className="exam-empty-state">
          <div className="exam-empty-state-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
            </svg>
          </div>
          <h3 className="exam-empty-state-title">Нет результатов</h3>
          <p className="exam-empty-state-desc">
            {isTeacher
              ? 'Пока ни один ученик не прошёл экзамен по этому шаблону.'
              : 'У вас пока нет пройденных экзаменов.'
            }
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
          {/* Table header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: isTeacher ? '1fr 150px 80px 80px 80px 100px' : '1fr 150px 80px 80px 80px',
            gap: 'var(--space-sm)',
            padding: '0.5rem 1rem',
            fontSize: 'var(--text-xs)',
            color: 'var(--text-muted)',
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}>
            <span>{isTeacher ? 'Ученик' : 'Экзамен'}</span>
            <span>Дата</span>
            <span>Первичный</span>
            <span>Тестовый</span>
            <span>Оценка</span>
            {isTeacher && <span>Статус</span>}
          </div>

          {attempts.map(att => (
            <div
              key={att.id}
              onClick={() => openResult(att.id)}
              style={{
                display: 'grid',
                gridTemplateColumns: isTeacher ? '1fr 150px 80px 80px 80px 100px' : '1fr 150px 80px 80px 80px',
                gap: 'var(--space-sm)',
                padding: '0.75rem 1rem',
                background: 'var(--bg-paper)',
                border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                alignItems: 'center',
                fontSize: 'var(--text-sm)',
                transition: 'all var(--duration-fast) var(--ease-smooth)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                e.currentTarget.style.borderColor = 'var(--border-medium)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.borderColor = 'var(--border-light)';
              }}
            >
              <span style={{ fontWeight: 500, color: 'var(--text-main)' }}>
                {isTeacher
                  ? (att.student_name || att.submission?.student_email || 'Ученик')
                  : (att.blueprint_title || att.variant_title || 'Экзамен')
                }
              </span>
              <span style={{ color: 'var(--text-muted)' }}>
                {att.started_at
                  ? new Date(att.started_at).toLocaleDateString('ru', {
                      day: 'numeric', month: 'short', year: 'numeric',
                    })
                  : '—'
                }
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                {att.primary_score ?? '—'}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                {att.test_score ?? '—'}
              </span>
              <span>
                {att.grade ? (
                  <Badge variant={
                    att.grade === '5' ? 'success' :
                    att.grade === '4' ? 'primary' :
                    att.grade === '3' ? 'warning' : 'error'
                  }>
                    {att.grade}
                  </Badge>
                ) : '—'}
              </span>
              {isTeacher && (
                <span>
                  <Badge variant={
                    att.submission?.status === 'graded' ? 'success' :
                    att.submission?.status === 'submitted' ? 'warning' : 'muted'
                  }>
                    {att.submission?.status === 'graded' ? 'Проверено' :
                     att.submission?.status === 'submitted' ? 'На проверке' :
                     att.auto_submitted ? 'Авто-сдача' : 'В процессе'}
                  </Badge>
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Ученик — кнопка начать экзамен если есть незначенные */}
      {!isTeacher && (
        <div style={{ marginTop: 'var(--space-lg)' }}>
          <Button variant="ghost" onClick={() => navigate('/exams')}>
            Назад к экзаменам
          </Button>
        </div>
      )}
    </div>
  );
}
