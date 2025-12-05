import React from 'react';

/**
 * Переиспользуемый компонент кнопки
 * @param {string} variant - 'primary' | 'secondary' | 'danger' | 'success'
 * @param {string} size - 'small' | 'medium' | 'large'
 * @param {boolean} disabled - отключена ли кнопка
 * @param {boolean} loading - показывать ли загрузку
 * @param {function} onClick - обработчик клика
 * @param {string} type - тип кнопки ('button' | 'submit')
 * @param {React.ReactNode} children - содержимое кнопки
 */
const Button = ({ 
  variant = 'primary', 
  size = 'medium', 
  disabled = false,
  loading = false,
  onClick,
  type = 'button',
  className = '',
  children,
  ...props 
}) => {
  const baseStyles = {
    border: 'none',
    borderRadius: 'var(--radius-lg)',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    fontWeight: '600',
    transition: 'all var(--transition-base)',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 'var(--space-sm)',
    opacity: disabled || loading ? 0.5 : 1,
    boxShadow: 'var(--shadow-sm)',
    fontFamily: 'inherit',
  };

  const variants = {
    primary: {
      background: 'linear-gradient(135deg, #2563eb 0%, #1e40af 100%)',
      color: 'white',
      boxShadow: '0 8px 20px -10px rgba(37, 99, 235, 0.55)',
    },
    secondary: {
      backgroundColor: '#f8fafc',
      color: '#0f172a',
      border: '1px solid #e2e8f0',
    },
    danger: {
      backgroundColor: '#ef4444',
      color: 'white',
      boxShadow: '0 4px 14px 0 rgba(239, 68, 68, 0.39)',
    },
    success: {
      backgroundColor: '#10b981',
      color: 'white',
      boxShadow: '0 4px 14px 0 rgba(16, 185, 129, 0.39)',
    },
    outline: {
      backgroundColor: 'transparent',
      color: '#2563eb',
      border: '2px solid #2563eb',
    },
    text: {
      backgroundColor: 'transparent',
      color: '#2563eb',
      boxShadow: 'none',
      textDecoration: 'underline',
    },
  };

  const sizes = {
    small: {
      padding: 'var(--space-sm) var(--space-md)',
      fontSize: '0.875rem',
    },
    medium: {
      padding: 'var(--space-sm) var(--space-lg)',
      fontSize: '0.9375rem',
    },
    large: {
      padding: 'var(--space-md) var(--space-xl)',
      fontSize: '1rem',
    },
  };

  const hoverStyles = {
    primary: '#1e40af',
    secondary: '#e2e8f0',
    danger: '#dc2626',
    success: '#059669',
    outline: 'rgba(37, 99, 235, 0.08)',
    text: 'rgba(37, 99, 235, 0.12)',
  };

  const safeVariant = variants[variant] ? variant : 'primary';

  const handleMouseEnter = (e) => {
    if (!disabled && !loading) {
      const target = e.currentTarget;
      if (!target) return;
      const hoverColor = hoverStyles[safeVariant];
      if (safeVariant === 'outline' || safeVariant === 'text') {
        target.style.backgroundColor = hoverColor;
      } else if (safeVariant === 'primary') {
        target.style.transform = 'scale(1.02)';
      } else {
        target.style.backgroundColor = hoverColor;
        target.style.transform = 'scale(1.02)';
      }
    }
  };

  const handleMouseLeave = (e) => {
    if (!disabled && !loading) {
      const target = e.currentTarget;
      if (!target) return;
      const variantStyle = variants[safeVariant] || {};
      // Для primary используется gradient, поэтому восстанавливаем background
      if (safeVariant === 'primary' && variantStyle.background) {
        target.style.background = variantStyle.background;
      } else if (variantStyle.backgroundColor) {
        target.style.backgroundColor = variantStyle.backgroundColor;
      } else {
        target.style.backgroundColor = '';
      }
      target.style.transform = 'scale(1)';
    }
  };

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={className}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{
        ...baseStyles,
        ...variants[safeVariant],
        ...sizes[size],
      }}
      {...props}
    >
      {loading && (
        <span style={{ 
          border: '2px solid rgba(255,255,255,0.3)',
          borderTopColor: 'white',
          borderRadius: '50%',
          width: '16px',
          height: '16px',
          animation: 'spin 0.6s linear infinite',
          display: 'inline-block',
        }} />
      )}
      {children}
    </button>
  );
};

// CSS для анимации загрузки (добавить в App.css или использовать styled-components)
const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;
if (!document.head.querySelector('style[data-button-styles]')) {
  styleSheet.setAttribute('data-button-styles', '');
  document.head.appendChild(styleSheet);
}

export default Button;
