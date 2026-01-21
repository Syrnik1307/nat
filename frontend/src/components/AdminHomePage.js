import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../auth';
import { getAccessToken } from '../apiService';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import TeachersManage from './TeachersManage';
import StudentsManage from './StudentsManage';
import StatusMessages from './StatusMessages';
import ZoomPoolManager from '../modules/core/zoom/ZoomPoolManager';
import ZoomPoolStats from './ZoomPoolStats';
import SystemSettings from './SystemSettings';
import '../styles/AdminPanel.css';
import '../styles/AdminDashboard.css';
import StorageQuotaModal from '../modules/Admin/StorageQuotaModal';
import SubscriptionsModal from '../modules/Admin/SubscriptionsModal';
import StorageStats from './StorageStats';
import AdminReferrals from '../modules/Admin/AdminReferrals';
import { Modal, Button } from '../shared/components';

/* ========================================
   SVG ICONS
   ======================================== */
const Icons = {
  dashboard: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>,
  business: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>,
  moderation: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  system: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>,
  users: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>,
  userPlus: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="17" y1="11" x2="23" y2="11"/></svg>,
  wallet: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/></svg>,
  trendingUp: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>,
  trendingDown: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>,
  video: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="7" width="15" height="10" rx="2"/><path d="m17 9 5-3v12l-5-3"/></svg>,
  hardDrive: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="12" x2="2" y2="12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>,
  message: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>,
  link: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>,
  refresh: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>,
  alert: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  check: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>,
  dollarSign: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>,
  percent: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="19" y1="5" x2="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/></svg>,
  activity: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
};

/* ========================================
   COLORS
   ======================================== */
const COLORS = {
  primary: '#4F46E5',
  success: '#10B981',
  warning: '#F59E0B',
  danger: '#EF4444',
  info: '#3B82F6',
  purple: '#8B5CF6',
  pink: '#EC4899',
};

const CHART_COLORS = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#3B82F6', '#8B5CF6'];

/* ========================================
   HELPERS
   ======================================== */
const formatRub = (value) => new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(value || 0);
const formatPercent = (value) => (Number(value) || 0).toFixed(1) + '%';

/* ========================================
   KPI CARD
   ======================================== */
const KpiCard = ({ label, value, subValue, icon, color = 'primary', trend, onClick }) => {
  const colorStyles = {
    primary: { bg: '#EEF2FF', text: '#4F46E5', iconBg: '#E0E7FF' },
    success: { bg: '#ECFDF5', text: '#059669', iconBg: '#D1FAE5' },
    warning: { bg: '#FFFBEB', text: '#D97706', iconBg: '#FEF3C7' },
    danger: { bg: '#FEF2F2', text: '#DC2626', iconBg: '#FEE2E2' },
    info: { bg: '#EFF6FF', text: '#2563EB', iconBg: '#DBEAFE' },
    purple: { bg: '#F5F3FF', text: '#7C3AED', iconBg: '#EDE9FE' },
  };
  const c = colorStyles[color] || colorStyles.primary;

  return (
    <div className={`kpi-card ${onClick ? 'kpi-card--clickable' : ''}`} onClick={onClick}
         style={{ '--kpi-bg': c.bg, '--kpi-text': c.text, '--kpi-icon-bg': c.iconBg }}>
      <div className="kpi-card__icon">{icon}</div>
      <div className="kpi-card__content">
        <div className="kpi-card__label">{label}</div>
        <div className="kpi-card__value">{value}</div>
        {subValue && <div className="kpi-card__sub">{subValue}</div>}
        {trend !== undefined && (
          <div className={`kpi-card__trend ${trend >= 0 ? 'positive' : 'negative'}`}>
            {trend >= 0 ? Icons.trendingUp : Icons.trendingDown}
            <span>{Math.abs(trend).toFixed(1)}%</span>
          </div>
        )}
      </div>
    </div>
  );
};

/* ========================================
   MINI CHART CARD
   ======================================== */
const MiniChartCard = ({ title, value, chartData, dataKey, color = COLORS.primary }) => (
  <div className="mini-chart-card">
    <div className="mini-chart-card__header">
      <span className="mini-chart-card__title">{title}</span>
      <span className="mini-chart-card__value">{value}</span>
    </div>
    <div className="mini-chart-card__chart">
      <ResponsiveContainer width="100%" height={60}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id={`gradient-${title}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3}/>
              <stop offset="100%" stopColor={color} stopOpacity={0}/>
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey={dataKey} stroke={color} fill={`url(#gradient-${title})`} strokeWidth={2}/>
        </AreaChart>
      </ResponsiveContainer>
    </div>
  </div>
);

/* ========================================
   MAIN TAB NAVIGATION
   ======================================== */
const TabNav = ({ activeTab, onTabChange, alertCount }) => (
  <div className="admin-tabs">
    <button className={`admin-tab ${activeTab === 'business' ? 'active' : ''}`} onClick={() => onTabChange('business')}>
      {Icons.business}
      <span>Бизнес</span>
    </button>
    <button className={`admin-tab ${activeTab === 'moderation' ? 'active' : ''}`} onClick={() => onTabChange('moderation')}>
      {Icons.moderation}
      <span>Модерация</span>
      {alertCount > 0 && <span className="tab-badge">{alertCount}</span>}
    </button>
    <button className={`admin-tab ${activeTab === 'system' ? 'active' : ''}`} onClick={() => onTabChange('system')}>
      {Icons.system}
      <span>Система</span>
    </button>
  </div>
);

/* ========================================
   BUSINESS TAB
   ======================================== */
const BusinessTab = ({ data, churnData, activePeriod, setActivePeriod, loadChurnData }) => {
  const currentPeriod = data?.periods?.find(p => p.key === activePeriod) || {};
  
  // Prepare chart data from periods
  const revenueChartData = data?.periods?.map(p => ({
    name: p.label,
    revenue: p.revenue || 0,
    registrations: p.registrations || 0,
  })) || [];

  // Cohort data for retention chart
  const retentionChartData = churnData?.cohorts?.slice(0, 6).reverse().map(c => ({
    name: c.month?.slice(5) || c.month_label?.slice(0, 3),
    retention: c.retention_rate || 0,
    conversion: c.conversion_rate || 0,
  })) || [];

  // Funnel data
  const funnelData = data?.funnel?.steps?.map((s, i) => ({
    name: s.name,
    value: s.value,
    fill: CHART_COLORS[i % CHART_COLORS.length],
  })) || [];

  return (
    <div className="tab-content business-tab">
      {/* TOP KPIs */}
      <div className="section-header">
        <h2>Ключевые показатели</h2>
        <div className="period-selector">
          {data?.periods?.map(p => (
            <button key={p.key} className={`period-btn ${activePeriod === p.key ? 'active' : ''}`}
                    onClick={() => setActivePeriod(p.key)}>{p.label}</button>
          ))}
        </div>
      </div>

      <div className="kpi-grid kpi-grid--5">
        <KpiCard label="Выручка" value={`${formatRub(currentPeriod.revenue)} ₽`} 
                 icon={Icons.dollarSign} color="success" subValue={currentPeriod.range_label} />
        <KpiCard label="MRR" value={`${formatRub(churnData?.metrics?.mrr)} ₽`}
                 icon={Icons.wallet} color="primary" />
        <KpiCard label="LTV" value={`${formatRub(churnData?.metrics?.ltv)} ₽`}
                 icon={Icons.trendingUp} color="purple" />
        <KpiCard label="ARPU" value={`${formatRub(churnData?.metrics?.arpu)} ₽`}
                 icon={Icons.users} color="info" />
        <KpiCard label="Churn" value={formatPercent(churnData?.metrics?.monthly_churn_rate)}
                 icon={Icons.trendingDown} color="danger" subValue={`${churnData?.metrics?.churned_this_month || 0} ушло`} />
      </div>

      {/* REVENUE CHART */}
      <div className="dashboard-grid-2" style={{ marginTop: 24 }}>
        <div className="chart-card">
          <div className="chart-card__header">
            <h3>Выручка по периодам</h3>
          </div>
          <div className="chart-card__body">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={revenueChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                <Tooltip formatter={(v) => [`${formatRub(v)} ₽`, 'Выручка']} />
                <Bar dataKey="revenue" fill={COLORS.primary} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-card__header">
            <h3>Retention по когортам</h3>
            <button className="btn-link" onClick={loadChurnData}>Обновить</button>
          </div>
          <div className="chart-card__body">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={retentionChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                <Tooltip formatter={(v) => [`${v.toFixed(1)}%`]} />
                <Line type="monotone" dataKey="retention" stroke={COLORS.success} strokeWidth={2} dot={{ fill: COLORS.success }} name="Retention" />
                <Line type="monotone" dataKey="conversion" stroke={COLORS.primary} strokeWidth={2} dot={{ fill: COLORS.primary }} name="Конверсия" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* CONVERSION METRICS */}
      <div className="section-header" style={{ marginTop: 32 }}>
        <h2>Конверсии</h2>
      </div>

      <div className="kpi-grid kpi-grid--4">
        <KpiCard label="Регистрации" value={currentPeriod.registrations || 0}
                 icon={Icons.userPlus} color="primary" />
        <KpiCard label="Рег → Оплата" value={formatPercent(currentPeriod.reg_to_pay_cr)}
                 icon={Icons.percent} color="success" subValue={`${currentPeriod.new_paid_users || 0} оплатили`} />
        <KpiCard label="Успешность платежей" value={formatPercent(currentPeriod.payment_success_rate)}
                 icon={Icons.check} color="info" subValue={`${currentPeriod.payments_succeeded || 0} / ${currentPeriod.payments_created || 0}`} />
        <KpiCard label="Средний чек" value={`${formatRub(currentPeriod.avg_check)} ₽`}
                 icon={Icons.wallet} color="purple" />
      </div>

      {/* FUNNEL + SOURCES */}
      <div className="dashboard-grid-2" style={{ marginTop: 24 }}>
        <div className="chart-card">
          <div className="chart-card__header">
            <h3>Воронка (30 дней)</h3>
          </div>
          <div className="chart-card__body">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={funnelData} layout="vertical">
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={100} />
                <Tooltip formatter={(v) => [v, 'Количество']} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {funnelData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-card__header">
            <h3>Источники трафика</h3>
          </div>
          <div className="chart-card__body">
            {data?.sources?.revenue?.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={data.sources.revenue.slice(0, 5)} dataKey="revenue" nameKey="source" cx="50%" cy="50%"
                       innerRadius={50} outerRadius={80} paddingAngle={2}>
                    {data.sources.revenue.slice(0, 5).map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => [`${formatRub(v)} ₽`]} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">Нет данных</div>
            )}
          </div>
        </div>
      </div>

      {/* COHORT TABLE */}
      {churnData?.cohorts?.length > 0 && (
        <div className="chart-card" style={{ marginTop: 24 }}>
          <div className="chart-card__header">
            <h3>Когортный анализ</h3>
          </div>
          <div className="chart-card__body">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Когорта</th>
                  <th className="text-right">Регистрации</th>
                  <th className="text-right">Оплатили</th>
                  <th className="text-right">Конверсия</th>
                  <th className="text-right">Активны</th>
                  <th className="text-right">Retention</th>
                </tr>
              </thead>
              <tbody>
                {churnData.cohorts.map((c, i) => (
                  <tr key={i}>
                    <td>{c.month_label || c.month}</td>
                    <td className="text-right">{c.registered}</td>
                    <td className="text-right">{c.converted}</td>
                    <td className="text-right">{formatPercent(c.conversion_rate)}</td>
                    <td className="text-right">{c.still_active}</td>
                    <td className="text-right font-bold" style={{ color: c.retention_rate > 50 ? COLORS.success : COLORS.danger }}>
                      {formatPercent(c.retention_rate)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

/* ========================================
   MODERATION TAB
   ======================================== */
const ModerationTab = ({ 
  data, alerts, activityLog, 
  setShowTeachersManage, setShowStudentsManage, setShowSubscriptionsModal,
  setShowStorageStats, setShowStatusMessages, setShowReferrals,
  setShowCreateUser, loadActivityLog
}) => (
  <div className="tab-content moderation-tab">
    {/* ALERTS */}
    {alerts.summary?.total > 0 && (
      <>
        <div className="section-header">
          <h2>Требуют внимания</h2>
          <span className="alert-count">{alerts.summary?.critical || 0} критичных, {alerts.summary?.warning || 0} предупреждений</span>
        </div>
        <div className="alerts-grid">
          {alerts.alerts?.slice(0, 6).map((alert) => (
            <div key={alert.id} className={`alert-card alert-card--${alert.severity}`}>
              <div className="alert-card__icon">
                {alert.severity === 'critical' ? Icons.alert : Icons.trendingDown}
              </div>
              <div className="alert-card__content">
                <div className="alert-card__title">{alert.title}</div>
                <div className="alert-card__user">{alert.user_name}</div>
              </div>
              <button className="alert-card__action" onClick={() => window.open(`mailto:${alert.user_email}`)}>
                Написать
              </button>
            </div>
          ))}
        </div>
      </>
    )}

    {/* QUICK STATS */}
    <div className="section-header" style={{ marginTop: alerts.summary?.total > 0 ? 32 : 0 }}>
      <h2>Статистика платформы</h2>
    </div>

    <div className="kpi-grid kpi-grid--4">
      <KpiCard label="Всего учителей" value={data?.platform?.total_teachers || 0}
               icon={Icons.users} color="primary" onClick={() => setShowTeachersManage(true)} />
      <KpiCard label="Активные подписки" value={data?.platform?.active_teachers || 0}
               icon={Icons.check} color="success" subValue={formatPercent(data?.platform?.active_rate)} />
      <KpiCard label="Истекает скоро" value={data?.platform?.expiring_soon || 0}
               icon={Icons.alert} color="warning" onClick={() => setShowSubscriptionsModal(true)} />
      <KpiCard label="Сегодня регистраций" value={data?.today?.registrations || 0}
               icon={Icons.userPlus} color="info" />
    </div>

    {/* MANAGEMENT ACTIONS */}
    <div className="section-header" style={{ marginTop: 32 }}>
      <h2>Управление</h2>
    </div>

    <div className="action-grid">
      <button className="action-card" onClick={() => setShowCreateUser(true)}>
        {Icons.userPlus}
        <span>Создать пользователя</span>
      </button>
      <button className="action-card" onClick={() => setShowTeachersManage(true)}>
        {Icons.users}
        <span>Управление учителями</span>
      </button>
      <button className="action-card" onClick={() => setShowStudentsManage(true)}>
        {Icons.users}
        <span>Управление учениками</span>
      </button>
      <button className="action-card" onClick={() => setShowSubscriptionsModal(true)}>
        {Icons.wallet}
        <span>Подписки</span>
      </button>
      <button className="action-card" onClick={() => setShowStorageStats(true)}>
        {Icons.hardDrive}
        <span>Хранилище</span>
      </button>
      <button className="action-card" onClick={() => setShowStatusMessages(true)}>
        {Icons.message}
        <span>Сообщения</span>
      </button>
      <button className="action-card" onClick={() => setShowReferrals(true)}>
        {Icons.link}
        <span>Рефералы</span>
      </button>
    </div>

    {/* ACTIVITY LOG */}
    <div className="section-header" style={{ marginTop: 32 }}>
      <h2>Последняя активность</h2>
      <button className="btn-link" onClick={loadActivityLog}>Обновить</button>
    </div>

    <div className="activity-feed">
      {activityLog.slice(0, 8).map((log, i) => (
        <div key={i} className="activity-item">
          <div className={`activity-item__icon activity-item__icon--${log.type}`}>
            {log.type === 'registration' && Icons.userPlus}
            {log.type === 'payment' && Icons.wallet}
            {log.type === 'lesson' && Icons.video}
          </div>
          <div className="activity-item__content">
            <span className="activity-item__message">{log.message}</span>
            <span className="activity-item__meta">{log.user_name} • {new Date(log.timestamp).toLocaleString('ru-RU')}</span>
          </div>
        </div>
      ))}
      {activityLog.length === 0 && <div className="empty-state">Нет активности</div>}
    </div>
  </div>
);

/* ========================================
   SYSTEM TAB
   ======================================== */
const SystemTab = ({ 
  data, healthData, 
  setShowZoomManager, setShowSystemSettings,
  runQuickAction, quickActionLoading, loadHealthData
}) => (
  <div className="tab-content system-tab">
    {/* SYSTEM HEALTH */}
    <div className="section-header">
      <h2>Состояние системы</h2>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span className={`health-badge health-badge--${healthData?.status || 'unknown'}`}>
          {healthData?.status === 'healthy' ? 'Все работает' : healthData?.status === 'degraded' ? 'Есть проблемы' : 'Проверка...'}
        </span>
        <button className="btn-link" onClick={loadHealthData}>Обновить</button>
      </div>
    </div>

    <div className="health-grid">
      {healthData?.checks?.map((check, i) => (
        <div key={i} className={`health-card health-card--${check.status}`}>
          <div className="health-card__status">
            {check.status === 'ok' && Icons.check}
            {check.status === 'warning' && Icons.alert}
            {check.status === 'error' && Icons.alert}
            {check.status === 'info' && Icons.activity}
          </div>
          <div className="health-card__info">
            <div className="health-card__name">{check.name}</div>
            <div className="health-card__message">{check.message}</div>
          </div>
        </div>
      ))}
    </div>

    {/* ZOOM POOL */}
    <div className="section-header" style={{ marginTop: 32 }}>
      <h2>Zoom Pool</h2>
    </div>

    <div className="kpi-grid kpi-grid--3">
      <KpiCard label="Всего аккаунтов" value={data?.zoom?.total || 0} icon={Icons.video} color="primary" />
      <KpiCard label="Используется" value={data?.zoom?.in_use || 0} icon={Icons.activity} color="warning" />
      <KpiCard label="Свободно" value={data?.zoom?.available || 0} icon={Icons.check} color="success" />
    </div>

    {/* STORAGE */}
    <div className="section-header" style={{ marginTop: 32 }}>
      <h2>Хранилище</h2>
    </div>

    <div className="storage-bar-container">
      <div className="storage-bar">
        <div className="storage-bar__fill" style={{ 
          width: `${data?.storage?.total_gb > 0 ? (data.storage.used_gb / data.storage.total_gb) * 100 : 0}%` 
        }} />
      </div>
      <div className="storage-bar__labels">
        <span>{(data?.storage?.used_gb || 0).toFixed(1)} ГБ использовано</span>
        <span>{(data?.storage?.total_gb || 0).toFixed(1)} ГБ всего</span>
      </div>
    </div>

    {/* QUICK ACTIONS */}
    <div className="section-header" style={{ marginTop: 32 }}>
      <h2>Служебные действия</h2>
    </div>

    <div className="admin-actions-grid">
      <button className="admin-action" onClick={() => runQuickAction('send_expiring_reminders')}
              disabled={quickActionLoading === 'send_expiring_reminders'}>
        {Icons.message}
        <span>Напомнить об истекающих подписках</span>
      </button>
      <button className="admin-action" onClick={() => runQuickAction('cleanup_stuck_zoom')}
              disabled={quickActionLoading === 'cleanup_stuck_zoom'}>
        {Icons.refresh}
        <span>Освободить застрявшие Zoom</span>
      </button>
      <button className="admin-action" onClick={() => runQuickAction('recalculate_storage')}
              disabled={quickActionLoading === 'recalculate_storage'}>
        {Icons.hardDrive}
        <span>Пересчитать хранилище</span>
      </button>
      <button className="admin-action" onClick={() => setShowZoomManager(true)}>
        {Icons.video}
        <span>Управление Zoom Pool</span>
      </button>
      <button className="admin-action" onClick={() => setShowSystemSettings(true)}>
        {Icons.system}
        <span>Настройки системы</span>
      </button>
    </div>
  </div>
);

/* ========================================
   MAIN COMPONENT
   ======================================== */
const AdminHomePage = () => {
  const { user } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('business');
  const [activePeriod, setActivePeriod] = useState('month');
  
  // Extended data
  const [alerts, setAlerts] = useState({ alerts: [], summary: {} });
  const [churnData, setChurnData] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [activityLog, setActivityLog] = useState([]);
  const [quickActionLoading, setQuickActionLoading] = useState('');
  
  // Modal states
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [showTeachersManage, setShowTeachersManage] = useState(false);
  const [showStudentsManage, setShowStudentsManage] = useState(false);
  const [showStatusMessages, setShowStatusMessages] = useState(false);
  const [showZoomManager, setShowZoomManager] = useState(false);
  const [showZoomStats, setShowZoomStats] = useState(false);
  const [showSystemSettings, setShowSystemSettings] = useState(false);
  const [showStorageModal, setShowStorageModal] = useState(false);
  const [showSubscriptionsModal, setShowSubscriptionsModal] = useState(false);
  const [showStorageStats, setShowStorageStats] = useState(false);
  const [showReferrals, setShowReferrals] = useState(false);
  
  // Create user form
  const [userRole, setUserRole] = useState('teacher');
  const [userForm, setUserForm] = useState({ email: '', password: '', first_name: '', last_name: '', middle_name: '' });
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  /* ======== LOADERS ======== */
  const loadDashboard = useCallback(async () => {
    try {
      setError('');
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/growth/overview/', { headers: { 'Authorization': `Bearer ${token}` }});
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Ошибка');
      setData(json);
    } catch (e) {
      setError(e?.message || 'Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAlerts = useCallback(async () => {
    try {
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/alerts/', { headers: { 'Authorization': `Bearer ${token}` }});
      const json = await res.json();
      if (res.ok) setAlerts(json);
    } catch (e) { console.error(e); }
  }, []);

  const loadChurnData = useCallback(async () => {
    try {
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/churn-retention/', { headers: { 'Authorization': `Bearer ${token}` }});
      const json = await res.json();
      if (res.ok) setChurnData(json);
    } catch (e) { console.error(e); }
  }, []);

  const loadHealthData = useCallback(async () => {
    try {
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/system-health/', { headers: { 'Authorization': `Bearer ${token}` }});
      const json = await res.json();
      if (res.ok) setHealthData(json);
    } catch (e) { console.error(e); }
  }, []);

  const loadActivityLog = useCallback(async () => {
    try {
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/activity-log/', { headers: { 'Authorization': `Bearer ${token}` }});
      const json = await res.json();
      if (res.ok) setActivityLog(json.logs || []);
    } catch (e) { console.error(e); }
  }, []);

  const runQuickAction = async (action) => {
    try {
      setQuickActionLoading(action);
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/quick-actions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ action })
      });
      const json = await res.json();
      alert(res.ok ? `Выполнено: ${JSON.stringify(json)}` : `Ошибка: ${json.error}`);
      if (res.ok) { loadDashboard(); loadAlerts(); }
    } catch (e) {
      alert(`Ошибка: ${e.message}`);
    } finally {
      setQuickActionLoading('');
    }
  };

  useEffect(() => {
    loadDashboard();
    loadAlerts();
    loadChurnData();
    loadHealthData();
    loadActivityLog();
  }, [loadDashboard, loadAlerts, loadChurnData, loadHealthData, loadActivityLog]);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');
    if (!userForm.email || !userForm.password || !userForm.first_name || !userForm.last_name) {
      setFormError('Заполните все обязательные поля');
      return;
    }
    try {
      const endpoint = userRole === 'teacher' ? '/accounts/api/admin/create-teacher/' : '/accounts/api/admin/create-student/';
      const token = getAccessToken();
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(userForm)
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Ошибка');
      setFormSuccess(`${userRole === 'teacher' ? 'Учитель' : 'Ученик'} создан!`);
      setUserForm({ email: '', password: '', first_name: '', last_name: '', middle_name: '' });
      loadDashboard();
      setTimeout(() => { setShowCreateUser(false); setFormSuccess(''); }, 1500);
    } catch (err) {
      setFormError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="admin-dashboard">
        <div className="admin-dashboard__loading">
          <div className="spinner"></div>
          <span>Загрузка...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      {/* HEADER */}
      <header className="admin-header-new">
        <div className="admin-header__brand">
          <span className="brand-primary">Easy</span>
          <span className="brand-secondary">Teaching</span>
          <span className="brand-admin">Admin</span>
        </div>
        
        <TabNav activeTab={activeTab} onTabChange={setActiveTab} alertCount={alerts.summary?.critical || 0} />
        
        <div className="admin-header__actions">
          <button className="btn-icon" onClick={() => { loadDashboard(); loadAlerts(); loadChurnData(); }} title="Обновить">
            {Icons.refresh}
          </button>
          <div className="user-badge">
            {user?.first_name?.charAt(0) || 'A'}
          </div>
        </div>
      </header>

      {/* MAIN */}
      <main className="admin-main-new">
        {error && (
          <div className="error-banner">
            {Icons.alert}
            <span>{error}</span>
            <button onClick={loadDashboard}>Повторить</button>
          </div>
        )}

        {/* TODAY SUMMARY - всегда показываем */}
        <div className="today-summary">
          <div className="today-summary__item">
            <span className="today-summary__label">Сегодня</span>
            <span className="today-summary__value">{data?.today?.registrations || 0} рег.</span>
          </div>
          <div className="today-summary__divider" />
          <div className="today-summary__item">
            <span className="today-summary__value">{data?.today?.payments || 0} платежей</span>
          </div>
          <div className="today-summary__divider" />
          <div className="today-summary__item">
            <span className="today-summary__value">{formatRub(data?.today?.revenue)} ₽</span>
          </div>
        </div>

        {/* TAB CONTENT */}
        {activeTab === 'business' && (
          <BusinessTab 
            data={data} 
            churnData={churnData}
            activePeriod={activePeriod}
            setActivePeriod={setActivePeriod}
            loadChurnData={loadChurnData}
          />
        )}
        
        {activeTab === 'moderation' && (
          <ModerationTab
            data={data}
            alerts={alerts}
            activityLog={activityLog}
            setShowTeachersManage={setShowTeachersManage}
            setShowStudentsManage={setShowStudentsManage}
            setShowSubscriptionsModal={setShowSubscriptionsModal}
            setShowStorageStats={setShowStorageStats}
            setShowStatusMessages={setShowStatusMessages}
            setShowReferrals={setShowReferrals}
            setShowCreateUser={setShowCreateUser}
            loadActivityLog={loadActivityLog}
          />
        )}
        
        {activeTab === 'system' && (
          <SystemTab
            data={data}
            healthData={healthData}
            setShowZoomManager={setShowZoomManager}
            setShowSystemSettings={setShowSystemSettings}
            runQuickAction={runQuickAction}
            quickActionLoading={quickActionLoading}
            loadHealthData={loadHealthData}
          />
        )}
      </main>

      {/* MODALS */}
      <Modal isOpen={showCreateUser} onClose={() => setShowCreateUser(false)} title="Создать пользователя" size="medium">
        <form onSubmit={handleCreateUser} className="create-user-form">
          {formError && <div className="form-error">{formError}</div>}
          {formSuccess && <div className="form-success">{formSuccess}</div>}
          <div className="form-group">
            <label>Тип пользователя</label>
            <div className="radio-group">
              <label><input type="radio" name="role" value="teacher" checked={userRole === 'teacher'} onChange={(e) => setUserRole(e.target.value)} /> Учитель</label>
              <label><input type="radio" name="role" value="student" checked={userRole === 'student'} onChange={(e) => setUserRole(e.target.value)} /> Ученик</label>
            </div>
          </div>
          <div className="form-group">
            <label>Email *</label>
            <input type="email" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Пароль *</label>
            <input type="password" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} required />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Имя *</label>
              <input type="text" value={userForm.first_name} onChange={(e) => setUserForm({ ...userForm, first_name: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Фамилия *</label>
              <input type="text" value={userForm.last_name} onChange={(e) => setUserForm({ ...userForm, last_name: e.target.value })} required />
            </div>
          </div>
          <div className="form-group">
            <label>Отчество</label>
            <input type="text" value={userForm.middle_name} onChange={(e) => setUserForm({ ...userForm, middle_name: e.target.value })} />
          </div>
          <div className="form-actions">
            <Button type="button" variant="secondary" onClick={() => setShowCreateUser(false)}>Отмена</Button>
            <Button type="submit">{userRole === 'teacher' ? 'Создать учителя' : 'Создать ученика'}</Button>
          </div>
        </form>
      </Modal>

      {showTeachersManage && <TeachersManage onClose={() => setShowTeachersManage(false)} />}
      {showStudentsManage && <StudentsManage onClose={() => setShowStudentsManage(false)} />}
      {showStatusMessages && <StatusMessages onClose={() => setShowStatusMessages(false)} />}
      {showSystemSettings && <SystemSettings onClose={() => setShowSystemSettings(false)} />}
      {showStorageModal && <StorageQuotaModal onClose={() => setShowStorageModal(false)} />}
      {showStorageStats && <StorageStats onClose={() => setShowStorageStats(false)} />}
      {showSubscriptionsModal && <SubscriptionsModal onClose={() => setShowSubscriptionsModal(false)} />}
      {showReferrals && <AdminReferrals onClose={() => setShowReferrals(false)} />}
      
      <Modal isOpen={showZoomManager} onClose={() => setShowZoomManager(false)} title="Zoom Pool Manager" size="large">
        <ZoomPoolManager onClose={() => setShowZoomManager(false)} />
      </Modal>
      
      <Modal isOpen={showZoomStats} onClose={() => setShowZoomStats(false)} title="Аналитика Zoom Pool" size="large">
        <ZoomPoolStats />
      </Modal>
    </div>
  );
};

export default AdminHomePage;
