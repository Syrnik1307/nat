import React, { useState, useEffect } from 'react';
import './AdminStorageManagementPage.css';
import api from '../../apiService';

function AdminStorageManagementPage() {
  const [quotas, setQuotas] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterExceeded, setFilterExceeded] = useState('all');
  const [filterWarning, setFilterWarning] = useState('all');
  const [sortBy, setSortBy] = useState('-used_bytes');
  const [selectedTeacher, setSelectedTeacher] = useState(null);
  const [showIncreaseModal, setShowIncreaseModal] = useState(false);
  const [increaseAmount, setIncreaseAmount] = useState(5);

  useEffect(() => {
    loadData();
  }, [searchTerm, filterExceeded, filterWarning, sortBy]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = {
        search: searchTerm,
        sort: sortBy
      };

      if (filterExceeded !== 'all') {
        params.exceeded = filterExceeded;
      }

      if (filterWarning !== 'all') {
        params.warning = filterWarning;
      }

      const responses = await Promise.all([
        api.get('/schedule/api/storage/quotas/', { params }),
        api.get('/schedule/api/storage/statistics/')
      ]);

      setQuotas(responses[0].data.results || responses[0].data);
      setStatistics(responses[1].data);
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  };

  const handleIncreaseQuota = async () => {
    if (!selectedTeacher) return;

    try {
      await api.post(`/schedule/api/storage/quotas/${selectedTeacher.id}/increase/`, {
        additional_gb: increaseAmount
      });

      setShowIncreaseModal(false);
      setSelectedTeacher(null);
      setIncreaseAmount(5);
      loadData();

      alert(`Квота увеличена на ${increaseAmount} ГБ`);
    } catch (err) {
      console.error('Error increasing quota:', err);
      alert('Не удалось увеличить квоту');
    }
  };

  const handleResetWarnings = async (quotaId) => {
    if (!window.confirm('Сбросить предупреждения для этого преподавателя?')) {
      return;
    }

    try {
      await api.post(`/schedule/api/storage/quotas/${quotaId}/reset-warnings/`);
      loadData();
      alert('Предупреждения сброшены');
    } catch (err) {
      console.error('Error resetting warnings:', err);
      alert('Не удалось сбросить предупреждения');
    }
  };

  const getUsageColor = (percent) => {
    if (percent >= 90) return '#ef4444';
    if (percent >= 80) return '#f59e0b';
    return '#10b981';
  };

  const openIncreaseModal = (quota) => {
    setSelectedTeacher(quota);
    setShowIncreaseModal(true);
  };

  return (
    <div className="admin-storage-page">
      <div className="admin-storage-header">
        <h1>💾 Управление хранилищем</h1>
        <p className="admin-storage-subtitle">Мониторинг квот преподавателей</p>
      </div>

      {/* Общая статистика */}
      {statistics && (
        <div className="storage-stats-grid">
          <div className="storage-stat-card">
            <div className="storage-stat-icon">👥</div>
            <div className="storage-stat-info">
              <div className="storage-stat-value">{statistics.total_teachers}</div>
              <div className="storage-stat-label">Преподавателей</div>
            </div>
          </div>

          <div className="storage-stat-card">
            <div className="storage-stat-icon">💾</div>
            <div className="storage-stat-info">
              <div className="storage-stat-value">{statistics.total_used_gb} / {statistics.total_quota_gb} GB</div>
              <div className="storage-stat-label">Использовано / Квота</div>
            </div>
          </div>

          <div className="storage-stat-card">
            <div className="storage-stat-icon">📊</div>
            <div className="storage-stat-info">
              <div className="storage-stat-value">{statistics.average_usage_percent}%</div>
              <div className="storage-stat-label">Средняя загрузка</div>
            </div>
          </div>

          <div className="storage-stat-card storage-stat-warning">
            <div className="storage-stat-icon">⚠️</div>
            <div className="storage-stat-info">
              <div className="storage-stat-value">{statistics.exceeded_count}</div>
              <div className="storage-stat-label">Превышений квоты</div>
            </div>
          </div>

          <div className="storage-stat-card">
            <div className="storage-stat-icon">📹</div>
            <div className="storage-stat-info">
              <div className="storage-stat-value">{statistics.total_recordings}</div>
              <div className="storage-stat-label">Всего записей</div>
            </div>
          </div>

          <div className="storage-stat-card">
            <div className="storage-stat-icon">✅</div>
            <div className="storage-stat-info">
              <div className="storage-stat-value">{statistics.total_available_gb.toFixed(2)} GB</div>
              <div className="storage-stat-label">Доступно</div>
            </div>
          </div>
        </div>
      )}

      {/* Топ пользователей по использованию */}
      {statistics?.top_users && statistics.top_users.length > 0 && (
        <div className="top-users-section">
          <h3>📈 Топ-5 по использованию</h3>
          <div className="top-users-list">
            {statistics.top_users.map((user, index) => (
              <div key={user.teacher_id} className="top-user-item">
                <div className="top-user-rank">#{index + 1}</div>
                <div className="top-user-info">
                  <div className="top-user-name">{user.teacher_name}</div>
                  <div className="top-user-usage">
                    {user.used_gb} / {user.total_gb} GB ({user.usage_percent}%)
                  </div>
                </div>
                <div className="top-user-bar">
                  <div
                    className="top-user-bar-fill"
                    style={{
                      width: `${user.usage_percent}%`,
                      backgroundColor: getUsageColor(user.usage_percent)
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Фильтры */}
      <div className="storage-filters">
        <div className="storage-search-box">
          <input
            type="text"
            placeholder="🔍 Поиск преподавателя..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="storage-search-input"
          />
        </div>

        <div className="storage-filter-group">
          <label>Превышение:</label>
          <select
            value={filterExceeded}
            onChange={(e) => setFilterExceeded(e.target.value)}
            className="storage-filter-select"
          >
            <option value="all">Все</option>
            <option value="true">Да</option>
            <option value="false">Нет</option>
          </select>
        </div>

        <div className="storage-filter-group">
          <label>Предупреждение:</label>
          <select
            value={filterWarning}
            onChange={(e) => setFilterWarning(e.target.value)}
            className="storage-filter-select"
          >
            <option value="all">Все</option>
            <option value="true">Да</option>
            <option value="false">Нет</option>
          </select>
        </div>

        <div className="storage-filter-group">
          <label>Сортировка:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="storage-filter-select"
          >
            <option value="-used_bytes">По использованию ↓</option>
            <option value="used_bytes">По использованию ↑</option>
            <option value="-total_quota_bytes">По квоте ↓</option>
            <option value="usage_percent">По проценту ↑</option>
          </select>
        </div>

        <button onClick={loadData} className="storage-refresh-btn">
          🔄 Обновить
        </button>
      </div>

      {/* Список квот */}
      {loading ? (
        <div className="storage-loading">
          <div className="storage-spinner"></div>
          <p>Загрузка...</p>
        </div>
      ) : error ? (
        <div className="storage-error">
          <p>❌ {error}</p>
          <button onClick={loadData} className="storage-retry-btn">Повторить</button>
        </div>
      ) : quotas.length === 0 ? (
        <div className="storage-empty">
          <div className="storage-empty-icon">📭</div>
          <h3>Квоты не найдены</h3>
          <p>Попробуйте изменить фильтры</p>
        </div>
      ) : (
        <div className="quotas-table">
          <table>
            <thead>
              <tr>
                <th>Преподаватель</th>
                <th>Использовано</th>
                <th>Квота</th>
                <th>Загрузка</th>
                <th>Записей</th>
                <th>Статус</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {quotas.map((quota) => (
                <tr key={quota.id} className={quota.quota_exceeded ? 'quota-exceeded' : ''}>
                  <td>
                    <div className="teacher-cell">
                      <div className="teacher-name">{quota.teacher_info.name}</div>
                      <div className="teacher-email">{quota.teacher_info.email}</div>
                    </div>
                  </td>
                  <td className="usage-cell">{quota.used_gb} GB</td>
                  <td className="quota-cell">{quota.total_gb} GB</td>
                  <td>
                    <div className="usage-bar-container">
                      <div
                        className="usage-bar-fill"
                        style={{
                          width: `${quota.usage_percent}%`,
                          backgroundColor: getUsageColor(quota.usage_percent)
                        }}
                      />
                      <span className="usage-percent">{quota.usage_percent}%</span>
                    </div>
                  </td>
                  <td className="recordings-cell">{quota.recordings_count}</td>
                  <td className="status-cell">
                    {quota.quota_exceeded && <span className="status-badge exceeded">Превышена</span>}
                    {quota.warning_sent && !quota.quota_exceeded && <span className="status-badge warning">Предупр.</span>}
                    {!quota.quota_exceeded && !quota.warning_sent && <span className="status-badge ok">OK</span>}
                  </td>
                  <td className="actions-cell">
                    <button
                      className="action-btn increase-btn"
                      onClick={() => openIncreaseModal(quota)}
                      title="Увеличить квоту"
                    >
                      ➕
                    </button>
                    {quota.warning_sent && (
                      <button
                        className="action-btn reset-btn"
                        onClick={() => handleResetWarnings(quota.id)}
                        title="Сбросить предупреждения"
                      >
                        🔄
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Модальное окно увеличения квоты */}
      {showIncreaseModal && selectedTeacher && (
        <div className="modal-overlay" onClick={() => setShowIncreaseModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Увеличить квоту</h3>
              <button className="modal-close" onClick={() => setShowIncreaseModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <p><strong>Преподаватель:</strong> {selectedTeacher.teacher_info.name}</p>
              <p><strong>Текущая квота:</strong> {selectedTeacher.total_gb} GB</p>
              <p><strong>Использовано:</strong> {selectedTeacher.used_gb} GB ({selectedTeacher.usage_percent}%)</p>

              <div className="increase-input-group">
                <label>Добавить ГБ:</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={increaseAmount}
                  onChange={(e) => setIncreaseAmount(parseInt(e.target.value) || 1)}
                  className="increase-input"
                />
              </div>

              <p className="new-quota-preview">
                Новая квота: <strong>{selectedTeacher.total_gb + increaseAmount} GB</strong>
              </p>
            </div>
            <div className="modal-footer">
              <button
                className="modal-btn modal-btn-cancel"
                onClick={() => setShowIncreaseModal(false)}
              >
                Отмена
              </button>
              <button
                className="modal-btn modal-btn-confirm"
                onClick={handleIncreaseQuota}
              >
                Увеличить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminStorageManagementPage;
