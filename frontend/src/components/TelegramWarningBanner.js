import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getTelegramStatus, generateTelegramCode } from '../apiService';
import './TelegramWarningBanner.css';

const TelegramWarningBanner = () => {
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [linkMessage, setLinkMessage] = useState('');
  const [linkError, setLinkError] = useState('');

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const response = await getTelegramStatus();
      console.log('[TelegramWarningBanner] API response:', response.data);
      if (!response.data.telegram_linked) {
        console.log('[TelegramWarningBanner] Telegram not linked, showing banner');
        setShow(true);
      } else {
        console.log('[TelegramWarningBanner] Telegram already linked, hiding banner');
      }
    } catch (err) {
      console.error('[TelegramWarningBanner] Failed to check telegram status:', err);
      // Не показываем баннер если не смогли проверить (избегаем ложных срабатываний)
    } finally {
      setLoading(false);
    }
  };

  const openTelegramLink = (url) => {
    if (!url) return;
    const newTab = window.open(url, '_blank');
    if (!newTab) {
      window.location.href = url;
    }
  };

  const handleConnectClick = async () => {
    if (linking) {
      return;
    }
    setLinkError('');
    setLinkMessage('');
    setLinking(true);

    try {
      const { data } = await generateTelegramCode();
      const deepLink = data?.deep_link;

      if (deepLink) {
        setLinkMessage('Открываем Telegram... Если ничего не произошло, нажмите повторно.');
        openTelegramLink(deepLink);
      } else {
        setLinkMessage('Код создан. Завершите привязку на странице профиля, вкладка «Безопасность».');
      }
    } catch (err) {
      console.error('[TelegramWarningBanner] Failed to generate telegram code:', err);
      setLinkError(err.response?.data?.detail || 'Не удалось открыть Telegram. Попробуйте ещё раз или настройте вручную.');
    } finally {
      setLinking(false);
    }
  };

  if (loading || !show) {
    console.log('[TelegramWarningBanner] Not rendering:', { loading, show });
    return null;
  }

  console.log('[TelegramWarningBanner] Rendering banner');
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
            <button
              type="button"
              className="banner-button primary"
              onClick={handleConnectClick}
              disabled={linking}
            >
              {linking ? 'Создаём ссылку...' : '🔗 Привязать Telegram сейчас'}
            </button>
            <div className="banner-benefits">
              <span className="benefit">✅ Восстановление пароля за 30 сек</span>
              <span className="benefit">✅ Уведомления в реальном времени</span>
              <span className="benefit">✅ Напоминания о занятиях</span>
            </div>
            {(linkMessage || linkError) && (
              <p className={`banner-message ${linkError ? 'error' : 'success'}`}>
                {linkError || linkMessage}
              </p>
            )}
            <Link to="/profile?tab=security" className="banner-secondary-link">
              Настроить вручную в профиле
            </Link>
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
