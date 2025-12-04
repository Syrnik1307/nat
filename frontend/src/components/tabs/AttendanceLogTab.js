/**
 * AttendanceLogTab.js
 * Таб журнала посещений в модале группы
 * Матрица: Ученик x Занятие с возможностью быстрого редактирования
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../../apiService';
import AttendanceStatusPicker from '../AttendanceStatusPicker';
import './AttendanceLogTab.css';

const AttendanceLogTab = ({ groupId, onStudentClick }) => {
  const [log, setLog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCell, setSelectedCell] = useState(null);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    loadAttendanceLog();
  }, [groupId]);

  const loadAttendanceLog = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(`/groups/${groupId}/attendance-log/`);
      setLog(response.data);
    } catch (err) {
      console.error('Ошибка загрузки журнала посещений:', err);
      setError('Не удалось загрузить журнал посещений');
    } finally {
      setLoading(false);
    }
  };

  const handleCellClick = (studentId, lessonId, e) => {
    e.stopPropagation();
    setSelectedCell({ studentId, lessonId });
  };

  const handleStatusChange = async (status) => {
    if (!selectedCell) return;

    try {
      setUpdating(true);
      await apiClient.post(`/groups/${groupId}/attendance-log/update/`, {
        lesson_id: selectedCell.lessonId,
        student_id: selectedCell.studentId,
        status: status
      });

      // Обновить логин
      await loadAttendanceLog();
      setSelectedCell(null);
    } catch (err) {
      console.error('Ошибка обновления посещения:', err);
      setError('Не удалось сохранить изменения');
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return <div className="tab-loading">⏳ Загрузка журнала...</div>;
  }

  if (error) {
    return <div className="tab-error">⚠️ {error}</div>;
  }

  if (!log || !log.lessons || !log.students) {
    return <div className="tab-empty">📋 Нет данных для отображения</div>;
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'attended':
        return '✓';
      case 'absent':
        return '✗';
      case 'watched_recording':
        return '👁';
      default:
        return '–';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'attended':
        return 'Был';
      case 'absent':
        return 'Не был';
      case 'watched_recording':
        return 'Запись';
      default:
        return '—';
    }
  };

  return (
    <div className="attendance-log-tab">
      <div className="table-wrapper">
        <table className="attendance-table">
          <thead>
            <tr>
              <th className="student-col">Ученик</th>
              {log.lessons.map((lesson) => (
                <th key={lesson.id} className="lesson-col" title={lesson.title}>
                  <div className="lesson-header">
                    <div className="lesson-title">{lesson.title}</div>
                    <div className="lesson-date">
                      {new Date(lesson.start_time).toLocaleDateString('ru-RU')}
                    </div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {log.students.map((student) => (
              <tr key={student.id} className="student-row">
                <td className="student-col">
                  <button
                    className="student-name-btn"
                    onClick={() => onStudentClick && onStudentClick(student.id, groupId)}
                    title="Открыть карточку ученика"
                  >
                    <span className="student-avatar">👤</span>
                    <span className="student-text">
                      <span className="name">{student.name}</span>
                      <span className="email">{student.email}</span>
                    </span>
                  </button>
                </td>
                {log.lessons.map((lesson) => {
                  const key = `${student.id}_${lesson.id}`;
                  const record = log.records[key];
                  const status = record ? record.status : null;
                  const isSelected = selectedCell?.studentId === student.id && 
                                    selectedCell?.lessonId === lesson.id;

                  return (
                    <td
                      key={key}
                      className={`attendance-cell ${status ? `status-${status}` : 'status-empty'} ${isSelected ? 'selected' : ''}`}
                      onClick={(e) => handleCellClick(student.id, lesson.id, e)}
                    >
                      <div className="cell-content">
                        <span className="status-icon">{getStatusIcon(status)}</span>
                        <span className="status-label">{getStatusLabel(status)}</span>
                      </div>

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

      {/* Легенда */}
      <div className="attendance-legend">
        <div className="legend-item">
          <span className="legend-icon status-icon-legend attended">✓</span>
          <span>Был на занятии</span>
        </div>
        <div className="legend-item">
          <span className="legend-icon status-icon-legend absent">✗</span>
          <span>Не был</span>
        </div>
        <div className="legend-item">
          <span className="legend-icon status-icon-legend watched">👁</span>
          <span>Посмотрел запись</span>
        </div>
        <div className="legend-item">
          <span className="legend-icon status-icon-legend empty">–</span>
          <span>Нет статуса</span>
        </div>
      </div>
    </div>
  );
};

export default AttendanceLogTab;
