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
    marginBottom: '8px',
    fontSize: '0.875rem',
    fontWeight: '500',
    color: '#1E293B', /* Slate-800 */
    letterSpacing: '0',
    fontFamily: 'Plus Jakarta Sans, sans-serif',
  };

  const inputBaseStyles = {
    width: '100%',
    padding: '13px 16px',
    fontSize: '1rem', /* 16px base */
    border: error ? '1px solid #F43F5E' : (focused ? '1px solid #4F46E5' : '1px solid transparent'),
    borderRadius: '16px',
    outline: 'none',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
    backgroundColor: disabled ? '#F1F5F9' : (focused ? '#FFFFFF' : '#F1F5F9'),
    color: disabled ? '#94A3B8' : '#1E293B', /* Slate-800 */
    cursor: disabled ? 'not-allowed' : 'text',
    boxShadow: focused ? (error ? '0 0 0 3px rgba(244, 63, 94, 0.12)' : '0 0 0 3px rgba(79, 70, 229, 0.12)') : 'none',
    fontFamily: 'Plus Jakarta Sans, Inter, -apple-system, BlinkMacSystemFont, sans-serif',
    minHeight: '48px',
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
    marginTop: '6px',
    fontSize: '0.75rem',
    color: '#F43F5E', /* Rose-500 */
    fontWeight: '500',
  };

  const helperStyles = {
    marginTop: '6px',
    fontSize: '0.75rem',
    color: '#64748B', /* Slate-500 */
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
