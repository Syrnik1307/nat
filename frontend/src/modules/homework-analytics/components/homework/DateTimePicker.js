import React from 'react';

/**
 * DateTimePicker — простой компонент для выбора даты и времени (дедлайн ДЗ).
 * Props:
 *   value    — ISO-строка или пустая строка
 *   onChange — (newValue: string) => void
 */
const DateTimePicker = ({ value, onChange }) => {
  return (
    <div className="form-group">
      <label className="form-label">Дедлайн</label>
      <input
        className="form-input"
        type="datetime-local"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
};

export default DateTimePicker;
