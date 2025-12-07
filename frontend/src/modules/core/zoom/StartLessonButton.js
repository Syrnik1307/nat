import React, { useEffect, useState } from 'react';
import { startLessonNew, updateLesson } from '../../../apiService';

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
    width: '360px',
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

const StartLessonButton = ({ lessonId, lesson, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [recordLesson, setRecordLesson] = useState(lesson?.record_lesson || false);

  // Блокируем скролл и компенсируем ширину скроллбара, чтобы не прыгал лэйаут
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
      });
      if (response.data?.zoom_start_url) {
        window.open(response.data.zoom_start_url, '_blank', 'noopener,noreferrer');
      }
      if (onSuccess) onSuccess(response.data);
      setShowModal(false);
    } catch (err) {
      if (err.response?.status === 503) {
        setError('Все Zoom аккаунты заняты. Попробуйте позже.');
      } else if (err.response?.status === 400 || err.response?.status === 403) {
        setError(err.response.data?.detail || 'Ошибка создания встречи');
      } else if (err.response?.status === 404) {
        setError('Урок не найден или API endpoint недоступен');
      } else {
        setError(err.response?.data?.detail || err.message || 'Не удалось начать занятие.');
      }
    } finally {
      setLoading(false);
    }
  };

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
              <div style={{ fontSize: '1rem', fontWeight: 600, color: '#1f2937' }}>
                Записать урок?
              </div>

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
                  Записывать в Zoom
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

              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                  type="button"
                  onClick={handleStartLesson}
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
                  {loading ? 'Начинаем...' : 'Начать'}
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
    </div>
  );
};

export default StartLessonButton;
