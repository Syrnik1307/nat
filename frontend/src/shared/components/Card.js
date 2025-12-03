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
    small: 'var(--space-lg)',
    medium: 'var(--space-xl)',
    large: 'var(--space-2xl)',
  };

  const baseStyles = {
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: 'var(--radius-xl)',
    padding: paddings[padding],
    transition: 'all var(--transition-base)',
    cursor: onClick ? 'pointer' : 'default',
    boxShadow: 'var(--shadow-sm)',
  };

  const handleMouseEnter = (e) => {
    if (hoverable || onClick) {
      e.currentTarget.style.transform = 'translateY(-4px)';
      e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
      e.currentTarget.style.borderColor = 'var(--primary-500)';
    }
  };

  const handleMouseLeave = (e) => {
    if (hoverable || onClick) {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
      e.currentTarget.style.borderColor = 'var(--border-color)';
    }
  };

  const titleStyles = {
    fontSize: 'var(--text-xl)',
    fontWeight: 'var(--font-semibold)',
    color: 'var(--text-primary)',
    marginBottom: 'var(--space-lg)',
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
