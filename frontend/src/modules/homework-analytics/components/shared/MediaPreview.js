import React, { useState } from 'react';
import './MediaPreview.css';

/**
 * Универсальный компонент для отображения медиа (изображения и аудио)
 * с обработкой ошибок загрузки и прогрессом
 */
const MediaPreview = ({ type = 'image', src, alt = 'Медиа', className = '' }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Нормализация URL - добавляем baseURL если нужно
  const normalizeUrl = (url) => {
    if (!url) return '';
    
    // Если уже полный URL, возвращаем как есть
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    
    // Если начинается с /media, добавляем базовый URL сервера
    if (url.startsWith('/media')) {
      // В production это будет домен сервера, в dev - proxy
      return url;
    }
    
    // Если относительный путь без слэша, добавляем /media/
    return `/media/${url}`;
  };

  const normalizedSrc = normalizeUrl(src);

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
        <span className="media-preview-icon">📎</span>
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
            <span className="error-icon">⚠️</span>
            <p>Не удалось загрузить изображение</p>
            <button 
              className="btn-retry"
              onClick={() => {
                setError(false);
                setLoading(true);
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
            <span className="error-icon">⚠️</span>
            <p>Не удалось загрузить аудио</p>
            <button 
              className="btn-retry"
              onClick={() => {
                setError(false);
                setLoading(true);
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
