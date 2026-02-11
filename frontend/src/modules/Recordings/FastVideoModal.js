import React, { useEffect, useRef, useCallback, useState } from 'react';
import ReactDOM from 'react-dom';
import './FastVideoModal.css';

/**
 * FastVideoModal - Быстрое модальное окно для просмотра записей
 * 
 * Использует Google Drive embed (iframe) для мгновенного воспроизведения.
 * Fallback: прямая ссылка на скачивание.
 */

function FastVideoModal({ recording, onClose }) {
  const iframeRef = useRef(null);
  const videoRef = useRef(null);
  const modalRef = useRef(null);
  const [showDetails, setShowDetails] = useState(false);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [iframeError, setIframeError] = useState(false);
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [videoError, setVideoError] = useState(false);

  // Определяем: есть ли GDrive или это local storage запись
  const hasGdrive = !!recording?.gdrive_file_id;
  
  // Для local storage записей используем play_url/download_url напрямую
  const isLocalStorage = !hasGdrive && (recording?.play_url || recording?.download_url);
  // Для local записей используем streaming endpoint (авторизованный) или прямой URL
  const localVideoUrl = isLocalStorage
    ? (() => {
        // Используем stream endpoint для авторизованного доступа
        const token = localStorage.getItem('tp_access_token');
        if (token) {
          return `/schedule/api/recordings/${recording.id}/stream/?token=${encodeURIComponent(token)}`;
        }
        // Fallback на прямой URL
        return recording?.play_url || recording?.download_url;
      })()
    : null;

  // Google Drive embed URL
  const embedUrl = hasGdrive
    ? `https://drive.google.com/file/d/${recording.gdrive_file_id}/preview`
    : null;

  // Fallback: direct download link
  const downloadUrl = hasGdrive
    ? `https://drive.google.com/uc?export=download&id=${recording.gdrive_file_id}`
    : recording?.download_url || recording?.play_url || null;

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

  // Обработка загрузки iframe
  const handleIframeLoad = useCallback(() => {
    setIframeLoaded(true);
  }, []);

  // Открыть в новой вкладке (Google Drive viewer)
  const handleOpenInNewTab = useCallback(() => {
    if (!recording?.gdrive_file_id) return;
    window.open(`https://drive.google.com/file/d/${recording.gdrive_file_id}/view`, '_blank', 'noopener,noreferrer');
  }, [recording?.gdrive_file_id]);

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

        {/* Видеоплеер (Google Drive Embed или HTML5 Video для local storage) */}
        <div className="fast-video-player">
          {isLocalStorage ? (
            /* Local storage: HTML5 video player */
            <>
              {!videoLoaded && !videoError && (
                <div className="fast-video-loading" role="status" aria-live="polite">
                  <div className="fast-video-loading-spinner" aria-hidden="true" />
                  <div className="fast-video-loading-text">
                    <div className="fast-video-loading-title">Загрузка видео…</div>
                  </div>
                </div>
              )}
              {videoError && (
                <div className="fast-video-error">
                  <div className="fast-video-error-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <circle cx="12" cy="12" r="10" />
                      <path d="M12 8v4M12 16h.01" />
                    </svg>
                  </div>
                  <p>Не удалось загрузить видео</p>
                  {downloadUrl && (
                    <a 
                      href={downloadUrl}
                      className="fast-video-retry"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Скачать видео
                    </a>
                  )}
                </div>
              )}
              <video
                ref={videoRef}
                src={localVideoUrl}
                controls
                autoPlay={false}
                playsInline
                preload="auto"
                onCanPlay={() => setVideoLoaded(true)}
                onError={() => setVideoError(true)}
                style={{ 
                  width: '100%', 
                  height: '100%', 
                  backgroundColor: '#000',
                  display: videoError ? 'none' : 'block',
                  opacity: videoLoaded ? 1 : 0,
                  transition: 'opacity 0.3s ease'
                }}
                title={title}
              />
            </>
          ) : embedUrl ? (
            /* GDrive: iframe embed */
            <>
              {!iframeLoaded && (
                <div className="fast-video-loading" role="status" aria-live="polite">
                  <div className="fast-video-loading-spinner" aria-hidden="true" />
                  <div className="fast-video-loading-text">
                    <div className="fast-video-loading-title">Загрузка видео…</div>
                  </div>
                </div>
              )}

              <iframe
                ref={iframeRef}
                src={embedUrl}
                className="fast-video-iframe"
                allow="autoplay; encrypted-media"
                allowFullScreen
                onLoad={handleIframeLoad}
                style={{ opacity: iframeLoaded ? 1 : 0 }}
                title={title}
              />
            </>
          ) : (
            <div className="fast-video-error">
              <div className="fast-video-error-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 8v4M12 16h.01" />
                </svg>
              </div>
              <p>Видео недоступно</p>
              {downloadUrl && (
                <a 
                  href={downloadUrl}
                  className="fast-video-retry"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Скачать видео
                </a>
              )}
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
