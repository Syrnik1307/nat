/**
 * GroupAIReportsTab.js
 * Таб AI-отчётов группы
 * Показывает AI-анализ ошибок учеников в группе
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../../apiService';
import './GroupAIReportsTab.css';

const GroupAIReportsTab = ({ groupId }) => {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(null); // studentId that is generating
  const [selectedReport, setSelectedReport] = useState(null);

  useEffect(() => {
    loadReports();
  }, [groupId]);

  const loadReports = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(`/analytics/ai-reports/?group_id=${groupId}`);
      const data = response.data.results || response.data || [];
      setReports(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Ошибка загрузки AI-отчётов:', err);
      setError('Не удалось загрузить AI-отчёты');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async (studentId, studentName) => {
    try {
      setGenerating(studentId);
      await apiClient.post(`/analytics/ai-reports/generate/`, {
        student_id: studentId,
        group_id: groupId,
        period: 'month'
      });
      // Перезагружаем отчёты
      await loadReports();
    } catch (err) {
      console.error('Ошибка генерации отчёта:', err);
      setError(`Не удалось сгенерировать отчёт для ${studentName}`);
    } finally {
      setGenerating(null);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      'pending': { label: 'В очереди', class: 'status-pending' },
      'processing': { label: 'Генерируется...', class: 'status-processing' },
      'completed': { label: 'Готов', class: 'status-completed' },
      'failed': { label: 'Ошибка', class: 'status-failed' }
    };
    return statusMap[status] || { label: status, class: '' };
  };

  if (loading) {
    return <div className="tab-loading">Загрузка AI-отчётов...</div>;
  }

  if (error) {
    return (
      <div className="tab-error">
        {error}
        <button onClick={loadReports} className="retry-btn">Повторить</button>
      </div>
    );
  }

  return (
    <div className="group-ai-reports-tab">
      <div className="tab-header">
        <h3 className="tab-title">🤖 AI-анализ успеваемости</h3>
        <p className="tab-description">
          Нейросеть анализирует ошибки учеников и формирует рекомендации для каждого
        </p>
      </div>

      {reports.length === 0 ? (
        <div className="tab-empty">
          <div className="empty-icon">📊</div>
          <p>Пока нет AI-отчётов для этой группы</p>
          <p className="empty-hint">
            Отчёты генерируются автоматически на основе выполненных домашних заданий
          </p>
        </div>
      ) : (
        <div className="reports-list">
          {reports.map((report) => {
            const status = getStatusBadge(report.status);
            return (
              <div key={report.id} className="report-card">
                <div className="report-header">
                  <div className="student-info">
                    <span className="student-name">{report.student_name}</span>
                    <span className={`status-badge ${status.class}`}>{status.label}</span>
                  </div>
                  <span className="report-date">{formatDate(report.created_at)}</span>
                </div>

                {report.status === 'completed' && report.ai_analysis && (
                  <div className="report-preview">
                    {/* Краткие показатели */}
                    <div className="quick-stats">
                      <div className="stat">
                        <span className="stat-label">ДЗ сдано</span>
                        <span className="stat-value">{report.statistics?.total_submissions || 0}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Средний балл</span>
                        <span className="stat-value">
                          {report.statistics?.average_score?.toFixed(1) || '—'}
                        </span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Тренд</span>
                        <span className={`stat-value trend-${report.ai_analysis.progress_trend || 'stable'}`}>
                          {report.ai_analysis.progress_trend === 'improving' ? '↑ Рост' :
                           report.ai_analysis.progress_trend === 'declining' ? '↓ Спад' : '→ Стабильно'}
                        </span>
                      </div>
                    </div>

                    <button 
                      className="view-details-btn"
                      onClick={() => setSelectedReport(report)}
                    >
                      Подробнее
                    </button>
                  </div>
                )}

                {report.status === 'processing' && (
                  <div className="report-processing">
                    <div className="spinner"></div>
                    <span>Анализ в процессе...</span>
                  </div>
                )}

                {report.status === 'failed' && (
                  <div className="report-failed">
                    <span>Не удалось сгенерировать отчёт</span>
                    <button 
                      className="retry-small-btn"
                      onClick={() => handleGenerateReport(report.student, report.student_name)}
                      disabled={generating === report.student}
                    >
                      Повторить
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Модальное окно с деталями отчёта */}
      {selectedReport && (
        <div className="report-modal-overlay" onClick={() => setSelectedReport(null)}>
          <div className="report-modal" onClick={(e) => e.stopPropagation()}>
            <div className="report-modal-header">
              <h3>AI-отчёт: {selectedReport.student_name}</h3>
              <button 
                className="modal-close-btn"
                onClick={() => setSelectedReport(null)}
              >
                ✕
              </button>
            </div>
            
            <div className="report-modal-content">
              {selectedReport.ai_analysis && (
                <>
                  {/* Сильные стороны */}
                  {selectedReport.ai_analysis.strengths?.length > 0 && (
                    <div className="analysis-section strengths">
                      <h4>✅ Сильные стороны</h4>
                      <ul>
                        {selectedReport.ai_analysis.strengths.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Слабые стороны */}
                  {selectedReport.ai_analysis.weaknesses?.length > 0 && (
                    <div className="analysis-section weaknesses">
                      <h4>⚠️ Требуют внимания</h4>
                      <ul>
                        {selectedReport.ai_analysis.weaknesses.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Типичные ошибки */}
                  {selectedReport.ai_analysis.common_mistakes?.length > 0 && (
                    <div className="analysis-section mistakes">
                      <h4>❌ Типичные ошибки</h4>
                      <ul>
                        {selectedReport.ai_analysis.common_mistakes.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Рекомендации */}
                  {selectedReport.ai_analysis.recommendations?.length > 0 && (
                    <div className="analysis-section recommendations">
                      <h4>💡 Рекомендации</h4>
                      <ul>
                        {selectedReport.ai_analysis.recommendations.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Общий комментарий */}
                  {selectedReport.ai_analysis.summary && (
                    <div className="analysis-section summary">
                      <h4>📝 Заключение</h4>
                      <p>{selectedReport.ai_analysis.summary}</p>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GroupAIReportsTab;
