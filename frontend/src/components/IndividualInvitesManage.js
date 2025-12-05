import React, { useState, useEffect } from 'react';
import {
  getIndividualInviteCodes,
  createIndividualInviteCode,
  deleteIndividualInviteCode,
} from '../apiService';
import { ConfirmModal } from '../shared/components';
import IndividualInviteModal from './IndividualInviteModal';
import '../styles/IndividualInvitesManage.css';

const IndividualInvitesManage = () => {
  const [codes, setCodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [subject, setSubject] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [selectedCode, setSelectedCode] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);

  useEffect(() => {
    fetchCodes();
  }, []);

  const normalizeCodes = (value) => {
    if (Array.isArray(value)) return value;
    if (Array.isArray(value?.results)) return value.results;
    return [];
  };

  const fetchCodes = async () => {
    setLoading(true);
    try {
      const { data } = await getIndividualInviteCodes();
      setCodes(normalizeCodes(data));
    } catch (err) {
      console.error('Failed to fetch codes:', err);
      setError('Ошибка при загрузке кодов');
      setCodes([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!subject.trim()) {
      setError('Введите название предмета');
      return;
    }

    setCreating(true);
    try {
      const { data } = await createIndividualInviteCode({ subject: subject.trim() });
      setCodes((prev) => [data, ...normalizeCodes(prev)]);
      setSubject('');
      setError('');
    } catch (err) {
      console.error('Failed to create code:', err);
      setError('Ошибка при создании кода');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (codeId) => {
    try {
      await deleteIndividualInviteCode(codeId);
      setCodes((prev) => normalizeCodes(prev).filter((c) => c.id !== codeId));
      setShowDeleteConfirm(null);
    } catch (err) {
      console.error('Failed to delete code:', err);
      setError('Ошибка при удалении кода');
    }
  };

  const safeCodes = normalizeCodes(codes);

  const getActiveCount = () => safeCodes.filter(c => !c.is_used).length;
  const getUsedCount = () => safeCodes.filter(c => c.is_used).length;

  return (
    <div className="individual-invites-manage">
      <div className="iim-header">
        <h2>📧 Индивидуальные приглашения</h2>
        <p className="subtitle">Создавайте коды для приглашения учеников на отдельные предметы</p>
      </div>

      <div className="iim-stats">
        <div className="stat-card active">
          <div className="stat-number">{getActiveCount()}</div>
          <div className="stat-label">Активные коды</div>
        </div>
        <div className="stat-card used">
          <div className="stat-number">{getUsedCount()}</div>
          <div className="stat-label">Использовано</div>
        </div>
        <div className="stat-card total">
          <div className="stat-number">{safeCodes.length}</div>
          <div className="stat-label">Всего кодов</div>
        </div>
      </div>

      {/* Форма создания */}
      <form className="iim-create-form" onSubmit={handleCreate}>
        <h3>Создать новый код</h3>
        <div className="form-group">
          <input
            type="text"
            placeholder="Название предмета (е.г. Математика, Физика)"
            value={subject}
            onChange={(e) => {
              setSubject(e.target.value);
              setError('');
            }}
            disabled={creating}
          />
          <button
            type="submit"
            className="btn-primary"
            disabled={creating || !subject.trim()}
          >
            {creating ? 'Создание...' : '+ Создать код'}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </form>

      {/* Список кодов */}
      <div className="iim-codes-list">
        <h3>Мои коды</h3>
        
        {loading ? (
          <div className="loading-spinner">⏳ Загрузка...</div>
        ) : safeCodes.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📭</div>
            <p>Нет кодов. Создайте первый!</p>
          </div>
        ) : (
          <>
            {/* Активные коды */}
            <div className="codes-section">
              <h4>Активные коды ({getActiveCount()})</h4>
              {safeCodes.filter(c => !c.is_used).length === 0 ? (
                <p className="text-muted">Нет активных кодов</p>
              ) : (
                <div className="codes-grid">
                  {safeCodes.filter(c => !c.is_used).map(code => (
                    <div key={code.id} className="code-card active">
                      <div className="code-header">
                        <span className="code-subject">{code.subject}</span>
                        <span className="code-status">○ Активен</span>
                      </div>
                      <div className="code-display">{code.invite_code}</div>
                      <div className="code-actions">
                        <button
                          className="btn-secondary"
                          onClick={() => setSelectedCode(code)}
                          title="Показать детали"
                        >
                          🔗 Пригласить
                        </button>
                        <button
                          className="btn-danger"
                          onClick={() => setShowDeleteConfirm(code)}
                          title="Удалить код"
                        >
                          🗑️
                        </button>
                      </div>
                      <div className="code-date">
                        Создан: {new Date(code.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Использованные коды */}
            {getUsedCount() > 0 && (
              <div className="codes-section used-codes">
                <h4>Использованные коды ({getUsedCount()})</h4>
                <div className="codes-grid">
                  {safeCodes.filter(c => c.is_used).map(code => (
                    <div key={code.id} className="code-card used">
                      <div className="code-header">
                        <span className="code-subject">{code.subject}</span>
                        <span className="code-status">✓ Использован</span>
                      </div>
                      <div className="code-display">{code.invite_code}</div>
                      <div className="code-used-by">
                        <strong>Ученик:</strong> {code.used_by_name || code.used_by_email}
                      </div>
                      <div className="code-date">
                        Использован: {new Date(code.used_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Модальные окна */}
      {selectedCode && (
        <IndividualInviteModal
          code={selectedCode}
          onClose={() => setSelectedCode(null)}
        />
      )}

      {showDeleteConfirm && (
        <ConfirmModal
          title="Удалить код?"
          message={`Удалить код для предмета "${showDeleteConfirm.subject}"? Это действие нельзя отменить.`}
          onConfirm={() => handleDelete(showDeleteConfirm.id)}
          onCancel={() => setShowDeleteConfirm(null)}
          confirmText="Удалить"
          cancelText="Отмена"
          danger={true}
        />
      )}
    </div>
  );
};

export default IndividualInvitesManage;
