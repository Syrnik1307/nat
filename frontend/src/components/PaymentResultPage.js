import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../apiService';
import { useAuth } from '../auth';
import Button from '../shared/components/Button';
import './PaymentResultPage.css';

// Иконка успеха (без эмодзи!)
const IconSuccess = ({ size = 64 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="32" cy="32" r="30" stroke="#10B981" strokeWidth="4" fill="rgba(16, 185, 129, 0.1)" />
    <path 
      d="M20 32L28 40L44 24" 
      stroke="#10B981" 
      strokeWidth="4" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    />
  </svg>
);

// Иконка ошибки
const IconError = ({ size = 64 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="32" cy="32" r="30" stroke="#EF4444" strokeWidth="4" fill="rgba(239, 68, 68, 0.1)" />
    <path 
      d="M24 24L40 40M40 24L24 40" 
      stroke="#EF4444" 
      strokeWidth="4" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    />
  </svg>
);

// Иконка обработки
const IconProcessing = ({ size = 64 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="processing-spinner">
    <circle cx="32" cy="32" r="30" stroke="#E2E8F0" strokeWidth="4" fill="none" />
    <path 
      d="M32 2C48.5685 2 62 15.4315 62 32" 
      stroke="#4F46E5" 
      strokeWidth="4" 
      strokeLinecap="round"
    />
  </svg>
);

// Иконка ожидания
const IconPending = ({ size = 64 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="32" cy="32" r="30" stroke="#F59E0B" strokeWidth="4" fill="rgba(245, 158, 11, 0.1)" />
    <circle cx="32" cy="32" r="4" fill="#F59E0B" />
    <path d="M32 18V28" stroke="#F59E0B" strokeWidth="4" strokeLinecap="round" />
    <path d="M32 36V46" stroke="#F59E0B" strokeWidth="4" strokeLinecap="round" />
    <path d="M18 32H28" stroke="#F59E0B" strokeWidth="4" strokeLinecap="round" />
    <path d="M36 32H46" stroke="#F59E0B" strokeWidth="4" strokeLinecap="round" />
  </svg>
);

const PaymentResultPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { refreshSubscription } = useAuth();
  
  const [status, setStatus] = useState('checking'); // checking, success, pending, error
  const [message, setMessage] = useState('');
  const [details, setDetails] = useState(null);
  const [countdown, setCountdown] = useState(5);

  // Проверка статуса платежа
  const checkPaymentStatus = useCallback(async () => {
    try {
      // Синхронизируем платежи с платёжной системой
      await apiClient.post('subscription/sync-payments/');
      
      // Получаем актуальную информацию о подписке
      const response = await apiClient.get('subscription/');
      const subscription = response.data;
      
      // Обновляем глобальный кеш подписки
      if (refreshSubscription) {
        refreshSubscription();
      }
      
      // Проверяем статус подписки
      const isSubscriptionActive = subscription.status === 'active' && 
                                   new Date(subscription.expires_at) > new Date();
      
      if (isSubscriptionActive) {
        setStatus('success');
        setMessage('Оплата прошла успешно');
        setDetails({
          plan: subscription.plan === 'monthly' ? 'Месячная подписка' : 'Годовая подписка',
          expiresAt: new Date(subscription.expires_at).toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
          })
        });
      } else if (subscription.status === 'pending') {
        setStatus('pending');
        setMessage('Платёж обрабатывается');
      } else if (subscription.status === 'active' && new Date(subscription.expires_at) <= new Date()) {
        // Подписка была активна, но уже истекла - нужно продлить
        setStatus('pending');
        setMessage('Подписка истекла. Продлите её чтобы продолжить пользование');
      } else {
        // Подписка не активна - возможно платёж не прошёл
        // Но не показываем ошибку сразу, платёж может ещё обрабатываться
        setStatus('pending');
        setMessage('Ожидание подтверждения платежа');
      }
    } catch (error) {
      console.error('Failed to check payment status:', error);
      setStatus('error');
      setMessage('Не удалось проверить статус платежа');
    }
  }, [refreshSubscription]);

  useEffect(() => {
    checkPaymentStatus();
  }, [checkPaymentStatus]);

  // Автоматический редирект после успешной оплаты
  useEffect(() => {
    if (status !== 'success') return;
    
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          navigate('/profile?tab=subscription', { replace: true });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [status, navigate]);

  const handleGoToSubscription = () => {
    navigate('/profile?tab=subscription', { replace: true });
  };

  const handleRetry = () => {
    setStatus('checking');
    checkPaymentStatus();
  };

  const handleGoToSupport = () => {
    navigate('/chat', { replace: true });
  };

  return (
    <div className="payment-result-page">
      <div className="payment-result-card">
        {/* Checking state */}
        {status === 'checking' && (
          <>
            <div className="result-icon result-icon-processing">
              <IconProcessing size={72} />
            </div>
            <h1 className="result-title">Проверяем платёж</h1>
            <p className="result-message">
              Пожалуйста, подождите...
            </p>
          </>
        )}

        {/* Success state */}
        {status === 'success' && (
          <>
            <div className="result-icon result-icon-success">
              <IconSuccess size={72} />
            </div>
            <h1 className="result-title result-title-success">Оплата прошла успешно</h1>
            <p className="result-message">
              Ваша подписка активирована
            </p>
            
            {details && (
              <div className="result-details">
                <div className="detail-row">
                  <span className="detail-label">Тариф</span>
                  <span className="detail-value">{details.plan}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Активна до</span>
                  <span className="detail-value">{details.expiresAt}</span>
                </div>
              </div>
            )}

            <div className="result-actions">
              <Button 
                variant="primary" 
                onClick={handleGoToSubscription}
                className="result-button"
              >
                Перейти в личный кабинет
              </Button>
              <p className="auto-redirect-text">
                Автоматический переход через {countdown} сек.
              </p>
            </div>
          </>
        )}

        {/* Pending state */}
        {status === 'pending' && (
          <>
            <div className="result-icon result-icon-pending">
              <IconPending size={72} />
            </div>
            <h1 className="result-title result-title-pending">Платёж обрабатывается</h1>
            <p className="result-message">
              Мы ожидаем подтверждение от платёжной системы. 
              Обычно это занимает несколько минут.
            </p>
            
            <div className="result-hint">
              <p>Вы можете закрыть эту страницу — подписка будет активирована автоматически после подтверждения оплаты.</p>
            </div>

            <div className="result-actions">
              <Button 
                variant="secondary" 
                onClick={handleRetry}
                className="result-button"
              >
                Проверить статус
              </Button>
              <Button 
                variant="ghost" 
                onClick={handleGoToSubscription}
                className="result-button"
              >
                Вернуться в личный кабинет
              </Button>
            </div>
          </>
        )}

        {/* Error state */}
        {status === 'error' && (
          <>
            <div className="result-icon result-icon-error">
              <IconError size={72} />
            </div>
            <h1 className="result-title result-title-error">Что-то пошло не так</h1>
            <p className="result-message">
              {message}
            </p>
            
            <div className="result-hint">
              <p>Если с вашей карты были списаны средства, но подписка не активировалась — свяжитесь с нами, мы поможем разобраться.</p>
            </div>

            <div className="result-actions">
              <Button 
                variant="primary" 
                onClick={handleRetry}
                className="result-button"
              >
                Попробовать снова
              </Button>
              <Button 
                variant="secondary" 
                onClick={handleGoToSupport}
                className="result-button"
              >
                Написать в поддержку
              </Button>
              <Button 
                variant="ghost" 
                onClick={handleGoToSubscription}
                className="result-button"
              >
                Вернуться в личный кабинет
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default PaymentResultPage;
