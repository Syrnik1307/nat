import React, { useState, useEffect } from 'react';
import './StatusPage.css';

const StatusPage = () => {
  const [status, setStatus] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadStatus = async () => {
      try {
        const [statusResp, healthResp] = await Promise.all([
          fetch('/api/support/status/'),
          fetch('/api/support/health/')
        ]);

        if (statusResp.ok) {
          setStatus(await statusResp.json());
        }
        if (healthResp.ok) {
          setHealth(await healthResp.json());
        }
      } catch (err) {
        setError('Не удалось загрузить статус');
      } finally {
        setLoading(false);
      }
    };

    loadStatus();
    // Автообновление каждые 30 секунд
    const interval = setInterval(loadStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="status-page">
        <div className="status-loading">Загрузка статуса...</div>
      </div>
    );
  }

  const getStatusColor = (statusValue) => {
    const colors = {
      operational: '#28a745',
      degraded: '#ffc107',
      major_outage: '#dc3545',
      maintenance: '#17a2b8',
    };
    return colors[statusValue] || '#6c757d';
  };

  const getStatusIcon = (statusValue) => {
    const icons = {
      operational: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22,4 12,14.01 9,11.01"/>
        </svg>
      ),
      degraded: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      ),
      major_outage: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
      ),
      maintenance: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
        </svg>
      ),
    };
    return icons[statusValue] || icons.operational;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="status-page">
      <div className="status-container">
        <header className="status-header">
          <h1>Статус системы</h1>
          <p className="status-updated">
            Обновлено: {status?.updated_at ? formatDate(status.updated_at) : 'Н/Д'}
          </p>
        </header>

        {/* Основной статус */}
        <div 
          className="status-main"
          style={{ backgroundColor: getStatusColor(status?.status) }}
        >
          <span className="status-icon">
            {getStatusIcon(status?.status)}
          </span>
          <span className="status-text">
            {status?.status_display || 'Загрузка...'}
          </span>
        </div>

        {/* Инцидент */}
        {status?.status !== 'operational' && status?.incident_title && (
          <div className="status-incident">
            <h3>Текущий инцидент</h3>
            <div className="incident-details">
              <p className="incident-title">{status.incident_title}</p>
              {status.message && (
                <p className="incident-message">{status.message}</p>
              )}
              {status.incident_started_at && (
                <p className="incident-time">
                  Начало: {formatDate(status.incident_started_at)}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Компоненты системы */}
        {health && (
          <div className="status-components">
            <h3>Компоненты</h3>
            <div className="components-list">
              <div className="component-item">
                <span className="component-name">База данных</span>
                <span 
                  className="component-status"
                  data-status={health.checks?.database?.status}
                >
                  {health.checks?.database?.status === 'ok' ? 'Работает' : 'Проблема'}
                  {health.checks?.database?.latency_ms && (
                    <small> ({health.checks.database.latency_ms}ms)</small>
                  )}
                </span>
              </div>
              <div className="component-item">
                <span className="component-name">Кэш</span>
                <span 
                  className="component-status"
                  data-status={health.checks?.cache?.status}
                >
                  {health.checks?.cache?.status === 'ok' ? 'Работает' : 
                   health.checks?.cache?.status === 'skipped' ? 'Не настроен' : 'Проблема'}
                </span>
              </div>
              <div className="component-item">
                <span className="component-name">API</span>
                <span 
                  className="component-status"
                  data-status={health.status === 'healthy' ? 'ok' : 'error'}
                >
                  {health.status === 'healthy' ? 'Работает' : 'Проблема'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Ссылка на поддержку */}
        <div className="status-support">
          <p>Возникли проблемы? Свяжитесь с поддержкой через виджет в правом нижнем углу.</p>
        </div>

        {error && (
          <div className="status-error">{error}</div>
        )}
      </div>
    </div>
  );
};

export default StatusPage;
