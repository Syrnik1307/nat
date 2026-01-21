import React, { useState, useEffect } from 'react';
import { apiClient, withScheduleApiBase } from '../apiService';
import './StorageStats.css';

const StorageStats = ({ onClose }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('storage/gdrive-stats/all/', withScheduleApiBase());
      setStats(response.data);
      setError('');
    } catch (err) {
      console.error('Failed to load storage stats:', err);
      setError(err.response?.data?.error || 'Ошибка загрузки статистики');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="storage-stats-modal">
        <div className="storage-stats-content">
          <div className="loading">Загрузка статистики...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="storage-stats-modal">
        <div className="storage-stats-content">
          <div className="storage-stats-header">
            <h2>Статистика хранилища</h2>
            <button onClick={onClose} className="close-btn">×</button>
          </div>
          <div className="error-message">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="storage-stats-modal" onClick={onClose}>
      <div className="storage-stats-content" onClick={e => e.stopPropagation()}>
        <div className="storage-stats-header">
          <h2>Статистика хранилища Google Drive</h2>
          <button onClick={onClose} className="close-btn">×</button>
        </div>

        {stats && (
          <>
            <div className="summary-cards">
              <div className="summary-card">
                <div className="card-label">Всего учителей</div>
                <div className="card-value">{stats.summary.total_teachers}</div>
              </div>
              <div className="summary-card">
                <div className="card-label">Общий объём</div>
                <div className="card-value">{stats.summary.total_size_gb.toFixed(2)} GB</div>
              </div>
              <div className="summary-card">
                <div className="card-label">Всего файлов</div>
                <div className="card-value">{stats.summary.total_files}</div>
              </div>
            </div>

            <div className="teachers-table-wrapper">
              <table className="teachers-table">
                <thead>
                  <tr>
                    <th>Учитель</th>
                    <th>Email</th>
                    <th>Размер (GB)</th>
                    <th>Файлов</th>
                    <th>Записи</th>
                    <th>ДЗ</th>
                    <th>Материалы</th>
                    <th>Студенты</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.teachers.map(teacher => (
                    <tr key={teacher.teacher_id}>
                      <td className="teacher-name">{teacher.teacher_name}</td>
                      <td className="teacher-email">{teacher.teacher_email}</td>
                      <td className="size-cell">
                        <strong>{teacher.total_size_gb.toFixed(2)} GB</strong>
                      </td>
                      <td>{teacher.total_files}</td>
                      <td className="breakdown-cell">
                        {teacher.recordings.size_mb.toFixed(0)} MB
                        <span className="file-count">({teacher.recordings.files})</span>
                      </td>
                      <td className="breakdown-cell">
                        {teacher.homework.size_mb.toFixed(0)} MB
                        <span className="file-count">({teacher.homework.files})</span>
                      </td>
                      <td className="breakdown-cell">
                        {teacher.materials.size_mb.toFixed(0)} MB
                        <span className="file-count">({teacher.materials.files})</span>
                      </td>
                      <td className="breakdown-cell">
                        {teacher.students_data.size_mb.toFixed(0)} MB
                        <span className="file-count">({teacher.students_data.files})</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default StorageStats;
