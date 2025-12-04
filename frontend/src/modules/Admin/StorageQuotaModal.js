import React, { useEffect, useMemo, useState } from 'react';
import api from '../../apiService';
import { Notification, ConfirmModal } from '../../shared/components';
import useNotification from '../../shared/hooks/useNotification';
import './StorageQuotaModal.css';

const formatBytes = (bytes) => {
  if (bytes === null || bytes === undefined) return '—';
  const gb = bytes / (1024 * 1024 * 1024);
  return `${gb.toFixed(2)} ГБ`;
};

const usagePercent = (quota) => {
  if (!quota?.max_bytes) return 0;
  return Math.min(100, Math.round((quota.used_bytes / quota.max_bytes) * 100));
};

const StorageQuotaModal = ({ onClose }) => {
  const { notification, confirm, showNotification, closeNotification, showConfirm, closeConfirm } = useNotification();
  const [quotas, setQuotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [selectedQuota, setSelectedQuota] = useState(null);
  const [materials, setMaterials] = useState([]);
  const [materialsLoading, setMaterialsLoading] = useState(false);
  const [increaseAmount, setIncreaseAmount] = useState(5);
  const [filters, setFilters] = useState({ exceeded: 'all', warning: 'all', sort: '-used_bytes' });
  const [busy, setBusy] = useState(false);

  const loadQuotas = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {
        search: search || undefined,
        exceeded: filters.exceeded !== 'all' ? filters.exceeded : undefined,
        warning: filters.warning !== 'all' ? filters.warning : undefined,
        sort: filters.sort
      };
      const response = await api.get('/storage/quotas/', { params });
      const items = response.data.results || response.data;
      setQuotas(items);
      if (selectedQuota) {
        const refreshed = items.find((item) => item.id === selectedQuota.id);
        setSelectedQuota(refreshed || null);
      }
    } catch (err) {
      console.error('Failed to load quotas', err);
      setError('Не удалось загрузить данные. Попробуйте ещё раз.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuotas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, filters]);

  const handleSelectQuota = async (quota) => {
    setSelectedQuota(quota);
    setMaterials([]);
    setMaterialsLoading(true);
    try {
      const response = await api.get(`/storage/teachers/${quota.teacher_id}/materials/`);
      setMaterials(response.data.results || response.data);
    } catch (err) {
      console.error('Failed to load materials', err);
    } finally {
      setMaterialsLoading(false);
    }
  };

  const handleIncreaseQuota = async () => {
    if (!selectedQuota || !increaseAmount) return;
    setBusy(true);
    try {
      await api.post(`/storage/quotas/${selectedQuota.id}/increase/`, {
        additional_gb: Number(increaseAmount)
      });
      await loadQuotas();
      showNotification('success', 'Успешно', `Квота увеличена на ${increaseAmount} ГБ`);
    } catch (err) {
      console.error('Failed to increase quota', err);
      showNotification('error', 'Ошибка', 'Не удалось увеличить квоту');
    } finally {
      setBusy(false);
    }
  };

  const handleResetWarnings = async (quotaId) => {
    const confirmed = await showConfirm({
      title: 'Сброс предупреждений',
      message: 'Вы уверены, что хотите сбросить предупреждения?',
      variant: 'warning',
      confirmText: 'Сбросить',
      cancelText: 'Отмена'
    });
    if (!confirmed) return;
    setBusy(true);
    try {
      await api.post(`/storage/quotas/${quotaId}/reset-warnings/`);
      await loadQuotas();
      showNotification('success', 'Успешно', 'Предупреждения сброшены');
    } catch (err) {
      console.error('Failed to reset warnings', err);
      showNotification('error', 'Ошибка', 'Не удалось сбросить предупреждения');
    } finally {
      setBusy(false);
    }
  };

  const statusTag = (quota) => {
    if (quota.quota_exceeded) return <span className="storage-tag exceeded">Превышена</span>;
    if (quota.warning_sent) return <span className="storage-tag warning">Предупреждение</span>;
    return <span className="storage-tag ok">OK</span>;
  };

  const searchInput = (
    <input
      type="text"
      placeholder="Поиск преподавателя"
      value={search}
      onChange={(e) => setSearch(e.target.value)}
    />
  );

  const filterControls = (
    <div className="storage-filters-inline">
      <select value={filters.exceeded} onChange={(e) => setFilters((prev) => ({ ...prev, exceeded: e.target.value }))}>
        <option value="all">Все</option>
        <option value="true">Превышение</option>
        <option value="false">Не превышает</option>
      </select>
      <select value={filters.warning} onChange={(e) => setFilters((prev) => ({ ...prev, warning: e.target.value }))}>
        <option value="all">Все предупреждения</option>
        <option value="true">Есть предупреждение</option>
        <option value="false">Без предупреждений</option>
      </select>
      <select value={filters.sort} onChange={(e) => setFilters((prev) => ({ ...prev, sort: e.target.value }))}>
        <option value="-used_bytes">По использованию ↓</option>
        <option value="used_bytes">По использованию ↑</option>
        <option value="usage_percent">По проценту ↑</option>
        <option value="-total_quota_bytes">По квоте ↓</option>
      </select>
      <button className="storage-small-button" onClick={loadQuotas} disabled={loading}>Обновить</button>
    </div>
  );

  const quotaRows = useMemo(() => {
    if (!quotas.length) {
      return (
        <tr>
          <td colSpan={5} className="storage-empty">Нет данных</td>
        </tr>
      );
    }

    return quotas.map((quota) => (
      <tr
        key={quota.id}
        className={selectedQuota?.id === quota.id ? 'storage-row-selected' : ''}
        onClick={() => handleSelectQuota(quota)}
      >
        <td>
          <div className="teacher-name">{quota.teacher_info?.name || quota.teacher_name || quota.teacher_email}</div>
          <div className="teacher-email">{quota.teacher_info?.email || quota.teacher_email}</div>
        </td>
        <td>
          {formatBytes(quota.used_bytes)} / {formatBytes(quota.max_bytes)}
        </td>
        <td>{usagePercent(quota)}%</td>
        <td>{statusTag(quota)}</td>
        <td>
          <div className="storage-actions" onClick={(e) => e.stopPropagation()}>
            <button className="storage-small-button primary" onClick={() => handleSelectQuota(quota)}>Записи</button>
            <button className="storage-small-button" onClick={() => handleResetWarnings(quota.id)} disabled={busy}>
              Сбросить предупреждения
            </button>
          </div>
        </td>
      </tr>
    ));
  }, [quotas, selectedQuota, busy]);

  return (
    <div className="storage-modal-overlay" onClick={onClose}>
      <div className="storage-modal" onClick={(e) => e.stopPropagation()}>
        <div className="storage-modal-header">
          <h2>💾 Управление хранилищем</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <p className="storage-modal-subtitle">
          Просматривайте использование хранилища, увеличивайте квоты и изучайте записи преподавателей.
        </p>

        {error && (
          <div className="storage-error">
            {error}
            <button className="storage-link-button" onClick={loadQuotas}>Повторить</button>
          </div>
        )}

        <div className="storage-controls">
          {searchInput}
          {filterControls}
        </div>

        <div className="storage-content">
          <div className="storage-panel left">
            {loading ? (
              <div className="storage-loading">Загрузка квот...</div>
            ) : (
              <table className="storage-table">
                <thead>
                  <tr>
                    <th>Преподаватель</th>
                    <th>Использовано</th>
                    <th>%</th>
                    <th>Статус</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>{quotaRows}</tbody>
              </table>
            )}

            {selectedQuota && (
              <div className="storage-increase-block">
                <div className="storage-increase-title">
                  Увеличить квоту для {selectedQuota.teacher_info?.name || selectedQuota.teacher_email}
                </div>
                <div className="storage-increase-row">
                  <input
                    type="number"
                    min="1"
                    value={increaseAmount}
                    onChange={(e) => setIncreaseAmount(e.target.value)}
                  />
                  <span>ГБ</span>
                  <button
                    className="storage-primary-button"
                    onClick={handleIncreaseQuota}
                    disabled={busy}
                  >
                    Увеличить
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="storage-panel right">
            <h3>🎬 Записи преподавателя</h3>
            {!selectedQuota && <div className="storage-right-placeholder">Выберите преподавателя слева</div>}
            {selectedQuota && materialsLoading && <div className="storage-loading">Загрузка записей...</div>}
            {selectedQuota && !materialsLoading && materials.length === 0 && (
              <div className="storage-right-placeholder">Записи не найдены</div>
            )}
            {selectedQuota && !materialsLoading && materials.length > 0 && (
              <ul className="storage-materials-list">
                {materials.slice(0, 12).map((material) => (
                  <li key={material.id}>
                    <div className="material-title">{material.title || material.file_name}</div>
                    <div className="material-meta">
                      {formatBytes(material.size_bytes)} • {new Date(material.created_at).toLocaleString('ru-RU')}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
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
  );
};

export default StorageQuotaModal;
