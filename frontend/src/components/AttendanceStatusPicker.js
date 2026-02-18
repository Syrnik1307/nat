/**
 * AttendanceStatusPicker.js
 * Мини-поп-ап для выбора статуса посещения
 * Открывается при клике на ячейку в журнале
 */

import React, { useState, useEffect, useRef } from 'react';
import './AttendanceStatusPicker.css';

const AttendanceStatusPicker = ({ currentStatus, onStatusSelect, onClose, isLoading }) => {
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const pickerRef = useRef(null);

  useEffect(() => {
    // Позиционировать поп-ап
    if (pickerRef.current) {
      const rect = pickerRef.current.parentElement?.getBoundingClientRect();
      if (rect) {
        setPosition({
          top: rect.bottom + 5,
          left: rect.left,
        });
      }
    }

    // Закрыть при клике вне
    // Используем mousedown, чтобы корректно работать вместе с другими "click outside" обработчиками
    // и не терять клики по кнопкам внутри поп-апа.
    const handlePointerDownOutside = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handlePointerDownOutside);
    return () => document.removeEventListener('mousedown', handlePointerDownOutside);
  }, [onClose]);

  const statusOptions = [
    { value: 'attended', label: 'Был', icon: '+', color: '#10b981' },
    { value: 'absent', label: 'Не был', icon: '-', color: '#ef4444' },
    { value: 'watched_recording', label: 'Посмотрел запись', icon: '◉', color: '#3b82f6' },
    { value: null, label: 'Очистить', icon: '—', color: '#9ca3af' },
  ];

  return (
    <div
      ref={pickerRef}
      className="attendance-status-picker"
      style={{
        position: 'fixed',
        top: `${position.top}px`,
        left: `${position.left}px`,
        zIndex: 1001,
      }}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="picker-content">
        {statusOptions.map((option) => (
          <button
            key={option.value ?? 'clear'}
            className={`picker-option ${currentStatus === option.value ? 'selected' : ''}`}
            onClick={() => {
              onStatusSelect(option.value);
            }}
            disabled={isLoading}
            title={option.label}
          >
            <span className="picker-icon">{option.icon}</span>
            <span className="picker-label">{option.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default AttendanceStatusPicker;
