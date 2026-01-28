import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, PieChart, Pie, CartesianGrid
} from 'recharts';
import { getAccessToken } from '../../apiService';
import './BusinessMetricsDashboard.css';

/**
 * Компонент расширенных бизнес-метрик для админ-панели.
 * Светлая тема, современный дизайн.
 * 
 * Включает:
 * - Воронку активации (funnel)
 * - MRR Waterfall
 * - Сегментацию по источникам и планам
 * - Ключевые KPI
 */
const BusinessMetricsDashboard = ({ onClose }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const token = getAccessToken();
      // Исправлен URL - используем путь без /accounts/ prefix
      const response = await fetch('/api/admin/business-metrics/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) {
        const text = await response.text();
        console.error('API Error:', text);
        throw new Error('Не удалось загрузить метрики');
      }
      const json = await response.json();
      setData(json);
    } catch (err) {
      console.error('Error loading business metrics:', err);
      setError(err.message || 'Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const formatRub = (value) => {
    if (value === undefined || value === null) return '0 RUB';
    return new Intl.NumberFormat('ru-RU').format(Math.round(value)) + ' RUB';
  };

  const formatRubShort = (value) => {
    if (value === undefined || value === null) return '0';
    if (Math.abs(value) >= 1000000) {
      return (value / 1000000).toFixed(1) + 'M';
    }
    if (Math.abs(value) >= 1000) {
      return (value / 1000).toFixed(0) + 'K';
    }
    return Math.round(value).toString();
  };

  const formatPercent = (value) => {
    if (value === undefined || value === null) return '0%';
    return value.toFixed(1) + '%';
  };

  // Overview KPI Cards
  const KPICards = () => {
    const funnel = data?.activation_funnel;
    const mrr = data?.mrr_waterfall;
    const plans = data?.plans_breakdown || [];
    
    const totalRevenue = plans.reduce((sum, p) => sum + (p.revenue || 0), 0);
    const activeSubs = plans.reduce((sum, p) => sum + (p.count || 0), 0);
    const conversionRate = funnel?.steps?.[5]?.percent || 0;
    const growthRate = mrr?.summary?.growth_rate || 0;
    
    return (
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon revenue-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </div>
          <div className="kpi-content">
            <div className="kpi-value">{formatRub(totalRevenue)}</div>
            <div className="kpi-label">Выручка за месяц</div>
          </div>
        </div>
        
        <div className="kpi-card">
          <div className="kpi-icon users-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <div className="kpi-content">
            <div className="kpi-value">{activeSubs}</div>
            <div className="kpi-label">Активных подписок</div>
          </div>
        </div>
        
        <div className="kpi-card">
          <div className="kpi-icon conversion-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div className="kpi-content">
            <div className="kpi-value">{formatPercent(conversionRate)}</div>
            <div className="kpi-label">Конверсия в оплату</div>
          </div>
        </div>
        
        <div className="kpi-card">
          <div className={`kpi-icon growth-icon ${growthRate >= 0 ? 'positive' : 'negative'}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {growthRate >= 0 ? (
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
              ) : (
                <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
              )}
              <polyline points={growthRate >= 0 ? "17 6 23 6 23 12" : "17 18 23 18 23 12"} />
            </svg>
          </div>
          <div className="kpi-content">
            <div className={`kpi-value ${growthRate >= 0 ? 'positive' : 'negative'}`}>
              {growthRate >= 0 ? '+' : ''}{formatPercent(growthRate)}
            </div>
            <div className="kpi-label">Рост MRR</div>
          </div>
        </div>
      </div>
    );
  };

  // Funnel Chart компонент
  const FunnelChart = ({ steps }) => {
    if (!steps || steps.length === 0) {
      return <div className="empty-state">Нет данных для воронки</div>;
    }
    
    const maxValue = steps[0]?.value || 1;
    const colors = ['#4F46E5', '#7C3AED', '#A855F7', '#D946EF', '#EC4899', '#10B981'];
    
    return (
      <div className="funnel-container">
        <div className="funnel-chart">
          {steps.map((step, index) => {
            const widthPercent = (step.value / maxValue) * 100;
            const dropoff = index > 0 ? steps[index - 1].value - step.value : 0;
            const dropoffPercent = index > 0 && steps[index - 1].value > 0
              ? ((dropoff / steps[index - 1].value) * 100).toFixed(1)
              : 0;
            
            return (
              <div key={step.name} className="funnel-step">
                <div className="funnel-info">
                  <span className="funnel-name">{step.name}</span>
                  <span className="funnel-percent">{formatPercent(step.percent)}</span>
                </div>
                <div className="funnel-bar-wrapper">
                  <div 
                    className="funnel-bar"
                    style={{ 
                      width: `${Math.max(widthPercent, 8)}%`,
                      backgroundColor: colors[index] || step.color
                    }}
                  >
                    <span className="funnel-value">{step.value}</span>
                  </div>
                  {index > 0 && dropoff > 0 && (
                    <div className="funnel-dropoff">
                      <svg viewBox="0 0 16 16" fill="currentColor" width="12" height="12">
                        <path d="M8 12l-4-4h8z"/>
                      </svg>
                      {dropoff} ({dropoffPercent}%)
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Conversion highlights */}
        <div className="funnel-highlights">
          <div className="highlight-card">
            <div className="highlight-value">{formatPercent(steps[1]?.percent || 0)}</div>
            <div className="highlight-label">Создают группу</div>
          </div>
          <div className="highlight-card">
            <div className="highlight-value">{formatPercent(steps[4]?.percent || 0)}</div>
            <div className="highlight-label">Проводят урок</div>
          </div>
          <div className="highlight-card success">
            <div className="highlight-value">{formatPercent(steps[5]?.percent || 0)}</div>
            <div className="highlight-label">Оплачивают</div>
          </div>
        </div>
      </div>
    );
  };

  // Waterfall Chart компонент
  const WaterfallChart = ({ bars }) => {
    if (!bars || bars.length === 0) {
      return <div className="empty-state">Нет данных для waterfall</div>;
    }
    
    const chartData = bars.map((bar) => ({
      name: bar.name,
      value: Math.abs(bar.value),
      displayValue: bar.value,
      fill: bar.color,
      type: bar.type
    }));
    
    return (
      <div className="waterfall-container">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 70 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
            <XAxis 
              dataKey="name" 
              tick={{ fill: '#6B7280', fontSize: 12 }}
              angle={-35}
              textAnchor="end"
              height={80}
              axisLine={{ stroke: '#E5E7EB' }}
              tickLine={false}
            />
            <YAxis 
              tick={{ fill: '#6B7280', fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => formatRubShort(v)}
            />
            <Tooltip 
              contentStyle={{ 
                background: '#fff', 
                border: '1px solid #E5E7EB', 
                borderRadius: 8,
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
              }}
              labelStyle={{ color: '#111827', fontWeight: 600 }}
              formatter={(value, name, props) => [
                formatRub(props.payload.displayValue),
                ''
              ]}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        
        {/* Summary cards */}
        <div className="waterfall-summary">
          <div className="summary-item positive">
            <div className="summary-value">{formatRub(data?.mrr_waterfall?.summary?.net_new_mrr || 0)}</div>
            <div className="summary-label">Net New MRR</div>
          </div>
          <div className="summary-item">
            <div className={`summary-value ${(data?.mrr_waterfall?.summary?.growth_rate || 0) >= 0 ? 'positive' : 'negative'}`}>
              {(data?.mrr_waterfall?.summary?.growth_rate || 0) >= 0 ? '+' : ''}
              {formatPercent(data?.mrr_waterfall?.summary?.growth_rate || 0)}
            </div>
            <div className="summary-label">Рост MRR</div>
          </div>
        </div>
      </div>
    );
  };

  // Sources Table компонент
  const SourcesTable = ({ sources }) => {
    if (!sources || sources.length === 0) {
      return <div className="empty-state">Нет данных по источникам</div>;
    }
    
    const colors = ['#4F46E5', '#7C3AED', '#EC4899', '#F59E0B', '#10B981', '#06B6D4', '#8B5CF6'];
    
    return (
      <div className="sources-container">
        <div className="sources-table-wrapper">
          <table className="sources-table">
            <thead>
              <tr>
                <th>Источник</th>
                <th>Регистрации</th>
                <th>С группой</th>
                <th>С уроком</th>
                <th>Оплатили</th>
                <th>Конверсия</th>
                <th>Выручка</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source, index) => (
                <tr key={source.source || index}>
                  <td>
                    <div className="source-name">
                      <span 
                        className="source-dot" 
                        style={{ backgroundColor: colors[index % colors.length] }} 
                      />
                      {source.source || 'unknown'}
                    </div>
                  </td>
                  <td className="number">{source.registrations}</td>
                  <td className="number">{source.with_group || 0}</td>
                  <td className="number">{source.with_lesson || 0}</td>
                  <td className="number">{source.paid_users || 0}</td>
                  <td className={`number ${source.conversion > 10 ? 'good' : source.conversion > 5 ? 'medium' : ''}`}>
                    {formatPercent(source.conversion || 0)}
                  </td>
                  <td className="number revenue">{formatRub(source.revenue || 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // Plans Breakdown компонент
  const PlansBreakdown = ({ plans }) => {
    if (!plans || plans.length === 0) {
      return <div className="empty-state">Нет данных по планам</div>;
    }
    
    const colors = ['#4F46E5', '#10B981', '#F59E0B', '#EC4899'];
    const pieData = plans.map((p, i) => ({
      name: p.plan_label || p.plan,
      value: p.count,
      fill: colors[i % colors.length]
    }));
    const totalRevenue = plans.reduce((sum, p) => sum + (p.revenue || 0), 0);
    
    return (
      <div className="plans-container">
        <div className="plans-grid">
          <div className="plans-chart-section">
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  innerRadius={55}
                  strokeWidth={2}
                  stroke="#fff"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    background: '#fff', 
                    border: '1px solid #E5E7EB', 
                    borderRadius: 8,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                  }}
                  formatter={(value) => [value, 'Подписок']}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="chart-center-label">
              <div className="center-value">{plans.reduce((s, p) => s + p.count, 0)}</div>
              <div className="center-text">всего</div>
            </div>
          </div>
          
          <div className="plans-list-section">
            {plans.map((plan, index) => (
              <div key={plan.plan} className="plan-card">
                <div className="plan-header">
                  <span 
                    className="plan-dot" 
                    style={{ backgroundColor: colors[index % colors.length] }} 
                  />
                  <span className="plan-name">{plan.plan_label || plan.plan}</span>
                  <span className="plan-count">{plan.count} подписок</span>
                </div>
                <div className="plan-revenue">
                  <div className="revenue-bar-bg">
                    <div 
                      className="revenue-bar-fill" 
                      style={{ 
                        width: `${totalRevenue > 0 ? (plan.revenue / totalRevenue) * 100 : 0}%`,
                        backgroundColor: colors[index % colors.length]
                      }} 
                    />
                  </div>
                  <span className="revenue-value">{formatRub(plan.revenue)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  // Tabs configuration
  const tabs = [
    { id: 'overview', label: 'Обзор' },
    { id: 'funnel', label: 'Воронка' },
    { id: 'mrr', label: 'MRR' },
    { id: 'sources', label: 'Источники' },
    { id: 'plans', label: 'Планы' }
  ];

  if (loading) {
    return (
      <div className="bm-modal-overlay" onClick={onClose}>
        <div className="bm-modal" onClick={(e) => e.stopPropagation()}>
          <div className="bm-loading">
            <div className="bm-spinner" />
            <span>Загрузка метрик...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bm-modal-overlay" onClick={onClose}>
        <div className="bm-modal" onClick={(e) => e.stopPropagation()}>
          <div className="bm-header">
            <h2>Бизнес-аналитика</h2>
            <button className="bm-close" onClick={onClose}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="bm-error">
            <div className="error-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="48" height="48">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8v4M12 16h.01" />
              </svg>
            </div>
            <span className="error-text">{error}</span>
            <button onClick={loadData} className="bm-retry-btn">
              Повторить
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bm-modal-overlay" onClick={onClose}>
      <div className="bm-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="bm-header">
          <div className="bm-title-section">
            <h2>Бизнес-аналитика</h2>
            <span className="bm-period">{data?.activation_funnel?.period || 'Последние 30 дней'}</span>
          </div>
          <button className="bm-close" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="bm-tabs">
          {tabs.map(tab => (
            <button 
              key={tab.id}
              className={`bm-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="bm-content">
          {activeTab === 'overview' && (
            <div className="bm-section">
              <KPICards />
              
              <div className="bm-overview-grid">
                <div className="bm-card">
                  <h3>Конверсия по воронке</h3>
                  <div className="mini-funnel">
                    {data?.activation_funnel?.steps?.slice(0, 4).map((step, i) => (
                      <div key={step.name} className="mini-step">
                        <div className="mini-bar" style={{ 
                          width: `${Math.max(step.percent, 5)}%`,
                          backgroundColor: ['#4F46E5', '#7C3AED', '#A855F7', '#D946EF'][i]
                        }} />
                        <span>{step.name}: {formatPercent(step.percent)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="bm-card">
                  <h3>Распределение планов</h3>
                  <div className="mini-plans">
                    {data?.plans_breakdown?.map((plan, i) => (
                      <div key={plan.plan} className="mini-plan">
                        <span 
                          className="plan-indicator" 
                          style={{ backgroundColor: ['#4F46E5', '#10B981', '#F59E0B'][i] }}
                        />
                        <span className="plan-label">{plan.plan_label || plan.plan}</span>
                        <span className="plan-value">{plan.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'funnel' && (
            <div className="bm-section">
              <div className="section-header">
                <h3>Воронка активации новых учителей</h3>
                <p>Показывает путь учителя от регистрации до первой оплаты. 
                   Всего зарегистрировалось: <strong>{data?.activation_funnel?.total_registered || 0}</strong></p>
              </div>
              <FunnelChart steps={data?.activation_funnel?.steps} />
            </div>
          )}

          {activeTab === 'mrr' && (
            <div className="bm-section">
              <div className="section-header">
                <h3>MRR Waterfall</h3>
                <p>Изменение месячной выручки: новые клиенты, expansion, продления и отток.</p>
              </div>
              <WaterfallChart bars={data?.mrr_waterfall?.bars} />
            </div>
          )}

          {activeTab === 'sources' && (
            <div className="bm-section">
              <div className="section-header">
                <h3>Источники трафика</h3>
                <p>Анализ эффективности каналов привлечения по регистрациям, активации и выручке.</p>
              </div>
              <SourcesTable sources={data?.sources_breakdown} />
            </div>
          )}

          {activeTab === 'plans' && (
            <div className="bm-section">
              <div className="section-header">
                <h3>Распределение по тарифам</h3>
                <p>Активные подписки по тарифным планам и выручка за период.</p>
              </div>
              <PlansBreakdown plans={data?.plans_breakdown} />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bm-footer">
          <span className="bm-updated">
            Обновлено: {data?.generated_at ? new Date(data.generated_at).toLocaleString('ru-RU') : '—'}
          </span>
          <button className="bm-refresh" onClick={loadData}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
              <path d="M23 4v6h-6M1 20v-6h6" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            Обновить
          </button>
        </div>
      </div>
    </div>
  );
};

export default BusinessMetricsDashboard;
