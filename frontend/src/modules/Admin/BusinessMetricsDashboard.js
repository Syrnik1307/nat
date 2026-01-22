import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, PieChart, Pie, Legend
} from 'recharts';
import { getAccessToken } from '../../apiService';
import './BusinessMetricsDashboard.css';

/**
 * Компонент расширенных бизнес-метрик для админ-панели.
 * Включает:
 * - Воронку активации (funnel)
 * - MRR Waterfall
 * - Сегментацию по источникам и планам
 */
const BusinessMetricsDashboard = ({ onClose }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('funnel');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const token = getAccessToken();
      const response = await fetch('/accounts/api/admin/business-metrics/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) {
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

  const formatPercent = (value) => {
    if (value === undefined || value === null) return '0%';
    return value.toFixed(1) + '%';
  };

  // Funnel Chart компонент
  const FunnelChart = ({ steps }) => {
    if (!steps || steps.length === 0) return null;
    
    const maxValue = steps[0]?.value || 1;
    
    return (
      <div className="funnel-chart">
        {steps.map((step, index) => {
          const widthPercent = (step.value / maxValue) * 100;
          const dropoff = index > 0 
            ? steps[index - 1].value - step.value 
            : 0;
          const dropoffPercent = index > 0 && steps[index - 1].value > 0
            ? ((dropoff / steps[index - 1].value) * 100).toFixed(1)
            : 0;
          
          return (
            <div key={step.name} className="funnel-step">
              <div className="funnel-bar-container">
                <div 
                  className="funnel-bar"
                  style={{ 
                    width: `${Math.max(widthPercent, 5)}%`,
                    backgroundColor: step.color || '#6366f1'
                  }}
                >
                  <span className="funnel-value">{step.value}</span>
                </div>
                {index > 0 && dropoff > 0 && (
                  <div className="funnel-dropoff">
                    -{dropoff} ({dropoffPercent}%)
                  </div>
                )}
              </div>
              <div className="funnel-label">
                <span className="funnel-name">{step.name}</span>
                <span className="funnel-percent">{formatPercent(step.percent)}</span>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // Waterfall Chart компонент
  const WaterfallChart = ({ bars }) => {
    if (!bars || bars.length === 0) return null;
    
    const chartData = bars.map((bar, index) => ({
      name: bar.name,
      value: Math.abs(bar.value),
      displayValue: bar.value,
      fill: bar.color,
      type: bar.type
    }));
    
    return (
      <div className="waterfall-chart">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
            <XAxis 
              dataKey="name" 
              tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
              angle={-35}
              textAnchor="end"
              height={80}
              axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
              tickLine={false}
            />
            <YAxis 
              tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip 
              contentStyle={{ 
                background: '#1a1a2e', 
                border: '1px solid rgba(255,255,255,0.1)', 
                borderRadius: 8 
              }}
              labelStyle={{ color: '#fff' }}
              formatter={(value, name, props) => [
                formatRub(props.payload.displayValue),
                props.payload.name
              ]}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  // Sources Table компонент
  const SourcesTable = ({ sources }) => {
    if (!sources || sources.length === 0) {
      return <div className="empty-state">Нет данных по источникам</div>;
    }
    
    return (
      <div className="sources-table-container">
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
                <td className="source-name">
                  <span className="source-badge" style={{ 
                    backgroundColor: `hsl(${(index * 40) % 360}, 70%, 50%)` 
                  }} />
                  {source.source || 'unknown'}
                </td>
                <td>{source.registrations}</td>
                <td>{source.with_group || 0}</td>
                <td>{source.with_lesson || 0}</td>
                <td>{source.paid_users || 0}</td>
                <td className={source.conversion > 10 ? 'good' : source.conversion > 5 ? 'medium' : 'low'}>
                  {formatPercent(source.conversion || 0)}
                </td>
                <td className="revenue">{formatRub(source.revenue || 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // Plans Breakdown компонент
  const PlansBreakdown = ({ plans }) => {
    if (!plans || plans.length === 0) {
      return <div className="empty-state">Нет данных по планам</div>;
    }
    
    const colors = ['#6366f1', '#22c55e', '#f59e0b', '#ec4899'];
    const pieData = plans.map((p, i) => ({
      name: p.plan_label || p.plan,
      value: p.count,
      fill: colors[i % colors.length]
    }));
    
    return (
      <div className="plans-breakdown">
        <div className="plans-chart">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={70}
                innerRadius={40}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: 8 }}
                formatter={(value) => [value, 'Подписок']}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="plans-list">
          {plans.map((plan, index) => (
            <div key={plan.plan} className="plan-item">
              <div className="plan-header">
                <span 
                  className="plan-dot" 
                  style={{ backgroundColor: colors[index % colors.length] }} 
                />
                <span className="plan-name">{plan.plan_label || plan.plan}</span>
              </div>
              <div className="plan-stats">
                <div className="plan-stat">
                  <span className="stat-value">{plan.count}</span>
                  <span className="stat-label">подписок</span>
                </div>
                <div className="plan-stat">
                  <span className="stat-value">{formatRub(plan.revenue)}</span>
                  <span className="stat-label">выручка</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="business-metrics-modal">
        <div className="business-metrics-content">
          <div className="loading-state">
            <div className="spinner" />
            <span>Загрузка метрик...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="business-metrics-modal">
        <div className="business-metrics-content">
          <div className="business-metrics-header">
            <h2>Бизнес-аналитика</h2>
            <button className="close-btn" onClick={onClose}>x</button>
          </div>
          <div className="error-state">
            <span>{error}</span>
            <button onClick={loadData} className="retry-btn">Повторить</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="business-metrics-modal" onClick={onClose}>
      <div className="business-metrics-content" onClick={(e) => e.stopPropagation()}>
        <div className="business-metrics-header">
          <h2>Бизнес-аналитика</h2>
          <button className="close-btn" onClick={onClose}>x</button>
        </div>

        {/* Табы */}
        <div className="metrics-tabs">
          <button 
            className={`tab-btn ${activeTab === 'funnel' ? 'active' : ''}`}
            onClick={() => setActiveTab('funnel')}
          >
            Воронка активации
          </button>
          <button 
            className={`tab-btn ${activeTab === 'mrr' ? 'active' : ''}`}
            onClick={() => setActiveTab('mrr')}
          >
            MRR Waterfall
          </button>
          <button 
            className={`tab-btn ${activeTab === 'sources' ? 'active' : ''}`}
            onClick={() => setActiveTab('sources')}
          >
            Источники
          </button>
          <button 
            className={`tab-btn ${activeTab === 'plans' ? 'active' : ''}`}
            onClick={() => setActiveTab('plans')}
          >
            Планы
          </button>
        </div>

        {/* Контент табов */}
        <div className="metrics-tab-content">
          {activeTab === 'funnel' && data?.activation_funnel && (
            <div className="tab-panel">
              <div className="panel-header">
                <h3>Воронка активации новых учителей</h3>
                <span className="period-badge">{data.activation_funnel.period}</span>
              </div>
              <p className="panel-description">
                Показывает путь учителя от регистрации до первой оплаты. 
                Всего зарегистрировалось: <strong>{data.activation_funnel.total_registered}</strong>
              </p>
              <FunnelChart steps={data.activation_funnel.steps} />
              
              {/* Инсайты */}
              <div className="insights-section">
                <h4>Ключевые инсайты</h4>
                <div className="insights-grid">
                  {data.activation_funnel.steps.length > 1 && (
                    <>
                      <div className="insight-card">
                        <div className="insight-value">
                          {formatPercent(data.activation_funnel.steps[1]?.percent || 0)}
                        </div>
                        <div className="insight-label">создают группу</div>
                      </div>
                      <div className="insight-card">
                        <div className="insight-value">
                          {formatPercent(data.activation_funnel.steps[5]?.percent || 0)}
                        </div>
                        <div className="insight-label">конверсия в оплату</div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'mrr' && data?.mrr_waterfall && (
            <div className="tab-panel">
              <div className="panel-header">
                <h3>MRR Waterfall</h3>
                <span className="period-badge">{data.mrr_waterfall.period}</span>
              </div>
              <p className="panel-description">
                Изменение месячной выручки: новые клиенты, expansion, продления и отток.
              </p>
              <WaterfallChart bars={data.mrr_waterfall.bars} />
              
              {/* Summary cards */}
              <div className="mrr-summary">
                <div className="summary-card positive">
                  <div className="summary-value">
                    {formatRub(data.mrr_waterfall.summary?.net_new_mrr || 0)}
                  </div>
                  <div className="summary-label">Net New MRR</div>
                </div>
                <div className="summary-card">
                  <div className="summary-value">
                    {formatPercent(data.mrr_waterfall.summary?.growth_rate || 0)}
                  </div>
                  <div className="summary-label">Рост MRR</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'sources' && (
            <div className="tab-panel">
              <div className="panel-header">
                <h3>Источники трафика</h3>
                <span className="period-badge">Последние 30 дней</span>
              </div>
              <p className="panel-description">
                Анализ эффективности каналов привлечения по регистрациям, активации и выручке.
              </p>
              <SourcesTable sources={data?.sources_breakdown || []} />
            </div>
          )}

          {activeTab === 'plans' && (
            <div className="tab-panel">
              <div className="panel-header">
                <h3>Распределение по планам</h3>
              </div>
              <p className="panel-description">
                Активные подписки по тарифным планам и выручка за период.
              </p>
              <PlansBreakdown plans={data?.plans_breakdown || []} />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="metrics-footer">
          <span className="generated-at">
            Обновлено: {data?.generated_at ? new Date(data.generated_at).toLocaleString('ru-RU') : '—'}
          </span>
          <button className="refresh-btn" onClick={loadData}>
            Обновить
          </button>
        </div>
      </div>
    </div>
  );
};

export default BusinessMetricsDashboard;
