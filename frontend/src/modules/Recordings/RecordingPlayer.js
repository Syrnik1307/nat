import React, { useEffect } from 'react';
import './RecordingPlayer.css';

function RecordingPlayer({ recording, onClose }) {
  // Закрытие по Escape
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    // Блокируем скролл body при открытом плеере
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [onClose]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="recording-player-modal" onClick={handleBackdropClick}>
      <div className="player-container">
        {/* Заголовок */}
        <div className="player-header">
          <div className="player-title">
            <h2>{recording.lesson_info?.subject || 'Запись урока'}</h2>
            <p className="player-subtitle">
              {recording.lesson_info?.group && (
                <span className="group-badge">{recording.lesson_info.group}</span>
              )}
              <span className="date-text">
                {formatDate(recording.lesson_info?.start_time)}
              </span>
            </p>
          </div>
          <button className="close-button" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Видеоплеер */}
        <div className="player-video">
          {recording.play_url ? (
            <iframe
              src={recording.play_url}
              width="100%"
              height="100%"
              frameBorder="0"
              allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              title={recording.lesson_info?.subject || 'Запись урока'}
            />
          ) : (
            <div className="no-video">
              <span className="no-video-icon">🎥</span>
              <p>Видео недоступно</p>
            </div>
          )}
        </div>

        {/* Дополнительная информация */}
        <div className="player-info">
          <div className="info-grid">
            {recording.lesson_info?.teacher && (
              <div className="info-item">
                <span className="info-label">Преподаватель:</span>
                <span className="info-value">{recording.lesson_info.teacher.name}</span>
              </div>
            )}
            
            {recording.duration_display && (
              <div className="info-item">
                <span className="info-label">Длительность:</span>
                <span className="info-value">{recording.duration_display} минут</span>
              </div>
            )}
            
            {recording.views_count > 0 && (
              <div className="info-item">
                <span className="info-label">Просмотров:</span>
                <span className="info-value">{recording.views_count}</span>
              </div>
            )}
            
            {recording.available_days_left !== null && (
              <div className="info-item">
                <span className="info-label">Доступна еще:</span>
                <span className="info-value">
                  {recording.available_days_left} {getDaysWord(recording.available_days_left)}
                </span>
              </div>
            )}
          </div>

          {/* Кнопка скачивания (если доступна) */}
          {recording.download_url && (
            <div className="player-actions">
              <a
                href={recording.download_url}
                download
                className="download-button"
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="button-icon">⬇</span>
                Скачать запись
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function getDaysWord(days) {
  if (days % 10 === 1 && days % 100 !== 11) {
    return 'день';
  } else if ([2, 3, 4].includes(days % 10) && ![12, 13, 14].includes(days % 100)) {
    return 'дня';
  } else {
    return 'дней';
  }
}

export default RecordingPlayer;
