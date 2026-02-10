/**
 * TaskBank — банк заданий для экзаменов.
 *
 * Учитель добавляет конкретные задания, привязанные к номеру в КИМ.
 * Задания потом используются при генерации вариантов.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Button, Badge } from '../../../shared/components';
import * as examService from '../services/examService';
import { ANSWER_TYPE_LABELS } from '../services/examService';
import TaskEditor from './TaskEditor';

const DIFFICULTY_LABELS = {
  easy: 'Лёгкое',
  medium: 'Среднее',
  hard: 'Сложное',
};

const SOURCE_LABELS = {
  fipi: 'ФИПИ',
  reshu_ege: 'Решу ЕГЭ',
  author: 'Авторское',
  textbook: 'Учебник',
  olympiad: 'Олимпиадное',
  other: 'Другое',
};

export default function TaskBank({ blueprintId, onSelectBlueprint }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [blueprints, setBlueprints] = useState([]);
  const [selectedBlueprint, setSelectedBlueprint] = useState(blueprintId);
  const [filterNumber, setFilterNumber] = useState('');
  const [filterDifficulty, setFilterDifficulty] = useState('');
  const [slots, setSlots] = useState([]);
  const [editingTaskId, setEditingTaskId] = useState(null); // null=list, 'new'=create, id=edit
  const [stats, setStats] = useState(null);

  // Загрузка списка шаблонов для выбора
  useEffect(() => {
    examService.getBlueprints().then(data => {
      setBlueprints(data.results || data);
    }).catch(() => {});
  }, []);

  // Загрузка слотов выбранного шаблона
  useEffect(() => {
    if (selectedBlueprint) {
      examService.getBlueprint(selectedBlueprint).then(data => {
        setSlots(data.task_slots || []);
      }).catch(() => setSlots([]));
    }
  }, [selectedBlueprint]);

  // Загрузка заданий
  const fetchTasks = useCallback(async () => {
    if (!selectedBlueprint) return;
    setLoading(true);
    try {
      const params = { blueprint: selectedBlueprint };
      if (filterNumber) params.task_number = filterNumber;
      if (filterDifficulty) params.difficulty = filterDifficulty;
      const data = await examService.getTasks(params);
      setTasks(data.results || data);
    } catch (err) {
      console.error('Failed to load tasks:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedBlueprint, filterNumber, filterDifficulty]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Загрузка статистики
  useEffect(() => {
    if (selectedBlueprint) {
      examService.getTaskStats(selectedBlueprint).then(setStats).catch(() => setStats(null));
    }
  }, [selectedBlueprint, tasks.length]);

  const handleBlueprintChange = (id) => {
    setSelectedBlueprint(id);
    if (onSelectBlueprint) onSelectBlueprint(id);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Удалить задание из банка?')) return;
    try {
      await examService.deleteTask(id);
      fetchTasks();
    } catch (err) {
      console.error('Failed to delete task:', err);
    }
  };

  // Если редактируем задание
  if (editingTaskId !== null) {
    return (
      <TaskEditor
        taskId={editingTaskId === 'new' ? null : editingTaskId}
        blueprintId={selectedBlueprint}
        slots={slots}
        onClose={() => setEditingTaskId(null)}
        onSaved={() => {
          setEditingTaskId(null);
          fetchTasks();
        }}
      />
    );
  }

  // Если шаблон не выбран
  if (!selectedBlueprint) {
    return (
      <div className="exam-empty-state">
        <div className="exam-empty-state-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
          </svg>
        </div>
        <h3 className="exam-empty-state-title">Выберите шаблон</h3>
        <p className="exam-empty-state-desc">
          Для работы с банком заданий сначала выберите шаблон экзамена.
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
    <div className="task-bank animate-content">
      {/* Toolbar */}
      <div className="task-bank-toolbar">
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

          <select
            className="blueprint-filter-select"
            value={filterNumber}
            onChange={e => setFilterNumber(e.target.value)}
          >
            <option value="">Все номера</option>
            {slots.map(s => (
              <option key={s.task_number} value={s.task_number}>
                #{s.task_number} — {s.title || ANSWER_TYPE_LABELS[s.answer_type] || s.answer_type}
              </option>
            ))}
          </select>

          <select
            className="blueprint-filter-select"
            value={filterDifficulty}
            onChange={e => setFilterDifficulty(e.target.value)}
          >
            <option value="">Все уровни</option>
            {Object.entries(DIFFICULTY_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>

        <Button variant="primary" onClick={() => setEditingTaskId('new')}>
          Добавить задание
        </Button>
      </div>

      {/* Статистика по слотам */}
      {stats && (
        <div className="task-bank-stats">
          <div className="task-bank-stat">
            <div className="task-bank-stat-value">{stats.total_tasks || tasks.length}</div>
            <div className="task-bank-stat-label">Всего заданий</div>
          </div>
          <div className="task-bank-stat">
            <div className="task-bank-stat-value">{stats.filled_slots || 0}</div>
            <div className="task-bank-stat-label">Заполнено слотов</div>
          </div>
          <div className="task-bank-stat">
            <div className="task-bank-stat-value">{stats.total_slots || slots.length}</div>
            <div className="task-bank-stat-label">Всего слотов</div>
          </div>
        </div>
      )}

      {/* Список заданий */}
      {loading ? (
        <div className="exam-skeleton-cards">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="exam-skeleton-card skeleton" />
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <div className="exam-empty-state">
          <div className="exam-empty-state-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="12" y1="8" x2="12" y2="16" />
              <line x1="8" y1="12" x2="16" y2="12" />
            </svg>
          </div>
          <h3 className="exam-empty-state-title">Банк пуст</h3>
          <p className="exam-empty-state-desc">
            Добавьте первое задание, чтобы потом генерировать варианты экзамена.
          </p>
          <Button variant="primary" onClick={() => setEditingTaskId('new')}>
            Добавить задание
          </Button>
        </div>
      ) : (
        <div className="task-bank-grid">
          {tasks.map(task => (
            <div key={task.id} className="task-card">
              <div className="task-card-header">
                <span className="task-card-number">{task.task_number}</span>
                <span className={`task-card-difficulty ${task.difficulty}`}>
                  {DIFFICULTY_LABELS[task.difficulty] || task.difficulty}
                </span>
              </div>

              <div className="task-card-prompt">
                {task.question_prompt || task.question?.prompt || 'Без текста'}
              </div>

              <div className="task-card-footer">
                <span>{SOURCE_LABELS[task.source] || task.source}</span>
                <div style={{ display: 'flex', gap: 'var(--space-xs)' }}>
                  <Button size="sm" variant="ghost" onClick={() => setEditingTaskId(task.id)}>
                    Изменить
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => handleDelete(task.id)}>
                    Удалить
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
