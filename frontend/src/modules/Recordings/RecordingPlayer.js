import React, { useEffect, useRef, useState } from 'react';
import './RecordingPlayer.css';

function RecordingPlayer({ recording, onClose }) {
  const [copyState, setCopyState] = useState('idle');
  const copyTimeoutRef = useRef(null);
  const lessonInfo = recording.lesson_info || {};
  const subject = lessonInfo.subject || 'Запись урока';
  const accessGroups = Array.isArray(recording.access_groups) && recording.access_groups.length > 0
    ? recording.access_groups
    : (lessonInfo.group || lessonInfo.group_name
        ? [{ id: lessonInfo.group_id, name: lessonInfo.group || lessonInfo.group_name }]
        : []);
  const accessStudents = Array.isArray(recording.access_students) ? recording.access_students : [];
  const groupName = accessGroups.length > 1
    ? `${accessGroups.length} групп`
    : accessGroups[0]?.name || null;

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
    };
  }, [onClose]);

  const formatDateTime = (dateString, options = {}) => {
    if (!dateString) {
      return null;
    }

    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...options
    });
  };

  const formattedFullDate = formatDateTime(lessonInfo.start_time);
  const availableDaysText =
    recording.available_days_left !== null && recording.available_days_left !== undefined
      ? `${recording.available_days_left} ${getDaysWord(recording.available_days_left)}`
      : null;

  const chips = [
    groupName && { icon: '', text: groupName },
    recording.duration_display && { icon: '', text: `${recording.duration_display} мин` },
    availableDaysText && { icon: '', text: `Еще ${availableDaysText}` }
  ].filter(Boolean);

  const heroMeta = [
    { label: 'Дата урока', value: formattedFullDate },
    { label: 'Группа', value: groupName },
    { label: 'Преподаватель', value: lessonInfo.teacher?.name }
  ].filter((item) => Boolean(item.value));

  const statusLabels = {
    ready: 'Готово к просмотру',
    processing: 'В обработке',
    failed: 'Ошибка записи',
    archived: 'Архив',
    default: 'Сохранена'
  };

  const detailRows = [
    { label: 'Статус', value: statusLabels[recording.status] || statusLabels.default },
    { label: 'Группы', value: accessGroups.map((group) => group.name).join(', ') || null },
    { label: 'Индивидуальный доступ', value: accessStudents.map((student) => student.name).join(', ') || null },
    { label: 'Продолжительность', value: recording.duration_display ? `${recording.duration_display} минут` : null },
    { label: 'Просмотров', value: typeof recording.views_count === 'number' ? `${recording.views_count}` : null },
    { label: 'Размер файла', value: recording.file_size_mb ? `${recording.file_size_mb} МБ` : null },
    { label: 'Доступна', value: availableDaysText ? `Еще ${availableDaysText}` : 'Без ограничения' }
  ].filter((item) => Boolean(item.value));

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleOpenInNewTab = () => {
    if (!recording.play_url || typeof window === 'undefined') {
      return;
    }
    window.open(recording.play_url, '_blank', 'noopener,noreferrer');
  };

  const handleCopyLink = async () => {
    if (!recording.play_url) {
      return;
    }

    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(recording.play_url);
      } else {
        throw new Error('Clipboard API unavailable');
      }
      setCopyState('copied');
    } catch (error) {
      window.prompt('Скопируйте ссылку на запись', recording.play_url);
      setCopyState('copied');
    }

    if (copyTimeoutRef.current) {
      clearTimeout(copyTimeoutRef.current);
    }
    copyTimeoutRef.current = setTimeout(() => setCopyState('idle'), 2000);
  };

  const heroSubtitle = formattedFullDate
    ? `Запись от ${formattedFullDate}`
    : 'Плеер Lectio Space';

  // Проверяем, является ли URL ссылкой на Google Drive (не поддерживает iframe)
  const isGoogleDriveUrl = recording.play_url && (
    recording.play_url.includes('drive.google.com') ||
    recording.play_url.includes('docs.google.com')
  );

  const mediaStats = [
    {
      label: 'Просмотров',
      value: recording.views_count ?? 0
    },
    {
      label: 'Доступ',
      value: availableDaysText ? `Еще ${availableDaysText}` : 'Без ограничений'
    }
  ];

  return (
    <div className="recording-player-modal" onClick={handleBackdropClick}>
      <div className="recording-player-shell">
        <button className="recording-player-close" onClick={onClose}>
          <span>Esc</span>
          ✕
        </button>

        <header className="recording-player-hero">
          {chips.length > 0 && (
            <div className="hero-badges">
              {chips.map((chip) => (
                <span key={chip.text} className="hero-badge">
                  <span className="hero-badge-icon">{chip.icon}</span>
                  {chip.text}
                </span>
              ))}
            </div>
          )}
          <h2>{subject}</h2>
          <p className="hero-subtitle">{heroSubtitle}</p>

          {heroMeta.length > 0 && (
            <div className="hero-meta">
              {heroMeta.map((item) => (
                <div key={item.label} className="hero-meta-item">
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
          )}
        </header>

        <div className="recording-player-body">
          <div className="player-media-column">
            <div className="player-video-wrapper">
              {recording.streaming_url ? (
                // Используем HTML5 video player для Google Drive
                <video
                  src={recording.streaming_url}
                  controls
                  autoPlay
                  playsInline
                  className="player-video"
                  onError={(e) => {
                    console.error('Video playback error:', e);
                    // Если не удалось загрузить, показываем fallback
                    e.target.style.display = 'none';
                    e.target.nextSibling.style.display = 'flex';
                  }}
                >
                  Ваш браузер не поддерживает воспроизведение видео.
                </video>
              ) : recording.play_url ? (
                isGoogleDriveUrl ? (
                  // Fallback: Google Drive без streaming_url - показываем placeholder с кнопкой
                  <div className="player-video-placeholder gdrive-placeholder">
                    <div className="gdrive-icon">
                      <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M7.71 3.5L1.15 15l4.58 7.5h13.54l4.58-7.5L17.29 3.5H7.71zm-.29 2h1.24l5.78 9.44-2.47 4.06H6.82l-2.47-4.06 5.07-8.3V5.5zm2.86 0h3.44l5.78 9.44H8.5L5.57 5.5h4.71zm4.72 0h1.24L21.02 14.56l-2.47 4.06h-5.15l-2.47-4.06L16.71 5.5h-1.71z"/>
                      </svg>
                    </div>
                    <p className="gdrive-title">Видео в Google Drive</p>
                    <p className="gdrive-hint">Нажмите кнопку ниже для просмотра</p>
                    <button 
                      type="button" 
                      className="gdrive-open-btn"
                      onClick={handleOpenInNewTab}
                    >
                      ▶ Открыть видео
                    </button>
                  </div>
                ) : (
                  <iframe
                    src={recording.play_url}
                    title={subject}
                    frameBorder="0"
                    allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                )
              ) : (
                <div className="player-video-placeholder">
                  <span className="placeholder-icon"></span>
                  <p>Видео недоступно</p>
                </div>
              )}
              {/* Fallback для ошибки загрузки видео */}
              <div className="player-video-placeholder gdrive-placeholder" style={{ display: 'none' }}>
                <div className="gdrive-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                  </svg>
                </div>
                <p className="gdrive-title">Не удалось загрузить видео</p>
                <p className="gdrive-hint">Попробуйте открыть в новой вкладке</p>
                <button 
                  type="button" 
                  className="gdrive-open-btn"
                  onClick={handleOpenInNewTab}
                >
                  ▶ Открыть видео
                </button>
              </div>
            </div>

            <div className="player-media-footer">
              <div className="media-stat">
                <span className="media-stat-label">{mediaStats[0].label}</span>
                <span className="media-stat-value">{mediaStats[0].value}</span>
              </div>

              <div className="media-wave" aria-hidden="true">
                {[...Array(7)].map((_, index) => (
                  <span key={index} className={`wave-bar wave-${index + 1}`} />
                ))}
              </div>

              <div className="media-stat">
                <span className="media-stat-label">{mediaStats[1].label}</span>
                <span className="media-stat-value">{mediaStats[1].value}</span>
              </div>
            </div>
          </div>

          <aside className="player-sidebar">
            <div className="sidebar-card">
              <h4>Детали урока</h4>
              <dl className="sidebar-details">
                {detailRows.map((detail) => (
                  <div key={detail.label}>
                    <dt>{detail.label}</dt>
                    <dd>{detail.value}</dd>
                  </div>
                ))}
              </dl>
            </div>

            <div className="sidebar-card">
              <h4>Доступ к записи</h4>
              <div className="player-actions">
                <button
                  type="button"
                  className="player-action-btn primary"
                  onClick={handleOpenInNewTab}
                  disabled={!recording.play_url}
                >
                  Открыть плеер
                </button>

                {recording.download_url && (
                  <a
                    href={recording.download_url}
                    className="player-action-btn secondary"
                    target="_blank"
                    rel="noopener noreferrer"
                    download
                  >
                    Скачать файл
                  </a>
                )}

                <button
                  type="button"
                  className="player-action-btn ghost"
                  onClick={handleCopyLink}
                  disabled={!recording.play_url}
                >
                  {copyState === 'copied' ? 'Ссылка скопирована' : 'Скопировать ссылку'}
                </button>
              </div>
              <p className="player-hint">
                Запись хранится в защищенном облаке Lectio Space. Делитесь ссылкой только с участниками группы.
              </p>
            </div>
          </aside>
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
