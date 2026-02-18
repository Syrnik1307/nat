import React from 'react';

const Notification = ({ isOpen, onClose, type = 'info', title, message }) => {
  if (!isOpen) return null;

  const typeConfig = {
    success: {
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      ),
      bg: 'var(--success-50, #F0FDF4)',
      border: 'var(--success-200, #BBF7D0)',
      iconBg: 'var(--success-100, #DCFCE7)',
      color: 'var(--success-600, #16A34A)',
      buttonBg: 'var(--success-600, #16A34A)',
    },
    error: {
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
      ),
      bg: 'var(--error-50, #FEF2F2)',
      border: 'var(--error-200, #FECACA)',
      iconBg: 'var(--error-100, #FEE2E2)',
      color: 'var(--error-600, #DC2626)',
      buttonBg: 'var(--error-600, #DC2626)',
    },
    warning: {
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      ),
      bg: 'var(--warning-50, #FFFBEB)',
      border: 'var(--warning-200, #FDE68A)',
      iconBg: 'var(--warning-100, #FEF3C7)',
      color: 'var(--warning-600, #D97706)',
      buttonBg: 'var(--warning-600, #D97706)',
    },
    info: {
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="16" x2="12" y2="12"/>
          <line x1="12" y1="8" x2="12.01" y2="8"/>
        </svg>
      ),
      bg: 'var(--blue-50, #EFF6FF)',
      border: 'var(--blue-200, #BFDBFE)',
      iconBg: 'var(--blue-100, #DBEAFE)',
      color: 'var(--blue-600, #2563EB)',
      buttonBg: 'var(--blue-600, #2563EB)',
    },
  };

  const config = typeConfig[type];

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.4)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 'var(--z-modal-backdrop, 1000)',
        animation: 'fadeIn 0.2s ease-out',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: config.bg,
          borderRadius: '16px',
          boxShadow: '0 20px 50px rgba(15, 23, 42, 0.15)',
          maxWidth: '420px',
          width: '90%',
          border: `1px solid ${config.border}`,
          animation: 'scaleIn 0.25s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ padding: '32px 24px', textAlign: 'center' }}>
          {/* Иконка */}
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              background: config.iconBg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              color: config.color,
            }}
          >
            {config.icon}
          </div>
          
          {/* Заголовок */}
          {title && (
            <h2
              style={{
                fontSize: '1.25rem',
                fontWeight: '600',
                color: '#1e293b',
                margin: '0 0 8px',
              }}
            >
              {title}
            </h2>
          )}
          
          {/* Сообщение */}
          {message && (
            <p
              style={{
                fontSize: '0.9375rem',
                color: '#64748b',
                margin: '0 0 24px',
                lineHeight: '1.5',
                whiteSpace: 'pre-line',
              }}
            >
              {message}
            </p>
          )}
          
          {/* Кнопка */}
          <button
            style={{
              background: config.buttonBg,
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              padding: '12px 32px',
              fontSize: '0.9375rem',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              minWidth: '120px',
            }}
            onClick={onClose}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            OK
          </button>
        </div>
      </div>
      
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
};

export default Notification;
