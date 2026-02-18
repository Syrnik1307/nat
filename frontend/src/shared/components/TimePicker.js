import React, { useState, useRef, useEffect } from 'react';

/**
 * Кастомный TimePicker без браузерного интерфейса
 */
const TimePicker = ({
  label,
  value,
  onChange,
  required = false,
  disabled = false,
  className = '',
  ...props
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [hours, setHours] = useState(value ? value.split(':')[0] : '09');
  const [minutes, setMinutes] = useState(value ? value.split(':')[1] : '00');
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

  useEffect(() => {
    if (value) {
      const [h, m] = value.split(':');
      setHours(h);
      setMinutes(m);
    }
  }, [value]);

  const handleApply = () => {
    const timeString = `${hours}:${minutes}`;
    onChange({ target: { value: timeString } });
    setIsOpen(false);
  };

  const hoursArray = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
  const minutesArray = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0'));

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
    color: value ? '#111827' : '#9ca3af',
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
    minWidth: '200px',
  };

  const timeDisplayStyles = {
    display: 'flex',
    gap: '1rem',
    marginBottom: '1rem',
    justifyContent: 'center',
  };

  const columnStyles = {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  };

  const columnLabelStyles = {
    fontSize: '0.75rem',
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: '0.25rem',
  };

  const scrollContainerStyles = {
    maxHeight: '150px',
    overflowY: 'auto',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    width: '60px',
  };

  const timeItemStyles = (isSelected) => ({
    padding: '0.5rem',
    fontSize: '0.875rem',
    color: isSelected ? 'white' : '#374151',
    backgroundColor: isSelected ? '#111827' : 'white',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  });

  const buttonContainerStyles = {
    display: 'flex',
    gap: '0.5rem',
    marginTop: '1rem',
  };

  const buttonStyles = (isPrimary) => ({
    flex: 1,
    padding: '0.5rem',
    fontSize: '0.875rem',
    fontWeight: '500',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    backgroundColor: isPrimary ? '#111827' : '#f3f4f6',
    color: isPrimary ? 'white' : '#374151',
    transition: 'all 0.2s ease',
  });

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
        <span>{value || '--:--'}</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: 'auto' }}>
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
      </div>

      {isOpen && !disabled && (
        <div style={dropdownStyles}>
          <div style={timeDisplayStyles}>
            <div style={columnStyles}>
              <div style={columnLabelStyles}>Час</div>
              <div style={scrollContainerStyles}>
                {hoursArray.map((h) => (
                  <div
                    key={h}
                    style={timeItemStyles(h === hours)}
                    onClick={() => setHours(h)}
                    onMouseEnter={(e) => {
                      if (h !== hours) {
                        e.currentTarget.style.backgroundColor = '#f9fafb';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (h !== hours) {
                        e.currentTarget.style.backgroundColor = 'white';
                      }
                    }}
                  >
                    {h}
                  </div>
                ))}
              </div>
            </div>

            <div style={columnStyles}>
              <div style={columnLabelStyles}>Мин</div>
              <div style={scrollContainerStyles}>
                {minutesArray.map((m) => (
                  <div
                    key={m}
                    style={timeItemStyles(m === minutes)}
                    onClick={() => setMinutes(m)}
                    onMouseEnter={(e) => {
                      if (m !== minutes) {
                        e.currentTarget.style.backgroundColor = '#f9fafb';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (m !== minutes) {
                        e.currentTarget.style.backgroundColor = 'white';
                      }
                    }}
                  >
                    {m}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div style={buttonContainerStyles}>
            <button
              style={buttonStyles(false)}
              onClick={() => setIsOpen(false)}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#e5e7eb'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
            >
              Отмена
            </button>
            <button
              style={buttonStyles(true)}
              onClick={handleApply}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#000'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#111827'}
            >
              Применить
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimePicker;
