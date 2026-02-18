import React from 'react';

/**
 * Переиспользуемый компонент бейджа
 * @param {string} variant - 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'
 * @param {string} size - 'small' | 'medium' | 'large'
 * @param {React.ReactNode} children - содержимое бейджа
 */
const Badge = ({ 
  variant = 'primary', 
  size = 'medium',
  className = '',
  style = {},
  children,
  ...props 
}) => {
  const variants = {
    primary: {
      backgroundColor: '#f0f9ff',
      color: '#1e3a8a',
      border: '1px solid #bae6fd',
    },
    success: {
      backgroundColor: '#ecfdf5',
      color: '#059669',
      border: '1px solid #a7f3d0',
    },
    warning: {
      backgroundColor: '#fffbeb',
      color: '#d97706',
      border: '1px solid #fde68a',
    },
    danger: {
      backgroundColor: '#fef2f2',
      color: '#dc2626',
      border: '1px solid #fecaca',
    },
    info: {
      backgroundColor: '#f0f9ff',
      color: '#1e3a8a',
      border: '1px solid #bae6fd',
    },
    neutral: {
      backgroundColor: '#f9fafb',
      color: '#6b7280',
      border: '1px solid #e5e7eb',
    },
  };

  const sizes = {
    small: {
      fontSize: '0.75rem',
      padding: '0.25rem 0.5rem',
    },
    medium: {
      fontSize: '0.875rem',
      padding: '0.375rem 0.75rem',
    },
    large: {
      fontSize: '0.9rem',
      padding: '0.5rem 1rem',
    },
  };

  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    borderRadius: '6px',
    fontWeight: '500',
    lineHeight: 1,
    whiteSpace: 'nowrap',
  };

  return (
    <span
      className={className}
      style={{
        ...baseStyles,
        ...variants[variant],
        ...sizes[size],
        ...style,
      }}
      {...props}
    >
      {children}
    </span>
  );
};

export default Badge;
