import React, { useEffect, useState } from 'react';
import { startLessonNew, updateLesson } from '../../../apiService';

/**
 * Кнопка "Начать занятие" с опцией записи
 * - Автоматически выделяет свободный Zoom аккаунт из пула
 * - Создает Zoom встречу с автозаписью (если включено)
 * - Сразу открывает Zoom для преподавателя
 * - Показывает ошибку если все аккаунты заняты
 * 
 * @param {number} lessonId - ID занятия
 * @param {object} lesson - Объект урока с полями
 * @param {string} groupName - Название группы (для темы встречи)
 * @param {function} onSuccess - Callback после успешного начала
 */
const StartLessonButton = ({ lessonId, lesson, groupName, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showRecordingOption, setShowRecordingOption] = useState(false);
  const [recordLesson, setRecordLesson] = useState(lesson?.record_lesson || false);

  // Блокируем скролл страницы, пока модалка открыта, чтобы исключить дергание на колесе мыши
  useEffect(() => {
    const preventScroll = (e) => e.preventDefault();
    if (showRecordingOption) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      window.addEventListener('wheel', preventScroll, { passive: false });
      return () => {
        document.body.style.overflow = originalOverflow;
        window.removeEventListener('wheel', preventScroll);
      };
    }
  }, [showRecordingOption]);

  const handleStartLesson = async () => {
    setLoading(true);
    setError(null);

    try {
      // Сначала обновляем настройку записи урока, если она изменилась
      if (lesson && recordLesson !== lesson.record_lesson) {
        await updateLesson(lessonId, { record_lesson: recordLesson });
      }

      // Вызов API для начала занятия
      // Бэкенд автоматически:
      // 1. Найдет свободный Zoom аккаунт из пула
      // 2. Создаст Zoom встречу с автозаписью (если record_lesson=true)
      // 3. Вернет ссылки на встречу
      const response = await startLessonNew(lessonId);
      
      // Сразу открываем Zoom для преподавателя
      if (response.data.zoom_start_url) {
        window.open(response.data.zoom_start_url, '_blank');
      }

      if (onSuccess) {
        onSuccess(response.data);
      }
      
      // Закрываем диалог записи после успешного старта
      setShowRecordingOption(false);
    } catch (err) {
      console.error('Ошибка начала занятия:', err);
      console.error('Response data:', err.response?.data);
      console.error('Status:', err.response?.status);
      
      if (err.response?.status === 503) {
        setError('Все Zoom аккаунты заняты. Попробуйте позже.');
      } else if (err.response?.status === 400 || err.response?.status === 403) {
        setError(err.response.data.detail || 'Ошибка создания встречи');
      } else if (err.response?.status === 404) {
        setError('Урок не найден или API endpoint недоступен');
      } else {
        setError(err.response?.data?.detail || err.message || 'Не удалось начать занятие.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleButtonClick = () => {
    // Если настройки записи ещё не показаны - показываем диалог
    if (!showRecordingOption) {
      setShowRecordingOption(true);
    } else {
      // Если диалог уже открыт - запускаем урок
      handleStartLesson();
    }
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        disabled={loading}
        onClick={handleButtonClick}
        style={{
          fontWeight: '600',
          background: loading ? '#9ca3af' : 'linear-gradient(135deg, #0b2b65 0%, #0a1f4d 100%)',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          padding: '0.65rem 1.35rem',
          fontSize: '0.9rem',
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'none',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
          boxShadow: '0 6px 16px rgba(11, 43, 101, 0.35)',
          transform: 'none',
          outline: 'none',
          willChange: 'auto',
        }}
      >
        {loading ? 'Начинаем...' : 'Начать занятие'}
      </button>

      {showRecordingOption && !loading && (
        <>
          {/* Overlay */}
          <div 
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 999,
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
            }}
            onClick={() => setShowRecordingOption(false)}
            onWheel={(e) => e.preventDefault()}
          />
          {/* Modal */}
          <div style={{
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
            minWidth: '320px',
            maxWidth: '420px',
            width: '360px',
            boxSizing: 'border-box',
            animation: 'none',
          }}>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}>
              <div style={{
                fontSize: '1rem',
                fontWeight: '600',
                color: '#1f2937',
              }}>
                Записать урок?
              </div>
              
              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                cursor: 'pointer',
                padding: '0.75rem',
                borderRadius: '8px',
                backgroundColor: recordLesson ? '#f0fdf4' : '#f9fafb',
                border: recordLesson ? '1px solid #d1fae5' : '1px solid #e5e7eb',
                transition: 'all 0.2s ease',
              }}>
                <input
                  type="checkbox"
                  checked={recordLesson}
                  onChange={(e) => setRecordLesson(e.target.checked)}
                  style={{
                    width: '1.25rem',
                    height: '1.25rem',
                    cursor: 'pointer',
                    accentColor: '#2563eb',
                  }}
                />
                <span style={{
                  fontSize: '0.9rem',
                  color: '#1f2937',
                  fontWeight: '500',
                }}>
                  Записывать в Zoom
                </span>
              </label>

              {recordLesson && (
                <div style={{
                  fontSize: '0.8rem',
                  color: '#6b7280',
                  padding: '0.75rem',
                  backgroundColor: '#f9fafb',
                  borderRadius: '8px',
                  border: '1px solid #e5e7eb',
                }}>
                  ℹ️ Запись будет доступна в разделе "Записи" после окончания урока
                </div>
              )}

              <div style={{
                display: 'flex',
                gap: '0.75rem',
              }}>
                <button
                  type="button"
                  onClick={handleStartLesson}
                  style={{
                    flex: 1,
                    padding: '0.65rem 1rem',
                    background: 'linear-gradient(135deg, #0b2b65 0%, #0a1f4d 100%)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'none',
                    boxShadow: '0 3px 10px rgba(11, 43, 101, 0.28)',
                    transform: 'none',
                    outline: 'none',
                  }}
                >
                  Начать
                </button>
                <button
                  type="button"
                  onClick={() => setShowRecordingOption(false)}
                  style={{
                    padding: '0.65rem 1rem',
                    backgroundColor: '#f3f4f6',
                    color: '#6b7280',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.backgroundColor = '#e5e7eb';
                    e.target.style.color = '#374151';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.backgroundColor = '#f3f4f6';
                    e.target.style.color = '#6b7280';
                  }}
                >
                  Отмена
                </button>
              </div>
            </div>
          </div>
          <style>{`
            @keyframes slideUp {
              from {
                opacity: 0;
                transform: translate(-50%, -48%);
              }
              to {
                opacity: 1;
                transform: translate(-50%, -50%);
              }
            }
          `}</style>
        </>
      )}

      {error && (
        <div style={{
          marginTop: '0.5rem',
          padding: '0.75rem',
          backgroundColor: '#fef2f2',
          color: '#dc2626',
          borderRadius: '8px',
          fontSize: '0.875rem',
          border: '1px solid #fecaca',
        }}>
          ⚠️ {error}
        </div>
      )}
    </div>
  );
};

export default StartLessonButton;
