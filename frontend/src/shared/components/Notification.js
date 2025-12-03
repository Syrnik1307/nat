import React from 'react';

const Notification = ({ isOpen, onClose, type = 'info', title, message }) => {
  if (!isOpen) return null;

  const typeConfig = {
    success: {
      icon: '+',
      gradient: 'linear-gradient(135deg, var(--success-500) 0%, var(--success-600) 100%)',
      color: 'var(--success-500)',
    },
    error: {
      icon: 'X',
      gradient: 'linear-gradient(135deg, var(--error-500) 0%, var(--error-600) 100%)',
      color: 'var(--error-500)',
    },
    warning: {
      icon: '!',
      gradient: 'linear-gradient(135deg, var(--warning-500) 0%, var(--warning-600) 100%)',
      color: 'var(--warning-500)',
    },
    info: {
      icon: 'i',
      gradient: 'linear-gradient(135deg, var(--blue-500) 0%, var(--blue-600) 100%)',
      color: 'var(--blue-500)',
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
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 'var(--z-modal-backdrop)',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg-primary)',
          borderRadius: 'var(--radius-xl)',
          boxShadow: 'var(--shadow-2xl)',
          maxWidth: '500px',
          width: '90%',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            background: config.gradient,
            padding: 'var(--space-xl)',
            textAlign: 'center',
            color: 'white',
          }}
        >
          <div style={{ fontSize: 'var(--text-4xl)', marginBottom: 'var(--space-md)' }}>
            {config.icon}
          </div>
          {title && <h2 style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-bold)', margin: 0 }}>{title}</h2>}
        </div>
        <div style={{ padding: 'var(--space-xl)', textAlign: 'center' }}>
          {message && <p style={{ fontSize: 'var(--text-base)', color: 'var(--text-secondary)', marginBottom: 'var(--space-xl)' }}>{message}</p>}
          <button
            style={{
              background: config.gradient,
              color: 'white',
              border: 'none',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-md) var(--space-2xl)',
              fontSize: 'var(--text-base)',
              fontWeight: 'var(--font-semibold)',
              cursor: 'pointer',
            }}
            onClick={onClose}
          >
            OK
          </button>
        </div>
      </div>
    </div>
  );
};

export default Notification;
