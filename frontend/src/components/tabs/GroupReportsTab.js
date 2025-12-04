/**
 * GroupReportsTab.js
 * Таб отчетов группы
 * Показывает сводную статистику по посещениям, ДЗ и контрольным
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../../apiService';
import './GroupReportsTab.css';

const GroupReportsTab = ({ groupId }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadGroupReport();
  }, [groupId]);

  const loadGroupReport = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(`/groups/${groupId}/report/`);
      setReport(response.data);
    } catch (err) {
      console.error('Ошибка загрузки отчета:', err);
      setError('Не удалось загрузить отчет группы');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="tab-loading">⏳ Загрузка отчета...</div>;
  }

  if (error) {
    return <div className="tab-error">⚠️ {error}</div>;
  }

  if (!report) {
    return <div className="tab-empty">📊 Нет данных для отображения</div>;
  }

  const ProgressBar = ({ value, color = '#2563eb' }) => (
    <div className="progress-bar">
      <div
        className="progress-fill"
        style={{
          width: `${value}%`,
          backgroundColor: color,
        }}
      />
      <span className="progress-value">{value}%</span>
    </div>
  );

  return (
    <div className="group-reports-tab">
      <h3 className="report-title">Сводный отчет по группе</h3>

      {/* Основная информация */}
      <div className="report-info">
        <div className="info-item">
          <span className="info-label">Название группы</span>
          <span className="info-value">{report.group_name}</span>
        </div>
        <div className="info-item">
          <span className="info-label">Всего занятий</span>
          <span className="info-value">{report.total_lessons}</span>
        </div>
        <div className="info-item">
          <span className="info-label">Всего учеников</span>
          <span className="info-value">{report.total_students}</span>
        </div>
      </div>

      {/* Статистика */}
      <div className="statistics-section">
        <h4 className="section-title">📊 Статистика по показателям</h4>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon">✅</span>
            <span className="stat-name">Посещаемость</span>
          </div>
          <ProgressBar
            value={report.attendance_percent}
            color="#10b981"
          />
          <div className="stat-description">
            {report.attendance_percent}% учеников присутствовали
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon">📝</span>
            <span className="stat-name">Домашние задания</span>
          </div>
          <ProgressBar
            value={report.homework_percent}
            color="#f59e0b"
          />
          <div className="stat-description">
            {report.homework_percent}% учеников выполняют ДЗ
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon">🎯</span>
            <span className="stat-name">Контрольные точки</span>
          </div>
          <ProgressBar
            value={report.control_points_percent}
            color="#2563eb"
          />
          <div className="stat-description">
            {report.control_points_percent}% учеников прошли контроли
          </div>
        </div>
      </div>

      {/* Примечание */}
      <div className="report-note">
        <strong>Примечание:</strong> Отчет основан на данных о посещениях, выполнении ДЗ и результатах контрольных точек.
        Обновляется в реальном времени при изменении данных.
      </div>
    </div>
  );
};

export default GroupReportsTab;
