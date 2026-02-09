import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getHomeworkList, deleteHomework, updateHomework, getGroups, getHomework, duplicateAndAssignHomework } from '../../../../apiService';
import { Button, Modal, Select } from '../../../../shared/components';
import { useNotifications } from '../../../../shared/context/NotificationContext';
import StudentPicker from '../homework/StudentPicker';
import './MyHomeworksList.css';

// SVG Icons
const IconEdit = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
  </svg>
);

const IconTrash = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3,6 5,6 21,6"/>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
    <line x1="10" y1="11" x2="10" y2="17"/>
    <line x1="14" y1="11" x2="14" y2="17"/>
  </svg>
);

const IconUsers = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const IconClock = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12,6 12,12 16,14"/>
  </svg>
);

const IconArchive = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="21,8 21,21 3,21 3,8"/>
    <rect x="1" y="3" width="22" height="5"/>
    <line x1="10" y1="12" x2="14" y2="12"/>
  </svg>
);

const IconCopy = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  </svg>
);

const IconCheck = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20,6 9,17 4,12"/>
  </svg>
);

const IconFile = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14,2 14,8 20,8"/>
    <line x1="16" y1="13" x2="8" y2="13"/>
    <line x1="16" y1="17" x2="8" y2="17"/>
    <polyline points="10,9 9,9 8,9"/>
  </svg>
);

const IconMove = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="5,9 2,12 5,15"/>
    <polyline points="9,5 12,2 15,5"/>
    <polyline points="15,19 12,22 9,19"/>
    <polyline points="19,9 22,12 19,15"/>
    <line x1="2" y1="12" x2="22" y2="12"/>
    <line x1="12" y1="2" x2="12" y2="22"/>
  </svg>
);

/**
 * Модальное окно переназначения/дублирования ДЗ с выбором учеников
 */
const ReassignModal = ({ homework, groups, onClose, onSave, toast }) => {
  // Режим: 'move' (перенести) или 'duplicate' (создать копию)
  const [mode, setMode] = useState('duplicate');
  
  // Назначения: [{groupId, studentIds: [], allStudents: bool}]
  // Начинаем с пустого списка - пользователь выбирает НОВЫЕ группы/учеников
  const [groupAssignments, setGroupAssignments] = useState([]);
  
  const [deadline, setDeadline] = useState(
    homework.deadline ? homework.deadline.slice(0, 16) : ''
  );
  const [publishNow, setPublishNow] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (groupAssignments.length === 0) {
      toast?.error?.('Выберите хотя бы одну группу');
      return;
    }
    
    setSaving(true);
    try {
      // Формируем данные для API
      const apiData = {
        mode,
        group_assignments: groupAssignments.map(ga => ({
          group_id: ga.groupId,
          student_ids: ga.allStudents ? [] : ga.studentIds,
          deadline: deadline ? new Date(deadline).toISOString() : null,
        })),
        individual_student_ids: [],
        deadline: deadline ? new Date(deadline).toISOString() : null,
        publish: publishNow,
      };
      
      await duplicateAndAssignHomework(homework.id, apiData);
      
      const actionLabel = mode === 'move' ? 'перенесено' : 'продублировано';
      toast?.success?.(`ДЗ успешно ${actionLabel}`);
      
      onSave?.();
      onClose();
    } catch (err) {
      console.error('Failed to reassign:', err);
      toast?.error?.(err.response?.data?.detail || 'Ошибка при назначении');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={true} onClose={onClose} title="Назначить ДЗ">
      <div className="reassign-modal-content">
        {/* Выбор режима */}
        <div className="reassign-field">
          <label className="reassign-label">Режим</label>
          <div className="reassign-mode-toggle">
            <button
              type="button"
              className={`reassign-mode-btn ${mode === 'duplicate' ? 'active' : ''}`}
              onClick={() => setMode('duplicate')}
            >
              <IconCopy size={16} />
              <span>Дублировать</span>
            </button>
            <button
              type="button"
              className={`reassign-mode-btn ${mode === 'move' ? 'active' : ''}`}
              onClick={() => setMode('move')}
            >
              <IconMove size={16} />
              <span>Перенести</span>
            </button>
          </div>
          <p className="reassign-hint">
            {mode === 'duplicate' 
              ? 'Создаст копию ДЗ для выбранных групп/учеников'
              : 'Переназначит существующее ДЗ (старые назначения будут заменены)'
            }
          </p>
        </div>

        {/* Выбор групп и учеников */}
        <div className="reassign-field">
          <label className="reassign-label">Назначить</label>
          <StudentPicker
            value={groupAssignments}
            onChange={setGroupAssignments}
            groups={groups}
          />
        </div>

        {/* Дедлайн */}
        <div className="reassign-field">
          <label className="reassign-label">Дедлайн</label>
          <input
            type="datetime-local"
            className="reassign-input"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
          />
          <p className="reassign-hint">Оставьте пустым, если срок не ограничен</p>
        </div>

        {/* Опубликовать сразу */}
        <div className="reassign-field">
          <label className="reassign-checkbox-label">
            <input
              type="checkbox"
              checked={publishNow}
              onChange={(e) => setPublishNow(e.target.checked)}
            />
            <span>Опубликовать сразу</span>
          </label>
        </div>

        <div className="reassign-actions">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Отмена
          </Button>
          <Button 
            variant="primary" 
            onClick={handleSave} 
            loading={saving}
            disabled={groupAssignments.length === 0}
          >
            {mode === 'duplicate' ? 'Дублировать' : 'Перенести'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

/**
 * Список домашних заданий учителя с управлением
 */
const MyHomeworksList = ({ onEditHomework }) => {
  const navigate = useNavigate();
  const { toast, showConfirm } = useNotifications();
  
  const [homeworks, setHomeworks] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all' | 'published' | 'draft' | 'archived'
  const [reassignHomework, setReassignHomework] = useState(null);
  const [editingId, setEditingId] = useState(null); // ID загружаемого ДЗ для индикатора

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [hwRes, groupsRes] = await Promise.all([
        getHomeworkList(),
        getGroups()
      ]);
      
      const hwData = hwRes.data?.results || hwRes.data || [];
      setHomeworks(Array.isArray(hwData) ? hwData : []);
      
      const groupsData = groupsRes.data?.results || groupsRes.data || [];
      setGroups(Array.isArray(groupsData) ? groupsData : []);
    } catch (err) {
      console.error('Failed to load homeworks:', err);
      setError('Не удалось загрузить домашние задания');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Фильтрация ДЗ
  const filteredHomeworks = homeworks.filter(hw => {
    if (filter === 'all') return true;
    return hw.status === filter;
  });

  // Удаление ДЗ
  const handleDelete = async (homework) => {
    const hasSubmissions = homework.submissions_count > 0;
    const message = hasSubmissions 
      ? `ДЗ "${homework.title}" имеет ${homework.submissions_count} ответов. Все они будут удалены. Продолжить?`
      : `Удалить ДЗ "${homework.title}"?`;

    const confirmed = await showConfirm({
      title: 'Удалить домашнее задание?',
      message,
      variant: 'danger',
      confirmText: 'Удалить',
      cancelText: 'Отмена'
    });
    
    if (!confirmed) return;

    try {
      await deleteHomework(homework.id);
      toast.success('Домашнее задание удалено');
      loadData();
    } catch (err) {
      toast.error('Ошибка удаления');
    }
  };

  // Архивация ДЗ
  const handleArchive = async (homework) => {
    const confirmed = await showConfirm({
      title: 'Архивировать ДЗ?',
      message: `ДЗ "${homework.title}" будет перемещено в архив. Ученики больше не смогут его видеть.`,
      variant: 'warning',
      confirmText: 'Архивировать',
      cancelText: 'Отмена'
    });
    
    if (!confirmed) return;

    try {
      await updateHomework(homework.id, { status: 'archived' });
      toast.success('ДЗ архивировано');
      loadData();
    } catch (err) {
      toast.error('Ошибка архивации');
    }
  };

  // Переназначение ДЗ
  const handleReassign = async (homeworkId, data) => {
    await updateHomework(homeworkId, data);
    toast.success('ДЗ переназначено');
    loadData();
  };

  // Дублирование ДЗ
  const handleDuplicate = async (homework) => {
    // Загружаем полные данные ДЗ с вопросами
    try {
      const response = await getHomework(homework.id);
      const fullHomework = response.data;
      if (onEditHomework) {
        onEditHomework(fullHomework, { duplicate: true });
      }
    } catch (err) {
      toast.error('Ошибка загрузки ДЗ');
    }
  };

  // Редактирование ДЗ
  const handleEdit = async (homework) => {
    if (editingId) return; // Предотвращаем двойной клик
    setEditingId(homework.id);
    try {
      const response = await getHomework(homework.id);
      const fullHomework = response.data;
      if (onEditHomework) {
        onEditHomework(fullHomework, { duplicate: false });
      }
    } catch (err) {
      toast.error('Ошибка загрузки ДЗ');
    } finally {
      setEditingId(null);
    }
  };

  // Форматирование даты
  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Получение статус бейджа
  const getStatusBadge = (status) => {
    switch (status) {
      case 'published':
        return <span className="myhw-status-badge published">Опубликовано</span>;
      case 'draft':
        return <span className="myhw-status-badge draft">Черновик</span>;
      case 'archived':
        return <span className="myhw-status-badge archived">Архив</span>;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="myhw-loading">
        <div className="myhw-spinner" />
        <span>Загрузка домашних заданий...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="myhw-error">
        <p>{error}</p>
        <Button variant="secondary" onClick={loadData}>Повторить</Button>
      </div>
    );
  }

  return (
    <div className="myhw-list">
      {/* Фильтры */}
      <div className="myhw-filters">
        <button 
          className={`myhw-filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          Все ({homeworks.length})
        </button>
        <button 
          className={`myhw-filter-btn ${filter === 'published' ? 'active' : ''}`}
          onClick={() => setFilter('published')}
        >
          Опубликованные ({homeworks.filter(h => h.status === 'published').length})
        </button>
        <button 
          className={`myhw-filter-btn ${filter === 'draft' ? 'active' : ''}`}
          onClick={() => setFilter('draft')}
        >
          Черновики ({homeworks.filter(h => h.status === 'draft').length})
        </button>
        <button 
          className={`myhw-filter-btn ${filter === 'archived' ? 'active' : ''}`}
          onClick={() => setFilter('archived')}
        >
          Архив ({homeworks.filter(h => h.status === 'archived').length})
        </button>
      </div>

      {/* Список ДЗ */}
      {filteredHomeworks.length === 0 ? (
        <div className="myhw-empty">
          <IconFile size={48} />
          <h3>Нет домашних заданий</h3>
          <p>
            {filter === 'all' 
              ? 'Создайте первое ДЗ в конструкторе'
              : `Нет ДЗ со статусом "${filter}"`
            }
          </p>
        </div>
      ) : (
        <div className="myhw-grid">
          {filteredHomeworks.map((homework) => (
            <div key={homework.id} className={`myhw-card ${homework.status}`}>
              <div className="myhw-card-header">
                <h3 className="myhw-title">{homework.title}</h3>
                {getStatusBadge(homework.status)}
              </div>

              {homework.description && (
                <p className="myhw-description">{homework.description}</p>
              )}

              <div className="myhw-meta">
                <div className="myhw-meta-item">
                  <IconFile size={14} />
                  <span>{homework.questions_count || 0} вопросов</span>
                </div>
                
                {homework.deadline && (
                  <div className="myhw-meta-item">
                    <IconClock size={14} />
                    <span>{formatDate(homework.deadline)}</span>
                  </div>
                )}
                
                <div className="myhw-meta-item">
                  <IconUsers size={14} />
                  <span>
                    {homework.assigned_groups?.length || 0} групп
                  </span>
                </div>

                {homework.submissions_count > 0 && (
                  <div className="myhw-meta-item submissions">
                    <IconCheck size={14} />
                    <span>{homework.submissions_count} ответов</span>
                  </div>
                )}
              </div>

              <div className="myhw-actions">
                <button 
                  className={`myhw-action-btn edit ${editingId === homework.id ? 'loading' : ''}`}
                  onClick={() => handleEdit(homework)}
                  title="Редактировать"
                  disabled={!!editingId}
                >
                  {editingId === homework.id ? (
                    <><div className="myhw-btn-spinner" /><span>Загрузка...</span></>
                  ) : (
                    <><IconEdit size={16} /><span>Редактировать</span></>
                  )}
                </button>
                
                <button 
                  className="myhw-action-btn reassign"
                  onClick={() => setReassignHomework(homework)}
                  title="Назначить"
                >
                  <IconUsers size={16} />
                  <span>Назначить</span>
                </button>

                {homework.status !== 'archived' && (
                  <button 
                    className="myhw-action-btn archive"
                    onClick={() => handleArchive(homework)}
                    title="Архивировать"
                  >
                    <IconArchive size={16} />
                  </button>
                )}

                <button 
                  className="myhw-action-btn delete"
                  onClick={() => handleDelete(homework)}
                  title="Удалить"
                >
                  <IconTrash size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Модальное окно назначения/дублирования */}
      {reassignHomework && (
        <ReassignModal
          homework={reassignHomework}
          groups={groups}
          onClose={() => setReassignHomework(null)}
          onSave={() => loadData()}
          toast={toast}
        />
      )}
    </div>
  );
};

export default MyHomeworksList;
