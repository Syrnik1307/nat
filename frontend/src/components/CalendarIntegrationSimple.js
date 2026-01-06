import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getCalendarSubscribeLinks } from '../apiService';
import { useAuth } from '../auth';
import './CalendarIntegrationSimple.css';

/* =====================================================
   CALENDAR INTEGRATION - SIMPLE VERSION
   Максимально простой UI "для бабушки"
   Один клик - готово!
   ===================================================== */

// Иконка стрелки назад
const IconArrowLeft = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M19 12H5M12 19l-7-7 7-7"/>
  </svg>
);

// Иконка галочки
const IconCheck = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
    <polyline points="20,6 9,17 4,12"/>
  </svg>
);

// Большие красивые логотипы календарей
const GoogleLogo = () => (
  <svg width="56" height="56" viewBox="0 0 56 56">
    <rect x="4" y="10" width="48" height="42" rx="6" fill="#4285F4"/>
    <rect x="10" y="20" width="36" height="28" fill="white"/>
    <rect x="14" y="24" width="10" height="8" fill="#EA4335"/>
    <rect x="24" y="24" width="10" height="8" fill="#FBBC05"/>
    <rect x="34" y="24" width="10" height="8" fill="#34A853"/>
    <rect x="14" y="32" width="10" height="8" fill="#4285F4"/>
    <rect x="24" y="32" width="10" height="8" fill="#EA4335"/>
    <rect x="34" y="32" width="10" height="8" fill="#FBBC05"/>
    <rect x="18" y="4" width="6" height="12" rx="2" fill="#4285F4"/>
    <rect x="34" y="4" width="6" height="12" rx="2" fill="#4285F4"/>
  </svg>
);

const AppleLogo = () => (
  <svg width="56" height="56" viewBox="0 0 56 56">
    <rect x="4" y="10" width="48" height="42" rx="6" fill="#FF3B30"/>
    <rect x="10" y="20" width="36" height="28" fill="white"/>
    <text x="28" y="42" textAnchor="middle" fontSize="22" fontWeight="bold" fill="#FF3B30">31</text>
    <rect x="18" y="4" width="6" height="12" rx="2" fill="#FF3B30"/>
    <rect x="34" y="4" width="6" height="12" rx="2" fill="#FF3B30"/>
  </svg>
);

const YandexLogo = () => (
  <svg width="56" height="56" viewBox="0 0 56 56">
    <rect x="4" y="10" width="48" height="42" rx="6" fill="#FC3F1D"/>
    <rect x="10" y="20" width="36" height="28" fill="white"/>
    <text x="28" y="42" textAnchor="middle" fontSize="18" fontWeight="bold" fill="#FC3F1D">Я</text>
    <rect x="18" y="4" width="6" height="12" rx="2" fill="#FC3F1D"/>
    <rect x="34" y="4" width="6" height="12" rx="2" fill="#FC3F1D"/>
  </svg>
);

const OutlookLogo = () => (
  <svg width="56" height="56" viewBox="0 0 56 56">
    <rect x="4" y="10" width="48" height="42" rx="6" fill="#0078D4"/>
    <rect x="10" y="20" width="36" height="28" fill="white"/>
    <text x="28" y="42" textAnchor="middle" fontSize="18" fontWeight="bold" fill="#0078D4">O</text>
    <rect x="18" y="4" width="6" height="12" rx="2" fill="#0078D4"/>
    <rect x="34" y="4" width="6" height="12" rx="2" fill="#0078D4"/>
  </svg>
);

const CalendarIntegrationSimple = () => {
  const { role } = useAuth();
  const [links, setLinks] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connectedCalendar, setConnectedCalendar] = useState(null); // Какой календарь подключён
  const [showSuccess, setShowSuccess] = useState(false);

  const backLink = role === 'student' ? '/student' : '/calendar';

  useEffect(() => {
    loadLinks();
    // Проверяем, был ли уже подключён календарь
    const saved = localStorage.getItem('lectio_connected_calendar');
    if (saved) setConnectedCalendar(saved);
  }, []);

  const loadLinks = async () => {
    setLoading(true);
    try {
      const response = await getCalendarSubscribeLinks();
      setLinks(response.data);
    } catch (err) {
      console.error('Failed to load calendar links:', err);
      setError('Не удалось загрузить. Попробуйте обновить страницу.');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = (provider, url) => {
    // Сохраняем что подключили
    localStorage.setItem('lectio_connected_calendar', provider);
    setConnectedCalendar(provider);
    setShowSuccess(true);
    
    // Открываем URL
    if (provider === 'google') {
      window.open(url, '_blank');
    } else {
      window.location.href = url;
    }
    
    // Скрываем success через 5 секунд
    setTimeout(() => setShowSuccess(false), 5000);
  };

  const handleDisconnect = () => {
    localStorage.removeItem('lectio_connected_calendar');
    setConnectedCalendar(null);
  };

  if (loading) {
    return (
      <div className="cal-simple-page">
        <div className="cal-simple-loading">
          <div className="cal-simple-spinner"></div>
          <p>Загрузка...</p>
        </div>
      </div>
    );
  }

  const feedUrl = links?.feed_url || '';
  const googleUrl = `https://calendar.google.com/calendar/r?cid=${encodeURIComponent(feedUrl)}`;
  const webcalUrl = feedUrl.replace('https://', 'webcal://').replace('http://', 'webcal://');

  return (
    <div className="cal-simple-page">
      <div className="cal-simple-container">
        
        {/* Шапка */}
        <header className="cal-simple-header">
          <Link to={backLink} className="cal-simple-back">
            <IconArrowLeft />
          </Link>
          <div className="cal-simple-header-content">
            <h1>📅 Мои занятия в календаре</h1>
            <p>Все уроки будут в вашем телефоне</p>
          </div>
        </header>

        {error && (
          <div className="cal-simple-error">
            <p>😕 {error}</p>
            <button onClick={loadLinks}>Попробовать снова</button>
          </div>
        )}

        {/* Успешное подключение */}
        {showSuccess && (
          <div className="cal-simple-success">
            <div className="cal-simple-success-icon">
              <IconCheck />
            </div>
            <div className="cal-simple-success-text">
              <strong>Отлично! 🎉</strong>
              <p>Подтвердите добавление в открывшемся окне</p>
            </div>
          </div>
        )}

        {/* Главный блок - выбор календаря */}
        <div className="cal-simple-main">
          <h2>Выберите ваш календарь:</h2>
          <p className="cal-simple-hint">Нажмите на тот, которым пользуетесь</p>
          
          <div className="cal-simple-grid">
            
            {/* Google */}
            <button 
              className={`cal-simple-card ${connectedCalendar === 'google' ? 'connected' : ''}`}
              onClick={() => handleConnect('google', googleUrl)}
            >
              <div className="cal-simple-card-logo">
                <GoogleLogo />
              </div>
              <div className="cal-simple-card-name">Google</div>
              <div className="cal-simple-card-desc">Android, Gmail</div>
              {connectedCalendar === 'google' && (
                <div className="cal-simple-card-badge">✓ Подключён</div>
              )}
            </button>

            {/* Apple */}
            <button 
              className={`cal-simple-card ${connectedCalendar === 'apple' ? 'connected' : ''}`}
              onClick={() => handleConnect('apple', webcalUrl)}
            >
              <div className="cal-simple-card-logo">
                <AppleLogo />
              </div>
              <div className="cal-simple-card-name">Apple</div>
              <div className="cal-simple-card-desc">iPhone, iPad, Mac</div>
              {connectedCalendar === 'apple' && (
                <div className="cal-simple-card-badge">✓ Подключён</div>
              )}
            </button>

            {/* Яндекс */}
            <button 
              className={`cal-simple-card ${connectedCalendar === 'yandex' ? 'connected' : ''}`}
              onClick={() => handleConnect('yandex', webcalUrl)}
            >
              <div className="cal-simple-card-logo">
                <YandexLogo />
              </div>
              <div className="cal-simple-card-name">Яндекс</div>
              <div className="cal-simple-card-desc">Яндекс Почта</div>
              {connectedCalendar === 'yandex' && (
                <div className="cal-simple-card-badge">✓ Подключён</div>
              )}
            </button>

            {/* Outlook */}
            <button 
              className={`cal-simple-card ${connectedCalendar === 'outlook' ? 'connected' : ''}`}
              onClick={() => handleConnect('outlook', webcalUrl)}
            >
              <div className="cal-simple-card-logo">
                <OutlookLogo />
              </div>
              <div className="cal-simple-card-name">Outlook</div>
              <div className="cal-simple-card-desc">Microsoft, работа</div>
              {connectedCalendar === 'outlook' && (
                <div className="cal-simple-card-badge">✓ Подключён</div>
              )}
            </button>

          </div>
        </div>

        {/* Что произойдёт */}
        <div className="cal-simple-info">
          <h3>Что получите:</h3>
          <ul>
            <li>📱 <strong>Все занятия в телефоне</strong> — не нужно заходить на сайт</li>
            <li>🔔 <strong>Напоминания</strong> — телефон напомнит о занятии</li>
            <li>🔄 <strong>Автообновление</strong> — новые занятия появятся сами</li>
            <li>🔗 <strong>Zoom ссылки</strong> — присоединяйтесь в один клик</li>
          </ul>
        </div>

        {/* Уже подключено */}
        {connectedCalendar && (
          <div className="cal-simple-connected-info">
            <p>
              ✅ Вы подключили <strong>{
                connectedCalendar === 'google' ? 'Google Calendar' :
                connectedCalendar === 'apple' ? 'Apple Calendar' :
                connectedCalendar === 'yandex' ? 'Яндекс Календарь' :
                'Outlook'
              }</strong>
            </p>
            <button className="cal-simple-disconnect" onClick={handleDisconnect}>
              Подключить другой
            </button>
          </div>
        )}

        {/* FAQ */}
        <details className="cal-simple-faq">
          <summary>❓ Не работает?</summary>
          <div className="cal-simple-faq-content">
            <p><strong>Если ничего не происходит:</strong></p>
            <ol>
              <li>Проверьте, что вы залогинены в календаре</li>
              <li>Попробуйте другой браузер</li>
              <li>На iPhone: откройте через Safari</li>
            </ol>
            <p><strong>Если занятия не появились:</strong></p>
            <p>Подождите 5-10 минут, календари обновляются не сразу.</p>
          </div>
        </details>

      </div>
    </div>
  );
};

export default CalendarIntegrationSimple;
