import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getIndividualInviteCodes,
  createIndividualInviteCode,
  updateIndividualInviteCode,
  deleteIndividualInviteCode,
  getAccessToken,
} from '../apiService';
import { ConfirmModal, Modal } from '../shared/components';
import IndividualInviteModal from './IndividualInviteModal';
import '../styles/IndividualInvitesManage.css';

const STORAGE_KEY_PREFIX = 'tp_invite_descriptions_';

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

const getStorageKey = () => {
  const userId = getCurrentUserId();
  return userId ? `${STORAGE_KEY_PREFIX}${userId}` : null;
};

const loadDescriptionMap = () => {
  try {
    const key = getStorageKey();
    if (!key) return {};
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : {};
  } catch (_) {
    return {};
  }
};

const persistDescriptionMap = (next) => {
  const key = getStorageKey();
  if (!key) return;
  try {
    localStorage.setItem(key, JSON.stringify(next));
  } catch (_) {
    /* ignore */
  }
};

const normalizeCodes = (value) => {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.results)) return value.results;
  return [];
};

export const useIndividualInvitesData = () => {
  const [codes, setCodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState('');
  const [loadError, setLoadError] = useState('');
  const [selectedCode, setSelectedCode] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);
  const [descriptionMap, setDescriptionMap] = useState({});
  
  // Редактирование
  const [editingCode, setEditingCode] = useState(null);
  const [editSubject, setEditSubject] = useState('');
  const [saving, setSaving] = useState(false);
  
  // Модалка ученика
  const [studentModalCode, setStudentModalCode] = useState(null);

  useEffect(() => {
    setDescriptionMap(loadDescriptionMap());
  }, []);

  useEffect(() => {
    fetchCodes();
  }, []);

  const fetchCodes = async () => {
    setLoading(true);
    try {
      const { data } = await getIndividualInviteCodes();
      setCodes(normalizeCodes(data));
      setLoadError('');
    } catch (err) {
      console.error('Failed to fetch codes:', err);
      setLoadError('Ошибка при загрузке кодов');
      setCodes([]);
    } finally {
      setLoading(false);
    }
  };

  const safeCodes = useMemo(
    () =>
      normalizeCodes(codes).map((code) => ({
        ...code,
        description: descriptionMap[code.invite_code] || '',
      })),
    [codes, descriptionMap]
  );

  const handleCreate = async (event) => {
    event.preventDefault();
    const trimmedSubject = subject.trim();
    if (!trimmedSubject) {
      setFormError('Введите название предмета');
      return;
    }

    setCreating(true);
    try {
      const { data } = await createIndividualInviteCode({ subject: trimmedSubject });
      const descriptionValue = description.trim();
      const nextCodes = [data, ...normalizeCodes(codes)];
      setCodes(nextCodes);

      if (descriptionValue) {
        const nextMap = { ...descriptionMap, [data.invite_code]: descriptionValue };
        setDescriptionMap(nextMap);
        persistDescriptionMap(nextMap);
      }

      setSubject('');
      setDescription('');
      setFormError('');
    } catch (err) {
      console.error('Failed to create code:', err);
      setFormError('Ошибка при создании кода');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (codeId, inviteCode) => {
    try {
      await deleteIndividualInviteCode(codeId);
      setCodes((prev) => normalizeCodes(prev).filter((c) => c.id !== codeId));

      if (inviteCode && descriptionMap[inviteCode]) {
        const { [inviteCode]: _, ...rest } = descriptionMap;
        setDescriptionMap(rest);
        persistDescriptionMap(rest);
      }

      setShowDeleteConfirm(null);
    } catch (err) {
      console.error('Failed to delete code:', err);
      setFormError('Ошибка при удалении кода');
    }
  };
  
  const startEdit = (code) => {
    setEditingCode(code);
    setEditSubject(code.subject || '');
  };
  
  const cancelEdit = () => {
    setEditingCode(null);
    setEditSubject('');
  };
  
  const handleSaveEdit = async () => {
    if (!editingCode) return;
    const trimmed = editSubject.trim();
    if (!trimmed) {
      setFormError('Введите название предмета');
      return;
    }
    
    setSaving(true);
    try {
      const { data } = await updateIndividualInviteCode(editingCode.id, { subject: trimmed });
      setCodes((prev) => 
        normalizeCodes(prev).map((c) => c.id === data.id ? { ...c, ...data } : c)
      );
      setEditingCode(null);
      setEditSubject('');
      setFormError('');
    } catch (err) {
      console.error('Failed to update code:', err);
      setFormError('Ошибка при сохранении');
    } finally {
      setSaving(false);
    }
  };

  return {
    // lists
    safeCodes,
    loading,
    loadError,
    setLoadError,
    // form
    subject,
    setSubject,
    description,
    setDescription,
    creating,
    formError,
    setFormError,
    handleCreate,
    // modals
    selectedCode,
    setSelectedCode,
    showDeleteConfirm,
    setShowDeleteConfirm,
    handleDelete,
    // editing
    editingCode,
    editSubject,
    setEditSubject,
    saving,
    startEdit,
    cancelEdit,
    handleSaveEdit,
    // student modal
    studentModalCode,
    setStudentModalCode,
  };
};

const IndividualInviteForm = ({ data }) => (
  <div className="gm-card iim-form-card">
    <div className="gm-card-heading">
      <div>
        <h3 className="gm-card-title">Индивидуальный ученик</h3>
        <p className="gm-card-subtitle">
          Создайте приглашение для индивидуального занятия. Код генерируется автоматически.
        </p>
      </div>
    </div>

    <form className="gm-form" onSubmit={data.handleCreate}>
      <div className="form-group">
        <label className="form-label">Название предмета</label>
        <input
          className="form-input"
          type="text"
          placeholder="Например: Математика 9 класс"
          value={data.subject}
          onChange={(e) => {
            data.setSubject(e.target.value);
            data.setFormError('');
          }}
          disabled={data.creating}
        />
      </div>
      <div className="form-group">
        <label className="form-label">Описание</label>
        <textarea
          className="form-textarea"
          rows={3}
          placeholder="Дополнительная информация"
          value={data.description}
          onChange={(e) => {
            data.setDescription(e.target.value);
            data.setFormError('');
          }}
          disabled={data.creating}
        />
      </div>
      {data.formError && <p className="iim-error-text">{data.formError}</p>}
      <div className="gm-actions">
        <button
          type="submit"
          className="gm-btn-primary"
          disabled={data.creating}
        >
          {data.creating ? 'Создание...' : 'Создать приглашение'}
        </button>
      </div>
    </form>
  </div>
);

const IndividualInviteList = ({ data, navigate }) => {
  const getInitials = (name) => {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    return parts.map(p => p[0] || '').join('').toUpperCase().slice(0, 2) || '?';
  };

  return (
  <div className="gm-card iim-list-card">
    <div className="gm-card-heading">
      <div>
        <h3 className="gm-card-title">Индивидуальные ученики</h3>
        <p className="gm-card-subtitle">
          {data.safeCodes.length
            ? 'Пригласите ученика по коду или ссылке. После регистрации ученик появится здесь.'
            : 'Создайте первое приглашение для индивидуального ученика.'}
        </p>
      </div>
      <span className="gm-badge gm-badge-blue">{data.safeCodes.length}</span>
    </div>

    {data.loadError && <div className="iim-error-text">{data.loadError}</div>}

    {data.loading ? (
      <div className="iim-loading">Загрузка...</div>
    ) : data.safeCodes.length === 0 ? (
      <div className="gm-empty-state">
        <p>Нет приглашений. Создайте первое!</p>
      </div>
    ) : (
      <div className="gm-groups-list">
        {data.safeCodes.map((code) => {
          const studentName = code.used_by_name || code.used_by_email || null;
          const descriptionText = code.description?.trim() || 'Без описания';
          const isEditing = data.editingCode?.id === code.id;

          return (
            <article key={code.id} className={`gm-group-card ${isEditing ? 'is-active' : ''}`}>
              <div className="gm-group-card-header">
                <div>
                  {isEditing ? (
                    <input
                      className="form-input iim-edit-input"
                      type="text"
                      value={data.editSubject}
                      onChange={(e) => data.setEditSubject(e.target.value)}
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') data.handleSaveEdit();
                        if (e.key === 'Escape') data.cancelEdit();
                      }}
                    />
                  ) : (
                    <button
                      type="button"
                      className="gm-group-name"
                      onClick={() => data.startEdit(code)}
                    >
                      {code.subject || 'Без названия'}
                    </button>
                  )}
                  <p className="gm-group-description">{descriptionText}</p>
                  {code.is_used && studentName && (
                    <p className="gm-group-description" style={{ marginTop: '0.25rem' }}>
                      <strong>Ученик:</strong> {studentName}
                    </p>
                  )}
                </div>
                <span className={`gm-badge ${code.is_used ? 'gm-badge-blue' : 'gm-badge-success'}`}>
                  {code.is_used ? '1 уч.' : 'Ожидает'}
                </span>
              </div>

              <div className="iim-code-row">
                <span className="iim-code-label">Код:</span>
                <span className="iim-code-value">{code.invite_code}</span>
              </div>

              <div className="gm-group-card-actions">
                {isEditing ? (
                  <>
                    <button
                      type="button"
                      className="gm-btn-primary"
                      onClick={data.handleSaveEdit}
                      disabled={data.saving}
                    >
                      {data.saving ? 'Сохранение...' : 'Сохранить'}
                    </button>
                    <button
                      type="button"
                      className="gm-btn-surface"
                      onClick={data.cancelEdit}
                      disabled={data.saving}
                    >
                      Отмена
                    </button>
                  </>
                ) : (
                  <>
                    {/* Открыть - только для присоединившихся */}
                    {code.is_used && code.group_id && (
                      <button
                        type="button"
                        className="gm-btn-primary"
                        onClick={() => navigate && navigate(`/attendance/${code.group_id}`)}
                      >
                        Открыть
                      </button>
                    )}
                    <button
                      type="button"
                      className="gm-btn-surface"
                      onClick={() => data.startEdit(code)}
                    >
                      Изменить
                    </button>
                    <button
                      type="button"
                      className="gm-btn-surface"
                      onClick={() => data.setSelectedCode(code)}
                    >
                      Пригласить
                    </button>
                    {/* Ученики - только для присоединившихся */}
                    {code.is_used && (
                      <button
                        type="button"
                        className="gm-btn-surface"
                        onClick={() => data.setStudentModalCode(code)}
                      >
                        Ученик
                      </button>
                    )}
                    <button
                      type="button"
                      className="gm-btn-danger"
                      onClick={() => data.setShowDeleteConfirm(code)}
                      disabled={code.is_used}
                    >
                      Удалить
                    </button>
                  </>
                )}
              </div>
            </article>
          );
        })}
      </div>
    )}

    {data.selectedCode && (
      <IndividualInviteModal
        code={data.selectedCode}
        onClose={() => data.setSelectedCode(null)}
      />
    )}

    {data.showDeleteConfirm && (
      <ConfirmModal
        isOpen={Boolean(data.showDeleteConfirm)}
        onClose={() => data.setShowDeleteConfirm(null)}
        onConfirm={() =>
          data.handleDelete(data.showDeleteConfirm.id, data.showDeleteConfirm.invite_code)
        }
        title="Удалить приглашение?"
        message={`Удалить код для предмета "${data.showDeleteConfirm.subject || 'Без названия'}"?`}
        variant="danger"
        confirmText="Удалить"
        cancelText="Отмена"
      />
    )}

    {/* Модалка ученика */}
    {data.studentModalCode && (
      <Modal
        isOpen={Boolean(data.studentModalCode)}
        onClose={() => data.setStudentModalCode(null)}
        title="Ученик"
        size="small"
      >
        <div className="iim-student-modal">
          <div className="iim-student-info">
            <div className="iim-student-avatar">
              {getInitials(data.studentModalCode.used_by_name)}
            </div>
            <div className="iim-student-details">
              <div className="iim-student-name">
                {data.studentModalCode.used_by_name || 'Без имени'}
              </div>
              {data.studentModalCode.used_by_email && (
                <div className="iim-student-email">{data.studentModalCode.used_by_email}</div>
              )}
            </div>
          </div>
          <div className="iim-student-meta">
            <div className="iim-meta-row">
              <span className="iim-meta-label">Предмет:</span>
              <span className="iim-meta-value">{data.studentModalCode.subject}</span>
            </div>
            {data.studentModalCode.used_at && (
              <div className="iim-meta-row">
                <span className="iim-meta-label">Присоединился:</span>
                <span className="iim-meta-value">
                  {new Date(data.studentModalCode.used_at).toLocaleDateString('ru-RU', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric'
                  })}
                </span>
              </div>
            )}
          </div>
        </div>
      </Modal>
    )}
  </div>
);
};

const IndividualInvitesManage = ({ mode = 'full', data: providedData, navigate: providedNavigate }) => {
  const hookData = useIndividualInvitesData();
  const internalNavigate = useNavigate();
  const data = providedData || hookData;
  const navigate = providedNavigate || internalNavigate;

  if (mode === 'form') {
    return <IndividualInviteForm data={data} />;
  }

  if (mode === 'list') {
    return <IndividualInviteList data={data} navigate={navigate} />;
  }

  return (
    <div className="individual-invites-manage">
      <IndividualInviteForm data={data} />
      <IndividualInviteList data={data} navigate={navigate} />
    </div>
  );
};

export { IndividualInviteForm, IndividualInviteList };
export default IndividualInvitesManage;
