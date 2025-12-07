import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient, getSubmissions } from '../../../../apiService';
import { Select, Input } from '../../../../shared/components';
import './SubmissionsList.css';

/**
 * Компонент списка работ учеников для проверки учителем
 * @param {string} filterStatus - Фильтр статуса ('submitted' для "на проверку", 'all' для всех)
 */
const SubmissionsList = ({ filterStatus = 'submitted' }) => {
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState('');

  useEffect(() => {
    loadSubmissions();
    loadGroups();
  }, [filterStatus, selectedGroup]);

  const loadGroups = async () => {
    try {
      const response = await apiClient.get('/groups/');
      const data = Array.isArray(response.data) ? response.data : response.data.results || [];
      setGroups(data);
    } catch (err) {
      console.error('Ошибка загрузки групп:', err);
    }
  };

  const loadSubmissions = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      
      // Применяем фильтр статуса
      if (filterStatus !== 'all') {
        params.status = filterStatus;
      }
      
      // Применяем фильтр по группе
      if (selectedGroup) {
        params.group_id = selectedGroup;
      }
      
      const response = await getSubmissions(params);
      
      // Предполагаем, что API возвращает массив или объект с results
      const data = Array.isArray(response.data) 
        ? response.data 
        : response.data.results || [];
      
      setSubmissions(data);
    } catch (err) {
      console.error('Ошибка загрузки работ:', err);
      setError(err.response?.data?.error || 'Не удалось загрузить список работ');
    } finally {
      setLoading(false);
    }
  };

  const getStatusLabel = (status) => {
    const labels = {
      'in_progress': 'В процессе',
      'submitted': 'Отправлено',
      'graded': 'Проверено'
    };
    return labels[status] || status;
  };

  const getStatusClass = (status) => {
    return `sl-status-${status}`;
  };

  const filteredSubmissions = submissions.filter(sub => {
    // Фильтр по поиску (группа и статус уже отфильтрованы на бэкенде)
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const studentMatch = sub.student_name?.toLowerCase().includes(term) ||
                           sub.student_email?.toLowerCase().includes(term);
      const homeworkMatch = sub.homework_title?.toLowerCase().includes(term);
      
      if (!studentMatch && !homeworkMatch) return false;
    }
    
    return true;
  });

  const needsReview = filteredSubmissions.length;

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
            {filterStatus === 'submitted' ? 'Работы на проверку' : 'Все работы'}
          </h1>
          <div className="sl-stats">
            <span className="sl-stat sl-stat-warning">Найдено работ: {needsReview}</span>
          </div>
        </div>
        <button className="sl-btn-refresh" onClick={loadSubmissions}>
          ↻ Обновить
        </button>
      </div>

      <div className="sl-controls">
        <div className="sl-search-wrapper">
          <Input
            type="text"
            placeholder="Поиск по ученику или заданию..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="sl-search-input"
          />
        </div>

        <div className="sl-filter-wrapper">
          <Select
            value={selectedGroup}
            onChange={(e) => setSelectedGroup(e.target.value)}
            options={[
              { value: '', label: 'Все группы' },
              ...groups.map(group => ({
                value: group.id,
                label: group.name
              }))
            ]}
            placeholder="Выберите группу..."
            className="sl-filter-select"
          />
        </div>
      </div>
      
      {filteredSubmissions.length === 0 ? (
        <div className="sl-empty">
          {searchTerm || selectedGroup 
            ? 'Работ по выбранным фильтрам не найдено'
            : 'Пока нет работ для проверки'}
        </div>
      ) : (
        <div className="sl-table-container">
          <table className="sl-table">
            <thead>
              <tr>
                <th>Ученик</th>
                <th>Задание</th>
                <th>Дата сдачи</th>
                <th>Статус</th>
                <th>Баллы</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {filteredSubmissions.map(submission => (
                <tr key={submission.id} className="sl-table-row">
                  <td>
                    <div className="sl-student-info">
                      <div className="sl-student-name">{submission.student_name}</div>
                      <div className="sl-student-email">{submission.student_email}</div>
                    </div>
                  </td>
                  <td className="sl-homework-title">{submission.homework_title}</td>
                  <td className="sl-date">
                    {new Date(submission.submitted_at).toLocaleDateString('ru-RU', {
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </td>
                  <td>
                    <span className={`sl-status ${getStatusClass(submission.status)}`}>
                      {getStatusLabel(submission.status)}
                    </span>
                  </td>
                  <td className="sl-score">
                    {submission.total_score !== null ? submission.total_score : '—'}
                  </td>
                  <td>
                    <button
                      className="sl-btn-review"
                      onClick={() => navigate(`/submissions/${submission.id}/review`)}
                    >
                      {submission.status === 'graded' ? 'Просмотр' : 'Проверить'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default SubmissionsList;
