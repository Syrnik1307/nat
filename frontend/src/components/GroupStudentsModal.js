/**
 * GroupStudentsModal.js
 * Модальное окно для управления учениками группы
 * Красивый дизайн в стиле приложения
 */

import React, { useState } from 'react';
import Modal from '../shared/components/Modal';
import { ConfirmModal } from '../shared/components';
import { removeStudentsFromGroup, addStudentsToGroup } from '../apiService';
import './GroupStudentsModal.css';

const GroupStudentsModal = ({ group, allGroups = [], isOpen, onClose, onStudentsRemoved }) => {
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [removing, setRemoving] = useState(false);
  const [transferring, setTransferring] = useState(false);
  const [showTransferSelect, setShowTransferSelect] = useState(false);
  const [targetGroupId, setTargetGroupId] = useState('');
  const [confirmModal, setConfirmModal] = useState({ isOpen: false });

  if (!isOpen || !group) return null;

  const students = Array.isArray(group.students) ? group.students : [];

  const toggleStudent = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === students.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(students.map(s => s.id)));
    }
  };

  const handleRemoveClick = () => {
    if (selectedIds.size === 0) return;
    setConfirmModal({
      isOpen: true,
      count: selectedIds.size,
      type: 'remove'
    });
  };

  const handleTransferClick = () => {
    if (selectedIds.size === 0) return;
    setShowTransferSelect(true);
    setTargetGroupId('');
  };

  const handleTransferConfirm = () => {
    if (!targetGroupId) return;
    setShowTransferSelect(false);
    setConfirmModal({
      isOpen: true,
      count: selectedIds.size,
      type: 'transfer',
      targetGroupId: targetGroupId,
      targetGroupName: availableGroups.find(g => g.id === parseInt(targetGroupId))?.name || ''
    });
  };

  const handleConfirmTransfer = async () => {
    setTransferring(true);
    try {
      const ids = Array.from(selectedIds);
      // Сначала удаляем из текущей группы
      await removeStudentsFromGroup(group.id, ids);
      // Затем добавляем в новую группу
      await addStudentsToGroup(parseInt(confirmModal.targetGroupId), ids);
      setSelectedIds(new Set());
      setConfirmModal({ isOpen: false });
      if (onStudentsRemoved) {
        onStudentsRemoved();
      }
    } catch (error) {
      console.error('Error transferring students:', error);
    } finally {
      setTransferring(false);
    }
  };

  const handleConfirmRemove = async () => {
    setRemoving(true);
    try {
      await removeStudentsFromGroup(group.id, Array.from(selectedIds));
      setSelectedIds(new Set());
      setConfirmModal({ isOpen: false });
      if (onStudentsRemoved) {
        onStudentsRemoved();
      }
    } catch (error) {
      console.error('Error removing students:', error);
    } finally {
      setRemoving(false);
    }
  };

  // Фильтруем группы для переноса (исключаем текущую)
  const availableGroups = allGroups.filter(g => g.id !== group.id);

  const getInitials = (student) => {
    const first = student.first_name?.[0] || '';
    const last = student.last_name?.[0] || '';
    return (first + last).toUpperCase() || '?';
  };

  const getFullName = (student) => {
    const name = `${student.first_name || ''} ${student.last_name || ''}`.trim();
    return name || student.email || `Ученик #${student.id}`;
  };

  const footer = students.length > 0 ? (
    <div className="gsm-footer">
      <div className="gsm-footer-info">
        {selectedIds.size > 0 && (
          <span className="gsm-selected-count">
            Выбрано: {selectedIds.size}
          </span>
        )}
      </div>
      <div className="gsm-footer-actions">
        <button
          className="gsm-btn gsm-btn-secondary"
          onClick={onClose}
        >
          Закрыть
        </button>
        {availableGroups.length > 0 && (
          <button
            className="gsm-btn gsm-btn-primary"
            onClick={handleTransferClick}
            disabled={selectedIds.size === 0 || transferring}
          >
            Перенести
          </button>
        )}
        <button
          className="gsm-btn gsm-btn-danger"
          onClick={handleRemoveClick}
          disabled={selectedIds.size === 0 || removing}
        >
          {removing ? 'Удаление...' : 'Удалить'}
        </button>
      </div>
    </div>
  ) : (
    <div className="gsm-footer">
      <button className="gsm-btn gsm-btn-primary" onClick={onClose}>
        Закрыть
      </button>
    </div>
  );

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title={`Ученики группы`}
        size="medium"
        footer={footer}
      >
        <div className="gsm-content">
          <div className="gsm-group-name">{group.name}</div>
          
          {students.length === 0 ? (
            <div className="gsm-empty">
              <div className="gsm-empty-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              </div>
              <h4>Нет учеников</h4>
              <p>В этой группе пока нет учеников</p>
              <div className="gsm-tip">
                Нажмите кнопку «Пригласить» на карточке группы и поделитесь кодом приглашения с учениками
              </div>
            </div>
          ) : (
            <>
              <div className="gsm-toolbar">
                <div className="gsm-count">
                  Всего учеников: <strong>{students.length}</strong>
                </div>
                <button
                  className="gsm-select-all"
                  onClick={toggleAll}
                >
                  {selectedIds.size === students.length ? 'Снять выделение' : 'Выбрать всех'}
                </button>
              </div>

              <div className="gsm-list">
                {students.map((student) => (
                  <div
                    key={student.id}
                    className={`gsm-student ${selectedIds.has(student.id) ? 'selected' : ''}`}
                    onClick={() => toggleStudent(student.id)}
                  >
                    <div className="gsm-checkbox">
                      {selectedIds.has(student.id) && (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </div>
                    <div className="gsm-avatar">
                      {getInitials(student)}
                    </div>
                    <div className="gsm-info">
                      <div className="gsm-name">{getFullName(student)}</div>
                      {student.email && (
                        <div className="gsm-email">{student.email}</div>
                      )}
                    </div>
                    <div className="gsm-id">#{student.id}</div>
                  </div>
                ))}
              </div>

              <div className="gsm-tip">
                Чтобы добавить учеников, нажмите «Пригласить» и поделитесь кодом
              </div>
            </>
          )}

          {/* Панель выбора группы для переноса */}
          {showTransferSelect && (
            <div className="gsm-transfer-panel">
              <div className="gsm-transfer-header">
                <span>Перенести в группу:</span>
                <button 
                  className="gsm-transfer-close"
                  onClick={() => setShowTransferSelect(false)}
                >
                  ✕
                </button>
              </div>
              <select
                className="gsm-transfer-select"
                value={targetGroupId}
                onChange={(e) => setTargetGroupId(e.target.value)}
              >
                <option value="">Выберите группу...</option>
                {availableGroups.map(g => (
                  <option key={g.id} value={g.id}>{g.name}</option>
                ))}
              </select>
              <button
                className="gsm-btn gsm-btn-primary gsm-transfer-confirm"
                onClick={handleTransferConfirm}
                disabled={!targetGroupId}
              >
                Перенести
              </button>
            </div>
          )}
        </div>
      </Modal>

      {/* Модалка подтверждения удаления */}
      <ConfirmModal
        isOpen={confirmModal.isOpen && confirmModal.type === 'remove'}
        onClose={() => setConfirmModal({ isOpen: false })}
        onConfirm={handleConfirmRemove}
        title="Удалить учеников?"
        message={`Вы собираетесь удалить ${confirmModal.count} ${confirmModal.count === 1 ? 'ученика' : 'учеников'} из группы. Они потеряют доступ к материалам группы.`}
        confirmText={removing ? 'Удаление...' : 'Удалить'}
        cancelText="Отмена"
        variant="danger"
      />

      {/* Модалка подтверждения переноса */}
      <ConfirmModal
        isOpen={confirmModal.isOpen && confirmModal.type === 'transfer'}
        onClose={() => setConfirmModal({ isOpen: false })}
        onConfirm={handleConfirmTransfer}
        title="Перенести учеников?"
        message={`Вы собираетесь перенести ${confirmModal.count} ${confirmModal.count === 1 ? 'ученика' : 'учеников'} в группу «${confirmModal.targetGroupName}». Они будут удалены из текущей группы.`}
        confirmText={transferring ? 'Перенос...' : 'Перенести'}
        cancelText="Отмена"
        variant="primary"
      />
    </>
  );
};

export default GroupStudentsModal;
