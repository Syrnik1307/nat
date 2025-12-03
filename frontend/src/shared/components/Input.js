import React, { useState } from 'react';

/**
 * Переиспользуемый компонент поля ввода
 * @param {string} label - метка поля
 * @param {string} type - тип поля ('text' | 'email' | 'password' | 'number' | 'date' | 'textarea')
 * @param {string} placeholder - плейсхолдер
 * @param {string} value - значение поля
 * @param {function} onChange - обработчик изменения
 * @param {string} error - текст ошибки
 * @param {boolean} required - обязательное ли поле
 * @param {boolean} disabled - отключено ли поле
 * @param {string} helperText - вспомогательный текст
 */
const Input = ({ 
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  error,
  required = false,
  disabled = false,
  helperText,
  rows = 4,
  className = '',
  disablePasswordToggle = false,
  ...props 
}) => {
  const [focused, setFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const containerStyles = {
    marginBottom: 'var(--space-lg)',
    width: '100%',
  };

  const labelStyles = {
    display: 'block',
    marginBottom: 'var(--space-sm)',
    fontSize: 'var(--text-sm)',
    fontWeight: 'var(--font-medium)',
    color: 'var(--text-primary)',
  };

  const inputBaseStyles = {
    width: '100%',
    padding: 'var(--space-md) var(--space-lg)',
    fontSize: 'var(--text-base)',
    border: `1px solid ${error ? 'var(--error-500)' : focused ? 'var(--primary-500)' : 'var(--border-color)'}`,
    borderRadius: 'var(--radius-lg)',
    outline: 'none',
    transition: 'all var(--transition-base)',
    backgroundColor: disabled ? 'var(--gray-100)' : 'var(--bg-primary)',
    color: disabled ? 'var(--text-tertiary)' : 'var(--text-primary)',
    cursor: disabled ? 'not-allowed' : 'text',
    boxShadow: focused ? `0 0 0 3px ${error ? 'rgba(239, 68, 68, 0.12)' : 'rgba(255, 107, 53, 0.12)'}` : 'none',
    fontFamily: 'var(--font-sans)',
  };

  const passwordContainerStyles = {
    position: 'relative',
    width: '100%',
  };

  const togglePasswordStyles = {
    position: 'absolute',
    right: 'var(--space-md)',
    top: '50%',
    transform: 'translateY(-50%)',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: 'var(--text-sm)',
    color: focused ? 'var(--primary-600)' : 'var(--text-secondary)',
    padding: 'var(--space-xs)',
    transition: 'color var(--transition-base)',
  };

  const errorStyles = {
    marginTop: 'var(--space-xs)',
    fontSize: 'var(--text-xs)',
    color: 'var(--error-500)',
  };

  const helperStyles = {
    marginTop: 'var(--space-xs)',
    fontSize: 'var(--text-xs)',
    color: 'var(--text-secondary)',
  };

  const handleChange = (e) => {
    if (onChange) {
      onChange(e);
    }
  };

  const renderInput = () => {
    if (type === 'textarea') {
      return (
        <textarea
          value={value}
          onChange={handleChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          rows={rows}
          className={className}
          style={{
            ...inputBaseStyles,
            resize: 'vertical',
            minHeight: '100px',
          }}
          {...props}
        />
      );
    }

    if (type === 'password' && !disablePasswordToggle) {
      return (
        <div style={passwordContainerStyles}>
          <input
            type={showPassword ? 'text' : 'password'}
            value={value}
            onChange={handleChange}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder={placeholder}
            disabled={disabled}
            required={required}
            className={className}
            style={inputBaseStyles}
            {...props}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            style={togglePasswordStyles}
            tabIndex={-1}
          >
            {showPassword ? '👁️' : '👁️‍🗨️'}
          </button>
        </div>
      );
    }

    return (
      <input
        type={type}
        value={value}
        onChange={handleChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        className={className}
        style={inputBaseStyles}
        {...props}
      />
    );
  };

  return (
    <div style={containerStyles}>
      {label && (
        <label style={labelStyles}>
          {label}
          {required && <span style={{ color: 'var(--error-500)', marginLeft: 'var(--space-xs)' }}>*</span>}
        </label>
      )}
      {renderInput()}
      {error && <div style={errorStyles}>{error}</div>}
      {helperText && !error && <div style={helperStyles}>{helperText}</div>}
    </div>
  );
};

export default Input;
