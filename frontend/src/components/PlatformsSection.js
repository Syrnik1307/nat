import React, { useState } from 'react';
import { apiClient } from '../apiService';
import './PlatformsSection.css';

/**
 * Секция "Платформы для проведения уроков" в профиле учителя.
 * Показывает статус подключения Zoom и Google Meet с кнопками настройки.
 */
const PlatformsSection = ({ user, onRefresh }) => {
  const [loading, setLoading] = useState(null); // 'zoom' | 'google_meet' | null
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Статусы из user (приходят с бэкенда через сериализатор)
  const zoomConnected = user?.zoom_connected || false;
  const googleMeetConnected = user?.google_meet_connected || false;
  const googleMeetEmail = user?.google_meet_email || '';

  // Начать OAuth авторизацию Google Meet
  const handleConnectGoogleMeet = async () => {
    setLoading('google_meet');
    setError('');
    try {
      const response = await apiClient.get('/integrations/google-meet/auth-url/');
      if (response.data?.auth_url) {
        // Редирект на Google OAuth
        window.location.href = response.data.auth_url;
      } else {
        setError('Не удалось получить ссылку авторизации. Попробуйте позже.');
      }
    } catch (err) {
      console.error('Google Meet auth error:', err);
      if (err.response?.status === 501) {
        setError('Google Meet интеграция пока не настроена на сервере.');
      } else {
        setError(err.response?.data?.detail || 'Ошибка подключения Google Meet');
      }
    } finally {
      setLoading(null);
    }
  };

  // Отключить Google Meet
  const handleDisconnectGoogleMeet = async () => {
    if (!window.confirm('Отключить Google Meet? Вы сможете подключить его снова в любой момент.')) {
      return;
    }
    setLoading('google_meet');
    setError('');
    try {
      await apiClient.post('/integrations/google-meet/disconnect/');
      setSuccess('Google Meet отключён');
      if (onRefresh) onRefresh();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      console.error('Google Meet disconnect error:', err);
      setError(err.response?.data?.detail || 'Не удалось отключить Google Meet');
    } finally {
      setLoading(null);
    }
  };

  return (
    <section className="platforms-section">
      <div className="platforms-header">
        <div>
          <h3>Платформы для уроков</h3>
          <p className="platforms-subtitle">
            Подключите платформы видеоконференций для проведения онлайн-уроков
          </p>
        </div>
      </div>

      <div className="platforms-grid">
        {/* Zoom через пул платформы */}
        <div className="platform-card">
          <div className="platform-icon zoom-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
              <path d="M4.585 11.828V16a2 2 0 002 2h7.829a2 2 0 002-2v-4.172a2 2 0 00-2-2H6.585a2 2 0 00-2 2zm13.243 4.415l2.829 2.122a.75.75 0 001.193-.607V10.071a.75.75 0 00-1.193-.607l-2.829 2.122v4.657z"/>
            </svg>
          </div>
          <div className="platform-info">
            <h4>Zoom (пул платформы)</h4>
            <p className="platform-description">
              Используйте Zoom без настройки. Аккаунты предоставляются платформой автоматически.
            </p>
            <span className="platform-status connected">
              Доступен
            </span>
          </div>
          <div className="platform-actions">
            <span className="platform-badge success">Готово к работе</span>
          </div>
        </div>

        {/* Персональный Zoom */}
        <div className="platform-card">
          <div className="platform-icon zoom-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
              <path d="M4.585 11.828V16a2 2 0 002 2h7.829a2 2 0 002-2v-4.172a2 2 0 00-2-2H6.585a2 2 0 00-2 2zm13.243 4.415l2.829 2.122a.75.75 0 001.193-.607V10.071a.75.75 0 00-1.193-.607l-2.829 2.122v4.657z"/>
            </svg>
          </div>
          <div className="platform-info">
            <h4>Zoom (личный аккаунт)</h4>
            <p className="platform-description">
              Подключите свой Zoom аккаунт для использования личных настроек и брендинга.
            </p>
            <span className={`platform-status ${zoomConnected ? 'connected' : 'disconnected'}`}>
              {zoomConnected ? 'Подключён' : 'Не подключён'}
            </span>
          </div>
          <div className="platform-actions">
            {zoomConnected ? (
              <span className="platform-badge success">Настроен</span>
            ) : (
              <button
                type="button"
                className="platform-connect-btn"
                onClick={() => {
                  // Показать инструкцию для Zoom (более сложная настройка)
                  setError('');
                  setSuccess('');
                  // Открываем модалку с инструкцией или переходим на страницу
                  window.open('/zoom-setup-guide', '_blank');
                }}
              >
                Инструкция по настройке
              </button>
            )}
          </div>
        </div>

        {/* Google Meet */}
        <div className="platform-card">
          <div className="platform-icon meet-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </div>
          <div className="platform-info">
            <h4>Google Meet</h4>
            <p className="platform-description">
              Подключите Google аккаунт для создания встреч в Google Meet.
              {googleMeetEmail && (
                <span className="platform-email"> ({googleMeetEmail})</span>
              )}
            </p>
            <span className={`platform-status ${googleMeetConnected ? 'connected' : 'disconnected'}`}>
              {googleMeetConnected ? 'Подключён' : 'Не подключён'}
            </span>
          </div>
          <div className="platform-actions">
            {googleMeetConnected ? (
              <>
                <span className="platform-badge success">Готово к работе</span>
                <button
                  type="button"
                  className="platform-disconnect-btn"
                  onClick={handleDisconnectGoogleMeet}
                  disabled={loading === 'google_meet'}
                >
                  {loading === 'google_meet' ? 'Отключение...' : 'Отключить'}
                </button>
              </>
            ) : (
              <button
                type="button"
                className="platform-connect-btn primary"
                onClick={handleConnectGoogleMeet}
                disabled={loading === 'google_meet'}
              >
                {loading === 'google_meet' ? 'Подключение...' : 'Подключить Google Meet'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Сообщения об ошибках и успехе */}
      {error && (
        <div className="platforms-message error">
          {error}
        </div>
      )}
      {success && (
        <div className="platforms-message success">
          {success}
        </div>
      )}

      {/* Инструкция */}
      <div className="platforms-help">
        <h4>Как это работает?</h4>
        <ul>
          <li>
            <strong>Zoom (пул платформы)</strong> — всегда доступен. При запуске урока система автоматически выделит вам Zoom-комнату.
          </li>
          <li>
            <strong>Zoom (личный)</strong> — для продвинутых пользователей. Требует настройки Server-to-Server OAuth в Zoom Marketplace.
          </li>
          <li>
            <strong>Google Meet</strong> — подключите Google аккаунт одним кликом. Встречи создаются автоматически через Google Calendar.
          </li>
        </ul>
        <p className="platforms-help-note">
          При запуске урока вы сможете выбрать любую из подключённых платформ.
        </p>
        <p className="platforms-help-link">
          <a 
            href="https://github.com/your-repo/teaching-panel/blob/main/PLATFORM_SETUP_GUIDE.md" 
            target="_blank" 
            rel="noopener noreferrer"
          >
            Подробная инструкция по настройке платформ
          </a>
          {' '}(для администраторов)
        </p>
      </div>
    </section>
  );
};

export default PlatformsSection;
