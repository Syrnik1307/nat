import React, { useState, useRef, useEffect } from 'react';

/**
 * Кастомный Select без браузерных стилей
 */
const Select = ({
  label,
  value,
  onChange,
  options = [],
  placeholder = 'Выберите...',
  required = false,
  disabled = false,
  className = '',
  ...props
}) => {
  const [isOpen, setIsOpen] = useState(false);
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

  const selectedOption = options.find(opt => String(opt.value) === String(value));

  const handleSelect = (optionValue) => {
    onChange({ target: { value: optionValue } });
    setIsOpen(false);
  };

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
    color: selectedOption ? '#111827' : '#9ca3af',
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
    right: 0,
    maxHeight: '240px',
    overflowY: 'auto',
    backgroundColor: 'white',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
    zIndex: 1000,
  };

  const optionStyles = (isSelected) => ({
    padding: '0.625rem 0.875rem',
    fontSize: '0.875rem',
    color: isSelected ? '#111827' : '#374151',
    backgroundColor: isSelected ? '#f3f4f6' : 'white',
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  });

  const arrowStyles = {
    marginLeft: '0.5rem',
    fontSize: '0.75rem',
    color: '#6b7280',
    transition: 'transform 0.2s ease',
    transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
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
        <span>{selectedOption ? selectedOption.label : placeholder}</span>
        <span style={arrowStyles}>▼</span>
      </div>

      {isOpen && !disabled && (
        <div style={dropdownStyles}>
          {options.map((option) => {
            const isSelected = String(option.value) === String(value);
            return (
              <div
                key={option.value}
                style={optionStyles(isSelected)}
                onClick={() => handleSelect(option.value)}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = '#f9fafb';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = 'white';
                  }
                }}
              >
                {option.label}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Select;
