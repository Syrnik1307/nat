import React, { useState, useEffect, useCallback } from 'react';
import { getGroups, instantiateTemplate } from '../../../../apiService';
import { Modal, Button, Input } from '../../../../shared/components';
import './InstantiateTemplateModal.css';

/**
 * Модальное окно для назначения ДЗ из шаблона.
 * Позволяет выбрать группы, установить дедлайн и макс. балл.
 */
const InstantiateTemplateModal = ({ template, onClose, onSuccess }) => {
  const [groups, setGroups] = useState([]);
  const [loadingGroups, setLoadingGroups] = useState(true);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [deadline, setDeadline] = useState('');
  const [maxScore, setMaxScore] = useState(template?.max_score || 100);
  const [publishNow, setPublishNow] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const loadGroups = useCallback(async () => {
    setLoadingGroups(true);
    try {
      const response = await getGroups();
      const data = response.data?.results || response.data || [];
      setGroups(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load groups:', err);
    } finally {
      setLoadingGroups(false);
    }
  }, []);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  const toggleGroup = (groupId) => {
    setSelectedGroupIds((prev) =>
      prev.includes(groupId)
        ? prev.filter((id) => id !== groupId)
        : [...prev, groupId]
    );
  };

  const selectAllGroups = () => {
    if (selectedGroupIds.length === groups.length) {
      setSelectedGroupIds([]);
    } else {
      setSelectedGroupIds(groups.map((g) => g.id));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (selectedGroupIds.length === 0) {
      setError('Выберите хотя бы одну группу');
      return;
    }

    setSaving(true);
    try {
      await instantiateTemplate(template.id, {
        group_ids: selectedGroupIds,
        student_ids: [],
        deadline: deadline || null,
        max_score: parseInt(maxScore, 10) || 100,
        publish: publishNow
      });
      onSuccess();
    } catch (err) {
      console.error('Instantiate error:', err);
      setError(err.response?.data?.detail || 'Ошибка создания ДЗ');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Назначить домашнее задание"
      size="medium"
    >
      <form onSubmit={handleSubmit} className="instantiate-form">
        <div className="instantiate-template-info">
          <span className="template-label">Шаблон:</span>
          <span className="template-name">{template.title}</span>
        </div>

        {/* Выбор групп */}
        <div className="form-group">
          <div className="groups-header">
            <label className="form-label">Группы</label>
            <button
              type="button"
              className="select-all-btn"
              onClick={selectAllGroups}
            >
              {selectedGroupIds.length === groups.length ? 'Снять все' : 'Выбрать все'}
            </button>
          </div>

          {loadingGroups ? (
            <div className="groups-loading">Загрузка групп...</div>
          ) : groups.length === 0 ? (
            <div className="groups-empty">Нет доступных групп</div>
          ) : (
            <div className="groups-grid">
              {groups.map((group) => (
                <label
                  key={group.id}
                  className={`group-checkbox ${selectedGroupIds.includes(group.id) ? 'selected' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={selectedGroupIds.includes(group.id)}
                    onChange={() => toggleGroup(group.id)}
                  />
                  <span className="group-name">{group.name}</span>
                  <span className="group-count">
                    {group.students_count || 0} уч.
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Дедлайн */}
        <div className="form-group">
          <label className="form-label">Дедлайн (необязательно)</label>
          <input
            type="datetime-local"
            className="form-input"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
          />
        </div>

        {/* Макс. балл */}
        <div className="form-group">
          <label className="form-label">Максимальный балл</label>
          <input
            type="number"
            className="form-input"
            min={1}
            value={maxScore}
            onChange={(e) => setMaxScore(e.target.value)}
          />
        </div>

        {/* Опубликовать сразу */}
        <div className="form-group">
          <label className="publish-checkbox">
            <input
              type="checkbox"
              checked={publishNow}
              onChange={(e) => setPublishNow(e.target.checked)}
            />
            <span>Опубликовать сразу (уведомить студентов)</span>
          </label>
        </div>

        {error && <div className="instantiate-error">{error}</div>}

        <div className="instantiate-actions">
          <Button variant="secondary" type="button" onClick={onClose} disabled={saving}>
            Отмена
          </Button>
          <Button variant="primary" type="submit" disabled={saving || selectedGroupIds.length === 0}>
            {saving ? 'Создание...' : 'Назначить ДЗ'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default InstantiateTemplateModal;
