import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import './MockPaymentPage.css';

const MockPaymentPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [countdown, setCountdown] = useState(5);
  const paymentId = searchParams.get('payment_id');

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          navigate('/teacher/subscription?payment=mock-success');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [navigate]);

  const handleSkip = () => {
    navigate('/teacher/subscription?payment=mock-success');
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
          <p>Автоматический возврат через <strong>{countdown}</strong> сек...</p>
          <button className="skip-button" onClick={handleSkip}>
            Вернуться сейчас
          </button>
        </div>
      </div>
    </div>
  );
};

export default MockPaymentPage;
