import React from 'react';

/**
 * Компонент уведомления в фирменном стиле
 * @param {boolean} isOpen - открыто ли уведомление
 * @param {function} onClose - функция закрытия
 * @param {string} type - 'success' | 'error' | 'info' | 'warning'
 * @param {string} title - заголовок
 * @param {string} message - текст сообщения
 */
const Notification = ({ 
  isOpen, 
  onClose, 
  type = 'info',
  title,
  message,
}) => {
  if (!isOpen) return null;

  const typeConfig = {
    success: {
      icon: '✅',
      gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
      color: '#10b981',
    },
    error: {
      icon: '❌',
      gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
      color: '#ef4444',
    },
    warning: {
      icon: '⚠️',
      gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
      color: '#f59e0b',
    },
    info: {
      icon: 'ℹ️',
      gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
      color: '#3b82f6',
    },
  };

  const config = typeConfig[type];

  const backdropStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    backdropFilter: 'blur(8px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10000,
    animation: 'fadeIn 0.2s ease-out',
  };

  const modalStyle = {
    background: 'white',
    borderRadius: 'var(--radius-xl)',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    maxWidth: '500px',
    width: '90%',
    overflow: 'hidden',
    animation: 'slideIn 0.3s ease-out',
  };

  const headerStyle = {
    background: config.gradient,
    padding: 'var(--space-xl)',
    textAlign: 'center',
    color: 'white',
  };

  const iconStyle = {
    fontSize: '4rem',
    marginBottom: 'var(--space-md)',
  };

  const titleStyle = {
    fontSize: '1.5rem',
    fontWeight: 700,
    margin: 0,
  };

  const bodyStyle = {
    padding: 'var(--space-xl)',
    textAlign: 'center',
  };

  const messageStyle = {
    fontSize: '1rem',
    color: 'var(--gray-700)',
    lineHeight: 1.6,
    whiteSpace: 'pre-line',
    marginBottom: 'var(--space-xl)',
  };

  const buttonStyle = {
    background: config.gradient,
    color: 'white',
    border: 'none',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-md) var(--space-xl)',
    fontSize: '1rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all var(--transition-base)',
    boxShadow: `0 4px 14px 0 ${config.color}66`,
  };

  return (
    <>
      <style>
        {`
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          @keyframes slideIn {
            from {
              opacity: 0;
              transform: translateY(-20px) scale(0.95);
            }
            to {
              opacity: 1;
              transform: translateY(0) scale(1);
            }
          }
        `}
      </style>
      <div style={backdropStyle} onClick={onClose}>
        <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
          <div style={headerStyle}>
            <div style={iconStyle}>{config.icon}</div>
            {title && <h2 style={titleStyle}>{title}</h2>}
          </div>
          <div style={bodyStyle}>
            {message && <p style={messageStyle}>{message}</p>}
            <button 
              style={buttonStyle}
              onClick={onClose}
              onMouseEnter={(e) => {
                e.target.style.transform = 'scale(1.05)';
                e.target.style.boxShadow = `0 6px 20px 0 ${config.color}88`;
              }}
              onMouseLeave={(e) => {
                e.target.style.transform = 'scale(1)';
                e.target.style.boxShadow = `0 4px 14px 0 ${config.color}66`;
              }}
            >
              OK
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default Notification;
