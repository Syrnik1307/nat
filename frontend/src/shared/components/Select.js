import React, { useEffect, useMemo, useRef, useState } from 'react';
import './Select.css';

/**
 * Кастомный Select без браузерных стилей.
 * Поддерживает псевдо-группы (аналог optgroup) через option.type === 'group'.
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

  const normalizedValue = value ?? '';

  const normalizedOptions = useMemo(() => {
    return Array.isArray(options) ? options : [];
  }, [options]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
        document.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [isOpen]);

  const selectedOption = useMemo(() => {
    return normalizedOptions.find(
      (opt) => opt && opt.type !== 'group' && String(opt.value) === String(normalizedValue)
    );
  }, [normalizedOptions, normalizedValue]);

  const handleSelect = (optionValue) => {
    if (disabled) return;
    onChange?.({ target: { value: optionValue } });
    setIsOpen(false);
  };

  const triggerText = selectedOption ? selectedOption.label : placeholder;
  const isPlaceholder = !selectedOption;

  return (
    <div className={`tp-select ${className}`.trim()} ref={containerRef} {...props}>
      {label && (
        <label className="tp-select-label">
          {label}
          {required && ' *'}
        </label>
      )}

      <button
        type="button"
        className={[
          'tp-select-trigger',
          isOpen ? 'is-open' : '',
          isPlaceholder ? 'is-placeholder' : ''
        ].filter(Boolean).join(' ')}
        onClick={() => !disabled && setIsOpen((v) => !v)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span>{triggerText}</span>
        <svg className="tp-select-arrow" viewBox="0 0 12 12" aria-hidden="true">
          <path fill="currentColor" d="M2 4l4 4 4-4" />
        </svg>
      </button>

      {isOpen && !disabled && (
        <div className="tp-select-menu" role="listbox">
          {normalizedOptions.map((option, idx) => {
            if (!option) return null;

            if (option.type === 'group') {
              const key = `group-${idx}-${option.label}`;
              return (
                <div key={key} className="tp-select-group">
                  {option.label}
                </div>
              );
            }

            const isSelected = String(option.value) === String(normalizedValue);
            return (
              <button
                type="button"
                key={String(option.value)}
                className={[
                  'tp-select-option',
                  isSelected ? 'is-selected' : ''
                ].filter(Boolean).join(' ')}
                onClick={() => handleSelect(option.value)}
                role="option"
                aria-selected={isSelected}
                disabled={Boolean(option.disabled)}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Select;
