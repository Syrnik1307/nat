/**
 * GroupRatingTab.js
 * Таб рейтинга группы в модале
 * Показывает список учеников отсортированный по очкам
 * Поддерживает фильтр по периоду (месяц или всё время)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../apiService';
import './GroupRatingTab.css';

// Генерация списка месяцев для фильтра (последние 6 месяцев)
const generatePeriodOptions = () => {
  const options = [{ value: '', label: 'За всё время' }];
  const now = new Date();
  
  for (let i = 0; i < 6; i++) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    const label = date.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' });
    options.push({ value, label: label.charAt(0).toUpperCase() + label.slice(1) });
  }
  
  return options;
};

const PERIOD_OPTIONS = generatePeriodOptions();

const GroupRatingTab = ({ groupId, onStudentClick }) => {
  const [rating, setRating] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState('');

  const loadGroupRating = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      let url = `/groups/${groupId}/rating/`;
      if (selectedPeriod) {
        url += `?month=${selectedPeriod}`;
      }
      const response = await apiClient.get(url);
      setRating(response.data);
    } catch (err) {
      console.error('Ошибка загрузки рейтинга:', err);
      setError('Не удалось загрузить рейтинг группы');
    } finally {
      setLoading(false);
    }
  }, [groupId, selectedPeriod]);

  useEffect(() => {
    loadGroupRating();
  }, [loadGroupRating]);

  const handlePeriodChange = (e) => {
    setSelectedPeriod(e.target.value);
  };

  if (loading) {
    return <div className="tab-loading">Загрузка рейтинга...</div>;
  }

  if (error) {
    return <div className="tab-error">{error}</div>;
  }

  if (!rating || !rating.students || rating.students.length === 0) {
    return <div className="tab-empty">Нет данных для отображения</div>;
  }

  return (
    <div className="group-rating-tab">
      {/* Фильтр по периоду */}
      <div className="rating-filter">
        <label className="filter-label">Период:</label>
        <select 
          className="period-select" 
          value={selectedPeriod} 
          onChange={handlePeriodChange}
        >
          {PERIOD_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        {selectedPeriod && (
          <span className="period-indicator">
            {PERIOD_OPTIONS.find(o => o.value === selectedPeriod)?.label}
          </span>
        )}
      </div>

      {/* Статистика группы */}
      {rating.group_stats && (
        <div className="rating-stats-card">
          <div className="stat-item">
            <span className="stat-label">Всего учеников</span>
            <span className="stat-value">{rating.group_stats.total_students}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Средний балл</span>
            <span className="stat-value">{rating.group_stats.average_points}</span>
          </div>
        </div>
      )}

      {/* Таблица рейтинга */}
      <div className="table-wrapper">
        <table className="rating-table">
          <thead>
            <tr>
              <th className="place-col">Место</th>
              <th className="student-col">Ученик</th>
              <th className="points-col">Всего</th>
              <th className="breakdown-col">Посещ.</th>
              <th className="breakdown-col">ДЗ</th>
              <th className="breakdown-col">Контр.</th>
            </tr>
          </thead>
          <tbody>
            {rating.students.map((student, index) => (
              <tr key={student.student_id} className="rating-row">
                <td className="place-col">
                  <div className="place-badge">
                    {index === 0 && <span className="place-medal">1</span>}
                    {index === 1 && <span className="place-medal">2</span>}
                    {index === 2 && <span className="place-medal">3</span>}
                    {index > 2 && <span className="place-number">{index + 1}</span>}
                  </div>
                </td>
                <td className="student-col">
                  <button
                    className="student-link"
                    onClick={() => onStudentClick && onStudentClick(student.student_id, groupId)}
                  >
                    <span className="student-avatar">{(student.student_name || '?').charAt(0).toUpperCase()}</span>
                    <div className="student-info">
                      <span className="name">{student.student_name}</span>
                      <span className="email">{student.email}</span>
                    </div>
                  </button>
                </td>
                <td className="points-col">
                  <span className="points-value">{student.total_points}</span>
                </td>
                <td className="breakdown-col">
                  <span className="breakdown-value" title="Очки за посещение">
                    {student.attendance_points}
                  </span>
                </td>
                <td className="breakdown-col">
                  <span className="breakdown-value" title="Очки за ДЗ">
                    {student.homework_points}
                  </span>
                </td>
                <td className="breakdown-col">
                  <span className="breakdown-value" title="Очки за контрольные">
                    {student.control_points}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Легенда */}
      <div className="rating-legend">
        <div className="legend-title">Как считаются очки:</div>
        <div className="legend-items">
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#10b981' }}></span>
            <span>+10 за посещение урока</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#f59e0b' }}></span>
            <span>Сумма баллов за ДЗ (total_score), -10 за просрок дедлайна</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#2563eb' }}></span>
            <span>Баллы за контрольные точки</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GroupRatingTab;
