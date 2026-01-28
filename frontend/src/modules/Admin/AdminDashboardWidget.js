import React, { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import { getAccessToken } from '../../apiService';
import './AdminDashboardWidget.css';

/**
 * Виджет главного дашборда админа
 * - Health checks для всех систем
 * - Графики доходов по дням
 * - Графики подписчиков
 * - Графики доходов по неделям
 */
const AdminDashboardWidget = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const [activeChart, setActiveChart] = useState('revenue');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const token = getAccessToken();
      const response = await fetch('/api/admin/dashboard-data/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) {
        throw new Error('Не удалось загрузить данные');
      }
      const json = await response.json();
      setData(json);
    } catch (err) {
      console.error('Dashboard load error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Автообновление каждые 5 минут
    const interval = setInterval(loadData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [loadData]);

  const formatRub = (value) => {
    if (value === undefined || value === null) return '0';
    return new Intl.NumberFormat('ru-RU').format(Math.round(value));
  };

  const formatRubShort = (value) => {
    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
    if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
    return Math.round(value).toString();
  };

  // Статус иконки для health checks
  const StatusIcon = ({ status }) => {
    const colors = {
      ok: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444',
      info: '#6b7280'
    };
    return (
      <div 
        className="health-status-dot" 
        style={{ backgroundColor: colors[status] || colors.info }}
      />
    );
  };

  if (loading && !data) {
    return (
      <div className="admin-dashboard-widget">
        <div className="dashboard-loading">
          <div className="loading-spinner" />
          <span>Загрузка дашборда...</span>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="admin-dashboard-widget">
        <div className="dashboard-error">
          <span>{error}</span>
          <button onClick={loadData} className="retry-btn">Повторить</button>
        </div>
      </div>
    );
  }

  const metrics = data?.metrics || {};
  const healthChecks = data?.health_checks || [];

  return (
    <div className="admin-dashboard-widget">
      {/* Ключевые метрики */}
      <div className="dashboard-metrics-row">
        <div className="metric-card primary">
          <div className="metric-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="24" height="24">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </div>
          <div className="metric-content">
            <div className="metric-value">{formatRub(metrics.today_revenue)} RUB</div>
            <div className="metric-label">Доход сегодня</div>
            {metrics.revenue_change !== 0 && (
              <div className={`metric-change ${metrics.revenue_change >= 0 ? 'positive' : 'negative'}`}>
                {metrics.revenue_change >= 0 ? '+' : ''}{formatRub(metrics.revenue_change)}
                <span className="change-label"> vs вчера</span>
              </div>
            )}
          </div>
        </div>

        <div className="metric-card success">
          <div className="metric-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="24" height="24">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <div className="metric-content">
            <div className="metric-value">{metrics.active_subscriptions}</div>
            <div className="metric-label">Активных подписок</div>
            {metrics.expiring_soon > 0 && (
              <div className="metric-change warning">
                {metrics.expiring_soon} истекают скоро
              </div>
            )}
          </div>
        </div>

        <div className="metric-card info">
          <div className="metric-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="24" height="24">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div className="metric-content">
            <div className="metric-value">{formatRub(metrics.mrr)} RUB</div>
            <div className="metric-label">MRR</div>
            <div className="metric-subtext">
              {metrics.monthly_subscribers} мес. + {metrics.yearly_subscribers} год.
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="24" height="24">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
          </div>
          <div className="metric-content">
            <div className="metric-value">{formatRub(metrics.month_revenue)} RUB</div>
            <div className="metric-label">За 30 дней</div>
            <div className="metric-subtext">
              +{metrics.today_new_subscribers} новых сегодня
            </div>
          </div>
        </div>
      </div>

      {/* Статус систем */}
      <div className="dashboard-section">
        <div className="section-header">
          <h3>Статус систем</h3>
          <button className="refresh-btn" onClick={loadData} title="Обновить">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
              <path d="M23 4v6h-6M1 20v-6h6" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
          </button>
        </div>
        <div className="health-checks-grid">
          {healthChecks.map((check, index) => (
            <div key={index} className={`health-check-item ${check.status}`}>
              <StatusIcon status={check.status} />
              <div className="health-check-content">
                <div className="health-check-name">{check.name}</div>
                <div className="health-check-message">{check.message}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Табы графиков */}
      <div className="dashboard-section charts-section">
        <div className="section-header">
          <div className="chart-tabs">
            <button 
              className={`chart-tab ${activeChart === 'revenue' ? 'active' : ''}`}
              onClick={() => setActiveChart('revenue')}
            >
              Доходы по дням
            </button>
            <button 
              className={`chart-tab ${activeChart === 'subscribers' ? 'active' : ''}`}
              onClick={() => setActiveChart('subscribers')}
            >
              Подписчики
            </button>
            <button 
              className={`chart-tab ${activeChart === 'weekly' ? 'active' : ''}`}
              onClick={() => setActiveChart('weekly')}
            >
              По неделям
            </button>
          </div>
        </div>

        <div className="chart-container">
          {activeChart === 'revenue' && data?.daily_revenue && (
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={data.daily_revenue} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                  <XAxis 
                    dataKey="label" 
                    tick={{ fill: '#6b7280', fontSize: 12 }}
                    axisLine={{ stroke: '#e5e7eb' }}
                    tickLine={false}
                  />
                  <YAxis 
                    tick={{ fill: '#6b7280', fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={formatRubShort}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      background: '#fff', 
                      border: '1px solid #e5e7eb', 
                      borderRadius: 8,
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                    }}
                    formatter={(value) => [formatRub(value) + ' RUB', 'Доход']}
                    labelFormatter={(label) => `Дата: ${label}`}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="revenue" 
                    stroke="#6366f1" 
                    strokeWidth={2}
                    fill="url(#revenueGradient)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
              <div className="chart-summary">
                <div className="summary-item">
                  <span className="summary-label">Всего за период:</span>
                  <span className="summary-value">
                    {formatRub(data.daily_revenue.reduce((sum, d) => sum + d.revenue, 0))} RUB
                  </span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Платежей:</span>
                  <span className="summary-value">
                    {data.daily_revenue.reduce((sum, d) => sum + d.payments, 0)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {activeChart === 'subscribers' && data?.daily_subscribers && (
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={data.daily_subscribers} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                  <XAxis 
                    dataKey="label" 
                    tick={{ fill: '#6b7280', fontSize: 12 }}
                    axisLine={{ stroke: '#e5e7eb' }}
                    tickLine={false}
                  />
                  <YAxis 
                    tick={{ fill: '#6b7280', fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      background: '#fff', 
                      border: '1px solid #e5e7eb', 
                      borderRadius: 8,
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                    }}
                    formatter={(value, name) => {
                      const labels = { new: 'Новых', cumulative: 'Всего' };
                      return [value, labels[name] || name];
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="new" 
                    stroke="#10b981" 
                    strokeWidth={2}
                    dot={{ fill: '#10b981', strokeWidth: 0, r: 3 }}
                    activeDot={{ r: 5 }}
                    name="new"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="cumulative" 
                    stroke="#6366f1" 
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                    name="cumulative"
                  />
                </LineChart>
              </ResponsiveContainer>
              <div className="chart-legend">
                <div className="legend-item">
                  <span className="legend-dot" style={{ backgroundColor: '#10b981' }} />
                  <span>Новых подписчиков</span>
                </div>
                <div className="legend-item">
                  <span className="legend-line" style={{ borderColor: '#6366f1' }} />
                  <span>Накопительный итог</span>
                </div>
              </div>
            </div>
          )}

          {activeChart === 'weekly' && data?.weekly_revenue && (
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data.weekly_revenue} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                  <XAxis 
                    dataKey="label" 
                    tick={{ fill: '#6b7280', fontSize: 11 }}
                    axisLine={{ stroke: '#e5e7eb' }}
                    tickLine={false}
                    angle={-20}
                    textAnchor="end"
                    height={50}
                  />
                  <YAxis 
                    tick={{ fill: '#6b7280', fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={formatRubShort}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      background: '#fff', 
                      border: '1px solid #e5e7eb', 
                      borderRadius: 8,
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                    }}
                    formatter={(value) => [formatRub(value) + ' RUB', 'Доход']}
                    labelFormatter={(label) => `Неделя: ${label}`}
                  />
                  <Bar 
                    dataKey="revenue" 
                    fill="#8b5cf6" 
                    radius={[6, 6, 0, 0]}
                    maxBarSize={50}
                  />
                </BarChart>
              </ResponsiveContainer>
              <div className="chart-summary">
                <div className="summary-item">
                  <span className="summary-label">Всего за период:</span>
                  <span className="summary-value">
                    {formatRub(data.weekly_revenue.reduce((sum, d) => sum + d.revenue, 0))} RUB
                  </span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Средний за неделю:</span>
                  <span className="summary-value">
                    {formatRub(data.weekly_revenue.length > 0 
                      ? data.weekly_revenue.reduce((sum, d) => sum + d.revenue, 0) / data.weekly_revenue.length 
                      : 0)} RUB
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Время обновления */}
      <div className="dashboard-footer">
        <span className="update-time">
          Обновлено: {data?.generated_at ? new Date(data.generated_at).toLocaleString('ru-RU') : '—'}
        </span>
      </div>
    </div>
  );
};

export default AdminDashboardWidget;
