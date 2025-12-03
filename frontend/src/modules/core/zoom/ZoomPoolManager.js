import React, { useState, useEffect } from 'react';
import apiService from '../../../apiService';
import { Button, Modal, Input, Badge, Card, ConfirmModal } from '../../../shared/components';

/**
 * Административный интерфейс для управления пулом Zoom аккаунтов
 * Только для администраторов
 */
const ZoomPoolManager = ({ onClose }) => {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [poolStats, setPoolStats] = useState(null);
  const [statsError, setStatsError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);
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

  const [newAccount, setNewAccount] = useState({
    email: '',
    api_key: '',
    api_secret: '',
    zoom_user_id: '',
    max_concurrent_meetings: 1,
    is_active: true,
  });

  // Загрузка аккаунтов и статистики
  useEffect(() => {
    loadAccounts();
    loadStats();
    const interval = setInterval(() => {
      loadAccounts(false);
      loadStats(false);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const loadAccounts = async (withSpinner = true) => {
    if (withSpinner) setLoading(true);
    try {
      const response = await apiService.get('zoom-pool/');
      const list = Array.isArray(response.data)
        ? response.data
        : Array.isArray(response.data?.results)
          ? response.data.results
          : [];
      setAccounts(list);
    } catch (error) {
      console.error('Ошибка загрузки аккаунтов:', error);
      setAccounts([]);
    } finally {
      if (withSpinner) setLoading(false);
    }
  };

  const loadStats = async (withSpinner = true) => {
    if (withSpinner) setStatsLoading(true);
    setStatsError(null);
    try {
      const response = await apiService.get('zoom-pool/stats/');
      setPoolStats(response.data);
    } catch (error) {
      console.error('Ошибка загрузки статистики пула:', error);
      setStatsError('Не удалось обновить статистику. Проверьте подключение и попробуйте снова.');
    } finally {
      if (withSpinner) setStatsLoading(false);
    }
  };

  const handleRefreshAll = async () => {
    setRefreshing(true);
    try {
      await Promise.all([loadAccounts(false), loadStats(false)]);
    } finally {
      setRefreshing(false);
    }
  };

  // Добавление нового аккаунта
  const handleAddAccount = async () => {
    try {
      await apiService.post('zoom-pool/', newAccount);
      setShowAddModal(false);
      setNewAccount({
        email: '',
        api_key: '',
        api_secret: '',
        zoom_user_id: '',
        max_concurrent_meetings: 1,
        is_active: true,
      });
      loadAccounts();
    } catch (error) {
      console.error('Ошибка добавления аккаунта:', error);
      setAlertModal({ isOpen: true, title: 'Ошибка', message: 'Ошибка добавления аккаунта', variant: 'danger' });
    }
  };

  // Редактирование аккаунта
  const handleEditAccount = async () => {
    try {
      await apiService.patch(`zoom-pool/${selectedAccount.id}/`, selectedAccount);
      setShowEditModal(false);
      setSelectedAccount(null);
      loadAccounts();
    } catch (error) {
      console.error('Ошибка редактирования аккаунта:', error);
      setAlertModal({ isOpen: true, title: 'Ошибка', message: 'Ошибка редактирования аккаунта', variant: 'danger' });
    }
  };

  // Удаление аккаунта
  const handleDeleteAccount = async (accountId) => {
    setConfirmModal({
      isOpen: true,
      title: 'Удаление Zoom аккаунта',
      message: 'Вы уверены, что хотите удалить этот Zoom аккаунт?',
      variant: 'danger',
      confirmText: 'Удалить',
      cancelText: 'Отмена',
      onConfirm: async () => {
        try {
          await apiService.delete(`zoom-pool/${accountId}/`);
          loadAccounts();
        } catch (error) {
          console.error('Ошибка удаления аккаунта:', error);
          setAlertModal({ isOpen: true, title: 'Ошибка', message: 'Ошибка удаления аккаунта', variant: 'danger' });
        }
        setConfirmModal({ ...confirmModal, isOpen: false });
      }
    });
  };

  // Переключение активности аккаунта
  const handleToggleActive = async (account) => {
    try {
      await apiService.patch(`zoom-pool/${account.id}/`, {
        is_active: !account.is_active,
      });
      loadAccounts();
    } catch (error) {
      console.error('Ошибка переключения активности:', error);
    }
  };

  // Освобождение аккаунта вручную
  const handleReleaseAccount = async (accountId) => {
    try {
      await apiService.post(`zoom-pool/${accountId}/release/`);
      alert('Аккаунт освобожден');
      loadAccounts();
    } catch (error) {
      console.error('Ошибка освобождения аккаунта:', error);
      setAlertModal({ isOpen: true, title: 'Ошибка', message: 'Ошибка освобождения аккаунта', variant: 'danger' });
    }
  };

  const getStatusBadge = (account) => {
    if (!account.is_active) {
      return <Badge variant="neutral">Отключен</Badge>;
    }
    if (account.current_meetings >= account.max_concurrent_meetings) {
      return <Badge variant="danger">Занят</Badge>;
    }
    return <Badge variant="success">Доступен</Badge>;
  };

  const containerStyles = {
    padding: '2rem',
    maxWidth: '1200px',
    width: '100%',
    margin: '0 auto',
  };

  const headerStyles = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '2rem',
  };

  const titleStyles = {
    fontSize: '1.75rem',
    fontWeight: '700',
    color: '#111827',
  };

  const subtitleStyles = {
    fontSize: '0.95rem',
    color: '#6b7280',
    marginTop: '0.25rem',
  };

  const errorSubtitleStyles = {
    ...subtitleStyles,
    color: '#ef4444',
  };

  const headerActionsStyles = {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  };

  const closeButtonStyles = {
    border: 'none',
    background: '#f3f4f6',
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    cursor: 'pointer',
    fontSize: '1.25rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#6b7280',
  };

  const statsCardStyles = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem',
    marginBottom: '2rem',
  };

  const statItemStyles = {
    textAlign: 'center',
    padding: '1rem',
  };

  const statNumberStyles = {
    fontSize: '2rem',
    fontWeight: '700',
    color: '#FF6B35',
    marginBottom: '0.25rem',
  };

  const statLabelStyles = {
    fontSize: '0.875rem',
    color: '#6b7280',
  };

  const accountCardStyles = {
    marginBottom: '1rem',
    padding: '1.5rem',
  };

  const accountHeaderStyles = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '1rem',
  };

  const accountInfoStyles = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem',
    marginBottom: '1rem',
  };

  const infoItemStyles = {
    fontSize: '0.875rem',
  };

  const labelStyles = {
    color: '#6b7280',
    marginBottom: '0.25rem',
  };

  const valueStyles = {
    fontWeight: '600',
    color: '#111827',
  };

  const actionsStyles = {
    display: 'flex',
    gap: '0.5rem',
  };

  // Статистика
  const accountList = Array.isArray(accounts) ? accounts : [];

  const stats = {
    total: accountList.length,
    active: accountList.filter(a => a.is_active).length,
    available: accountList.filter(a => a.is_active && a.current_meetings < a.max_concurrent_meetings).length,
    busy: accountList.filter(a => a.is_active && a.current_meetings > 0).length,
  };

  const busySessions = accountList.reduce((sum, account) => {
    if (!account.is_active) {
      return sum;
    }
    const current = Number(account.current_meetings) || 0;
    return sum + current;
  }, 0);

  const summaryStats = {
    totalAccounts: poolStats?.total_accounts ?? stats.total,
    currentSessions: poolStats?.current_sessions ?? busySessions,
    peakSessions: poolStats?.peak_sessions ?? busySessions,
    availableAccounts: poolStats?.available_accounts ?? stats.available,
    inactiveAccounts: (poolStats ? poolStats.total_accounts - poolStats.active_accounts : stats.total - stats.active) || 0,
  };

  const statsUpdatedLabel = poolStats?.updated_at
    ? new Date(poolStats.updated_at).toLocaleString('ru-RU')
    : null;

  if (loading && accounts.length === 0) {
    return (
      <div style={{ ...containerStyles, textAlign: 'center', padding: '4rem' }}>
        <div style={{ fontSize: '1.25rem', color: '#6b7280' }}>Загрузка...</div>
      </div>
    );
  }

  return (
    <div style={containerStyles}>
      <div style={headerStyles}>
        <div>
          <h1 style={titleStyles}>🎥 Zoom Pool Manager</h1>
          {statsError ? (
            <p style={errorSubtitleStyles}>{statsError}</p>
          ) : statsLoading ? (
            <p style={subtitleStyles}>Обновляем статистику…</p>
          ) : (
            statsUpdatedLabel && (
              <p style={subtitleStyles}>Обновлено {statsUpdatedLabel}</p>
            )
          )}
        </div>
        <div style={headerActionsStyles}>
          <Button
            variant="secondary"
            onClick={handleRefreshAll}
            disabled={refreshing}
            loading={refreshing}
          >
            {refreshing ? 'Обновление…' : '🔄 Обновить данные'}
          </Button>
          <Button variant="success" onClick={() => setShowAddModal(true)}>
            + Добавить аккаунт
          </Button>
          {onClose && (
            <button type="button" style={closeButtonStyles} onClick={onClose}>
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Статистика */}
      <div style={statsCardStyles}>
        <Card>
          <div style={statItemStyles}>
            <div style={statNumberStyles}>{summaryStats.totalAccounts}</div>
            <div style={statLabelStyles}>Всего аккаунтов</div>
          </div>
        </Card>
        <Card>
          <div style={statItemStyles}>
            <div style={{ ...statNumberStyles, color: '#f97316' }}>{summaryStats.currentSessions}</div>
            <div style={statLabelStyles}>Используется сейчас (уроков)</div>
          </div>
        </Card>
        <Card>
          <div style={statItemStyles}>
            <div style={{ ...statNumberStyles, color: '#8b5cf6' }}>{summaryStats.peakSessions}</div>
            <div style={statLabelStyles}>Пиковая нагрузка (уроков)</div>
          </div>
        </Card>
        <Card>
          <div style={statItemStyles}>
            <div style={{ ...statNumberStyles, color: '#10b981' }}>{summaryStats.availableAccounts}</div>
            <div style={statLabelStyles}>Доступно</div>
          </div>
        </Card>
        <Card>
          <div style={statItemStyles}>
            <div style={{ ...statNumberStyles, color: '#6b7280' }}>{summaryStats.inactiveAccounts}</div>
            <div style={statLabelStyles}>Отключено</div>
          </div>
        </Card>
      </div>

      {/* Список аккаунтов */}
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>Аккаунты</h2>
        {accounts.length === 0 ? (
          <Card>
            <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
              Нет добавленных Zoom аккаунтов. Добавьте первый аккаунт.
            </div>
          </Card>
        ) : (
          accounts.map(account => (
            <Card key={account.id} style={accountCardStyles}>
              <div style={accountHeaderStyles}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <h3 style={{ fontSize: '1.125rem', fontWeight: '600', margin: 0 }}>
                    {account.email}
                  </h3>
                  {getStatusBadge(account)}
                </div>
                <div style={actionsStyles}>
                  <Button
                    size="small"
                    variant="secondary"
                    onClick={() => {
                      setSelectedAccount(account);
                      setShowEditModal(true);
                    }}
                  >
                    ✏️ Изменить
                  </Button>
                  <Button
                    size="small"
                    variant={account.is_active ? 'warning' : 'success'}
                    onClick={() => handleToggleActive(account)}
                  >
                    {account.is_active ? '⏸️ Отключить' : '▶️ Включить'}
                  </Button>
                  <Button
                    size="small"
                    variant="danger"
                    onClick={() => handleDeleteAccount(account.id)}
                  >
                    🗑️
                  </Button>
                </div>
              </div>

              <div style={accountInfoStyles}>
                <div style={infoItemStyles}>
                  <div style={labelStyles}>Zoom User ID</div>
                  <div style={valueStyles}>{account.zoom_user_id || 'N/A'}</div>
                </div>
                <div style={infoItemStyles}>
                  <div style={labelStyles}>Макс. одновременных встреч</div>
                  <div style={valueStyles}>{account.max_concurrent_meetings}</div>
                </div>
                <div style={infoItemStyles}>
                  <div style={labelStyles}>Текущих встреч</div>
                  <div style={valueStyles}>{account.current_meetings || 0}</div>
                </div>
                <div style={infoItemStyles}>
                  <div style={labelStyles}>Последнее использование</div>
                  <div style={valueStyles}>
                    {account.last_used_at 
                      ? new Date(account.last_used_at).toLocaleString('ru-RU')
                      : 'Не использовался'
                    }
                  </div>
                </div>
              </div>

              {account.current_meetings > 0 && (
                <Button
                  size="small"
                  variant="outline"
                  onClick={() => handleReleaseAccount(account.id)}
                >
                  🔓 Освободить аккаунт вручную
                </Button>
              )}
            </Card>
          ))
        )}
      </div>

      {/* Модальное окно добавления аккаунта */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Добавить Zoom аккаунт"
        size="medium"
      >
        <Input
          label="Email аккаунта Zoom"
          type="email"
          value={newAccount.email}
          onChange={(e) => setNewAccount({ ...newAccount, email: e.target.value })}
          placeholder="zoom@example.com"
          required
        />

        <Input
          label="API Key"
          type="text"
          value={newAccount.api_key}
          onChange={(e) => setNewAccount({ ...newAccount, api_key: e.target.value })}
          placeholder="API Key из настроек Zoom"
          required
        />

        <Input
          label="API Secret"
          type="password"
          value={newAccount.api_secret}
          onChange={(e) => setNewAccount({ ...newAccount, api_secret: e.target.value })}
          placeholder="API Secret из настроек Zoom"
          required
        />

        <Input
          label="Zoom User ID (опционально)"
          type="text"
          value={newAccount.zoom_user_id}
          onChange={(e) => setNewAccount({ ...newAccount, zoom_user_id: e.target.value })}
          placeholder="User ID из Zoom"
        />

        <Input
          label="Макс. одновременных встреч"
          type="number"
          value={newAccount.max_concurrent_meetings}
          onChange={(e) => setNewAccount({ ...newAccount, max_concurrent_meetings: parseInt(e.target.value) })}
          helperText="Обычно 1 для базового тарифа, 100 для Pro"
        />

        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
          <Button
            variant="secondary"
            onClick={() => setShowAddModal(false)}
            style={{ flex: 1 }}
          >
            Отмена
          </Button>
          <Button
            variant="success"
            onClick={handleAddAccount}
            style={{ flex: 1 }}
          >
            Добавить
          </Button>
        </div>
      </Modal>

      {/* Модальное окно редактирования аккаунта */}
      {selectedAccount && (
        <Modal
          isOpen={showEditModal}
          onClose={() => {
            setShowEditModal(false);
            setSelectedAccount(null);
          }}
          title="Редактировать Zoom аккаунт"
          size="medium"
        >
          <Input
            label="Email аккаунта Zoom"
            type="email"
            value={selectedAccount.email}
            onChange={(e) => setSelectedAccount({ ...selectedAccount, email: e.target.value })}
            disabled
          />

          <Input
            label="API Key"
            type="text"
            value={selectedAccount.api_key}
            onChange={(e) => setSelectedAccount({ ...selectedAccount, api_key: e.target.value })}
            placeholder="Оставьте пустым, чтобы не менять"
          />

          <Input
            label="API Secret"
            type="password"
            value={selectedAccount.api_secret || ''}
            onChange={(e) => setSelectedAccount({ ...selectedAccount, api_secret: e.target.value })}
            placeholder="Оставьте пустым, чтобы не менять"
          />

          <Input
            label="Макс. одновременных встреч"
            type="number"
            value={selectedAccount.max_concurrent_meetings}
            onChange={(e) => setSelectedAccount({ ...selectedAccount, max_concurrent_meetings: parseInt(e.target.value) })}
          />

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
            <Button
              variant="secondary"
              onClick={() => {
                setShowEditModal(false);
                setSelectedAccount(null);
              }}
              style={{ flex: 1 }}
            >
              Отмена
            </Button>
            <Button
              variant="primary"
              onClick={handleEditAccount}
              style={{ flex: 1 }}
            >
              Сохранить
            </Button>
          </div>
        </Modal>
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
  );
};

export default ZoomPoolManager;
