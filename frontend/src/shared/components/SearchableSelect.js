import React, { useEffect, useMemo, useRef, useState } from 'react';
import './SearchableSelect.css';

/**
 * Кастомный Select с поиском по ключевым словам.
 * Поддерживает псевдо-группы (аналог optgroup) через option.type === 'group'.
 */
const SearchableSelect = ({
  label,
  value,
  onChange,
  options = [],
  placeholder = 'Выберите...',
  searchPlaceholder = 'Поиск...',
  required = false,
  disabled = false,
  className = '',
  ...props
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef(null);
  const searchInputRef = useRef(null);

  const normalizedValue = value ?? '';

  const normalizedOptions = useMemo(() => {
    return Array.isArray(options) ? options : [];
  }, [options]);

  // Фильтрация опций по поисковому запросу
  const filteredOptions = useMemo(() => {
    if (!searchQuery.trim()) {
      return normalizedOptions;
    }
    
    const query = searchQuery.toLowerCase().trim();
    const result = [];
    let currentGroup = null;
    let groupHasItems = false;
    
    normalizedOptions.forEach((option, idx) => {
      if (!option) return;
      
      if (option.type === 'group') {
        // Сохраняем группу, добавим её только если в ней есть совпадения
        if (currentGroup && groupHasItems) {
          // Ничего не делаем, группа уже добавлена
        }
        currentGroup = option;
        groupHasItems = false;
        return;
      }
      
      // Проверяем совпадение
      const labelMatch = option.label?.toLowerCase().includes(query);
      if (labelMatch) {
        // Если есть текущая группа и она ещё не добавлена
        if (currentGroup && !groupHasItems) {
          result.push(currentGroup);
          groupHasItems = true;
        }
        result.push(option);
      }
    });
    
    return result;
  }, [normalizedOptions, searchQuery]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchQuery('');
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
        setSearchQuery('');
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
      // Фокус на поле поиска при открытии
      setTimeout(() => searchInputRef.current?.focus(), 50);
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
    setSearchQuery('');
  };

  const triggerText = selectedOption ? selectedOption.label : placeholder;
  const isPlaceholder = !selectedOption;

  return (
    <div className={`tp-searchable-select ${className}`.trim()} ref={containerRef} {...props}>
      {label && (
        <label className="tp-searchable-select-label">
          {label}
          {required && ' *'}
        </label>
      )}

      <button
        type="button"
        className={[
          'tp-searchable-select-trigger',
          isOpen ? 'is-open' : '',
          isPlaceholder ? 'is-placeholder' : ''
        ].filter(Boolean).join(' ')}
        onClick={() => !disabled && setIsOpen((v) => !v)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className="tp-searchable-select-value">{triggerText}</span>
        <svg className="tp-searchable-select-arrow" viewBox="0 0 12 12" aria-hidden="true">
          <path fill="currentColor" d="M2 4l4 4 4-4" />
        </svg>
      </button>

      {isOpen && !disabled && (
        <div className="tp-searchable-select-menu" role="listbox">
          <div className="tp-searchable-select-search">
            <svg className="tp-searchable-select-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={searchPlaceholder}
              className="tp-searchable-select-search-input"
              onClick={(e) => e.stopPropagation()}
            />
            {searchQuery && (
              <button 
                type="button"
                className="tp-searchable-select-search-clear"
                onClick={(e) => {
                  e.stopPropagation();
                  setSearchQuery('');
                  searchInputRef.current?.focus();
                }}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
              </button>
            )}
          </div>
          
          <div className="tp-searchable-select-options">
            {filteredOptions.length === 0 ? (
              <div className="tp-searchable-select-empty">
                Ничего не найдено
              </div>
            ) : (
              filteredOptions.map((option, idx) => {
                if (!option) return null;

                if (option.type === 'group') {
                  const key = `group-${idx}-${option.label}`;
                  return (
                    <div key={key} className="tp-searchable-select-group">
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
                      'tp-searchable-select-option',
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
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchableSelect;
