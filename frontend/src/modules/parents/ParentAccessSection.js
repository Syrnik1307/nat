/**
 * ParentAccessSection.js
 * Секция "Доступ для родителя" внутри StudentCardModal.
 * Позволяет учителю: создать доступ, скопировать ссылку,
 * настроить видимость, писать комментарии, деактивировать.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../apiService';
import './ParentAccessSection.css';

const ParentAccessSection = ({ studentId, groupId }) => {
  const [loading, setLoading] = useState(true);
  const [accessData, setAccessData] = useState(null);
  const [myGrant, setMyGrant] = useState(null);
  const [hasAccess, setHasAccess] = useState(false);

  // Создание доступа
  const [creating, setCreating] = useState(false);
  const [subjectLabel, setSubjectLabel] = useState('');
  const [parentName, setParentName] = useState('');

  // Комментарии
  const [commentText, setCommentText] = useState('');
  const [sendingComment, setSendingComment] = useState(false);

  // Настройки видимости
  const [showSettings, setShowSettings] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);

  // Копирование
  const [copied, setCopied] = useState(false);

  const loadAccess = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await apiClient.get(
        `/parents/access/student/${studentId}/group/${groupId}/`
      );
      if (resp.data.exists === false) {
        setHasAccess(false);
        setAccessData(null);
        setMyGrant(null);
      } else {
        setHasAccess(true);
        setAccessData(resp.data);
        setMyGrant(resp.data.my_grant || null);
      }
    } catch {
      setHasAccess(false);
    } finally {
      setLoading(false);
    }
  }, [studentId, groupId]);

  useEffect(() => {
    if (studentId && groupId) {
      loadAccess();
    }
  }, [studentId, groupId, loadAccess]);

  const handleCreate = async () => {
    if (!subjectLabel.trim()) return;
    try {
      setCreating(true);
      await apiClient.post('/parents/access/', {
        student_id: studentId,
        group_id: groupId,
        subject_label: subjectLabel.trim(),
        parent_name: parentName.trim(),
      });
      await loadAccess();
      setSubjectLabel('');
      setParentName('');
    } catch (err) {
      console.error('Ошибка создания доступа:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleCopyLink = async () => {
    if (!accessData?.link) return;
    try {
      await navigator.clipboard.writeText(accessData.link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
      const input = document.createElement('input');
      input.value = accessData.link;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleToggleVisibility = async (field) => {
    if (!myGrant) return;
    try {
      setSavingSettings(true);
      const newValue = !myGrant[field];
      const resp = await apiClient.patch(`/parents/grants/${myGrant.id}/`, {
        [field]: newValue,
      });
      setMyGrant(resp.data);
    } catch (err) {
      console.error('Ошибка обновления настроек:', err);
    } finally {
      setSavingSettings(false);
    }
  };

  const handleSendComment = async () => {
    if (!commentText.trim() || !myGrant) return;
    try {
      setSendingComment(true);
      await apiClient.post(`/parents/grants/${myGrant.id}/comments/`, {
        text: commentText.trim(),
      });
      setCommentText('');
      await loadAccess();
    } catch (err) {
      console.error('Ошибка отправки комментария:', err);
    } finally {
      setSendingComment(false);
    }
  };

  const handleDeleteComment = async (commentId) => {
    if (!myGrant) return;
    try {
      await apiClient.delete(
        `/parents/grants/${myGrant.id}/comments/${commentId}/`
      );
      await loadAccess();
    } catch (err) {
      console.error('Ошибка удаления комментария:', err);
    }
  };

  const handleDeactivate = async () => {
    if (!myGrant) return;
    try {
      await apiClient.delete(`/parents/grants/${myGrant.id}/`);
      setMyGrant(null);
      await loadAccess();
    } catch (err) {
      console.error('Ошибка деактивации:', err);
    }
  };

  const handleUpdateLabel = async (newLabel) => {
    if (!myGrant || !newLabel.trim()) return;
    try {
      const resp = await apiClient.patch(`/parents/grants/${myGrant.id}/`, {
        subject_label: newLabel.trim(),
      });
      setMyGrant(resp.data);
    } catch (err) {
      console.error('Ошибка обновления:', err);
    }
  };

  if (loading) {
    return (
      <div className="parent-access-section">
        <h3 className="section-title">Доступ для родителя</h3>
        <div className="pa-loading">Загрузка...</div>
      </div>
    );
  }

  // --- Нет доступа — форма создания ---
  if (!hasAccess || !myGrant || !myGrant.is_active) {
    return (
      <div className="parent-access-section">
        <h3 className="section-title">Доступ для родителя</h3>
        <div className="pa-create-form">
          <p className="pa-description">
            Создайте ссылку для родителя, чтобы он мог видеть прогресс ученика
          </p>
          <div className="pa-field">
            <label>Название предмета</label>
            <input
              type="text"
              value={subjectLabel}
              onChange={(e) => setSubjectLabel(e.target.value)}
              placeholder="Математика, Английский..."
              maxLength={200}
            />
          </div>
          <div className="pa-field">
            <label>Имя родителя (необязательно)</label>
            <input
              type="text"
              value={parentName}
              onChange={(e) => setParentName(e.target.value)}
              placeholder="Иванова Мария Петровна"
              maxLength={200}
            />
          </div>
          <button
            className="pa-btn pa-btn-create"
            onClick={handleCreate}
            disabled={creating || !subjectLabel.trim()}
          >
            {creating ? 'Создание...' : 'Создать доступ'}
          </button>
        </div>
      </div>
    );
  }

  // --- Доступ есть — управление ---
  const visibilityFields = [
    { key: 'show_attendance', label: 'Посещаемость' },
    { key: 'show_homework', label: 'Домашние задания' },
    { key: 'show_grades', label: 'Оценки' },
    { key: 'show_knowledge_map', label: 'Карта знаний' },
    { key: 'show_finance', label: 'Финансы' },
  ];

  const comments = myGrant.comments || [];

  return (
    <div className="parent-access-section">
      <h3 className="section-title">Доступ для родителя</h3>

      {/* Ссылка */}
      <div className="pa-link-row">
        <div className="pa-link-value">{accessData.link}</div>
        <button className="pa-btn pa-btn-copy" onClick={handleCopyLink}>
          {copied ? 'Скопировано' : 'Копировать'}
        </button>
      </div>

      {/* Мета-информация */}
      <div className="pa-meta">
        <span>Предмет: <strong>{myGrant.subject_label}</strong></span>
        {accessData.view_count > 0 && (
          <span>Просмотров: {accessData.view_count}</span>
        )}
        {accessData.last_viewed_at && (
          <span>
            Последний визит:{' '}
            {new Date(accessData.last_viewed_at).toLocaleDateString('ru-RU')}
          </span>
        )}
        {accessData.telegram_connected && (
          <span className="pa-tg-badge">Telegram подключён</span>
        )}
      </div>

      {/* Настройки видимости */}
      <div className="pa-settings-toggle">
        <button
          className="pa-btn pa-btn-settings"
          onClick={() => setShowSettings(!showSettings)}
        >
          {showSettings ? 'Скрыть настройки' : 'Настройки видимости'}
        </button>
      </div>

      {showSettings && (
        <div className="pa-visibility-grid">
          {visibilityFields.map(({ key, label }) => (
            <label key={key} className="pa-vis-item">
              <input
                type="checkbox"
                checked={!!myGrant[key]}
                onChange={() => handleToggleVisibility(key)}
                disabled={savingSettings}
              />
              <span>{label}</span>
            </label>
          ))}
          <EditableLabel
            value={myGrant.subject_label}
            onSave={handleUpdateLabel}
          />
        </div>
      )}

      {/* Комментарии для родителя */}
      <div className="pa-comments">
        <h4>Комментарии для родителя</h4>
        <div className="pa-comment-input-row">
          <input
            type="text"
            className="pa-comment-input"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder="Написать комментарий..."
            maxLength={2000}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendComment();
              }
            }}
          />
          <button
            className="pa-btn pa-btn-send"
            onClick={handleSendComment}
            disabled={sendingComment || !commentText.trim()}
          >
            {sendingComment ? '...' : 'Отправить'}
          </button>
        </div>
        {comments.length > 0 ? (
          <ul className="pa-comments-list">
            {comments.map((c) => (
              <li key={c.id} className="pa-comment-item">
                <div className="pa-comment-text">{c.text}</div>
                <div className="pa-comment-footer">
                  <span className="pa-comment-date">
                    {new Date(c.created_at).toLocaleDateString('ru-RU')}
                  </span>
                  <button
                    className="pa-btn-delete-comment"
                    onClick={() => handleDeleteComment(c.id)}
                    title="Удалить"
                  >
                    ×
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="pa-no-comments">Нет комментариев</p>
        )}
      </div>

      {/* Деактивация */}
      <div className="pa-deactivate">
        <button
          className="pa-btn pa-btn-danger"
          onClick={handleDeactivate}
        >
          Отключить доступ
        </button>
      </div>
    </div>
  );
};

// --- Вспомогательный компонент для редактирования subject_label ---
const EditableLabel = ({ value, onSave }) => {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(value);

  if (!editing) {
    return (
      <div className="pa-editable-label">
        <span>Название: {value}</span>
        <button className="pa-btn-edit" onClick={() => setEditing(true)}>
          Изменить
        </button>
      </div>
    );
  }

  return (
    <div className="pa-editable-label pa-editable-editing">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={200}
        autoFocus
      />
      <button
        className="pa-btn-edit"
        onClick={() => {
          onSave(text);
          setEditing(false);
        }}
        disabled={!text.trim()}
      >
        OK
      </button>
      <button
        className="pa-btn-edit"
        onClick={() => {
          setText(value);
          setEditing(false);
        }}
      >
        Отмена
      </button>
    </div>
  );
};

export default ParentAccessSection;
