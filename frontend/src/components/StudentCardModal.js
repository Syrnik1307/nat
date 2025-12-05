/**
 * StudentCardModal.js
 * Модальная карточка ученика с информацией о прогрессе и замечаниями
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../apiService';
import './StudentCardModal.css';

const StudentCardModal = ({ studentId, groupId, isOpen, onClose, isIndividual = false }) => {
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen && studentId) {
      loadStudentCard();
    }
  }, [isOpen, studentId, groupId]);

  const loadStudentCard = async () => {
    try {
      setLoading(true);
      setError(null);
      const endpoint = isIndividual 
        ? `/students/${studentId}/individual-card/`
        : `/students/${studentId}/card/?group_id=${groupId || ''}`;
      
      const response = await apiClient.get(endpoint);
      setCard(response.data);
      setNotes(response.data.teacher_notes || '');
    } catch (err) {
      console.error('Ошибка загрузки карточки:', err);
      setError('Не удалось загрузить информацию об ученике');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!card) return;

    try {
      setSaving(true);
      if (isIndividual) {
        await apiClient.patch(`/individual-students/${studentId}/update_notes/`, {
          teacher_notes: notes
        });
      } else {
        // TODO: Реализовать сохранение замечаний для группового ученика
        console.log('Сохранение замечаний для группового ученика');
      }
      
      setEditing(false);
      loadStudentCard();
    } catch (err) {
      console.error('Ошибка сохранения замечаний:', err);
      setError('Не удалось сохранить замечания');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content student-card-modal" onClick={(e) => e.stopPropagation()}>
        {/* Заголовок */}
        <div className="modal-header">
          <div className="header-info">
            {loading ? (
              <h2 className="modal-title">Загрузка...</h2>
            ) : card ? (
              <div className="student-header">
                <div className="student-avatar-large">👤</div>
                <div className="student-header-info">
                  <h2 className="modal-title">{card.name}</h2>
                  <p className="student-email">{card.email}</p>
                </div>
              </div>
            ) : null}
          </div>
          <button
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Закрыть"
          >
            ✕
          </button>
        </div>

        {/* Содержимое */}
        <div className="modal-body">
          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}

          {loading ? (
            <div className="loading-state">Загрузка информации об ученике...</div>
          ) : card ? (
            <>
              {/* Статистика */}
              <div className="stats-grid">
                <div className="stat-card">
                  <span className="stat-icon">+</span>
                  <span className="stat-label">Посещаемость</span>
                  <span className="stat-value">{card.stats?.attendance_percent || 0}%</span>
                  <span className="stat-detail">
                    {card.stats?.attended || 0}/{card.stats?.total_lessons || 0} занятий
                  </span>
                </div>

                <div className="stat-card">
                  <span className="stat-icon">📝</span>
                  <span className="stat-label">Домашние задания</span>
                  <span className="stat-value">—</span>
                  <span className="stat-detail">Интеграция с модулем ДЗ</span>
                </div>

                <div className="stat-card">
                  <span className="stat-icon">🎯</span>
                  <span className="stat-label">Контрольные точки</span>
                  <span className="stat-value">—</span>
                  <span className="stat-detail">Интеграция с модулем аналитики</span>
                </div>

                {!isIndividual && (
                  <div className="stat-card">
                    <span className="stat-icon">⭐</span>
                    <span className="stat-label">Место в группе</span>
                    <span className="stat-value">—</span>
                    <span className="stat-detail">Из рейтинга группы</span>
                  </div>
                )}
              </div>

              {/* Ошибки и пробелы */}
              {card.errors && (Object.keys(card.errors).length > 0) && (
                <div className="errors-section">
                  <h3 className="section-title">⚠️ Пробелы и недовыполнения</h3>
                  
                  {card.errors.incomplete_homework && card.errors.incomplete_homework.length > 0 && (
                    <div className="error-item">
                      <span className="error-type">Недовыполненные ДЗ:</span>
                      <ul className="error-list">
                        {card.errors.incomplete_homework.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {card.errors.failed_control_points && card.errors.failed_control_points.length > 0 && (
                    <div className="error-item">
                      <span className="error-type">Непройденные контрольные:</span>
                      <ul className="error-list">
                        {card.errors.failed_control_points.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Замечания учителя */}
              <div className="notes-section">
                <div className="notes-header">
                  <h3 className="section-title">📝 Замечания учителя</h3>
                  <button
                    className="edit-btn"
                    onClick={() => setEditing(!editing)}
                  >
                    {editing ? '✓' : '✎'}
                  </button>
                </div>

                {editing ? (
                  <div className="notes-editor">
                    <textarea
                      className="notes-textarea"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Добавьте замечания об ученике..."
                      rows={4}
                    />
                    <div className="editor-buttons">
                      <button
                        className="btn btn-primary"
                        onClick={handleSaveNotes}
                        disabled={saving}
                      >
                        {saving ? '💾 Сохранение...' : '💾 Сохранить'}
                      </button>
                      <button
                        className="btn btn-secondary"
                        onClick={() => {
                          setEditing(false);
                          setNotes(card.teacher_notes || '');
                        }}
                      >
                        ✕ Отмена
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="notes-display">
                    {notes ? (
                      <p className="notes-text">{notes}</p>
                    ) : (
                      <p className="notes-empty">Нет замечаний</p>
                    )}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="empty-state">Информация не найдена</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StudentCardModal;
