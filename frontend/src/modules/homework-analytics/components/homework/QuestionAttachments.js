import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  getQuestionAttachments,
  uploadQuestionAttachment,
  deleteQuestionAttachment,
  getAttachmentDownloadUrl,
} from '../../services/homeworkService';
import { getAccessToken } from '../../../../apiService';
import './QuestionAttachments.css';

const MAX_FILES = 10;
const MAX_SIZE_MB = 25;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

const ALLOWED_EXTENSIONS = [
  // PDF
  '.pdf',
  // Audio
  '.mp3', '.wav', '.ogg',
  // Video
  '.mp4', '.webm', '.mov',
  // Office
  '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  // Archives
  '.zip', '.rar', '.7z', '.gz',
  // Images
  '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
];

const ACCEPT_STRING = ALLOWED_EXTENSIONS.join(',');

const FILE_ICONS = {
  'application/pdf': '📄',
  'audio/': '🎵',
  'video/': '🎬',
  'image/': '🖼️',
  'application/zip': '📦',
  'application/x-rar': '📦',
  'application/x-7z': '📦',
  'application/gzip': '📦',
  default: '📎',
};

const getFileIcon = (mimeType) => {
  if (!mimeType) return FILE_ICONS.default;
  for (const [key, icon] of Object.entries(FILE_ICONS)) {
    if (key !== 'default' && mimeType.startsWith(key)) return icon;
  }
  return FILE_ICONS.default;
};

const formatSize = (bytes) => {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
};

/**
 * Компонент вложений к вопросу ДЗ (для учителя — конструктор).
 *
 * Props:
 *   questionId — ID вопроса (серверный, после сохранения ДЗ)
 *   readOnly — только чтение (для студента)
 */
const QuestionAttachments = ({ questionId, readOnly = false }) => {
  const [attachments, setAttachments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  // Загрузка списка вложений
  const loadAttachments = useCallback(async () => {
    if (!questionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getQuestionAttachments(questionId);
      setAttachments(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('[QuestionAttachments] load error:', err);
      setError('Не удалось загрузить вложения');
    } finally {
      setLoading(false);
    }
  }, [questionId]);

  useEffect(() => {
    loadAttachments();
  }, [loadAttachments]);

  // Обработчик выбора файлов
  const handleFileSelect = useCallback(
    async (event) => {
      const files = Array.from(event.target.files || []);
      if (files.length === 0) return;

      // Проверка лимита
      const remaining = MAX_FILES - attachments.length;
      if (remaining <= 0) {
        setError(`Достигнут лимит: максимум ${MAX_FILES} файлов на вопрос`);
        return;
      }

      const filesToUpload = files.slice(0, remaining);

      for (const file of filesToUpload) {
        // Проверка размера
        if (file.size > MAX_SIZE_BYTES) {
          setError(`Файл "${file.name}" слишком большой (${formatSize(file.size)}). Максимум: ${MAX_SIZE_MB} МБ`);
          continue;
        }

        setUploading(true);
        setUploadProgress(0);
        setError(null);

        try {
          const newAttachment = await uploadQuestionAttachment(
            questionId,
            file,
            (percent) => setUploadProgress(percent)
          );
          setAttachments((prev) => [...prev, newAttachment]);
        } catch (err) {
          console.error('[QuestionAttachments] upload error:', err);
          const msg =
            err.response?.data?.errors?.[0] ||
            err.response?.data?.error ||
            `Ошибка при загрузке "${file.name}"`;
          setError(msg);
        } finally {
          setUploading(false);
          setUploadProgress(0);
        }
      }

      // Сброс input для возможности повторной загрузки того же файла
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [questionId, attachments.length]
  );

  // Удаление файла
  const handleDelete = useCallback(
    async (attachmentId, fileName) => {
      if (!window.confirm(`Удалить файл "${fileName}"?`)) return;

      try {
        await deleteQuestionAttachment(attachmentId);
        setAttachments((prev) => prev.filter((a) => a.id !== attachmentId));
      } catch (err) {
        console.error('[QuestionAttachments] delete error:', err);
        setError(`Не удалось удалить "${fileName}"`);
      }
    },
    []
  );

  // Скачивание файла
  const handleDownload = useCallback((attachment) => {
    const url = attachment.download_url || getAttachmentDownloadUrl(attachment.id);
    const link = document.createElement('a');
    link.href = url;
    link.download = attachment.original_name;
    // Добавляем токен для авторизации
    const token = getAccessToken();
    if (token) {
      // Используем fetch для авторизованной загрузки
      fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => {
          if (!res.ok) throw new Error('Download failed');
          return res.blob();
        })
        .then((blob) => {
          const objUrl = URL.createObjectURL(blob);
          link.href = objUrl;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(objUrl);
        })
        .catch((err) => {
          console.error('[QuestionAttachments] download error:', err);
        });
    }
  }, []);

  if (!questionId) {
    return (
      <div className="qa-container qa-notice">
        <span className="qa-notice-icon">💡</span>
        <span>Сначала сохраните задание, чтобы прикрепить файлы к вопросам.</span>
      </div>
    );
  }

  return (
    <div className="qa-container">
      <div className="qa-header">
        <span className="qa-header-title">📎 Файлы к вопросу</span>
        <span className="qa-header-count">
          {attachments.length}/{MAX_FILES}
        </span>
      </div>

      {error && (
        <div className="qa-error">
          <span>{error}</span>
          <button type="button" className="qa-error-dismiss" onClick={() => setError(null)}>
            ✕
          </button>
        </div>
      )}

      {loading ? (
        <div className="qa-loading">Загрузка вложений...</div>
      ) : (
        <>
          {attachments.length > 0 && (
            <div className="qa-file-list">
              {attachments.map((attachment) => (
                <div key={attachment.id} className="qa-file-item">
                  <span className="qa-file-icon">{getFileIcon(attachment.mime_type)}</span>
                  <div className="qa-file-info">
                    <span className="qa-file-name">{attachment.original_name}</span>
                    <span className="qa-file-meta">
                      {attachment.size_display || formatSize(attachment.size)}
                    </span>
                  </div>
                  <div className="qa-file-actions">
                    <button
                      type="button"
                      className="qa-btn qa-btn-download"
                      onClick={() => handleDownload(attachment)}
                      title="Скачать"
                    >
                      ⬇️
                    </button>
                    {!readOnly && (
                      <button
                        type="button"
                        className="qa-btn qa-btn-delete"
                        onClick={() => handleDelete(attachment.id, attachment.original_name)}
                        title="Удалить"
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {!readOnly && attachments.length < MAX_FILES && (
            <div className="qa-upload-area">
              {uploading ? (
                <div className="qa-upload-progress">
                  <div className="qa-progress-bar">
                    <div
                      className="qa-progress-fill"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                  <span className="qa-progress-text">Загрузка... {uploadProgress}%</span>
                </div>
              ) : (
                <label className="qa-upload-label">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={ACCEPT_STRING}
                    multiple
                    onChange={handleFileSelect}
                    className="qa-upload-input"
                  />
                  <span className="qa-upload-icon">➕</span>
                  <span className="qa-upload-text">
                    Прикрепить файл
                  </span>
                  <span className="qa-upload-hint">
                    PDF, аудио, видео, документы, архивы, изображения · до {MAX_SIZE_MB} МБ
                  </span>
                </label>
              )}
            </div>
          )}

          {attachments.length === 0 && readOnly && (
            <div className="qa-empty">Нет прикреплённых файлов</div>
          )}
        </>
      )}
    </div>
  );
};

export default QuestionAttachments;
