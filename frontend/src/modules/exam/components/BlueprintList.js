/**
 * BlueprintList — список шаблонов экзаменов с фильтрами.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Button, Badge } from '../../../shared/components';
import * as examService from '../services/examService';

export default function BlueprintList({ selectedId, onSelect, onEdit, onCreate }) {
  const [blueprints, setBlueprints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [examType, setExamType] = useState('');
  const [yearFilter, setYearFilter] = useState('');

  const fetchBlueprints = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (examType) params.exam_type = examType;
      if (yearFilter) params.year = yearFilter;
      const data = await examService.getBlueprints(params);
      setBlueprints(data.results || data);
    } catch (err) {
      console.error('Failed to load blueprints:', err);
    } finally {
      setLoading(false);
    }
  }, [examType, yearFilter]);

  useEffect(() => {
    fetchBlueprints();
  }, [fetchBlueprints]);

  const handleDuplicate = async (id, e) => {
    e.stopPropagation();
    try {
      await examService.duplicateBlueprint(id);
      fetchBlueprints();
    } catch (err) {
      console.error('Failed to duplicate blueprint:', err);
    }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Удалить шаблон? Это действие нельзя отменить.')) return;
    try {
      await examService.deleteBlueprint(id);
      if (selectedId === id) onSelect(null);
      fetchBlueprints();
    } catch (err) {
      console.error('Failed to delete blueprint:', err);
    }
  };

  if (loading) {
    return (
      <div className="exam-skeleton-cards">
        {[1, 2, 3].map(i => (
          <div key={i} className="exam-skeleton-card skeleton" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="blueprint-list-toolbar">
        <div className="blueprint-list-filters">
          <select
            className="blueprint-filter-select"
            value={examType}
            onChange={e => setExamType(e.target.value)}
          >
            <option value="">Все типы</option>
            <option value="ege">ЕГЭ</option>
            <option value="oge">ОГЭ</option>
          </select>
          <select
            className="blueprint-filter-select"
            value={yearFilter}
            onChange={e => setYearFilter(e.target.value)}
          >
            <option value="">Все годы</option>
            <option value="2026">2026</option>
            <option value="2025">2025</option>
            <option value="2024">2024</option>
          </select>
        </div>
        <Button variant="primary" onClick={onCreate}>
          Создать шаблон
        </Button>
      </div>

      {blueprints.length === 0 ? (
        <div className="exam-empty-state">
          <div className="exam-empty-state-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14,2 14,8 20,8" />
              <line x1="12" y1="18" x2="12" y2="12" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
          </div>
          <h3 className="exam-empty-state-title">Нет шаблонов</h3>
          <p className="exam-empty-state-desc">
            Создайте первый шаблон экзамена с нужной структурой заданий и шкалой оценивания.
          </p>
          <Button variant="primary" onClick={onCreate}>
            Создать шаблон
          </Button>
        </div>
      ) : (
        <div className="blueprint-grid">
          {blueprints.map(bp => (
            <div
              key={bp.id}
              className={`blueprint-card ${selectedId === bp.id ? 'selected' : ''}`}
              onClick={() => onSelect(bp.id)}
            >
              <div className="blueprint-card-header">
                <h3 className="blueprint-card-name">{bp.title}</h3>
                <div className="blueprint-card-badges">
                  {bp.exam_type && (
                    <Badge variant={bp.exam_type === 'ege' ? 'primary' : 'warning'}>
                      {bp.exam_type === 'ege' ? 'ЕГЭ' : 'ОГЭ'}
                    </Badge>
                  )}
                  {!bp.is_active && <Badge variant="muted">Черновик</Badge>}
                </div>
              </div>

              <div className="blueprint-card-subject">{bp.subject_name}</div>

              <div className="blueprint-card-meta">
                <span>{bp.task_slots_count} заданий</span>
                <span>{bp.total_primary_score} баллов</span>
                <span>{bp.duration_minutes} мин.</span>
                {bp.year && <span>{bp.year}</span>}
              </div>

              <div className="blueprint-card-actions">
                <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); onEdit(bp.id); }}>
                  Редактировать
                </Button>
                <Button size="sm" variant="ghost" onClick={(e) => handleDuplicate(bp.id, e)}>
                  Дублировать
                </Button>
                <Button size="sm" variant="ghost" onClick={(e) => handleDelete(bp.id, e)}>
                  Удалить
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
