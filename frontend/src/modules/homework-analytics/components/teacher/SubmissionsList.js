import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../../../apiService';
import './SubmissionsList.css';

/**
 * Компонент списка работ учеников для проверки учителем
 */
const SubmissionsList = () => {
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [filter, setFilter] = useState('all'); // all, submitted, graded
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadSubmissions();
  }, []);

  const loadSubmissions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get('submissions/');
      
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
    // Фильтр по статусу
    if (filter !== 'all' && sub.status !== filter) return false;
    
    // Фильтр по поиску
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const studentMatch = sub.student_name?.toLowerCase().includes(term) ||
                           sub.student_email?.toLowerCase().includes(term);
      const homeworkMatch = sub.homework_title?.toLowerCase().includes(term);
      
      if (!studentMatch && !homeworkMatch) return false;
    }
    
    return true;
  });

  const needsReview = submissions.filter(s => s.status === 'submitted').length;
  const graded = submissions.filter(s => s.status === 'graded').length;

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
          <h1 className="sl-title">Проверка работ</h1>
          <div className="sl-stats">
            <span className="sl-stat">Всего работ: {submissions.length}</span>
            <span className="sl-stat sl-stat-warning">На проверке: {needsReview}</span>
            <span className="sl-stat sl-stat-success">Проверено: {graded}</span>
          </div>
        </div>
        <button className="sl-btn-refresh" onClick={loadSubmissions}>
          ↻ Обновить
        </button>
      </div>

      <div className="sl-controls">
        <div className="sl-search">
          <input
            type="text"
            className="sl-search-input"
            placeholder="Поиск по ученику или заданию..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="sl-filters">
          <button
            className={`sl-filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            Все
          </button>
          <button
            className={`sl-filter-btn ${filter === 'submitted' ? 'active' : ''}`}
            onClick={() => setFilter('submitted')}
          >
            На проверке
          </button>
          <button
            className={`sl-filter-btn ${filter === 'graded' ? 'active' : ''}`}
            onClick={() => setFilter('graded')}
          >
            Проверено
          </button>
        </div>
      </div>

      {filteredSubmissions.length === 0 ? (
        <div className="sl-empty">
          {searchTerm || filter !== 'all' 
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
