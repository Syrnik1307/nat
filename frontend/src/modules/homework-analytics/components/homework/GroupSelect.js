import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const GroupSelect = ({
  label = 'Группа',
  placeholder = 'Выберите группу',
  value,
  options = [],
  onChange,
  disabled = false,
  loading = false,
  error = null,
  onRetry,
}) => {
  const containerRef = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);

  const normalizedValue = value === undefined || value === null ? '' : String(value);

  const selectedOption = useMemo(
    () => options.find((option) => String(option.value) === normalizedValue) || null,
    [options, normalizedValue]
  );

  const toggleOpen = () => {
    if (disabled) return;
    setIsOpen((previous) => !previous);
  };

  const close = useCallback(() => setIsOpen(false), []);

  const handleOutsideClick = useCallback(
    (event) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target)) {
        close();
      }
    },
    [close]
  );

  const handleSelect = useCallback(
    (option) => {
      if (!option) return;
      onChange(String(option.value));
      setIsOpen(false);
    },
    [onChange]
  );

  useEffect(() => {
    if (!isOpen) return undefined;
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen, handleOutsideClick]);

  useEffect(() => {
    if (!isOpen) {
      const index = options.findIndex((option) => String(option.value) === normalizedValue);
      setHighlightIndex(index >= 0 ? index : 0);
      return undefined;
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        close();
        return;
      }

      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setHighlightIndex((previous) => {
          const nextIndex = previous + 1;
          return nextIndex >= options.length ? 0 : nextIndex;
        });
        return;
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setHighlightIndex((previous) => {
          const nextIndex = previous - 1;
          return nextIndex < 0 ? Math.max(options.length - 1, 0) : nextIndex;
        });
        return;
      }

      if (event.key === 'Enter') {
        event.preventDefault();
        if (options[highlightIndex]) {
          handleSelect(options[highlightIndex]);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, options, highlightIndex, normalizedValue, handleSelect, close]);

  const renderDropdownContent = () => {
    if (loading) {
      return <div className="hc-fancy-select-loading">Загружаем группы...</div>;
    }

    if (!options.length) {
      return <div className="hc-fancy-select-empty">Группы не найдены</div>;
    }

    return options.map((option, index) => {
      const isSelected = selectedOption && String(option.value) === normalizedValue;
      const isHighlighted = index === highlightIndex;
      return (
        <button
          type="button"
          key={option.value}
          className={`hc-fancy-option${isSelected ? ' is-selected' : ''}${
            isHighlighted ? ' is-highlighted' : ''
          }`}
          onClick={() => handleSelect(option)}
        >
          <span>{option.label}</span>
          {isSelected && <span className="hc-fancy-check">Выбрано</span>}
        </button>
      );
    });
  };

  return (
    <div className="form-group">
      {label && <label className="form-label">{label}</label>}
      <div
        className={`hc-fancy-select${isOpen ? ' is-open' : ''}${disabled ? ' is-disabled' : ''}`}
        ref={containerRef}
      >
        <button
          type="button"
          className="hc-fancy-select-trigger"
          onClick={toggleOpen}
          disabled={disabled}
        >
          <div className="hc-fancy-select-content">
            <span className="hc-fancy-select-placeholder">
              {selectedOption ? 'Группа назначена' : 'Группа не выбрана'}
            </span>
            <span className={`hc-fancy-select-value${selectedOption ? ' is-set' : ''}`}>
              {selectedOption ? selectedOption.label : placeholder}
            </span>
          </div>
          {loading && <span className="hc-fancy-select-badge">•••</span>}
          <span className="hc-fancy-select-chevron" aria-hidden="true" />
        </button>

        {isOpen && <div className="hc-fancy-select-dropdown">{renderDropdownContent()}</div>}
      </div>

      {error && (
        <div className="hc-fancy-select-error">
          <span>{error}</span>
          {onRetry && (
            <button type="button" onClick={onRetry} className="gm-btn-surface">
              Обновить
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default GroupSelect;
