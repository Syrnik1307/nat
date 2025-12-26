/**
 * StudentAIReports.js
 * Страница AI-отчётов по студентам для преподавателя
 */

import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../apiService';
import { Button, Card, Badge, Modal } from '../shared/components';
import './StudentAIReports.css';

const TrendBadge = ({ trend }) => {
  const config = {
    improving: { label: '📈 Прогресс', variant: 'success' },
    stable: { label: '➡️ Стабильно', variant: 'default' },
    declining: { label: '📉 Снижение', variant: 'warning' }
  };
  const { label, variant } = config[trend] || config.stable;
  return <Badge variant={variant}>{label}</Badge>;
};

const ReportCard = ({ report, onViewDetails }) => {
  const analysis = report.ai_analysis || {};
  
  return (
    <Card className="ai-report-card">
      <div className="report-header">
        <div className="student-info">
          <h4>{report.student_name}</h4>
          <span className="student-email">{report.student_email}</span>
        </div>
        <TrendBadge trend={analysis.progress_trend || 'stable'} />
      </div>
      
      <div className="report-stats">
        <div className="stat">
          <span className="stat-value">
            {report.avg_score_percent !== null 
              ? `${Math.round(report.avg_score_percent)}%` 
              : '—'}
          </span>
          <span className="stat-label">Средний балл</span>
        </div>
        <div className="stat">
          <span className="stat-value">{report.total_submissions}</span>
          <span className="stat-label">Сдано ДЗ</span>
        </div>
      </div>
      
      {analysis.summary && (
        <p className="report-summary">{analysis.summary}</p>
      )}
      
      <div className="report-actions">
        <Button variant="surface" onClick={() => onViewDetails(report)}>
          Подробнее
        </Button>
      </div>
    </Card>
  );
};

const ReportDetailsModal = ({ report, onClose }) => {
  if (!report) return null;
  
  const analysis = report.ai_analysis || {};
  
  return (
    <Modal isOpen={!!report} onClose={onClose} title={`AI-отчёт: ${report.student_name}`}>
      <div className="report-details">
        {/* Сводка */}
        <div className="details-section">
          <h4>📊 Сводка</h4>
          <div className="summary-stats">
            <div className="summary-item">
              <span className="label">Средний балл:</span>
              <span className="value">
                {report.avg_score_percent !== null 
                  ? `${Math.round(report.avg_score_percent)}%` 
                  : '—'}
              </span>
            </div>
            <div className="summary-item">
              <span className="label">Сдано ДЗ:</span>
              <span className="value">{report.total_submissions}</span>
            </div>
            <div className="summary-item">
              <span className="label">Ответов проверено:</span>
              <span className="value">{report.total_questions_answered}</span>
            </div>
            <div className="summary-item">
              <span className="label">Тренд:</span>
              <TrendBadge trend={analysis.progress_trend || 'stable'} />
            </div>
          </div>
          {analysis.summary && (
            <p className="ai-summary">{analysis.summary}</p>
          )}
        </div>
        
        {/* Сильные стороны */}
        {analysis.strengths?.length > 0 && (
          <div className="details-section">
            <h4>✅ Сильные стороны</h4>
            <ul className="analysis-list strengths">
              {analysis.strengths.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Слабые стороны */}
        {analysis.weaknesses?.length > 0 && (
          <div className="details-section">
            <h4>⚠️ Требует внимания</h4>
            <ul className="analysis-list weaknesses">
              {analysis.weaknesses.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Типичные ошибки */}
        {analysis.common_mistakes?.length > 0 && (
          <div className="details-section">
            <h4>🔍 Типичные ошибки</h4>
            <div className="mistakes-list">
              {analysis.common_mistakes.map((mistake, idx) => (
                <div key={idx} className="mistake-item">
                  <strong>{mistake.topic}</strong>
                  {mistake.frequency && (
                    <Badge variant="default">{mistake.frequency}x</Badge>
                  )}
                  {mistake.description && (
                    <p>{mistake.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Рекомендации */}
        {analysis.recommendations?.length > 0 && (
          <div className="details-section">
            <h4>💡 Рекомендации</h4>
            <ul className="analysis-list recommendations">
              {analysis.recommendations.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Метаданные */}
        <div className="details-section meta">
          <small>
            Отчёт сгенерирован: {new Date(report.created_at).toLocaleString('ru-RU')}
            {report.ai_confidence && ` • Уверенность AI: ${Math.round(report.ai_confidence * 100)}%`}
          </small>
        </div>
      </div>
    </Modal>
  );
};

const StudentAIReports = () => {
  const [reports, setReports] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [selectedGroup, setSelectedGroup] = useState('');
  const [selectedReport, setSelectedReport] = useState(null);
  
  const loadGroups = useCallback(async () => {
    try {
      const response = await apiClient.get('/groups/');
      const data = Array.isArray(response.data) 
        ? response.data 
        : response.data?.results || [];
      setGroups(data);
    } catch (err) {
      console.error('Ошибка загрузки групп:', err);
    }
  }, []);
  
  const loadReports = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = {};
      if (selectedGroup) {
        params.group = selectedGroup;
      }
      
      const response = await apiClient.get('/analytics/ai-reports/', { params });
      const data = Array.isArray(response.data) 
        ? response.data 
        : response.data?.results || [];
      setReports(data);
    } catch (err) {
      console.error('Ошибка загрузки отчётов:', err);
      setError('Не удалось загрузить отчёты');
    } finally {
      setLoading(false);
    }
  }, [selectedGroup]);
  
  useEffect(() => {
    loadGroups();
  }, [loadGroups]);
  
  useEffect(() => {
    loadReports();
  }, [loadReports]);
  
  const handleGenerateForGroup = async () => {
    if (!selectedGroup) {
      setError('Выберите группу для генерации отчётов');
      return;
    }
    
    try {
      setGenerating(true);
      setError(null);
      
      await apiClient.post('/analytics/ai-reports/generate-for-group/', {
        group_id: selectedGroup,
        period_days: 30
      });
      
      // Перезагружаем отчёты
      await loadReports();
    } catch (err) {
      console.error('Ошибка генерации отчётов:', err);
      setError(err.response?.data?.detail || 'Ошибка при генерации отчётов');
    } finally {
      setGenerating(false);
    }
  };
  
  return (
    <div className="student-ai-reports">
      <div className="reports-header">
        <h2>🤖 AI-отчёты по студентам</h2>
        <p className="subtitle">
          Анализ ошибок и прогресса на основе выполненных домашних заданий
        </p>
      </div>
      
      <div className="reports-controls">
        <div className="filter-group">
          <label>Группа:</label>
          <select 
            value={selectedGroup} 
            onChange={(e) => setSelectedGroup(e.target.value)}
            className="form-input"
          >
            <option value="">Все группы</option>
            {groups.map(group => (
              <option key={group.id} value={group.id}>{group.name}</option>
            ))}
          </select>
        </div>
        
        <Button 
          variant="primary" 
          onClick={handleGenerateForGroup}
          disabled={!selectedGroup || generating}
        >
          {generating ? '⏳ Генерация...' : '🔄 Сгенерировать отчёты'}
        </Button>
      </div>
      
      {error && (
        <div className="error-message">{error}</div>
      )}
      
      {loading ? (
        <div className="loading-state">Загрузка отчётов...</div>
      ) : reports.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <h3>Пока нет отчётов</h3>
          <p>Выберите группу и нажмите "Сгенерировать отчёты" для создания AI-анализа</p>
        </div>
      ) : (
        <div className="reports-grid">
          {reports.map(report => (
            <ReportCard 
              key={report.id} 
              report={report}
              onViewDetails={setSelectedReport}
            />
          ))}
        </div>
      )}
      
      <ReportDetailsModal 
        report={selectedReport} 
        onClose={() => setSelectedReport(null)}
      />
    </div>
  );
};

export default StudentAIReports;
