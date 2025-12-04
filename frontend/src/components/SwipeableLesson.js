import React, { useState, useRef } from 'react';
import StartLessonButton from '../modules/core/zoom/StartLessonButton';
import './SwipeableLesson.css';

/**
 * Карточка урока с поддержкой swipe-to-delete
 */
const SwipeableLesson = ({ lesson, onDelete, formatTime, getLessonDuration }) => {
  const [translateX, setTranslateX] = useState(0);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteType, setDeleteType] = useState('single'); // 'single' или 'recurring'
  const [deleting, setDeleting] = useState(false);
  
  const touchStartX = useRef(0);
  const touchCurrentX = useRef(0);
  const isDragging = useRef(false);

  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
    isDragging.current = true;
  };

  const handleTouchMove = (e) => {
    if (!isDragging.current) return;
    
    touchCurrentX.current = e.touches[0].clientX;
    const diff = touchCurrentX.current - touchStartX.current;
    
    // Только свайп влево (diff < 0)
    if (diff < 0 && diff > -120) {
      setTranslateX(diff);
    }
  };

  const handleTouchEnd = () => {
    isDragging.current = false;
    
    // Если свайпнули больше 60px - показываем кнопку удаления
    if (translateX < -60) {
      setTranslateX(-100);
    } else {
      setTranslateX(0);
    }
  };

  const handleDeleteClick = () => {
    setShowDeleteModal(true);
    setTranslateX(0); // Возвращаем карточку на место
  };

  const handleConfirmDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(lesson.id, deleteType);
      setShowDeleteModal(false);
    } catch (error) {
      console.error('Ошибка удаления:', error);
      alert('Не удалось удалить урок');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <div 
        className="swipeable-lesson-container"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Фон с кнопкой удаления */}
        <div className="swipe-background">
          <button 
            className="delete-trigger"
            onClick={handleDeleteClick}
            aria-label="Удалить урок"
          >
            🗑️
          </button>
        </div>

        {/* Карточка урока */}
        <div 
          className="lesson-card"
          style={{
            transform: `translateX(${translateX}px)`,
            transition: isDragging.current ? 'none' : 'transform 0.3s ease',
          }}
        >
          <div className="lesson-time">
            <span className="time">{formatTime(lesson.start_time)}</span>
            <span className="duration">
              {getLessonDuration(lesson)} мин
            </span>
          </div>
          <div className="lesson-info">
            <h3 className="lesson-title">{lesson.title}</h3>
            <div className="lesson-meta">
              <span className="group">
                👥 {lesson.group_name || 'Группа'}
              </span>
              {lesson.zoom_link && (
                <a 
                  href={lesson.zoom_link} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="zoom-link"
                >
                  🎥 Zoom
                </a>
              )}
            </div>
          </div>
          <div className="lesson-actions">
            <StartLessonButton 
              lessonId={lesson.id}
              lesson={lesson}
              groupName={lesson.group_name || 'Группа'}
              onSuccess={() => {
                console.log('Занятие успешно начато!');
              }}
            />
          </div>
        </div>
      </div>

      {/* Модальное окно подтверждения удаления */}
      {showDeleteModal && (
        <div className="delete-modal-overlay" onClick={() => !deleting && setShowDeleteModal(false)}>
          <div className="delete-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Удалить занятие?</h3>
            <p className="lesson-title-display">{lesson.title}</p>
            
            <div className="delete-options">
              <label className="delete-option">
                <input
                  type="radio"
                  name="deleteType"
                  value="single"
                  checked={deleteType === 'single'}
                  onChange={(e) => setDeleteType(e.target.value)}
                  disabled={deleting}
                />
                <div>
                  <strong>Только это занятие</strong>
                  <p>Удалить урок от {new Date(lesson.start_time).toLocaleDateString('ru-RU')}</p>
                </div>
              </label>

              <label className="delete-option">
                <input
                  type="radio"
                  name="deleteType"
                  value="recurring"
                  checked={deleteType === 'recurring'}
                  onChange={(e) => setDeleteType(e.target.value)}
                  disabled={deleting}
                />
                <div>
                  <strong>Все похожие занятия</strong>
                  <p>Удалить все уроки "{lesson.title}" в группе {lesson.group_name}</p>
                </div>
              </label>
            </div>

            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => setShowDeleteModal(false)}
                disabled={deleting}
              >
                Отмена
              </button>
              <button
                className="btn-delete"
                onClick={handleConfirmDelete}
                disabled={deleting}
              >
                {deleting ? 'Удаление...' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SwipeableLesson;
