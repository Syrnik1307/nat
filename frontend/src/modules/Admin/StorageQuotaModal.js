import React, { useState, useEffect, useCallback, useMemo } from 'react';
import api, { withScheduleApiBase } from '../../apiService';
import Notification from '../../shared/components/Notification';
import ConfirmModal from '../../shared/components/ConfirmModal';
import './StorageQuotaModal.css';

// Форматирование в ГБ
const formatGB = (gb) => {
  if (gb === undefined || gb === null || isNaN(gb)) return '0 ГБ';
  if (gb >= 1) return `${gb.toFixed(2)} ГБ`;
  return `${(gb * 1024).toFixed(0)} МБ`;
};

const StorageQuotaModal = ({ onClose }) => {
  const [quotas, setQuotas] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('used_gb');
  const [sortOrder, setSortOrder] = useState('desc');
  const [selectedTeacher, setSelectedTeacher] = useState(null);
  const [editingQuota, setEditingQuota] = useState(null);
  const [newQuotaGB, setNewQuotaGB] = useState('');

  // Уведомления
  const [notification, setNotification] = useState({ isOpen: false, type: 'info', title: '', message: '' });
  const [confirm, setConfirm] = useState({ isOpen: false, title: '', message: '', onConfirm: null });

  const showNotification = (type, title, message) => {
    setNotification({ isOpen: true, type, title, message });
  };
  const closeNotification = () => setNotification(prev => ({ ...prev, isOpen: false }));
  const closeConfirm = () => setConfirm(prev => ({ ...prev, isOpen: false }));

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Используем быстрые API из БД
      const [quotasRes, statsRes] = await Promise.all([
        api.get('storage/quotas/', withScheduleApiBase()),
        api.get('storage/statistics/', withScheduleApiBase())
      ]);

      const quotaData = quotasRes.data.results || quotasRes.data;
      setQuotas(quotaData);
      setStatistics(statsRes.data);
    } catch (err) {
      console.error('Error loading storage data:', err);
      setError('Не удалось загрузить данные хранилища');
    } finally {
      setLoading(false);
    }
  }, []);

  const syncFromGDrive = async () => {
    setSyncing(true);
    try {
      const response = await api.post('storage/sync-from-gdrive/', {}, withScheduleApiBase());
      showNotification('success', 'Синхронизация завершена', response.data.message);
      // Перезагружаем данные
      await loadData();
    } catch (err) {
      console.error('Error syncing from GDrive:', err);
      showNotification('error', 'Ошибка', 'Не удалось синхронизировать данные с Google Drive');
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredTeachers = useMemo(() => {
    if (!quotas || quotas.length === 0) return [];
    
    let result = [...quotas];
    
    // Фильтр по поиску
    if (search.trim()) {
      const searchLower = search.toLowerCase();
      result = result.filter(q => 
        q.teacher_info?.name?.toLowerCase().includes(searchLower) ||
        q.teacher_info?.email?.toLowerCase().includes(searchLower)
      );
    }
    
    // Сортировка
    result.sort((a, b) => {
      let aVal, bVal;
      switch (sortBy) {
        case 'used_gb':
          aVal = a.used_gb || 0;
          bVal = b.used_gb || 0;
          break;
        case 'total_gb':
          aVal = a.total_gb || 0;
          bVal = b.total_gb || 0;
          break;
        case 'usage_percent':
          aVal = a.usage_percent || 0;
          bVal = b.usage_percent || 0;
          break;
        case 'recordings_count':
          aVal = a.recordings_count || 0;
          bVal = b.recordings_count || 0;
          break;
        case 'name':
          aVal = a.teacher_info?.name || '';
          bVal = b.teacher_info?.name || '';
          return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        default:
          aVal = a.used_gb || 0;
          bVal = b.used_gb || 0;
      }
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
    });
    
    return result;
  }, [quotas, search, sortBy, sortOrder]);

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const getSortIcon = (field) => {
    if (sortBy !== field) return '';
    return sortOrder === 'asc' ? ' ↑' : ' ↓';
  };

  const getUsageColor = (percent) => {
    if (percent >= 90) return '#ef4444'; // Красный
    if (percent >= 70) return '#f59e0b'; // Оранжевый
    return '#10b981'; // Зелёный
  };

  const handleUpdateQuota = async (quotaId, newTotalGB) => {
    try {
      await api.patch(`storage/quotas/${quotaId}/update_quota/`, {
        total_gb: parseFloat(newTotalGB)
      }, withScheduleApiBase());
      showNotification('success', 'Успешно', 'Квота обновлена');
      setEditingQuota(null);
      setNewQuotaGB('');
      loadData();
    } catch (err) {
      console.error('Error updating quota:', err);
      showNotification('error', 'Ошибка', 'Не удалось обновить квоту');
    }
  };

  const renderTeacherDetails = () => {
    if (!selectedTeacher) {
      return (
        <div className="storage-details-placeholder">
          <div className="storage-details-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <p>Выберите преподавателя слева для просмотра информации о хранилище</p>
        </div>
      );
    }

    const usagePercent = selectedTeacher.usage_percent || 0;
    const usageColor = getUsageColor(usagePercent);

    return (
      <div className="storage-details-content">
        <div className="storage-details-header">
          <h3>{selectedTeacher.teacher_info?.name || 'Преподаватель'}</h3>
          <p className="storage-details-email">{selectedTeacher.teacher_info?.email}</p>
        </div>

        <div className="storage-details-total">
          <div className="storage-details-total-value" style={{ color: usageColor }}>
            {formatGB(selectedTeacher.used_gb)}
          </div>
          <div className="storage-details-total-label">
            из {formatGB(selectedTeacher.total_gb)} использовано
          </div>
        </div>

        <div className="storage-usage-bar-container">
          <div 
            className="storage-usage-bar-fill"
            style={{ 
              width: `${Math.min(usagePercent, 100)}%`,
              backgroundColor: usageColor
            }}
          />
        </div>
        <div className="storage-usage-percent" style={{ color: usageColor }}>
          {usagePercent.toFixed(1)}% заполнено
        </div>

        <div className="storage-details-stats">
          <div className="storage-stat-item">
            <span className="storage-stat-label">Записей:</span>
            <span className="storage-stat-value">{selectedTeacher.recordings_count || 0}</span>
          </div>
          <div className="storage-stat-item">
            <span className="storage-stat-label">Свободно:</span>
            <span className="storage-stat-value">{formatGB(selectedTeacher.available_gb)}</span>
          </div>
          <div className="storage-stat-item">
            <span className="storage-stat-label">Докуплено:</span>
            <span className="storage-stat-value">{selectedTeacher.purchased_gb || 0} ГБ</span>
          </div>
          {selectedTeacher.quota_exceeded && (
            <div className="storage-stat-item storage-stat-warning">
              <span className="storage-stat-label">Статус:</span>
              <span className="storage-stat-value warning">Квота превышена</span>
            </div>
          )}
        </div>

        <div className="storage-details-actions">
          {editingQuota === selectedTeacher.id ? (
            <div className="quota-edit-form">
              <input
                type="number"
                value={newQuotaGB}
                onChange={(e) => setNewQuotaGB(e.target.value)}
                placeholder="Новая квота (ГБ)"
                min="1"
                step="1"
              />
              <button 
                className="btn-save"
                onClick={() => handleUpdateQuota(selectedTeacher.id, newQuotaGB)}
                disabled={!newQuotaGB || parseFloat(newQuotaGB) <= 0}
              >
                Сохранить
              </button>
              <button 
                className="btn-cancel"
                onClick={() => { setEditingQuota(null); setNewQuotaGB(''); }}
              >
                Отмена
              </button>
            </div>
          ) : (
            <button 
              className="btn-edit-quota"
              onClick={() => {
                setEditingQuota(selectedTeacher.id);
                setNewQuotaGB(selectedTeacher.total_gb?.toFixed(0) || '5');
              }}
            >
              Изменить квоту
            </button>
          )}
        </div>
      </div>
    );
  };

  const renderSummary = () => {
    if (!statistics) return null;

    return (
      <div className="storage-summary">
        <div className="storage-summary-item">
          <div className="storage-summary-value">{statistics.total_teachers || quotas.length}</div>
          <div className="storage-summary-label">Преподавателей</div>
        </div>
        <div className="storage-summary-item">
          <div className="storage-summary-value">{formatGB(statistics.total_used_gb)}</div>
          <div className="storage-summary-label">Использовано</div>
        </div>
        <div className="storage-summary-item">
          <div className="storage-summary-value">{formatGB(statistics.total_quota_gb)}</div>
          <div className="storage-summary-label">Всего выделено</div>
        </div>
        <div className="storage-summary-item">
          <div className="storage-summary-value">{statistics.total_recordings || 0}</div>
          <div className="storage-summary-label">Записей</div>
        </div>
        {statistics.exceeded_count > 0 && (
          <div className="storage-summary-item storage-summary-warning">
            <div className="storage-summary-value warning">{statistics.exceeded_count}</div>
            <div className="storage-summary-label">Превышений</div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="storage-modal-overlay" onClick={onClose}>
      <div className="storage-modal storage-modal-v2" onClick={(e) => e.stopPropagation()}>
        <div className="storage-modal-header">
          <div className="storage-modal-title">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
            <h2>Управление хранилищем</h2>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Закрыть">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        
        <p className="storage-modal-subtitle">
          Просматривайте и управляйте квотами хранилища преподавателей.
        </p>

        {error && (
          <div className="storage-error">
            {error}
            <button className="storage-link-button" onClick={loadData}>Повторить</button>
          </div>
        )}

        {renderSummary()}

        <div className="storage-controls">
          <div className="storage-search-wrapper">
            <svg className="storage-search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35"/>
            </svg>
            <input
              type="text"
              placeholder="Поиск преподавателя..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button 
            className="storage-sync-btn" 
            onClick={syncFromGDrive} 
            disabled={syncing || loading}
            title="Синхронизировать данные с Google Drive (может занять несколько минут)"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
            </svg>
            {syncing ? 'Синхронизация...' : 'Синхронизировать с GDrive'}
          </button>
          <button className="storage-refresh-btn" onClick={loadData} disabled={loading}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 4v6h-6M1 20v-6h6"/>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
            Обновить
          </button>
        </div>

        <div className="storage-content">
          <div className="storage-panel storage-panel-left">
            {loading ? (
              <div className="storage-loading">
                <div className="storage-spinner" />
                <span>Загрузка...</span>
              </div>
            ) : filteredTeachers.length === 0 ? (
              <div className="storage-empty">
                {search ? 'Преподаватели не найдены' : 'Нет данных о хранилище'}
              </div>
            ) : (
              <table className="storage-table">
                <thead>
                  <tr>
                    <th 
                      className="sortable" 
                      onClick={() => handleSort('name')}
                    >
                      Преподаватель{getSortIcon('name')}
                    </th>
                    <th 
                      className="sortable numeric" 
                      onClick={() => handleSort('used_gb')}
                    >
                      Использовано{getSortIcon('used_gb')}
                    </th>
                    <th 
                      className="sortable numeric" 
                      onClick={() => handleSort('total_gb')}
                    >
                      Квота{getSortIcon('total_gb')}
                    </th>
                    <th 
                      className="sortable numeric" 
                      onClick={() => handleSort('usage_percent')}
                    >
                      %{getSortIcon('usage_percent')}
                    </th>
                    <th 
                      className="sortable numeric" 
                      onClick={() => handleSort('recordings_count')}
                    >
                      Записей{getSortIcon('recordings_count')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTeachers.map((teacher) => {
                    const usagePercent = teacher.usage_percent || 0;
                    const usageColor = getUsageColor(usagePercent);
                    
                    return (
                      <tr
                        key={teacher.id}
                        className={`${selectedTeacher?.id === teacher.id ? 'selected' : ''} ${teacher.quota_exceeded ? 'exceeded' : ''}`}
                        onClick={() => setSelectedTeacher(teacher)}
                      >
                        <td>
                          <div className="teacher-cell">
                            <div className="teacher-name">{teacher.teacher_info?.name || 'Без имени'}</div>
                            <div className="teacher-email">{teacher.teacher_info?.email}</div>
                          </div>
                        </td>
                        <td className="numeric">
                          <span className="size-value" style={{ color: usageColor }}>
                            {formatGB(teacher.used_gb)}
                          </span>
                        </td>
                        <td className="numeric">
                          <span className="size-value">
                            {formatGB(teacher.total_gb)}
                          </span>
                        </td>
                        <td className="numeric">
                          <div className="usage-cell">
                            <div className="mini-progress-bar">
                              <div 
                                className="mini-progress-fill"
                                style={{ 
                                  width: `${Math.min(usagePercent, 100)}%`,
                                  backgroundColor: usageColor
                                }}
                              />
                            </div>
                            <span className="percent-value" style={{ color: usageColor }}>
                              {usagePercent.toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td className="numeric">
                          <span className="recordings-value">
                            {teacher.recordings_count || 0}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          <div className="storage-panel storage-panel-right">
            {renderTeacherDetails()}
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
