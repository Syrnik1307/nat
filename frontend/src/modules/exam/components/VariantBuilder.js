/**
 * VariantBuilder — генерация и управление вариантами экзамена.
 *
 * Позволяет:
 * - Генерировать варианты автоматически
 * - Собирать вручную
 * - Назначать группе учеников
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Button, Badge } from '../../../shared/components';
import * as examService from '../services/examService';

export default function VariantBuilder({ blueprintId, onSelectBlueprint }) {
  const [variants, setVariants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [blueprints, setBlueprints] = useState([]);
  const [selectedBlueprint, setSelectedBlueprint] = useState(blueprintId);
  const [blueprint, setBlueprint] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [assigning, setAssigning] = useState(null); // variant id being assigned
  const [assignForm, setAssignForm] = useState({ group_ids: [], deadline: '' });
  const [groups, setGroups] = useState([]);

  useEffect(() => {
    examService.getBlueprints().then(data => {
      setBlueprints(data.results || data);
    }).catch(() => {});

    // Загрузка групп для назначения
    import('../../../apiService').then(m => {
      m.apiClient.get('schedule/groups/').then(res => {
        setGroups(res.data.results || res.data || []);
      }).catch(() => {});
    });
  }, []);

  useEffect(() => {
    if (selectedBlueprint) {
      examService.getBlueprint(selectedBlueprint).then(setBlueprint).catch(() => {});
    }
  }, [selectedBlueprint]);

  const fetchVariants = useCallback(async () => {
    if (!selectedBlueprint) return;
    setLoading(true);
    try {
      const data = await examService.getVariants({ blueprint: selectedBlueprint });
      setVariants(data.results || data);
    } catch (err) {
      console.error('Failed to load variants:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedBlueprint]);

  useEffect(() => {
    fetchVariants();
  }, [fetchVariants]);

  const handleBlueprintChange = (id) => {
    setSelectedBlueprint(id);
    if (onSelectBlueprint) onSelectBlueprint(id);
  };

  const handleGenerate = async (count = 1) => {
    setGenerating(true);
    try {
      await examService.generateVariants({
        blueprint: selectedBlueprint,
        count,
      });
      fetchVariants();
    } catch (err) {
      alert('Ошибка генерации: ' + (err.response?.data?.detail || err.message));
    } finally {
      setGenerating(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Удалить вариант?')) return;
    try {
      await examService.deleteVariant(id);
      fetchVariants();
    } catch (err) {
      console.error('Failed to delete variant:', err);
    }
  };

  const handleAssign = async (variantId) => {
    try {
      await examService.assignVariant(variantId, assignForm);
      setAssigning(null);
      setAssignForm({ group_ids: [], deadline: '' });
      fetchVariants();
    } catch (err) {
      alert('Ошибка назначения: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (!selectedBlueprint) {
    return (
      <div className="exam-empty-state">
        <div className="exam-empty-state-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
          </svg>
        </div>
        <h3 className="exam-empty-state-title">Выберите шаблон</h3>
        <p className="exam-empty-state-desc">
          Для генерации вариантов сначала выберите шаблон экзамена.
        </p>
        <select
          className="blueprint-filter-select"
          value=""
          onChange={e => handleBlueprintChange(Number(e.target.value))}
        >
          <option value="">Выберите шаблон...</option>
          {blueprints.map(bp => (
            <option key={bp.id} value={bp.id}>{bp.title}</option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className="variant-builder animate-content">
      <div className="variant-builder-toolbar">
        <div className="task-bank-filters">
          <select
            className="blueprint-filter-select"
            value={selectedBlueprint || ''}
            onChange={e => handleBlueprintChange(Number(e.target.value))}
          >
            {blueprints.map(bp => (
              <option key={bp.id} value={bp.id}>{bp.title}</option>
            ))}
          </select>

          {blueprint && (
            <span style={{
              fontSize: 'var(--text-sm)',
              color: 'var(--text-muted)',
            }}>
              {blueprint.task_slots?.length || 0} заданий,
              {' '}{blueprint.duration_minutes} мин.
            </span>
          )}
        </div>

        <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
          <Button
            variant="secondary"
            onClick={() => handleGenerate(1)}
            disabled={generating}
          >
            {generating ? 'Генерация...' : 'Сгенерировать 1 вариант'}
          </Button>
          <Button
            variant="primary"
            onClick={() => handleGenerate(5)}
            disabled={generating}
          >
            {generating ? 'Генерация...' : 'Сгенерировать 5 вариантов'}
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="exam-skeleton-cards">
          {[1, 2, 3].map(i => (
            <div key={i} className="exam-skeleton-card skeleton" />
          ))}
        </div>
      ) : variants.length === 0 ? (
        <div className="exam-empty-state">
          <div className="exam-empty-state-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
            </svg>
          </div>
          <h3 className="exam-empty-state-title">Нет вариантов</h3>
          <p className="exam-empty-state-desc">
            Сгенерируйте варианты из банка заданий.
            Убедитесь, что в банке есть задания для каждого номера.
          </p>
        </div>
      ) : (
        <div className="variant-list">
          {variants.map(v => (
            <div key={v.id} className="variant-card">
              <div className="variant-card-header">
                <h3 className="variant-card-name">
                  {v.title || `Вариант ${v.variant_number}`}
                </h3>
                <div style={{ display: 'flex', gap: 'var(--space-xs)', alignItems: 'center' }}>
                  {v.is_manual ? (
                    <Badge variant="muted">Ручной</Badge>
                  ) : (
                    <Badge variant="primary">Авто</Badge>
                  )}
                  {v.homework && (
                    <Badge variant="success">Назначен</Badge>
                  )}
                </div>
              </div>

              <div className="variant-card-meta">
                <span>{v.task_count || v.variant_tasks?.length || 0} заданий</span>
                <span>Создан: {new Date(v.created_at).toLocaleDateString('ru')}</span>
              </div>

              {/* Пилюли номеров заданий */}
              {v.variant_tasks && (
                <div className="variant-task-pills">
                  {(blueprint?.task_slots || []).map(slot => {
                    const filled = v.variant_tasks.some(
                      vt => vt.task_number === slot.task_number
                    );
                    return (
                      <span
                        key={slot.task_number}
                        className={`variant-task-pill ${filled ? 'filled' : 'empty'}`}
                      >
                        {slot.task_number}
                      </span>
                    );
                  })}
                </div>
              )}

              {/* Назначение */}
              {assigning === v.id ? (
                <div style={{
                  marginTop: 'var(--space-md)',
                  padding: 'var(--space-md)',
                  background: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-light)',
                }}>
                  <div style={{ marginBottom: 'var(--space-sm)' }}>
                    <label className="blueprint-editor-label">Группы</label>
                    <select
                      className="blueprint-editor-input"
                      multiple
                      size={Math.min(groups.length, 4)}
                      value={assignForm.group_ids.map(String)}
                      onChange={e => {
                        const selected = Array.from(e.target.selectedOptions, o => Number(o.value));
                        setAssignForm(prev => ({ ...prev, group_ids: selected }));
                      }}
                      style={{ width: '100%' }}
                    >
                      {groups.map(g => (
                        <option key={g.id} value={g.id}>{g.name}</option>
                      ))}
                    </select>
                  </div>
                  <div style={{ marginBottom: 'var(--space-sm)' }}>
                    <label className="blueprint-editor-label">Дедлайн</label>
                    <input
                      className="blueprint-editor-input"
                      type="datetime-local"
                      value={assignForm.deadline}
                      onChange={e => setAssignForm(prev => ({
                        ...prev, deadline: e.target.value,
                      }))}
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 'var(--space-xs)', justifyContent: 'flex-end' }}>
                    <Button size="sm" variant="ghost" onClick={() => setAssigning(null)}>Отмена</Button>
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => handleAssign(v.id)}
                      disabled={assignForm.group_ids.length === 0}
                    >
                      Назначить
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="variant-card-actions">
                  {!v.homework && (
                    <Button size="sm" variant="primary" onClick={() => setAssigning(v.id)}>
                      Назначить группе
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" onClick={() => handleDelete(v.id)}>
                    Удалить
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
