import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth';
import { getAccessToken } from '../apiService';
import './SupportWidget.css';

const SupportWidget = () => {
  const { accessTokenValid } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [supportUrl, setSupportUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorText, setErrorText] = useState('');

  useEffect(() => {
    if (accessTokenValid) {
      // preload link lazily (only when widget is opened)
    }
  }, [accessTokenValid]);

  const loadSupportLink = async () => {
    setLoading(true);
    setErrorText('');
    try {
      const token = getAccessToken();
      const response = await fetch('/api/support/telegram-link/', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        setErrorText(body.detail || 'Не удалось получить ссылку на Telegram');
        return;
      }

      const data = await response.json();
      setSupportUrl(data.url || '');
      if (!data.url) {
        setErrorText('Не удалось получить ссылку на Telegram');
      }
    } catch (err) {
      setErrorText('Не удалось получить ссылку на Telegram');
    } finally {
      setLoading(false);
    }
  };

  const openTelegram = async () => {
    if (!supportUrl) {
      await loadSupportLink();
    }
    if (supportUrl) {
      window.open(supportUrl, '_blank', 'noopener,noreferrer');
    }
  };

  const onToggle = async () => {
    const next = !isOpen;
    setIsOpen(next);
    if (next && accessTokenValid && !supportUrl) {
      await loadSupportLink();
    }
  };

  return (
    <>
      {/* Плавающая кнопка */}
      <button
        className={`support-fab ${isOpen ? 'support-fab-open' : ''}`}
        onClick={onToggle}
        title="Поддержка"
        aria-label={isOpen ? 'Закрыть чат поддержки' : 'Открыть чат поддержки'}
      >
        {isOpen ? '×' : '💬'}
      </button>

      {/* Виджет поддержки */}
      {isOpen && (
        <div className="support-widget">
          <div className="support-widget-header">
            <h3>💬 Поддержка</h3>
            <button
              className="support-widget-close"
              onClick={() => setIsOpen(false)}
            >
              ×
            </button>
          </div>

          <div className="support-widget-body">
            <div className="support-empty-state">
              <p>Поддержка доступна в Telegram.</p>
              {errorText && (
                <p>{errorText}</p>
              )}
              <button
                className="support-create-first-btn"
                onClick={openTelegram}
                disabled={loading || !accessTokenValid}
              >
                {loading ? 'Открываем...' : 'Открыть поддержку в Telegram'}
              </button>
              {!accessTokenValid && (
                <small>Войдите в аккаунт, чтобы написать в поддержку.</small>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SupportWidget;
