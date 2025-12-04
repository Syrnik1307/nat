/**
 * GroupRatingTab.js
 * Таб рейтинга группы в модале
 * Показывает список учеников отсортированный по очкам
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../../apiService';
import './GroupRatingTab.css';

const GroupRatingTab = ({ groupId, onStudentClick }) => {
  const [rating, setRating] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadGroupRating();
  }, [groupId]);

  const loadGroupRating = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(`/groups/${groupId}/rating/`);
      setRating(response.data);
    } catch (err) {
      console.error('Ошибка загрузки рейтинга:', err);
      setError('Не удалось загрузить рейтинг группы');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="tab-loading">⏳ Загрузка рейтинга...</div>;
  }

  if (error) {
    return <div className="tab-error">⚠️ {error}</div>;
  }

  if (!rating || !rating.students || rating.students.length === 0) {
    return <div className="tab-empty">📊 Нет данных для отображения</div>;
  }

  return (
    <div className="group-rating-tab">
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
                    {index === 0 && '🥇'}
                    {index === 1 && '🥈'}
                    {index === 2 && '🥉'}
                    {index > 2 && <span className="place-number">{index + 1}</span>}
                  </div>
                </td>
                <td className="student-col">
                  <button
                    className="student-link"
                    onClick={() => onStudentClick && onStudentClick(student.student_id, groupId)}
                  >
                    <span className="student-avatar">👤</span>
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
            <span>+10 за посещение, -5 за отсутствие</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#f59e0b' }}></span>
            <span>+5 за выполненное ДЗ</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#2563eb' }}></span>
            <span>+15 за пройденную контрольную, +8 с ошибками</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GroupRatingTab;
