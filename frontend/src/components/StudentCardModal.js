/**
 * StudentCardModal.js
 * Модальная карточка ученика с информацией о прогрессе и замечаниями
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../apiService';
import './StudentCardModal.css';

const StudentCardModal = ({ studentId, groupId, isOpen, onClose, isIndividual = false }) => {
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  
  // AI-отчёт
  const [aiReport, setAiReport] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [generatingAi, setGeneratingAi] = useState(false);
  
  // Поведенческий отчёт
  const [behaviorReport, setBehaviorReport] = useState(null);
  const [behaviorLoading, setBehaviorLoading] = useState(false);
  const [generatingBehavior, setGeneratingBehavior] = useState(false);

  useEffect(() => {
    if (isOpen && studentId) {
      loadStudentCard();
      loadAiReport();
      loadBehaviorReport();
    }
  }, [isOpen, studentId, groupId]);

  const loadStudentCard = async () => {
    try {
      setLoading(true);
      setError(null);
      const endpoint = isIndividual 
        ? `/students/${studentId}/individual-card/`
        : `/students/${studentId}/card/?group_id=${groupId || ''}`;
      
      const response = await apiClient.get(endpoint);
      setCard(response.data);
      setNotes(response.data.teacher_notes || '');
    } catch (err) {
      console.error('Ошибка загрузки карточки:', err);
      setError('Не удалось загрузить информацию об ученике');
    } finally {
      setLoading(false);
    }
  };

  const loadAiReport = async () => {
    try {
      setAiLoading(true);
      const params = groupId ? `student_id=${studentId}&group_id=${groupId}` : `student_id=${studentId}`;
      const response = await apiClient.get(`/analytics/ai-reports/?${params}`);
      const reports = response.data.results || response.data || [];
      // Берём последний отчёт
      if (Array.isArray(reports) && reports.length > 0) {
        setAiReport(reports[0]);
      }
    } catch (err) {
      console.error('Ошибка загрузки AI-отчёта:', err);
    } finally {
      setAiLoading(false);
    }
  };

  const handleGenerateAiReport = async () => {
    try {
      setGeneratingAi(true);
      await apiClient.post('/analytics/ai-reports/generate/', {
        student_id: studentId,
        group_id: groupId || null,
        period: 'month'
      });
      await loadAiReport();
    } catch (err) {
      console.error('Ошибка генерации AI-отчёта:', err);
    } finally {
      setGeneratingAi(false);
    }
  };

  const loadBehaviorReport = async () => {
    try {
      setBehaviorLoading(true);
      const params = groupId ? `student=${studentId}&group=${groupId}` : `student=${studentId}`;
      const response = await apiClient.get(`/analytics/behavior-reports/?${params}`);
      const reports = response.data.results || response.data || [];
      if (Array.isArray(reports) && reports.length > 0) {
        setBehaviorReport(reports[0]);
      }
    } catch (err) {
      console.error('Ошибка загрузки поведенческого отчёта:', err);
    } finally {
      setBehaviorLoading(false);
    }
  };

  const handleGenerateBehaviorReport = async () => {
    try {
      setGeneratingBehavior(true);
      await apiClient.post('/analytics/behavior-reports/generate/', {
        student_id: studentId,
        group_id: groupId || null,
        period_days: 30
      });
      await loadBehaviorReport();
    } catch (err) {
      console.error('Ошибка генерации поведенческого отчёта:', err);
    } finally {
      setGeneratingBehavior(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!card) return;

    try {
      setSaving(true);
      if (isIndividual) {
        await apiClient.patch(`/individual-students/${studentId}/update_notes/`, {
          teacher_notes: notes
        });
      } else {
        // TODO: Реализовать сохранение замечаний для группового ученика
        console.log('Сохранение замечаний для группового ученика');
      }
      
      setEditing(false);
      loadStudentCard();
    } catch (err) {
      console.error('Ошибка сохранения замечаний:', err);
      setError('Не удалось сохранить замечания');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content student-card-modal" onClick={(e) => e.stopPropagation()}>
        {/* Заголовок */}
        <div className="modal-header">
          <div className="header-info">
            {loading ? (
              <h2 className="modal-title">Загрузка...</h2>
            ) : card ? (
              <div className="student-header">
                <div className="student-avatar-large">
                  {(card?.first_name || card?.name || '?').charAt(0).toUpperCase()}
                </div>
                <div className="student-header-info">
                  <h2 className="modal-title">{card.name}</h2>
                  <p className="student-email">{card.email}</p>
                </div>
              </div>
            ) : null}
          </div>
          <button
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Закрыть"
          >
            ✕
          </button>
        </div>

        {/* Содержимое */}
        <div className="modal-body">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {loading ? (
            <div className="loading-state">Загрузка информации об ученике...</div>
          ) : card ? (
            <>
              {/* Статистика */}
              <div className="stats-grid">
                <div className="stat-card">
                  <span className="stat-icon">+</span>
                  <span className="stat-label">Посещаемость</span>
                  <span className="stat-value">{card.stats?.attendance_percent || 0}%</span>
                  <span className="stat-detail">
                    {card.stats?.attended || 0}/{card.stats?.total_lessons || 0} занятий
                  </span>
                </div>

                <div className="stat-card">
                  <span className="stat-icon">📝</span>
                  <span className="stat-label">Домашние задания</span>
                  <span className="stat-value">—</span>
                  <span className="stat-detail">Интеграция с модулем ДЗ</span>
                </div>

                <div className="stat-card">
                  <span className="stat-icon">🎯</span>
                  <span className="stat-label">Контрольные точки</span>
                  <span className="stat-value">—</span>
                  <span className="stat-detail">Интеграция с модулем аналитики</span>
                </div>

                {!isIndividual && (
                  <div className="stat-card">
                    <span className="stat-icon">•</span>
                    <span className="stat-label">Место в группе</span>
                    <span className="stat-value">—</span>
                    <span className="stat-detail">Из рейтинга группы</span>
                  </div>
                )}
              </div>

              {/* Ошибки и пробелы */}
              {card.errors && (Object.keys(card.errors).length > 0) && (
                <div className="errors-section">
                  <h3 className="section-title">Пробелы и недовыполнения</h3>
                  
                  {card.errors.incomplete_homework && card.errors.incomplete_homework.length > 0 && (
                    <div className="error-item">
                      <span className="error-type">Недовыполненные ДЗ:</span>
                      <ul className="error-list">
                        {card.errors.incomplete_homework.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {card.errors.failed_control_points && card.errors.failed_control_points.length > 0 && (
                    <div className="error-item">
                      <span className="error-type">Непройденные контрольные:</span>
                      <ul className="error-list">
                        {card.errors.failed_control_points.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Замечания учителя */}
              <div className="notes-section">
                <div className="notes-header">
                  <h3 className="section-title">📝 Замечания учителя</h3>
                  <button
                    className="edit-btn"
                    onClick={() => setEditing(!editing)}
                  >
                    {editing ? '✓' : '✎'}
                  </button>
                </div>

                {editing ? (
                  <div className="notes-editor">
                    <textarea
                      className="notes-textarea"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Добавьте замечания об ученике..."
                      rows={4}
                    />
                    <div className="editor-buttons">
                      <button
                        className="btn btn-primary"
                        onClick={handleSaveNotes}
                        disabled={saving}
                      >
                        {saving ? '💾 Сохранение...' : '💾 Сохранить'}
                      </button>
                      <button
                        className="btn btn-secondary"
                        onClick={() => {
                          setEditing(false);
                          setNotes(card.teacher_notes || '');
                        }}
                      >
                        ✕ Отмена
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="notes-display">
                    {notes ? (
                      <p className="notes-text">{notes}</p>
                    ) : (
                      <p className="notes-empty">Нет замечаний</p>
                    )}
                  </div>
                )}
              </div>

              {/* AI-анализ ученика */}
              <div className="ai-report-section">
                <div className="ai-report-header">
                  <h3 className="section-title">🤖 AI-анализ</h3>
                  <button
                    className="generate-btn"
                    onClick={handleGenerateAiReport}
                    disabled={generatingAi || aiLoading}
                  >
                    {generatingAi ? 'Генерация...' : aiReport ? 'Обновить' : 'Сгенерировать'}
                  </button>
                </div>

                {aiLoading ? (
                  <div className="ai-loading">Загрузка AI-отчёта...</div>
                ) : aiReport && aiReport.status === 'completed' && aiReport.ai_analysis ? (
                  <div className="ai-report-content">
                    {/* Тренд */}
                    <div className="ai-trend">
                      <span className="trend-label">Тренд прогресса:</span>
                      <span className={`trend-value trend-${aiReport.ai_analysis.progress_trend || 'stable'}`}>
                        {aiReport.ai_analysis.progress_trend === 'improving' ? '↑ Улучшение' :
                         aiReport.ai_analysis.progress_trend === 'declining' ? '↓ Снижение' : '→ Стабильно'}
                      </span>
                    </div>

                    {/* Сильные стороны */}
                    {aiReport.ai_analysis.strengths?.length > 0 && (
                      <div className="ai-section strengths">
                        <h4>✅ Сильные стороны</h4>
                        <ul>
                          {aiReport.ai_analysis.strengths.slice(0, 3).map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Слабые стороны */}
                    {aiReport.ai_analysis.weaknesses?.length > 0 && (
                      <div className="ai-section weaknesses">
                        <h4>⚠️ Требуют внимания</h4>
                        <ul>
                          {aiReport.ai_analysis.weaknesses.slice(0, 3).map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Рекомендации */}
                    {aiReport.ai_analysis.recommendations?.length > 0 && (
                      <div className="ai-section recommendations">
                        <h4>💡 Рекомендации</h4>
                        <ul>
                          {aiReport.ai_analysis.recommendations.slice(0, 3).map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <p className="ai-report-date">
                      Отчёт от {new Date(aiReport.created_at).toLocaleDateString('ru-RU')}
                    </p>
                  </div>
                ) : aiReport && aiReport.status === 'processing' ? (
                  <div className="ai-processing">
                    <div className="ai-spinner"></div>
                    <span>AI анализирует данные ученика...</span>
                  </div>
                ) : (
                  <div className="ai-empty">
                    <p>AI-отчёт ещё не сгенерирован</p>
                    <p className="ai-hint">Нажмите «Сгенерировать» для создания анализа</p>
                  </div>
                )}
              </div>

              {/* Поведенческий AI-анализ */}
              <div className="behavior-report-section">
                <div className="ai-report-header">
                  <h3 className="section-title">📊 Поведенческий анализ</h3>
                  <button
                    className="generate-btn"
                    onClick={handleGenerateBehaviorReport}
                    disabled={generatingBehavior || behaviorLoading}
                  >
                    {generatingBehavior ? 'Генерация...' : behaviorReport ? 'Обновить' : 'Сгенерировать'}
                  </button>
                </div>

                {behaviorLoading ? (
                  <div className="ai-loading">Загрузка поведенческого отчёта...</div>
                ) : behaviorReport && behaviorReport.status === 'completed' ? (
                  <div className="behavior-report-content">
                    {/* Риск и надёжность */}
                    <div className="behavior-stats-row">
                      <div className={`risk-badge risk-${behaviorReport.risk_level || 'medium'}`}>
                        {behaviorReport.risk_level === 'low' ? '🟢 Низкий риск' :
                         behaviorReport.risk_level === 'high' ? '🔴 Высокий риск' : '🟡 Средний риск'}
                      </div>
                      {behaviorReport.reliability_score !== null && (
                        <div className="reliability-score">
                          Надёжность: <strong>{behaviorReport.reliability_score}%</strong>
                        </div>
                      )}
                    </div>

                    {/* Статистика */}
                    <div className="behavior-metrics">
                      <div className="metric-item">
                        <span className="metric-label">Посещаемость</span>
                        <span className="metric-value">{behaviorReport.attendance_rate?.toFixed(0) || 0}%</span>
                        <span className="metric-detail">{behaviorReport.attended_lessons}/{behaviorReport.total_lessons} занятий</span>
                      </div>
                      <div className="metric-item">
                        <span className="metric-label">Сдача ДЗ</span>
                        <span className="metric-value">{behaviorReport.homework_rate?.toFixed(0) || 0}%</span>
                        <span className="metric-detail">{behaviorReport.submitted_on_time + behaviorReport.submitted_late}/{behaviorReport.total_homework} заданий</span>
                      </div>
                    </div>

                    {/* Алерты */}
                    {behaviorReport.ai_analysis?.alerts?.length > 0 && (
                      <div className="behavior-alerts">
                        {behaviorReport.ai_analysis.alerts.map((alert, i) => (
                          <div key={i} className={`alert-item alert-${alert.type}`}>
                            {alert.type === 'warning' ? '⚠️' : 'ℹ️'} {alert.message}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Рекомендации */}
                    {behaviorReport.ai_analysis?.recommendations?.length > 0 && (
                      <div className="ai-section recommendations">
                        <h4>💡 Рекомендации</h4>
                        <ul>
                          {behaviorReport.ai_analysis.recommendations.slice(0, 3).map((rec, i) => (
                            <li key={i}>
                              {rec.priority === 'high' && '🔴 '}
                              {rec.priority === 'medium' && '🟡 '}
                              {rec.priority === 'low' && '🟢 '}
                              {rec.action}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Резюме */}
                    {behaviorReport.ai_analysis?.summary && (
                      <p className="behavior-summary">{behaviorReport.ai_analysis.summary}</p>
                    )}

                    <p className="ai-report-date">
                      Отчёт от {new Date(behaviorReport.created_at).toLocaleDateString('ru-RU')}
                    </p>
                  </div>
                ) : (
                  <div className="ai-empty">
                    <p>Поведенческий отчёт не сгенерирован</p>
                    <p className="ai-hint">Анализ посещаемости, сдачи ДЗ и рисков</p>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="empty-state">Информация не найдена</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StudentCardModal;
