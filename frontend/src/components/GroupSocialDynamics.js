import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../apiService';
import './GroupSocialDynamics.css';

/**
 * Компонент социальной динамики группы
 * Показывает: роли учеников, влиятельность, взаимодействия, рейтинг
 */

const ROLE_ICONS = {
  leader: '👑',
  helper: '🤝',
  active: '💬',
  observer: '👀',
  silent: '🔇',
};

const ROLE_COLORS = {
  leader: '#fbbf24',
  helper: '#4ade80',
  active: '#3b82f6',
  observer: '#94a3b8',
  silent: '#e2e8f0',
};

function StudentSocialCard({ student, onViewDetails }) {
  return (
    <div 
      className="student-social-card"
      style={{ borderLeftColor: ROLE_COLORS[student.detected_role] }}
      onClick={() => onViewDetails?.(student.student_id)}
    >
      <div className="card-header">
        <span className="role-icon">{ROLE_ICONS[student.detected_role]}</span>
        <span className="student-name">{student.student_name}</span>
        <span 
          className="influence-badge"
          style={{ 
            opacity: student.influence_score > 20 ? 1 : 0.5,
            background: student.influence_score >= 50 ? '#dcfce7' : '#f3f4f6'
          }}
        >
          💪 {student.influence_score}
        </span>
      </div>
      
      <div className="card-stats">
        <div className="stat">
          <span className="stat-value">{student.total_messages}</span>
          <span className="stat-label">💬 Сообщений</span>
        </div>
        <div className="stat">
          <span className="stat-value">{student.questions_asked}</span>
          <span className="stat-label">❓ Вопросов</span>
        </div>
        <div className="stat">
          <span className="stat-value">{student.answers_given}</span>
          <span className="stat-label">💡 Ответов</span>
        </div>
        <div className="stat">
          <span className="stat-value">{student.times_mentioned}</span>
          <span className="stat-label">@ Упоминаний</span>
        </div>
      </div>
      
      {student.avg_sentiment !== null && (
        <div className="sentiment-row">
          Тональность: {
            student.avg_sentiment > 0.3 ? '😊 Позитивная' :
            student.avg_sentiment < -0.3 ? '😤 Негативная' : '😐 Нейтральная'
          }
        </div>
      )}
    </div>
  );
}

function RolesDistribution({ rolesCount }) {
  const roles = [
    { key: 'leader', label: 'Лидеры' },
    { key: 'helper', label: 'Помощники' },
    { key: 'active', label: 'Активные' },
    { key: 'observer', label: 'Наблюдатели' },
    { key: 'silent', label: 'Молчуны' },
  ];

  const total = Object.values(rolesCount).reduce((a, b) => a + b, 0);

  return (
    <div className="roles-distribution">
      <h3>📊 Распределение ролей</h3>
      <div className="roles-bars">
        {roles.map(({ key, label }) => {
          const count = rolesCount[key] || 0;
          const percent = total > 0 ? (count / total) * 100 : 0;
          
          return (
            <div key={key} className="role-bar-row">
              <span className="role-icon-small">{ROLE_ICONS[key]}</span>
              <span className="role-bar-label">{label}</span>
              <div className="role-bar-container">
                <div 
                  className="role-bar-fill"
                  style={{ 
                    width: `${percent}%`,
                    backgroundColor: ROLE_COLORS[key]
                  }}
                />
              </div>
              <span className="role-bar-count">{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RankingsTable({ rankings }) {
  const getMedalEmoji = (rank) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
  };

  return (
    <div className="rankings-table-container">
      <h3>🏆 Рейтинг группы</h3>
      <table className="rankings-table">
        <thead>
          <tr>
            <th>Место</th>
            <th>Ученик</th>
            <th>Баллы</th>
            <th>Посещаемость</th>
            <th>Ср. оценка</th>
          </tr>
        </thead>
        <tbody>
          {rankings.map((student) => (
            <tr key={student.student_id} className={student.rank <= 3 ? 'top-rank' : ''}>
              <td className="rank-cell">{getMedalEmoji(student.rank)}</td>
              <td className="name-cell">{student.student_name}</td>
              <td className="points-cell">
                <span className="points-badge">{student.total_points}</span>
              </td>
              <td className="attendance-cell">
                <span 
                  className="attendance-badge"
                  style={{
                    backgroundColor: 
                      student.attendance_rate >= 80 ? '#dcfce7' :
                      student.attendance_rate >= 60 ? '#fef3c7' : '#fee2e2'
                  }}
                >
                  {student.attendance_rate}%
                </span>
              </td>
              <td className="score-cell">
                {student.avg_score !== null ? student.avg_score : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GroupSocialDynamics({ groupId, onStudentClick }) {
  const [socialData, setSocialData] = useState(null);
  const [rankings, setRankings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState('social'); // social, rankings
  const [recalculating, setRecalculating] = useState(false);

  const loadData = useCallback(async () => {
    if (!groupId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const [socialRes, rankingsRes] = await Promise.all([
        apiClient.get(`/analytics/extended/group/${groupId}/social/`),
        apiClient.get(`/analytics/extended/group/${groupId}/rankings/`),
      ]);
      
      setSocialData(socialRes.data);
      setRankings(rankingsRes.data);
    } catch (err) {
      console.error('Failed to load group dynamics:', err);
      setError(err.response?.data?.detail || 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRecalculate = async () => {
    setRecalculating(true);
    try {
      await apiClient.post('/analytics/extended/recalculate-chat/', {
        group_id: groupId,
      });
      await loadData();
    } catch (err) {
      console.error('Failed to recalculate:', err);
    } finally {
      setRecalculating(false);
    }
  };

  if (loading) {
    return (
      <div className="group-dynamics-loading">
        <div className="spinner"></div>
        <span>Загрузка динамики группы...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="group-dynamics-error">
        <span>❌ {error}</span>
        <button onClick={loadData}>Повторить</button>
      </div>
    );
  }

  return (
    <div className="group-social-dynamics">
      <div className="dynamics-header">
        <h2>👥 Социальная динамика: {socialData?.group_name}</h2>
        <div className="header-actions">
          <span className="period-label">
            {socialData?.period_start} — {socialData?.period_end}
          </span>
          <button 
            className="recalculate-btn"
            onClick={handleRecalculate}
            disabled={recalculating}
          >
            {recalculating ? '⏳ Пересчёт...' : '🔄 Пересчитать'}
          </button>
        </div>
      </div>

      <div className="view-toggle">
        <button 
          className={activeView === 'social' ? 'active' : ''}
          onClick={() => setActiveView('social')}
        >
          👥 Роли и активность
        </button>
        <button 
          className={activeView === 'rankings' ? 'active' : ''}
          onClick={() => setActiveView('rankings')}
        >
          🏆 Рейтинг
        </button>
      </div>

      {activeView === 'social' && (
        <div className="social-view">
          <RolesDistribution rolesCount={socialData?.roles_distribution || {}} />
          
          <div className="students-grid">
            <h3>📋 Участники группы ({socialData?.total_students})</h3>
            <div className="students-cards">
              {socialData?.students?.map(student => (
                <StudentSocialCard 
                  key={student.student_id}
                  student={student}
                  onViewDetails={onStudentClick}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {activeView === 'rankings' && rankings && (
        <RankingsTable rankings={rankings.rankings} />
      )}
    </div>
  );
}

export default GroupSocialDynamics;
