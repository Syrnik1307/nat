import React, { useState, useEffect } from 'react';
import api from '../../apiService';
import './SubscriptionsModal.css';

const SubscriptionsModal = ({ onClose }) => {
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSubscription, setSelectedSubscription] = useState(null);
  const [filterPlan, setFilterPlan] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    loadSubscriptions();
  }, [searchQuery, filterPlan, filterStatus]);

  const loadSubscriptions = async () => {
    setLoading(true);
    setError('');
    try {
      // Бэкенд сейчас предоставляет только эндпоинт текущей подписки пользователя:
      // GET /api/subscription/
      // Для избежания 404 загружаем одну подписку и отображаем её.
      // Используем относительный путь без повторного префикса /api/
      const response = await api.get('subscription/');
      const data = response.data;
      // Приводим к массиву для дальнейшей фильтрации/рендера списка
      setSubscriptions(Array.isArray(data) ? data : (data ? [data] : []));
    } catch (err) {
      console.error('Failed to load subscriptions:', err);
      setError('Не удалось загрузить подписки. Попробуйте обновить страницу.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSubscription = (sub) => {
    setSelectedSubscription(selectedSubscription?.id === sub.id ? null : sub);
  };

  const handleExtendTrial = async () => {
    // Эндпоинта для продления пробного периода в админке пока нет.
    alert('Продление пробного периода пока недоступно: отсутствует API.');
  };

  const handleCancelSubscription = async () => {
    if (!window.confirm('Отменить автопродление? Доступ сохранится до окончания оплаченного периода.')) return;
    setBusy(true);
    try {
      await api.post('subscription/cancel/');
      await loadSubscriptions();
      alert('Подписка отменена');
    } catch (err) {
      console.error('Failed to cancel subscription:', err);
      alert('Не удалось отменить подписку');
    } finally {
      setBusy(false);
    }
  };

  const handleActivateSubscription = async () => {
    // Эндпоинта для активации из админки пока нет.
    alert('Активация подписки пока недоступна: отсутствует API.');
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getDaysRemaining = (expiresAt) => {
    if (!expiresAt) return null;
    const now = new Date();
    const expiry = new Date(expiresAt);
    const diff = expiry - now;
    const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
    return days;
  };

  const getStatusBadge = (status) => {
    const badges = {
      active: { label: 'Активна', color: '#10b981' },
      pending: { label: 'Ожидает оплаты', color: '#f59e0b' },
      cancelled: { label: 'Отменена', color: '#ef4444' },
      expired: { label: 'Истекла', color: '#6b7280' }
    };
    const badge = badges[status] || badges.active;
    return (
      <span className="subscription-badge" style={{ backgroundColor: badge.color }}>
        {badge.label}
      </span>
    );
  };

  const getPlanLabel = (plan) => {
    const plans = {
      trial: 'Пробная',
      monthly: 'Месячная',
      yearly: 'Годовая'
    };
    return plans[plan] || plan;
  };

  const filteredSubscriptions = subscriptions.filter(sub => {
    const matchSearch = !searchQuery || 
      sub.teacher_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      sub.teacher_email?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchPlan = filterPlan === 'all' || sub.plan === filterPlan;
    const matchStatus = filterStatus === 'all' || sub.status === filterStatus;
    return matchSearch && matchPlan && matchStatus;
  });

  return (
    <div className="subscriptions-modal-overlay" onClick={onClose}>
      <div className="subscriptions-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="subscriptions-modal-header">
          <h2>💳 Управление подписками</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <p className="subscriptions-modal-subtitle">
          Просмотр и управление подписками преподавателей
        </p>

        {error && (
          <div className="subscriptions-error">
            <span className="error-icon">⚠️</span>
            {error}
            <button className="error-retry" onClick={loadSubscriptions}>
              Повторить
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="subscriptions-filters">
          <div className="search-box">
            <input
              type="text"
              placeholder="🔍 Поиск по имени или email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="filter-row">
            <select
              value={filterPlan}
              onChange={(e) => setFilterPlan(e.target.value)}
              className="filter-select"
            >
              <option value="all">Все тарифы</option>
              <option value="trial">Пробная</option>
              <option value="monthly">Месячная</option>
              <option value="yearly">Годовая</option>
            </select>

            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="filter-select"
            >
              <option value="all">Все статусы</option>
              <option value="active">Активна</option>
              <option value="pending">Ожидает оплаты</option>
              <option value="cancelled">Отменена</option>
              <option value="expired">Истекла</option>
            </select>

            <button onClick={loadSubscriptions} className="refresh-btn" disabled={loading}>
              🔄 Обновить
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="subscriptions-content">
          {/* Left Panel - List */}
          <div className="subscriptions-list-panel">
            {loading && subscriptions.length === 0 ? (
              <div className="subscriptions-loading">
                <div className="spinner"></div>
                <p>Загрузка подписок...</p>
              </div>
            ) : filteredSubscriptions.length === 0 ? (
              <div className="subscriptions-empty">
                <span className="empty-icon">💳</span>
                <p>Подписки не найдены</p>
                {searchQuery && (
                  <button onClick={() => setSearchQuery('')} className="clear-search-btn">
                    Сбросить поиск
                  </button>
                )}
              </div>
            ) : (
              <div className="subscriptions-list">
                {filteredSubscriptions.map((sub) => {
                  const daysLeft = getDaysRemaining(sub.expires_at);
                  const isExpiringSoon = daysLeft !== null && daysLeft <= 7 && daysLeft > 0;
                  const isExpired = daysLeft !== null && daysLeft <= 0;

                  return (
                    <div
                      key={sub.id}
                      className={`subscription-item ${selectedSubscription?.id === sub.id ? 'selected' : ''} ${isExpired ? 'expired' : ''}`}
                      onClick={() => handleSelectSubscription(sub)}
                    >
                      <div className="subscription-item-header">
                        <div className="teacher-info">
                          <div className="teacher-avatar">
                            {sub.teacher_name?.charAt(0) || '👤'}
                          </div>
                          <div className="teacher-details">
                            <div className="teacher-name">{sub.teacher_name || 'Без имени'}</div>
                            <div className="teacher-email">{sub.teacher_email}</div>
                          </div>
                        </div>
                        {getStatusBadge(sub.status)}
                      </div>

                      <div className="subscription-item-body">
                        <div className="subscription-meta">
                          <span className="meta-label">Тариф:</span>
                          <span className="meta-value">{getPlanLabel(sub.plan)}</span>
                        </div>

                        {daysLeft !== null && (
                          <div className="subscription-meta">
                            <span className="meta-label">Осталось:</span>
                            <span className={`meta-value ${isExpiringSoon ? 'warning' : ''} ${isExpired ? 'expired' : ''}`}>
                              {isExpired ? 'Истекла' : `${daysLeft} дн.`}
                            </span>
                          </div>
                        )}

                        <div className="subscription-meta">
                          <span className="meta-label">Оплачено:</span>
                          <span className="meta-value">{sub.total_paid} {sub.currency || 'RUB'}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right Panel - Details */}
          <div className="subscriptions-details-panel">
            {!selectedSubscription ? (
              <div className="subscriptions-details-empty">
                <span className="empty-icon">👈</span>
                <p>Выберите подписку для просмотра деталей</p>
              </div>
            ) : (
              <div className="subscriptions-details">
                <h3>Подробная информация</h3>

                <div className="details-section">
                  <h4>Преподаватель</h4>
                  <div className="detail-row">
                    <span className="detail-label">Имя:</span>
                    <span className="detail-value">{selectedSubscription.teacher_name || '—'}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Email:</span>
                    <span className="detail-value">{selectedSubscription.teacher_email}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">ID:</span>
                    <span className="detail-value">{selectedSubscription.teacher_id}</span>
                  </div>
                </div>

                <div className="details-section">
                  <h4>Подписка</h4>
                  <div className="detail-row">
                    <span className="detail-label">Тариф:</span>
                    <span className="detail-value">{getPlanLabel(selectedSubscription.plan)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Статус:</span>
                    <span className="detail-value">{getStatusBadge(selectedSubscription.status)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Начало:</span>
                    <span className="detail-value">{formatDate(selectedSubscription.started_at)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Истекает:</span>
                    <span className="detail-value">{formatDate(selectedSubscription.expires_at)}</span>
                  </div>
                  {selectedSubscription.cancelled_at && (
                    <div className="detail-row">
                      <span className="detail-label">Отменена:</span>
                      <span className="detail-value">{formatDate(selectedSubscription.cancelled_at)}</span>
                    </div>
                  )}
                  <div className="detail-row">
                    <span className="detail-label">Автопродление:</span>
                    <span className="detail-value">{selectedSubscription.auto_renew ? '✅ Да' : '❌ Нет'}</span>
                  </div>
                </div>

                <div className="details-section">
                  <h4>Финансы</h4>
                  <div className="detail-row">
                    <span className="detail-label">Всего оплачено:</span>
                    <span className="detail-value">
                      {selectedSubscription.total_paid} {selectedSubscription.currency || 'RUB'}
                    </span>
                  </div>
                  {selectedSubscription.last_payment_date && (
                    <div className="detail-row">
                      <span className="detail-label">Последний платёж:</span>
                      <span className="detail-value">{formatDate(selectedSubscription.last_payment_date)}</span>
                    </div>
                  )}
                </div>

                {/* Payments History */}
                {selectedSubscription.payments && selectedSubscription.payments.length > 0 && (
                  <div className="details-section">
                    <h4>История платежей ({selectedSubscription.payments.length})</h4>
                    <div className="payments-list">
                      {selectedSubscription.payments.map((payment) => (
                        <div key={payment.id} className="payment-item">
                          <div className="payment-amount">
                            {payment.amount} {payment.currency || 'RUB'}
                          </div>
                          <div className="payment-meta">
                            <span className={`payment-status status-${payment.status}`}>
                              {payment.status === 'succeeded' && '✅ Успешно'}
                              {payment.status === 'pending' && '⏳ Ожидает'}
                              {payment.status === 'failed' && '❌ Ошибка'}
                              {payment.status === 'refunded' && '↩️ Возврат'}
                            </span>
                            <span className="payment-date">{formatDate(payment.created_at)}</span>
                          </div>
                          {payment.payment_system && (
                            <div className="payment-system">
                              Система: {payment.payment_system}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="details-actions">
                  {false && selectedSubscription.plan === 'trial' && selectedSubscription.status === 'active' && (
                    <button
                      onClick={handleExtendTrial}
                      disabled={busy}
                      className="action-btn btn-primary"
                    >
                      ⏱️ Продлить пробный период
                    </button>
                  )}

                  {selectedSubscription.status === 'active' && selectedSubscription.auto_renew && (
                    <button
                      onClick={handleCancelSubscription}
                      disabled={busy}
                      className="action-btn btn-warning"
                    >
                      ❌ Отменить автопродление
                    </button>
                  )}

                  {false && (selectedSubscription.status === 'cancelled' || selectedSubscription.status === 'expired') && (
                    <button
                      onClick={handleActivateSubscription}
                      disabled={busy}
                      className="action-btn btn-success"
                    >
                      ✅ Активировать подписку
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionsModal;
