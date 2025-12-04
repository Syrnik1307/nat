import React, { useState } from 'react';
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
          backgroundColor: loading ? '#9ca3af' : '#2563eb',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          padding: '0.65rem 1.35rem',
          fontSize: '0.9rem',
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s ease',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
          boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)',
        }}
        onMouseEnter={(e) => {
          if (!loading) {
            e.target.style.transform = 'translateY(-2px)';
            e.target.style.boxShadow = '0 6px 16px rgba(37, 99, 235, 0.35)';
          }
        }}
        onMouseLeave={(e) => {
          e.target.style.transform = 'translateY(0)';
          e.target.style.boxShadow = '0 4px 12px rgba(37, 99, 235, 0.25)';
        }}
      >
        {loading ? '⏳ Начинаем...' : '▶ Начать занятие'}
      </button>

      {showRecordingOption && !loading && (
        <>
          {/* Overlay для закрытия при клике снаружи */}
          <div 
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 999,
            }}
            onClick={() => setShowRecordingOption(false)}
          />
          <div style={{
            position: 'absolute',
            top: 0,
            left: '100%',
            marginLeft: '0.5rem',
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '1rem',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
            zIndex: 1000,
            minWidth: '280px',
          }}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
          }}>
            <div style={{
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#111827',
            }}>
              ⚙️ Настройки записи
            </div>
            
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              padding: '0.5rem',
              borderRadius: '6px',
              backgroundColor: recordLesson ? '#f0fdf4' : 'transparent',
              border: recordLesson ? '1px solid #86efac' : '1px solid transparent',
              transition: 'all 0.2s ease',
            }}>
              <input
                type="checkbox"
                checked={recordLesson}
                onChange={(e) => setRecordLesson(e.target.checked)}
                style={{
                  width: '1.125rem',
                  height: '1.125rem',
                  cursor: 'pointer',
                }}
              />
              <span style={{
                fontSize: '0.875rem',
                color: '#374151',
              }}>
                🎥 Записывать урок в Zoom
              </span>
            </label>

            {recordLesson && (
              <div style={{
                fontSize: '0.75rem',
                color: '#6b7280',
                padding: '0.5rem',
                backgroundColor: '#f3f4f6',
                borderRadius: '6px',
              }}>
                ℹ️ Запись появится в разделе "Записи" после окончания урока и будет доступна вашей группе.
              </div>
            )}

            <div style={{
              display: 'flex',
              gap: '0.5rem',
              marginTop: '0.25rem',
            }}>
              <button
                type="button"
                onClick={handleStartLesson}
                style={{
                  flex: 1,
                  padding: '0.55rem 1rem',
                  background: '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '0.875rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: '0 2px 8px rgba(37, 99, 235, 0.2)',
                }}
                onMouseEnter={(e) => {
                  e.target.style.transform = 'translateY(-1px)';
                  e.target.style.boxShadow = '0 4px 12px rgba(37, 99, 235, 0.3)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.transform = 'translateY(0)';
                  e.target.style.boxShadow = '0 2px 8px rgba(37, 99, 235, 0.2)';
                }}
              >
                ▶ Начать
              </button>
              <button
                type="button"
                onClick={() => setShowRecordingOption(false)}
                style={{
                  padding: '0.55rem 1rem',
                  backgroundColor: '#f3f4f6',
                  color: '#6b7280',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  fontSize: '0.875rem',
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
