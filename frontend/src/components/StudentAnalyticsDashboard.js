import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../apiService';
import './StudentAnalyticsDashboard.css';

/**
 * Расширенный дашборд аналитики ученика
 * Показывает: когнитивный профиль, паттерны ошибок, мотивацию, социальную динамику
 */

const DAYS_OF_WEEK = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

const ROLE_ICONS = {
  leader: '👑',
  helper: '🤝',
  active: '💬',
  observer: '👀',
  silent: '🔇',
};

const ROLE_LABELS = {
  leader: 'Лидер',
  helper: 'Помощник',
  active: 'Активный',
  observer: 'Наблюдатель',
  silent: 'Молчун',
};

const TREND_ICONS = {
  improving: '📈',
  stable: '➡️',
  declining: '📉',
};

const RISK_COLORS = {
  low: '#4ade80',
  medium: '#fbbf24',
  high: '#ef4444',
};

// ============ Компоненты карточек ============

function MetricCard({ title, value, subtitle, icon, trend, color }) {
  return (
    <div className="metric-card" style={{ borderLeftColor: color || '#3b82f6' }}>
      <div className="metric-header">
        {icon && <span className="metric-icon">{icon}</span>}
        <span className="metric-title">{title}</span>
      </div>
      <div className="metric-value">
        {value}
        {trend && <span className="metric-trend">{TREND_ICONS[trend] || ''}</span>}
      </div>
      {subtitle && <div className="metric-subtitle">{subtitle}</div>}
    </div>
  );
}

function ErrorPatternCard({ pattern }) {
  const getBarColor = (accuracy) => {
    if (accuracy >= 80) return '#4ade80';
    if (accuracy >= 60) return '#fbbf24';
    return '#ef4444';
  };

  const errorTypeLabel = {
    systematic: '⚠️ Системные',
    random: '🎲 Случайные',
    careless: '😵 Невнимательность',
    unknown: '❓ Неизвестно',
  };

  return (
    <div className="error-pattern-card">
      <div className="pattern-header">
        <span className="pattern-type">{pattern.question_type}</span>
        <span className="pattern-error-type">{errorTypeLabel[pattern.error_type]}</span>
      </div>
      <div className="pattern-bar-container">
        <div 
          className="pattern-bar" 
          style={{ 
            width: `${pattern.accuracy_percent}%`,
            backgroundColor: getBarColor(pattern.accuracy_percent)
          }}
        />
      </div>
      <div className="pattern-stats">
        <span>✅ {pattern.correct_count}</span>
        <span>❌ {pattern.error_count}</span>
        <span className="pattern-accuracy">{pattern.accuracy_percent.toFixed(0)}%</span>
      </div>
    </div>
  );
}

function ActivityHeatmap({ heatmapData, optimalHours, bestDays }) {
  const getColor = (value, maxValue) => {
    if (!value) return '#f3f4f6';
    const intensity = Math.min(value / Math.max(maxValue, 1), 1);
    return `rgba(59, 130, 246, ${0.2 + intensity * 0.8})`;
  };

  // Находим максимальное значение
  const maxValue = Math.max(...heatmapData.map(d => d.value), 1);

  // Создаём матрицу 7x24
  const matrix = Array.from({ length: 7 }, () => Array(24).fill(0));
  heatmapData.forEach(({ day, hour, value }) => {
    if (day >= 0 && day < 7 && hour >= 0 && hour < 24) {
      matrix[day][hour] = value;
    }
  });

  return (
    <div className="heatmap-container">
      <div className="heatmap-title">🕐 Активность по времени</div>
      <div className="heatmap-grid">
        <div className="heatmap-hours-header">
          <div className="heatmap-corner"></div>
          {HOURS.filter(h => h % 3 === 0).map(hour => (
            <div key={hour} className="heatmap-hour-label">{hour}:00</div>
          ))}
        </div>
        {DAYS_OF_WEEK.map((day, dayIdx) => (
          <div key={day} className="heatmap-row">
            <div className={`heatmap-day-label ${bestDays?.includes(dayIdx) ? 'best-day' : ''}`}>
              {day}
            </div>
            {HOURS.map(hour => (
              <div
                key={`${dayIdx}-${hour}`}
                className={`heatmap-cell ${optimalHours?.includes(hour) ? 'optimal-hour' : ''}`}
                style={{ backgroundColor: getColor(matrix[dayIdx][hour], maxValue) }}
                title={`${day} ${hour}:00 - ${matrix[dayIdx][hour]} действий`}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="heatmap-legend">
        {optimalHours?.length > 0 && (
          <span className="legend-item">
            ⭐ Оптимальные часы: {optimalHours.map(h => `${h}:00`).join(', ')}
          </span>
        )}
      </div>
    </div>
  );
}

function CognitiveProfileCard({ cognitive }) {
  if (!cognitive) return null;

  return (
    <div className="profile-card cognitive-profile">
      <h3>🧠 Когнитивный профиль</h3>
      
      <div className="profile-row">
        <span className="profile-label">Сильные типы вопросов:</span>
        <div className="profile-tags">
          {cognitive.preferred_question_types?.map(t => (
            <span key={t} className="tag tag-green">{t}</span>
          )) || <span className="no-data">Нет данных</span>}
        </div>
      </div>
      
      <div className="profile-row">
        <span className="profile-label">Слабые типы:</span>
        <div className="profile-tags">
          {cognitive.weak_question_types?.map(t => (
            <span key={t} className="tag tag-red">{t}</span>
          )) || <span className="no-data">—</span>}
        </div>
      </div>
      
      <div className="profile-metrics">
        {cognitive.avg_warmup_time_seconds && (
          <MetricCard
            title="Время на разгон"
            value={`${(cognitive.avg_warmup_time_seconds / 60).toFixed(0)} мин`}
            icon="🐢"
            color={cognitive.avg_warmup_time_seconds > 600 ? '#fbbf24' : '#4ade80'}
          />
        )}
        
        {cognitive.avg_answer_time_seconds && (
          <MetricCard
            title="Ср. время на ответ"
            value={`${(cognitive.avg_answer_time_seconds / 60).toFixed(1)} мин`}
            icon="⏱️"
          />
        )}
        
        <MetricCard
          title="Порядок ответов"
          value={cognitive.follows_question_order ? 'По порядку' : 'Хаотично'}
          icon={cognitive.follows_question_order ? '📋' : '🔀'}
          color={cognitive.follows_question_order ? '#4ade80' : '#fbbf24'}
        />
        
        {cognitive.avg_revisions_per_answer > 0 && (
          <MetricCard
            title="Самокоррекция"
            value={`${cognitive.avg_revisions_per_answer.toFixed(1)} правок`}
            subtitle="в среднем на ответ"
            icon="✏️"
          />
        )}
      </div>
      
      {cognitive.total_questions_asked > 0 && (
        <div className="question-quality">
          <h4>💡 Качество вопросов</h4>
          <div className="question-stats">
            <span className="stat">
              Всего: <strong>{cognitive.total_questions_asked}</strong>
            </span>
            <span className="stat">
              Концептуальных: <strong>{cognitive.conceptual_questions}</strong>
            </span>
            <span className="stat">
              Процедурных: <strong>{cognitive.procedural_questions}</strong>
            </span>
          </div>
          <div className="quality-bar-container">
            <div 
              className="quality-bar"
              style={{ 
                width: `${cognitive.question_quality_score * 100}%`,
                backgroundColor: cognitive.question_quality_score > 0.6 ? '#4ade80' : '#fbbf24'
              }}
            />
          </div>
          <span className="quality-label">
            Качество: {(cognitive.question_quality_score * 100).toFixed(0)}%
          </span>
        </div>
      )}
    </div>
  );
}

function MotivationProfileCard({ motivation, energy }) {
  if (!motivation && !energy) return null;

  const motivationTypeLabels = {
    intrinsic: '🌟 Внутренняя (к успеху)',
    extrinsic: '🎯 Внешняя',
    fear_driven: '😰 От страха',
    unknown: '❓ Не определена',
  };

  const submissionPatternLabels = {
    early: '🚀 Ранняя сдача',
    on_time: '✅ Вовремя',
    last_minute: '⏰ В последний момент',
    late: '❌ С опозданием',
  };

  const stressLabels = {
    high: '💪 Высокая',
    normal: '😐 Средняя',
    low: '😰 Низкая',
  };

  return (
    <div className="profile-card motivation-profile">
      <h3>💪 Мотивация и энергия</h3>
      
      <div className="motivation-grid">
        <MetricCard
          title="Тип мотивации"
          value={motivationTypeLabels[motivation?.motivation_type] || '—'}
          color={motivation?.motivation_type === 'intrinsic' ? '#4ade80' : '#fbbf24'}
        />
        
        <MetricCard
          title="Паттерн сдачи"
          value={submissionPatternLabels[motivation?.submission_pattern] || '—'}
          color={
            motivation?.submission_pattern === 'early' ? '#4ade80' :
            motivation?.submission_pattern === 'late' ? '#ef4444' : '#3b82f6'
          }
        />
        
        <MetricCard
          title="Стрессоустойчивость"
          value={stressLabels[motivation?.stress_resilience] || '—'}
          subtitle={motivation?.control_point_vs_hw_diff !== null 
            ? `КТ vs ДЗ: ${motivation.control_point_vs_hw_diff > 0 ? '+' : ''}${motivation.control_point_vs_hw_diff?.toFixed(0)}` 
            : ''}
          color={
            motivation?.stress_resilience === 'high' ? '#4ade80' :
            motivation?.stress_resilience === 'low' ? '#ef4444' : '#fbbf24'
          }
        />
        
        {energy?.fatigue_onset_minute && (
          <MetricCard
            title="Усталость наступает"
            value={`~${energy.fatigue_onset_minute} мин`}
            subtitle="от начала работы"
            icon="⚡"
            color={energy.fatigue_onset_minute < 30 ? '#ef4444' : '#4ade80'}
          />
        )}
      </div>
      
      {motivation?.avg_days_before_deadline !== null && (
        <div className="deadline-info">
          📅 В среднем сдаёт за <strong>{motivation.avg_days_before_deadline?.toFixed(1)}</strong> дн. до дедлайна
        </div>
      )}
    </div>
  );
}

function SocialProfileCard({ social }) {
  if (!social) return null;

  return (
    <div className="profile-card social-profile">
      <h3>👥 Социальная динамика</h3>
      
      <div className="social-role">
        <span className="role-icon">{ROLE_ICONS[social.detected_role]}</span>
        <span className="role-label">{ROLE_LABELS[social.detected_role]}</span>
        {social.rank_in_group && (
          <span className="rank-badge">#{social.rank_in_group} в группе</span>
        )}
      </div>
      
      <div className="social-metrics">
        <MetricCard
          title="Сообщений в чате"
          value={social.total_messages}
          icon="💬"
        />
        <MetricCard
          title="Вопросов задано"
          value={social.questions_asked}
          icon="❓"
        />
        <MetricCard
          title="Ответов другим"
          value={social.answers_given}
          icon="💡"
          color={social.answers_given > 5 ? '#4ade80' : '#3b82f6'}
        />
        <MetricCard
          title="Упоминаний"
          value={social.times_mentioned}
          subtitle="другими учениками"
          icon="@"
        />
        <MetricCard
          title="Индекс влияния"
          value={`${social.influence_score}/100`}
          color={
            social.influence_score >= 50 ? '#4ade80' :
            social.influence_score >= 20 ? '#fbbf24' : '#9ca3af'
          }
        />
      </div>
      
      {social.avg_sentiment !== null && (
        <div className="sentiment-bar">
          <span className="sentiment-label">Тональность:</span>
          <div className="sentiment-indicator">
            {social.avg_sentiment > 0.3 ? '😊 Позитивная' :
             social.avg_sentiment < -0.3 ? '😤 Негативная' : '😐 Нейтральная'}
          </div>
        </div>
      )}
    </div>
  );
}

function InsightsCard({ insights, recommendations, riskLevel }) {
  if (!insights?.length && !recommendations?.length) return null;

  return (
    <div className="profile-card insights-card">
      <h3>
        🎯 Ключевые выводы
        <span 
          className="risk-badge"
          style={{ backgroundColor: RISK_COLORS[riskLevel] }}
        >
          Риск: {riskLevel === 'high' ? 'Высокий' : riskLevel === 'medium' ? 'Средний' : 'Низкий'}
        </span>
      </h3>
      
      {insights?.length > 0 && (
        <div className="insights-list">
          {insights.map((insight, i) => (
            <div key={i} className="insight-item">{insight}</div>
          ))}
        </div>
      )}
      
      {recommendations?.length > 0 && (
        <div className="recommendations-list">
          <h4>📋 Рекомендации</h4>
          {recommendations.map((rec, i) => (
            <div 
              key={i} 
              className={`recommendation-item priority-${rec.priority}`}
            >
              <span className="priority-badge">{rec.priority}</span>
              {rec.action}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============ Главный компонент ============

function StudentAnalyticsDashboard({ studentId, groupId }) {
  const [analytics, setAnalytics] = useState(null);
  const [activityData, setActivityData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const loadAnalytics = useCallback(async () => {
    if (!studentId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (groupId) params.append('group_id', groupId);
      params.append('period_days', '30');
      
      const [analyticsRes, activityRes] = await Promise.all([
        apiClient.get(`/analytics/extended/student/${studentId}/?${params}`),
        apiClient.get(`/analytics/extended/student/${studentId}/activity/?${params}`),
      ]);
      
      setAnalytics(analyticsRes.data);
      setActivityData(activityRes.data);
    } catch (err) {
      console.error('Failed to load analytics:', err);
      setError(err.response?.data?.detail || 'Ошибка загрузки аналитики');
    } finally {
      setLoading(false);
    }
  }, [studentId, groupId]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  if (loading) {
    return (
      <div className="analytics-loading">
        <div className="spinner"></div>
        <span>Загрузка аналитики...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-error">
        <span>❌ {error}</span>
        <button onClick={loadAnalytics}>Повторить</button>
      </div>
    );
  }

  if (!analytics) {
    return <div className="analytics-empty">Нет данных для отображения</div>;
  }

  return (
    <div className="student-analytics-dashboard">
      <div className="dashboard-header">
        <h2>📊 Аналитика: {analytics.student_name}</h2>
        <div className="header-meta">
          {analytics.group_name && <span className="group-badge">{analytics.group_name}</span>}
          <span className="period">
            {analytics.period_start} — {analytics.period_end}
          </span>
        </div>
      </div>

      <div className="dashboard-tabs">
        <button 
          className={activeTab === 'overview' ? 'active' : ''}
          onClick={() => setActiveTab('overview')}
        >
          📈 Обзор
        </button>
        <button 
          className={activeTab === 'cognitive' ? 'active' : ''}
          onClick={() => setActiveTab('cognitive')}
        >
          🧠 Когнитивный
        </button>
        <button 
          className={activeTab === 'errors' ? 'active' : ''}
          onClick={() => setActiveTab('errors')}
        >
          ❌ Ошибки
        </button>
        <button 
          className={activeTab === 'social' ? 'active' : ''}
          onClick={() => setActiveTab('social')}
        >
          👥 Социальный
        </button>
      </div>

      <div className="dashboard-content">
        {activeTab === 'overview' && (
          <div className="overview-tab">
            <div className="metrics-grid">
              <MetricCard
                title="Посещаемость"
                value={`${analytics.attendance_rate?.toFixed(0)}%`}
                icon="📅"
                color={
                  analytics.attendance_rate >= 80 ? '#4ade80' :
                  analytics.attendance_rate >= 60 ? '#fbbf24' : '#ef4444'
                }
              />
              <MetricCard
                title="Средний балл"
                value={analytics.avg_score?.toFixed(1) || '—'}
                trend={analytics.score_trend}
                icon="🎯"
              />
              <MetricCard
                title="Уровень риска"
                value={analytics.risk_level === 'high' ? 'Высокий' : 
                       analytics.risk_level === 'medium' ? 'Средний' : 'Низкий'}
                icon={analytics.risk_level === 'high' ? '🔴' : 
                      analytics.risk_level === 'medium' ? '🟡' : '🟢'}
                color={RISK_COLORS[analytics.risk_level]}
              />
            </div>
            
            <InsightsCard 
              insights={analytics.key_insights}
              recommendations={analytics.recommendations}
              riskLevel={analytics.risk_level}
            />
            
            <MotivationProfileCard 
              motivation={analytics.motivation}
              energy={analytics.energy}
            />
          </div>
        )}

        {activeTab === 'cognitive' && (
          <div className="cognitive-tab">
            <CognitiveProfileCard cognitive={analytics.cognitive} />
            
            {activityData?.heatmap && (
              <ActivityHeatmap 
                heatmapData={activityData.heatmap}
                optimalHours={activityData.optimal_hours}
                bestDays={activityData.best_days}
              />
            )}
          </div>
        )}

        {activeTab === 'errors' && (
          <div className="errors-tab">
            <h3>📊 Паттерны ошибок по типам вопросов</h3>
            
            {analytics.error_patterns?.length > 0 ? (
              <div className="error-patterns-grid">
                {analytics.error_patterns.map((pattern, i) => (
                  <ErrorPatternCard key={i} pattern={pattern} />
                ))}
              </div>
            ) : (
              <div className="no-data-message">
                Недостаточно данных для анализа ошибок
              </div>
            )}
          </div>
        )}

        {activeTab === 'social' && (
          <div className="social-tab">
            <SocialProfileCard social={analytics.social} />
          </div>
        )}
      </div>
    </div>
  );
}

export default StudentAnalyticsDashboard;
