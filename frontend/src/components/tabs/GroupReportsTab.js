/**
 * GroupReportsTab.js
 * Таб отчетов группы — компактная таблица со статистикой
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../../apiService';
import './GroupReportsTab.css';

/* ─────────────────────────────────────────────
   HELPER: Цвет по проценту
   ───────────────────────────────────────────── */
const getPercentClass = (pct) => {
  if (pct >= 80) return 'grt-good';
  if (pct >= 50) return 'grt-warn';
  return 'grt-bad';
};

/* ─────────────────────────────────────────────
   ГЛАВНЫЙ КОМПОНЕНТ
   ───────────────────────────────────────────── */
const GroupReportsTab = ({ groupId }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadGroupReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  /* ── Состояния загрузки / ошибки ── */
  if (loading) {
    return (
      <div className="grt-loading">
        <div className="grt-spinner" />
        <span>Загрузка отчёта...</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="grt-error">
        <span className="grt-error-icon">⚠️</span>
        {error}
        <button className="grt-retry-btn" onClick={loadGroupReport}>Повторить</button>
      </div>
    );
  }
  if (!report) {
    return <div className="grt-empty">Нет данных для отображения</div>;
  }

  const students = Array.isArray(report.students) ? report.students : [];

  /* ── UI ── */
  return (
    <div className="group-reports-tab">

      {/* ========== СВОДКА ========== */}
      <div className="grt-stats-row">
        <div className="grt-stat">
          <span className="grt-stat-value">{report.total_students}</span>
          <span className="grt-stat-label">учеников</span>
        </div>
        <div className="grt-stat">
          <span className="grt-stat-value">{report.total_lessons}</span>
          <span className="grt-stat-label">занятий</span>
        </div>
        <div className="grt-stat">
          <span className={`grt-stat-value ${getPercentClass(report.attendance_percent)}`}>
            {report.attendance_percent}%
          </span>
          <span className="grt-stat-label">посещаемость</span>
        </div>
        <div className="grt-stat">
          <span className={`grt-stat-value ${getPercentClass(report.homework_percent)}`}>
            {report.homework_percent}%
          </span>
          <span className="grt-stat-label">сдача ДЗ</span>
        </div>
      </div>

      {/* ========== ТАБЛИЦА ========== */}
      {students.length === 0 ? (
        <div className="grt-empty">В группе пока нет учеников</div>
      ) : (
        <div className="grt-table-wrap">
          <table className="grt-table">
            <thead>
              <tr>
                <th className="grt-th-name">Ученик</th>
                <th colSpan="4" className="grt-th-group">Посещаемость</th>
                <th colSpan="3" className="grt-th-group">Домашние задания</th>
              </tr>
              <tr className="grt-subheader">
                <th></th>
                <th>%</th>
                <th>Был</th>
                <th>Пропуск</th>
                <th>Опоздал</th>
                <th>%</th>
                <th>Сдано</th>
                <th>Не сдано</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => {
                const att = s.attendance || {};
                const hw = s.homework || {};
                return (
                  <tr key={s.student_id}>
                    <td className="grt-cell-name">
                      <span className="grt-name">{s.name || s.email}</span>
                    </td>
                    <td className={`grt-cell-pct ${getPercentClass(att.percent ?? 0)}`}>
                      {att.percent ?? 0}%
                    </td>
                    <td className="grt-cell-num grt-c-good">{att.attended ?? 0}</td>
                    <td className="grt-cell-num grt-c-bad">{att.absent ?? 0}</td>
                    <td className="grt-cell-num grt-c-warn">{att.late ?? 0}</td>
                    <td className={`grt-cell-pct ${getPercentClass(hw.percent ?? 0)}`}>
                      {hw.percent ?? 0}%
                    </td>
                    <td className="grt-cell-num grt-c-good">{hw.submitted ?? 0}</td>
                    <td className="grt-cell-num grt-c-bad">{hw.missing ?? 0}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default GroupReportsTab;
