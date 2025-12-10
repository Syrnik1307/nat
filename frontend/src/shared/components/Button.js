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
    borderRadius: '16px',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    fontWeight: '500',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    opacity: disabled || loading ? 0.5 : 1,
    fontFamily: 'Plus Jakarta Sans, Inter, -apple-system, BlinkMacSystemFont, sans-serif',
    transform: 'none',
    whiteSpace: 'nowrap',
  };

  const variants = {
    primary: {
      backgroundColor: '#4F46E5', /* Indigo-600 */
      color: '#F8FAFC', /* Slate-50 inverted text */
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.08), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
      border: 'none',
    },
    secondary: {
      backgroundColor: '#F1F5F9',
      color: '#1E293B', /* Slate-800 */
      border: '1px solid #E2E8F0',
      boxShadow: 'none',
    },
    danger: {
      backgroundColor: '#F43F5E', /* Rose-500 */
      color: '#F8FAFC',
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.08)',
      border: 'none',
    },
    success: {
      backgroundColor: '#10B981', /* Emerald-500 */
      color: '#F8FAFC',
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.08)',
      border: 'none',
    },
    outline: {
      backgroundColor: 'transparent',
      color: '#4F46E5', /* Indigo-600 */
      border: '2px solid #4F46E5',
      boxShadow: 'none',
    },
    text: {
      backgroundColor: 'transparent',
      color: '#4F46E5', /* Indigo-600 */
      boxShadow: 'none',
      border: 'none',
    },
  };

  const sizes = {
    small: {
      padding: '10px 16px',
      fontSize: '0.875rem',
      minHeight: '36px',
    },
    medium: {
      padding: '12px 24px',
      fontSize: '0.9375rem',
      minHeight: '44px',
    },
    large: {
      padding: '14px 32px',
      fontSize: '1rem',
      minHeight: '52px',
    },
  };

  const hoverStyles = {
    primary: '#4338CA', /* Indigo-700 */
    secondary: '#F8FAFC',
    danger: '#E11D48', /* Rose-600 */
    success: '#059669', /* Emerald-600 */
    outline: '#E0E7FF', /* Indigo-100 */
    text: '#F1F5F9',
  };

  const safeVariant = variants[variant] ? variant : 'primary';

  const handleMouseEnter = (e) => {
    if (!disabled && !loading) {
      const target = e.currentTarget;
      if (!target) return;
      const hoverColor = hoverStyles[safeVariant];
      if (safeVariant === 'primary') {
        target.style.background = hoverColor;
      } else if (safeVariant === 'outline' || safeVariant === 'text') {
        target.style.backgroundColor = hoverColor;
      } else {
        target.style.backgroundColor = hoverColor;
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
