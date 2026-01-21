import React, { useEffect, useState } from 'react';
import { startLessonNew, updateLesson, getCurrentUser } from '../../../apiService';

const PRIMARY_GRADIENT = 'linear-gradient(135deg, #0b2b65 0%, #0a1f4d 100%)';
const MEET_GRADIENT = 'linear-gradient(135deg, #00ac47 0%, #00832d 100%)';

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

// Стили для выбора платформы
const platformOptionStyle = (selected, disabled) => ({
  display: 'flex',
  alignItems: 'center',
  gap: '0.75rem',
  padding: '0.875rem',
  borderRadius: '10px',
  border: selected ? '2px solid #0b2b65' : '1px solid #e5e7eb',
  backgroundColor: disabled ? '#f9fafb' : (selected ? '#f0f4ff' : 'white'),
  cursor: disabled ? 'not-allowed' : 'pointer',
  opacity: disabled ? 0.6 : 1,
  transition: 'all 0.15s ease',
});

const platformIconStyle = (type) => ({
  width: '36px',
  height: '36px',
  borderRadius: '8px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: type === 'google_meet' ? MEET_GRADIENT : PRIMARY_GRADIENT,
  color: 'white',
  flexShrink: 0,
});

const StartLessonButton = ({ lessonId, lesson, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [recordLesson, setRecordLesson] = useState(lesson?.record_lesson || false);
  
  // Выбор платформы
  const [selectedPlatform, setSelectedPlatform] = useState('zoom_pool');
  const [availablePlatforms, setAvailablePlatforms] = useState([]);
  const [platformsLoading, setPlatformsLoading] = useState(false);

  // Загружаем доступные платформы при открытии модалки
  useEffect(() => {
    if (showModal && availablePlatforms.length === 0) {
      setPlatformsLoading(true);
      getCurrentUser()
        .then((res) => {
          const platforms = res.data?.available_platforms || [];
          setAvailablePlatforms(platforms);
          // Если google_meet подключён — оставляем zoom_pool по умолчанию
          // Можно изменить логику, если нужно запоминать последний выбор
        })
        .catch((err) => {
          console.error('Failed to load platforms:', err);
          // Fallback: показываем только zoom_pool
          setAvailablePlatforms([{
            id: 'zoom_pool',
            name: 'Zoom (пул платформы)',
            connected: true,
          }]);
        })
        .finally(() => setPlatformsLoading(false));
    }
  }, [showModal, availablePlatforms.length]);

  // Блокируем скролл и компенсируем ширину скроллбара
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

  const handleStartLesson = async () => {
    setLoading(true);
    setError(null);
    try {
      const recordFlagChanged = lesson && recordLesson !== lesson.record_lesson;
      // Update record_lesson flag before starting
      if (recordFlagChanged) {
        await updateLesson(lessonId, {
          record_lesson: recordLesson
        });
      }

      const response = await startLessonNew(lessonId, {
        record_lesson: recordLesson,
        force_new_meeting: recordFlagChanged && recordLesson && Boolean(lesson?.zoom_meeting_id),
        provider: selectedPlatform, // Новый параметр: zoom_pool | google_meet
      });
      
      // Открываем ссылку в зависимости от платформы
      // ВАЖНО: Используем provider из ответа бэкенда, чтобы открыть правильную ссылку
      const responseProvider = response.data?.provider;
      let startUrl;
      if (responseProvider === 'google_meet') {
        // Google Meet - используем meet_link или start_url
        startUrl = response.data?.meet_link || response.data?.start_url;
      } else {
        // Zoom - используем zoom_start_url
        startUrl = response.data?.zoom_start_url || response.data?.start_url;
      }
      if (startUrl) {
        window.open(startUrl, '_blank', 'noopener,noreferrer');
      }
      if (onSuccess) onSuccess(response.data);
      setShowModal(false);
    } catch (err) {
      if (err.response?.status === 503) {
        setError('Все аккаунты заняты. Попробуйте позже.');
      } else if (err.response?.status === 400 || err.response?.status === 403) {
        setError(err.response.data?.detail || 'Ошибка создания встречи');
      } else if (err.response?.status === 404) {
        setError('Урок не найден или API endpoint недоступен');
      } else if (err.response?.status === 501) {
        setError('Google Meet пока не настроен. Подключите его в профиле.');
      } else {
        setError(err.response?.data?.detail || err.message || 'Не удалось начать занятие.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Проверяем, доступна ли запись для выбранной платформы
  const isRecordingAvailable = selectedPlatform === 'zoom_pool' || selectedPlatform === 'zoom_personal';
  
  // Проверяем, подключён ли Google Meet
  const googleMeetPlatform = availablePlatforms.find(p => p.id === 'google_meet');
  const isGoogleMeetConnected = googleMeetPlatform?.connected || false;

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        disabled={loading}
        onClick={() => setShowModal(true)}
        style={{
          ...buttonBase,
          background: loading ? '#9ca3af' : PRIMARY_GRADIENT,
          cursor: loading ? 'not-allowed' : 'pointer',
        }}
      >
        {loading ? 'Начинаем...' : 'Начать занятие'}
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
              {/* Заголовок */}
              <div style={{ fontSize: '1.125rem', fontWeight: 600, color: '#1f2937' }}>
                Начать урок
              </div>

              {/* Выбор платформы */}
              <div>
                <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#374151', marginBottom: '0.5rem' }}>
                  Платформа для урока
                </div>
                
                {platformsLoading ? (
                  <div style={{ padding: '1rem', textAlign: 'center', color: '#6b7280' }}>
                    Загрузка...
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {/* Zoom (пул) - всегда доступен */}
                    <div
                      style={platformOptionStyle(selectedPlatform === 'zoom_pool', false)}
                      onClick={() => setSelectedPlatform('zoom_pool')}
                    >
                      <div style={platformIconStyle('zoom')}>
                        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                          <path d="M4.585 11.828V16a2 2 0 002 2h7.829a2 2 0 002-2v-4.172a2 2 0 00-2-2H6.585a2 2 0 00-2 2zm13.243 4.415l2.829 2.122a.75.75 0 001.193-.607V10.071a.75.75 0 00-1.193-.607l-2.829 2.122v4.657z"/>
                        </svg>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500, color: '#1f2937', fontSize: '0.9rem' }}>
                          Zoom
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                          Пул платформы, всегда доступен
                        </div>
                      </div>
                      <div style={{
                        width: '18px',
                        height: '18px',
                        borderRadius: '50%',
                        border: selectedPlatform === 'zoom_pool' ? '5px solid #0b2b65' : '2px solid #d1d5db',
                        backgroundColor: 'white',
                      }} />
                    </div>

                    {/* Google Meet */}
                    <div
                      style={platformOptionStyle(selectedPlatform === 'google_meet', !isGoogleMeetConnected)}
                      onClick={() => isGoogleMeetConnected && setSelectedPlatform('google_meet')}
                    >
                      <div style={platformIconStyle('google_meet')}>
                        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500, color: '#1f2937', fontSize: '0.9rem' }}>
                          Google Meet
                        </div>
                        <div style={{ fontSize: '0.75rem', color: isGoogleMeetConnected ? '#059669' : '#dc2626' }}>
                          {isGoogleMeetConnected 
                            ? (googleMeetPlatform?.email || 'Подключён')
                            : 'Не подключён — настройте в профиле'
                          }
                        </div>
                      </div>
                      {isGoogleMeetConnected ? (
                        <div style={{
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          border: selectedPlatform === 'google_meet' ? '5px solid #00832d' : '2px solid #d1d5db',
                          backgroundColor: 'white',
                        }} />
                      ) : (
                        <a
                          href="/profile?tab=platforms"
                          style={{
                            fontSize: '0.75rem',
                            color: '#0b2b65',
                            textDecoration: 'none',
                            padding: '0.25rem 0.5rem',
                            backgroundColor: '#f0f4ff',
                            borderRadius: '4px',
                          }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          Подключить
                        </a>
                      )}
                    </div>
                    
                    {/* Предупреждение об ограничениях Google Meet */}
                    {selectedPlatform === 'google_meet' && (
                      <div style={{
                        fontSize: '0.8rem',
                        color: '#92400e',
                        padding: '0.75rem',
                        backgroundColor: '#fffbeb',
                        borderRadius: '8px',
                        border: '1px solid #fde68a',
                        marginTop: '0.5rem',
                      }}>
                        <strong>Ограничения Google Meet:</strong>
                        <ul style={{ margin: '0.5rem 0 0 0', paddingLeft: '1.25rem' }}>
                          <li>Нет автоматической расшифровки активности</li>
                          <li>Посещаемость фиксируется по клику «Присоединиться»</li>
                          <li>Ученикам нужен Google аккаунт</li>
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Опция записи (только для Zoom) */}
              {isRecordingAvailable && (
                <>
                  <div style={{ borderTop: '1px solid #e5e7eb', margin: '0.25rem 0' }} />
                  
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
                      Записывать урок
                    </span>
                  </label>

                  {recordLesson && (
                    <div style={{
                      fontSize: '0.8rem', color: '#6b7280', padding: '0.75rem',
                      backgroundColor: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb',
                    }}>
                      Запись будет доступна в разделе «Записи» после окончания урока
                    </div>
                  )}
                </>
              )}

              {/* Примечание для Google Meet */}
              {selectedPlatform === 'google_meet' && (
                <div style={{
                  fontSize: '0.8rem', color: '#92400e', padding: '0.75rem',
                  backgroundColor: '#fffbeb', borderRadius: '8px', border: '1px solid #fde68a',
                }}>
                  Запись в Google Meet настраивается в настройках Google аккаунта
                </div>
              )}

              {/* Кнопки */}
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  onClick={handleStartLesson}
                  disabled={loading}
                  style={{
                    ...buttonBase,
                    flex: 1,
                    padding: '0.75rem 1rem',
                    background: selectedPlatform === 'google_meet' ? MEET_GRADIENT : PRIMARY_GRADIENT,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    boxShadow: selectedPlatform === 'google_meet' 
                      ? '0 3px 10px rgba(0, 172, 71, 0.28)'
                      : '0 3px 10px rgba(11, 43, 101, 0.28)',
                  }}
                >
                  {loading ? 'Начинаем...' : 'Начать урок'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  style={{
                    flex: 0.6,
                    padding: '0.75rem 1rem',
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
    </div>
  );
};

export default StartLessonButton;
