/**
 * BlueprintEditor — создание/редактирование шаблона экзамена.
 *
 * Включает:
 * - Основные поля (название, предмет, год, длительность)
 * - Таблицу слотов заданий (номер, тип ответа, макс. баллы)
 * - Редактор ФИПИ шкалы (первичный → тестовый балл)
 * - Пороги оценок
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../../../shared/components';
import * as examService from '../services/examService';
import { ANSWER_TYPE_LABELS } from '../services/examService';

const EMPTY_SLOT = {
  task_number: '',
  title: '',
  answer_type: 'short_number',
  max_points: 1,
  description: '',
  answer_config: {},
};

export default function BlueprintEditor({ blueprintId, onClose, onSaved }) {
  const isNew = !blueprintId;

  const [form, setForm] = useState({
    title: '',
    subject: '',
    year: 2026,
    duration_minutes: 235,
    description: '',
    is_active: false,
    is_public: true,
    score_scale: {},
    grade_thresholds: { 5: 0, 4: 0, 3: 0 },
  });

  const [slots, setSlots] = useState([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(!isNew);
  const [error, setError] = useState(null);
  const [subjects, setSubjects] = useState([]);

  // Загрузка данных для редактирования
  useEffect(() => {
    if (!isNew) {
      (async () => {
        try {
          const data = await examService.getBlueprint(blueprintId);
          setForm({
            title: data.title || '',
            subject: data.subject || '',
            year: data.year || 2026,
            duration_minutes: data.duration_minutes || 235,
            description: data.description || '',
            is_active: data.is_active || false,
            is_public: data.is_public ?? true,
            score_scale: data.score_scale || {},
            grade_thresholds: data.grade_thresholds || { 5: 0, 4: 0, 3: 0 },
          });
          setSlots(data.task_slots || []);
        } catch (err) {
          setError('Не удалось загрузить шаблон');
        } finally {
          setLoading(false);
        }
      })();
    }
  }, [blueprintId, isNew]);

  // Загрузка списка предметов (knowledge_map)
  useEffect(() => {
    (async () => {
      try {
        const res = await import('../../../apiService').then(m =>
          m.apiClient.get('knowledge-map/subjects/')
        );
        setSubjects(res.data.results || res.data || []);
      } catch {
        // Предметы не загрузились — покажем текстовый инпут
      }
    })();
  }, []);

  const handleFieldChange = useCallback((field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  }, []);

  // --- Slots management ---

  const addSlot = () => {
    const nextNum = slots.length > 0
      ? Math.max(...slots.map(s => Number(s.task_number) || 0)) + 1
      : 1;
    setSlots(prev => [
      ...prev,
      { ...EMPTY_SLOT, task_number: nextNum, order: prev.length },
    ]);
  };

  const updateSlot = (index, field, value) => {
    setSlots(prev => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  const removeSlot = (index) => {
    setSlots(prev => prev.filter((_, i) => i !== index));
  };

  // --- Score scale ---

  const updateScaleEntry = (primary, testValue) => {
    setForm(prev => ({
      ...prev,
      score_scale: {
        ...prev.score_scale,
        [String(primary)]: Number(testValue) || 0,
      },
    }));
  };

  const totalPrimary = slots.reduce((sum, s) => sum + (Number(s.max_points) || 0), 0);

  // --- Save ---

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      let bp;
      const payload = {
        ...form,
        total_primary_score: totalPrimary,
        slots: slots.map((s, i) => ({
          ...s,
          order: i,
          task_number: Number(s.task_number),
          max_points: Number(s.max_points),
        })),
      };

      if (isNew) {
        bp = await examService.createBlueprint(payload);
      } else {
        bp = await examService.updateBlueprint(blueprintId, payload);
      }

      // Сохраняем слоты отдельно, если бэкенд требует
      if (bp.id && slots.length > 0) {
        try {
          await examService.updateBlueprintSlots(
            bp.id,
            slots.map((s, i) => ({
              id: s.id || undefined,
              task_number: Number(s.task_number),
              title: s.title || '',
              answer_type: s.answer_type,
              max_points: Number(s.max_points),
              description: s.description || '',
              answer_config: s.answer_config || {},
              order: i,
              topic: s.topic || null,
            }))
          );
        } catch {
          // Слоты могут быть сохранены через вложенный сериализатор
        }
      }

      onSaved(bp);
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
          {isNew ? 'Новый шаблон экзамена' : 'Редактирование шаблона'}
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

      {/* Основные поля */}
      <div className="blueprint-editor-form">
        <div className="blueprint-editor-field full-width">
          <label className="blueprint-editor-label">Название</label>
          <input
            className="blueprint-editor-input"
            value={form.title}
            onChange={e => handleFieldChange('title', e.target.value)}
            placeholder="Например: ЕГЭ Информатика 2026"
          />
        </div>

        <div className="blueprint-editor-field">
          <label className="blueprint-editor-label">Предмет</label>
          {subjects.length > 0 ? (
            <select
              className="blueprint-editor-input"
              value={form.subject}
              onChange={e => handleFieldChange('subject', e.target.value)}
            >
              <option value="">Выберите предмет</option>
              {subjects.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          ) : (
            <input
              className="blueprint-editor-input"
              type="number"
              value={form.subject}
              onChange={e => handleFieldChange('subject', e.target.value)}
              placeholder="ID предмета"
            />
          )}
        </div>

        <div className="blueprint-editor-field">
          <label className="blueprint-editor-label">Год</label>
          <input
            className="blueprint-editor-input"
            type="number"
            value={form.year}
            onChange={e => handleFieldChange('year', Number(e.target.value))}
          />
        </div>

        <div className="blueprint-editor-field">
          <label className="blueprint-editor-label">Длительность (мин.)</label>
          <input
            className="blueprint-editor-input"
            type="number"
            value={form.duration_minutes}
            onChange={e => handleFieldChange('duration_minutes', Number(e.target.value))}
          />
        </div>

        <div className="blueprint-editor-field">
          <label className="blueprint-editor-label">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={e => handleFieldChange('is_active', e.target.checked)}
              style={{ marginRight: 6 }}
            />
            Активен
          </label>
        </div>

        <div className="blueprint-editor-field full-width">
          <label className="blueprint-editor-label">Описание</label>
          <textarea
            className="blueprint-editor-input"
            rows={2}
            value={form.description}
            onChange={e => handleFieldChange('description', e.target.value)}
            placeholder="Описание (необязательно)"
          />
        </div>
      </div>

      {/* Таблица слотов */}
      <div className="slots-section">
        <div className="slots-section-header">
          <h3 className="slots-section-title">Задания ({slots.length})</h3>
          <Button size="sm" variant="secondary" onClick={addSlot}>
            Добавить задание
          </Button>
        </div>

        {slots.length > 0 && (
          <table className="slots-table">
            <thead>
              <tr>
                <th style={{ width: 60 }}>#</th>
                <th>Название</th>
                <th style={{ width: 220 }}>Тип ответа</th>
                <th style={{ width: 80 }}>Баллы</th>
                <th style={{ width: 40 }} />
              </tr>
            </thead>
            <tbody>
              {slots.map((slot, idx) => (
                <tr key={slot.id || idx}>
                  <td>
                    <input
                      className="slot-input"
                      type="number"
                      min={1}
                      value={slot.task_number}
                      onChange={e => updateSlot(idx, 'task_number', e.target.value)}
                      style={{ width: 50, textAlign: 'center' }}
                    />
                  </td>
                  <td>
                    <input
                      className="slot-input"
                      value={slot.title || ''}
                      onChange={e => updateSlot(idx, 'title', e.target.value)}
                      placeholder={`Задание ${slot.task_number}`}
                    />
                  </td>
                  <td>
                    <select
                      className="slot-select"
                      value={slot.answer_type}
                      onChange={e => updateSlot(idx, 'answer_type', e.target.value)}
                    >
                      {Object.entries(ANSWER_TYPE_LABELS).map(([key, label]) => (
                        <option key={key} value={key}>{label}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      className="slot-input"
                      type="number"
                      min={0}
                      value={slot.max_points}
                      onChange={e => updateSlot(idx, 'max_points', e.target.value)}
                      style={{ width: 60, textAlign: 'center' }}
                    />
                  </td>
                  <td>
                    <button
                      className="slot-remove-btn"
                      onClick={() => removeSlot(idx)}
                      title="Удалить"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div style={{
          marginTop: 'var(--space-sm)',
          fontSize: 'var(--text-sm)',
          color: 'var(--text-muted)',
        }}>
          Итого первичных баллов: <strong style={{ color: 'var(--text-main)' }}>{totalPrimary}</strong>
        </div>
      </div>

      {/* ФИПИ Шкала */}
      <div className="scale-editor">
        <h3 className="scale-editor-title">Шкала перевода (первичный → тестовый)</h3>
        <div className="scale-entries">
          {Array.from({ length: totalPrimary + 1 }, (_, i) => (
            <div key={i} className="scale-entry">
              <span>{i} =</span>
              <input
                className="scale-entry-input"
                type="number"
                min={0}
                max={100}
                value={form.score_scale[String(i)] ?? ''}
                onChange={e => updateScaleEntry(i, e.target.value)}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Пороги оценок */}
      <div className="scale-editor" style={{ marginTop: 'var(--space-md)' }}>
        <h3 className="scale-editor-title">Пороги оценок (тестовые баллы)</h3>
        <div style={{ display: 'flex', gap: 'var(--space-lg)' }}>
          {[5, 4, 3].map(grade => (
            <div key={grade} className="blueprint-editor-field">
              <label className="blueprint-editor-label">Оценка {grade}</label>
              <input
                className="blueprint-editor-input"
                type="number"
                min={0}
                style={{ width: 80 }}
                value={form.grade_thresholds[grade] ?? ''}
                onChange={e => handleFieldChange('grade_thresholds', {
                  ...form.grade_thresholds,
                  [grade]: Number(e.target.value) || 0,
                })}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="blueprint-editor-footer">
        <Button variant="ghost" onClick={onClose} disabled={saving}>
          Отмена
        </Button>
        <Button variant="primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Сохранение...' : isNew ? 'Создать' : 'Сохранить'}
        </Button>
      </div>
    </div>
  );
}
