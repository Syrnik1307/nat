import React, { useEffect, useMemo, useState } from 'react';
import {
  getIndividualInviteCodes,
  createIndividualInviteCode,
  deleteIndividualInviteCode,
  getAccessToken,
} from '../apiService';
import { ConfirmModal } from '../shared/components';
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
  };
};

const IndividualInviteForm = ({ data }) => (
  <div className="gm-card iim-form-card">
    <div className="gm-card-heading">
      <div>
        <h3 className="gm-card-title">Индивидуальный ученик</h3>
        <p className="gm-card-subtitle">
          Название предмета и описание как у групп, код генерится автоматически.
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

const IndividualInviteList = ({ data }) => (
  <div className="gm-card iim-list-card">
    <div className="gm-card-heading">
      <div>
        <h3 className="gm-card-title">Индивидуальные приглашения</h3>
        <p className="gm-card-subtitle">Приглашения работают как групповые: код, ссылка, QR.</p>
      </div>
      <span className="gm-badge gm-badge-blue">{data.safeCodes.length}</span>
    </div>

    {data.loadError && <div className="iim-error-text">{data.loadError}</div>}

    {data.loading ? (
      <div className="iim-loading">Загрузка...</div>
    ) : data.safeCodes.length === 0 ? (
      <div className="iim-empty">
        <div className="iim-empty-icon">📭</div>
        <p>Нет приглашений. Создайте первое!</p>
      </div>
    ) : (
      <div className="iim-list">
        {data.safeCodes.map((code) => {
          const descriptionText = code.description?.trim()
            ? code.description
            : 'Нет описания';
          return (
            <div key={code.id} className="iim-invite-card">
              <div className="iim-invite-header">
                <div className="iim-invite-meta">
                  <div className="iim-invite-subject">{code.subject || 'Без названия'}</div>
                  <div className="iim-invite-description">{descriptionText}</div>
                </div>
                <span className={`iim-status ${code.is_used ? 'used' : 'active'}`}>
                  {code.is_used ? 'Использован' : 'Активен'}
                </span>
              </div>

              <div className="iim-code-row">
                <span className="iim-code-label">Код:</span>
                <span className="iim-code-value">{code.invite_code}</span>
              </div>

              <div className="iim-actions-row">
                <button
                  type="button"
                  className="gm-btn-primary"
                  onClick={() => data.setSelectedCode(code)}
                >
                  📩 Пригласить
                </button>
                <button
                  type="button"
                  className="gm-btn-danger"
                  onClick={() => data.setShowDeleteConfirm(code)}
                  disabled={code.is_used}
                >
                  Удалить
                </button>
              </div>
            </div>
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
  </div>
);

const IndividualInvitesManage = ({ mode = 'full', data: providedData }) => {
  const hookData = useIndividualInvitesData();
  const data = providedData || hookData;

  if (mode === 'form') {
    return <IndividualInviteForm data={data} />;
  }

  if (mode === 'list') {
    return <IndividualInviteList data={data} />;
  }

  return (
    <div className="individual-invites-manage">
      <IndividualInviteForm data={data} />
      <IndividualInviteList data={data} />
    </div>
  );
};

export { IndividualInviteForm, IndividualInviteList };
export default IndividualInvitesManage;
