import React, { useState, useRef, useCallback, useEffect } from 'react';
import { uploadStudentAnswerFile } from '../../../../apiService';
import './AnswerAttachment.css';

/**
 * Компактный компонент для прикрепления файлов/фото к ответу ученика.
 * Позволяет добавить до 3 файлов к любому типу вопроса.
 * 
 * Поддерживает:
 * - Выбор файла через кнопку
 * - Drag & Drop
 * - Вставку из буфера обмена (Ctrl+V)
 */
const AnswerAttachment = ({ 
  attachments = [], 
  onChange, 
  disabled = false, 
  homeworkId = null,
  maxFiles = 3,
  maxSizeMB = 10 
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);

  // Текущие загруженные файлы
  const files = Array.isArray(attachments) ? attachments : [];

  // Валидация файла
  const validateFile = (file) => {
    if (file.size > maxSizeMB * 1024 * 1024) {
      return `Файл слишком большой. Максимум: ${maxSizeMB} MB`;
    }
    return null;
  };

  // Загрузка файла
  const handleUpload = async (file) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    if (files.length >= maxFiles) {
      setError(`Можно прикрепить максимум ${maxFiles} файл(ов)`);
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setError(null);

    try {
      const response = await uploadStudentAnswerFile(file, homeworkId, (percent) => {
        setUploadProgress(percent);
      });

      if (response.data?.url) {
        const newFile = {
          url: response.data.url,
          file_id: response.data.file_id,
          name: response.data.file_name || file.name,
          size: response.data.size || file.size,
          mime_type: response.data.mime_type || file.type,
        };
        onChange([...files, newFile]);
        setExpanded(true); // Раскрываем после успешной загрузки
      }
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.message || 'Ошибка загрузки';
      setError(errMsg);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  // Обработка выбора файла
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(file);
    }
    e.target.value = '';
  };

  // Обработка Drag & Drop
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled && !uploading) {
      setDragOver(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    if (disabled || uploading) return;

    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleUpload(file);
    }
  };

  // Обработка вставки из буфера (Ctrl+V)
  const handlePaste = useCallback((e) => {
    if (disabled || uploading) return;

    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          handleUpload(file);
        }
        return;
      }
    }
  }, [disabled, uploading, files.length, maxFiles, homeworkId]);

  // Глобальный обработчик paste
  useEffect(() => {
    if (!expanded) return;
    
    const handleGlobalPaste = (e) => {
      const activeEl = document.activeElement;
      const isTextInput = activeEl?.tagName === 'INPUT' || 
                          activeEl?.tagName === 'TEXTAREA' ||
                          activeEl?.contentEditable === 'true';
      
      if (isTextInput) return;
      handlePaste(e);
    };

    document.addEventListener('paste', handleGlobalPaste);
    return () => {
      document.removeEventListener('paste', handleGlobalPaste);
    };
  }, [handlePaste, expanded]);

  // Удаление файла
  const handleRemove = (index) => {
    const newFiles = files.filter((_, i) => i !== index);
    onChange(newFiles);
  };

  // Форматирование размера
  const formatSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  // Иконка по типу файла
  const getFileIcon = (mimeType, name) => {
    if (mimeType?.startsWith('image/')) return 'IMG';
    const ext = name?.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf': return 'PDF';
      case 'doc': case 'docx': return 'DOC';
      case 'xls': case 'xlsx': return 'XLS';
      case 'ppt': case 'pptx': return 'PPT';
      default: return 'FILE';
    }
  };

  // Компактный режим: кнопка + счётчик
  if (!expanded && files.length === 0) {
    return (
      <div className="answer-attachment-compact">
        <button
          type="button"
          className="answer-attachment-add-btn"
          onClick={() => setExpanded(true)}
          disabled={disabled}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
          </svg>
          <span>Прикрепить файл</span>
        </button>
      </div>
    );
  }

  return (
    <div className="answer-attachment">
      <div className="answer-attachment-header">
        <span className="answer-attachment-title">
          Прикреплённые файлы ({files.length}/{maxFiles})
        </span>
        {files.length === 0 && (
          <button
            type="button"
            className="answer-attachment-collapse-btn"
            onClick={() => setExpanded(false)}
          >
            Свернуть
          </button>
        )}
      </div>

      {/* Зона загрузки */}
      {files.length < maxFiles && !disabled && (
        <div
          ref={dropZoneRef}
          className={`answer-attachment-dropzone ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            disabled={disabled || uploading}
          />

          {uploading ? (
            <div className="answer-attachment-progress">
              <div className="answer-attachment-progress-bar">
                <div 
                  className="answer-attachment-progress-fill" 
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <span>{uploadProgress}%</span>
            </div>
          ) : (
            <button
              type="button"
              className="answer-attachment-upload-btn"
              onClick={() => fileInputRef.current?.click()}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <span>Загрузить файл или фото</span>
            </button>
          )}
          <p className="answer-attachment-hint">
            Перетащите файл или вставьте изображение (Ctrl+V)
          </p>
        </div>
      )}

      {/* Ошибка */}
      {error && (
        <div className="answer-attachment-error">
          {error}
        </div>
      )}

      {/* Загруженные файлы */}
      {files.length > 0 && (
        <div className="answer-attachment-files">
          {files.map((file, index) => (
            <div key={file.file_id || index} className="answer-attachment-file">
              {file.mime_type?.startsWith('image/') ? (
                <div className="answer-attachment-preview">
                  <img src={file.url} alt={file.name} />
                </div>
              ) : (
                <div className="answer-attachment-file-icon">
                  {getFileIcon(file.mime_type, file.name)}
                </div>
              )}
              <div className="answer-attachment-file-info">
                <a 
                  href={file.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="answer-attachment-file-name"
                >
                  {file.name}
                </a>
                <span className="answer-attachment-file-size">{formatSize(file.size)}</span>
              </div>
              {!disabled && (
                <button
                  type="button"
                  className="answer-attachment-remove-btn"
                  onClick={() => handleRemove(index)}
                  aria-label="Удалить файл"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AnswerAttachment;
