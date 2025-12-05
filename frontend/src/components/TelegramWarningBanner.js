import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { getTelegramStatus, generateTelegramCode } from '../apiService';
import './TelegramWarningBanner.css';

const TelegramWarningBanner = () => {
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [linkMessage, setLinkMessage] = useState('');
  const [linkError, setLinkError] = useState('');
  const [deepLink, setDeepLink] = useState('');
  const [prefetching, setPrefetching] = useState(false);
  const isPrefetchingRef = useRef(false);

  const prefetchTelegramLink = useCallback(async (silent = false) => {
    if (isPrefetchingRef.current) {
      return;
    }
    isPrefetchingRef.current = true;
    if (!silent) {
      setLinkMessage('Готовим ссылку для Telegram...');
    }
    setLinkError('');
    setPrefetching(true);
    try {
      const { data } = await generateTelegramCode();
      // Резерв: если backend вернул пустой deep_link, собираем сами из bot_username + code
      const fallbackLink = data?.code && data?.bot_username
        ? `https://t.me/${data.bot_username}?start=${data.code}`
        : '';
      setDeepLink(data?.deep_link || fallbackLink);
      if (!silent) {
        setLinkMessage('Ссылка обновлена. Нажмите кнопку, чтобы открыть Telegram.');
      }
    } catch (err) {
      console.error('[TelegramWarningBanner] Failed to prefetch telegram code:', err);
      setLinkError(err.response?.data?.detail || 'Не удалось подготовить ссылку. Попробуйте позже или настройте вручную.');
    } finally {
      setPrefetching(false);
      isPrefetchingRef.current = false;
    }
  }, []);

  const checkStatus = useCallback(async () => {
    try {
      const response = await getTelegramStatus();
      console.log('[TelegramWarningBanner] API response:', response.data);
      if (!response.data.telegram_linked) {
        console.log('[TelegramWarningBanner] Telegram not linked, showing banner');
        setShow(true);
        prefetchTelegramLink();
      } else {
        console.log('[TelegramWarningBanner] Telegram already linked, hiding banner');
      }
    } catch (err) {
      console.error('[TelegramWarningBanner] Failed to check telegram status:', err);
      // Не показываем баннер если не смогли проверить (избегаем ложных срабатываний)
    } finally {
      setLoading(false);
    }
  }, [prefetchTelegramLink]);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const openTelegramLink = (url) => {
    if (!url) return;
    const newTab = window.open(url, '_blank');
    if (!newTab) {
      window.location.href = url;
    }
  };

  const handleConnectClick = async () => {
    if (linking || prefetching) {
      return;
    }

    if (!deepLink) {
      setLinkError('Не удалось получить ссылку автоматически. Пробуем ещё раз...');
      await prefetchTelegramLink(true);
      return;
    }

    setLinkError('');
    setLinkMessage('Открываем Telegram...');
    setLinking(true);

    openTelegramLink(deepLink);
    await prefetchTelegramLink(true);
    setLinking(false);
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
              disabled={linking || prefetching}
            >
              {linking || prefetching ? 'Готовим ссылку...' : 'Привязать Telegram сейчас'}
            </button>
            <div className="banner-benefits">
              <span className="benefit">Восстановление пароля за 30 сек</span>
              <span className="benefit">Уведомления в реальном времени</span>
              <span className="benefit">Напоминания о занятиях</span>
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
