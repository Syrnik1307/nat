import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getCalendarSubscribeLinks } from '../apiService';
import { useAuth } from '../auth';
import { Button } from '../shared/components';
import './CalendarIntegrationSimple.css';

/**
 * Страница интеграции с календарём
 * Минималистичный дизайн в стиле платформы
 */

const IconArrowLeft = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M19 12H5M12 19l-7-7 7-7"/>
  </svg>
);

const IconCheck = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <polyline points="20,6 9,17 4,12"/>
  </svg>
);

const IconCalendar = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
    <line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/>
    <line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
);

// Провайдеры календарей
const PROVIDERS = [
  {
    id: 'google',
    name: 'Google Calendar',
    subtitle: 'Android, Gmail',
    color: '#4285F4',
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22 5.5H2v13a2 2 0 002 2h16a2 2 0 002-2v-13z"/>
        <path fill="#fff" d="M4 8h16v10H4z"/>
        <path fill="#EA4335" d="M6 10h4v3H6z"/>
        <path fill="#FBBC05" d="M10 10h4v3h-4z"/>
        <path fill="#34A853" d="M14 10h4v3h-4z"/>
        <path fill="#4285F4" d="M6 13h4v3H6z"/>
        <path fill="#EA4335" d="M10 13h4v3h-4z"/>
        <rect fill="#4285F4" x="7" y="2" width="2" height="5" rx="1"/>
        <rect fill="#4285F4" x="15" y="2" width="2" height="5" rx="1"/>
      </svg>
    ),
  },
  {
    id: 'apple',
    name: 'Apple Calendar',
    subtitle: 'iPhone, iPad, Mac',
    color: '#FF3B30',
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24">
        <rect x="2" y="5" width="20" height="17" rx="2" fill="#FF3B30"/>
        <rect x="4" y="9" width="16" height="11" fill="#fff"/>
        <text x="12" y="17" textAnchor="middle" fontSize="9" fontWeight="bold" fill="#FF3B30">31</text>
        <rect x="7" y="2" width="2" height="5" rx="1" fill="#FF3B30"/>
        <rect x="15" y="2" width="2" height="5" rx="1" fill="#FF3B30"/>
      </svg>
    ),
  },
  {
    id: 'yandex',
    name: 'Яндекс Календарь',
    subtitle: 'Яндекс почта',
    color: '#FC3F1D',
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24">
        <rect x="2" y="5" width="20" height="17" rx="2" fill="#FC3F1D"/>
        <rect x="4" y="9" width="16" height="11" fill="#fff"/>
        <text x="12" y="17" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#FC3F1D">Я</text>
        <rect x="7" y="2" width="2" height="5" rx="1" fill="#FC3F1D"/>
        <rect x="15" y="2" width="2" height="5" rx="1" fill="#FC3F1D"/>
      </svg>
    ),
  },
  {
    id: 'outlook',
    name: 'Outlook',
    subtitle: 'Microsoft 365',
    color: '#0078D4',
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24">
        <rect x="2" y="5" width="20" height="17" rx="2" fill="#0078D4"/>
        <rect x="4" y="9" width="16" height="11" fill="#fff"/>
        <text x="12" y="17" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#0078D4">O</text>
        <rect x="7" y="2" width="2" height="5" rx="1" fill="#0078D4"/>
        <rect x="15" y="2" width="2" height="5" rx="1" fill="#0078D4"/>
      </svg>
    ),
  },
];

const CalendarIntegrationSimple = () => {
  const { role } = useAuth();
  const [links, setLinks] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connectedCalendar, setConnectedCalendar] = useState(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const backLink = role === 'student' ? '/student' : '/calendar';

  useEffect(() => {
    loadLinks();
    const saved = localStorage.getItem('lectio_connected_calendar');
    if (saved) setConnectedCalendar(saved);
  }, []);

  const loadLinks = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCalendarSubscribeLinks();
      setLinks(response.data);
    } catch (err) {
      console.error('Failed to load calendar links:', err);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = (providerId) => {
    if (!links?.feed_url) return;
    
    const feedUrl = links.feed_url;
    let targetUrl = '';

    if (providerId === 'google') {
      targetUrl = `https://calendar.google.com/calendar/r?cid=${encodeURIComponent(feedUrl)}`;
      window.open(targetUrl, '_blank');
    } else {
      // webcal:// для Apple, Yandex, Outlook
      targetUrl = feedUrl.replace('https://', 'webcal://').replace('http://', 'webcal://');
      window.location.href = targetUrl;
    }

    localStorage.setItem('lectio_connected_calendar', providerId);
    setConnectedCalendar(providerId);
    setShowSuccess(true);
    setTimeout(() => setShowSuccess(false), 5000);
  };

  const handleDisconnect = () => {
    localStorage.removeItem('lectio_connected_calendar');
    setConnectedCalendar(null);
  };

  if (loading) {
    return (
      <div className="cal-page">
        <div className="cal-container">
          <div className="cal-loading">
            <div className="cal-spinner" />
            <p>Загрузка...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="cal-page">
      <div className="cal-container">
        {/* Шапка */}
        <header className="cal-header">
          <Link to={backLink} className="cal-back">
            <IconArrowLeft />
          </Link>
          <div className="cal-header-text">
            <h1>Добавить в свой календарь</h1>
            <p>Все занятия будут автоматически синхронизироваться</p>
          </div>
        </header>

        {/* Ошибка */}
        {error && (
          <div className="cal-error">
            <p>{error}</p>
            <Button variant="secondary" size="small" onClick={loadLinks}>
              Попробовать снова
            </Button>
          </div>
        )}

        {/* Успех */}
        {showSuccess && (
          <div className="cal-success">
            <span className="cal-success-icon"><IconCheck /></span>
            <div>
              <strong>Готово</strong>
              <p>Подтвердите добавление в открывшемся окне</p>
            </div>
          </div>
        )}

        {/* Выбор провайдера */}
        {!error && (
          <div className="cal-main">
            <div className="cal-section-header">
              <IconCalendar />
              <span>Выберите ваш календарь</span>
            </div>

            <div className="cal-grid">
              {PROVIDERS.map((provider) => {
                const isConnected = connectedCalendar === provider.id;
                return (
                  <button
                    key={provider.id}
                    className={`cal-card ${isConnected ? 'cal-card--connected' : ''}`}
                    onClick={() => isConnected ? handleDisconnect() : handleConnect(provider.id)}
                    disabled={!links?.feed_url}
                  >
                    <div className="cal-card-icon">{provider.icon}</div>
                    <div className="cal-card-info">
                      <span className="cal-card-name">{provider.name}</span>
                      <span className="cal-card-subtitle">{provider.subtitle}</span>
                    </div>
                    {isConnected && (
                      <span className="cal-card-badge">Подключено</span>
                    )}
                  </button>
                );
              })}
            </div>

            <p className="cal-hint">
              После нажатия откроется ваш календарь. Подтвердите подписку — и все занятия появятся автоматически.
            </p>
          </div>
        )}

        {/* Дополнительная информация */}
        <div className="cal-info">
          <h3>Как это работает</h3>
          <ul>
            <li>Занятия синхронизируются автоматически каждые 15-30 минут</li>
            <li>Новые уроки появятся в календаре без дополнительных действий</li>
            <li>Изменения в расписании также обновятся автоматически</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default CalendarIntegrationSimple;
