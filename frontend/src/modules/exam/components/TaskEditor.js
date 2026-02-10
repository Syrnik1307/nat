/**
 * TaskEditor — создание/редактирование задания в банке.
 *
 * Привязывает задание к номеру в КИМ (ExamTaskSlot).
 * Использует тот же формат config, что и homework Question.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../../../shared/components';
import * as examService from '../services/examService';
import { ANSWER_TYPE_LABELS } from '../services/examService';

const DIFFICULTY_OPTIONS = [
  { value: 'easy', label: 'Лёгкое' },
  { value: 'medium', label: 'Среднее' },
  { value: 'hard', label: 'Сложное' },
];

const SOURCE_OPTIONS = [
  { value: 'fipi', label: 'ФИПИ (официальный банк)' },
  { value: 'reshu_ege', label: 'Решу ЕГЭ / Решу ОГЭ' },
  { value: 'author', label: 'Авторское задание' },
  { value: 'textbook', label: 'Учебник' },
  { value: 'olympiad', label: 'Олимпиадное' },
  { value: 'other', label: 'Другой источник' },
];

export default function TaskEditor({ taskId, blueprintId, slots, onClose, onSaved }) {
  const isNew = !taskId;

  const [form, setForm] = useState({
    task_number: slots.length > 0 ? slots[0].task_number : 1,
    difficulty: 'medium',
    source: 'author',
    source_reference: '',
    tags: [],
    // Question fields
    prompt: '',
    correct_answer: '',
    points: 1,
    explanation: '',
    // Choices for single/multi choice
    choices: [],
    // Matching pairs
    matching_pairs: [],
  });

  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [tagInput, setTagInput] = useState('');

  // Текущий слот (по выбранному номеру задания)
  const currentSlot = slots.find(s => s.task_number === Number(form.task_number));
  const answerType = currentSlot?.answer_type || 'short_number';

  // Загрузка данных для редактирования
  useEffect(() => {
    if (!isNew) {
      (async () => {
        try {
          const data = await examService.getTask(taskId);
          setForm({
            task_number: data.task_number || 1,
            difficulty: data.difficulty || 'medium',
            source: data.source || 'author',
            source_reference: data.source_reference || '',
            tags: data.tags || [],
            prompt: data.question?.prompt || data.question_prompt || '',
            correct_answer: data.question?.config?.correctAnswer || '',
            points: data.question?.points || currentSlot?.max_points || 1,
            explanation: data.question?.explanation || '',
            choices: data.question?.choices || [],
            matching_pairs: data.question?.config?.pairs || [],
          });
        } catch {
          setError('Не удалось загрузить задание');
        } finally {
          setLoading(false);
        }
      })();
    }
  }, [taskId, isNew]);

  // Обновить баллы при смене слота
  useEffect(() => {
    if (currentSlot) {
      setForm(prev => ({ ...prev, points: currentSlot.max_points }));
    }
  }, [form.task_number, currentSlot?.max_points]);

  const handleChange = useCallback((field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  }, []);

  const addTag = () => {
    const tag = tagInput.trim();
    if (tag && !form.tags.includes(tag)) {
      handleChange('tags', [...form.tags, tag]);
    }
    setTagInput('');
  };

  const removeTag = (tag) => {
    handleChange('tags', form.tags.filter(t => t !== tag));
  };

  // Choices management
  const addChoice = () => {
    handleChange('choices', [
      ...form.choices,
      { text: '', is_correct: false },
    ]);
  };

  const updateChoice = (idx, field, value) => {
    const copy = [...form.choices];
    if (field === 'is_correct' && answerType === 'single_choice') {
      // Single choice — снять все остальные
      copy.forEach((c, i) => { c.is_correct = i === idx ? value : false; });
    } else {
      copy[idx] = { ...copy[idx], [field]: value };
    }
    handleChange('choices', copy);
  };

  const removeChoice = (idx) => {
    handleChange('choices', form.choices.filter((_, i) => i !== idx));
  };

  // Matching pairs management
  const addPair = () => {
    handleChange('matching_pairs', [
      ...form.matching_pairs,
      { left: '', right: '' },
    ]);
  };

  const updatePair = (idx, side, value) => {
    const copy = [...form.matching_pairs];
    copy[idx] = { ...copy[idx], [side]: value };
    handleChange('matching_pairs', copy);
  };

  const removePair = (idx) => {
    handleChange('matching_pairs', form.matching_pairs.filter((_, i) => i !== idx));
  };

  // Save
  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      // Строим config на основе answer_type
      const config = {};
      if (['short_number', 'short_text', 'digit_sequence', 'letter_sequence',
           'decimal_number', 'number_range', 'multiple_numbers'].includes(answerType)) {
        config.correctAnswer = form.correct_answer;
        config.answer_format = answerType;
      } else if (answerType === 'matching') {
        config.pairs = form.matching_pairs;
      } else if (['single_choice', 'multi_choice'].includes(answerType)) {
        // Choices идут отдельно
      } else if (['extended_text', 'essay', 'math_solution'].includes(answerType)) {
        config.answer_format = answerType;
        if (form.correct_answer) config.correctAnswer = form.correct_answer;
      } else if (answerType === 'code_solution') {
        config.answer_format = 'code_solution';
        config.language = 'python';
        if (form.correct_answer) config.correctAnswer = form.correct_answer;
      }

      // Маппинг answer_type → question_type
      const questionType = examService.ANSWER_TYPE_TO_QUESTION_TYPE[answerType] || 'TEXT';

      const payload = {
        blueprint: blueprintId,
        task_number: Number(form.task_number),
        difficulty: form.difficulty,
        source: form.source,
        source_reference: form.source_reference,
        tags: form.tags,
        question_data: {
          prompt: form.prompt,
          question_type: questionType,
          points: form.points,
          explanation: form.explanation,
          config: config,
          choices: ['single_choice', 'multi_choice'].includes(answerType) ? form.choices : [],
        },
      };

      if (isNew) {
        await examService.createTask(payload);
      } else {
        await examService.updateTask(taskId, payload);
      }

      onSaved();
    } catch (err) {
      const msg = err.response?.data;
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg) || 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="blueprint-editor">
        <div className="skeleton" style={{ height: 400, borderRadius: 'var(--radius-md)' }} />
      </div>
    );
  }

  return (
    <div className="blueprint-editor animate-content">
      <div className="blueprint-editor-header">
        <h2 className="blueprint-editor-title">
          {isNew ? 'Новое задание' : 'Редактирование задания'}
        </h2>
        <Button variant="ghost" onClick={onClose}>Закрыть</Button>
      </div>

      {error && (
        <div style={{
          padding: '0.75rem 1rem',
          background: 'rgba(244,63,94,0.08)',
          color: 'var(--color-error)',
          borderRadius: 'var(--radius-sm)',
          fontSize: 'var(--text-sm)',
          marginBottom: 'var(--space-md)',
        }}>
          {error}
        </div>
      )}

      {/* Метаданные задания */}
      <div className="blueprint-editor-form">
        <div className="blueprint-editor-field">
          <label className="blueprint-editor-label">Номер задания в КИМ</label>
          <select
            className="blueprint-editor-input"
            value={form.task_number}
            onChange={e => handleChange('task_number', e.target.value)}
          >
            {slots.map(s => (
              <option key={s.task_number} value={s.task_number}>
                #{s.task_number} — {s.title || ANSWER_TYPE_LABELS[s.answer_type]}
                {' '}({s.max_points} б.)
              </option>
            ))}
          </select>
        </div>

        <div className="blueprint-editor-field">
          <label className="blueprint-editor-label">Сложность</label>
          <select
            className="blueprint-editor-input"
            value={form.difficulty}
            onChange={e => handleChange('difficulty', e.target.value)}
          >
            {DIFFICULTY_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <div className="blueprint-editor-field">
          <label className="blueprint-editor-label">Источник</label>
          <select
            className="blueprint-editor-input"
            value={form.source}
            onChange={e => handleChange('source', e.target.value)}
          >
            {SOURCE_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <div className="blueprint-editor-field">
          <label className="blueprint-editor-label">Ссылка / номер из банка</label>
          <input
            className="blueprint-editor-input"
            value={form.source_reference}
            onChange={e => handleChange('source_reference', e.target.value)}
            placeholder="Например: ФИПИ #12345"
          />
        </div>

        {/* Текст задания */}
        <div className="blueprint-editor-field full-width">
          <label className="blueprint-editor-label">Текст задания</label>
          <textarea
            className="blueprint-editor-input"
            rows={5}
            value={form.prompt}
            onChange={e => handleChange('prompt', e.target.value)}
            placeholder="Условие задачи..."
          />
        </div>

        {/* Тип-зависимый ввод */}
        {renderAnswerConfig()}

        {/* Пояснение */}
        <div className="blueprint-editor-field full-width">
          <label className="blueprint-editor-label">Пояснение (для ученика после проверки)</label>
          <textarea
            className="blueprint-editor-input"
            rows={2}
            value={form.explanation}
            onChange={e => handleChange('explanation', e.target.value)}
            placeholder="Разбор решения (необязательно)"
          />
        </div>

        {/* Теги */}
        <div className="blueprint-editor-field full-width">
          <label className="blueprint-editor-label">Теги</label>
          <div style={{ display: 'flex', gap: 'var(--space-xs)', flexWrap: 'wrap', marginBottom: 'var(--space-xs)' }}>
            {form.tags.map(tag => (
              <span key={tag} style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                padding: '0.125rem 0.5rem',
                background: 'var(--color-primary-subtle)',
                color: 'var(--color-primary)',
                borderRadius: 'var(--radius-full)',
                fontSize: 'var(--text-xs)',
                fontWeight: 500,
              }}>
                {tag}
                <button
                  onClick={() => removeTag(tag)}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'inherit', padding: 0, fontSize: '0.8em',
                  }}
                >
                  x
                </button>
              </span>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-xs)' }}>
            <input
              className="blueprint-editor-input"
              value={tagInput}
              onChange={e => setTagInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addTag())}
              placeholder="Добавить тег..."
              style={{ flex: 1 }}
            />
            <Button size="sm" variant="secondary" onClick={addTag}>+</Button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="blueprint-editor-footer">
        <Button variant="ghost" onClick={onClose} disabled={saving}>Отмена</Button>
        <Button variant="primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Сохранение...' : isNew ? 'Создать' : 'Сохранить'}
        </Button>
      </div>
    </div>
  );

  // Рендер конфигурации ответа в зависимости от answer_type
  function renderAnswerConfig() {
    switch (answerType) {
      case 'short_number':
      case 'decimal_number':
        return (
          <div className="blueprint-editor-field full-width">
            <label className="blueprint-editor-label">Правильный ответ (число)</label>
            <input
              className="blueprint-editor-input"
              type="text"
              value={form.correct_answer}
              onChange={e => handleChange('correct_answer', e.target.value)}
              placeholder="Например: 42"
              style={{ fontFamily: 'var(--font-mono)', maxWidth: 200 }}
            />
          </div>
        );

      case 'short_text':
        return (
          <div className="blueprint-editor-field full-width">
            <label className="blueprint-editor-label">Правильный ответ (текст)</label>
            <input
              className="blueprint-editor-input"
              value={form.correct_answer}
              onChange={e => handleChange('correct_answer', e.target.value)}
              placeholder="Ответ"
              style={{ maxWidth: 400 }}
            />
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              Регистр не учитывается при проверке
            </span>
          </div>
        );

      case 'digit_sequence':
        return (
          <div className="blueprint-editor-field full-width">
            <label className="blueprint-editor-label">Правильная последовательность цифр</label>
            <input
              className="blueprint-editor-input"
              value={form.correct_answer}
              onChange={e => handleChange('correct_answer', e.target.value.replace(/[^\d]/g, ''))}
              placeholder="Например: 2413"
              style={{ fontFamily: 'var(--font-mono)', maxWidth: 200, letterSpacing: '0.15em' }}
            />
          </div>
        );

      case 'letter_sequence':
        return (
          <div className="blueprint-editor-field full-width">
            <label className="blueprint-editor-label">Правильная последовательность букв</label>
            <input
              className="blueprint-editor-input"
              value={form.correct_answer}
              onChange={e => handleChange('correct_answer', e.target.value.toUpperCase().replace(/[^А-ЯЁABCDE]/g, ''))}
              placeholder="Например: БВГА"
              style={{ fontFamily: 'var(--font-mono)', maxWidth: 200, letterSpacing: '0.15em' }}
            />
          </div>
        );

      case 'number_range':
      case 'multiple_numbers':
        return (
          <div className="blueprint-editor-field full-width">
            <label className="blueprint-editor-label">
              {answerType === 'number_range' ? 'Правильный ответ (диапазон, через дефис)' : 'Правильные числа (через пробел)'}
            </label>
            <input
              className="blueprint-editor-input"
              value={form.correct_answer}
              onChange={e => handleChange('correct_answer', e.target.value)}
              placeholder={answerType === 'number_range' ? '5-10' : '3 7 12'}
              style={{ fontFamily: 'var(--font-mono)', maxWidth: 300 }}
            />
          </div>
        );

      case 'single_choice':
      case 'multi_choice':
        return (
          <div className="blueprint-editor-field full-width">
            <label className="blueprint-editor-label">
              Варианты ответа
              <span style={{ fontWeight: 400, color: 'var(--text-muted)', marginLeft: 8, fontSize: 'var(--text-xs)' }}>
                Отметьте правильный{answerType === 'multi_choice' ? '(-ые)' : ''}
              </span>
            </label>
            {form.choices.map((ch, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', marginBottom: 'var(--space-xs)' }}>
                <input
                  type={answerType === 'single_choice' ? 'radio' : 'checkbox'}
                  checked={ch.is_correct}
                  onChange={e => updateChoice(idx, 'is_correct', e.target.checked)}
                  name="correct_choice"
                />
                <input
                  className="blueprint-editor-input"
                  value={ch.text}
                  onChange={e => updateChoice(idx, 'text', e.target.value)}
                  placeholder={`Вариант ${idx + 1}`}
                  style={{ flex: 1 }}
                />
                <button
                  className="slot-remove-btn"
                  onClick={() => removeChoice(idx)}
                  title="Удалить"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            ))}
            <Button size="sm" variant="secondary" onClick={addChoice}>
              Добавить вариант
            </Button>
          </div>
        );

      case 'matching':
        return (
          <div className="blueprint-editor-field full-width">
            <label className="blueprint-editor-label">Пары для сопоставления</label>
            {form.matching_pairs.map((pair, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', marginBottom: 'var(--space-xs)' }}>
                <input
                  className="blueprint-editor-input"
                  value={pair.left}
                  onChange={e => updatePair(idx, 'left', e.target.value)}
                  placeholder="Левая часть"
                  style={{ flex: 1 }}
                />
                <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>
                <input
                  className="blueprint-editor-input"
                  value={pair.right}
                  onChange={e => updatePair(idx, 'right', e.target.value)}
                  placeholder="Правая часть"
                  style={{ flex: 1 }}
                />
                <button className="slot-remove-btn" onClick={() => removePair(idx)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            ))}
            <Button size="sm" variant="secondary" onClick={addPair}>
              Добавить пару
            </Button>
          </div>
        );

      case 'extended_text':
      case 'essay':
      case 'math_solution':
        return (
          <div className="blueprint-editor-field full-width">
            <label className="blueprint-editor-label">Эталонный ответ (для проверяющего)</label>
            <textarea
              className="blueprint-editor-input"
              rows={4}
              value={form.correct_answer}
              onChange={e => handleChange('correct_answer', e.target.value)}
              placeholder="Развёрнутый эталонный ответ (необязательно, используется для AI-проверки)"
            />
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              Этот тип проверяется вручную или через AI
            </span>
          </div>
        );

      case 'code_solution':
      case 'code_file':
        return (
          <div className="blueprint-editor-field full-width">
            <label className="blueprint-editor-label">Эталонное решение</label>
            <textarea
              className="blueprint-editor-input"
              rows={6}
              value={form.correct_answer}
              onChange={e => handleChange('correct_answer', e.target.value)}
              placeholder="# Эталонный код решения"
              style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)' }}
            />
          </div>
        );

      case 'ordered_sequence':
        return (
          <div className="blueprint-editor-field full-width">
            <label className="blueprint-editor-label">Правильный порядок (через пробел)</label>
            <input
              className="blueprint-editor-input"
              value={form.correct_answer}
              onChange={e => handleChange('correct_answer', e.target.value)}
              placeholder="Например: 3 1 4 2"
              style={{ fontFamily: 'var(--font-mono)', maxWidth: 300 }}
            />
          </div>
        );

      default:
        return null;
    }
  }
}
