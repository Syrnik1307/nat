import React, { useEffect } from 'react';

/**
 * Переиспользуемый компонент модального окна
 * @param {boolean} isOpen - открыто ли модальное окно
 * @param {function} onClose - функция закрытия модального окна
 * @param {string} title - заголовок модального окна
 * @param {string} size - 'small' | 'medium' | 'large' | 'fullscreen'
 * @param {boolean} closeOnBackdrop - закрывать ли при клике на фон
 * @param {React.ReactNode} children - содержимое модального окна
 * @param {React.ReactNode} footer - футер модального окна
 */
const Modal = ({ 
  isOpen, 
  onClose, 
  title, 
  size = 'medium',
  closeOnBackdrop = true,
  children,
  footer,
}) => {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizes = {
    small: '400px',
    medium: '600px',
    large: '900px',
    fullscreen: '95vw',
  };

  const handleBackdropClick = (e) => {
    if (closeOnBackdrop && e.target === e.currentTarget) {
      onClose();
    }
  };

  const backdropStyles = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '1rem',
    animation: 'fadeIn 0.2s ease',
  };

  const modalStyles = {
    backgroundColor: 'white',
    borderRadius: '12px',
    maxWidth: sizes[size],
    width: '100%',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    animation: 'slideUp 0.3s ease',
  };

  const headerStyles = {
    padding: '1.5rem',
    borderBottom: '1px solid #e5e7eb',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  };

  const titleStyles = {
    fontSize: '1.25rem',
    fontWeight: '600',
    color: '#111827',
    margin: 0,
  };

  const closeButtonStyles = {
    background: 'none',
    border: 'none',
    fontSize: '1.5rem',
    cursor: 'pointer',
    color: '#6b7280',
    padding: '0.25rem',
    lineHeight: 1,
    transition: 'color 0.2s ease',
  };

  const bodyStyles = {
    padding: '1.5rem',
    overflowY: 'auto',
    flex: 1,
  };

  const footerStyles = {
    padding: '1rem 1.5rem',
    borderTop: '1px solid #e5e7eb',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: '0.75rem',
  };

  return (
    <>
      <style>
        {`
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          @keyframes slideUp {
            from { 
              transform: translateY(20px);
              opacity: 0;
            }
            to { 
              transform: translateY(0);
              opacity: 1;
            }
          }
        `}
      </style>
      <div style={backdropStyles} onClick={handleBackdropClick}>
        <div style={modalStyles}>
          {title && (
            <div style={headerStyles}>
              <h3 style={titleStyles}>{title}</h3>
              <button
                style={closeButtonStyles}
                onClick={onClose}
                onMouseEnter={(e) => e.target.style.color = '#111827'}
                onMouseLeave={(e) => e.target.style.color = '#6b7280'}
              >
                ×
              </button>
            </div>
          )}
          <div style={bodyStyles}>
            {children}
          </div>
          {footer && (
            <div style={footerStyles}>
              {footer}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default Modal;
