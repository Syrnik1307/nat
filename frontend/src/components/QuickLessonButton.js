import React, { useState, useEffect } from 'react';
import { startQuickLesson, apiClient } from '../apiService';

const PRIMARY_GRADIENT = 'linear-gradient(135deg, #0b2b65 0%, #0a1f4d 100%)';

const buttonBase = {
  fontWeight: '600',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  padding: '0.65rem 1.35rem',
  fontSize: '0.9rem',
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '0.5rem',
  boxShadow: '0 6px 16px rgba(11, 43, 101, 0.35)',
  transform: 'none',
  outline: 'none',
  transition: 'none',
};

const modalStyles = {
  container: {
    position: 'fixed',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    backgroundColor: 'white',
    border: '1px solid #e5e7eb',
    borderRadius: '12px',
    padding: '1.5rem',
    boxShadow: '0 12px 40px rgba(0, 0, 0, 0.15)',
    zIndex: 1000,
    width: '420px',
    maxWidth: '92vw',
    maxHeight: '85vh',
    overflowY: 'auto',
    boxSizing: 'border-box',
    animation: 'none',
  },
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 999,
    backgroundColor: 'rgba(0, 0, 0, 0.32)',
    pointerEvents: 'auto',
  },
};

const QuickLessonButton = ({ onSuccess, className = '' }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [recordLesson, setRecordLesson] = useState(false);
  const [privacyType, setPrivacyType] = useState('all'); // 'all', 'groups', 'students'
  const [selectedGroups, setSelectedGroups] = useState([]);
  const [selectedStudents, setSelectedStudents] = useState([]);
  const [groups, setGroups] = useState([]);
  const [students, setStudents] = useState([]);

  // Блокируем скролл когда модалка открыта
  useEffect(() => {
    const preventScroll = (e) => e.preventDefault();
    if (showModal) {
      const originalOverflow = document.body.style.overflow;
      const originalPaddingRight = document.body.style.paddingRight;
      const scrollBarWidth = window.innerWidth - document.documentElement.clientWidth;
      document.body.style.overflow = 'hidden';
      if (scrollBarWidth > 0) {
        document.body.style.paddingRight = `${scrollBarWidth}px`;
      }
      window.addEventListener('wheel', preventScroll, { passive: false });
      return () => {
        document.body.style.overflow = originalOverflow;
        document.body.style.paddingRight = originalPaddingRight;
        window.removeEventListener('wheel', preventScroll);
      };
    }
  }, [showModal]);

  // Загружаем группы и учеников при открытии модалки
  useEffect(() => {
    if (showModal && recordLesson) {
      loadGroupsAndStudents();
    }
  }, [showModal, recordLesson]);

  const loadGroupsAndStudents = async () => {
    try {
      // Загружаем группы
      const groupsResponse = await apiClient.get('/schedule/groups/');
      const groupsData = groupsResponse.data.results || groupsResponse.data;
      setGroups(Array.isArray(groupsData) ? groupsData : []);

      // Собираем всех студентов из групп
      const allStudents = [];
      groupsData.forEach(group => {
        if (group.students && Array.isArray(group.students)) {
          group.students.forEach(student => {
            if (!allStudents.find(s => s.id === student.id)) {
              allStudents.push(student);
            }
          });
        }
      });
      setStudents(allStudents);
    } catch (err) {
      console.error('Error loading groups/students:', err);
    }
  };

  const handleStartQuickLesson = async () => {
    setLoading(true);
    setError(null);

    // Валидация
    if (recordLesson && privacyType === 'groups' && selectedGroups.length === 0) {
      setError('Выберите хотя бы одну группу');
      setLoading(false);
      return;
    }

    if (recordLesson && privacyType === 'students' && selectedStudents.length === 0) {
      setError('Выберите хотя бы одного ученика');
      setLoading(false);
      return;
    }

    try {
      const payload = {
        record_lesson: recordLesson,
      };

      // Добавляем настройки приватности если запись включена
      if (recordLesson) {
        payload.privacy_type = privacyType;
        if (privacyType === 'groups') {
          payload.allowed_groups = selectedGroups;
        } else if (privacyType === 'students') {
          payload.allowed_students = selectedStudents;
        }
      }

      const response = await startQuickLesson(payload);
      
      if (response.data?.zoom_start_url) {
        window.open(response.data.zoom_start_url, '_blank', 'noopener,noreferrer');
      }
      
      if (onSuccess) {
        onSuccess(response.data);
      }
      
      setShowModal(false);
      
      // Сбрасываем состояние
      setRecordLesson(false);
      setPrivacyType('all');
      setSelectedGroups([]);
      setSelectedStudents([]);
    } catch (err) {
      if (err.response?.status === 503) {
        setError('Все Zoom аккаунты заняты. Попробуйте позже.');
      } else if (err.response?.status === 400 || err.response?.status === 403) {
        setError(err.response.data?.detail || 'Ошибка создания встречи');
      } else {
        setError(err.response?.data?.detail || err.message || 'Не удалось начать занятие.');
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleGroupSelection = (groupId) => {
    setSelectedGroups(prev => 
      prev.includes(groupId) 
        ? prev.filter(id => id !== groupId)
        : [...prev, groupId]
    );
  };

  const toggleStudentSelection = (studentId) => {
    setSelectedStudents(prev => 
      prev.includes(studentId) 
        ? prev.filter(id => id !== studentId)
        : [...prev, studentId]
    );
  };

  return (
    <>
      <button
        type="button"
        disabled={loading}
        onClick={() => setShowModal(true)}
        className={`header-message-button ${className}`}
        aria-label="Быстрый урок"
      >
        <span className="header-message-icon" aria-hidden="true">
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M15 10l-4 4-2-2"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle
              cx="12"
              cy="12"
              r="9"
              stroke="currentColor"
              strokeWidth="2"
              fill="none"
            />
            <path
              d="M12 6v6l3 2"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span className="header-message-label">
          {loading ? 'Запуск...' : 'Быстрый урок'}
        </span>
      </button>

      {showModal && (
        <>
          <div
            style={modalStyles.overlay}
            onClick={() => setShowModal(false)}
            onWheel={(e) => e.preventDefault()}
          />
          <div style={modalStyles.container} onWheel={(e) => e.preventDefault()}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#1f2937' }}>
                Быстрый урок
              </div>

              {/* Опция записи */}
              <label style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer',
                padding: '0.75rem', borderRadius: '8px',
                backgroundColor: recordLesson ? '#f0fdf4' : '#f9fafb',
                border: recordLesson ? '1px solid #d1fae5' : '1px solid #e5e7eb',
              }}>
                <input
                  type="checkbox"
                  checked={recordLesson}
                  onChange={(e) => setRecordLesson(e.target.checked)}
                  style={{ width: '1.1rem', height: '1.1rem', cursor: 'pointer', accentColor: '#0b2b65' }}
                />
                <span style={{ fontSize: '0.9rem', color: '#1f2937', fontWeight: 500 }}>
                  Записать урок
                </span>
              </label>

              {recordLesson && (
                <>
                  <div style={{
                    fontSize: '0.8rem', color: '#6b7280', padding: '0.75rem',
                    backgroundColor: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb',
                  }}>
                    Запись будет доступна в разделе «Записи» после окончания урока
                  </div>

                  {/* Настройки приватности */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#1f2937' }}>
                      Кому будет доступна запись?
                    </div>
                    
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        onClick={() => setPrivacyType('all')}
                        style={{
                          flex: '1 1 auto',
                          padding: '0.5rem 0.75rem',
                          fontSize: '0.85rem',
                          fontWeight: 500,
                          borderRadius: '6px',
                          border: privacyType === 'all' ? '2px solid #0b2b65' : '1px solid #e5e7eb',
                          backgroundColor: privacyType === 'all' ? '#f0f9ff' : 'white',
                          color: privacyType === 'all' ? '#0b2b65' : '#4b5563',
                          cursor: 'pointer',
                          transition: 'none',
                        }}
                      >
                        Все ученики
                      </button>
                      <button
                        type="button"
                        onClick={() => setPrivacyType('groups')}
                        style={{
                          flex: '1 1 auto',
                          padding: '0.5rem 0.75rem',
                          fontSize: '0.85rem',
                          fontWeight: 500,
                          borderRadius: '6px',
                          border: privacyType === 'groups' ? '2px solid #0b2b65' : '1px solid #e5e7eb',
                          backgroundColor: privacyType === 'groups' ? '#f0f9ff' : 'white',
                          color: privacyType === 'groups' ? '#0b2b65' : '#4b5563',
                          cursor: 'pointer',
                          transition: 'none',
                        }}
                      >
                        Выбрать группы
                      </button>
                      <button
                        type="button"
                        onClick={() => setPrivacyType('students')}
                        style={{
                          flex: '1 1 auto',
                          padding: '0.5rem 0.75rem',
                          fontSize: '0.85rem',
                          fontWeight: 500,
                          borderRadius: '6px',
                          border: privacyType === 'students' ? '2px solid #0b2b65' : '1px solid #e5e7eb',
                          backgroundColor: privacyType === 'students' ? '#f0f9ff' : 'white',
                          color: privacyType === 'students' ? '#0b2b65' : '#4b5563',
                          cursor: 'pointer',
                          transition: 'none',
                        }}
                      >
                        Выбрать учеников
                      </button>
                    </div>

                    {/* Выбор групп */}
                    {privacyType === 'groups' && (
                      <div style={{
                        maxHeight: '200px',
                        overflowY: 'auto',
                        padding: '0.75rem',
                        backgroundColor: '#f9fafb',
                        borderRadius: '8px',
                        border: '1px solid #e5e7eb',
                      }}>
                        {groups.length === 0 ? (
                          <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                            Нет доступных групп
                          </div>
                        ) : (
                          groups.map(group => (
                            <label key={group.id} style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.5rem',
                              padding: '0.5rem',
                              cursor: 'pointer',
                              borderRadius: '4px',
                              marginBottom: '0.25rem',
                              backgroundColor: selectedGroups.includes(group.id) ? '#f0f9ff' : 'transparent',
                            }}>
                              <input
                                type="checkbox"
                                checked={selectedGroups.includes(group.id)}
                                onChange={() => toggleGroupSelection(group.id)}
                                style={{ width: '1rem', height: '1rem', cursor: 'pointer', accentColor: '#0b2b65' }}
                              />
                              <span style={{ fontSize: '0.85rem', color: '#1f2937' }}>
                                {group.name} ({group.student_count || 0} учеников)
                              </span>
                            </label>
                          ))
                        )}
                      </div>
                    )}

                    {/* Выбор учеников */}
                    {privacyType === 'students' && (
                      <div style={{
                        maxHeight: '200px',
                        overflowY: 'auto',
                        padding: '0.75rem',
                        backgroundColor: '#f9fafb',
                        borderRadius: '8px',
                        border: '1px solid #e5e7eb',
                      }}>
                        {students.length === 0 ? (
                          <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                            Нет доступных учеников
                          </div>
                        ) : (
                          students.map(student => (
                            <label key={student.id} style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.5rem',
                              padding: '0.5rem',
                              cursor: 'pointer',
                              borderRadius: '4px',
                              marginBottom: '0.25rem',
                              backgroundColor: selectedStudents.includes(student.id) ? '#f0f9ff' : 'transparent',
                            }}>
                              <input
                                type="checkbox"
                                checked={selectedStudents.includes(student.id)}
                                onChange={() => toggleStudentSelection(student.id)}
                                style={{ width: '1rem', height: '1rem', cursor: 'pointer', accentColor: '#0b2b65' }}
                              />
                              <span style={{ fontSize: '0.85rem', color: '#1f2937' }}>
                                {student.first_name} {student.last_name}
                              </span>
                            </label>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* Кнопки действий */}
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  onClick={handleStartQuickLesson}
                  disabled={loading}
                  style={{
                    ...buttonBase,
                    flex: 1,
                    padding: '0.65rem 1rem',
                    background: PRIMARY_GRADIENT,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    boxShadow: '0 3px 10px rgba(11, 43, 101, 0.28)',
                  }}
                >
                  {loading ? 'Запуск...' : 'Начать'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  style={{
                    flex: 1,
                    padding: '0.65rem 1rem',
                    backgroundColor: '#f3f4f6',
                    color: '#4b5563',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '0.9rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    boxShadow: 'none',
                    transition: 'none',
                  }}
                >
                  Отмена
                </button>
              </div>

              {error && (
                <div style={{
                  marginTop: '0.25rem',
                  padding: '0.75rem',
                  backgroundColor: '#fef2f2',
                  color: '#b91c1c',
                  borderRadius: '8px',
                  fontSize: '0.875rem',
                  border: '1px solid #fecaca',
                }}>
                  {error}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default QuickLessonButton;
