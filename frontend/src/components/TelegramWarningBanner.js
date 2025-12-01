import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getTelegramStatus } from '../apiService';
import './TelegramWarningBanner.css';

const TelegramWarningBanner = () => {
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const { data } = await getTelegramStatus();
      if (!data.telegram_linked) {
        setShow(true);
      }
    } catch (err) {
      console.error('Failed to check telegram status:', err);
      // Показываем баннер если не смогли проверить
      setShow(true);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !show) {
    return null;
  }

  return (
    <div className="telegram-warning-banner">
      <div className="banner-container">
        <div className="banner-icon">
          <span className="icon-emoji">⚠️</span>
        </div>
        <div className="banner-content">
          <h3 className="banner-title">Защитите свой аккаунт</h3>
          <p className="banner-text">
            Привяжите Telegram для быстрого восстановления пароля и получения уведомлений о новых домашних заданиях.
            <strong> Это займёт всего 1 минуту!</strong>
          </p>
          <div className="banner-actions">
            <Link to="/profile?tab=security" className="banner-button primary">
              🔗 Привязать Telegram сейчас
            </Link>
            <div className="banner-benefits">
              <span className="benefit">✅ Восстановление пароля за 30 сек</span>
              <span className="benefit">✅ Уведомления в реальном времени</span>
              <span className="benefit">✅ Напоминания о занятиях</span>
            </div>
          </div>
        </div>
        <button 
          className="banner-close"
          onClick={() => setShow(false)}
          title="Скрыть до следующего входа"
        >
          ✕
        </button>
      </div>
    </div>
  );
};

export default TelegramWarningBanner;
