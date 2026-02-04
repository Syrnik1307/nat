import React, { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient } from '../apiService';
import { useAuth } from '../auth';
import Modal from '../shared/components/Modal';
import Button from '../shared/components/Button';
import { SubscriptionOnboarding } from './Onboarding';
import './SubscriptionPage.css';

const SubscriptionPage = ({ embedded = false }) => {
  const { subscription: cachedSubscription, refreshSubscription } = useAuth();
  
  // Используем кешированные данные из AuthContext как начальные
  const [loading, setLoading] = useState(!cachedSubscription);
  const [subData, setSubData] = useState(cachedSubscription);
  const [storageStats, setStorageStats] = useState(null);
  const [storageLoading, setStorageLoading] = useState(false);
  const [storageGb, setStorageGb] = useState(10);
  const [processing, setProcessing] = useState(false);
  const processingRef = useRef(false);

  // Zoom add-on
  const [zoomMode, setZoomMode] = useState('pool');
  const [zoomPersonal, setZoomPersonal] = useState({
    accountId: '',
    clientId: '',
    clientSecret: '',
    userId: 'me',
  });
  const [zoomAssignedEmail, setZoomAssignedEmail] = useState('');
  
  // Состояния для модальных окон
  const [errorModal, setErrorModal] = useState({ isOpen: false, message: '' });
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, action: null, message: '' });

  const loadSubscription = useCallback(async (skipMainLoading = false) => {
    if (!skipMainLoading) {
      setLoading(true);
    }
    try {
      const subResponse = await apiClient.get('subscription/');
      setSubData(subResponse.data);
      // Also update global cache in AuthContext
      if (refreshSubscription) {
        refreshSubscription();
      }
    } catch (error) {
      console.error('Failed to load subscription:', error);
    } finally {
      setLoading(false);
    }

    setStorageLoading(true);
    try {
      const storageResponse = await apiClient.get('subscription/storage/');
      setStorageStats(storageResponse.data);
    } catch (error) {
      console.error('Failed to load storage stats:', error);
    } finally {
      setStorageLoading(false);
    }
  }, [refreshSubscription]);

  // Sync pending payments with T-Bank API
  const syncPendingPayments = useCallback(async () => {
    try {
      await apiClient.post('subscription/sync-payments/');
    } catch (error) {
      console.error('Failed to sync payments:', error);
    }
    // Always reload subscription and storage after sync attempt
    await loadSubscription();
  }, [loadSubscription]);

  useEffect(() => {
    processingRef.current = processing;
  }, [processing]);

  useEffect(() => {
    // Check if returning from payment
    const searchParams = new URLSearchParams(window.location.search);
    const hasPaymentStatus = searchParams.has('status') || searchParams.has('payment');
    
    if (hasPaymentStatus) {
      // Sync payments first, then load subscription
      syncPendingPayments();
      // Clean up URL
      const newUrl = window.location.pathname;
      window.history.replaceState({}, '', newUrl);
    } else {
      // Если есть кеш — не показываем loading, просто обновляем данные в фоне
      loadSubscription(!!cachedSubscription);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadSubscription]);

  useEffect(() => {
    const handlePageShow = (event) => {
      const navEntries = typeof performance !== 'undefined' && performance.getEntriesByType
        ? performance.getEntriesByType('navigation')
        : [];
      const cameFromHistory = Array.isArray(navEntries) && navEntries.some((entry) => entry.type === 'back_forward');

      if ((event.persisted || cameFromHistory) && processingRef.current) {
        setProcessing(false);
        // Sync pending payments when returning from payment page
        syncPendingPayments();
      }
    };

    const handleFocus = () => {
      if (!processingRef.current) return;
      setProcessing(false);
      // Also sync on window focus (user returned from payment tab)
      syncPendingPayments();
    };

    window.addEventListener('pageshow', handlePageShow);
    window.addEventListener('focus', handleFocus);

    return () => {
      window.removeEventListener('pageshow', handlePageShow);
      window.removeEventListener('focus', handleFocus);
    };
  }, [loadSubscription]);

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
      
      // Если подписка уже активна, показываем сообщение
      if (response.data.status === 'already_active') {
        setErrorModal({ 
          isOpen: true, 
          message: 'У вас уже есть активная подписка. Продление будет доступно после её истечения.' 
        });
        setProcessing(false);
        return;
      }
      
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

  const handlePayZoomAddon = async () => {
    if (processing) return;
    setProcessing(true);
    try {
      const response = await apiClient.post('subscription/zoom/create-payment/', {});
      const paymentUrl = response.data.payment_url;
      window.location.href = paymentUrl;
    } catch (error) {
      console.error('Zoom add-on payment failed:', error);
      setErrorModal({
        isOpen: true,
        message: 'Не удалось создать платёж за Zoom. Попробуйте позже.'
      });
      setProcessing(false);
    }
  };

  const handleSetupZoomAddon = async () => {
    if (processing) return;
    setProcessing(true);
    try {
      setZoomAssignedEmail('');
      const payload = zoomMode === 'personal'
        ? { mode: 'personal', ...zoomPersonal }
        : { mode: 'pool' };

      const response = await apiClient.post('subscription/zoom/setup/', payload);
      if (response?.data?.assigned_zoom_email) {
        setZoomAssignedEmail(response.data.assigned_zoom_email);
      }
      await loadSubscription(true);
    } catch (error) {
      console.error('Zoom add-on setup failed:', error);
      const detail = error?.response?.data?.detail;
      setErrorModal({
        isOpen: true,
        message: detail || 'Не удалось настроить Zoom. Проверьте данные и попробуйте ещё раз.'
      });
    } finally {
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
  const isZoomAddonActive = !!subData?.zoom_addon_active;

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

  const containerClassName = `subscription-page${embedded ? ' embedded' : ''}`;

  return (
    <div className={containerClassName}>
      {/* Онбординг для страницы подписки */}
      {!embedded && <SubscriptionOnboarding />}
      
      <header className={`sub-header${embedded ? ' sub-header-embedded' : ''}`}>
        <h1>Подписка</h1>
      </header>

      {/* Уведомление для новых пользователей без оплаченной подписки */}
      {subData?.status === 'pending' && (
        <div className="subscription-notice pending-notice">
          <div className="notice-content">
            <h3>Добро пожаловать!</h3>
            <p>
              Для запуска занятий через Zoom и использования всех функций платформы 
              необходимо оформить подписку. После оплаты вы получите доступ к:
            </p>
            <ul>
              <li>Создание и запуск Zoom-уроков</li>
              <li>Автоматическая запись занятий</li>
              <li>Хранилище для видеозаписей (10 GB)</li>
              <li>Система домашних заданий</li>
            </ul>
          </div>
        </div>
      )}

      {/* Текущая подписка */}
      <section className="current-subscription" data-tour="subscription-status">
        <h2>Статус</h2>
        <div className="sub-card">
          <div className="sub-status">
            <span className={`status-badge status-${subData?.status}`}>
              {subData?.status === 'active' && isActive && 'Активна'}
              {subData?.status === 'active' && !isActive && 'Истекла'}
              {subData?.status === 'pending' && 'Требуется оплата'}
              {subData?.status === 'cancelled' && 'Отменена'}
              {subData?.status === 'expired' && 'Истекла'}
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
                {storageStats ? formatGb(storageStats.used_gb) : formatGb(subData?.used_storage_gb)} / {storageStats?.limit_gb || subData?.total_storage_gb} GB
                {subData?.extra_storage_gb > 0 && (
                  <span className="storage-extra"> (+{subData.extra_storage_gb} GB доп.)</span>
                )}
              </span>
            </div>
            {subData?.gdrive_folder_link && (
              <div className="detail-row">
                <span className="label">Папка на Диске:</span>
                <span className="value">
                  <a href={subData.gdrive_folder_link} target="_blank" rel="noopener noreferrer" className="gdrive-link">
                    Открыть в Google Drive
                  </a>
                </span>
              </div>
            )}
          </div>

          {/* Прогресс-бар использования хранилища */}
          {(storageStats || subData) && (
            <div className="storage-usage-bar" data-tour="subscription-storage-bar">
              <div className="storage-bar-container">
                <div
                  className={`storage-bar-fill ${getStorageClass(storageStats?.usage_percent || 0)}`}
                  style={{ width: `${Math.min(100, storageStats?.usage_percent || 0)}%` }}
                />
              </div>
              <div className="storage-bar-label">
                {storageLoading
                  ? 'Обновляем статистику хранилища...'
                  : storageStats ? (
                    <>
                      Использовано: {formatGb(storageStats.used_gb)} из {storageStats.limit_gb} GB
                      ({storageStats.usage_percent}%)
                      {storageStats.file_count > 0 && ` • ${storageStats.file_count} файлов`}
                    </>
                  ) : (
                    `Использовано: ${formatGb(subData?.used_storage_gb)} из ${subData?.total_storage_gb} GB`
                  )}
              </div>
            </div>
          )}

          {/* Минималистичный прогресс-бар оставшихся дней */}
          {daysLeft != null && (
            <div className="cycle-progress" data-tour="subscription-cycle">
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
              data-tour="subscription-pay-btn"
            >
              Оплатить 28 дней
            </button>
            <button 
              className={`toggle-renew-btn ${subData?.auto_renew ? 'renew-enabled' : 'renew-disabled'}`}
              onClick={handleToggleAutoRenew}
              disabled={processing}
              data-tour="subscription-autorenew"
            >
              {subData?.auto_renew ? 'Отключить автопродление' : 'Подключить автопродление'}
            </button>
          </div>
        </div>
      </section>

      {/* Дополнительное хранилище */}
      <section className="storage-section" data-tour="subscription-extra-storage">
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

function getStorageClass(percent) {
  if (percent >= 90) return 'storage-critical';
  if (percent >= 75) return 'storage-warning';
  return 'storage-normal';
}
