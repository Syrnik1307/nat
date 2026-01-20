import React, { useState, useRef, useEffect, useCallback } from 'react';
import { uploadHomeworkFile } from '../../../../apiService';
import './FileUploader.css';

/**
 * Универсальный компонент для загрузки файлов с drag-and-drop и вставкой из буфера обмена
 * Загружает в Google Drive в папку учителя
 * 
 * @param {string} fileType - 'image' или 'audio'
 * @param {function} onUploadSuccess - callback(url, fileData) при успешной загрузке
 * @param {string} currentUrl - текущий URL файла (для отображения превью)
 * @param {string} accept - строка для HTML accept attribute (например, 'image/*')
 */
const FileUploader = ({ fileType = 'image', onUploadSuccess, currentUrl, accept }) => {
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [isFocused, setIsFocused] = useState(false);
  const fileInputRef = useRef(null);
  const dropzoneRef = useRef(null);

  const acceptTypes = accept || (fileType === 'image' ? 'image/*' : 'audio/*');
  const maxSizeMB = 50;

  // Обработка вставки из буфера обмена (Ctrl+V)
  const handlePaste = useCallback((event) => {
    // Работаем только если dropzone в фокусе или компонент активен
    const clipboardData = event.clipboardData || window.clipboardData;
    if (!clipboardData) return;

    const items = clipboardData.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      
      // Проверяем тип файла в зависимости от fileType
      if (fileType === 'image' && item.type.startsWith('image/')) {
        event.preventDefault();
        const file = item.getAsFile();
        if (file) {
          handleUpload(file);
        }
        break;
      } else if (fileType === 'audio' && item.type.startsWith('audio/')) {
        event.preventDefault();
        const file = item.getAsFile();
        if (file) {
          handleUpload(file);
        }
        break;
      }
    }
  }, [fileType]);

  // Подписка на событие paste когда dropzone в фокусе
  useEffect(() => {
    const dropzone = dropzoneRef.current;
    if (!dropzone || currentUrl || uploading) return;

    const handleFocus = () => setIsFocused(true);
    const handleBlur = () => setIsFocused(false);

    dropzone.addEventListener('focus', handleFocus);
    dropzone.addEventListener('blur', handleBlur);

    return () => {
      dropzone.removeEventListener('focus', handleFocus);
      dropzone.removeEventListener('blur', handleBlur);
    };
  }, [currentUrl, uploading]);

  // Глобальный обработчик paste когда dropzone в фокусе
  useEffect(() => {
    if (!isFocused || currentUrl || uploading) return;

    const pasteHandler = (e) => handlePaste(e);
    document.addEventListener('paste', pasteHandler);

    return () => {
      document.removeEventListener('paste', pasteHandler);
    };
  }, [isFocused, currentUrl, uploading, handlePaste]);

  const validateFile = (file) => {
    // Проверка типа
    const validImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    const validAudioTypes = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/x-m4a'];

    if (fileType === 'image' && !validImageTypes.includes(file.type)) {
      throw new Error(`Неподдерживаемый формат изображения. Разрешены: JPG, PNG, GIF, WebP`);
    }

    if (fileType === 'audio' && !validAudioTypes.includes(file.type)) {
      throw new Error(`Неподдерживаемый формат аудио. Разрешены: MP3, WAV, OGG, M4A`);
    }

    // Проверка размера
    const maxSize = maxSizeMB * 1024 * 1024;
    if (file.size > maxSize) {
      throw new Error(`Файл слишком большой. Максимум: ${maxSizeMB} MB`);
    }
  };

  const handleUpload = async (file) => {
    setError(null);
    setUploading(true);
    setProgress(0);

    try {
      validateFile(file);

      // Реальный прогресс загрузки через onProgress callback
      const response = await uploadHomeworkFile(file, fileType, (progressPercent) => {
        setProgress(progressPercent);
      });

      setProgress(100);

      if (response.data && response.data.url) {
        onUploadSuccess(response.data.url, response.data);
        setTimeout(() => {
          setProgress(0);
          setUploading(false);
        }, 500);
      } else {
        throw new Error('Неверный ответ сервера');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.response?.data?.detail || err.message || 'Ошибка загрузки файла');
      setUploading(false);
      setProgress(0);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      handleUpload(file);
    }
  };

  const handleDragEnter = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragging(true);
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragging(false);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();
  };

  const handleDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragging(false);

    const files = event.dataTransfer.files;
    if (files.length > 0) {
      handleUpload(files[0]);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleRemove = () => {
    onUploadSuccess('', null);
  };

  return (
    <div className="file-uploader">
      {!currentUrl && !uploading && (
        <div
          ref={dropzoneRef}
          className={`file-uploader-dropzone ${dragging ? 'dragging' : ''} ${isFocused ? 'focused' : ''}`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={handleClick}
          tabIndex={0}
          onPaste={handlePaste}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={acceptTypes}
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          <div className="file-uploader-icon">
            {fileType === 'image' ? '' : ''}
          </div>
          <div className="file-uploader-text">
            <strong>Перетащите {fileType === 'image' ? 'изображение' : 'аудио'} сюда</strong>
            <span>или нажмите для выбора</span>
            {fileType === 'image' && (
              <span className="file-uploader-paste-hint">или вставьте Ctrl+V</span>
            )}
          </div>
          <div className="file-uploader-hint">
            {fileType === 'image' ? 'JPG, PNG, GIF, WebP' : 'MP3, WAV, OGG, M4A'} • До {maxSizeMB} MB
          </div>
        </div>
      )}

      {uploading && (
        <div className="file-uploader-progress">
          <div className="file-uploader-progress-bar">
            <div
              className="file-uploader-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="file-uploader-progress-text">
            Загрузка... {progress}%
          </div>
        </div>
      )}

      {currentUrl && !uploading && (
        <div className="file-uploader-preview">
          {fileType === 'image' && (
            <img src={currentUrl} alt="Загруженное изображение" />
          )}
          {fileType === 'audio' && (
            <audio controls src={currentUrl}>
              Ваш браузер не поддерживает аудио.
            </audio>
          )}
          <div className="file-uploader-actions">
            <button
              type="button"
              className="gm-btn-surface"
              onClick={handleClick}
            >
              Заменить
            </button>
            <button
              type="button"
              className="gm-btn-danger-text"
              onClick={handleRemove}
            >
              Удалить
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept={acceptTypes}
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </div>
      )}

      {error && (
        <div className="file-uploader-error">
          {error}
        </div>
      )}
    </div>
  );
};

export default FileUploader;
