import React, { useEffect } from 'react';
import './Toast.css';

/**
 * Toast notification component
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether the toast is visible
 * @param {function} props.onClose - Close callback
 * @param {string} props.type - 'success' | 'error' | 'warning' | 'info' | 'progress'
 * @param {string} props.title - Toast title
 * @param {string} props.message - Toast message
 * @param {number} props.progress - Progress percentage (0-100) for progress type
 * @param {number} props.duration - Auto-close duration in ms (0 = no auto-close)
 */
const Toast = ({ 
  isOpen, 
  onClose, 
  type = 'info', 
  title, 
  message, 
  progress = 0,
  duration = 5000 
}) => {
  useEffect(() => {
    if (isOpen && duration > 0 && type !== 'progress') {
      const timer = setTimeout(() => {
        onClose();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [isOpen, duration, onClose, type]);

  if (!isOpen) return null;

  const icons = {
    success: '✓',
    error: '✕',
    warning: '!',
    info: 'i',
    progress: '↑'
  };

  return (
    <div className={`toast toast-${type}`}>
      <div className="toast-icon">
        {icons[type]}
      </div>
      <div className="toast-content">
        {title && <div className="toast-title">{title}</div>}
        {message && <div className="toast-message">{message}</div>}
        {type === 'progress' && (
          <div className="toast-progress-bar">
            <div 
              className="toast-progress-fill" 
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>
      {type !== 'progress' && (
        <button className="toast-close" onClick={onClose}>
          ✕
        </button>
      )}
    </div>
  );
};

/**
 * ToastContainer - holds multiple toasts
 */
export const ToastContainer = ({ toasts, onRemove }) => {
  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          isOpen={true}
          onClose={() => onRemove(toast.id)}
          {...toast}
        />
      ))}
    </div>
  );
};

export default Toast;
