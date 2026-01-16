import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../apiService';
import PlatformInstructionModal from './PlatformInstructionModal';
import './PlatformsSection.css';

/**
 * Секция "Платформы для проведения уроков" в профиле учителя.
 * Каждый учитель подключает свой личный Zoom и/или Google Meet аккаунт.
 */
const PlatformsSection = ({ user, onRefresh }) => {
  const [loading, setLoading] = useState(null); // 'zoom' | 'google_meet' | null
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [platformsStatus, setPlatformsStatus] = useState(null);
  const [instructionModal, setInstructionModal] = useState(null); // 'zoom' | 'google_meet' | null

  // Статусы из user (приходят с бэкенда через сериализатор)
  const zoomConnected = user?.zoom_connected || false;
  const googleMeetConnected = user?.google_meet_connected || false;
  const googleMeetEmail = user?.google_meet_email || '';
  const zoomEmail = user?.zoom_email || '';

  // Загрузка статуса доступности платформ
  const fetchPlatformsStatus = useCallback(async () => {
    try {
      const response = await apiClient.get('/integrations/platforms/');
      setPlatformsStatus(response.data?.platforms || null);
    } catch (err) {
      console.error('Failed to fetch platforms status:', err);
      // При ошибке показываем все платформы
      setPlatformsStatus(null);
    }
  }, []);

  useEffect(() => {
    fetchPlatformsStatus();
  }, [fetchPlatformsStatus]);

  // Показать модальное окно с инструкцией
  const handleShowInstruction = (platform) => {
    setInstructionModal(platform);
    setError('');
    setSuccess('');
  };

  // Подключение Zoom с credentials (вызывается из модалки)
  const handleConnectZoom = async (credentials = null) => {
    setLoading('zoom');
    setError('');
    setSuccess('');
    try {
      // Если переданы credentials - сохраняем их
      if (credentials && credentials.accountId && credentials.clientId && credentials.clientSecret) {
        const response = await apiClient.post('/integrations/zoom/save-credentials/', {
          account_id: credentials.accountId,
          client_id: credentials.clientId,
          client_secret: credentials.clientSecret
        });
        if (response.data?.success) {
          setSuccess('Zoom подключён');
          setInstructionModal(null);
          if (onRefresh) onRefresh();
          setTimeout(() => setSuccess(''), 3000);
          return;
        } else {
          setError(response.data?.detail || 'Не удалось сохранить данные');
          setInstructionModal(null);
          return;
        }
      }
      
      // Старый путь OAuth (если нет credentials)
      const response = await apiClient.get('/integrations/zoom/auth-url/');
      if (response.data?.auth_url) {
        window.location.href = response.data.auth_url;
      } else {
        setError('Не удалось получить ссылку авторизации');
        setInstructionModal(null);
      }
    } catch (err) {
      console.error('Zoom auth error:', err);
      if (err.response?.status === 501) {
        setError('Zoom OAuth пока не настроен. Обратитесь к администратору.');
      } else {
        setError(err.response?.data?.detail || 'Ошибка подключения Zoom');
      }
      setInstructionModal(null);
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

  // OAuth авторизация Google Meet с credentials (вызывается из модалки)
  const handleConnectGoogleMeet = async (credentials = null) => {
    setLoading('google_meet');
    setError('');
    setSuccess('');
    try {
      // Если переданы credentials - сначала сохраняем их, затем начинаем OAuth
      if (credentials && credentials.clientId && credentials.clientSecret) {
        const response = await apiClient.post('/integrations/google-meet/save-credentials/', {
          client_id: credentials.clientId,
          client_secret: credentials.clientSecret
        });
        if (response.data?.auth_url) {
          window.location.href = response.data.auth_url;
          return;
        } else {
          setError('Не удалось получить ссылку авторизации');
          setInstructionModal(null);
          return;
        }
      }
      
      // Старый путь - без credentials (если уже сохранены)
      const response = await apiClient.get('/integrations/google-meet/auth-url/');
      if (response.data?.auth_url) {
        window.location.href = response.data.auth_url;
      } else {
        setError('Не удалось получить ссылку авторизации');
        setInstructionModal(null);
      }
    } catch (err) {
      console.error('Google Meet auth error:', err);
      if (err.response?.status === 501) {
        setError('Google Meet пока не настроен. Обратитесь к администратору.');
      } else {
        setError(err.response?.data?.detail || 'Ошибка подключения Google Meet');
      }
      setInstructionModal(null);
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
        <p className="platforms-subtitle">Подключите аккаунты для проведения онлайн-уроков</p>
      </div>

      {error && <div className="platforms-message error">{error}</div>}
      {success && <div className="platforms-message success">{success}</div>}

      <div className="platforms-list">
        {/* Zoom */}
        <div className={`platform-row ${zoomConnected ? 'connected' : ''}`}>
          <div className="platform-icon zoom">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M4.585 11.828V16a2 2 0 002 2h7.829a2 2 0 002-2v-4.172a2 2 0 00-2-2H6.585a2 2 0 00-2 2zm13.243 4.415l2.829 2.122a.75.75 0 001.193-.607V10.071a.75.75 0 00-1.193-.607l-2.829 2.122v4.657z"/>
            </svg>
          </div>
          <div className="platform-info">
            <p className="platform-name">Zoom</p>
            <p className={`platform-status ${zoomConnected ? 'is-connected' : ''}`}>
              {zoomConnected ? (zoomEmail || 'Подключён') : 'Не подключён'}
            </p>
          </div>
          <div className="platform-action">
            {zoomConnected ? (
              <button
                type="button"
                className="btn-platform disconnect"
                onClick={handleDisconnectZoom}
                disabled={loading === 'zoom'}
              >
                {loading === 'zoom' ? '...' : 'Отключить'}
              </button>
            ) : (
              <button
                type="button"
                className="btn-platform connect zoom"
                onClick={() => handleShowInstruction('zoom')}
                disabled={loading === 'zoom'}
              >
                {loading === 'zoom' ? '...' : 'Подключить'}
              </button>
            )}
          </div>
        </div>

        {/* Google Meet */}
        <div className={`platform-row ${googleMeetConnected ? 'connected' : ''}`}>
          <div className="platform-icon google">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </div>
          <div className="platform-info">
            <p className="platform-name">Google Meet</p>
            <p className={`platform-status ${googleMeetConnected ? 'is-connected' : ''}`}>
              {googleMeetConnected 
                ? (googleMeetEmail || 'Подключён') 
                : 'Не подключён'}
            </p>
          </div>
          <div className="platform-action">
            {googleMeetConnected ? (
              <button
                type="button"
                className="btn-platform disconnect"
                onClick={handleDisconnectGoogleMeet}
                disabled={loading === 'google_meet'}
              >
                {loading === 'google_meet' ? '...' : 'Отключить'}
              </button>
            ) : (
              <button
                type="button"
                className="btn-platform connect google"
                onClick={() => handleShowInstruction('google_meet')}
                disabled={loading === 'google_meet'}
              >
                {loading === 'google_meet' ? '...' : 'Подключить'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Справка */}
      <div className="platforms-help">
        <p className="platforms-help-title">Как это работает?</p>
        <ol>
          <li>Нажмите «Подключить» → просмотрите инструкцию → подключите аккаунт</li>
          <li>При запуске урока выберите платформу</li>
        </ol>
        <div className="platforms-note">
          <strong>Совет:</strong> Zoom работает без регистрации для учеников. Для Google Meet ученикам нужен Google аккаунт.
        </div>
      </div>

      {/* Модальное окно с инструкцией */}
      <PlatformInstructionModal
        platform={instructionModal}
        isOpen={!!instructionModal}
        onClose={() => setInstructionModal(null)}
        onConnect={instructionModal === 'zoom' ? handleConnectZoom : handleConnectGoogleMeet}
        isConnecting={loading === instructionModal}
      />
    </section>
  );
};

export default PlatformsSection;
