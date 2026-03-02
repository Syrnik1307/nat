import React, { useState } from 'react';
import './RecordingCard.css';

/* ---- SVG-иконки (inline, без эмодзи) ---- */

const IconPlay = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none">
    <polygon points="5 3 19 12 5 21 5 3" />
  </svg>
);

const IconPlayLarge = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor" stroke="none">
    <polygon points="6 3 20 12 6 21 6 3" />
  </svg>
);

const IconCalendar = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" />
    <line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const IconClock = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

const IconUser = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const IconEye = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const IconFile = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
  </svg>
);

const IconTimer = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

const IconTrash = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
  </svg>
);

const IconLoader = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="rc-spin-icon">
    <line x1="12" y1="2" x2="12" y2="6" />
    <line x1="12" y1="18" x2="12" y2="22" />
    <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
    <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
    <line x1="2" y1="12" x2="6" y2="12" />
    <line x1="18" y1="12" x2="22" y2="12" />
    <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
    <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
  </svg>
);

const IconCheck = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const IconX = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const IconVideo = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="23 7 16 12 23 17 23 7" />
    <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
  </svg>
);

function RecordingCard({ recording, onPlay, onDelete, onRename, showDelete, showEdit }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  const formatTime = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getDaysLeftColor = (daysLeft) => {
    if (daysLeft > 30) return '#22c55e';
    if (daysLeft > 7) return '#f59e0b';
    return '#ef4444';
  };

  const getStatusBadge = () => {
    switch (recording.status) {
      case 'ready':
        return <span className="status-badge ready"><IconCheck /> Готово</span>;
      case 'processing':
        return <span className="status-badge processing"><IconLoader /> Обработка...</span>;
      case 'failed':
        return <span className="status-badge failed"><IconX /> Ошибка</span>;
      default:
        return null;
    }
  };

  const handleStartEdit = () => {
    setEditTitle(recording.title || recording.lesson_info?.subject || 'Урок');
    setIsEditing(true);
  };

  const handleSaveTitle = async () => {
    const newTitle = editTitle.trim();
    if (!newTitle || newTitle === (recording.title || recording.lesson_info?.subject || 'Урок')) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);
    try {
      if (onRename) {
        await onRename(recording.id, newTitle);
      }
      setIsEditing(false);
    } catch (err) {
      console.error('Error renaming recording:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const accessGroups = Array.isArray(recording.access_groups) && recording.access_groups.length > 0
    ? recording.access_groups
    : (recording.lesson_info?.group
        ? [{ id: recording.lesson_info.group_id, name: recording.lesson_info.group }]
        : []);

  return (
    <div className="recording-card" data-tour="rec-card-item">
      {/* Превью */}
      <div className="recording-thumbnail">
        {recording.thumbnail_url ? (
          <img src={recording.thumbnail_url} alt="Preview" />
        ) : (
          <div className="no-thumbnail">
            <IconVideo />
          </div>
        )}
        <div className="play-overlay" onClick={() => onPlay(recording)}>
          <div className="play-button">
            <IconPlayLarge />
          </div>
        </div>
        {recording.duration_display && (
          <div className="duration-badge">
            {recording.duration_display} мин
          </div>
        )}
      </div>

      {/* Информация */}
      <div className="recording-info">
        {/* Название с возможностью редактирования */}
        {isEditing ? (
          <div className="recording-title-edit">
            <input
              type="text"
              className="title-edit-input"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSaveTitle();
                } else if (e.key === 'Escape') {
                  setIsEditing(false);
                }
              }}
              autoFocus
              maxLength={255}
              disabled={isSaving}
            />
            <div className="title-edit-actions">
              <button 
                className="title-edit-save"
                onClick={handleSaveTitle}
                disabled={isSaving || !editTitle.trim()}
                title="Сохранить"
              >
                {isSaving ? '...' : 'OK'}
              </button>
              <button 
                className="title-edit-cancel"
                onClick={() => setIsEditing(false)}
                disabled={isSaving}
                title="Отмена"
              >
                X
              </button>
            </div>
          </div>
        ) : (
          <div className="recording-title-wrapper">
            <div className="recording-title">
              {recording.title || recording.lesson_info?.subject || 'Урок'}
            </div>
            {showEdit && (
              <button 
                className="title-edit-button"
                onClick={handleStartEdit}
                title="Редактировать название"
                data-tour="rec-card-rename"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
            )}
          </div>
        )}

        {/* Группы - показываем в одну строку */}
        {accessGroups.length > 0 && (
          <div className="recording-groups-list">
            {accessGroups.slice(0, 3).map((group) => (
              <span key={group.id} className="group-pill">
                {group.name}
              </span>
            ))}
            {accessGroups.length > 3 && (
              <span className="group-pill more">+{accessGroups.length - 3}</span>
            )}
          </div>
        )}

        <div className="recording-meta">
          {(() => {
            const baseDate = recording.lesson_info?.start_time || recording.created_at;
            const dateLabel = formatDate(baseDate);
            const timeLabel = formatTime(baseDate);
            return (
              <>
                {dateLabel && (
                  <div className="meta-row">
                    <span className="meta-icon"><IconCalendar /></span>
                    <span>{dateLabel}</span>
                  </div>
                )}
                {timeLabel && (
                  <div className="meta-row">
                    <span className="meta-icon"><IconClock /></span>
                    <span>{timeLabel}</span>
                  </div>
                )}
              </>
            );
          })()}
          {recording.lesson_info?.teacher && (
            <div className="meta-row">
              <span className="meta-icon"><IconUser /></span>
              <span>{recording.lesson_info.teacher.name}</span>
            </div>
          )}
        </div>

        {/* Статистика */}
        <div className="recording-stats">
          <div className="stat">
            <span className="stat-icon"><IconEye /></span>
            <span className="stat-value">{recording.views_count || 0}</span>
            <span className="stat-label">просмотров</span>
          </div>
          
          {recording.file_size_mb && (
            <div className="stat">
              <span className="stat-icon"><IconFile /></span>
              <span className="stat-value">{recording.file_size_mb}</span>
              <span className="stat-label">МБ</span>
            </div>
          )}
          
          {recording.available_days_left !== null && (
            <div className="stat">
              <span 
                className="stat-icon"
                style={{ color: getDaysLeftColor(recording.available_days_left) }}
              >
                <IconTimer />
              </span>
              <span className="stat-value">{recording.available_days_left}</span>
              <span className="stat-label">дней</span>
            </div>
          )}
        </div>

        {/* Кнопка воспроизведения */}
        <button 
          className="watch-button"
          onClick={() => onPlay(recording)}
          disabled={recording.status !== 'ready'}
          data-tour="rec-card-play"
        >
          {recording.status === 'ready' ? (
            <>
              <span className="button-icon"><IconPlay /></span>
              Смотреть запись
            </>
          ) : recording.status === 'processing' ? (
            <>
              <span className="button-icon"><IconLoader /></span>
              Обработка...
            </>
          ) : (
            <>
              <span className="button-icon"><IconX /></span>
              Недоступно
            </>
          )}
        </button>

        {/* Кнопка удаления для преподавателей */}
        {showDelete && (
          <button 
            className="delete-button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(recording.id);
            }}
            title="Удалить запись"
            data-tour="rec-card-delete"
          >
            <span className="button-icon"><IconTrash /></span>
            Удалить
          </button>
        )}

      
        {getStatusBadge()}
      </div>
    </div>
  );
}

export default RecordingCard;
