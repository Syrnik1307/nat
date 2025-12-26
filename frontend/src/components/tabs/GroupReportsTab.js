/**
 * GroupReportsTab.js
 * Таб отчетов группы — алгоритмический дашборд
 * Показывает сводную статистику и детализацию по каждому ученику
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../../apiService';
import './GroupReportsTab.css';

/* ─────────────────────────────────────────────
   HELPER: Инициалы для аватара
   ───────────────────────────────────────────── */
const getInitials = (name, email) => {
  if (name && name.trim()) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return parts[0].slice(0, 2).toUpperCase();
  }
  return email ? email.slice(0, 2).toUpperCase() : '??';
};

/* ─────────────────────────────────────────────
   HELPER: Цвет бейджа по проценту
   ───────────────────────────────────────────── */
const getPercentVariant = (pct) => {
  if (pct >= 80) return 'success';
  if (pct >= 50) return 'warning';
  return 'danger';
};

/* ─────────────────────────────────────────────
   КОМПОНЕНТ: Мини‑прогресс бар
   ───────────────────────────────────────────── */
const MiniProgress = ({ value, variant = 'primary' }) => (
  <div className="mini-progress">
    <div className={`mini-progress-fill mini-progress-${variant}`} style={{ width: `${Math.min(100, value)}%` }} />
  </div>
);

/* ─────────────────────────────────────────────
   КОМПОНЕНТ: Бейдж‑метрика (число + подпись)
   ───────────────────────────────────────────── */
const MetricBadge = ({ icon, value, label, variant = 'neutral' }) => (
  <div className={`metric-badge metric-badge-${variant}`}>
    <span className="metric-icon">{icon}</span>
    <span className="metric-value">{value}</span>
    <span className="metric-label">{label}</span>
  </div>
);

/* ─────────────────────────────────────────────
   КОМПОНЕНТ: Карточка ученика
   ───────────────────────────────────────────── */
const StudentReportCard = ({ student, totalLessons, totalHomework }) => {
  const att = student.attendance || {};
  const hw = student.homework || {};

  const attPct = att.percent ?? 0;
  const hwPct = hw.percent ?? 0;

  return (
    <div className="student-report-card">
      {/* Заголовок: аватар + имя */}
      <div className="src-header">
        <div className="src-avatar">{getInitials(student.name, student.email)}</div>
        <div className="src-info">
          <div className="src-name">{student.name || student.email}</div>
          <div className="src-email">{student.email}</div>
        </div>
      </div>

      {/* Посещаемость */}
      <div className="src-section">
        <div className="src-section-title">
          <span className="src-section-icon">📅</span> Посещаемость
          <span className={`src-pct src-pct-${getPercentVariant(attPct)}`}>{attPct}%</span>
        </div>
        <MiniProgress value={attPct} variant={getPercentVariant(attPct)} />
        <div className="src-metrics">
          <MetricBadge icon="✓" value={att.attended ?? 0} label="был" variant="success" />
          <MetricBadge icon="✕" value={att.absent ?? 0} label="пропуск" variant="danger" />
          <MetricBadge icon="▶" value={att.watched_recording ?? 0} label="запись" variant="info" />
          <MetricBadge icon="⏰" value={att.late ?? 0} label="опоздал" variant="warning" />
        </div>
      </div>

      {/* ДЗ */}
      <div className="src-section">
        <div className="src-section-title">
          <span className="src-section-icon">📝</span> Домашние задания
          <span className={`src-pct src-pct-${getPercentVariant(hwPct)}`}>{hwPct}%</span>
        </div>
        <MiniProgress value={hwPct} variant={getPercentVariant(hwPct)} />
        <div className="src-metrics">
          <MetricBadge icon="📤" value={hw.submitted ?? 0} label="сдано" variant="success" />
          <MetricBadge icon="📭" value={hw.missing ?? 0} label="не сдано" variant="danger" />
          <MetricBadge icon="✅" value={hw.graded ?? 0} label="проверено" variant="info" />
        </div>
      </div>
    </div>
  );
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
      <section className="grt-summary">
        <div className="grt-summary-card">
          <span className="grt-summary-icon">👥</span>
          <div className="grt-summary-data">
            <span className="grt-summary-value">{report.total_students}</span>
            <span className="grt-summary-label">учеников</span>
          </div>
        </div>
        <div className="grt-summary-card">
          <span className="grt-summary-icon">📚</span>
          <div className="grt-summary-data">
            <span className="grt-summary-value">{report.total_lessons}</span>
            <span className="grt-summary-label">занятий</span>
          </div>
        </div>
        <div className="grt-summary-card grt-summary-card--accent">
          <span className="grt-summary-icon">📊</span>
          <div className="grt-summary-data">
            <span className="grt-summary-value">{report.attendance_percent}%</span>
            <span className="grt-summary-label">посещаемость</span>
          </div>
        </div>
        <div className="grt-summary-card grt-summary-card--accent">
          <span className="grt-summary-icon">✏️</span>
          <div className="grt-summary-data">
            <span className="grt-summary-value">{report.homework_percent}%</span>
            <span className="grt-summary-label">сдача ДЗ</span>
          </div>
        </div>
      </section>

      {/* ========== СПИСОК УЧЕНИКОВ ========== */}
      <section className="grt-students">
        <h4 className="grt-section-title">Детализация по ученикам</h4>

        {students.length === 0 ? (
          <div className="grt-empty">В группе пока нет учеников</div>
        ) : (
          <div className="grt-students-grid">
            {students.map((s) => (
              <StudentReportCard
                key={s.student_id}
                student={s}
                totalLessons={report.total_lessons}
                totalHomework={s.homework?.total_homework ?? 0}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default GroupReportsTab;
