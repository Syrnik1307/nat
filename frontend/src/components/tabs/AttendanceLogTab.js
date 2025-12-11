/**
 * AttendanceLogTab.js
 * Таб журнала посещений в модале группы
 * Матрица: Ученик x Занятие с возможностью быстрого редактирования
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getGroupAttendanceLog,
  updateGroupAttendanceLog,
} from '../../apiService';
import AttendanceStatusPicker from '../AttendanceStatusPicker';
import './AttendanceLogTab.css';

const STATUS_META = {
  attended: { label: 'Был на занятии', short: '✓', className: 'status-attended' },
  absent: { label: 'Не был', short: '✗', className: 'status-absent' },
  watched_recording: { label: 'Посмотрел запись', short: '○', className: 'status-watched' },
  default: { label: 'Нет статуса', short: '–', className: 'status-empty' },
};

const formatDate = (value) => {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
};

const getStatusMeta = (status) => STATUS_META[status] || STATUS_META.default;

const formatPercent = (value) => `${Math.max(0, Math.min(100, Math.round(value || 0)))}%`;

const AttendanceLogTab = ({ groupId, onStudentClick }) => {
  const navigate = useNavigate();
  const [log, setLog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCell, setSelectedCell] = useState(null);
  const [updating, setUpdating] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const tableWrapperRef = useRef(null);

  useEffect(() => {
    loadAttendanceLog();
  }, [groupId]);

  useEffect(() => {
    setSelectedCell(null);
  }, [groupId]);

  const loadAttendanceLog = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getGroupAttendanceLog(groupId);
      const payload = response.data;
      setLog(payload);
      const updatedAt = payload?.meta?.updated_at;
      setLastUpdated(updatedAt ? new Date(updatedAt) : new Date());
    } catch (err) {
      console.error('Ошибка загрузки журнала посещений:', err);
      setError('Не удалось загрузить журнал посещений');
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
        stats: {
          avgAttendance: 0,
          watched: 0,
          absences: 0,
          lessonsCount: lessons.length,
        },
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

      return {
        student,
        stats,
        lessonStatuses,
        attendancePercent,
      };
    });

    const totalStudents = rows.length;
    const avgAttendance = totalStudents
      ? Math.round(rows.reduce((sum, row) => sum + row.attendancePercent, 0) / totalStudents)
      : 0;

    const watched = rows.reduce((sum, row) => sum + row.stats.watched, 0);
    const absences = rows.reduce((sum, row) => sum + row.stats.absent, 0);

    return {
      rows,
      stats: {
        avgAttendance,
        watched,
        absences,
        lessonsCount: lessons.length,
      },
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
      await loadAttendanceLog();
      setSelectedCell(null);
    } catch (err) {
      console.error('Ошибка обновления посещения:', err);
      setError('Не удалось сохранить изменения');
    } finally {
      setUpdating(false);
    }
  };

  const handleOpenFullPage = () => {
    navigate(`/attendance/${groupId}`, {
      state: {
        logSnapshot: log,
      },
    });
  };

  const scrollTable = (direction) => {
    if (!tableWrapperRef.current) return;
    const delta = direction === 'left' ? -320 : 320;
    tableWrapperRef.current.scrollBy({ left: delta, behavior: 'smooth' });
  };

  if (loading) {
    return <div className="tab-loading">Загружка журнала...</div>;
  }


  if (error) {
    return <div className="tab-error">{error}</div>;
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
    ? lastUpdated.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : 'только что';

  return (
    <div className="attendance-log-tab">
      <div className="attendance-log-toolbar">
        <div>
          <p className="toolbar-title">Данные посещений</p>
          <p className="toolbar-subtitle">Обновлено {updatedAtLabel}</p>
        </div>
        <div className="toolbar-actions">
          <button type="button" className="toolbar-icon-btn" onClick={() => scrollTable('left')} aria-label="Прокрутить влево">‹</button>
          <button type="button" className="toolbar-icon-btn" onClick={() => scrollTable('right')} aria-label="Прокрутить вправо">›</button>
          <button type="button" className="toolbar-btn ghost" onClick={loadAttendanceLog} disabled={loading}>
            Обновить
          </button>
          <button type="button" className="toolbar-btn" onClick={handleOpenFullPage}>
            Открыть полный журнал
          </button>
        </div>
      </div>

      <div className="attendance-stats-grid">
        <div className="attendance-stat-card">
          <span className="stat-label">Средняя посещаемость</span>
          <span className="stat-value">{formatPercent(cardsStats.avgAttendance)}</span>
          <span className="stat-hint">по {cardsStats.lessonsCount} занятиям</span>
        </div>
        <div className="attendance-stat-card">
          <span className="stat-label">Просмотрели запись</span>
          <span className="stat-value accent">{cardsStats.watched}</span>
          <span className="stat-hint">учеников вместо онлайн</span>
        </div>
        <div className="attendance-stat-card">
          <span className="stat-label">Пропуски</span>
          <span className="stat-value danger">{cardsStats.absences}</span>
          <span className="stat-hint">требуют внимания</span>
        </div>
      </div>

      {!hasData ? (
        <div className="tab-empty">📋 Пока нет данных по посещениям</div>
      ) : (
        <>
          <div className="table-wrapper" ref={tableWrapperRef}>
            <table className="attendance-table modern">
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
                      <button
                        className="student-summary"
                        onClick={() => onStudentClick && onStudentClick(row.student.id, groupId)}
                      >
                        <span className="avatar-circle">{row.student.name?.[0] || '?'}</span>
                        <span className="student-info">
                          <span className="student-name">{row.student.name}</span>
                          <span className="student-email">{row.student.email}</span>
                        </span>
                      </button>
                    </td>
                    <td className="presence-col">
                      <span className="presence-chip">{formatPercent(row.attendancePercent)}</span>
                      <span className="presence-meta">{row.stats.attended} из {lessons.length} занятий</span>
                    </td>
                    {row.lessonStatuses.map(({ lessonId, status, autoRecorded }) => {
                      const cellMeta = getStatusMeta(status);
                      const isSelected =
                        selectedCell?.studentId === row.student.id &&
                        selectedCell?.lessonId === lessonId;

                      return (
                        <td
                          key={`${row.student.id}_${lessonId}`}
                          className={`attendance-cell-modern ${cellMeta.className} ${isSelected ? 'selected' : ''}`}
                          onClick={(e) => handleCellClick(row.student.id, lessonId, e)}
                        >
                          <span className="status-pill">{cellMeta.short}</span>
                          <span className="status-caption">{cellMeta.label}</span>
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

          <div className="attendance-footer-note">
            <span>✔ Ответы автосохраняются после изменения статуса</span>
          </div>

          <div className="attendance-legend">
            {['attended', 'absent', 'watched_recording', null].map((statusKey) => {
              const meta = getStatusMeta(statusKey);
              return (
                <div key={meta.className} className="legend-item">
                  <span className={`status-pill small ${meta.className}`}>{meta.short}</span>
                  <span>{meta.label}</span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default AttendanceLogTab;
