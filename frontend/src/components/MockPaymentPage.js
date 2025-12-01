import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import './MockPaymentPage.css';

const MockPaymentPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [redirecting, setRedirecting] = useState(false);
  const paymentId = searchParams.get('payment_id');

  // Защита от зависания при навигации "Назад"
  useEffect(() => {
    let isNavigating = false;

    // Обработка возврата назад через браузер
    const handleBackButton = (e) => {
      if (!isNavigating) {
        isNavigating = true;
        // При возврате назад редиректим на subscription
        navigate('/teacher/subscription', { replace: true });
      }
    };
    
    // Обработка pageshow (когда страница восстанавливается из bfcache)
    const handlePageShow = (e) => {
      if (e.persisted && !isNavigating) {
        // Страница из cache - редиректим
        isNavigating = true;
        navigate('/teacher/subscription', { replace: true });
      }
    };
    
    window.addEventListener('popstate', handleBackButton);
    window.addEventListener('pageshow', handlePageShow);
    
    return () => {
      window.removeEventListener('popstate', handleBackButton);
      window.removeEventListener('pageshow', handlePageShow);
    };
  }, [navigate]);

  const handleReturn = () => {
    if (redirecting) return; // Защита от повторных кликов
    setRedirecting(true);
    // Используем replace вместо push, чтобы не добавлять в историю
    navigate('/teacher/subscription', { replace: true });
  };

  return (
    <div className="mock-payment-page">
      <div className="mock-payment-card">
        <div className="mock-icon">💳</div>
        <h1>Тестовый платёж</h1>
        <p className="mock-subtitle">
          Это демо-страница оплаты для разработки
        </p>

        <div className="mock-info">
          <div className="info-row">
            <span className="label">Payment ID:</span>
            <span className="value">{paymentId || 'N/A'}</span>
          </div>
          <div className="info-row">
            <span className="label">Статус:</span>
            <span className="value success">✅ Успешно (mock)</span>
          </div>
          <div className="info-row">
            <span className="label">Режим:</span>
            <span className="value">Development (без реальных credentials)</span>
          </div>
        </div>

        <div className="mock-notice">
          <div className="notice-icon">ℹ️</div>
          <div className="notice-text">
            <strong>Для production:</strong>
            <p>Установите YOOKASSA_ACCOUNT_ID, YOOKASSA_SECRET_KEY в переменные окружения для реальной интеграции с YooKassa.</p>
          </div>
        </div>

        <div className="mock-redirect">
          <button 
            className="skip-button" 
            onClick={handleReturn}
            disabled={redirecting}
          >
            {redirecting ? 'Возвращаем...' : 'Вернуться в личный кабинет'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default MockPaymentPage;
