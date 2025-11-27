import React from 'react';
import './RecordingCard.css';

function RecordingCard({ recording, onPlay }) {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getDaysLeftColor = (daysLeft) => {
    if (daysLeft > 30) return 'green';
    if (daysLeft > 7) return 'orange';
    return 'red';
  };

  const getStatusBadge = () => {
    switch (recording.status) {
      case 'ready':
        return <span className="status-badge ready">✓ Готово</span>;
      case 'processing':
        return <span className="status-badge processing">⏳ Обработка...</span>;
      case 'failed':
        return <span className="status-badge failed">✗ Ошибка</span>;
      default:
        return null;
    }
  };

  return (
    <div className="recording-card">
      {/* Превью */}
      <div className="recording-thumbnail">
        {recording.thumbnail_url ? (
          <img src={recording.thumbnail_url} alt="Preview" />
        ) : (
          <div className="no-thumbnail">
            <span className="thumbnail-icon">🎥</span>
          </div>
        )}
        <div className="play-overlay" onClick={() => onPlay(recording)}>
          <div className="play-button">▶</div>
        </div>
        {recording.duration_display && (
          <div className="duration-badge">
            {recording.duration_display} мин
          </div>
        )}
      </div>

      {/* Информация */}
      <div className="recording-info">
        <div className="recording-title">
          {recording.lesson_info?.subject || 'Урок'}
        </div>

        <div className="recording-subtitle">
          {recording.lesson_info?.group && (
            <span className="group-name">{recording.lesson_info.group}</span>
          )}
        </div>

        <div className="recording-meta">
          <div className="meta-row">
            <span className="meta-icon">📅</span>
            <span>{formatDate(recording.lesson_info?.start_time)}</span>
          </div>
          <div className="meta-row">
            <span className="meta-icon">🕐</span>
            <span>{formatTime(recording.lesson_info?.start_time)}</span>
          </div>
          {recording.lesson_info?.teacher && (
            <div className="meta-row">
              <span className="meta-icon">👨‍🏫</span>
              <span>{recording.lesson_info.teacher.name}</span>
            </div>
          )}
        </div>

        {/* Статистика */}
        <div className="recording-stats">
          <div className="stat">
            <span className="stat-icon">👁️</span>
            <span className="stat-value">{recording.views_count || 0}</span>
            <span className="stat-label">просмотров</span>
          </div>
          
          {recording.file_size_mb && (
            <div className="stat">
              <span className="stat-icon">💾</span>
              <span className="stat-value">{recording.file_size_mb}</span>
              <span className="stat-label">МБ</span>
            </div>
          )}
          
          {recording.available_days_left !== null && (
            <div className="stat">
              <span 
                className="stat-icon"
                style={{ color: getDaysLeftColor(recording.available_days_left) }}
              >
                ⏰
              </span>
              <span className="stat-value">{recording.available_days_left}</span>
              <span className="stat-label">дней</span>
            </div>
          )}
        </div>

        {/* Кнопка воспроизведения */}
        <button 
          className="watch-button"
          onClick={() => onPlay(recording)}
          disabled={recording.status !== 'ready'}
        >
          {recording.status === 'ready' ? (
            <>
              <span className="button-icon">▶</span>
              Смотреть запись
            </>
          ) : recording.status === 'processing' ? (
            <>
              <span className="button-icon">⏳</span>
              Обработка...
            </>
          ) : (
            <>
              <span className="button-icon">✗</span>
              Недоступно
            </>
          )}
        </button>

        {getStatusBadge()}
      </div>
    </div>
  );
}

export default RecordingCard;
