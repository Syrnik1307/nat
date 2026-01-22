import React, { useMemo, useState } from 'react';
import './MediaPreview.css';

const IconPaperclip = ({ size = 28, className = '' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    <path d="M21.44 11.05 12.25 20.24a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.82-2.82l8.49-8.48" />
  </svg>
);

const IconAlertTriangle = ({ size = 28, className = '' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
    <path d="M12 9v4" />
    <path d="M12 17h.01" />
  </svg>
);

/**
 * Универсальный компонент для отображения медиа (изображения и аудио)
 * с обработкой ошибок загрузки и прогрессом
 */
const MediaPreview = ({ type = 'image', src, alt = 'Медиа', className = '' }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [reloadNonce, setReloadNonce] = useState(0);

  // Сбрасываем состояние загрузки при смене src
  React.useEffect(() => {
    setLoading(true);
    setError(false);
  }, [src]);

  // Нормализация URL - добавляем baseURL если нужно, конвертируем Google Drive
  const normalizeUrl = (url) => {
    if (!url) return '';

    // blob/data URL (локальные превью) — не трогаем
    if (url.startsWith('blob:') || url.startsWith('data:')) {
      return url;
    }
    
    // Конвертация Google Drive ссылок для inline отображения
    // https://drive.google.com/uc?export=download&id=FILE_ID -> прямая ссылка
    if (url.includes('drive.google.com')) {
      // Извлекаем file ID из разных форматов Google Drive URL
      let fileId = null;
      
      // Формат: /uc?export=download&id=FILE_ID или /uc?id=FILE_ID
      const ucMatch = url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
      if (ucMatch) {
        fileId = ucMatch[1];
      }
      
      // Формат: /file/d/FILE_ID/view или /file/d/FILE_ID
      const fileMatch = url.match(/\/file\/d\/([a-zA-Z0-9_-]+)/);
      if (fileMatch) {
        fileId = fileMatch[1];
      }
      
      // Формат: /open?id=FILE_ID
      const openMatch = url.match(/\/open\?id=([a-zA-Z0-9_-]+)/);
      if (openMatch) {
        fileId = openMatch[1];
      }
      
      if (fileId) {
        // Используем lh3.googleusercontent.com для прямого доступа к изображениям
        return `https://lh3.googleusercontent.com/d/${fileId}`;
      }
    }
    
    // Если уже полный URL (не Google Drive), возвращаем как есть
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }

    // Абсолютные пути на нашем домене (например /api/homework/file/...) — возвращаем как есть
    if (url.startsWith('/')) {
      return url;
    }

    // Частый кейс: пришёл путь без ведущего слэша (api/..., media/...)
    if (url.startsWith('api/') || url.startsWith('media/')) {
      return `/${url}`;
    }
    
    // Если относительный путь без слэша, добавляем /media/
    return `/media/${url}`;
  };

  const normalizedSrc = useMemo(() => {
    const base = normalizeUrl(src);
    if (!base) return '';
    const sep = base.includes('?') ? '&' : '?';
    return `${base}${sep}v=${reloadNonce}`;
  }, [src, reloadNonce]);

  const handleLoad = () => {
    setLoading(false);
    setError(false);
  };

  const handleError = () => {
    setLoading(false);
    setError(true);
    console.error(`[MediaPreview] Ошибка загрузки ${type}:`, normalizedSrc);
  };

  if (!src) {
    return (
      <div className={`media-preview media-preview-empty ${className}`}>
        <IconPaperclip size={28} className="media-preview-icon" />
        <p>Файл не прикреплён</p>
      </div>
    );
  }

  if (type === 'image') {
    return (
      <div className={`media-preview media-preview-image ${className}`}>
        {loading && (
          <div className="media-preview-loading">
            <div className="spinner"></div>
            <p>Загрузка изображения...</p>
          </div>
        )}
        {error && (
          <div className="media-preview-error">
            <IconAlertTriangle size={28} className="error-icon" />
            <p>Не удалось загрузить изображение</p>
            <button 
              className="btn-retry"
              onClick={() => {
                setError(false);
                setLoading(true);
                setReloadNonce((n) => n + 1);
              }}
            >
              Повторить
            </button>
          </div>
        )}
        <img
          src={normalizedSrc}
          alt={alt}
          onLoad={handleLoad}
          onError={handleError}
          style={{ display: error || loading ? 'none' : 'block' }}
          className="media-preview-img"
        />
      </div>
    );
  }

  if (type === 'audio') {
    return (
      <div className={`media-preview media-preview-audio ${className}`}>
        {loading && (
          <div className="media-preview-loading">
            <div className="spinner"></div>
            <p>Загрузка аудио...</p>
          </div>
        )}
        {error && (
          <div className="media-preview-error">
            <IconAlertTriangle size={28} className="error-icon" />
            <p>Не удалось загрузить аудио</p>
            <button 
              className="btn-retry"
              onClick={() => {
                setError(false);
                setLoading(true);
                setReloadNonce((n) => n + 1);
              }}
            >
              Повторить
            </button>
          </div>
        )}
        <audio
          controls
          src={normalizedSrc}
          onLoadedMetadata={handleLoad}
          onError={handleError}
          style={{ display: error ? 'none' : 'block' }}
          className="media-preview-audio-player"
        >
          Ваш браузер не поддерживает аудио.
        </audio>
      </div>
    );
  }

  return (
    <div className={`media-preview media-preview-unknown ${className}`}>
      <p>Неподдерживаемый тип медиа: {type}</p>
    </div>
  );
};

export default MediaPreview;
