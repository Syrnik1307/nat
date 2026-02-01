import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';

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
    backgroundColor: 'rgba(15, 23, 42, 0.5)',
    backdropFilter: 'blur(8px)',
    WebkitBackdropFilter: 'blur(8px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999, // Fixed high z-index for iOS compatibility
    padding: 'var(--space-lg, 16px)',
    animation: 'backdropFadeIn var(--duration-slow, 400ms) var(--ease-smooth, cubic-bezier(0.4, 0, 0.2, 1))',
    // iOS Safari fixes
    WebkitOverflowScrolling: 'touch',
    overscrollBehavior: 'contain',
  };

  const modalStyles = {
    backgroundColor: 'var(--bg-primary, #ffffff)',
    borderRadius: 'var(--radius-xl, 16px)',
    maxWidth: sizes[size],
    width: '100%',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 25px 50px -12px rgba(79, 70, 229, 0.25), 0 10px 25px -5px rgba(0, 0, 0, 0.1)',
    animation: 'smoothScaleIn var(--duration-slow, 400ms) var(--ease-spring, cubic-bezier(0.34, 1.56, 0.64, 1))',
    // iOS Safari fixes
    WebkitTransform: 'translateZ(0)',
    transform: 'translateZ(0)',
  };

  const headerStyles = {
    padding: 'var(--space-xl)',
    borderBottom: '1px solid var(--border-color)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  };

  const titleStyles = {
    fontSize: 'var(--text-xl)',
    fontWeight: 'var(--font-semibold)',
    color: 'var(--text-primary)',
    margin: 0,
  };

  const closeButtonStyles = {
    background: 'none',
    border: 'none',
    fontSize: 'var(--text-2xl)',
    cursor: 'pointer',
    color: 'var(--text-secondary)',
    padding: 'var(--space-xs)',
    lineHeight: 1,
    transition: 'color var(--duration-fast, 180ms) var(--ease-smooth, cubic-bezier(0.4, 0, 0.2, 1)), transform var(--duration-fast, 180ms) var(--ease-spring, cubic-bezier(0.34, 1.56, 0.64, 1))',
    borderRadius: '8px',
  };

  const bodyStyles = {
    padding: 'var(--space-xl)',
    overflowY: 'auto',
    flex: 1,
  };

  const footerStyles = {
    padding: 'var(--space-lg) var(--space-xl)',
    borderTop: '1px solid var(--border-color)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 'var(--space-md)',
    flexWrap: 'wrap',
  };

  return createPortal(
    <div style={backdropStyles} onClick={handleBackdropClick}>
      <div style={modalStyles}>
        {title && (
          <div style={headerStyles}>
            <h3 style={titleStyles}>{title}</h3>
            <button
              style={closeButtonStyles}
              onClick={onClose}
              onMouseEnter={(e) => e.target.style.color = 'var(--text-primary)'}
              onMouseLeave={(e) => e.target.style.color = 'var(--text-secondary)'}
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
    </div>,
    document.body
  );
};

export default Modal;
