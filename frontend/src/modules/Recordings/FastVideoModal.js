import React, { useEffect, useRef, useCallback, useState } from 'react';
import ReactDOM from 'react-dom';
import './FastVideoModal.css';

/**
 * FastVideoModal - Быстрое модальное окно для просмотра записей
 * 
 * Оптимизации:
 * 1. Минимальный рендер - только видео и базовая информация
 * 2. Прямой streaming URL без промежуточных запросов
 * 3. Мгновенное открытие с анимацией
 * 4. Lazy-loaded детали (подгружаются после открытия)
 */

// Токен для авторизации
const getAccessToken = () => localStorage.getItem('tp_access_token') || '';

function FastVideoModal({ recording, onClose }) {
  const videoRef = useRef(null);
  const modalRef = useRef(null);
  const [showDetails, setShowDetails] = useState(false);
  const [videoError, setVideoError] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  // Быстрое получение URL для стриминга
  const getVideoUrl = useCallback(() => {
    if (!recording?.id) return null;
    
    // Приоритет: streaming_url > play_url (прямая ссылка) > stream endpoint
    if (recording.streaming_url) {
      return recording.streaming_url;
    }
    
    // Если есть play_url и это НЕ Google Drive - используем его
    const isGoogleDriveUrl = recording.play_url && (
      recording.play_url.includes('drive.google.com') ||
      recording.play_url.includes('docs.google.com')
    );
    
    if (recording.play_url && !isGoogleDriveUrl) {
      return recording.play_url;
    }
    
    // Для Google Drive или отсутствия play_url используем backend stream endpoint
    const token = getAccessToken();
    return `/schedule/api/recordings/${recording.id}/stream/?token=${encodeURIComponent(token)}`;
  }, [recording?.id, recording?.streaming_url, recording?.play_url]);

  const videoUrl = getVideoUrl();

  // Закрытие по Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    
    // Показываем детали через 300ms (после анимации открытия)
    const detailsTimer = setTimeout(() => setShowDetails(true), 300);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
      clearTimeout(detailsTimer);
    };
  }, [onClose]);

  // Клик по оверлею
  const handleBackdropClick = useCallback((e) => {
    if (e.target === modalRef.current) {
      onClose();
    }
  }, [onClose]);

  // Обработка ошибки видео
  const handleVideoError = useCallback(() => {
    setVideoError(true);
  }, []);

  // Обработка успешной загрузки
  const handleVideoLoaded = useCallback(() => {
    setVideoError(false);
  }, []);

  // Play/Pause отслеживание
  const handlePlay = useCallback(() => setIsPlaying(true), []);
  const handlePause = useCallback(() => setIsPlaying(false), []);

  // Получаем базовую информацию
  const title = recording?.title || recording?.lesson_info?.subject || 'Запись урока';
  const groupName = recording?.access_groups?.[0]?.name 
    || recording?.lesson_info?.group 
    || recording?.lesson_info?.group_name 
    || '';

  // Если нет document (SSR), не рендерим
  if (typeof document === 'undefined') return null;

  return ReactDOM.createPortal(
    <div 
      ref={modalRef}
      className="fast-video-modal" 
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="fast-video-title"
    >
      <div className="fast-video-container">
        {/* Кнопка закрытия */}
        <button 
          className="fast-video-close" 
          onClick={onClose}
          aria-label="Закрыть"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        {/* Заголовок */}
        <header className="fast-video-header">
          <h2 id="fast-video-title" className="fast-video-title">{title}</h2>
          {groupName && (
            <span className="fast-video-group">{groupName}</span>
          )}
        </header>

        {/* Видеоплеер */}
        <div className={`fast-video-player ${isPlaying ? 'is-playing' : ''}`}>
          {videoUrl && !videoError ? (
            <video
              ref={videoRef}
              src={videoUrl}
              controls
              autoPlay
              playsInline
              preload="auto"
              onError={handleVideoError}
              onLoadedData={handleVideoLoaded}
              onPlay={handlePlay}
              onPause={handlePause}
              className="fast-video-element"
            >
              Ваш браузер не поддерживает воспроизведение видео.
            </video>
          ) : (
            <div className="fast-video-error">
              <div className="fast-video-error-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 8v4M12 16h.01" />
                </svg>
              </div>
              <p>Не удалось загрузить видео</p>
              <button 
                className="fast-video-retry"
                onClick={() => {
                  setVideoError(false);
                  videoRef.current?.load();
                }}
              >
                Попробовать снова
              </button>
            </div>
          )}
        </div>

        {/* Детали (lazy-loaded) */}
        {showDetails && (
          <footer className="fast-video-footer">
            <div className="fast-video-stats">
              {recording?.views_count !== undefined && (
                <div className="fast-video-stat">
                  <span className="stat-value">{recording.views_count}</span>
                  <span className="stat-label">просмотров</span>
                </div>
              )}
              {recording?.duration_display && (
                <div className="fast-video-stat">
                  <span className="stat-value">{recording.duration_display}</span>
                  <span className="stat-label">минут</span>
                </div>
              )}
              {recording?.file_size_mb && (
                <div className="fast-video-stat">
                  <span className="stat-value">{recording.file_size_mb}</span>
                  <span className="stat-label">МБ</span>
                </div>
              )}
            </div>

            <div className="fast-video-actions">
              {recording?.download_url && (
                <a
                  href={recording.download_url}
                  className="fast-video-btn secondary"
                  target="_blank"
                  rel="noopener noreferrer"
                  download
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
                  </svg>
                  Скачать
                </a>
              )}
            </div>
          </footer>
        )}
      </div>
    </div>,
    document.body
  );
}

export default FastVideoModal;
