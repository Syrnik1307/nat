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
    marginBottom: '1rem',
    width: '100%',
  };

  const labelStyles = {
    display: 'block',
    marginBottom: '0.5rem',
    fontSize: '0.875rem',
    fontWeight: '500',
    color: '#374151',
  };

  const inputBaseStyles = {
    width: '100%',
    padding: 'var(--space-sm) var(--space-md)',
    fontSize: '0.9375rem',
    border: `1px solid ${error ? 'var(--error-500)' : focused ? 'var(--accent-500)' : '#cbd5f5'}`,
    borderRadius: 'var(--radius-lg)',
    outline: 'none',
    transition: 'all var(--transition-base)',
    backgroundColor: disabled ? '#e2e8f0' : '#ffffff',
    color: disabled ? '#94a3b8' : '#0f172a',
    cursor: disabled ? 'not-allowed' : 'text',
    boxShadow: focused ? '0 0 0 3px rgba(37, 99, 235, 0.12)' : 'none',
    fontFamily: 'inherit',
  };

  const passwordContainerStyles = {
    position: 'relative',
    width: '100%',
  };

  const togglePasswordStyles = {
    position: 'absolute',
    right: '0.75rem',
    top: '50%',
    transform: 'translateY(-50%)',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '0.875rem',
    color: focused ? 'var(--accent-600)' : '#6b7280',
    padding: '0.25rem',
  };

  const errorStyles = {
    marginTop: '0.25rem',
    fontSize: '0.75rem',
    color: '#ef4444',
  };

  const helperStyles = {
    marginTop: '0.25rem',
    fontSize: '0.75rem',
    color: '#6b7280',
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
          {required && <span style={{ color: '#ef4444', marginLeft: '0.25rem' }}>*</span>}
        </label>
      )}
      {renderInput()}
      {error && <div style={errorStyles}>{error}</div>}
      {helperText && !error && <div style={helperStyles}>{helperText}</div>}
    </div>
  );
};

export default Input;
