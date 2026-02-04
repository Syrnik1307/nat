import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useAuth } from '../auth';
import { getAccessToken } from '../apiService';
import './SupportWidget.css';

const SUGGEST_IMPROVEMENTS_TG_USER_ID = process.env.REACT_APP_SUGGEST_IMPROVEMENTS_TG_USER_ID || '';
const SUPPORT_BOT_FALLBACK_URL = 'https://t.me/help_lectio_space_bot';

// Категории проблем
const CATEGORIES = [
  { value: 'login', label: 'Вход/Регистрация' },
  { value: 'payment', label: 'Оплата/Подписка' },
  { value: 'lesson', label: 'Уроки/Расписание' },
  { value: 'zoom', label: 'Zoom/Видеосвязь' },
  { value: 'homework', label: 'Домашние задания' },
  { value: 'recording', label: 'Записи уроков' },
  { value: 'other', label: 'Другое' },
];

// Сбор контекста браузера
const collectBrowserContext = () => {
  const ua = navigator.userAgent;
  let browserInfo = 'Unknown';
  
  if (ua.includes('Firefox')) browserInfo = 'Firefox';
  else if (ua.includes('Edg')) browserInfo = 'Edge';
  else if (ua.includes('Chrome')) browserInfo = 'Chrome';
  else if (ua.includes('Safari')) browserInfo = 'Safari';
  
  return {
    user_agent: ua,
    browser_info: browserInfo,
    screen_resolution: `${window.screen.width}x${window.screen.height}`,
    page_url: window.location.href,
    build_version: process.env.REACT_APP_BUILD_VERSION || 'dev',
  };
};

const SupportWidget = () => {
  const { accessTokenValid } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [view, setView] = useState('menu'); // menu | form | telegram | success
  const [telegramAction, setTelegramAction] = useState('support'); // support | improvements
  const [loading, setLoading] = useState(false);
  const [errorText, setErrorText] = useState('');
  const [supportUrl, setSupportUrl] = useState('');
  const [systemStatus, setSystemStatus] = useState(null);
  
  // Форма тикета
  const [formData, setFormData] = useState({
    category: 'other',
    subject: '',
    description: '',
    error_message: '',
    steps_to_reproduce: '',
  });

  // Загрузка статуса системы
  useEffect(() => {
    const loadStatus = async () => {
      try {
        const resp = await fetch('/api/support/status/');
        if (resp.ok) {
          const data = await resp.json();
          setSystemStatus(data);
        }
      } catch (e) {
        // Игнорируем ошибки
      }
    };
    if (isOpen) loadStatus();
  }, [isOpen]);

  const loadSupportLink = useCallback(async () => {
    if (!accessTokenValid) return;
    setLoading(true);
    try {
      const token = getAccessToken();
      const response = await fetch('/api/support/telegram-link/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSupportUrl(data.url || '');
      }
    } catch (err) {
      // Ignore
    } finally {
      setLoading(false);
    }
  }, [accessTokenValid]);

  const openTelegram = async () => {
    if (!supportUrl) await loadSupportLink();
    if (supportUrl) {
      window.open(supportUrl, '_blank', 'noopener,noreferrer');
    }
  };

  const openSuggestImprovements = async () => {
    if (SUGGEST_IMPROVEMENTS_TG_USER_ID) {
      const deepLink = `tg://user?id=${SUGGEST_IMPROVEMENTS_TG_USER_ID}`;
      // Для кастомных схем надёжнее использовать location
      window.location.href = deepLink;
      return;
    }

    // Заглушка до получения ID: используем существующий чат поддержки
    if (supportUrl) {
      window.open(supportUrl, '_blank', 'noopener,noreferrer');
      return;
    }

    await loadSupportLink();
    const url = supportUrl || SUPPORT_BOT_FALLBACK_URL;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const submitTicket = async (e) => {
    e.preventDefault();
    if (!formData.subject.trim() || !formData.description.trim()) {
      setErrorText('Заполните тему и описание');
      return;
    }

    setLoading(true);
    setErrorText('');

    try {
      const token = getAccessToken();
      const context = collectBrowserContext();
      
      const payload = {
        ...formData,
        ...context,
      };

      const response = await fetch('/api/support/tickets/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'Не удалось отправить обращение');
      }

      setView('success');
      setFormData({
        category: 'other',
        subject: '',
        description: '',
        error_message: '',
        steps_to_reproduce: '',
      });
    } catch (err) {
      setErrorText(err.message);
    } finally {
      setLoading(false);
    }
  };

  const onToggle = async () => {
    const next = !isOpen;
    setIsOpen(next);
    if (next) {
      setView('menu');
      setErrorText('');
      if (accessTokenValid && !supportUrl) {
        loadSupportLink();
      }
    }
  };

  const renderIncidentBanner = () => {
    if (!systemStatus || systemStatus.status === 'operational') return null;
    
    const statusColors = {
      degraded: '#ffc107',
      major_outage: '#dc3545',
      maintenance: '#17a2b8',
    };
    
    return (
      <div 
        className="support-incident-banner"
        style={{ backgroundColor: statusColors[systemStatus.status] || '#6c757d' }}
      >
        <strong>{systemStatus.incident_title || systemStatus.status_display}</strong>
        {systemStatus.message && <p>{systemStatus.message}</p>}
      </div>
    );
  };

  const renderMenu = () => (
    <div className="support-menu">
      {renderIncidentBanner()}
      
      <button 
        className="support-menu-item"
        onClick={() => {
          setTelegramAction('improvements');
          setView('telegram');
          openSuggestImprovements();
        }}
      >
        <span className="support-menu-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14,2 14,8 20,8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10,9 9,9 8,9"/>
          </svg>
        </span>
        <span>
          <strong>Предложить улучшение</strong>
          <small>Сообщить идею команде разработки</small>
        </span>
      </button>

      <button 
        className="support-menu-item"
        onClick={() => {
          setTelegramAction('support');
          setView('telegram');
          openTelegram();
        }}
        disabled={!accessTokenValid}
      >
        <span className="support-menu-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18 1.897-.962 6.502-1.359 8.627-.168.9-.5 1.201-.82 1.23-.697.064-1.226-.461-1.901-.903-1.056-.692-1.653-1.123-2.678-1.799-1.185-.781-.417-1.21.258-1.911.177-.184 3.247-2.977 3.307-3.23.007-.032.015-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.139-5.062 3.345-.479.329-.913.489-1.302.481-.428-.009-1.252-.242-1.865-.442-.751-.244-1.349-.374-1.297-.789.027-.216.324-.437.893-.663 3.498-1.524 5.831-2.529 6.998-3.015 3.333-1.386 4.025-1.627 4.477-1.635.099-.002.321.023.465.141.121.1.154.234.17.331.015.098.035.321.02.496z"/>
          </svg>
        </span>
        <span>
          <strong>Чат в Telegram</strong>
          <small>Быстрый чат с поддержкой</small>
        </span>
      </button>

      {!accessTokenValid && (
        <p className="support-login-hint">
          Войдите в аккаунт для доступа к поддержке
        </p>
      )}
    </div>
  );

  const renderForm = () => (
    <form className="support-form" onSubmit={submitTicket}>
      <button 
        type="button" 
        className="support-back-btn"
        onClick={() => setView('menu')}
      >
        ← Назад
      </button>

      <div className="support-form-group">
        <label>Категория</label>
        <select
          value={formData.category}
          onChange={(e) => handleInputChange('category', e.target.value)}
        >
          {CATEGORIES.map(cat => (
            <option key={cat.value} value={cat.value}>{cat.label}</option>
          ))}
        </select>
      </div>

      <div className="support-form-group">
        <label>Тема <span className="required">*</span></label>
        <input
          type="text"
          value={formData.subject}
          onChange={(e) => handleInputChange('subject', e.target.value)}
          placeholder="Кратко опишите идею"
          maxLength={200}
          required
        />
      </div>

      <div className="support-form-group">
        <label>Описание <span className="required">*</span></label>
        <textarea
          value={formData.description}
          onChange={(e) => handleInputChange('description', e.target.value)}
          placeholder="Подробно опишите идею или пожелание..."
          rows={4}
          required
        />
      </div>

      <div className="support-form-group">
        <label>Сообщение об ошибке (если есть)</label>
        <input
          type="text"
          value={formData.error_message}
          onChange={(e) => handleInputChange('error_message', e.target.value)}
          placeholder="Скопируйте текст ошибки"
        />
      </div>

      <div className="support-form-group">
        <label>Шаги воспроизведения</label>
        <textarea
          value={formData.steps_to_reproduce}
          onChange={(e) => handleInputChange('steps_to_reproduce', e.target.value)}
          placeholder="1. Открыл страницу...&#10;2. Нажал на кнопку...&#10;3. Появилась ошибка..."
          rows={3}
        />
      </div>

      {errorText && (
        <div className="support-error">{errorText}</div>
      )}

      <button 
        type="submit" 
        className="support-submit-btn"
        disabled={loading}
      >
        {loading ? 'Отправка...' : 'Отправить предложение'}
      </button>

      <p className="support-context-note">
        Технический контекст (браузер, страница) будет добавлен автоматически
      </p>
    </form>
  );

  const renderSuccess = () => (
    <div className="support-success">
      <div className="support-success-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#28a745" strokeWidth="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22,4 12,14.01 9,11.01"/>
        </svg>
      </div>
      <h4>Предложение отправлено</h4>
      <p>Спасибо! Мы рассмотрим ваше предложение. Уведомление придёт в Telegram.</p>
      <button 
        className="support-done-btn"
        onClick={() => {
          setView('menu');
          setIsOpen(false);
        }}
      >
        Готово
      </button>
    </div>
  );

  const renderTelegram = () => (
    <div className="support-telegram">
      <p>Telegram должен был открыться в новом окне.</p>
      <button 
        className="support-telegram-retry"
        onClick={telegramAction === 'improvements' ? openSuggestImprovements : openTelegram}
        disabled={loading}
      >
        Открыть снова
      </button>
      <button 
        className="support-back-btn"
        onClick={() => setView('menu')}
      >
        ← Назад
      </button>
    </div>
  );

  const ui = (
    <>
      <button
        className={`support-fab ${isOpen ? 'support-fab-open' : ''}`}
        onClick={onToggle}
        title="Поддержка"
        aria-label={isOpen ? 'Закрыть поддержку' : 'Открыть поддержку'}
      >
        {isOpen ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        )}
      </button>

      {isOpen && (
        <div className="support-widget">
          <div className="support-widget-header">
            <h3>Поддержка</h3>
            <button
              className="support-widget-close"
              onClick={() => setIsOpen(false)}
              aria-label="Закрыть"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          <div className="support-widget-body">
            {view === 'menu' && renderMenu()}
            {view === 'form' && renderForm()}
            {view === 'success' && renderSuccess()}
            {view === 'telegram' && renderTelegram()}
          </div>
        </div>
      )}
    </>
  );

  // Рендерим через портал, чтобы fixed-позиционирование не ломалось из-за transform/overflow у контейнеров страниц
  if (typeof document === 'undefined') return null;
  return createPortal(ui, document.body);
};

export default SupportWidget;
