import React, { useRef, useState } from 'react';
import StartLessonButton from '../modules/core/zoom/StartLessonButton';
import { ConfirmModal } from '../shared/components';
import './SwipeableLesson.css';

const SwipeableLesson = ({ lesson, onDelete, formatTime, getLessonDuration }) => {
  const [showDeleteMenu, setShowDeleteMenu] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [deleteMessage, setDeleteMessage] = useState('');
  const [confirmState, setConfirmState] = useState({ open: false, type: null });

  const pendingDeleteType = useRef(null);

  const openConfirm = (type) => {
    pendingDeleteType.current = type;
    setConfirmState({ open: true, type });
  };

  const closeConfirm = () => {
    setConfirmState({ open: false, type: null });
    pendingDeleteType.current = null;
  };

  const handleConfirmDelete = async () => {
    const deleteType = pendingDeleteType.current;
    if (!deleteType || deleting) {
      return;
    }

    setDeleting(true);
    setErrorMessage('');
    setDeleteMessage('');

    try {
      await onDelete(lesson.id, deleteType);
      setDeleteMessage(deleteType === 'recurring' ? '✓ Серия удалена' : '✓ Урок удалён');
      setTimeout(() => {
        closeConfirm();
        setShowDeleteMenu(false);
        setDeleteMessage('');
      }, 800);
    } catch (error) {
      const detail = error.response?.data?.detail || error.message || 'Не удалось удалить урок';
      setErrorMessage(detail);
    } finally {
      setDeleting(false);
      pendingDeleteType.current = null;
    }
  };

  const confirmMessage = confirmState.type === 'recurring'
    ? `Удалить все занятия "${lesson.title}" в группе "${lesson.group_name || 'группа'}"?`
    : `Удалить занятие "${lesson.title}"?`;

  return (
    <div className="swipeable-lesson-wrapper">
      <div className="lesson-card">
        <div className="lesson-time">
          <span className="time">{formatTime(lesson.start_time)}</span>
          <span className="duration">↔ {getLessonDuration(lesson)} мин</span>
        </div>

        <div className="lesson-info">
          <div className="lesson-title-row">
            <h3 className="lesson-title">{lesson.title}</h3>
            {lesson.topics && <span className="lesson-topic">{lesson.topics}</span>}
          </div>
          <div className="lesson-meta">
            <span className="meta-pill">{lesson.group_name || 'Группа'}</span>
            {lesson.location && <span className="meta-text">{lesson.location}</span>}
            {lesson.zoom_start_url && (
              <a
                href={lesson.zoom_start_url}
                target="_blank"
                rel="noopener noreferrer"
                className="meta-link"
              >
                Zoom
              </a>
            )}
          </div>
        </div>

        <div className="lesson-actions">
          <StartLessonButton
            lessonId={lesson.id}
            lesson={lesson}
            groupName={lesson.group_name || 'Группа'}
            onSuccess={() => setErrorMessage('')}
          />
          
          <div className="delete-menu-container">
            <button
              type="button"
              className="delete-btn"
              onClick={() => setShowDeleteMenu(!showDeleteMenu)}
              title="Удалить урок"
            >
              ⚙️
            </button>
            
            {showDeleteMenu && (
              <>
                <div
                  className="delete-menu-overlay"
                  onClick={() => setShowDeleteMenu(false)}
                />
                <div className="delete-menu">
                  <button
                    type="button"
                    className="delete-menu-item single"
                    onClick={() => {
                      openConfirm('single');
                      setShowDeleteMenu(false);
                    }}
                    disabled={deleting}
                  >
                    Удалить урок
                  </button>
                  <button
                    type="button"
                    className="delete-menu-item recurring"
                    onClick={() => {
                      openConfirm('recurring');
                      setShowDeleteMenu(false);
                    }}
                    disabled={deleting}
                  >
                    Удалить серию
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="lesson-message error" role="alert">
          {errorMessage}
        </div>
      )}

      {deleteMessage && (
        <div className="lesson-message success">
          {deleteMessage}
        </div>
      )}

      <ConfirmModal
        isOpen={confirmState.open}
        onClose={closeConfirm}
        onConfirm={handleConfirmDelete}
        title="Удаление урока"
        message={confirmMessage}
        confirmText={confirmState.type === 'recurring' ? 'Удалить все' : 'Удалить'}
        cancelText="Отмена"
        variant="danger"
      />
    </div>
  );
};

export default SwipeableLesson;
