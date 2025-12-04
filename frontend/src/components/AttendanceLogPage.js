/**
 * AttendanceLogPage.js
 * Отдельная страница журнала посещений для группы
 * Полноценная страница вместо скачивания CSV
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getGroupAttendanceLog,
  updateGroupAttendanceLog,
  getGroup,
} from '../apiService';
import AttendanceStatusPicker from './AttendanceStatusPicker';
import './AttendanceLogPage.css';

const STATUS_META = {
  attended: { label: 'Был на занятии', short: '✓', className: 'status-attended' },
  absent: { label: 'Не был', short: '✗', className: 'status-absent' },
  watched_recording: { label: 'Посмотрел запись', short: '👁', className: 'status-watched' },
  default: { label: 'Нет статуса', short: '–', className: 'status-empty' },
};

const formatDate = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
};

const getStatusMeta = (status) => STATUS_META[status] || STATUS_META.default;
const formatPercent = (value) => `${Math.max(0, Math.min(100, Math.round(value || 0)))}%`;

const AttendanceLogPage = () => {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const [group, setGroup] = useState(null);
  const [log, setLog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCell, setSelectedCell] = useState(null);
  const [updating, setUpdating] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const tableWrapperRef = useRef(null);

  useEffect(() => {
    loadData();
  }, [groupId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [groupResponse, logResponse] = await Promise.all([
        getGroup(groupId),
        getGroupAttendanceLog(groupId),
      ]);
      setGroup(groupResponse.data);
      setLog(logResponse.data);
      const updatedAt = logResponse.data?.meta?.updated_at;
      setLastUpdated(updatedAt ? new Date(updatedAt) : new Date());
    } catch (err) {
      console.error('Ошибка загрузки данных:', err);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  };

  const lessons = log?.lessons || [];
  const students = log?.students || [];
  const records = log?.records || {};

  const computedData = useMemo(() => {
    if (!log || !students.length || !lessons.length) {
      return {
        rows: [],
        stats: { avgAttendance: 0, watched: 0, absences: 0, lessonsCount: lessons.length },
      };
    }

    const rows = students.map((student) => {
      const stats = { attended: 0, watched: 0, absent: 0, empty: 0 };

      const lessonStatuses = lessons.map((lesson) => {
        const key = `${student.id}_${lesson.id}`;
        const record = records[key];
        const status = record?.status || null;

        if (status === 'attended') stats.attended += 1;
        else if (status === 'watched_recording') stats.watched += 1;
        else if (status === 'absent') stats.absent += 1;
        else stats.empty += 1;

        return {
          lessonId: lesson.id,
          status,
          autoRecorded: Boolean(record?.auto_recorded),
        };
      });

      const attendancePercent = lessons.length
        ? Math.round((stats.attended / lessons.length) * 100)
        : 0;

      return { student, stats, lessonStatuses, attendancePercent };
    });

    const totalStudents = rows.length;
    const avgAttendance = totalStudents
      ? Math.round(rows.reduce((sum, row) => sum + row.attendancePercent, 0) / totalStudents)
      : 0;

    const watched = rows.reduce((sum, row) => sum + row.stats.watched, 0);
    const absences = rows.reduce((sum, row) => sum + row.stats.absent, 0);

    return {
      rows,
      stats: { avgAttendance, watched, absences, lessonsCount: lessons.length },
    };
  }, [log, students, lessons, records]);

  const handleCellClick = (studentId, lessonId, e) => {
    e.stopPropagation();
    setSelectedCell({ studentId, lessonId });
  };

  const handleStatusChange = async (status) => {
    if (!selectedCell) return;

    try {
      setUpdating(true);
      await updateGroupAttendanceLog(
        groupId,
        selectedCell.lessonId,
        selectedCell.studentId,
        status
      );
      await loadData();
      setSelectedCell(null);
    } catch (err) {
      console.error('Ошибка обновления:', err);
      setError('Не удалось сохранить изменения');
    } finally {
      setUpdating(false);
    }
  };

  const scrollTable = (direction) => {
    if (!tableWrapperRef.current) return;
    const delta = direction === 'left' ? -320 : 320;
    tableWrapperRef.current.scrollBy({ left: delta, behavior: 'smooth' });
  };

  if (loading) {
    return (
      <div className="attendance-log-page">
        <div className="page-loading">Загрузка журнала...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="attendance-log-page">
        <div className="page-error">
          <p>{error}</p>
          <button onClick={() => navigate(-1)}>Назад</button>
        </div>
      </div>
    );
  }

  const { rows, stats: computedStats } = computedData;
  const backendStats = log?.meta?.stats;
  const cardsStats = backendStats
    ? {
        avgAttendance: backendStats.avg_attendance_percent ?? 0,
        watched: backendStats.watched_total ?? 0,
        absences: backendStats.absences_total ?? 0,
        lessonsCount: backendStats.lessons_count ?? lessons.length,
      }
    : computedStats;

  const hasData = Boolean(rows.length && lessons.length);
  const updatedAtLabel = lastUpdated
    ? lastUpdated.toLocaleString('ru-RU', { 
        day: '2-digit', 
        month: '2-digit', 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    : 'только что';

  return (
    <div className="attendance-log-page">
      <div className="page-header">
        <div className="header-left">
          <button className="back-button" onClick={() => navigate(-1)}>
            ← Назад
          </button>
          <div className="header-info">
            <h1 className="page-title">Журнал посещений</h1>
            <p className="page-subtitle">{group?.name || 'Группа'}</p>
          </div>
        </div>
        <div className="header-actions">
          <button 
            className="action-button secondary" 
            onClick={loadData}
            disabled={loading}
          >
            Обновить
          </button>
        </div>
      </div>

      <div className="attendance-stats-grid">
        <div className="stat-card">
          <div className="stat-content">
            <span className="stat-label">Средняя посещаемость</span>
            <span className="stat-value">{formatPercent(cardsStats.avgAttendance)}</span>
            <span className="stat-hint">по {cardsStats.lessonsCount} занятиям</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-content">
            <span className="stat-label">Просмотрели запись</span>
            <span className="stat-value accent">{cardsStats.watched}</span>
            <span className="stat-hint">учеников вместо онлайн</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-content">
            <span className="stat-label">Пропуски</span>
            <span className="stat-value danger">{cardsStats.absences}</span>
            <span className="stat-hint">требуют внимания</span>
          </div>
        </div>
      </div>

      {!hasData ? (
        <div className="page-empty">
          <p>Пока нет данных по посещениям</p>
        </div>
      ) : (
        <div className="attendance-content">
          <div className="table-toolbar">
            <p className="table-info">Обновлено {updatedAtLabel}</p>
            <div className="table-controls">
              <button 
                className="control-button" 
                onClick={() => scrollTable('left')}
                aria-label="Прокрутить влево"
              >
                ‹
              </button>
              <button 
                className="control-button" 
                onClick={() => scrollTable('right')}
                aria-label="Прокрутить вправо"
              >
                ›
              </button>
            </div>
          </div>

          <div className="table-wrapper" ref={tableWrapperRef}>
            <table className="attendance-table">
              <thead>
                <tr>
                  <th className="student-col">Ученик</th>
                  <th className="presence-col">Посещаемость</th>
                  {lessons.map((lesson, idx) => (
                    <th key={lesson.id} className="lesson-col" title={lesson.title}>
                      <div className="lesson-index">Занятие {idx + 1}</div>
                      <div className="lesson-date">{formatDate(lesson.start_time)}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.student.id} className="student-row">
                    <td className="student-col">
                      <div className="student-info-cell">
                        <span className="avatar-circle">
                          {row.student.name?.[0] || '👤'}
                        </span>
                        <div className="student-details">
                          <span className="student-name">{row.student.name}</span>
                          <span className="student-email">{row.student.email}</span>
                        </div>
                      </div>
                    </td>
                    <td className="presence-col">
                      <span className="presence-chip">
                        {formatPercent(row.attendancePercent)}
                      </span>
                      <span className="presence-meta">
                        {row.stats.attended} из {lessons.length}
                      </span>
                    </td>
                    {row.lessonStatuses.map(({ lessonId, status, autoRecorded }) => {
                      const cellMeta = getStatusMeta(status);
                      const isSelected =
                        selectedCell?.studentId === row.student.id &&
                        selectedCell?.lessonId === lessonId;

                      return (
                        <td
                          key={`${row.student.id}_${lessonId}`}
                          className={`attendance-cell ${cellMeta.className} ${
                            isSelected ? 'selected' : ''
                          }`}
                          onClick={(e) => handleCellClick(row.student.id, lessonId, e)}
                        >
                          <span className="status-pill">{cellMeta.short}</span>
                          {autoRecorded && <span className="auto-badge">auto</span>}

                          {isSelected && (
                            <AttendanceStatusPicker
                              currentStatus={status}
                              onStatusSelect={handleStatusChange}
                              onClose={() => setSelectedCell(null)}
                              isLoading={updating}
                            />
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="attendance-legend">
            <p className="legend-title">Обозначения:</p>
            <div className="legend-items">
              {['attended', 'absent', 'watched_recording', null].map((statusKey) => {
                const meta = getStatusMeta(statusKey);
                return (
                  <div key={meta.className} className="legend-item">
                    <span className={`status-pill small ${meta.className}`}>
                      {meta.short}
                    </span>
                    <span className="legend-label">{meta.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AttendanceLogPage;
