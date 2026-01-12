import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getGroups,
  createGroup,
  updateGroup,
  deleteGroup,
  getAccessToken,
} from '../apiService';
import GroupInviteModal from './GroupInviteModal';
import GroupDetailModal from './GroupDetailModal';
import StudentCardModal from './StudentCardModal';
import GroupStudentsModal from './GroupStudentsModal';
import {
  useIndividualInvitesData,
  IndividualInviteForm,
  IndividualInviteList,
} from './IndividualInvitesManage';
import './GroupsManage.css';
import { ConfirmModal } from '../shared/components';

const initialGroupForm = { name: '', description: '' };

// Utility to read user_id from JWT payload (handle base64url)
const getCurrentUserId = () => {
  const token = getAccessToken();
  if (!token) return null;
  try {
    const part = token.split('.')[1];
    if (!part) return null;
    const base64 = part.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64 + '='.repeat((4 - base64.length % 4) % 4);
    const payload = JSON.parse(atob(padded));
    return payload.user_id || null;
  } catch (_) {
    return null;
  }
};

const GroupsManage = () => {
  const navigate = useNavigate();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  const [activePanel, setActivePanel] = useState('group');
  const [groupForm, setGroupForm] = useState(initialGroupForm);
  const [editingId, setEditingId] = useState(null);
  const [studentsModalGroup, setStudentsModalGroup] = useState(null);
  const [inviteModalGroup, setInviteModalGroup] = useState(null);
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: null,
    variant: 'warning',
    confirmText: 'Да',
    cancelText: 'Отмена'
  });
  const [alertModal, setAlertModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    variant: 'info'
  });

  // Состояния для карточки группы и ученика
  const [detailModal, setDetailModal] = useState({ isOpen: false, group: null });
  const [studentModal, setStudentModal] = useState({ isOpen: false, studentId: null, groupId: null });

  // shared state for individual invites (used on both columns when таб "Индивидуальные")
  const invitesData = useIndividualInvitesData();

  const resetGroupForm = () => {
    setGroupForm(initialGroupForm);
    setEditingId(null);
  };

  const load = async () => {
    try {
      const res = await getGroups();
      const data = Array.isArray(res.data) ? res.data : res.data.results || [];
      setGroups(data);
      // Обновляем модалку учеников если открыта
      setStudentsModalGroup((current) => {
        if (!current) return null;
        return data.find((item) => item.id === current.id) || null;
      });
      setError(null);
    } catch (e) {
      console.error('[GroupsManage] Load error:', e);
      setError('Ошибка загрузки групп: ' + (e.message || 'Неизвестная ошибка'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleTabSelect = (panel) => {
    if (panel === 'group') {
      resetGroupForm();
    }
    setActivePanel(panel);
  };

  const handleCreateGroup = async (event) => {
    event.preventDefault();
    const teacherId = getCurrentUserId();
    if (!teacherId) {
      setAlertModal({
        isOpen: true,
        title: 'Ошибка',
        message: 'Не удалось определить преподавателя из токена',
        variant: 'danger'
      });
      return;
    }

    const trimmedName = groupForm.name.trim();
    if (!trimmedName) {
      setAlertModal({
        isOpen: true,
        title: 'Внимание',
        message: 'Введите название группы',
        variant: 'warning'
      });
      return;
    }

    setCreating(true);
    try {
      if (editingId) {
        await updateGroup(editingId, {
          name: trimmedName,
          description: groupForm.description.trim(),
        });
      } else {
        await createGroup({
          name: trimmedName,
          description: groupForm.description.trim(),
          teacher_id: teacherId,
        });
      }

      await load();
      resetGroupForm();
      setActivePanel('group');
    } catch (e) {
      setAlertModal({
        isOpen: true,
        title: 'Ошибка',
        message: e.response?.data ? JSON.stringify(e.response.data) : 'Ошибка сохранения группы',
        variant: 'danger'
      });
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (group) => {
    setGroupForm({
      name: group.name,
      description: group.description || '',
    });
    setEditingId(group.id);
    setActivePanel('group');
  };

  const handleDelete = async (id) => {
    setConfirmModal({
      isOpen: true,
      title: 'Удаление группы',
      message: 'Удалить группу?',
      variant: 'danger',
      confirmText: 'Удалить',
      cancelText: 'Отмена',
      onConfirm: async () => {
        try {
          await deleteGroup(id);
          await load();
        } catch (e) {
          setAlertModal({
            isOpen: true,
            title: 'Ошибка',
            message: e.response?.data ? JSON.stringify(e.response.data) : 'Ошибка удаления',
            variant: 'danger'
          });
        }
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
      }
    });
  };

  if (loading) {
    return (
      <div className="groups-manage-page">
        <div className="gm-state gm-state-loading">Загрузка...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="groups-manage-page">
        <div className="gm-state gm-state-error">
          <span>{error}</span>
          <button
            type="button"
            className="gm-btn-primary"
            onClick={() => {
              setLoading(true);
              load();
            }}
          >
            Повторить
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="groups-manage-page">
      <div className="groups-manage-header">
        <div>
          <h1 className="groups-manage-title">Группы и ученики</h1>
          <p className="groups-manage-subtitle">Управление группами и создание учеников</p>
        </div>
        <div style={{fontSize:'0.9rem', color:'#64748b', display:'flex', gap:'1rem', alignItems:'center'}}>
          <span>Всего групп: {groups.length}</span>
          <span>Всего учеников: {groups.reduce((sum, g) => sum + (g.students?.length || 0), 0)}</span>
        </div>
      </div>

      <div className="groups-manage-content">
        <div className="groups-manage-column">
          <div className="gm-tab-switch">
            <button
              type="button"
              className={`gm-tab-button ${activePanel === 'group' ? 'active' : ''}`}
              onClick={() => handleTabSelect('group')}
            >
              Группа
            </button>
            <button
              type="button"
              className={`gm-tab-button ${activePanel === 'individual' ? 'active' : ''}`}
              onClick={() => handleTabSelect('individual')}
            >
              Индивидуальные
            </button>
          </div>

          {activePanel === 'group' ? (
            <div className="gm-card">
              <div className="gm-card-heading">
                <div>
                  <h3 className="gm-card-title">
                    {editingId ? 'Редактировать группу' : 'Новая группа'}
                  </h3>
                  <p className="gm-card-subtitle">
                    {editingId
                      ? 'Обновите название и описание, затем сохраните изменения.'
                      : 'Создайте новое пространство для обучения и совместной работы.'}
                  </p>
                </div>
              </div>

              <form className="gm-form" onSubmit={handleCreateGroup}>
                <div className="form-group">
                  <label className="form-label">Название группы</label>
                  <input
                    className="form-input"
                    required
                    value={groupForm.name}
                    onChange={(event) => setGroupForm({ ...groupForm, name: event.target.value })}
                    placeholder="Например: Математика 9 класс"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Описание</label>
                  <textarea
                    className="form-textarea"
                    rows={3}
                    value={groupForm.description}
                    onChange={(event) =>
                      setGroupForm({ ...groupForm, description: event.target.value })
                    }
                    placeholder="Дополнительная информация о группе"
                  />
                </div>
                <div className="gm-actions">
                  <button className="gm-btn-primary" type="submit" disabled={creating}>
                    {creating ? 'Сохранение...' : editingId ? 'Сохранить' : 'Создать группу'}
                  </button>
                  {editingId && (
                    <button
                      type="button"
                      className="gm-btn-surface"
                      onClick={resetGroupForm}
                      disabled={creating}
                    >
                      Отмена
                    </button>
                  )}
                </div>
              </form>
            </div>
          ) : (
            <IndividualInviteForm data={invitesData} />
          )}
        </div>

        <div className="groups-manage-column">
          {activePanel === 'group' ? (
            <div className="gm-card">
              <div className="gm-card-heading">
                <div>
                  <h3 className="gm-card-title">📋 Мои группы</h3>
                  <p className="gm-card-subtitle">
                    {groups.length
                      ? 'Выберите группу, чтобы отредактировать данные или управлять учениками.'
                      : 'Пока нет групп — создайте первую, чтобы начать обучение.'}
                  </p>
                </div>
                <span className="gm-badge gm-badge-blue">{groups.length}</span>
              </div>

              <div className="gm-groups-list">
                {groups.map((group) => {
                  const studentCount = Array.isArray(group.students)
                    ? group.students.length
                    : group.student_count || 0;

                  return (
                    <article
                      key={group.id}
                      className={`gm-group-card ${editingId === group.id ? 'is-active' : ''}`}
                    >
                      <div className="gm-group-card-header">
                        <div>
                          <button
                            type="button"
                            className="gm-group-name"
                            onClick={() => startEdit(group)}
                          >
                            {group.name}
                          </button>
                          <p className="gm-group-description">{group.description || 'Без описания'}</p>
                        </div>
                        <span className="gm-badge">{studentCount} уч.</span>
                      </div>
                      <div className="gm-group-card-actions">
                        <button
                          type="button"
                          className="gm-btn-primary"
                          onClick={() => navigate(`/attendance/${group.id}`)}
                        >
                          Открыть
                        </button>
                        <button
                          type="button"
                          className="gm-btn-surface"
                          onClick={() => startEdit(group)}
                        >
                          Изменить
                        </button>
                        <button
                          type="button"
                          className="gm-btn-surface"
                          onClick={() => setInviteModalGroup(group)}
                        >
                          Пригласить
                        </button>
                        <button
                          type="button"
                          className="gm-btn-surface"
                          onClick={() => setStudentsModalGroup(group)}
                        >
                          Ученики
                        </button>
                        <button
                          type="button"
                          className="gm-btn-danger"
                          onClick={() => handleDelete(group.id)}
                        >
                          Удалить
                        </button>
                      </div>
                    </article>
                  );
                })}

                {groups.length === 0 && (
                  <div className="gm-empty-state">
                    <div className="gm-empty-icon">📂</div>
                    <p>Нет групп. Создайте первую!</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <IndividualInviteList data={invitesData} />
          )}
        </div>
      </div>

      <ConfirmModal
        isOpen={confirmModal.isOpen}
        onClose={() => setConfirmModal({ ...confirmModal, isOpen: false })}
        onConfirm={confirmModal.onConfirm}
        title={confirmModal.title}
        message={confirmModal.message}
        variant={confirmModal.variant}
        confirmText={confirmModal.confirmText}
        cancelText={confirmModal.cancelText}
      />

      <ConfirmModal
        isOpen={alertModal.isOpen}
        onClose={() => setAlertModal({ ...alertModal, isOpen: false })}
        onConfirm={() => setAlertModal({ ...alertModal, isOpen: false })}
        title={alertModal.title}
        message={alertModal.message}
        variant={alertModal.variant}
        confirmText="OK"
        cancelText=""
      />

      {inviteModalGroup && (
        <GroupInviteModal
          group={inviteModalGroup}
          onClose={() => setInviteModalGroup(null)}
        />
      )}

      {/* Модальное окно управления учениками */}
      <GroupStudentsModal
        group={studentsModalGroup}
        allGroups={groups}
        isOpen={!!studentsModalGroup}
        onClose={() => setStudentsModalGroup(null)}
        onStudentsRemoved={load}
      />

      {/* Модальное окно карточки группы */}
      <GroupDetailModal
        group={detailModal.group}
        isOpen={detailModal.isOpen}
        onClose={() => setDetailModal({ isOpen: false, group: null })}
        onStudentClick={(studentId, groupId) => {
          setStudentModal({ isOpen: true, studentId, groupId });
        }}
      />

      {/* Модальное окно карточки ученика */}
      <StudentCardModal
        studentId={studentModal.studentId}
        groupId={studentModal.groupId}
        isOpen={studentModal.isOpen}
        onClose={() => setStudentModal({ isOpen: false, studentId: null, groupId: null })}
      />
    </div>
  );
};

export default GroupsManage;