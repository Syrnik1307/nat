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
      background: 'linear-gradient(135deg, var(--accent-500) 0%, var(--accent-600) 100%)',
      color: 'white',
      boxShadow: '0 4px 14px 0 rgba(255, 107, 53, 0.39)',
    },
    secondary: {
      backgroundColor: 'var(--gray-100)',
      color: 'var(--gray-700)',
      border: '1px solid var(--gray-200)',
    },
    danger: {
      backgroundColor: 'var(--error-500)',
      color: 'white',
      boxShadow: '0 4px 14px 0 rgba(239, 68, 68, 0.39)',
    },
    success: {
      backgroundColor: 'var(--success-500)',
      color: 'white',
      boxShadow: '0 4px 14px 0 rgba(16, 185, 129, 0.39)',
    },
    outline: {
      backgroundColor: 'transparent',
      color: 'var(--accent-500)',
      border: '2px solid var(--accent-500)',
    },
    text: {
      backgroundColor: 'transparent',
      color: 'var(--accent-500)',
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
    primary: '#e55a2b',
    secondary: '#e5e7eb',
    danger: '#dc2626',
    success: '#059669',
    outline: '#fff5f2',
    text: 'rgba(102, 126, 234, 0.1)',
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
