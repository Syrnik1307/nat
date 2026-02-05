import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient, getSubmissions } from '../../../../apiService';
import { Select } from '../../../../shared/components';
import './SubmissionsList.css';

const SubmissionsList = ({ filterStatus = 'submitted' }) => {
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState('');

  const loadGroups = useCallback(async () => {
    try {
      const response = await apiClient.get('/groups/');
      const data = Array.isArray(response.data) ? response.data : response.data.results || [];
      setGroups(data);
    } catch (err) {
      console.error('Error loading groups:', err);
    }
  }, []);

  const loadSubmissions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      
      if (filterStatus !== 'all') {
        params.status = filterStatus;
      }
      
      if (selectedGroup === 'individual') {
        params.individual = 1;
      } else if (selectedGroup) {
        params.group_id = selectedGroup;
      }
      
      const response = await getSubmissions(params);
      const data = Array.isArray(response.data) 
        ? response.data 
        : response.data.results || [];
      
      setSubmissions(data);
    } catch (err) {
      console.error('Error loading submissions:', err);
      setError(err.response?.data?.error || 'Failed to load submissions');
    } finally {
      setLoading(false);
    }
  }, [filterStatus, selectedGroup]);

  useEffect(() => {
    loadSubmissions();
  }, [loadSubmissions]);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  const getStatusLabel = (status) => {
    const labels = {
      'in_progress': 'В работе',
      'submitted': 'Отправлено',
      'graded': 'Проверено'
    };
    return labels[status] || status;
  };

  const filteredSubmissions = submissions.filter(sub => {
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const studentMatch = sub.student_name?.toLowerCase().includes(term) ||
                           sub.student_email?.toLowerCase().includes(term);
      const homeworkMatch = sub.homework_title?.toLowerCase().includes(term);
      
      if (!studentMatch && !homeworkMatch) return false;
    }
    return true;
  });

  const isIndividual = (item) => {
    const flag = item?.is_individual;
    return flag === true || flag === 1 || flag === '1' || flag === 'true';
  };

  const displayedSubmissions = filteredSubmissions.filter((item) => {
    if (selectedGroup === 'individual') return isIndividual(item);
    if (selectedGroup) return String(item.group_id) === String(selectedGroup);
    return true;
  });

  const needsReview = displayedSubmissions.length;

  if (loading) {
    return (
      <div className="sl-container">
        <div className="sl-loading">Загрузка работ...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="sl-container">
        <div className="sl-error">{error}</div>
        <button className="sl-btn-retry" onClick={loadSubmissions}>
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <div className="sl-container">
      <div className="sl-header">
        <div>
          <h1 className="sl-title">
            {filterStatus === 'submitted' ? 'ДЗ на проверку' : 'Все работы'}
          </h1>
          <div className="sl-stats">
            <span className="sl-stat">Найдено: {needsReview}</span>
          </div>
        </div>
        <button className="sl-btn-refresh" onClick={loadSubmissions}>
          ↻ Обновить
        </button>
      </div>

      <div className="sl-controls">
        <input
          type="text"
          placeholder="Поиск по ученику или заданию..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="sl-search-input"
        />
        <Select
          value={selectedGroup}
          onChange={(e) => setSelectedGroup(e.target.value)}
          options={[
            { value: '', label: 'Все группы' },
            ...groups.map((group) => ({ value: group.id, label: group.name })),
            { value: 'individual', label: 'Индивидуальные' },
          ]}
          placeholder="Все группы"
          className="sl-filter-select"
        />
      </div>
      
      {displayedSubmissions.length === 0 ? (
        <div className="sl-empty">
          {searchTerm || selectedGroup 
            ? 'Работ по выбранным фильтрам не найдено'
            : 'Пока нет работ для проверки'}
        </div>
      ) : (
        <div className="sl-table-container">
          {Object.entries(
            displayedSubmissions.reduce((acc, item) => {
              const key = item.group_name || (isIndividual(item) ? 'Индивидуальные' : 'Без группы');
              if (!acc[key]) acc[key] = [];
              acc[key].push(item);
              return acc;
            }, {})
          )
            .sort(([aKey], [bKey]) => aKey.localeCompare(bKey, 'ru'))
            .map(([groupLabel, items]) => (
              <div key={groupLabel} className="sl-group-block">
                <div className="sl-group-header">
                  <span className="sl-group-title">{groupLabel}</span>
                  <span className="sl-group-count">{items.length}</span>
                </div>
                <table className="sl-table">
                  <thead>
                    <tr>
                      <th>Ученик</th>
                      <th>Задание</th>
                      <th>Статус</th>
                      <th>Отправлено</th>
                      <th>Инфо</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map(sub => (
                      <tr key={sub.id} className="sl-table-row">
                        <td className="sl-student-name">{sub.student_name}</td>
                        <td>{sub.homework_title}</td>
                        <td>
                          <span className={`sl-status sl-status-${sub.status}`}>
                            {getStatusLabel(sub.status)}
                          </span>
                        </td>
                        <td className="sl-date">{sub.submitted_at ? new Date(sub.submitted_at).toLocaleDateString('ru-RU') : '—'}</td>
                        <td className="sl-telemetry-cell">
                          {(sub.has_paste_flags || sub.total_tab_switches > 5) && (
                            <span 
                              className="sl-telemetry-alert" 
                              title={`${sub.paste_count ? `Вставок: ${sub.paste_count}` : ''}${sub.paste_count && sub.total_tab_switches > 5 ? ', ' : ''}${sub.total_tab_switches > 5 ? `Перекл. вкладок: ${sub.total_tab_switches}` : ''}`}
                            >
                              !
                            </span>
                          )}
                        </td>
                        <td>
                          <button 
                            className="sl-btn-view"
                            onClick={() => navigate(`/submissions/${sub.id}/review`)}
                          >
                            Открыть
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
        </div>
      )}
    </div>
  );
};

export default SubmissionsList;
