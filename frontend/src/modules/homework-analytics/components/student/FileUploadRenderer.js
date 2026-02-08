import React, { useState, useRef, useEffect, useCallback } from 'react';
import { uploadStudentAnswerFile } from '../../../../apiService';
import './FileUploadRenderer.css';

/**
 * Компонент для загрузки файлов/фото учеником в качестве ответа.
 * Поддерживает:
 * - Выбор файла через кнопку
 * - Drag & Drop
 * - Вставку из буфера обмена (Ctrl+V)
 */
const FileUploadRenderer = ({ question, answer, onChange, disabled = false, homeworkId = null }) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);

  const config = question.config || {};
  const allowedTypes = config.allowedTypes || ['image', 'document'];
  const maxFiles = config.maxFiles || 1;
  const maxSizeMB = config.maxSizeMB || 10;

  // Текущие загруженные файлы (массив URL/объектов)
  const files = Array.isArray(answer) ? answer : (answer ? [answer] : []);

  // Определяем допустимые MIME типы
  const getAcceptString = () => {
    const types = [];
    if (allowedTypes.includes('image') || allowedTypes.includes('any')) {
      types.push('image/*');
    }
    if (allowedTypes.includes('document') || allowedTypes.includes('any')) {
      types.push('.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip,.rar,.7z');
    }
    if (allowedTypes.includes('any')) {
      types.push('*/*');
    }
    return types.join(',');
  };

  // Валидация файла
  const validateFile = (file) => {
    // Проверка размера
    if (file.size > maxSizeMB * 1024 * 1024) {
      return `Файл слишком большой. Максимум: ${maxSizeMB} MB`;
    }

    // Проверка типа
    const isImage = file.type.startsWith('image/');
    const isDocument = !isImage;

    if (!allowedTypes.includes('any')) {
      if (isImage && !allowedTypes.includes('image')) {
        return 'Изображения не разрешены для этого вопроса';
      }
      if (isDocument && !allowedTypes.includes('document')) {
        return 'Документы не разрешены для этого вопроса';
      }
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

    // Проверка лимита файлов
    if (files.length >= maxFiles) {
      setError(`Можно загрузить максимум ${maxFiles} файл(ов)`);
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

        if (maxFiles === 1) {
          onChange(newFile);
        } else {
          onChange([...files, newFile]);
        }
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
    // Сбрасываем input для повторного выбора того же файла
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
  }, [disabled, uploading, files.length, maxFiles]);

  // Подписка на события вставки
  useEffect(() => {
    const dropZone = dropZoneRef.current;
    if (!dropZone) return;

    // Слушаем paste на уровне dropzone (когда он в фокусе)
    dropZone.addEventListener('paste', handlePaste);

    return () => {
      dropZone.removeEventListener('paste', handlePaste);
    };
  }, [handlePaste]);

  // Глобальный обработчик paste (когда dropzone видим)
  useEffect(() => {
    const handleGlobalPaste = (e) => {
      // Проверяем что фокус не в текстовом поле
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
  }, [handlePaste]);

  // Удаление файла
  const handleRemove = (index) => {
    if (maxFiles === 1) {
      onChange(null);
    } else {
      const newFiles = files.filter((_, i) => i !== index);
      onChange(newFiles.length > 0 ? newFiles : null);
    }
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
      case 'csv': return 'CSV';
      case 'txt': return 'TXT';
      case 'zip': case 'rar': case '7z': return 'ZIP';
      default: return 'FILE';
    }
  };

  return (
    <div className="file-upload-renderer">
      {/* Инструкции от учителя */}
      {config.instructions && (
        <p className="file-upload-instructions">{config.instructions}</p>
      )}

      {/* Зона загрузки */}
      {files.length < maxFiles && !disabled && (
        <div
          ref={dropZoneRef}
          className={`file-upload-dropzone ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          tabIndex={0}
          role="button"
          aria-label="Зона загрузки файла"
          data-tour="q-file-dropzone"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={getAcceptString()}
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            disabled={disabled || uploading}
          />

          {uploading ? (
            <div className="file-upload-progress">
              <div className="file-upload-progress-bar">
                <div 
                  className="file-upload-progress-fill" 
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <span className="file-upload-progress-text">{uploadProgress}%</span>
            </div>
          ) : (
            <>
              <div className="file-upload-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <p className="file-upload-text">
                Перетащите файл сюда или{' '}
                <button
                  type="button"
                  className="file-upload-browse-btn"
                  onClick={() => fileInputRef.current?.click()}
                >
                  выберите
                </button>
              </p>
              <p className="file-upload-hint">
                Ctrl+V для вставки изображения из буфера
              </p>
              <p className="file-upload-limits">
                Макс. размер: {maxSizeMB} MB
                {allowedTypes.includes('image') && !allowedTypes.includes('document') && ' (только изображения)'}
                {allowedTypes.includes('document') && !allowedTypes.includes('image') && ' (только документы)'}
              </p>
            </>
          )}
        </div>
      )}

      {/* Ошибка */}
      {error && (
        <div className="file-upload-error">
          {error}
        </div>
      )}

      {/* Загруженные файлы */}
      {files.length > 0 && (
        <div className="file-upload-files" data-tour="q-file-list">
          {files.map((file, index) => (
            <div key={file.file_id || index} className="file-upload-file">
              {file.mime_type?.startsWith('image/') ? (
                <div className="file-upload-preview">
                  <img src={file.url} alt={file.name} />
                </div>
              ) : (
                <div className="file-upload-file-icon">
                  {getFileIcon(file.mime_type, file.name)}
                </div>
              )}
              <div className="file-upload-file-info">
                <span className="file-upload-file-name">{file.name}</span>
                <span className="file-upload-file-size">{formatSize(file.size)}</span>
              </div>
              {!disabled && (
                <button
                  type="button"
                  className="file-upload-remove-btn"
                  onClick={() => handleRemove(index)}
                  aria-label="Удалить файл"
                  data-tour="q-file-remove"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Disabled state */}
      {disabled && files.length === 0 && (
        <div className="file-upload-disabled">
          Файл не загружен
        </div>
      )}
    </div>
  );
};

export default FileUploadRenderer;
