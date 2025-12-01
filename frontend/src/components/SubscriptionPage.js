import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../apiService';
import Modal from '../shared/components/Modal';
import Button from '../shared/components/Button';
import './SubscriptionPage.css';

const SubscriptionPage = () => {
  const { user, subscription } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [subData, setSubData] = useState(null);
  const [storageGb, setStorageGb] = useState(10);
  const [processing, setProcessing] = useState(false);
  
  // Состояния для модальных окон
  const [errorModal, setErrorModal] = useState({ isOpen: false, message: '' });
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, action: null, message: '' });

  useEffect(() => {
    loadSubscription();
    
    // Убираем query параметры после показа уведомления
    const searchParams = new URLSearchParams(window.location.search);
    if (searchParams.has('payment')) {
      const newUrl = window.location.pathname;
      window.history.replaceState({}, '', newUrl);
    }
  }, []);

  const loadSubscription = async () => {
    try {
      // Используем относительный путь без повторного /api/
      const response = await apiClient.get('subscription/');
      setSubData(response.data);
    } catch (error) {
      console.error('Failed to load subscription:', error);
    } finally {
      setLoading(false);
    }
  };

  // Тариф один — убираем оплату планов и оставляем только прогресс подписки

  const handleBuyStorage = async () => {
    if (processing || storageGb < 1) return;
    setProcessing(true);

    try {
      const response = await apiClient.post('subscription/add-storage/', { gb: storageGb });
      const paymentUrl = response.data.payment_url;
      
      window.location.href = paymentUrl;
    } catch (error) {
      console.error('Storage payment failed:', error);
      setErrorModal({ 
        isOpen: true, 
        message: 'Не удалось создать платёж. Попробуйте позже.' 
      });
      setProcessing(false);
    }
  };

  const handleToggleAutoRenew = async () => {
    const isCurrentlyEnabled = subData?.auto_renew;
    const action = isCurrentlyEnabled ? 'отключить' : 'включить';
    
    setConfirmModal({
      isOpen: true,
      message: `Вы уверены, что хотите ${action} автопродление?`,
      action: async () => {
        setProcessing(true);
        try {
          if (isCurrentlyEnabled) {
            await apiClient.post('subscription/cancel/');
          } else {
            await apiClient.post('subscription/enable-auto-renew/');
          }
          await loadSubscription();
        } catch (error) {
          console.error('Toggle auto-renew failed:', error);
          setErrorModal({ 
            isOpen: true, 
            message: `Не удалось ${action} автопродление` 
          });
        } finally {
          setProcessing(false);
        }
      }
    });
  };

  const handlePayCycle = async () => {
    if (processing) return;
    setProcessing(true);
    try {
      const response = await apiClient.post('subscription/create-payment/', { plan: 'monthly' });
      const paymentUrl = response.data.payment_url;
      window.location.href = paymentUrl;
    } catch (error) {
      console.error('Payment failed:', error);
      setErrorModal({ 
        isOpen: true, 
        message: 'Не удалось создать платёж' 
      });
      setProcessing(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  const getDaysLeft = () => {
    if (!subData?.expires_at) return null;
    const days = Math.ceil((new Date(subData.expires_at) - new Date()) / (1000 * 60 * 60 * 24));
    return Math.max(0, days);
  };

  const isActive = subData?.status === 'active' && getDaysLeft() > 0;

  // Прогресс-бар: цикл 28 дней
  const totalCycleDays = 28;
  const daysLeft = getDaysLeft();
  const progressPercent = daysLeft != null ? Math.max(0, Math.min(100, Math.round((daysLeft / totalCycleDays) * 100))) : 0;

  if (loading) {
    return (
      <div className="subscription-page">
        <div className="loading">Загрузка...</div>
      </div>
    );
  }

  return (
    <div className="subscription-page">
      <header className="sub-header">
        <h1>Подписка</h1>
      </header>

      {/* Текущая подписка */}
      <section className="current-subscription">
        <h2>Статус</h2>
        <div className="sub-card">
          <div className="sub-status">
            <span className={`status-badge status-${subData?.status}`}>
              {subData?.status === 'active' && isActive && '✅ Активна'}
              {subData?.status === 'active' && !isActive && '⏱️ Истекла'}
              {subData?.status === 'pending' && '⏳ Ожидает оплаты'}
              {subData?.status === 'cancelled' && '❌ Отменена'}
              {subData?.status === 'expired' && '⏱️ Истекла'}
            </span>
          </div>

          <div className="sub-details">
            <div className="detail-row">
              <span className="label">Начало:</span>
              <span className="value">{formatDate(subData?.started_at)}</span>
            </div>
            <div className="detail-row">
              <span className="label">Истекает:</span>
              <span className="value">
                {formatDate(subData?.expires_at)}
                {getDaysLeft() !== null && (
                  <span className={`days-left ${getDaysLeft() <= 7 ? 'warning' : ''}`}>
                    {' '}({getDaysLeft()} дн.)
                  </span>
                )}
              </span>
            </div>
            <div className="detail-row">
              <span className="label">Хранилище:</span>
              <span className="value">
                {formatGb(subData?.used_storage_gb)} / {formatGb(subData?.total_storage_gb)} GB
                {subData?.extra_storage_gb > 0 && (
                  <span className="storage-extra"> (+{subData.extra_storage_gb} GB)</span>
                )}
              </span>
            </div>
          </div>

          {/* Минималистичный прогресс-бар оставшихся дней */}
          {daysLeft != null && (
            <div className="cycle-progress">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <div className="progress-meta">
                Осталось {daysLeft} из {totalCycleDays} дней
              </div>
            </div>
          )}

          <div className="subscription-actions">
            <button 
              className={`pay-btn ${processing ? 'is-loading' : ''}`}
              onClick={handlePayCycle}
              disabled={processing}
            >
              Оплатить 28 дней
            </button>
            <button 
              className={`toggle-renew-btn ${subData?.auto_renew ? 'renew-enabled' : 'renew-disabled'}`}
              onClick={handleToggleAutoRenew}
              disabled={processing}
            >
              {subData?.auto_renew ? 'Отключить автопродление' : 'Подключить автопродление'}
            </button>
          </div>
        </div>
      </section>

      {/* Дополнительное хранилище */}
      <section className="storage-section">
        <h2>Дополнительное хранилище</h2>
        <div className="storage-card">
          <p>Нужно больше места для записей уроков? Докупите дополнительные гигабайты.</p>
          <div className="storage-input-group">
            <label>
              Количество GB:
              <input 
                type="number" 
                min="1" 
                max="1000" 
                value={storageGb}
                onChange={(e) => setStorageGb(parseInt(e.target.value) || 1)}
                disabled={processing}
              />
            </label>
            <div className="storage-price">
              Стоимость: {storageGb * 20} ₽
            </div>
          </div>
          <button 
            className="buy-storage-btn"
            onClick={handleBuyStorage}
            disabled={processing || storageGb < 1}
          >
            Купить {storageGb} GB
          </button>
        </div>
      </section>

      {/* История платежей скрыта для минималистичного вида */}
      
      {/* Модальное окно ошибки */}
      <Modal
        isOpen={errorModal.isOpen}
        onClose={() => setErrorModal({ isOpen: false, message: '' })}
        title="Ошибка"
        size="small"
      >
        <p style={{ margin: 0, fontSize: '1rem', color: '#374151' }}>
          {errorModal.message}
        </p>
        <div style={{ marginTop: '1.5rem', textAlign: 'right' }}>
          <Button 
            variant="primary" 
            onClick={() => setErrorModal({ isOpen: false, message: '' })}
          >
            ОК
          </Button>
        </div>
      </Modal>

      {/* Модальное окно подтверждения */}
      <Modal
        isOpen={confirmModal.isOpen}
        onClose={() => setConfirmModal({ isOpen: false, action: null, message: '' })}
        title="Подтверждение"
        size="small"
      >
        <p style={{ margin: 0, fontSize: '1rem', color: '#374151' }}>
          {confirmModal.message}
        </p>
        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <Button 
            variant="secondary" 
            onClick={() => setConfirmModal({ isOpen: false, action: null, message: '' })}
          >
            Отмена
          </Button>
          <Button 
            variant="primary" 
            onClick={() => {
              if (confirmModal.action) {
                confirmModal.action();
              }
              setConfirmModal({ isOpen: false, action: null, message: '' });
            }}
          >
            Подтвердить
          </Button>
        </div>
      </Modal>
    </div>
  );
};

export default SubscriptionPage;

// Helpers
function formatGb(value) {
  if (value === null || value === undefined) return '0.00';
  const num = typeof value === 'number' ? value : parseFloat(value);
  if (Number.isNaN(num)) return '0.00';
  return num.toFixed(2);
}
