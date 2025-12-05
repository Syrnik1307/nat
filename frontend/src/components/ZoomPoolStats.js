import React, { useState, useEffect } from 'react';
import { getZoomPoolStats } from '../apiService';
import './ZoomPoolStats.css';

const ZoomPoolStats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadStats = async () => {
    try {
      setError(null);
      const data = await getZoomPoolStats();
      setStats(data);
      setLoading(false);
    } catch (err) {
      console.error('Error loading Zoom pool stats:', err);
      setError('Не удалось загрузить статистику');
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
    
    let interval;
    if (autoRefresh) {
      interval = setInterval(loadStats, 30000); // Обновление каждые 30 секунд
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  if (loading) {
    return (
      <div className="zoom-pool-stats">
        <div className="loading-spinner">Загрузка...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="zoom-pool-stats">
        <div className="error-message">
          <p>{error}</p>
          <button onClick={loadStats} className="retry-btn">Повторить</button>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  const utilizationPercent = stats.active_accounts > 0 
    ? Math.round((stats.currently_in_use / stats.active_accounts) * 100) 
    : 0;

  const sessionUtilization = stats.current_sessions > 0 && stats.peak_sessions > 0
    ? Math.round((stats.current_sessions / stats.peak_sessions) * 100)
    : 0;

  return (
    <div className="zoom-pool-stats">
      <div className="stats-header">
        <h2>📊 Аналитика Zoom Pool</h2>
        <div className="stats-controls">
          <label className="auto-refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>Автообновление (30с)</span>
          </label>
          <button onClick={loadStats} className="refresh-btn">🔄 Обновить</button>
        </div>
      </div>

      <div className="stats-grid">
        {/* Карточка: Аккаунты */}
        <div className="stat-card accounts-card">
          <div className="stat-icon">⚠</div>
          <div className="stat-content">
            <h3>Zoom Аккаунты</h3>
            <div className="stat-main-value">{stats.total_accounts}</div>
            <div className="stat-details">
              <div className="stat-detail">
                <span className="label">Активные:</span>
                <span className="value active">{stats.active_accounts}</span>
              </div>
              <div className="stat-detail">
                <span className="label">Доступны:</span>
                <span className="value available">{stats.available_accounts}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Карточка: Текущая нагрузка */}
        <div className="stat-card usage-card">
          <div className="stat-icon">⚡</div>
          <div className="stat-content">
            <h3>Текущая нагрузка</h3>
            <div className="stat-main-value">{stats.currently_in_use}</div>
            <div className="stat-subtitle">аккаунтов используется</div>
            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{ width: `${utilizationPercent}%` }}
              ></div>
            </div>
            <div className="progress-label">{utilizationPercent}% загрузка</div>
          </div>
        </div>

        {/* Карточка: Пиковая нагрузка */}
        <div className="stat-card peak-card">
          <div className="stat-icon">📈</div>
          <div className="stat-content">
            <h3>Пиковая нагрузка (месяц)</h3>
            <div className="stat-main-value">{stats.peak_in_use}</div>
            <div className="stat-subtitle">макс. одновременно</div>
            <div className="stat-comparison">
              {stats.currently_in_use === stats.peak_in_use && (
                <span className="badge peak-now">🔴 Сейчас на пике!</span>
              )}
              {stats.currently_in_use < stats.peak_in_use && (
                <span className="badge normal">Нормальная загрузка</span>
              )}
            </div>
          </div>
        </div>

        {/* Карточка: Сессии */}
        <div className="stat-card sessions-card">
          <div className="stat-icon">●</div>
          <div className="stat-content">
            <h3>Активные сессии</h3>
            <div className="stat-main-value">{stats.current_sessions}</div>
            <div className="stat-details">
              <div className="stat-detail">
                <span className="label">Пик (месяц):</span>
                <span className="value peak">{stats.peak_sessions}</span>
              </div>
              <div className="stat-detail">
                <span className="label">Загрузка:</span>
                <span className="value">{sessionUtilization}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Информационная панель */}
      <div className="info-panel">
        <div className="info-section">
          <h4>ℹ️ Информация</h4>
          <ul>
            <li><strong>Текущая нагрузка</strong> - количество Zoom аккаунтов, используемых прямо сейчас</li>
            <li><strong>Пиковая нагрузка</strong> - максимальное количество одновременно используемых аккаунтов за текущий месяц</li>
            <li><strong>Активные сессии</strong> - количество активных Zoom-конференций в данный момент</li>
            <li><strong>Пик сессий</strong> - максимальное количество одновременных конференций за месяц</li>
          </ul>
        </div>
        <div className="info-section">
          <h4>Статистика</h4>
          <p>Данные обновляются автоматически каждые 30 секунд</p>
        </div>
      </div>

      {/* Рекомендации */}
      {stats.available_accounts === 0 && (
        <div className="alert alert-warning">
          ⚠️ <strong>Внимание!</strong> Все аккаунты заняты. Рассмотрите возможность добавления новых аккаунтов.
        </div>
      )}
      
      {stats.currently_in_use === stats.peak_in_use && stats.peak_in_use > 0 && (
        <div className="alert alert-info">
          📊 <strong>Пиковая нагрузка!</strong> Система работает на максимальной загрузке. Мониторьте доступность.
        </div>
      )}
    </div>
  );
};

export default ZoomPoolStats;
