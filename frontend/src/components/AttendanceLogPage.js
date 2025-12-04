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
  getLessons,
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
  const [lessonColumns, setLessonColumns] = useState([]);
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
      const [groupResponse, logResponse, lessonsResponse] = await Promise.all([
        getGroup(groupId),
        getGroupAttendanceLog(groupId),
        getLessons({ group: groupId }),
      ]);

      const lessonsFromLog = logResponse.data?.lessons || [];
      const lessonsPayload = Array.isArray(lessonsResponse.data)
        ? lessonsResponse.data
        : lessonsResponse.data?.results || [];

      const lessonsMap = new Map();
      lessonsPayload.forEach((lesson) => {
        lessonsMap.set(lesson.id, {
          id: lesson.id,
          title: lesson.title,
          start_time: lesson.start_time,
          end_time: lesson.end_time,
        });
      });
      lessonsFromLog.forEach((lesson) => {
        const existing = lessonsMap.get(lesson.id) || {};
        lessonsMap.set(lesson.id, {
          id: lesson.id,
          title: lesson.title || existing.title,
          start_time: lesson.start_time || existing.start_time,
          end_time: lesson.end_time || existing.end_time,
        });
      });

      const mergedLessons = Array.from(lessonsMap.values()).sort((a, b) => {
        const aTime = a.start_time ? new Date(a.start_time).getTime() : 0;
        const bTime = b.start_time ? new Date(b.start_time).getTime() : 0;
        return aTime - bTime;
      });

      setLessonColumns(mergedLessons);
      setGroup(groupResponse.data);
      setLog({
        ...logResponse.data,
        lessons: mergedLessons,
      });
      const updatedAt = logResponse.data?.meta?.updated_at;
      setLastUpdated(updatedAt ? new Date(updatedAt) : new Date());
    } catch (err) {
      console.error('Ошибка загрузки данных:', err);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  };

  const MIN_COLUMNS = 6;
  const actualLessons = lessonColumns.length ? lessonColumns : log?.lessons || [];
  const displayLessons = useMemo(() => {
    const base = actualLessons.length ? actualLessons : [];
    if (base.length >= MIN_COLUMNS) {
      return base;
    }
    const placeholdersNeeded = MIN_COLUMNS - base.length;
    const placeholders = Array.from({ length: placeholdersNeeded }, (_, idx) => ({
      id: `placeholder-${idx}`,
      title: `Занятие ${base.length + idx + 1}`,
      start_time: null,
      isPlaceholder: true,
    }));
    return [...base, ...placeholders];
  }, [actualLessons]);

  const lessons = displayLessons;
  const students = log?.students || [];
  const records = log?.records || {};
  const actualLessonCount = actualLessons.length;
  const displayedLessonCount = actualLessonCount || lessons.length;

  const computedData = useMemo(() => {
    if (!log || !students.length || !lessons.length) {
      return {
        rows: [],
        stats: { avgAttendance: 0, watched: 0, absences: 0, lessonsCount: displayedLessonCount },
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

      const attendancePercent = actualLessonCount
        ? Math.round((stats.attended / actualLessonCount) * 100)
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
          stats: { avgAttendance, watched, absences, lessonsCount: displayedLessonCount },
    };
        }, [log, students, lessons, records, actualLessonCount, displayedLessonCount]);

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

  const { rows } = computedData;
  const hasStudents = Boolean(rows.length);
  const hasLessons = Boolean(lessons.length);
  const showEmptyMessage = !hasStudents || !hasLessons;
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

      <div className="attendance-board">
        <div className="board-toolbar">
          <div className="board-meta">
            <p className="board-updated">Обновлено {updatedAtLabel}</p>
          </div>
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
          <table className="attendance-table compact">
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
                      {row.stats.attended} из {displayedLessonCount}
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

        {showEmptyMessage && (
          <div className="board-empty">Пока нет данных по посещениям</div>
        )}

        <div className="attendance-legend">
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
  );
};

export default AttendanceLogPage;
