import React, { useState, useEffect } from 'react';
import { startQuickLesson, apiClient } from '../apiService';

// Снежинка компонент
const Snowflake = ({ delay, duration, left }) => (
  <div
    style={{
      position: 'absolute',
      top: '-10px',
      left: `${left}%`,
      width: '8px',
      height: '8px',
      background: 'white',
      borderRadius: '50%',
      opacity: 0.8,
      animation: `snowfall ${duration}s linear infinite`,
      animationDelay: `${delay}s`,
      boxShadow: '0 0 10px rgba(255, 255, 255, 0.8)',
    }}
  />
);

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
    background: 'linear-gradient(180deg, #0f172a 0%, #1e3a8a 50%, #2563eb 100%)',
    border: '3px solid rgba(255, 255, 255, 0.4)',
    borderRadius: '20px',
    padding: '1.5rem',
    boxShadow: '0 25px 70px rgba(0, 0, 0, 0.5), inset 0 2px 0 rgba(255, 255, 255, 0.3), 0 0 100px rgba(96, 165, 250, 0.3)',
    zIndex: 1000,
    width: '420px',
    maxWidth: '92vw',
    maxHeight: '85vh',
    overflowY: 'auto',
    boxSizing: 'border-box',
    animation: 'glow 3s ease-in-out infinite alternate',
  },
  innerContainer: {
    position: 'relative',
    minHeight: '100%',
    overflow: 'hidden',
  },
  backdrop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.1) 0%, transparent 60%)',
    zIndex: 0,
    pointerEvents: 'none',
  },
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 999,
    backgroundColor: 'rgba(0, 20, 60, 0.6)',
    backdropFilter: 'blur(4px)',
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
      
      // Открываем ссылку СРАЗУ после получения ответа (как было раньше)
      if (response.data?.zoom_start_url) {
        window.open(response.data.zoom_start_url, '_blank');
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
        // Показываем сообщение от сервера (там понятный текст про подключение Zoom/Meet)
        const serverMessage = err.response.data?.detail;
        setError(serverMessage || 'Подключите Zoom или Google Meet в настройках интеграций.');
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

  console.log('QuickLessonButton rendered, showModal:', showModal);

  return (
    <>
      <button
        type="button"
        disabled={loading}
        onClick={() => {
          console.log('Quick Lesson button clicked!');
          setShowModal(true);
        }}
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
            <circle
              cx="12"
              cy="12"
              r="9"
              stroke="currentColor"
              strokeWidth="2"
              fill="none"
            />
            <path
              d="M9 12l2 2 4-4"
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
          <style>
            {`
              @keyframes snowfall {
                0% { 
                  transform: translateY(-10px) translateX(0) rotate(0deg);
                  opacity: 0;
                }
                10% {
                  opacity: 1;
                }
                100% { 
                  transform: translateY(600px) translateX(100px) rotate(360deg);
                  opacity: 0.8;
                }
              }
              
              @keyframes glow {
                0% {
                  box-shadow: 0 25px 70px rgba(0, 0, 0, 0.5), 
                             inset 0 2px 0 rgba(255, 255, 255, 0.3), 
                             0 0 80px rgba(96, 165, 250, 0.2);
                }
                100% {
                  box-shadow: 0 25px 70px rgba(0, 0, 0, 0.5), 
                             inset 0 2px 0 rgba(255, 255, 255, 0.3), 
                             0 0 120px rgba(96, 165, 250, 0.4);
                }
              }
            `}
          </style>
          <div
            style={modalStyles.overlay}
            onClick={() => setShowModal(false)}
            onWheel={(e) => e.preventDefault()}
          />
          <div style={modalStyles.container} onWheel={(e) => e.preventDefault()}>
            <div style={modalStyles.innerContainer}>
              {/* Radial glow backdrop */}
              <div style={modalStyles.backdrop}></div>
              
              {/* Интенсивный снегопад */}
              {[...Array(50)].map((_, i) => (
                <Snowflake
                  key={i}
                  delay={Math.random() * 5}
                  duration={5 + Math.random() * 5}
                  left={Math.random() * 100}
                />
              ))}
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', position: 'relative', zIndex: 1 }}>
              <div style={{ 
                fontSize: '1.3rem', 
                fontWeight: 700, 
                color: 'white',
                textShadow: '0 2px 10px rgba(0, 0, 0, 0.3)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                <span style={{ fontSize: '1.5rem' }}>❄️</span>
                Быстрый урок
                <span style={{ fontSize: '1.5rem' }}>🎄</span>
              </div>

              {/* Опция записи */}
              <label style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer',
                padding: '0.75rem', borderRadius: '8px',
                backgroundColor: recordLesson ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.15)',
                border: recordLesson ? '2px solid rgba(255, 255, 255, 0.5)' : '2px solid rgba(255, 255, 255, 0.2)',
                color: 'white',
                transition: 'all 0.3s ease',
              }}>
                <input
                  type="checkbox"
                  checked={recordLesson}
                  onChange={(e) => setRecordLesson(e.target.checked)}
                  style={{ width: '1.1rem', height: '1.1rem', cursor: 'pointer', accentColor: '#60a5fa' }}
                />
                <span style={{ fontSize: '0.95rem', fontWeight: 500 }}>
                  🎥 Записать урок
                </span>
              </label>

              {recordLesson && (
                <>
                  <div style={{
                    fontSize: '0.85rem', 
                    color: 'rgba(255, 255, 255, 0.9)', 
                    padding: '0.75rem',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                  }}>
                    ⏺️ Запись будет доступна в разделе «Записи» после окончания урока
                  </div>

                  {/* Настройки приватности */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'white', textShadow: '0 1px 3px rgba(0,0,0,0.3)' }}>
                      🎁 Кому будет доступна запись?
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
                          borderRadius: '8px',
                          border: privacyType === 'all' ? '2px solid white' : '2px solid rgba(255, 255, 255, 0.3)',
                          backgroundColor: privacyType === 'all' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.15)',
                          color: 'white',
                          cursor: 'pointer',
                          transition: 'all 0.3s ease',
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
                          borderRadius: '8px',
                          border: privacyType === 'groups' ? '2px solid white' : '2px solid rgba(255, 255, 255, 0.3)',
                          backgroundColor: privacyType === 'groups' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.15)',
                          color: 'white',
                          cursor: 'pointer',
                          transition: 'all 0.3s ease',
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
                          borderRadius: '8px',
                          border: privacyType === 'students' ? '2px solid white' : '2px solid rgba(255, 255, 255, 0.3)',
                          backgroundColor: privacyType === 'students' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.15)',
                          color: 'white',
                          cursor: 'pointer',
                          transition: 'all 0.3s ease',
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
                        backgroundColor: 'rgba(255, 255, 255, 0.15)',
                        borderRadius: '8px',
                        border: '1px solid rgba(255, 255, 255, 0.3)',
                      }}>
                        {groups.length === 0 ? (
                          <div style={{ fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.7)' }}>
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
                              borderRadius: '6px',
                              marginBottom: '0.25rem',
                              backgroundColor: selectedGroups.includes(group.id) ? 'rgba(255, 255, 255, 0.25)' : 'transparent',
                              transition: 'all 0.2s ease',
                            }}>
                              <input
                                type="checkbox"
                                checked={selectedGroups.includes(group.id)}
                                onChange={() => toggleGroupSelection(group.id)}
                                style={{ width: '1rem', height: '1rem', cursor: 'pointer', accentColor: '#60a5fa' }}
                              />
                              <span style={{ fontSize: '0.85rem', color: 'white' }}>
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
                        backgroundColor: 'rgba(255, 255, 255, 0.15)',
                        borderRadius: '8px',
                        border: '1px solid rgba(255, 255, 255, 0.3)',
                      }}>
                        {students.length === 0 ? (
                          <div style={{ fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.7)' }}>
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
                              borderRadius: '6px',
                              marginBottom: '0.25rem',
                              backgroundColor: selectedStudents.includes(student.id) ? 'rgba(255, 255, 255, 0.25)' : 'transparent',
                              transition: 'all 0.2s ease',
                            }}>
                              <input
                                type="checkbox"
                                checked={selectedStudents.includes(student.id)}
                                onChange={() => toggleStudentSelection(student.id)}
                                style={{ width: '1rem', height: '1rem', cursor: 'pointer', accentColor: '#60a5fa' }}
                              />
                              <span style={{ fontSize: '0.85rem', color: 'white' }}>
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
                    flex: 1,
                    padding: '0.75rem 1.25rem',
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    color: 'white',
                    border: '2px solid rgba(255, 255, 255, 0.4)',
                    borderRadius: '10px',
                    fontSize: '1rem',
                    fontWeight: 700,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)',
                    transition: 'all 0.3s ease',
                    opacity: loading ? 0.7 : 1,
                  }}
                >
                  {loading ? '⏳ Запуск...' : '🚀 Начать'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  style={{
                    flex: 1,
                    padding: '0.75rem 1.25rem',
                    backgroundColor: 'rgba(255, 255, 255, 0.2)',
                    color: 'white',
                    border: '2px solid rgba(255, 255, 255, 0.3)',
                    borderRadius: '10px',
                    fontSize: '1rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                  }}
                >
                  ❌ Отмена
                </button>
              </div>

              {error && (
                <div style={{
                  marginTop: '0.25rem',
                  padding: '0.75rem',
                  backgroundColor: 'rgba(239, 68, 68, 0.2)',
                  color: 'white',
                  borderRadius: '8px',
                  fontSize: '0.875rem',
                  border: '2px solid rgba(239, 68, 68, 0.5)',
                  fontWeight: 500,
                }}>
                  ⚠️ {error}
                </div>
              )}
            </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default QuickLessonButton;
