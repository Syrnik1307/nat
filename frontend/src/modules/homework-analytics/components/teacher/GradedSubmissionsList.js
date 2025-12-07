import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getSubmissions } from '../../../../apiService';
import './GradedSubmissionsList.css';

/**
 * Список проверенных домашних заданий
 * Показывает архив всех проверенных работ с возможностью повторного просмотра
 */
const GradedSubmissionsList = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const groupIdFromUrl = searchParams.get('group');
  
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [groups, setGroups] = useState([]);
  const [filters, setFilters] = useState({
    search: '',
    group: groupIdFromUrl || '',
    dateFrom: '',
    dateTo: '',
  });

  useEffect(() => {
    loadGradedSubmissions();
    loadGroups();
  }, [groupIdFromUrl]);

  useEffect(() => {
    if (!groupIdFromUrl) {
      loadGradedSubmissions();
    }
  }, [filters.group, groupIdFromUrl]);

  const loadGroups = async () => {
    try {
      const res = await fetch('/api/groups/');
      const data = await res.json();
      const arr = Array.isArray(data) ? data : data.results || [];
      setGroups(arr);
    } catch (err) {
      console.error('Ошибка загрузки групп', err);
    }
  };

  const loadGradedSubmissions = async () => {
    setLoading(true);
    setError(null);
    try {
      // Загружаем submissions со статусом 'graded'
      const params = {
        status: 'graded',
        ordering: '-graded_at',
      };
      
      // Добавляем фильтр по группе если есть
      if (groupIdFromUrl) {
        params.homework__lesson__group = groupIdFromUrl;
      } else if (filters.group === 'individual') {
        params.individual = 1;
      } else if (filters.group) {
        params.group_id = filters.group;
      }
      
      const response = await getSubmissions(params);
      
      const data = Array.isArray(response.data) ? response.data : response.data.results || [];
      setSubmissions(data);
    } catch (err) {
      console.error('Ошибка загрузки проверенных работ:', err);
      setError('Не удалось загрузить проверенные работы');
    } finally {
      setLoading(false);
    }
  };

  const handleViewSubmission = (submissionId) => {
    navigate(`/submissions/${submissionId}/review`);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  const getScoreColor = (score, maxScore) => {
    if (!score || !maxScore) return '#64748B';
    const percentage = (score / maxScore) * 100;
    if (percentage >= 80) return '#10B981';
    if (percentage >= 60) return '#F59E0B';
    return '#EF4444';
  };

  // Фильтрация
  const filteredSubmissions = submissions.filter(sub => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      const studentName = sub.student_name?.toLowerCase() || '';
      const homeworkTitle = sub.homework_title?.toLowerCase() || '';
      if (!studentName.includes(searchLower) && !homeworkTitle.includes(searchLower)) {
        return false;
      }
    }
    return true;
  });

  if (loading) {
    return (
      <div className="graded-submissions-loading">
        <div className="spinner"></div>
        <p>Загрузка проверенных работ...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="graded-submissions-error">
        <span className="error-icon">⚠️</span>
        <p>{error}</p>
        <button onClick={loadGradedSubmissions} className="btn-retry">
          Повторить
        </button>
      </div>
    );
  }

  return (
    <div className="graded-submissions-list">
      {/* Фильтры */}
      <div className="graded-filters">
        <div className="filter-group">
          <input
            type="text"
            placeholder="Поиск по ученику или названию..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="filter-input"
          />
        </div>
        <div className="filter-group">
          <select
            value={filters.group}
            onChange={(e) => setFilters({ ...filters, group: e.target.value })}
            className="filter-select"
          >
            <option value="">Все группы</option>
            {groups.map(g => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
            <option value="individual">Индивидуальные</option>
          </select>
        </div>
      </div>

      {/* Список */}
      {filteredSubmissions.length === 0 ? (
        <div className="graded-empty">
          <div className="empty-icon">📚</div>
          <h3>Нет проверенных работ</h3>
          <p>Проверенные домашние задания появятся здесь</p>
        </div>
      ) : (
        <div className="graded-grid">
          {Object.entries(
            filteredSubmissions.reduce((acc, sub) => {
              const key = sub.group_name || (sub.is_individual ? 'Индивидуальные' : 'Без группы');
              if (!acc[key]) acc[key] = [];
              acc[key].push(sub);
              return acc;
            }, {})
          ).sort(([a], [b]) => a.localeCompare(b, 'ru')).map(([groupLabel, items]) => (
            <div key={groupLabel} className="graded-group">
              <div className="graded-group-header">
                <span className="graded-group-title">{groupLabel}</span>
                <span className="graded-group-count">{items.length} шт.</span>
              </div>
              <div className="graded-group-items">
                {items.map((submission) => (
                  <div key={submission.id} className="graded-card">
                    <div className="graded-card-header">
                      <div className="student-info">
                        <div className="student-avatar">🎓</div>
                        <div className="student-details">
                          <h4 className="student-name">{submission.student_name || 'Ученик'}</h4>
                          <p className="homework-title">{submission.homework_title || 'Домашнее задание'}</p>
                        </div>
                      </div>
                      <div 
                        className="score-badge"
                        style={{ 
                          color: getScoreColor(submission.total_score, submission.max_score),
                          borderColor: getScoreColor(submission.total_score, submission.max_score),
                        }}
                      >
                        {submission.total_score || 0} / {submission.max_score || 0}
                      </div>
                    </div>

                    <div className="graded-card-meta">
                      <div className="meta-item">
                        <span className="meta-label">Сдано:</span>
                        <span className="meta-value">{formatDate(submission.submitted_at)}</span>
                      </div>
                      <div className="meta-item">
                        <span className="meta-label">Проверено:</span>
                        <span className="meta-value">{formatDate(submission.graded_at)}</span>
                      </div>
                    </div>

                    <div className="graded-card-actions">
                      <button
                        onClick={() => handleViewSubmission(submission.id)}
                        className="btn-view"
                      >
                        Просмотреть
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default GradedSubmissionsList;
