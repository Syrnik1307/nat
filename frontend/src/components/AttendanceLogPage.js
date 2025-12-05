/**
 * AttendanceLogPage.js
 * Отдельная страница журнала посещений для группы
 * Полноценная страница вместо скачивания CSV
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  getGroupAttendanceLog,
  updateGroupAttendanceLog,
  getGroup,
  getLessons,
  createLesson,
} from '../apiService';
import AttendanceStatusPicker from './AttendanceStatusPicker';
import './AttendanceLogPage.css';

const STATUS_META = {
  attended: { label: 'Был на занятии', short: '✓', className: 'status-attended' },
  absent: { label: 'Не был', short: '✗', className: 'status-absent' },
  watched_recording: { label: 'Посмотрел запись', short: '○', className: 'status-watched' },
  default: { label: 'Нет статуса', short: '–', className: 'status-empty' },
};

const formatDate = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
};

const getLessonLabel = (lesson, index) => {
  if (!lesson) {
    return `Занятие ${index + 1}`;
  }
  const raw = lesson.title || lesson.topic;
  return raw?.trim() || `Занятие ${index + 1}`;
};

const getStatusMeta = (status) => STATUS_META[status] || STATUS_META.default;
const formatPercent = (value) => `${Math.max(0, Math.min(100, Math.round(value || 0)))}%`;

const AttendanceLogPage = () => {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const preloadedLog = location.state?.logSnapshot;
  const [group, setGroup] = useState(null);
  const [log, setLog] = useState(null);
  const [lessonColumns, setLessonColumns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCell, setSelectedCell] = useState(null);
  const [updating, setUpdating] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [showLessonCreator, setShowLessonCreator] = useState(false);
  const [lessonDraft, setLessonDraft] = useState({
    title: '',
    date: '',
    time: '19:00',
    duration: 60,
  });
  const [creatingLesson, setCreatingLesson] = useState(false);
  const [lessonCreateError, setLessonCreateError] = useState(null);
  const tableWrapperRef = useRef(null);
  const hydratedFromPreloadRef = useRef(false);

  useEffect(() => {
    hydratedFromPreloadRef.current = false;
  }, [groupId]);

  useEffect(() => {
    if (preloadedLog && !hydratedFromPreloadRef.current) {
      const lessonsFromLog = preloadedLog?.lessons || [];
      setLessonColumns(lessonsFromLog);
      setLog(preloadedLog);
      const updatedAt = preloadedLog?.meta?.updated_at;
      setLastUpdated(updatedAt ? new Date(updatedAt) : new Date());
      hydratedFromPreloadRef.current = true;
    }
  }, [preloadedLog]);

  const loadData = useCallback(async () => {
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
  }, [groupId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const MIN_COLUMNS = 6;
  const actualLessons = lessonColumns.length ? lessonColumns : log?.lessons || [];
  const displayLessons = useMemo(() => {
    const normalized = (actualLessons || []).map((lesson) => {
      const numericId = Number(lesson?.id);
      const hasValidId = Number.isFinite(numericId);
      return {
        ...lesson,
        numericId: hasValidId ? numericId : null,
        isPlaceholder: lesson?.isPlaceholder || !hasValidId,
      };
    });
    if (normalized.length >= MIN_COLUMNS) {
      return normalized;
    }
    const placeholdersNeeded = MIN_COLUMNS - normalized.length;
    const placeholders = Array.from({ length: placeholdersNeeded }, (_, idx) => ({
      id: `placeholder-${idx}`,
      numericId: null,
      title: `Занятие ${normalized.length + idx + 1}`,
      start_time: null,
      isPlaceholder: true,
    }));
    return [...normalized, ...placeholders];
  }, [actualLessons]);

  const lessons = displayLessons;
  const realLessons = useMemo(() => lessons.filter((lesson) => !lesson.isPlaceholder), [lessons]);
  const realLessonsCount = realLessons.length;
  const students = log?.students || [];
  const records = log?.records || {};
  const actualLessonCount = actualLessons.length;
  const displayedLessonCount = actualLessonCount || lessons.length;
  const gridTemplateColumns = useMemo(() => {
    const base = '260px 140px';
    const lessonCount = lessons.length;
    if (!lessonCount) {
      return base;
    }
    return `${base} repeat(${lessonCount}, minmax(88px, 1fr))`;
  }, [lessons.length]);

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
        const numericLessonId = Number(lesson?.numericId ?? lesson?.id);
        const isPlaceholderLesson = lesson.isPlaceholder || !Number.isFinite(numericLessonId);

        if (isPlaceholderLesson) {
          stats.empty += 1;
          return {
            lessonId: null,
            rawLessonId: lesson.id,
            status: null,
            autoRecorded: false,
            isPlaceholder: true,
          };
        }

        const key = `${student.id}_${lesson.id}`;
        const record = records[key];
        const status = record?.status || null;

        if (status === 'attended') stats.attended += 1;
        else if (status === 'watched_recording') stats.watched += 1;
        else if (status === 'absent') stats.absent += 1;
        else stats.empty += 1;

        return {
          lessonId: numericLessonId,
          rawLessonId: lesson.id,
          status,
          autoRecorded: Boolean(record?.auto_recorded),
          isPlaceholder: false,
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

  const handleCellClick = (studentId, lessonId, isPlaceholder, e) => {
    e.stopPropagation();
    if (isPlaceholder) {
      return;
    }
    const numericLessonId = Number(lessonId);
    if (!Number.isFinite(numericLessonId)) {
      console.warn('Попытка изменить занятие с некорректным ID', lessonId);
      return;
    }
    setSelectedCell({ studentId, lessonId: numericLessonId });
  };

  const resetLessonDraft = useCallback(() => {
    const now = new Date();
    const defaultTitle = `Занятие ${realLessonsCount + 1}`;
    setLessonDraft({
      title: defaultTitle,
      date: now.toISOString().slice(0, 10),
      time: '19:00',
      duration: 60,
    });
    setLessonCreateError(null);
  }, [realLessonsCount]);

  useEffect(() => {
    if (showLessonCreator) {
      resetLessonDraft();
    }
  }, [showLessonCreator, resetLessonDraft]);

  const handleLessonDraftChange = (field, value) => {
    setLessonDraft((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateLesson = async (event) => {
    event.preventDefault();
    setLessonCreateError(null);

    if (!lessonDraft.date || !lessonDraft.time) {
      setLessonCreateError('Укажите дату и время урока');
      return;
    }

    const start = new Date(`${lessonDraft.date}T${lessonDraft.time}`);
    if (Number.isNaN(start.getTime())) {
      setLessonCreateError('Неверный формат даты или времени');
      return;
    }

    const durationMinutes = Number(lessonDraft.duration) || 60;
    const end = new Date(start.getTime() + durationMinutes * 60000);
    const safeTitle = (lessonDraft.title || '').trim() || `Занятие ${realLessonsCount + 1}`;
    const parsedGroupId = Number(groupId);
    const targetGroupId = Number.isFinite(parsedGroupId) ? parsedGroupId : group?.id;

    if (!targetGroupId) {
      setLessonCreateError('Не удалось определить группу для урока');
      return;
    }

    try {
      setCreatingLesson(true);
      await createLesson({
        title: safeTitle,
        group: targetGroupId,
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        topics: '',
        location: '',
        notes: '',
      });
      await loadData();
      setShowLessonCreator(false);
    } catch (lessonErr) {
      console.error('Не удалось создать занятие:', lessonErr);
      setLessonCreateError('Не удалось создать занятие. Попробуйте ещё раз.');
    } finally {
      setCreatingLesson(false);
    }
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
            className="action-button ghost"
            onClick={() => setShowLessonCreator((prev) => !prev)}
          >
            {showLessonCreator ? 'Скрыть форму' : 'Добавить занятие'}
          </button>
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

        {!realLessonsCount && (
          <div className="lesson-empty-state">
            <div>
              <h3>Занятия ещё не созданы</h3>
              <p>
                Добавьте хотя бы одно занятие, чтобы отмечать посещаемость. Можно создать урок прямо здесь
                или открыть расписание в новом окне.
              </p>
            </div>
            <div className="lesson-empty-actions">
              <a className="action-link" href="/schedule/teacher" target="_blank" rel="noreferrer">
                Открыть расписание
              </a>
            </div>
          </div>
        )}

        {showLessonCreator && (
          <form className="quick-lesson-form" onSubmit={handleCreateLesson}>
            <div className="form-grid">
              <label>
                <span>Название</span>
                <input
                  type="text"
                  value={lessonDraft.title}
                  onChange={(e) => handleLessonDraftChange('title', e.target.value)}
                  placeholder="Например: Разбор Домашки"
                  required
                />
              </label>
              <label>
                <span>Дата</span>
                <input
                  type="date"
                  value={lessonDraft.date}
                  onChange={(e) => handleLessonDraftChange('date', e.target.value)}
                  required
                />
              </label>
              <label>
                <span>Время начала</span>
                <input
                  type="time"
                  value={lessonDraft.time}
                  onChange={(e) => handleLessonDraftChange('time', e.target.value)}
                  required
                />
              </label>
              <label>
                <span>Длительность (мин)</span>
                <input
                  type="number"
                  min="15"
                  step="15"
                  value={lessonDraft.duration}
                  onChange={(e) => handleLessonDraftChange('duration', e.target.value)}
                  required
                />
              </label>
            </div>
            {lessonCreateError && <p className="form-error">{lessonCreateError}</p>}
            <div className="form-actions">
              <button type="submit" className="action-button" disabled={creatingLesson}>
                {creatingLesson ? 'Создание...' : 'Создать занятие'}
              </button>
              <button
                type="button"
                className="action-button ghost"
                onClick={() => setShowLessonCreator(false)}
                disabled={creatingLesson}
              >
                Отменить
              </button>
            </div>
          </form>
        )}

        <div className="table-wrapper" ref={tableWrapperRef}>
          <div className="attendance-grid">
            <div className="grid-header" style={{ gridTemplateColumns }}>
              <div className="grid-header-cell student-col">Ученик</div>
              <div className="grid-header-cell presence-col">Посещаемость</div>
              {lessons.map((lesson, idx) => (
                <div
                  key={lesson.id}
                  className="grid-header-cell lesson-col"
                  title={lesson.title || lesson.topic || undefined}
                >
                  <div className="lesson-index">{getLessonLabel(lesson, idx)}</div>
                  <div className="lesson-date">{formatDate(lesson.start_time)}</div>
                </div>
              ))}
            </div>

            <div className="grid-body">
              {rows.map((row) => (
                <div
                  key={row.student.id}
                  className="grid-row"
                  style={{ gridTemplateColumns }}
                >
                  <div className="grid-cell student-cell">
                    <span className="avatar-circle">
                      {row.student.name?.[0] || '👤'}
                    </span>
                    <div className="student-details">
                      <span className="student-name">{row.student.name}</span>
                      <span className="student-email">{row.student.email}</span>
                    </div>
                  </div>
                  <div className="grid-cell presence-cell">
                    <span className="presence-chip">
                      {formatPercent(row.attendancePercent)}
                    </span>
                    <span className="presence-meta">
                      {row.stats.attended} из {displayedLessonCount}
                    </span>
                  </div>
                  {row.lessonStatuses.map(({ lessonId, rawLessonId, status, autoRecorded, isPlaceholder }, lessonIndex) => {
                    const cellMeta = getStatusMeta(status);
                    const isSelected =
                      selectedCell?.studentId === row.student.id &&
                      selectedCell?.lessonId === lessonId;
                    const lessonLabel = getLessonLabel(lessons[lessonIndex], lessonIndex);

                    return (
                      <div
                        key={`${row.student.id}_${rawLessonId ?? lessonId ?? lessonIndex}`}
                        className={`grid-cell lesson-cell ${isPlaceholder ? 'placeholder' : ''}`}
                      >
                        <button
                          type="button"
                          className={`attendance-cell-button ${cellMeta.className} ${
                            isSelected ? 'selected' : ''
                          } ${isPlaceholder ? 'placeholder' : ''}`}
                          onClick={(e) => handleCellClick(row.student.id, lessonId, isPlaceholder, e)}
                          aria-label={`Изменить статус: ${row.student.name} — ${lessonLabel}`}
                          disabled={isPlaceholder}
                        >
                          <span className="status-pill">{cellMeta.short}</span>
                          <span className="status-label">{cellMeta.label}</span>
                        </button>
                        {autoRecorded && <span className="auto-badge">auto</span>}

                        {isSelected && (
                          <AttendanceStatusPicker
                            currentStatus={status}
                            onStatusSelect={handleStatusChange}
                            onClose={() => setSelectedCell(null)}
                            isLoading={updating}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
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
