import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../auth';
import { getAccessToken } from '../apiService';
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
   SVG ICONS (no emoji)
   ======================================== */
const Icons = {
  users: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
      <circle cx="9" cy="7" r="4"/>
      <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
      <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>
  ),
  userPlus: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
      <circle cx="8.5" cy="7" r="4"/>
      <line x1="20" y1="8" x2="20" y2="14"/>
      <line x1="17" y1="11" x2="23" y2="11"/>
    </svg>
  ),
  wallet: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/>
      <path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/>
      <path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>
    </svg>
  ),
  trendingUp: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
      <polyline points="17 6 23 6 23 12"/>
    </svg>
  ),
  trendingDown: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/>
      <polyline points="17 18 23 18 23 12"/>
    </svg>
  ),
  video: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="15" height="10" rx="2"/>
      <path d="m17 9 5-3v12l-5-3"/>
    </svg>
  ),
  hardDrive: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="12" x2="2" y2="12"/>
      <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
      <line x1="6" y1="16" x2="6.01" y2="16"/>
      <line x1="10" y1="16" x2="10.01" y2="16"/>
    </svg>
  ),
  barChart: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="20" x2="12" y2="10"/>
      <line x1="18" y1="20" x2="18" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="16"/>
    </svg>
  ),
  message: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  ),
  link: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
    </svg>
  ),
  settings: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  ),
  refresh: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/>
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
    </svg>
  ),
  alert: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  ),
  check: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  ),
};

/* ========================================
   HELPER FUNCTIONS
   ======================================== */
const formatRub = (value) => {
  const n = Number(value || 0);
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(n);
};

const formatPercent = (value) => {
  const n = Number(value || 0);
  return n.toFixed(1) + '%';
};

/* ========================================
   KPI CARD COMPONENT
   ======================================== */
const KpiCard = ({ label, value, subValue, icon, color = 'indigo', onClick }) => {
  const colorMap = {
    indigo: { bg: '#EEF2FF', text: '#4F46E5', iconBg: '#E0E7FF' },
    emerald: { bg: '#ECFDF5', text: '#059669', iconBg: '#D1FAE5' },
    amber: { bg: '#FFFBEB', text: '#D97706', iconBg: '#FEF3C7' },
    rose: { bg: '#FFF1F2', text: '#E11D48', iconBg: '#FFE4E6' },
    sky: { bg: '#F0F9FF', text: '#0284C7', iconBg: '#E0F2FE' },
    violet: { bg: '#F5F3FF', text: '#7C3AED', iconBg: '#EDE9FE' },
  };
  const c = colorMap[color] || colorMap.indigo;

  return (
    <div 
      className={`kpi-card ${onClick ? 'kpi-card--clickable' : ''}`}
      onClick={onClick}
      style={{ '--kpi-bg': c.bg, '--kpi-text': c.text, '--kpi-icon-bg': c.iconBg }}
    >
      <div className="kpi-card__icon">{icon}</div>
      <div className="kpi-card__content">
        <div className="kpi-card__label">{label}</div>
        <div className="kpi-card__value">{value}</div>
        {subValue && <div className="kpi-card__sub">{subValue}</div>}
      </div>
    </div>
  );
};

/* ========================================
   FUNNEL COMPONENT
   ======================================== */
const FunnelChart = ({ steps }) => {
  if (!steps || steps.length === 0) return null;
  const maxValue = steps[0]?.value || 1;

  return (
    <div className="funnel-chart">
      {steps.map((step, i) => (
        <div key={step.name} className="funnel-step">
          <div className="funnel-step__label">
            <span className="funnel-step__name">{step.name}</span>
            <span className="funnel-step__value">{step.value}</span>
          </div>
          <div className="funnel-step__bar-container">
            <div 
              className="funnel-step__bar"
              style={{ 
                width: `${(step.value / maxValue) * 100}%`,
                opacity: 1 - (i * 0.15)
              }}
            />
          </div>
          <div className="funnel-step__percent">{step.percent}%</div>
        </div>
      ))}
    </div>
  );
};

/* ========================================
   SOURCES TABLE
   ======================================== */
const SourcesTable = ({ data, type = 'revenue' }) => {
  if (!data || data.length === 0) {
    return <div className="sources-empty">Нет данных об источниках</div>;
  }

  return (
    <div className="sources-table-container">
      <table className="sources-table">
        <thead>
          <tr>
            <th>Источник</th>
            {type === 'revenue' ? (
              <>
                <th className="text-right">Выручка</th>
                <th className="text-right">Платежи</th>
                <th className="text-right">Плательщики</th>
              </>
            ) : (
              <th className="text-right">Регистрации</th>
            )}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={row.source || i}>
              <td>
                <span className="source-badge">{row.source || 'unknown'}</span>
              </td>
              {type === 'revenue' ? (
                <>
                  <td className="text-right font-medium">{formatRub(row.revenue)} ₽</td>
                  <td className="text-right">{row.count || row.payments || 0}</td>
                  <td className="text-right">{row.users || row.unique_payers || 0}</td>
                </>
              ) : (
                <td className="text-right font-medium">{row.count || 0}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

/* ========================================
   RECENT PAYMENTS LIST
   ======================================== */
const RecentPayments = ({ payments }) => {
  if (!payments || payments.length === 0) {
    return <div className="recent-empty">Нет недавних платежей</div>;
  }

  return (
    <div className="recent-payments">
      {payments.map((p) => (
        <div key={p.id} className="recent-payment-item">
          <div className="recent-payment__icon">{Icons.check}</div>
          <div className="recent-payment__info">
            <div className="recent-payment__user">{p.user}</div>
            <div className="recent-payment__date">
              {p.date ? new Date(p.date).toLocaleDateString('ru-RU') : '—'}
            </div>
          </div>
          <div className="recent-payment__amount">+{formatRub(p.amount)} ₽</div>
        </div>
      ))}
    </div>
  );
};

/* ========================================
   PERIOD SELECTOR
   ======================================== */
const PeriodTabs = ({ periods, activeKey, onChange }) => {
  return (
    <div className="period-tabs">
      {periods.map((p) => (
        <button
          key={p.key}
          type="button"
          className={`period-tab ${activeKey === p.key ? 'active' : ''}`}
          onClick={() => onChange(p.key)}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
};

/* ========================================
   MAIN ADMIN DASHBOARD
   ======================================== */
const AdminHomePage = () => {
  const { user } = useAuth();
  
  // Data states
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [activePeriod, setActivePeriod] = useState('month');
  
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
  
  // New dashboard states
  const [activeTab, setActiveTab] = useState('overview');
  const [alerts, setAlerts] = useState({ alerts: [], summary: {} });
  const [churnData, setChurnData] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [activityLog, setActivityLog] = useState([]);
  const [teachersActivity, setTeachersActivity] = useState({ teachers: [], summary: {} });
  const [loadingSection, setLoadingSection] = useState('');
  const [quickActionLoading, setQuickActionLoading] = useState('');
  
  // Create user form
  const [userRole, setUserRole] = useState('teacher');
  const [userForm, setUserForm] = useState({ email: '', password: '', first_name: '', last_name: '', middle_name: '' });
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  /* ======== LOAD DATA ======== */
  const loadDashboard = useCallback(async () => {
    try {
      setError('');
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/growth/overview/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || json.detail || 'Ошибка загрузки');
      setData(json);
    } catch (e) {
      console.error('Dashboard load error:', e);
      setError(e?.message || 'Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAlerts = useCallback(async () => {
    try {
      setLoadingSection('alerts');
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/alerts/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const json = await res.json();
      if (res.ok) setAlerts(json);
    } catch (e) {
      console.error('Alerts load error:', e);
    } finally {
      setLoadingSection('');
    }
  }, []);

  const loadChurnData = useCallback(async () => {
    try {
      setLoadingSection('churn');
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/churn-retention/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const json = await res.json();
      if (res.ok) setChurnData(json);
    } catch (e) {
      console.error('Churn load error:', e);
    } finally {
      setLoadingSection('');
    }
  }, []);

  const loadHealthData = useCallback(async () => {
    try {
      setLoadingSection('health');
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/system-health/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const json = await res.json();
      if (res.ok) setHealthData(json);
    } catch (e) {
      console.error('Health load error:', e);
    } finally {
      setLoadingSection('');
    }
  }, []);

  const loadActivityLog = useCallback(async () => {
    try {
      setLoadingSection('activity');
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/activity-log/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const json = await res.json();
      if (res.ok) setActivityLog(json.logs || []);
    } catch (e) {
      console.error('Activity log load error:', e);
    } finally {
      setLoadingSection('');
    }
  }, []);

  const loadTeachersActivity = useCallback(async () => {
    try {
      setLoadingSection('teachers');
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/teachers-activity/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const json = await res.json();
      if (res.ok) setTeachersActivity(json);
    } catch (e) {
      console.error('Teachers activity load error:', e);
    } finally {
      setLoadingSection('');
    }
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
      if (res.ok) {
        alert(`Действие выполнено: ${JSON.stringify(json)}`);
        loadDashboard();
        loadAlerts();
      } else {
        alert(`Ошибка: ${json.error || 'Неизвестная ошибка'}`);
      }
    } catch (e) {
      alert(`Ошибка: ${e.message}`);
    } finally {
      setQuickActionLoading('');
    }
  };

  useEffect(() => {
    loadDashboard();
    loadAlerts();
    loadHealthData();
  }, [loadDashboard, loadAlerts, loadHealthData]);

  useEffect(() => {
    if (activeTab === 'analytics') {
      loadChurnData();
    } else if (activeTab === 'activity') {
      loadActivityLog();
    } else if (activeTab === 'teachers') {
      loadTeachersActivity();
    }
  }, [activeTab, loadChurnData, loadActivityLog, loadTeachersActivity]);

  /* ======== CREATE USER ======== */
  const handleCreateUser = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');

    if (!userForm.email || !userForm.password || !userForm.first_name || !userForm.last_name) {
      setFormError('Заполните все обязательные поля');
      return;
    }

    try {
      const endpoint = userRole === 'teacher' 
        ? '/accounts/api/admin/create-teacher/'
        : '/accounts/api/admin/create-student/';
      
      const token = getAccessToken();
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(userForm)
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || json.detail || 'Ошибка');
      
      setFormSuccess(`${userRole === 'teacher' ? 'Учитель' : 'Ученик'} создан!`);
      setUserForm({ email: '', password: '', first_name: '', last_name: '', middle_name: '' });
      loadDashboard();
      
      setTimeout(() => {
        setShowCreateUser(false);
        setFormSuccess('');
      }, 1500);
    } catch (err) {
      setFormError(err.message);
    }
  };

  /* ======== CURRENT PERIOD DATA ======== */
  const currentPeriod = data?.periods?.find(p => p.key === activePeriod) || {};

  /* ======== RENDER ======== */
  if (loading) {
    return (
      <div className="admin-dashboard">
        <div className="admin-dashboard__loading">
          <div className="spinner"></div>
          <span>Загрузка панели управления...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      {/* ======== SIDEBAR ======== */}
      <aside className="admin-sidebar">
        <div className="admin-sidebar__logo">
          <span className="logo-primary">Easy</span>
          <span className="logo-secondary">Teaching</span>
        </div>
        
        <nav className="admin-sidebar__nav">
          <button type="button" className="nav-item active">
            {Icons.barChart}
            <span>Dashboard</span>
          </button>
          <button type="button" className="nav-item" onClick={() => setShowTeachersManage(true)}>
            {Icons.users}
            <span>Учителя</span>
          </button>
          <button type="button" className="nav-item" onClick={() => setShowStudentsManage(true)}>
            {Icons.users}
            <span>Ученики</span>
          </button>
          <button type="button" className="nav-item" onClick={() => setShowZoomManager(true)}>
            {Icons.video}
            <span>Zoom Pool</span>
          </button>
          <button type="button" className="nav-item" onClick={() => setShowSubscriptionsModal(true)}>
            {Icons.wallet}
            <span>Подписки</span>
          </button>
          <button type="button" className="nav-item" onClick={() => setShowStorageStats(true)}>
            {Icons.hardDrive}
            <span>Хранилище</span>
          </button>
          <button type="button" className="nav-item" onClick={() => setShowStatusMessages(true)}>
            {Icons.message}
            <span>Сообщения</span>
          </button>
          <button type="button" className="nav-item" onClick={() => setShowReferrals(true)}>
            {Icons.link}
            <span>Рефералы</span>
          </button>
          <button type="button" className="nav-item" onClick={() => setShowSystemSettings(true)}>
            {Icons.settings}
            <span>Настройки</span>
          </button>
        </nav>
      </aside>

      {/* ======== MAIN CONTENT ======== */}
      <main className="admin-main">
        {/* Header */}
        <header className="admin-header">
          <div className="admin-header__left">
            <h1>Панель управления</h1>
            <p>Добро пожаловать, {user?.first_name || 'Администратор'}</p>
          </div>
          <div className="admin-header__right">
            <button type="button" className="btn-icon" onClick={loadDashboard} title="Обновить">
              {Icons.refresh}
            </button>
            <div className="user-avatar">
              {user?.first_name?.charAt(0) || 'A'}
            </div>
          </div>
        </header>

        {error && (
          <div className="dashboard-error">
            {Icons.alert}
            <span>{error}</span>
            <button onClick={loadDashboard}>Повторить</button>
          </div>
        )}

        {/* TODAY KPIs */}
        <section className="dashboard-section">
          <div className="section-header">
            <h2>Сегодня</h2>
            <span className="section-date">{new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })}</span>
          </div>
          <div className="kpi-grid kpi-grid--3">
            <KpiCard
              label="Регистрации"
              value={data?.today?.registrations || 0}
              icon={Icons.userPlus}
              color="indigo"
              onClick={() => setShowTeachersManage(true)}
            />
            <KpiCard
              label="Платежи"
              value={data?.today?.payments || 0}
              icon={Icons.check}
              color="emerald"
              onClick={() => setShowSubscriptionsModal(true)}
            />
            <KpiCard
              label="Выручка"
              value={`${formatRub(data?.today?.revenue || 0)} ₽`}
              icon={Icons.wallet}
              color="amber"
            />
          </div>
        </section>

        {/* PERIOD METRICS */}
        <section className="dashboard-section">
          <div className="section-header">
            <h2>Метрики</h2>
            <PeriodTabs 
              periods={data?.periods || []}
              activeKey={activePeriod}
              onChange={setActivePeriod}
            />
          </div>
          
          <div className="kpi-grid kpi-grid--4">
            <KpiCard
              label="Регистрации"
              value={currentPeriod.registrations || 0}
              subValue={currentPeriod.range_label}
              icon={Icons.userPlus}
              color="indigo"
            />
            <KpiCard
              label="Выручка"
              value={`${formatRub(currentPeriod.revenue || 0)} ₽`}
              subValue={`Средний чек: ${formatRub(currentPeriod.avg_check || 0)} ₽`}
              icon={Icons.wallet}
              color="emerald"
            />
            <KpiCard
              label="Конверсия рег->оплата"
              value={formatPercent(currentPeriod.reg_to_pay_cr || 0)}
              subValue={`${currentPeriod.new_paid_users || 0} оплатили`}
              icon={Icons.trendingUp}
              color="amber"
            />
            <KpiCard
              label="Успешность платежей"
              value={formatPercent(currentPeriod.payment_success_rate || 0)}
              subValue={`${currentPeriod.payments_succeeded || 0} из ${currentPeriod.payments_created || 0}`}
              icon={Icons.check}
              color="sky"
            />
          </div>
        </section>

        {/* TWO COLUMNS: FUNNEL + SOURCES */}
        <div className="dashboard-grid-2">
          {/* Funnel */}
          <section className="dashboard-card">
            <div className="card-header">
              <h3>Воронка (30 дней)</h3>
            </div>
            <div className="card-body">
              <FunnelChart steps={data?.funnel?.steps} />
            </div>
          </section>

          {/* Sources */}
          <section className="dashboard-card">
            <div className="card-header">
              <h3>Источники по выручке</h3>
              <span className="card-period">{data?.sources?.period}</span>
            </div>
            <div className="card-body">
              <SourcesTable data={data?.sources?.revenue} type="revenue" />
            </div>
          </section>
        </div>

        {/* THREE COLUMNS: PLATFORM + ZOOM + RECENT */}
        <div className="dashboard-grid-3">
          {/* Platform Health */}
          <section className="dashboard-card">
            <div className="card-header">
              <h3>Платформа</h3>
            </div>
            <div className="card-body">
              <div className="stat-row">
                <span>Активных учителей</span>
                <strong>{data?.platform?.active_teachers || 0} / {data?.platform?.total_teachers || 0}</strong>
              </div>
              <div className="stat-row">
                <span>Активность</span>
                <strong>{formatPercent(data?.platform?.active_rate || 0)}</strong>
              </div>
              <div className="stat-row highlight-warning">
                <span>Истекает скоро</span>
                <strong>{data?.platform?.expiring_soon || 0}</strong>
              </div>
            </div>
          </section>

          {/* Zoom */}
          <section className="dashboard-card">
            <div className="card-header">
              <h3>Zoom Pool</h3>
            </div>
            <div className="card-body">
              <div className="stat-row">
                <span>Всего аккаунтов</span>
                <strong>{data?.zoom?.total || 0}</strong>
              </div>
              <div className="stat-row">
                <span>Используется</span>
                <strong>{data?.zoom?.in_use || 0}</strong>
              </div>
              <div className="stat-row highlight-success">
                <span>Свободно</span>
                <strong>{data?.zoom?.available || 0}</strong>
              </div>
            </div>
          </section>

          {/* Recent Payments */}
          <section className="dashboard-card">
            <div className="card-header">
              <h3>Последние платежи</h3>
            </div>
            <div className="card-body">
              <RecentPayments payments={data?.recent_payments} />
            </div>
          </section>
        </div>

        {/* QUICK ACTIONS */}
        <section className="dashboard-section">
          <div className="section-header">
            <h2>Быстрые действия</h2>
          </div>
          <div className="quick-actions">
            <button type="button" className="quick-action" onClick={() => setShowCreateUser(true)}>
              {Icons.userPlus}
              <span>Создать пользователя</span>
            </button>
            <button type="button" className="quick-action" onClick={() => setShowTeachersManage(true)}>
              {Icons.users}
              <span>Управление учителями</span>
            </button>
            <button type="button" className="quick-action" onClick={() => setShowZoomStats(true)}>
              {Icons.video}
              <span>Zoom аналитика</span>
            </button>
            <button type="button" className="quick-action" onClick={() => setShowReferrals(true)}>
              {Icons.link}
              <span>Реферальная программа</span>
            </button>
          </div>
        </section>

        {/* ALERTS SECTION */}
        {alerts.summary?.total > 0 && (
          <section className="dashboard-section">
            <div className="section-header">
              <h2>Алерты</h2>
              <span className="alert-badge alert-badge--critical">{alerts.summary?.critical || 0} критичных</span>
            </div>
            <div className="alerts-list">
              {alerts.alerts?.slice(0, 5).map((alert) => (
                <div key={alert.id} className={`alert-item alert-item--${alert.severity}`}>
                  <div className="alert-item__icon">
                    {alert.severity === 'critical' ? Icons.alert : Icons.trendingDown}
                  </div>
                  <div className="alert-item__content">
                    <div className="alert-item__title">{alert.title}</div>
                    <div className="alert-item__message">{alert.message}</div>
                  </div>
                  <div className="alert-item__action">
                    {alert.action === 'contact' && <button onClick={() => window.open(`mailto:${alert.user_email}`)}>Написать</button>}
                    {alert.action === 'renew' && <button onClick={() => setShowSubscriptionsModal(true)}>Продлить</button>}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* SYSTEM HEALTH */}
        {healthData && (
          <section className="dashboard-section">
            <div className="section-header">
              <h2>Состояние системы</h2>
              <span className={`health-status health-status--${healthData.status}`}>
                {healthData.status === 'healthy' ? 'Все работает' : healthData.status === 'degraded' ? 'Есть проблемы' : 'Критично'}
              </span>
            </div>
            <div className="health-checks">
              {healthData.checks?.map((check, i) => (
                <div key={i} className={`health-check health-check--${check.status}`}>
                  <div className="health-check__status">
                    {check.status === 'ok' ? Icons.check : check.status === 'error' ? Icons.alert : Icons.trendingDown}
                  </div>
                  <div className="health-check__name">{check.name}</div>
                  <div className="health-check__message">{check.message}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* CHURN/RETENTION METRICS */}
        {churnData && (
          <section className="dashboard-section">
            <div className="section-header">
              <h2>Retention и Churn</h2>
              <button type="button" className="btn-link" onClick={loadChurnData}>Обновить</button>
            </div>
            <div className="kpi-grid kpi-grid--4">
              <KpiCard
                label="MRR"
                value={`${formatRub(churnData.metrics?.mrr || 0)} ₽`}
                icon={Icons.wallet}
                color="emerald"
              />
              <KpiCard
                label="LTV"
                value={`${formatRub(churnData.metrics?.ltv || 0)} ₽`}
                icon={Icons.trendingUp}
                color="indigo"
              />
              <KpiCard
                label="ARPU"
                value={`${formatRub(churnData.metrics?.arpu || 0)} ₽`}
                icon={Icons.users}
                color="sky"
              />
              <KpiCard
                label="Churn за месяц"
                value={formatPercent(churnData.metrics?.monthly_churn_rate || 0)}
                subValue={`${churnData.metrics?.churned_this_month || 0} ушло`}
                icon={Icons.trendingDown}
                color="rose"
              />
            </div>
            {churnData.cohorts?.length > 0 && (
              <div className="cohorts-table-container">
                <table className="cohorts-table">
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
                        <td className="text-right font-medium">{formatPercent(c.retention_rate)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {/* ADMIN QUICK ACTIONS */}
        <section className="dashboard-section">
          <div className="section-header">
            <h2>Автоматические действия</h2>
          </div>
          <div className="admin-actions">
            <button
              type="button"
              className="admin-action-btn"
              onClick={() => runQuickAction('send_expiring_reminders')}
              disabled={quickActionLoading === 'send_expiring_reminders'}
            >
              {Icons.message}
              <span>Напомнить об истекающих подписках</span>
            </button>
            <button
              type="button"
              className="admin-action-btn"
              onClick={() => runQuickAction('cleanup_stuck_zoom')}
              disabled={quickActionLoading === 'cleanup_stuck_zoom'}
            >
              {Icons.refresh}
              <span>Освободить застрявшие Zoom</span>
            </button>
            <button
              type="button"
              className="admin-action-btn"
              onClick={() => runQuickAction('recalculate_storage')}
              disabled={quickActionLoading === 'recalculate_storage'}
            >
              {Icons.hardDrive}
              <span>Пересчитать хранилище</span>
            </button>
          </div>
        </section>

        {/* ACTIVITY LOG */}
        {activityLog.length > 0 && (
          <section className="dashboard-section">
            <div className="section-header">
              <h2>Последняя активность</h2>
              <button type="button" className="btn-link" onClick={loadActivityLog}>Обновить</button>
            </div>
            <div className="activity-log">
              {activityLog.slice(0, 10).map((log, i) => (
                <div key={i} className="activity-item">
                  <div className="activity-item__icon">
                    {log.type === 'registration' && Icons.userPlus}
                    {log.type === 'payment' && Icons.wallet}
                    {log.type === 'lesson' && Icons.video}
                  </div>
                  <div className="activity-item__content">
                    <div className="activity-item__message">{log.message}</div>
                    <div className="activity-item__meta">
                      <span>{log.user_name}</span>
                      <span>{new Date(log.timestamp).toLocaleString('ru-RU')}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      {/* ======== MODALS ======== */}
      
      {/* Create User */}
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

      {/* Other modals */}
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
