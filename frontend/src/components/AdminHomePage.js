import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { useAuth } from '../auth';
import { getAccessToken } from '../apiService';
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts';
import TeachersManage from './TeachersManage';
import StudentsManage from './StudentsManage';
import StatusMessages from './StatusMessages';
import SystemSettings from './SystemSettings';
import StorageQuotaModal from '../modules/Admin/StorageQuotaModal';
import SubscriptionsModal from '../modules/Admin/SubscriptionsModal';
import SystemErrorsModal from '../modules/Admin/SystemErrorsModal';
import StorageStats from './StorageStats';
import AdminReferrals from '../modules/Admin/AdminReferrals';
import BusinessMetricsDashboard from '../modules/Admin/BusinessMetricsDashboard';
import { Modal, Button } from '../shared/components';
import '../styles/AdminPanel.css';

/* ========== ICONS ========== */
const Icon = {
  revenue: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>,
  users: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>,
  trend: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>,
  video: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="7" width="15" height="10" rx="2"/><path d="m17 9 5-3v12l-5-3"/></svg>,
  storage: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>,
  settings: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>,
  refresh: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>,
  plus: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>,
  alert: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  check: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>,
  analytics: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 21H4.6c-.56 0-.84 0-1.054-.109a1 1 0 01-.437-.437C3 20.24 3 19.96 3 19.4V3"/><path d="M7 14l4-4 4 4 6-6"/></svg>,
};

/* ========== HELPERS ========== */
const fmt = (n) => new Intl.NumberFormat('ru-RU').format(n || 0);
const fmtRub = (n) => `${fmt(n)} ₽`;

/* ========== STYLES ========== */
const styles = {
  page: {
    minHeight: '100vh',
    background: '#0a0a0f',
    color: '#fff',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '20px 32px',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    background: 'rgba(255,255,255,0.02)',
  },
  logo: {
    fontSize: 20,
    fontWeight: 700,
    display: 'flex',
    gap: 6,
  },
  logoAccent: { color: '#6366f1' },
  nav: {
    display: 'flex',
    gap: 4,
    background: 'rgba(255,255,255,0.04)',
    padding: 4,
    borderRadius: 10,
  },
  navBtn: (active) => ({
    padding: '10px 20px',
    background: active ? 'rgba(99,102,241,0.15)' : 'transparent',
    border: 'none',
    borderRadius: 8,
    color: active ? '#818cf8' : 'rgba(255,255,255,0.5)',
    fontSize: 14,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
  }),
  actions: {
    display: 'flex',
    gap: 8,
  },
  iconBtn: {
    width: 40,
    height: 40,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 10,
    color: 'rgba(255,255,255,0.6)',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  main: {
    padding: '24px 32px',
    maxWidth: 1400,
    margin: '0 auto',
  },
  grid: (cols) => ({
    display: 'grid',
    gridTemplateColumns: `repeat(${cols}, 1fr)`,
    gap: 16,
  }),
  card: {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 16,
    padding: 20,
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 13,
    fontWeight: 500,
    color: 'rgba(255,255,255,0.5)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  statValue: {
    fontSize: 32,
    fontWeight: 700,
    color: '#fff',
    lineHeight: 1.2,
  },
  statSub: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.4)',
    marginTop: 4,
  },
  badge: (color) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '4px 10px',
    background: color === 'green' ? 'rgba(34,197,94,0.15)' : color === 'red' ? 'rgba(239,68,68,0.15)' : 'rgba(255,255,255,0.08)',
    color: color === 'green' ? '#22c55e' : color === 'red' ? '#ef4444' : 'rgba(255,255,255,0.6)',
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 500,
  }),
  section: {
    marginTop: 32,
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  sectionHeaderStack: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: 16,
    gap: 16,
  },
  sectionTitleWrap: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: '#fff',
  },
  sectionNote: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.45)',
  },
  actionGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
    gap: 12,
  },
  actionBtn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    padding: '20px 16px',
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 12,
    color: '#fff',
    cursor: 'pointer',
    transition: 'all 0.2s',
    fontSize: 13,
    fontWeight: 500,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
  },
  th: {
    textAlign: 'left',
    padding: '12px 16px',
    color: 'rgba(255,255,255,0.4)',
    fontWeight: 500,
    borderBottom: '1px solid rgba(255,255,255,0.06)',
  },
  td: {
    padding: '12px 16px',
    borderBottom: '1px solid rgba(255,255,255,0.04)',
    color: 'rgba(255,255,255,0.8)',
  },
  progressBar: {
    height: 6,
    background: 'rgba(255,255,255,0.1)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: (pct, color) => ({
    height: '100%',
    width: `${Math.min(pct, 100)}%`,
    background: color || '#6366f1',
    borderRadius: 3,
    transition: 'width 0.5s ease',
  }),
  alertItem: (severity) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '12px 16px',
    background: severity === 'critical' ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)',
    border: `1px solid ${severity === 'critical' ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)'}`,
    borderRadius: 10,
    marginBottom: 8,
  }),
};

/* ========== STAT CARD ========== */
const StatCard = ({ icon, label, value, sub, trend, color = '#6366f1' }) => (
  <div style={styles.card}>
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
      <div style={{ width: 40, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'center', background: `${color}15`, borderRadius: 10, color }}>
        <div style={{ width: 20, height: 20 }}>{icon}</div>
      </div>
      {trend !== undefined && (
        <span style={styles.badge(trend >= 0 ? 'green' : 'red')}>
          {trend >= 0 ? '+' : ''}{trend}%
        </span>
      )}
    </div>
    <div style={{ marginTop: 16 }}>
      <div style={styles.statValue}>{value}</div>
      <div style={styles.statSub}>{label}</div>
      {sub && <div style={{ ...styles.statSub, marginTop: 2 }}>{sub}</div>}
    </div>
  </div>
);

/* ========== MAIN COMPONENT ========== */
const AdminHomePage = () => {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [tab, setTab] = useState('overview');
  const [alerts, setAlerts] = useState([]);
  const [churn, setChurn] = useState(null);
  const [health, setHealth] = useState(null);

  // Profile menu
  const profileButtonRef = useRef(null);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [profileMenuPosition, setProfileMenuPosition] = useState({ top: 64, right: 24 });

  const getAdminInitial = (u) => {
    const first = (u?.first_name || '').trim();
    const last = (u?.last_name || '').trim();
    const email = (u?.email || '').trim();
    const fallback = (first || last || email || 'A').charAt(0);
    return fallback.toUpperCase();
  };

  const updateProfileMenuPosition = useCallback(() => {
    const el = profileButtonRef.current;
    if (!el || typeof window === 'undefined') return;
    const rect = el.getBoundingClientRect();
    const top = Math.round(rect.bottom + 8);
    const right = Math.max(12, Math.round(window.innerWidth - rect.right));
    setProfileMenuPosition({ top, right });
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      setShowProfileMenu(false);
    } finally {
      await logout();
    }
  }, [logout]);

  // Modals
  const [showCreate, setShowCreate] = useState(false);
  const [showTeachers, setShowTeachers] = useState(false);
  const [showStudents, setShowStudents] = useState(false);
  const [showMessages, setShowMessages] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showStorage, setShowStorage] = useState(false);
  const [showSubs, setShowSubs] = useState(false);
  const [showStorageStats, setShowStorageStats] = useState(false);
  const [showReferrals, setShowReferrals] = useState(false);
  const [showBusinessMetrics, setShowBusinessMetrics] = useState(false);
  const [showErrors, setShowErrors] = useState(false);

  // Sub-tabs for overview
  const [overviewTab, setOverviewTab] = useState('moderation');

  // Create user
  const [userRole, setUserRole] = useState('teacher');
  const [userForm, setUserForm] = useState({ email: '', password: '', first_name: '', last_name: '' });
  const [formMsg, setFormMsg] = useState({ type: '', text: '' });

  const load = useCallback(async () => {
    try {
      const token = getAccessToken();
      const headers = { Authorization: `Bearer ${token}` };
      const [overview, alertsRes, churnRes, healthRes] = await Promise.all([
        fetch('/accounts/api/admin/growth/overview/', { headers }).then(r => r.json()),
        fetch('/accounts/api/admin/alerts/', { headers }).then(r => r.json()).catch(() => ({ alerts: [] })),
        fetch('/accounts/api/admin/churn-retention/', { headers }).then(r => r.json()).catch(() => null),
        fetch('/accounts/api/admin/system-health/', { headers }).then(r => r.json()).catch(() => null),
      ]);
      setData(overview);
      setAlerts(alertsRes?.alerts || []);
      setChurn(churnRes);
      setHealth(healthRes);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!showProfileMenu) return;

    const onPointerDown = (e) => {
      const btn = profileButtonRef.current;
      if (btn && (btn === e.target || btn.contains(e.target))) return;
      setShowProfileMenu(false);
    };

    const onKeyDown = (e) => {
      if (e.key === 'Escape') setShowProfileMenu(false);
    };

    const onResize = () => updateProfileMenuPosition();

    window.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('resize', onResize);
    };
  }, [showProfileMenu, updateProfileMenuPosition]);

  const quickAction = async (action) => {
    try {
      const token = getAccessToken();
      const res = await fetch('/accounts/api/admin/quick-actions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ action }),
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        throw new Error(payload?.error || 'Ошибка выполнения действия');
      }
      load();
    } catch (e) {
      alert(e?.message || 'Ошибка выполнения действия');
    }
  };

  const createUser = async (e) => {
    e.preventDefault();
    setFormMsg({ type: '', text: '' });
    try {
      const endpoint = userRole === 'teacher' ? '/accounts/api/admin/create-teacher/' : '/accounts/api/admin/create-student/';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getAccessToken()}` },
        body: JSON.stringify(userForm),
      });
      if (!res.ok) throw new Error((await res.json()).error || 'Ошибка');
      setFormMsg({ type: 'success', text: 'Создано!' });
      setUserForm({ email: '', password: '', first_name: '', last_name: '' });
      setTimeout(() => setShowCreate(false), 1000);
      load();
    } catch (err) {
      setFormMsg({ type: 'error', text: err.message });
    }
  };

  if (loading) {
    return (
      <div style={{ ...styles.page, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>Загрузка...</div>
      </div>
    );
  }

  const period = data?.periods?.find(p => p.key === 'month') || {};
  const chartData = data?.periods?.map(p => ({ name: p.label?.slice(0, 3), revenue: p.revenue || 0, users: p.registrations || 0 })) || [];

  return (
    <div style={styles.page}>
      {/* HEADER */}
      <header style={styles.header}>
        <div style={styles.logo}>
          <span style={styles.logoAccent}>Lectio</span>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Admin</span>
        </div>
        <nav style={styles.nav}>
          <button style={styles.navBtn(tab === 'overview')} onClick={() => setTab('overview')}>Обзор</button>
          <button style={styles.navBtn(tab === 'users')} onClick={() => setTab('users')}>Пользователи</button>
          <button style={styles.navBtn(tab === 'system')} onClick={() => setTab('system')}>Система</button>
        </nav>
        <div style={styles.actions}>
          <button style={styles.iconBtn} onClick={load} title="Обновить">
            <div style={{ width: 18, height: 18 }}>{Icon.refresh}</div>
          </button>
          <button
            type="button"
            ref={profileButtonRef}
            style={styles.profileBtn}
            aria-label="Меню профиля"
            aria-haspopup="true"
            aria-expanded={showProfileMenu}
            onClick={() => {
              if (!showProfileMenu) updateProfileMenuPosition();
              setShowProfileMenu((prev) => !prev);
            }}
          >
            {getAdminInitial(user)}
          </button>

          {showProfileMenu && createPortal(
            <div
              className="animate-modal-enter"
              style={{
                position: 'fixed',
                top: profileMenuPosition.top,
                right: profileMenuPosition.right,
                zIndex: 2147483647,
              }}
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={styles.dropdown}>
                <div style={styles.dropdownHeader}>Администратор</div>
                <Link
                  to="/profile"
                  style={styles.dropdownItemLink}
                  onClick={() => setShowProfileMenu(false)}
                >
                  Профиль
                </Link>
                <button
                  type="button"
                  style={styles.dropdownItemBtn}
                  onClick={handleLogout}
                >
                  Выйти
                </button>
              </div>
            </div>,
            document.body
          )}
        </div>
      </header>

      <main style={styles.main}>
        {/* OVERVIEW TAB */}
        {tab === 'overview' && (
          <>
            {/* SUB-TABS */}
            <div style={{ display: 'flex', gap: 4, background: 'rgba(255,255,255,0.04)', padding: 4, borderRadius: 10, marginBottom: 24, width: 'fit-content' }}>
              <button
                style={{
                  padding: '10px 20px',
                  background: overviewTab === 'moderation' ? 'rgba(99,102,241,0.15)' : 'transparent',
                  border: 'none',
                  borderRadius: 8,
                  color: overviewTab === 'moderation' ? '#818cf8' : 'rgba(255,255,255,0.5)',
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
                onClick={() => setOverviewTab('moderation')}
              >
                Модерация
              </button>
              <button
                style={{
                  padding: '10px 20px',
                  background: overviewTab === 'business' ? 'rgba(99,102,241,0.15)' : 'transparent',
                  border: 'none',
                  borderRadius: 8,
                  color: overviewTab === 'business' ? '#818cf8' : 'rgba(255,255,255,0.5)',
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
                onClick={() => setOverviewTab('business')}
              >
                Бизнес-метрики
              </button>
            </div>

            {/* MODERATION SUB-TAB */}
            {overviewTab === 'moderation' && (
            <div style={{ marginBottom: 24 }}>
              <div style={styles.sectionHeaderStack}>
                <div style={styles.sectionTitleWrap}>
                  <h2 style={styles.sectionTitle}>Модерация</h2>
                  <div style={styles.sectionNote}>Оперативные сигналы и управление пользователями</div>
                </div>
              </div>

              {alerts.length > 0 ? (
                <div>
                  {alerts.slice(0, 3).map((a, i) => (
                    <div key={i} style={styles.alertItem(a.severity)}>
                      <div style={{ width: 20, height: 20, color: a.severity === 'critical' ? '#ef4444' : '#f59e0b' }}>{Icon.alert}</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500, color: '#fff' }}>{a.title}</div>
                        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>{a.user_name}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ ...styles.card, padding: 16, color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
                  Нет активных сигналов
                </div>
              )}

              <div style={{ ...styles.actionGrid, marginTop: 12 }}>
                <button style={styles.actionBtn} onClick={() => setShowMessages(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.alert}</div>
                  Сообщения
                </button>
                <button style={styles.actionBtn} onClick={() => setShowErrors(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.alert}</div>
                  Ошибки
                </button>
                <button style={styles.actionBtn} onClick={() => setShowTeachers(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.users}</div>
                  Учителя
                </button>
                <button style={styles.actionBtn} onClick={() => setShowStudents(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.users}</div>
                  Ученики
                </button>
                <button style={styles.actionBtn} onClick={() => setShowCreate(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.plus}</div>
                  Создать пользователя
                </button>
              </div>
            </div>
            )}

            {/* BUSINESS METRICS SUB-TAB */}
            {overviewTab === 'business' && (
            <>
            <div style={{ marginBottom: 16 }}>
              <div style={styles.sectionHeaderStack}>
                <div style={styles.sectionTitleWrap}>
                  <h2 style={styles.sectionTitle}>Бизнес-метрики</h2>
                  <div style={styles.sectionNote}>Выручка, удержание, конверсия, рост</div>
                </div>
              </div>

              <div style={{ ...styles.actionGrid, marginTop: 12 }}>
                <button style={styles.actionBtn} onClick={() => setShowSubs(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.revenue}</div>
                  Подписки
                </button>
                <button style={styles.actionBtn} onClick={() => setShowStorageStats(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.storage}</div>
                  Хранилище
                </button>
                <button style={styles.actionBtn} onClick={() => setShowStorage(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.settings}</div>
                  Квоты хранилища
                </button>
                <button style={styles.actionBtn} onClick={() => setShowReferrals(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.trend}</div>
                  Рефералы
                </button>
                <button
                  style={styles.actionBtn}
                  onClick={() => {
                    const ok = window.confirm('Пересчитать хранилище для активных подписок? Операция может занять время.');
                    if (ok) quickAction('recalculate_storage');
                  }}
                >
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.refresh}</div>
                  Пересчитать хранилище
                </button>
              </div>
            </div>

            {/* KPI CARDS */}
            <div style={styles.grid(4)}>
              <StatCard icon={Icon.revenue} label="Выручка за месяц" value={fmtRub(period.revenue)} color="#22c55e" />
              <StatCard icon={Icon.users} label="Активные учителя" value={data?.platform?.active_teachers || 0} sub={`из ${data?.platform?.total_teachers || 0}`} color="#6366f1" />
              <StatCard icon={Icon.trend} label="MRR" value={fmtRub(churn?.metrics?.mrr)} color="#8b5cf6" />
              <StatCard icon={Icon.trend} label="LTV" value={fmtRub(churn?.metrics?.ltv)} color="#ec4899" />
            </div>

            {/* CHARTS */}
            <div style={{ ...styles.grid(2), marginTop: 24 }}>
              <div style={styles.card}>
                <div style={styles.cardHeader}>
                  <span style={styles.cardTitle}>Выручка</span>
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={chartData}>
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 12 }} />
                    <YAxis hide />
                    <Tooltip contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: 8 }} labelStyle={{ color: '#fff' }} />
                    <Bar dataKey="revenue" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div style={styles.card}>
                <div style={styles.cardHeader}>
                  <span style={styles.cardTitle}>Регистрации</span>
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="regGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#22c55e" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 12 }} />
                    <YAxis hide />
                    <Tooltip contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: 8 }} labelStyle={{ color: '#fff' }} />
                    <Area type="monotone" dataKey="users" stroke="#22c55e" strokeWidth={2} fill="url(#regGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* METRICS */}
            <div style={{ ...styles.grid(4), marginTop: 24 }}>
              <div style={styles.card}>
                <div style={styles.cardTitle}>Конверсия</div>
                <div style={{ ...styles.statValue, marginTop: 8 }}>{(period.reg_to_pay_cr || 0).toFixed(1)}%</div>
                <div style={styles.statSub}>рег → оплата</div>
              </div>
              <div style={styles.card}>
                <div style={styles.cardTitle}>Churn</div>
                <div style={{ ...styles.statValue, marginTop: 8, color: '#ef4444' }}>{(churn?.metrics?.monthly_churn_rate || 0).toFixed(1)}%</div>
                <div style={styles.statSub}>{churn?.metrics?.churned_this_month || 0} ушло</div>
              </div>
              <div style={styles.card}>
                <div style={styles.cardTitle}>ARPU</div>
                <div style={{ ...styles.statValue, marginTop: 8 }}>{fmtRub(churn?.metrics?.arpu)}</div>
                <div style={styles.statSub}>средний доход</div>
              </div>
              <div style={styles.card}>
                <div style={styles.cardTitle}>Средний чек</div>
                <div style={{ ...styles.statValue, marginTop: 8 }}>{fmtRub(period.avg_check)}</div>
                <div style={styles.statSub}>за период</div>
              </div>
            </div>

            {/* COHORTS */}
            {churn?.cohorts?.length > 0 && (
              <div style={{ ...styles.card, marginTop: 24 }}>
                <div style={styles.cardHeader}>
                  <span style={styles.cardTitle}>Когорты</span>
                </div>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Месяц</th>
                      <th style={{ ...styles.th, textAlign: 'right' }}>Рег.</th>
                      <th style={{ ...styles.th, textAlign: 'right' }}>Конв.</th>
                      <th style={{ ...styles.th, textAlign: 'right' }}>Retention</th>
                    </tr>
                  </thead>
                  <tbody>
                    {churn.cohorts.slice(0, 6).map((c, i) => (
                      <tr key={i}>
                        <td style={styles.td}>{c.month_label || c.month}</td>
                        <td style={{ ...styles.td, textAlign: 'right' }}>{c.registered}</td>
                        <td style={{ ...styles.td, textAlign: 'right' }}>{(c.conversion_rate || 0).toFixed(1)}%</td>
                        <td style={{ ...styles.td, textAlign: 'right', color: c.retention_rate > 50 ? '#22c55e' : '#ef4444' }}>
                          {(c.retention_rate || 0).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            </>
            )}
          </>
        )}

        {/* USERS TAB */}
        {tab === 'users' && (
          <>
            <div style={styles.sectionHeaderStack}>
              <div style={styles.sectionTitleWrap}>
                <h2 style={styles.sectionTitle}>Модерация</h2>
                <div style={styles.sectionNote}>Пользователи, сообщения, ручные проверки</div>
              </div>
            </div>
            <div style={styles.actionGrid}>
              <button style={styles.actionBtn} onClick={() => setShowCreate(true)}>
                <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.plus}</div>
                Создать пользователя
              </button>
              <button style={styles.actionBtn} onClick={() => setShowTeachers(true)}>
                <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.users}</div>
                Учителя
              </button>
              <button style={styles.actionBtn} onClick={() => setShowStudents(true)}>
                <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.users}</div>
                Ученики
              </button>
              <button style={styles.actionBtn} onClick={() => setShowMessages(true)}>
                <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.alert}</div>
                Сообщения
              </button>
              <button style={styles.actionBtn} onClick={() => setShowErrors(true)}>
                <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.alert}</div>
                Ошибки
              </button>
            </div>

            <div style={{ marginTop: 28 }}>
              <div style={styles.sectionHeaderStack}>
                <div style={styles.sectionTitleWrap}>
                  <h2 style={styles.sectionTitle}>Бизнес-метрики</h2>
                  <div style={styles.sectionNote}>Подписки, хранилище и каналы роста</div>
                </div>
              </div>
              <div style={styles.actionGrid}>
                <button style={styles.actionBtn} onClick={() => setShowSubs(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.revenue}</div>
                  Подписки
                </button>
                <button style={styles.actionBtn} onClick={() => setShowStorageStats(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.storage}</div>
                  Хранилище
                </button>
                <button style={styles.actionBtn} onClick={() => setShowReferrals(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.trend}</div>
                  Рефералы
                </button>
                <button style={styles.actionBtn} onClick={() => setShowBusinessMetrics(true)}>
                  <div style={{ width: 24, height: 24, color: '#6366f1' }}>{Icon.analytics}</div>
                  Аналитика
                </button>
              </div>
            </div>

            {/* Stats */}
            <div style={{ ...styles.grid(3), marginTop: 32 }}>
              <div style={styles.card}>
                <div style={styles.cardTitle}>Учителя</div>
                <div style={{ ...styles.statValue, marginTop: 8 }}>{data?.platform?.total_teachers || 0}</div>
                <div style={{ ...styles.progressBar, marginTop: 12 }}>
                  <div style={styles.progressFill((data?.platform?.active_teachers / data?.platform?.total_teachers) * 100 || 0, '#22c55e')} />
                </div>
                <div style={styles.statSub}>{data?.platform?.active_teachers || 0} активных</div>
              </div>
              <div style={styles.card}>
                <div style={styles.cardTitle}>Истекает скоро</div>
                <div style={{ ...styles.statValue, marginTop: 8, color: '#f59e0b' }}>{data?.platform?.expiring_soon || 0}</div>
                <div style={styles.statSub}>подписок</div>
              </div>
              <div style={styles.card}>
                <div style={styles.cardTitle}>Сегодня</div>
                <div style={{ ...styles.statValue, marginTop: 8 }}>{data?.today?.registrations || 0}</div>
                <div style={styles.statSub}>новых регистраций</div>
              </div>
            </div>
          </>
        )}

        {/* SYSTEM TAB */}
        {tab === 'system' && (
          <>
            {/* Health */}
            <div style={styles.sectionHeader}>
              <h2 style={styles.sectionTitle}>Состояние</h2>
              <span style={styles.badge(health?.status === 'healthy' ? 'green' : 'red')}>
                {health?.status === 'healthy' ? 'OK' : health?.status || 'N/A'}
              </span>
            </div>
            <div style={styles.grid(4)}>
              {health?.checks?.map((c, i) => (
                <div key={i} style={{ ...styles.card, borderColor: c.status === 'ok' ? 'rgba(34,197,94,0.3)' : c.status === 'warning' ? 'rgba(245,158,11,0.3)' : 'rgba(239,68,68,0.3)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: c.status === 'ok' ? '#22c55e' : c.status === 'warning' ? '#f59e0b' : '#ef4444' }} />
                    <span style={{ fontSize: 14, fontWeight: 500 }}>{c.name}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 8 }}>{c.message}</div>
                </div>
              ))}
            </div>

            {/* Storage - Real Disk Usage */}
            <div style={{ ...styles.sectionHeader, marginTop: 32 }}>
              <h2 style={styles.sectionTitle}>Хранилище сервера</h2>
            </div>
            <div style={styles.grid(2)}>
              <div style={styles.card}>
                <div style={styles.cardTitle}>Диск сервера</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12, marginBottom: 8 }}>
                  <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: 14 }}>
                    Занято: {(data?.storage?.disk_used_gb || 0).toFixed(1)} ГБ
                  </span>
                  <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 14 }}>
                    Всего: {(data?.storage?.disk_total_gb || 0).toFixed(1)} ГБ
                  </span>
                </div>
                <div style={styles.progressBar}>
                  <div style={styles.progressFill(
                    data?.storage?.disk_total_gb 
                      ? (data.storage.disk_used_gb / data.storage.disk_total_gb) * 100 
                      : 0,
                    (data?.storage?.disk_free_gb || 0) < 5 ? '#ef4444' : '#22c55e'
                  )} />
                </div>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginTop: 8 }}>
                  Свободно: {(data?.storage?.disk_free_gb || 0).toFixed(1)} ГБ
                </div>
              </div>
              <div style={styles.card}>
                <div style={styles.cardTitle}>Медиа-файлы платформы</div>
                <div style={{ ...styles.statValue, marginTop: 12, fontSize: 28 }}>
                  {(data?.storage?.media_used_gb || 0).toFixed(2)} ГБ
                </div>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginTop: 8 }}>
                  Записи уроков, загрузки
                </div>
              </div>
            </div>

            {/* Actions */}
            <div style={{ ...styles.sectionHeader, marginTop: 32 }}>
              <h2 style={styles.sectionTitle}>Действия</h2>
            </div>
            <div style={styles.actionGrid}>
              <button style={styles.actionBtn} onClick={() => quickAction('send_expiring_reminders')}>Напомнить об истекающих</button>
              <button style={styles.actionBtn} onClick={() => setShowSettings(true)}>Настройки</button>
            </div>
          </>
        )}
      </main>

      {/* MODALS */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Создать пользователя" size="medium">
        <form onSubmit={createUser}>
          {formMsg.text && (
            <div style={{ padding: 12, marginBottom: 16, borderRadius: 8, background: formMsg.type === 'error' ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)', color: formMsg.type === 'error' ? '#ef4444' : '#22c55e', fontSize: 13 }}>
              {formMsg.text}
            </div>
          )}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'flex', gap: 16 }}>
              <label><input type="radio" value="teacher" checked={userRole === 'teacher'} onChange={(e) => setUserRole(e.target.value)} /> Учитель</label>
              <label><input type="radio" value="student" checked={userRole === 'student'} onChange={(e) => setUserRole(e.target.value)} /> Ученик</label>
            </label>
          </div>
          <div style={{ display: 'grid', gap: 12 }}>
            <input type="email" placeholder="Email *" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} required style={{ padding: '10px 14px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, background: 'rgba(255,255,255,0.05)', color: '#fff', fontSize: 14 }} />
            <input type="password" placeholder="Пароль *" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} required style={{ padding: '10px 14px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, background: 'rgba(255,255,255,0.05)', color: '#fff', fontSize: 14 }} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <input type="text" placeholder="Имя *" value={userForm.first_name} onChange={(e) => setUserForm({ ...userForm, first_name: e.target.value })} required style={{ padding: '10px 14px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, background: 'rgba(255,255,255,0.05)', color: '#fff', fontSize: 14 }} />
              <input type="text" placeholder="Фамилия *" value={userForm.last_name} onChange={(e) => setUserForm({ ...userForm, last_name: e.target.value })} required style={{ padding: '10px 14px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, background: 'rgba(255,255,255,0.05)', color: '#fff', fontSize: 14 }} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 20, justifyContent: 'flex-end' }}>
            <Button variant="secondary" onClick={() => setShowCreate(false)}>Отмена</Button>
            <Button type="submit">Создать</Button>
          </div>
        </form>
      </Modal>

      {showTeachers && <TeachersManage onClose={() => setShowTeachers(false)} />}
      {showStudents && <StudentsManage onClose={() => setShowStudents(false)} />}
      {showMessages && <StatusMessages onClose={() => setShowMessages(false)} />}
      {showErrors && <SystemErrorsModal onClose={() => setShowErrors(false)} />}
      {showSettings && <SystemSettings onClose={() => setShowSettings(false)} />}
      {showStorage && <StorageQuotaModal onClose={() => setShowStorage(false)} />}
      {showSubs && <SubscriptionsModal onClose={() => setShowSubs(false)} />}
      {showStorageStats && <StorageStats onClose={() => setShowStorageStats(false)} />}
      {showReferrals && <AdminReferrals onClose={() => setShowReferrals(false)} />}
      {showBusinessMetrics && <BusinessMetricsDashboard onClose={() => setShowBusinessMetrics(false)} />}
    </div>
  );
};

export default AdminHomePage;
