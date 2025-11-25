import React from 'react';

/**
 * Переиспользуемый компонент карточки
 * @param {string} title - заголовок карточки
 * @param {boolean} hoverable - добавить эффект hover
 * @param {function} onClick - обработчик клика
 * @param {string} padding - размер отступов ('small' | 'medium' | 'large')
 * @param {React.ReactNode} children - содержимое карточки
 */
const Card = ({ 
  title, 
  hoverable = false, 
  onClick,
  padding = 'medium',
  className = '',
  style = {},
  children,
  ...props 
}) => {
  const paddings = {
    small: '1rem',
    medium: '1.5rem',
    large: '2rem',
  };

  const baseStyles = {
    backgroundColor: '#ffffff',
    border: '1px solid var(--gray-200)',
    borderRadius: 'var(--radius-2xl)',
    padding: paddings[padding],
    transition: 'all var(--transition-base)',
    cursor: onClick ? 'pointer' : 'default',
    boxShadow: 'var(--shadow-sm)',
  };

  const handleMouseEnter = (e) => {
    if (hoverable || onClick) {
      e.currentTarget.style.transform = 'translateY(-4px)';
      e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
      e.currentTarget.style.borderColor = 'var(--accent-500)';
    }
  };

  const handleMouseLeave = (e) => {
    if (hoverable || onClick) {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
      e.currentTarget.style.borderColor = 'var(--gray-200)';
    }
  };

  const titleStyles = {
    fontSize: '1.25rem',
    fontWeight: '600',
    color: '#111827',
    marginBottom: '1rem',
    marginTop: 0,
  };

  return (
    <div
      className={className}
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{
        ...baseStyles,
        ...style,
      }}
      {...props}
    >
      {title && <h3 style={titleStyles}>{title}</h3>}
      {children}
    </div>
  );
};

export default Card;
