import React, { useRef, useState } from 'react';
import StartLessonButton from '../modules/core/zoom/StartLessonButton';
import { ConfirmModal } from '../shared/components';
import './SwipeableLesson.css';

const SwipeableLesson = ({ lesson, onDelete, formatTime, getLessonDuration }) => {
  const [translateX, setTranslateX] = useState(0);
  const [showActions, setShowActions] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [confirmState, setConfirmState] = useState({ open: false, type: null });
  const [deleteMessage, setDeleteMessage] = useState('');

  const startX = useRef(0);
  const isDragging = useRef(false);
  const pendingDeleteType = useRef(null);

  const handleStart = (clientX) => {
    startX.current = clientX;
    isDragging.current = true;
  };

  const handleMove = (clientX) => {
    if (!isDragging.current) return;
    const diff = clientX - startX.current;
    if (diff < 0) {
      const clamped = Math.max(diff, -200);
      setTranslateX(clamped);
    }
  };

  const resetPosition = () => {
    setTranslateX(0);
    setShowActions(false);
    isDragging.current = false;
  };

  const handleEnd = () => {
    if (!isDragging.current) return;
    isDragging.current = false;
    if (translateX < -110) {
      setTranslateX(-190);
      setShowActions(true);
    } else {
      resetPosition();
    }
  };

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
        resetPosition();
        closeConfirm();
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
      <div
        className="swipeable-lesson-container"
        onTouchStart={(e) => handleStart(e.touches[0].clientX)}
        onTouchMove={(e) => handleMove(e.touches[0].clientX)}
        onTouchEnd={handleEnd}
        onTouchCancel={handleEnd}
        onMouseDown={(e) => handleStart(e.clientX)}
        onMouseMove={(e) => isDragging.current && handleMove(e.clientX)}
        onMouseUp={handleEnd}
        onMouseLeave={() => isDragging.current && handleEnd()}
      >
        <div className={`swipe-actions ${showActions ? 'visible' : ''}`}>
          <button
            type="button"
            className="action-btn subtle"
            onClick={() => openConfirm('single')}
            disabled={deleting}
          >
            Удалить
          </button>
          <button
            type="button"
            className="action-btn solid"
            onClick={() => openConfirm('recurring')}
            disabled={deleting}
          >
            Удалить серию
          </button>
        </div>

        <article
          className="lesson-card swipeable-card"
          style={ {
            transform: `translateX(${translateX}px)`,
            transition: isDragging.current ? 'none' : 'transform 0.25s ease',
            cursor: isDragging.current ? 'grabbing' : 'grab',
          } }
        >
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
          </div>
        </article>
      </div>

      {errorMessage && (
        <div className="swipeable-lesson-message error" role="alert">
          {errorMessage}
        </div>
      )}

      {deleteMessage && (
        <div className="swipeable-lesson-message success">
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
