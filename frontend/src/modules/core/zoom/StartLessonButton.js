import React, { useState } from 'react';
import { startLesson } from '../../../apiService';

/**
 * Кнопка "Начать занятие"
 * - Автоматически выделяет свободный Zoom аккаунт из пула
 * - Создает Zoom встречу
 * - Сразу открывает Zoom для преподавателя
 * - Показывает ошибку если все аккаунты заняты
 * 
 * @param {number} lessonId - ID занятия
 * @param {string} groupName - Название группы (для темы встречи)
 * @param {function} onSuccess - Callback после успешного начала
 */
const StartLessonButton = ({ lessonId, groupName, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleStartLesson = async () => {
    setLoading(true);
    setError(null);

    try {
      // Вызов API для начала занятия
      // Бэкенд автоматически:
      // 1. Найдет свободный Zoom аккаунт из пула
      // 2. Создаст Zoom встречу
      // 3. Вернет ссылки на встречу
      const response = await startLesson(lessonId);
      
      // Сразу открываем Zoom для преподавателя
      if (response.data.zoom_start_url) {
        window.open(response.data.zoom_start_url, '_blank');
      }

      if (onSuccess) {
        onSuccess(response.data);
      }
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

  return (
    <>
      <button
        type="button"
        disabled={loading}
        onClick={handleStartLesson}
        style={{
          fontWeight: '600',
          backgroundColor: loading ? '#9ca3af' : 'rgb(5, 150, 105)',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          padding: '0.625rem 1.25rem',
          fontSize: '0.9375rem',
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s ease',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
          boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        }}
        onMouseEnter={(e) => {
          if (!loading) {
            e.target.style.transform = 'scale(1.02)';
          }
        }}
        onMouseLeave={(e) => {
          e.target.style.transform = 'scale(1)';
        }}
      >
        {loading ? '⏳ Создание встречи...' : '▶️ Начать занятие'}
      </button>

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
    </>
  );
};

export default StartLessonButton;
