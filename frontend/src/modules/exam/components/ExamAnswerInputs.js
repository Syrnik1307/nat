/**
 * ExamAnswerInputs — специализированные компоненты ввода ответов.
 *
 * Каждый answer_type из ExamTaskSlot имеет свой компонент ввода,
 * повторяющий формат реального ЕГЭ/ОГЭ.
 */

import React, { useState, useCallback } from 'react';

// ============================================================
// ShortNumberInput — краткий числовой ответ (задания 1-25 информатика)
// ============================================================

export function ShortNumberInput({ value, onChange, disabled }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Ответ (целое число):</label>
      <input
        className="exam-answer-input mono"
        type="text"
        inputMode="numeric"
        value={value || ''}
        onChange={e => {
          const v = e.target.value.replace(/[^\d\-]/g, '');
          onChange(v);
        }}
        placeholder="Введите число"
        disabled={disabled}
        autoComplete="off"
        style={{ maxWidth: 240 }}
      />
    </div>
  );
}

// ============================================================
// ShortTextInput — краткий текстовый ответ
// ============================================================

export function ShortTextInput({ value, onChange, disabled }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Ответ:</label>
      <input
        className="exam-answer-input"
        type="text"
        value={value || ''}
        onChange={e => onChange(e.target.value)}
        placeholder="Введите ответ"
        disabled={disabled}
        autoComplete="off"
        style={{ maxWidth: 400 }}
      />
    </div>
  );
}

// ============================================================
// DigitSequenceInput — последовательность цифр (без пробелов)
// ============================================================

export function DigitSequenceInput({ value, onChange, disabled, maxLength = 20 }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Последовательность цифр (без пробелов):</label>
      <input
        className="exam-answer-input mono"
        type="text"
        inputMode="numeric"
        value={value || ''}
        onChange={e => {
          const v = e.target.value.replace(/[^\d]/g, '').slice(0, maxLength);
          onChange(v);
        }}
        placeholder="Например: 2413"
        disabled={disabled}
        autoComplete="off"
        style={{ maxWidth: 300, letterSpacing: '0.2em', fontSize: 'var(--text-lg)' }}
      />
      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 4 }}>
        Введите цифры подряд, без пробелов и разделителей
      </div>
    </div>
  );
}

// ============================================================
// LetterSequenceInput — последовательность букв (АБВГД)
// ============================================================

export function LetterSequenceInput({ value, onChange, disabled, maxLength = 10 }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Последовательность букв:</label>
      <input
        className="exam-answer-input mono"
        type="text"
        value={value || ''}
        onChange={e => {
          const v = e.target.value.toUpperCase().replace(/[^А-ЯЁABCDE]/g, '').slice(0, maxLength);
          onChange(v);
        }}
        placeholder="Например: БВГА"
        disabled={disabled}
        autoComplete="off"
        style={{ maxWidth: 300, letterSpacing: '0.2em', fontSize: 'var(--text-lg)' }}
      />
    </div>
  );
}

// ============================================================
// DecimalNumberInput — десятичная дробь
// ============================================================

export function DecimalNumberInput({ value, onChange, disabled }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Ответ (десятичная дробь, через запятую):</label>
      <input
        className="exam-answer-input mono"
        type="text"
        value={value || ''}
        onChange={e => {
          // Разрешаем цифры, запятую, точку, минус
          const v = e.target.value.replace(/[^\d,.\-]/g, '');
          onChange(v);
        }}
        placeholder="Например: 3,14"
        disabled={disabled}
        autoComplete="off"
        style={{ maxWidth: 240 }}
      />
      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 4 }}>
        Используйте запятую или точку как разделитель
      </div>
    </div>
  );
}

// ============================================================
// NumberRangeInput — диапазон чисел
// ============================================================

export function NumberRangeInput({ value, onChange, disabled }) {
  const [from, to] = (value || '').split('-').map(s => s.trim());

  const handleChange = (part, val) => {
    if (part === 'from') onChange(`${val}-${to || ''}`);
    else onChange(`${from || ''}-${val}`);
  };

  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Диапазон чисел:</label>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
        <input
          className="exam-answer-input mono"
          type="text"
          inputMode="numeric"
          value={from || ''}
          onChange={e => handleChange('from', e.target.value.replace(/[^\d\-]/g, ''))}
          placeholder="От"
          disabled={disabled}
          style={{ width: 100 }}
        />
        <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>&mdash;</span>
        <input
          className="exam-answer-input mono"
          type="text"
          inputMode="numeric"
          value={to || ''}
          onChange={e => handleChange('to', e.target.value.replace(/[^\d\-]/g, ''))}
          placeholder="До"
          disabled={disabled}
          style={{ width: 100 }}
        />
      </div>
    </div>
  );
}

// ============================================================
// MultipleNumbersInput — несколько чисел через пробел
// ============================================================

export function MultipleNumbersInput({ value, onChange, disabled }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Несколько чисел (через пробел):</label>
      <input
        className="exam-answer-input mono"
        type="text"
        value={value || ''}
        onChange={e => {
          const v = e.target.value.replace(/[^\d\s\-]/g, '');
          onChange(v);
        }}
        placeholder="Например: 3 7 12"
        disabled={disabled}
        autoComplete="off"
        style={{ maxWidth: 400, letterSpacing: '0.05em' }}
      />
    </div>
  );
}

// ============================================================
// MatchingInput — таблица соответствий (А→1, Б→3...)
// ============================================================

export function MatchingInput({ value, onChange, disabled, config }) {
  const pairs = config?.pairs || [];
  const leftItems = pairs.map(p => p.left);
  const rightItems = [...new Set(pairs.map(p => p.right))];

  // value = JSON dict: {"А": "1", "Б": "3"...} or serialized
  const answers = typeof value === 'string' ? (tryParse(value) || {}) : (value || {});

  const handleMatch = (leftKey, rightVal) => {
    const updated = { ...answers, [leftKey]: rightVal };
    onChange(JSON.stringify(updated));
  };

  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Установите соответствие:</label>
      <table style={{
        width: '100%',
        maxWidth: 500,
        borderCollapse: 'separate',
        borderSpacing: 0,
        fontSize: 'var(--text-sm)',
      }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              Элемент
            </th>
            <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              Соответствие
            </th>
          </tr>
        </thead>
        <tbody>
          {leftItems.map((left, idx) => {
            const key = String.fromCharCode(1040 + idx); // А, Б, В...
            return (
              <tr key={idx}>
                <td style={{ padding: '0.375rem 0.5rem', borderBottom: '1px solid var(--border-light)' }}>
                  <strong>{key})</strong> {left}
                </td>
                <td style={{ padding: '0.375rem 0.5rem', borderBottom: '1px solid var(--border-light)' }}>
                  <select
                    className="slot-select"
                    value={answers[key] || ''}
                    onChange={e => handleMatch(key, e.target.value)}
                    disabled={disabled}
                    style={{ width: 'auto', minWidth: 80 }}
                  >
                    <option value="">—</option>
                    {rightItems.map((right, ri) => (
                      <option key={ri} value={String(ri + 1)}>{ri + 1}) {right}</option>
                    ))}
                  </select>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================
// SingleChoiceInput — один вариант (radio)
// ============================================================

export function SingleChoiceInput({ value, onChange, disabled, choices }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Выберите один правильный ответ:</label>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', marginTop: 'var(--space-sm)' }}>
        {(choices || []).map((ch, idx) => (
          <label
            key={ch.id || idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-sm)',
              padding: '0.625rem 0.75rem',
              background: value === String(ch.id || idx) ? 'var(--color-primary-subtle)' : 'var(--bg-paper)',
              border: `1px solid ${value === String(ch.id || idx) ? 'var(--color-primary)' : 'var(--border-light)'}`,
              borderRadius: 'var(--radius-sm)',
              cursor: disabled ? 'default' : 'pointer',
              transition: 'all var(--duration-fast) var(--ease-smooth)',
            }}
          >
            <input
              type="radio"
              name="exam-single-choice"
              checked={value === String(ch.id || idx)}
              onChange={() => onChange(String(ch.id || idx))}
              disabled={disabled}
            />
            <span style={{ fontSize: 'var(--text-sm)' }}>{ch.text}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

// ============================================================
// MultiChoiceInput — несколько вариантов (checkbox)
// ============================================================

export function MultiChoiceInput({ value, onChange, disabled, choices }) {
  const selected = Array.isArray(value) ? value : (tryParse(value) || []);

  const toggle = (id) => {
    const idStr = String(id);
    const next = selected.includes(idStr)
      ? selected.filter(s => s !== idStr)
      : [...selected, idStr];
    onChange(JSON.stringify(next));
  };

  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Выберите все правильные ответы:</label>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', marginTop: 'var(--space-sm)' }}>
        {(choices || []).map((ch, idx) => {
          const idStr = String(ch.id || idx);
          const isSelected = selected.includes(idStr);
          return (
            <label
              key={ch.id || idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-sm)',
                padding: '0.625rem 0.75rem',
                background: isSelected ? 'var(--color-primary-subtle)' : 'var(--bg-paper)',
                border: `1px solid ${isSelected ? 'var(--color-primary)' : 'var(--border-light)'}`,
                borderRadius: 'var(--radius-sm)',
                cursor: disabled ? 'default' : 'pointer',
                transition: 'all var(--duration-fast) var(--ease-smooth)',
              }}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggle(ch.id || idx)}
                disabled={disabled}
              />
              <span style={{ fontSize: 'var(--text-sm)' }}>{ch.text}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================
// OrderedSequenceInput — упорядоченная последовательность
// ============================================================

export function OrderedSequenceInput({ value, onChange, disabled }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Упорядоченная последовательность (через пробел):</label>
      <input
        className="exam-answer-input mono"
        type="text"
        value={value || ''}
        onChange={e => onChange(e.target.value)}
        placeholder="Например: 3 1 4 2"
        disabled={disabled}
        autoComplete="off"
        style={{ maxWidth: 400, letterSpacing: '0.1em' }}
      />
    </div>
  );
}

// ============================================================
// ExtendedTextInput — развёрнутый текстовый ответ (часть 2)
// ============================================================

export function ExtendedTextInput({ value, onChange, disabled, label }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">{label || 'Развёрнутый ответ:'}</label>
      <textarea
        className="exam-answer-input"
        rows={8}
        value={value || ''}
        onChange={e => onChange(e.target.value)}
        placeholder="Введите ваш ответ..."
        disabled={disabled}
        style={{ resize: 'vertical', minHeight: 150 }}
      />
    </div>
  );
}

// ============================================================
// CodeInput — ввод программного кода
// ============================================================

export function CodeInput({ value, onChange, disabled, language = 'python' }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">
        Программный код ({language})
      </label>
      <textarea
        className="exam-answer-input"
        rows={12}
        value={value || ''}
        onChange={e => onChange(e.target.value)}
        placeholder={`# Введите ваш код на ${language}`}
        disabled={disabled}
        style={{
          resize: 'vertical',
          minHeight: 200,
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-sm)',
          lineHeight: 1.6,
          tabSize: 4,
          whiteSpace: 'pre',
        }}
        spellCheck={false}
      />
    </div>
  );
}

// ============================================================
// MathSolutionInput — математическое решение
// ============================================================

export function MathSolutionInput({ value, onChange, disabled }) {
  return (
    <div className="exam-answer-area">
      <label className="exam-answer-label">Математическое решение:</label>
      <textarea
        className="exam-answer-input"
        rows={10}
        value={value || ''}
        onChange={e => onChange(e.target.value)}
        placeholder="Запишите полное решение с обоснованиями..."
        disabled={disabled}
        style={{ resize: 'vertical', minHeight: 200 }}
      />
      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 4 }}>
        Оформляйте решение пошагово. Используйте ^ для степени, sqrt() для корня.
      </div>
    </div>
  );
}

// ============================================================
// ExamAnswerInput — dispatcher компонент
// ============================================================

export default function ExamAnswerInput({ answerType, value, onChange, disabled, config, choices }) {
  switch (answerType) {
    case 'short_number':
      return <ShortNumberInput value={value} onChange={onChange} disabled={disabled} />;
    case 'short_text':
      return <ShortTextInput value={value} onChange={onChange} disabled={disabled} />;
    case 'digit_sequence':
      return <DigitSequenceInput value={value} onChange={onChange} disabled={disabled} maxLength={config?.maxLength} />;
    case 'letter_sequence':
      return <LetterSequenceInput value={value} onChange={onChange} disabled={disabled} maxLength={config?.maxLength} />;
    case 'decimal_number':
      return <DecimalNumberInput value={value} onChange={onChange} disabled={disabled} />;
    case 'number_range':
      return <NumberRangeInput value={value} onChange={onChange} disabled={disabled} />;
    case 'multiple_numbers':
      return <MultipleNumbersInput value={value} onChange={onChange} disabled={disabled} />;
    case 'matching':
      return <MatchingInput value={value} onChange={onChange} disabled={disabled} config={config} />;
    case 'ordered_sequence':
      return <OrderedSequenceInput value={value} onChange={onChange} disabled={disabled} />;
    case 'single_choice':
      return <SingleChoiceInput value={value} onChange={onChange} disabled={disabled} choices={choices} />;
    case 'multi_choice':
      return <MultiChoiceInput value={value} onChange={onChange} disabled={disabled} choices={choices} />;
    case 'extended_text':
      return <ExtendedTextInput value={value} onChange={onChange} disabled={disabled} />;
    case 'essay':
      return <ExtendedTextInput value={value} onChange={onChange} disabled={disabled} label="Сочинение / эссе:" />;
    case 'math_solution':
      return <MathSolutionInput value={value} onChange={onChange} disabled={disabled} />;
    case 'code_solution':
      return <CodeInput value={value} onChange={onChange} disabled={disabled} language={config?.language} />;
    case 'code_file':
      return <CodeInput value={value} onChange={onChange} disabled={disabled} language={config?.language} />;
    default:
      return <ShortTextInput value={value} onChange={onChange} disabled={disabled} />;
  }
}

// ============================================================
// Helpers
// ============================================================

function tryParse(str) {
  try { return JSON.parse(str); } catch { return null; }
}
