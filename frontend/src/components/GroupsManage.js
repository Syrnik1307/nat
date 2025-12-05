import React, { useEffect, useState } from 'react';
import {
  getGroups,
  createGroup,
  updateGroup,
  deleteGroup,
  addStudentsToGroup,
  removeStudentsFromGroup,
  createIndividualInviteCode,
  getIndividualInviteCodes,
  deleteIndividualInviteCode,
} from '../apiService';
import { getAccessToken } from '../apiService';
import GroupInviteModal from './GroupInviteModal';
import IndividualInviteModal from './IndividualInviteModal';
import './GroupsManage.css';
import { ConfirmModal } from '../shared/components';

const initialGroupForm = { name: '', description: '' };
// Student accounts создаются через код — ручная регистрация убрана

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
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  const [activePanel, setActivePanel] = useState('group');
  const [groupForm, setGroupForm] = useState(initialGroupForm);
  const [editingId, setEditingId] = useState(null);
  const [studentOpsGroup, setStudentOpsGroup] = useState(null);
  const [inviteModalGroup, setInviteModalGroup] = useState(null);
  const [addIds, setAddIds] = useState('');
  const [removeIds, setRemoveIds] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
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
  const [filterActive, setFilterActive] = useState('all'); // 'all' | 'with_students' | 'empty'
  const [individualInvite, setIndividualInvite] = useState(null);
  const [individualCodes, setIndividualCodes] = useState([]);
  const [individualLoading, setIndividualLoading] = useState(false);
  const [individualSubject, setIndividualSubject] = useState('');
  const [individualDescription, setIndividualDescription] = useState('');
  const [individualError, setIndividualError] = useState('');
  const [individualDelete, setIndividualDelete] = useState(null);

  const resetGroupForm = () => {
    setGroupForm(initialGroupForm);
    setEditingId(null);
  };

  const parseIds = (value) =>
    value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => Number(item))
      .filter((item) => Number.isFinite(item));

  const load = async () => {
    try {
      const res = await getGroups();
      const data = Array.isArray(res.data) ? res.data : res.data.results || [];
      setGroups(data);
      setStudentOpsGroup((current) => {
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
    loadIndividuals();
  }, []);

  const handleTabSelect = (panel) => {
    if (panel === 'group') {
      resetGroupForm();
    }
    if (panel === 'individual') {
      loadIndividuals();
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

  const normalizeIndividuals = (value) => {
    if (Array.isArray(value)) return value;
    if (Array.isArray(value?.results)) return value.results;
    return [];
  };

  const loadIndividuals = async () => {
    setIndividualLoading(true);
    try {
      const { data } = await getIndividualInviteCodes();
      setIndividualCodes(normalizeIndividuals(data));
      setIndividualError('');
    } catch (e) {
      setIndividualError('Ошибка загрузки индивидуальных приглашений');
      setIndividualCodes([]);
    } finally {
      setIndividualLoading(false);
    }
  };

  const handleCreateIndividual = async (event) => {
    event.preventDefault();
    if (!individualSubject.trim()) {
      setIndividualError('Введите название предмета');
      return;
    }
    setCreating(true);
    setIndividualError('');
    try {
      const payload = {
        subject: individualSubject.trim(),
        description: individualDescription.trim(),
      };
      const { data } = await createIndividualInviteCode(payload);
      const created = data?.code || data;
      setIndividualCodes((prev) => [created, ...normalizeIndividuals(prev)]);
      setIndividualSubject('');
      setIndividualDescription('');
    } catch (e) {
      setIndividualError('Ошибка при создании приглашения');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteIndividual = async () => {
    if (!individualDelete) return;
    try {
      await deleteIndividualInviteCode(individualDelete.id);
      setIndividualCodes((prev) => normalizeIndividuals(prev).filter((c) => c.id !== individualDelete.id));
      setIndividualDelete(null);
    } catch (e) {
      setIndividualError('Ошибка при удалении приглашения');
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
        setConfirmModal({ ...confirmModal, isOpen: false });
      }
    });
  };

  const openStudentOps = (group) => {
    setStudentOpsGroup(group);
    setAddIds('');
    setRemoveIds('');
  };

  const closeStudentOps = () => setStudentOpsGroup(null);

  const commitAddStudents = async () => {
    if (!studentOpsGroup) return;
    const ids = parseIds(addIds);
    if (!ids.length) return;

    try {
      await addStudentsToGroup(studentOpsGroup.id, ids);
      await load();
      setAddIds('');
    } catch (e) {
      setAlertModal({
        isOpen: true,
        title: 'Ошибка',
        message: e.response?.data ? JSON.stringify(e.response.data) : 'Ошибка добавления',
        variant: 'danger'
      });
    }
  };

  const commitRemoveStudents = async () => {
    if (!studentOpsGroup) return;
    const ids = parseIds(removeIds);
    if (!ids.length) return;

    try {
      await removeStudentsFromGroup(studentOpsGroup.id, ids);
      await load();
      setRemoveIds('');
    } catch (e) {
      setAlertModal({
        isOpen: true,
        title: 'Ошибка',
        message: e.response?.data ? JSON.stringify(e.response.data) : 'Ошибка удаления',
        variant: 'danger'
      });
    }
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
            <>
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
                        ✕ Отмена
                      </button>
                    )}

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
                  </div>
                </form>
              </div>
            </>
          ) : (
            <>
              <div className="gm-card">
                <div className="gm-card-heading">
                  <div>
                    <h3 className="gm-card-title">Индивидуальный ученик</h3>
                    <p className="gm-card-subtitle">Название предмета и описание как у групп, код генерится автоматически.</p>
                  </div>
                </div>
                <form className="gm-form" onSubmit={handleCreateIndividual}>
                  <div className="form-group">
                    <label className="form-label">Название предмета</label>
                    <input
                      className="form-input"
                      required
                      value={individualSubject}
                      onChange={(event) => setIndividualSubject(event.target.value)}
                      placeholder="Например: Математика 9 класс"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Описание</label>
                    <textarea
                      className="form-textarea"
                      rows={3}
                      value={individualDescription}
                      onChange={(event) => setIndividualDescription(event.target.value)}
                      placeholder="Дополнительная информация"
                    />
                  </div>
                  <div className="gm-actions">
                    <button className="gm-btn-primary" type="submit" disabled={creating}>
                      {creating ? 'Создание...' : 'Создать приглашение'}
                    </button>
                  </div>
                  {individualError && <p className="gm-hint gm-text-error">{individualError}</p>}
                </form>
              </div>

              <div className="gm-card">
                <div className="gm-card-heading">
                  <div>
                    <h3 className="gm-card-title">📋 Индивидуальные приглашения</h3>
                    <p className="gm-card-subtitle">Приглашения работают как групповые: код, ссылка, QR.</p>
                  </div>
                  <span className="gm-badge gm-badge-blue">{individualCodes.length}</span>
                </div>

                {individualLoading ? (
                  <div className="gm-state gm-state-loading">Загрузка...</div>
                ) : individualCodes.length === 0 ? (
                  <div className="gm-empty-state">
                    <div className="gm-empty-icon">📭</div>
                    <p>Нет приглашений. Создайте первое.</p>
                  </div>
                ) : (
                  <div className="gm-groups-list">
                    {individualCodes.map((item) => {
                      const isUsed = item.is_used;
                      return (
                        <article key={item.id} className="gm-group-card">
                          <div className="gm-group-card-header">
                            <div>
                              <div className="gm-group-name" style={{ cursor: 'default' }}>
                                {item.subject || 'Без названия'}
                              </div>
                              <p className="gm-group-description">{item.description || 'Нет описания'}</p>
                              <p className="gm-hint" style={{ marginTop: '0.25rem' }}>Код: {item.invite_code}</p>
                            </div>
                            <span className={`gm-badge ${isUsed ? 'gm-badge-muted' : 'gm-badge-blue'}`}>
                              {isUsed ? 'Использован' : 'Активен'}
                            </span>
                          </div>
                          <div className="gm-group-card-actions">
                            <button
                              type="button"
                              className="gm-btn-primary"
                              onClick={() => setIndividualInvite(item)}
                            >
                              📨 Пригласить
                            </button>
                            <button
                              type="button"
                              className="gm-btn-surface"
                              onClick={() => setIndividualDelete(item)}
                            >
                              Удалить
                            </button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {activePanel === 'group' && (
          <div className="groups-manage-column">
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
                          className="gm-btn-surface"
                          onClick={() => startEdit(group)}
                        >
                          Изменить
                        </button>
                        <button
                          type="button"
                          className="gm-btn-primary"
                          onClick={() => setInviteModalGroup(group)}
                        >
                          📨 Пригласить
                        </button>
                        <button
                          type="button"
                          className="gm-btn-surface"
                          onClick={() => openStudentOps(group)}
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
          </div>
        )}
      </div>

      {inviteModalGroup && (
        <GroupInviteModal
          group={inviteModalGroup}
          onClose={() => setInviteModalGroup(null)}
        />
      )}

      {individualInvite && (
        <IndividualInviteModal
          code={individualInvite}
          onClose={() => setIndividualInvite(null)}
        />
      )}

      {studentOpsGroup && (
        <div className="gm-modal-backdrop" onClick={closeStudentOps}>
          <div className="gm-modal" onClick={(event) => event.stopPropagation()}>
            <div className="gm-modal-header">
              <h3 className="gm-modal-title">Ученики группы: {studentOpsGroup.name}</h3>
              <button type="button" className="gm-modal-close" onClick={closeStudentOps}>
                ✕
              </button>
            </div>
            <div className="gm-modal-body">
              <div className="gm-modal-section">
                <span className="gm-modal-label">Текущие ученики</span>
                <div className="gm-modal-student-list">
                  {Array.isArray(studentOpsGroup.students) && studentOpsGroup.students.length ? (
                    studentOpsGroup.students.map((student) => (
                      <div key={student.id} className="gm-modal-student">
                        <span>
                          {student.first_name || ''} {student.last_name || ''}
                        </span>
                        <span className="gm-badge gm-badge-muted">#{student.id}</span>
                      </div>
                    ))
                  ) : (
                    <div className="gm-modal-empty">Нет учеников</div>
                  )}
                </div>
              </div>

              <div className="gm-modal-section">
                <p style={{padding: '1rem', background: '#f0f9ff', borderRadius: '8px', color: '#0369a1', fontSize: '0.9rem'}}>
                  <strong>Как добавить учеников:</strong> Нажмите кнопку "Пригласить" в карточке группы и поделитесь кодом приглашения с учениками.
                </p>
              </div>

              <div className="gm-modal-controls">
                <div className="gm-modal-column" style={{width: '100%'}}>
                  <label className="gm-modal-label">Удалить учеников (ID через запятую)</label>
                  <input
                    className="gm-modal-input"
                    value={removeIds}
                    onChange={(event) => setRemoveIds(event.target.value)}
                    placeholder="1, 2, 3"
                  />
                  <button type="button" className="gm-btn-danger gm-btn-block" onClick={commitRemoveStudents}>
                    Удалить из группы
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {individualDelete && (
        <ConfirmModal
          title="Удалить приглашение?"
          message={`Удалить приглашение для предмета "${individualDelete.subject || ''}"?`}
          onConfirm={handleDeleteIndividual}
          onCancel={() => setIndividualDelete(null)}
          confirmText="Удалить"
          cancelText="Отмена"
          danger
        />
      )}
    </div>
  );
};

export default GroupsManage;