import React, { useState, useRef, useCallback } from 'react';
import './FileDropzone.css';

const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'application/pdf'];
const MAX_SIZE = 5 * 1024 * 1024; // 5MB
const MAX_FILES = 5;

const CloseIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const UploadIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
  </svg>
);

const FileDropzone = ({ files = [], onChange, maxFiles = MAX_FILES, disabled = false }) => {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const validateFile = useCallback((file) => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return 'Недопустимый формат. Разрешены: PNG, JPG, GIF, WebP, PDF';
    }
    if (file.size > MAX_SIZE) {
      return `Файл слишком большой (${(file.size / 1024 / 1024).toFixed(1)} МБ). Максимум 5 МБ`;
    }
    return null;
  }, []);

  const addFiles = useCallback((newFiles) => {
    setError('');
    const remaining = maxFiles - files.length;
    if (remaining <= 0) {
      setError(`Максимум ${maxFiles} файлов`);
      return;
    }

    const toAdd = [];
    for (const file of Array.from(newFiles).slice(0, remaining)) {
      const err = validateFile(file);
      if (err) {
        setError(err);
        continue;
      }
      toAdd.push({
        file,
        id: null,
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
        progress: 0,
        uploading: false,
        error: null,
      });
    }
    if (toAdd.length > 0) {
      onChange([...files, ...toAdd]);
    }
  }, [files, maxFiles, onChange, validateFile]);

  const removeFile = useCallback((index) => {
    const updated = [...files];
    if (updated[index]?.preview) {
      URL.revokeObjectURL(updated[index].preview);
    }
    updated.splice(index, 1);
    onChange(updated);
    setError('');
  }, [files, onChange]);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (!disabled && e.dataTransfer.files?.length) {
      addFiles(e.dataTransfer.files);
    }
  }, [addFiles, disabled]);

  const handleInput = useCallback((e) => {
    if (e.target.files?.length) {
      addFiles(e.target.files);
    }
    e.target.value = '';
  }, [addFiles]);

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
  };

  return (
    <div className="file-dropzone-container">
      <div
        className={`file-dropzone ${dragActive ? 'file-dropzone--active' : ''} ${disabled ? 'file-dropzone--disabled' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && !disabled && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES.join(',')}
          onChange={handleInput}
          style={{ display: 'none' }}
        />
        <UploadIcon />
        <span className="file-dropzone__text">
          Перетащите файлы сюда или нажмите для выбора
        </span>
        <span className="file-dropzone__hint">
          PNG, JPG, GIF, WebP, PDF. До 5 МБ, не более {maxFiles} файлов
        </span>
      </div>

      {error && <div className="file-dropzone__error">{error}</div>}

      {files.length > 0 && (
        <div className="file-dropzone__files">
          {files.map((f, idx) => (
            <div key={idx} className="file-dropzone__file">
              {f.preview ? (
                <img src={f.preview} alt="" className="file-dropzone__thumb" />
              ) : (
                <div className="file-dropzone__thumb file-dropzone__thumb--pdf">PDF</div>
              )}
              <div className="file-dropzone__file-info">
                <span className="file-dropzone__filename">{f.file.name}</span>
                <span className="file-dropzone__filesize">{formatSize(f.file.size)}</span>
                {f.uploading && (
                  <div className="file-dropzone__progress">
                    <div className="file-dropzone__progress-bar" style={{ width: `${f.progress}%` }} />
                  </div>
                )}
                {f.error && <span className="file-dropzone__file-error">{f.error}</span>}
              </div>
              {!f.uploading && (
                <button
                  type="button"
                  className="file-dropzone__remove"
                  onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                  aria-label="Удалить файл"
                >
                  <CloseIcon />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileDropzone;
