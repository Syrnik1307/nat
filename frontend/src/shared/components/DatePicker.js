import React, { useState, useRef, useEffect } from 'react';

/**
 * Кастомный DatePicker без браузерного календаря
 */
const DatePicker = ({
  label,
  value,
  onChange,
  required = false,
  disabled = false,
  className = '',
  minDate,
  maxDate,
  ...props
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const containerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const months = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
  ];

  const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  const formatDate = (date) => {
    if (!date) return '';
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const parseDate = (dateString) => {
    if (!dateString) return null;
    const [year, month, day] = dateString.split('-');
    return new Date(year, month - 1, day);
  };

  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    
    let firstDayOfWeek = firstDay.getDay();
    firstDayOfWeek = firstDayOfWeek === 0 ? 6 : firstDayOfWeek - 1;

    const days = [];
    
    // Пустые ячейки до первого дня
    for (let i = 0; i < firstDayOfWeek; i++) {
      days.push(null);
    }
    
    // Дни месяца
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(new Date(year, month, i));
    }
    
    return days;
  };

  const handleDateSelect = (date) => {
    if (date) {
      onChange({ target: { value: formatDate(date) } });
      setIsOpen(false);
    }
  };

  const handlePrevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  };

  const handleNextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
  };

  const handleToday = () => {
    const today = new Date();
    onChange({ target: { value: formatDate(today) } });
    setCurrentMonth(today);
    setIsOpen(false);
  };

  const isDateSelected = (date) => {
    if (!date || !value) return false;
    return formatDate(date) === value;
  };

  const isDateDisabled = (date) => {
    if (!date) return true;
    if (minDate && date < parseDate(minDate)) return true;
    if (maxDate && date > parseDate(maxDate)) return true;
    return false;
  };

  const selectedDate = value ? parseDate(value) : null;
  const displayValue = selectedDate 
    ? `${selectedDate.getDate().toString().padStart(2, '0')}.${(selectedDate.getMonth() + 1).toString().padStart(2, '0')}.${selectedDate.getFullYear()}`
    : '';

  const days = getDaysInMonth(currentMonth);

  // Styles
  const containerStyles = {
    position: 'relative',
    width: '100%',
  };

  const labelStyles = {
    display: 'block',
    marginBottom: '0.5rem',
    fontSize: '0.875rem',
    fontWeight: '500',
    color: '#374151',
  };

  const triggerStyles = {
    width: '100%',
    padding: '0.625rem 0.875rem',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '0.875rem',
    color: displayValue ? '#111827' : '#9ca3af',
    backgroundColor: disabled ? '#f9fafb' : 'white',
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    userSelect: 'none',
  };

  const dropdownStyles = {
    position: 'absolute',
    top: 'calc(100% + 4px)',
    left: 0,
    backgroundColor: 'white',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
    zIndex: 1000,
    padding: '1rem',
    minWidth: '280px',
  };

  const headerStyles = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '1rem',
  };

  const monthYearStyles = {
    fontSize: '0.875rem',
    fontWeight: '600',
    color: '#111827',
  };

  const navButtonStyles = {
    background: 'none',
    border: 'none',
    fontSize: '1.25rem',
    color: '#6b7280',
    cursor: 'pointer',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    transition: 'all 0.2s ease',
  };

  const weekDaysContainerStyles = {
    display: 'grid',
    gridTemplateColumns: 'repeat(7, 1fr)',
    gap: '0.25rem',
    marginBottom: '0.5rem',
  };

  const weekDayStyles = {
    fontSize: '0.75rem',
    color: '#6b7280',
    textAlign: 'center',
    padding: '0.25rem',
    fontWeight: '500',
  };

  const daysContainerStyles = {
    display: 'grid',
    gridTemplateColumns: 'repeat(7, 1fr)',
    gap: '0.25rem',
  };

  const dayStyles = (isSelected, isDisabled) => ({
    padding: '0.5rem',
    fontSize: '0.875rem',
    color: isDisabled ? '#d1d5db' : isSelected ? 'white' : '#374151',
    backgroundColor: isSelected ? '#111827' : 'transparent',
    textAlign: 'center',
    cursor: isDisabled ? 'not-allowed' : 'pointer',
    borderRadius: '6px',
    transition: 'all 0.15s ease',
    fontWeight: isSelected ? '600' : '400',
  });

  const footerStyles = {
    marginTop: '1rem',
    paddingTop: '1rem',
    borderTop: '1px solid #e5e7eb',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  };

  const todayButtonStyles = {
    background: 'none',
    border: 'none',
    fontSize: '0.875rem',
    color: '#111827',
    cursor: 'pointer',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    fontWeight: '500',
    transition: 'background-color 0.2s ease',
  };

  const clearButtonStyles = {
    background: 'none',
    border: 'none',
    fontSize: '0.875rem',
    color: '#6b7280',
    cursor: 'pointer',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    transition: 'color 0.2s ease',
  };

  return (
    <div style={containerStyles} className={className} ref={containerRef}>
      {label && <label style={labelStyles}>{label}{required && ' *'}</label>}
      
      <div
        style={triggerStyles}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        onMouseEnter={(e) => {
          if (!disabled && !isOpen) {
            e.currentTarget.style.borderColor = '#9ca3af';
          }
        }}
        onMouseLeave={(e) => {
          if (!isOpen) {
            e.currentTarget.style.borderColor = '#d1d5db';
          }
        }}
      >
        <span>{displayValue || 'дд.мм.гггг'}</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: 'auto' }}>
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
          <line x1="16" y1="2" x2="16" y2="6"/>
          <line x1="8" y1="2" x2="8" y2="6"/>
          <line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
      </div>

      {isOpen && !disabled && (
        <div style={dropdownStyles}>
          <div style={headerStyles}>
            <button
              style={navButtonStyles}
              onClick={handlePrevMonth}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              ‹
            </button>
            <div style={monthYearStyles}>
              {months[currentMonth.getMonth()]} {currentMonth.getFullYear()}
            </div>
            <button
              style={navButtonStyles}
              onClick={handleNextMonth}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              ›
            </button>
          </div>

          <div style={weekDaysContainerStyles}>
            {weekDays.map(day => (
              <div key={day} style={weekDayStyles}>{day}</div>
            ))}
          </div>

          <div style={daysContainerStyles}>
            {days.map((date, index) => {
              const isSelected = isDateSelected(date);
              const isDisabled = isDateDisabled(date);
              
              return (
                <div
                  key={index}
                  style={dayStyles(isSelected, isDisabled || !date)}
                  onClick={() => !isDisabled && date && handleDateSelect(date)}
                  onMouseEnter={(e) => {
                    if (!isDisabled && date && !isSelected) {
                      e.currentTarget.style.backgroundColor = '#f3f4f6';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  {date ? date.getDate() : ''}
                </div>
              );
            })}
          </div>

          <div style={footerStyles}>
            <button
              style={todayButtonStyles}
              onClick={handleToday}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              Сегодня
            </button>
            {value && (
              <button
                style={clearButtonStyles}
                onClick={() => {
                  onChange({ target: { value: '' } });
                  setIsOpen(false);
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = '#dc2626'}
                onMouseLeave={(e) => e.currentTarget.style.color = '#6b7280'}
              >
                Очистить
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DatePicker;
