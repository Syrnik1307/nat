import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth';
import { Notification, ConfirmModal } from '../shared/components';
import useNotification from '../shared/hooks/useNotification';
import './StudentsManage.css';

const StudentsManage = ({ onClose }) => {
  const { notification, confirm, showNotification, closeNotification, showConfirm, closeConfirm } = useNotification();
  const { user } = useAuth();
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editForm, setEditForm] = useState({
    first_name: '',
    last_name: '',
    middle_name: '',
    email: ''
  });
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  useEffect(() => {
    loadStudents();
    const interval = setInterval(loadStudents, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadStudents = async () => {
    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('/accounts/api/admin/students/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setStudents(data);
      setLoading(false);
    } catch (error) {
      console.error('Ошибка загрузки учеников:', error);
      setLoading(false);
    }
  };

  const handleSelectStudent = (student) => {
    setSelectedStudent(student);
    setEditForm({
      first_name: student.first_name || '',
      last_name: student.last_name || '',
      middle_name: student.middle_name || '',
      email: student.email || ''
    });
    setShowEditForm(true);
    setFormError('');
    setFormSuccess('');
  };

  const handleUpdateStudent = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');

    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`/accounts/api/admin/students/${selectedStudent.id}/update/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(editForm)
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to update');
      }
      setFormSuccess('Данные ученика успешно обновлены!');
      loadStudents();
      setTimeout(() => {
        setShowEditForm(false);
        setSelectedStudent(null);
        setFormSuccess('');
      }, 2000);
    } catch (error) {
      setFormError(error.message || 'Ошибка обновления данных');
    }
  };

  const handleDeleteStudent = async (studentId, studentName) => {
    const confirmed = await showConfirm({
      title: 'Удаление ученика',
      message: `Вы уверены, что хотите удалить ученика ${studentName}? Это действие нельзя отменить.`,
      variant: 'danger',
      confirmText: 'Удалить',
      cancelText: 'Отмена'
    });
    if (!confirmed) return;

    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`/accounts/api/admin/students/${studentId}/delete/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to delete');
      }
      
      await loadStudents();
      
      if (selectedStudent?.id === studentId) {
        setShowEditForm(false);
        setSelectedStudent(null);
      }
      showNotification('success', 'Успешно', 'Ученик удален');
    } catch (error) {
      showNotification('error', 'Ошибка', 'Ошибка удаления ученика: ' + (error.message || 'Неизвестная ошибка'));
    }
  };

  if (loading) {
    return (
      <div className="students-manage-overlay">
        <div className="students-manage-modal">
          <div className="sm-loading">Загрузка...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="students-manage-overlay" onClick={onClose}>
      <div className="students-manage-modal" onClick={(e) => e.stopPropagation()}>
        <div className="sm-header">
          <h2>🎓 Управление учениками</h2>
          <button className="sm-refresh" onClick={loadStudents} title="Обновить список">
            🔄
          </button>
          <button className="sm-close" onClick={onClose}>✕</button>
        </div>

        <div className="sm-content">
          {!showEditForm ? (
            <div className="sm-students-list">
              <div className="sm-list-header">
                <span>Ученик</span>
                <span>Email</span>
                <span>Дата регистрации</span>
                <span>Действия</span>
              </div>
              {students.map((student) => (
                <div 
                  key={student.id} 
                  className="sm-student-item"
                >
                  <div className="sm-student-name" onClick={() => handleSelectStudent(student)}>
                    {student.last_name} {student.first_name} {student.middle_name}
                  </div>
                  <div className="sm-student-email" onClick={() => handleSelectStudent(student)}>{student.email}</div>
                  <div className="sm-student-date" onClick={() => handleSelectStudent(student)}>
                    {student.created_at ? new Date(student.created_at).toLocaleDateString('ru-RU') : '—'}
                  </div>
                  <div className="sm-student-actions">
                    <button 
                      className="sm-edit-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectStudent(student);
                      }}
                      title="Редактировать ученика"
                    >
                      Пэ
                    </button>
                    <button 
                      className="sm-delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteStudent(student.id, `${student.first_name} ${student.last_name}`);
                      }}
                      title="Удалить ученика"
                    >
                      ×
                    </button>
                  </div>
                </div>
              ))}
              {students.length === 0 && (
                <div className="sm-empty">Нет учеников в системе</div>
              )}
            </div>
          ) : (
            <div className="sm-edit-form">
              <button className="sm-back" onClick={() => setShowEditForm(false)}>
                ← Назад к списку
              </button>
              
              <div className="sm-selected-student">
                <h3>Редактирование: {selectedStudent.last_name} {selectedStudent.first_name}</h3>
                <p className="sm-student-email-small">{selectedStudent.email}</p>
              </div>

              <form onSubmit={handleUpdateStudent}>
                {formError && <div className="form-error">{formError}</div>}
                {formSuccess && <div className="form-success">{formSuccess}</div>}

                <div className="form-group">
                  <label>Имя *</label>
                  <input
                    type="text"
                    value={editForm.first_name}
                    onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                    placeholder="Иван"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Фамилия *</label>
                  <input
                    type="text"
                    value={editForm.last_name}
                    onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                    placeholder="Иванов"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Отчество</label>
                  <input
                    type="text"
                    value={editForm.middle_name}
                    onChange={(e) => setEditForm({ ...editForm, middle_name: e.target.value })}
                    placeholder="Иванович"
                  />
                </div>

                <div className="form-group">
                  <label>Email (только для просмотра)</label>
                  <input
                    type="email"
                    value={editForm.email}
                    disabled
                    style={{ backgroundColor: '#f5f5f5', cursor: 'not-allowed' }}
                  />
                  <small>Email нельзя изменить</small>
                </div>

                <div className="form-actions">
                  <button type="button" onClick={() => setShowEditForm(false)} className="btn-cancel">
                    Отмена
                  </button>
                  <button type="submit" className="btn-submit">
                    Сохранить изменения
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>

        <Notification
          isOpen={notification.isOpen}
          onClose={closeNotification}
          type={notification.type}
          title={notification.title}
          message={notification.message}
        />

        <ConfirmModal
          isOpen={confirm.isOpen}
          onClose={closeConfirm}
          onConfirm={confirm.onConfirm}
          title={confirm.title}
          message={confirm.message}
          variant={confirm.variant}
          confirmText={confirm.confirmText}
          cancelText={confirm.cancelText}
        />
      </div>
    </div>
  );
};

export default StudentsManage;
