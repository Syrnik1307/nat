import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Select } from '../../../../shared/components';
import { getSubmissions } from '../../../../apiService';
import './GradedSubmissionsList.css';

const GradedSubmissionsList = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const groupIdFromUrl = searchParams.get('group');
  
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [groups, setGroups] = useState([]);
  const [searchText, setSearchText] = useState('');
  const [selectedGroup, setSelectedGroup] = useState(groupIdFromUrl || '');
  const effectiveGroup = groupIdFromUrl || selectedGroup;

  const loadGroups = useCallback(async () => {
    try {
      const res = await fetch('/api/groups/');
      const data = await res.json();
      const arr = Array.isArray(data) ? data : data.results || [];
      setGroups(arr);
    } catch (err) {
      console.error('Error loading groups', err);
    }
  }, []);

  const loadGradedSubmissions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        status: 'graded',
        ordering: '-graded_at',
      };
      
      if (effectiveGroup === 'individual') {
        params.individual = 1;
      } else if (effectiveGroup) {
        params.group_id = effectiveGroup;
      }
      
      const response = await getSubmissions(params);
      const data = Array.isArray(response.data) ? response.data : response.data.results || [];
      setSubmissions(data);
    } catch (err) {
      console.error('Error loading graded submissions:', err);
      setError('Не удалось загрузить проверенные работы');
    } finally {
      setLoading(false);
    }
  }, [effectiveGroup]);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  useEffect(() => {
    loadGradedSubmissions();
  }, [loadGradedSubmissions]);

  useEffect(() => {
    if (groupIdFromUrl) {
      setSelectedGroup(groupIdFromUrl);
    }
  }, [groupIdFromUrl]);

  const handleViewSubmission = (submissionId) => {
    navigate(`/submissions/${submissionId}/review`);
  };

  const handleGroupChange = (event) => {
    const nextValue = event.target.value;
    setSelectedGroup(nextValue);
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
    if (score == null || !maxScore) return '#64748B';
    const percentage = (score / maxScore) * 100;
    if (percentage >= 80) return '#10B981';
    if (percentage >= 60) return '#F59E0B';
    return '#EF4444';
  };

  const filteredSubmissions = submissions.filter(sub => {
    if (searchText) {
      const searchLower = searchText.toLowerCase();
      const studentName = sub.student_name?.toLowerCase() || '';
      const homeworkTitle = sub.homework_title?.toLowerCase() || '';
      if (!studentName.includes(searchLower) && !homeworkTitle.includes(searchLower)) {
        return false;
      }
    }
    return true;
  });

  const isIndividual = (item) => {
    const flag = item?.is_individual;
    return flag === true || flag === 1 || flag === '1' || flag === 'true';
  };

  const displayedSubmissions = filteredSubmissions.filter((item) => {
    if (effectiveGroup === 'individual') return isIndividual(item);
    if (effectiveGroup) return String(item.group_id) === String(effectiveGroup);
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
      <div className="graded-controls">
        <input
          type="text"
          placeholder="Поиск по ученику или заданию..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className="graded-search"
        />
        <Select
          value={selectedGroup}
          onChange={handleGroupChange}
          options={[
            { value: '', label: 'Все группы' },
            ...groups.map((group) => ({ value: group.id, label: group.name })),
            { value: 'individual', label: 'Индивидуальные' },
          ]}
          placeholder="Все группы"
          className="graded-select"
        />
      </div>

      {displayedSubmissions.length === 0 ? (
        <div className="graded-empty">
          <div className="empty-icon">📚</div>
          <h3>Нет проверенных работ</h3>
          <p>Завершенные домашние задания появятся здесь</p>
        </div>
      ) : (
        <div className="graded-grid">
          {Object.entries(
            displayedSubmissions.reduce((acc, sub) => {
              const key = sub.group_name || (isIndividual(sub) ? 'Индивидуальные' : 'Без группы');
              if (!acc[key]) acc[key] = [];
              acc[key].push(sub);
              return acc;
            }, {})
          ).sort(([a], [b]) => a.localeCompare(b, 'ru')).map(([groupLabel, items]) => (
            <div key={groupLabel} className="graded-group">
              <div className="graded-group-header">
                <h3 className="graded-group-title">{groupLabel}</h3>
                <span className="graded-group-count">{items.length} шт.</span>
              </div>
              <div className="graded-group-items">
                {items.map(sub => (
                  <div key={sub.id} className="graded-card">
                    <div className="graded-card-score">
                      <span style={{ color: getScoreColor(sub.total_score, sub.max_score) }}>
                        {sub.total_score ?? '—'} / {sub.max_score}
                      </span>
                    </div>
                    <div className="graded-card-title">{sub.homework_title}</div>
                    <div className="graded-card-student">{sub.student_name}</div>
                    <div className="graded-card-dates">
                      <div>Отправлено: {formatDate(sub.submitted_at)}</div>
                      <div>Проверено: {formatDate(sub.graded_at)}</div>
                    </div>
                    <button 
                      onClick={() => handleViewSubmission(sub.id)}
                      className="graded-card-btn"
                    >
                      Открыть
                    </button>
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
