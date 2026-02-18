import React, { useEffect, useState, useMemo } from 'react';
import { useAuth } from '../auth';
import { getFinanceStats } from '../apiService';
import './FinanceDashboard.css';

/**
 * Панель «Финансы» — обзор доходов, продаж и статистики по курсам.
 *
 * Доступна для admin и teacher.
 */
const FinanceDashboard = () => {
  const { accessTokenValid } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [tab, setTab] = useState('overview'); // overview | courses | sales

  useEffect(() => {
    if (!accessTokenValid) return;
    loadData();
  }, [accessTokenValid]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getFinanceStats();
      setData(res.data);
    } catch (err) {
      console.error('Finance load error:', err);
      setError('Не удалось загрузить финансовые данные');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    const num = parseFloat(value) || 0;
    return num.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' ₽';
  };

  const formatDate = (isoString) => {
    const d = new Date(isoString);
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const formatDateTime = (isoString) => {
    const d = new Date(isoString);
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) + ' ' +
      d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  // Monthly chart — simple bar chart via CSS
  const maxMonthlyRevenue = useMemo(() => {
    if (!data?.monthly) return 1;
    const vals = data.monthly.map(m => parseFloat(m.revenue) || 0);
    return Math.max(...vals, 1);
  }, [data]);

  const monthLabel = (str) => {
    if (!str || str === '—') return '—';
    const [y, m] = str.split('-');
    const months = ['', 'Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
    return `${months[parseInt(m, 10)]} ${y?.slice(2)}`;
  };

  if (loading) {
    return (
      <div className="finance-page">
        <div className="finance-loading">
          <div className="finance-spinner"></div>
          <p>Загрузка финансов...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="finance-page">
        <div className="finance-error">
          <span className="finance-error-icon">⚠️</span>
          <p>{error}</p>
          <button onClick={loadData} className="finance-retry-btn">Попробовать снова</button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { summary, monthly, courses, recent_sales } = data;

  return (
    <div className="finance-page">
      {/* Header */}
      <div className="finance-header">
        <div className="finance-header-left">
          <h1 className="finance-title">Финансы</h1>
          <p className="finance-subtitle">Доходы, продажи и статистика курсов</p>
        </div>
        <button onClick={loadData} className="finance-refresh-btn" title="Обновить">
          Обновить
        </button>
      </div>

      {/* Summary Cards */}
      <div className="finance-summary-grid">
        <div className="finance-card finance-card-primary">
          <div className="finance-card-icon">₽</div>
          <div className="finance-card-body">
            <span className="finance-card-label">Общая выручка</span>
            <span className="finance-card-value finance-card-value-lg">
              {formatCurrency(summary.total_revenue)}
            </span>
          </div>
        </div>

        <div className="finance-card">
          <div className="finance-card-icon">—</div>
          <div className="finance-card-body">
            <span className="finance-card-label">Покупки</span>
            <span className="finance-card-value">{summary.purchased}</span>
          </div>
        </div>

        <div className="finance-card">
          <div className="finance-card-icon">—</div>
          <div className="finance-card-body">
            <span className="finance-card-label">Подарено</span>
            <span className="finance-card-value">{summary.granted}</span>
          </div>
        </div>

        <div className="finance-card">
          <div className="finance-card-icon">—</div>
          <div className="finance-card-body">
            <span className="finance-card-label">Пробный доступ</span>
            <span className="finance-card-value">{summary.trial}</span>
          </div>
        </div>

        <div className="finance-card">
          <div className="finance-card-icon">—</div>
          <div className="finance-card-body">
            <span className="finance-card-label">Активные доступы</span>
            <span className="finance-card-value">{summary.active_accesses}</span>
          </div>
        </div>

        <div className="finance-card">
          <div className="finance-card-icon">—</div>
          <div className="finance-card-body">
            <span className="finance-card-label">Курсов</span>
            <span className="finance-card-value">{summary.courses_count}</span>
            <span className="finance-card-sub">{summary.published_courses} опубликовано</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="finance-tabs">
        <button className={`finance-tab ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}>
          Динамика
        </button>
        <button className={`finance-tab ${tab === 'courses' ? 'active' : ''}`} onClick={() => setTab('courses')}>
          По курсам
        </button>
        <button className={`finance-tab ${tab === 'sales' ? 'active' : ''}`} onClick={() => setTab('sales')}>
          Последние продажи
        </button>
      </div>

      {/* Tab Content */}
      <div className="finance-tab-content">
        {tab === 'overview' && (
          <div className="finance-chart-section">
            <h3 className="finance-section-title">Продажи по месяцам</h3>
            {monthly.length === 0 ? (
              <div className="finance-empty">Нет данных за последние 12 месяцев</div>
            ) : (
              <div className="finance-bar-chart">
                {monthly.map((m, i) => {
                  const rev = parseFloat(m.revenue) || 0;
                  const perc = (rev / maxMonthlyRevenue) * 100;
                  return (
                    <div key={i} className="finance-bar-col">
                      <div className="finance-bar-value">{formatCurrency(m.revenue)}</div>
                      <div className="finance-bar-track">
                        <div
                          className="finance-bar-fill"
                          style={{ height: `${Math.max(perc, 4)}%` }}
                        ></div>
                      </div>
                      <div className="finance-bar-label">{monthLabel(m.month)}</div>
                      <div className="finance-bar-sub">{m.purchased} пок.</div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Quick stats row */}
            <div className="finance-quick-row">
              <div className="finance-quick-item">
                <span className="finance-quick-label">Всего доступов</span>
                <span className="finance-quick-value">{summary.total_accesses}</span>
              </div>
              <div className="finance-quick-item">
                <span className="finance-quick-label">Истёкших</span>
                <span className="finance-quick-value">{summary.expired_accesses}</span>
              </div>
              <div className="finance-quick-item">
                <span className="finance-quick-label">Конверсия</span>
                <span className="finance-quick-value">
                  {summary.total_accesses > 0 
                    ? Math.round((summary.purchased / summary.total_accesses) * 100) 
                    : 0}%
                </span>
              </div>
            </div>
          </div>
        )}

        {tab === 'courses' && (
          <div className="finance-courses-section">
            <h3 className="finance-section-title">Статистика по курсам</h3>
            {courses.length === 0 ? (
              <div className="finance-empty">Курсов пока нет</div>
            ) : (
              <div className="finance-courses-table-wrap">
                <table className="finance-courses-table">
                  <thead>
                    <tr>
                      <th>Курс</th>
                      <th>Цена</th>
                      <th>Статус</th>
                      <th>Покупки</th>
                      <th>Подарено</th>
                      <th>Пробный</th>
                      <th>Выручка</th>
                    </tr>
                  </thead>
                  <tbody>
                    {courses.map(c => (
                      <tr key={c.id}>
                        <td className="finance-course-name">{c.title}</td>
                        <td>{c.price ? `${parseFloat(c.price).toLocaleString('ru-RU')} ₽` : <span className="finance-free-badge">Бесплатно</span>}</td>
                        <td>
                          <span className={`finance-status-badge ${c.is_published ? 'published' : 'draft'}`}>
                            {c.is_published ? '🟢 Опубликован' : '⚪ Черновик'}
                          </span>
                        </td>
                        <td className="finance-num">{c.purchased}</td>
                        <td className="finance-num">{c.granted}</td>
                        <td className="finance-num">{c.trial}</td>
                        <td className="finance-revenue-cell">
                          {formatCurrency(c.revenue)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan="3"><strong>Итого</strong></td>
                      <td className="finance-num"><strong>{courses.reduce((s, c) => s + c.purchased, 0)}</strong></td>
                      <td className="finance-num"><strong>{courses.reduce((s, c) => s + c.granted, 0)}</strong></td>
                      <td className="finance-num"><strong>{courses.reduce((s, c) => s + c.trial, 0)}</strong></td>
                      <td className="finance-revenue-cell">
                        <strong>{formatCurrency(summary.total_revenue)}</strong>
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        )}

        {tab === 'sales' && (
          <div className="finance-sales-section">
            <h3 className="finance-section-title">Последние продажи и доступы</h3>
            {recent_sales.length === 0 ? (
              <div className="finance-empty">Нет данных о продажах</div>
            ) : (
              <div className="finance-sales-list">
                {recent_sales.map(sale => (
                  <div key={sale.id} className="finance-sale-row">
                    <div className="finance-sale-avatar">
                      {sale.user_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="finance-sale-info">
                      <div className="finance-sale-user">{sale.user_name}</div>
                      <div className="finance-sale-email">{sale.user_email}</div>
                    </div>
                    <div className="finance-sale-course">{sale.course_title}</div>
                    <div className="finance-sale-meta">
                      <span className={`finance-access-badge ${sale.access_type}`}>
                        {sale.access_type === 'purchased' ? '🛒 Покупка' :
                         sale.access_type === 'granted' ? '🎁 Подарено' : '🔓 Пробный'}
                      </span>
                      {sale.access_type === 'purchased' && parseFloat(sale.amount) > 0 && (
                        <span className="finance-sale-amount">{formatCurrency(sale.amount)}</span>
                      )}
                    </div>
                    <div className="finance-sale-date">{formatDateTime(sale.granted_at)}</div>
                    <div className={`finance-sale-status ${sale.is_active ? 'active' : 'inactive'}`}>
                      {sale.is_active ? '✅' : '❌'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default FinanceDashboard;
