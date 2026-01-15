import React, { useState } from 'react';
import { apiClient } from '../apiService';
import './PlatformsSection.css';

/**
 * Секция "Платформы для проведения уроков" в профиле учителя.
 * Каждый учитель подключает свой личный Zoom и/или Google Meet аккаунт.
 */
const PlatformsSection = ({ user, onRefresh }) => {
  const [loading, setLoading] = useState(null); // 'zoom' | 'google_meet' | null
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Статусы из user (приходят с бэкенда через сериализатор)
  const zoomConnected = user?.zoom_connected || false;
  const googleMeetConnected = user?.google_meet_connected || false;
  const googleMeetEmail = user?.google_meet_email || '';
  const zoomEmail = user?.zoom_email || '';

  // OAuth авторизация Zoom
  const handleConnectZoom = async () => {
    setLoading('zoom');
    setError('');
    setSuccess('');
    try {
      const response = await apiClient.get('/integrations/zoom/auth-url/');
      if (response.data?.auth_url) {
        window.location.href = response.data.auth_url;
      } else {
        setError('Не удалось получить ссылку авторизации');
      }
    } catch (err) {
      console.error('Zoom auth error:', err);
      if (err.response?.status === 501) {
        setError('Zoom OAuth пока не настроен. Обратитесь к администратору.');
      } else {
        setError(err.response?.data?.detail || 'Ошибка подключения Zoom');
      }
    } finally {
      setLoading(null);
    }
  };

  // Отключить Zoom
  const handleDisconnectZoom = async () => {
    if (!window.confirm('Отключить Zoom?')) return;
    setLoading('zoom');
    setError('');
    try {
      await apiClient.post('/integrations/zoom/disconnect/');
      setSuccess('Zoom отключён');
      if (onRefresh) onRefresh();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось отключить Zoom');
    } finally {
      setLoading(null);
    }
  };

  // OAuth авторизация Google Meet
  const handleConnectGoogleMeet = async () => {
    setLoading('google_meet');
    setError('');
    setSuccess('');
    try {
      const response = await apiClient.get('/integrations/google-meet/auth-url/');
      if (response.data?.auth_url) {
        window.location.href = response.data.auth_url;
      } else {
        setError('Не удалось получить ссылку авторизации');
      }
    } catch (err) {
      console.error('Google Meet auth error:', err);
      if (err.response?.status === 501) {
        setError('Google Meet пока не настроен. Обратитесь к администратору.');
      } else {
        setError(err.response?.data?.detail || 'Ошибка подключения Google Meet');
      }
    } finally {
      setLoading(null);
    }
  };

  // Отключить Google Meet
  const handleDisconnectGoogleMeet = async () => {
    if (!window.confirm('Отключить Google Meet?')) return;
    setLoading('google_meet');
    setError('');
    try {
      await apiClient.post('/integrations/google-meet/disconnect/');
      setSuccess('Google Meet отключён');
      if (onRefresh) onRefresh();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось отключить Google Meet');
    } finally {
      setLoading(null);
    }
  };

  return (
    <section className="platforms-section">
      <div className="platforms-header">
        <h3>Платформы для уроков</h3>
        <p className="platforms-subtitle">
          Подключите свои аккаунты для проведения онлайн-уроков
        </p>
      </div>

      {/* Сообщения */}
      {error && <div className="platforms-message error">{error}</div>}
      {success && <div className="platforms-message success">{success}</div>}

      <div className="platforms-grid">
        {/* Zoom */}
        <div className={`platform-card ${zoomConnected ? 'is-connected' : ''}`}>
          <div className="platform-icon zoom-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="28" height="28">
              <path d="M4.585 11.828V16a2 2 0 002 2h7.829a2 2 0 002-2v-4.172a2 2 0 00-2-2H6.585a2 2 0 00-2 2zm13.243 4.415l2.829 2.122a.75.75 0 001.193-.607V10.071a.75.75 0 00-1.193-.607l-2.829 2.122v4.657z"/>
            </svg>
          </div>
          
          <div className="platform-content">
            <div className="platform-row">
              <h4>Zoom</h4>
              <span className={`status-pill ${zoomConnected ? 'connected' : 'disconnected'}`}>
                {zoomConnected ? 'Подключён' : 'Не подключён'}
              </span>
            </div>
            
            {zoomConnected && zoomEmail && (
              <p className="platform-email">{zoomEmail}</p>
            )}
            
            <p className="platform-desc">
              {zoomConnected 
                ? 'Zoom готов к проведению уроков. Запись и расшифровка активности работают автоматически.'
                : 'Подключите ваш Zoom аккаунт для проведения видеоуроков с записью и аналитикой.'
              }
            </p>
            
            <div className="platform-actions">
              {zoomConnected ? (
                <button
                  type="button"
                  className="btn-action disconnect"
                  onClick={handleDisconnectZoom}
                  disabled={loading === 'zoom'}
                >
                  {loading === 'zoom' ? 'Отключение...' : 'Отключить'}
                </button>
              ) : (
                <button
                  type="button"
                  className="btn-action connect zoom"
                  onClick={handleConnectZoom}
                  disabled={loading === 'zoom'}
                >
                  {loading === 'zoom' ? 'Подключение...' : 'Подключить Zoom'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Google Meet */}
        <div className={`platform-card ${googleMeetConnected ? 'is-connected' : ''}`}>
          <div className="platform-icon meet-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="28" height="28">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </div>
          
          <div className="platform-content">
            <div className="platform-row">
              <h4>Google Meet</h4>
              <span className={`status-pill ${googleMeetConnected ? 'connected' : 'disconnected'}`}>
                {googleMeetConnected ? 'Подключён' : 'Не подключён'}
              </span>
            </div>
            
            {googleMeetConnected && googleMeetEmail && (
              <p className="platform-email">{googleMeetEmail}</p>
            )}
            
            <p className="platform-desc">
              {googleMeetConnected 
                ? 'Google Meet готов к проведению уроков. Посещаемость фиксируется автоматически.'
                : 'Подключите Google аккаунт для проведения уроков через Google Meet.'
              }
            </p>
            
            <div className="platform-actions">
              {googleMeetConnected ? (
                <button
                  type="button"
                  className="btn-action disconnect"
                  onClick={handleDisconnectGoogleMeet}
                  disabled={loading === 'google_meet'}
                >
                  {loading === 'google_meet' ? 'Отключение...' : 'Отключить'}
                </button>
              ) : (
                <button
                  type="button"
                  className="btn-action connect google"
                  onClick={handleConnectGoogleMeet}
                  disabled={loading === 'google_meet'}
                >
                  {loading === 'google_meet' ? 'Подключение...' : 'Подключить Google Meet'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Простая инструкция */}
      <div className="platforms-info">
        <h4>Как подключить?</h4>
        <ol>
          <li>Нажмите <strong>«Подключить»</strong> для нужной платформы</li>
          <li>Войдите в свой аккаунт Zoom или Google</li>
          <li>Разрешите доступ приложению</li>
          <li>Готово! Выбирайте платформу при запуске урока</li>
        </ol>
        
        <div className="platforms-note">
          <strong>Важно:</strong> Для Google Meet ученикам нужен Google аккаунт. 
          Zoom работает без регистрации для учеников.
        </div>
      </div>
    </section>
  );
};

export default PlatformsSection;
