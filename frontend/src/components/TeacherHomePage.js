import React, { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { getTeacherStatsSummary, getLessons, getGroups, startQuickLesson } from '../apiService';
import { Link } from 'react-router-dom';
import SubscriptionBanner from './SubscriptionBanner';

/* =====================================================
   TEACHER HOME PAGE - Premium Glass & Gradient Design
   Design System: Inter font, Purple-Blue gradients
   ===================================================== */

const TeacherHomePage = () => {
  const { user, logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const now = new Date();
        const in30 = new Date();
        in30.setDate(now.getDate() + 30);

        const [statsRes, lessonsRes, groupsRes] = await Promise.all([
          getTeacherStatsSummary(),
          getLessons({ start: now.toISOString(), end: in30.toISOString(), include_recurring: true }),
          getGroups(),
        ]);

        setStats(statsRes.data);
        const lessonList = Array.isArray(lessonsRes.data) ? lessonsRes.data : lessonsRes.data.results || [];
        setLessons(lessonList.slice(0, 5));
        setGroups(Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || []);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const handleQuickStart = async () => {
    if (starting) return;
    setStarting(true);
    try {
      const res = await startQuickLesson();
      if (res.data?.zoom_start_url) {
        window.open(res.data.zoom_start_url, '_blank');
      } else if (res.data?.start_url) {
        window.open(res.data.start_url, '_blank');
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Ошибка запуска урока');
    } finally {
      setStarting(false);
    }
  };

  const formatTime = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  };

  // Generate consistent color for group based on name
  const getGroupColor = (name) => {
    const colors = [
      { bg: 'linear-gradient(135deg, #6366f1, #8b5cf6)', icon: '📐' },
      { bg: 'linear-gradient(135deg, #3b82f6, #0ea5e9)', icon: '📚' },
      { bg: 'linear-gradient(135deg, #10b981, #14b8a6)', icon: '🧪' },
      { bg: 'linear-gradient(135deg, #f59e0b, #f97316)', icon: '🎨' },
      { bg: 'linear-gradient(135deg, #ec4899, #f43f5e)', icon: '🎭' },
      { bg: 'linear-gradient(135deg, #8b5cf6, #a855f7)', icon: '💻' },
    ];
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  if (loading) {
    return (
      <div className="teacher-dashboard">
        <style>{globalStyles}</style>
        <div className="dashboard-loading">
          <div className="loading-spinner"></div>
          <p>Загрузка данных...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="teacher-dashboard">
      <style>{globalStyles}</style>
      
      {/* Subscription Banner */}
      <SubscriptionBanner />

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* LEFT COLUMN */}
        <div className="dashboard-left">
          {/* Hero: Quick Lesson */}
          <div className="hero-card">
            <div className="hero-decoration"></div>
            <div className="hero-decoration-2"></div>
            <div className="hero-content">
              <div className="hero-icon">🚀</div>
              <h2 className="hero-title">Начать урок</h2>
              <p className="hero-subtitle">Мгновенный запуск Zoom-конференции для вашего следующего занятия</p>
              <button
                className="hero-button"
                onClick={handleQuickStart}
                disabled={starting}
              >
                <span className="hero-button-icon">📹</span>
                {starting ? 'Запуск...' : 'Запустить Zoom'}
              </button>
            </div>
          </div>

          {/* Schedule */}
          <div className="section-card">
            <div className="section-header">
              <h3 className="section-title">
                <span className="section-icon">📅</span>
                Расписание
              </h3>
              <Link to="/recurring-lessons/manage" className="section-link">
                Все занятия <span className="arrow">→</span>
              </Link>
            </div>
            <div className="schedule-list">
              {lessons.length > 0 ? (
                lessons.map((lesson) => (
                  <div key={lesson.id} className="schedule-item">
                    <div className="schedule-time">
                      <span className="schedule-date">{formatDate(lesson.start_time)}</span>
                      <span className="schedule-hour">{formatTime(lesson.start_time)}</span>
                    </div>
                    <div className="schedule-info">
                      <div className="schedule-title">{lesson.title || 'Без названия'}</div>
                      <div className="schedule-group">{lesson.group_name || `Группа #${lesson.group}`}</div>
                    </div>
                    <div className="schedule-status">
                      {lesson.zoom_start_url ? (
                        <span className="status-active">● Активен</span>
                      ) : (
                        <span className="status-pending">○ Ожидает</span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-state">
                  <span className="empty-icon">📭</span>
                  <p>Нет предстоящих занятий</p>
                </div>
              )}
            </div>
          </div>

          {/* Groups - Premium Cards */}
          <div className="section-card">
            <div className="section-header">
              <h3 className="section-title">
                <span className="section-icon">👥</span>
                Группы
              </h3>
              <Link to="/groups/manage" className="section-link">
                Управление <span className="arrow">→</span>
              </Link>
            </div>
            <div className="groups-grid">
              {groups.length > 0 ? (
                groups.map((group) => {
                  const colorInfo = getGroupColor(group.name);
                  return (
                    <Link
                      key={group.id}
                      to={`/attendance/${group.id}`}
                      className="group-card"
                    >
                      <div className="group-cover" style={{ background: colorInfo.bg }}>
                        <span className="group-icon">{colorInfo.icon}</span>
                      </div>
                      <div className="group-content">
                        <h4 className="group-name">{group.name}</h4>
                        <div className="group-meta">
                          <span className="group-students">
                            <span className="meta-icon">👤</span>
                            {group.students?.length || 0} учеников
                          </span>
                        </div>
                      </div>
                      <div className="group-arrow">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M9 18l6-6-6-6"/>
                        </svg>
                      </div>
                    </Link>
                  );
                })
              ) : (
                <div className="empty-state full-width">
                  <span className="empty-icon">📁</span>
                  <p>Нет групп</p>
                  <Link to="/groups/manage" className="empty-action">Создать группу</Link>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="dashboard-right">
          {/* Statistics */}
          <div className="stats-card">
            <h3 className="stats-title">
              <span className="section-icon">📊</span>
              Статистика
            </h3>
            <div className="stats-grid">
              <div className="stat-tile">
                <div className="stat-value">{stats?.total_lessons || 0}</div>
                <div className="stat-label">уроков</div>
              </div>
              <div className="stat-tile">
                <div className="stat-value">{stats?.total_students || 0}</div>
                <div className="stat-label">учеников</div>
              </div>
              <div className="stat-tile">
                <div className="stat-value">{stats?.recorded_lessons || 0}</div>
                <div className="stat-label">записей</div>
              </div>
              <div className="stat-tile">
                <div className="stat-value">{stats?.recording_ratio_percent || 0}%</div>
                <div className="stat-label">с записью</div>
              </div>
            </div>
          </div>

          {/* Progress */}
          <div className="progress-card">
            <h3 className="progress-title">
              <span className="section-icon">🎯</span>
              Прогресс
            </h3>
            
            <div className="progress-item">
              <div className="progress-header">
                <span className="progress-label">Проведено уроков</span>
                <span className="progress-value">{stats?.total_lessons || 0}</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${Math.min((stats?.total_lessons || 0) * 2, 100)}%` }}
                ></div>
              </div>
            </div>

            <div className="progress-item">
              <div className="progress-header">
                <span className="progress-label">Записи уроков</span>
                <span className="progress-value">{stats?.recording_ratio_percent || 0}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${stats?.recording_ratio_percent || 0}%` }}
                ></div>
              </div>
            </div>

            <div className="progress-item">
              <div className="progress-header">
                <span className="progress-label">Активные группы</span>
                <span className="progress-value">{groups.length}</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${Math.min(groups.length * 20, 100)}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* Quick Links */}
          <div className="links-card">
            <h3 className="links-title">
              <span className="section-icon">⚡</span>
              Быстрые ссылки
            </h3>
            <nav className="links-list">
              <Link to="/homework/manage" className="link-item">
                <span className="link-icon">📝</span>
                <span className="link-text">Домашние задания</span>
                <span className="link-arrow">→</span>
              </Link>
              <Link to="/teacher/recordings" className="link-item">
                <span className="link-icon">🎥</span>
                <span className="link-text">Записи уроков</span>
                <span className="link-arrow">→</span>
              </Link>
              <Link to="/profile" className="link-item">
                <span className="link-icon">⚙️</span>
                <span className="link-text">Профиль</span>
                <span className="link-arrow">→</span>
              </Link>
              <Link to="/teacher/subscription" className="link-item">
                <span className="link-icon">💳</span>
                <span className="link-text">Подписка</span>
                <span className="link-arrow">→</span>
              </Link>
            </nav>
          </div>
        </div>
      </div>
    </div>
  );
};

/* =====================================================
   GLOBAL STYLES - Design System
   ===================================================== */
const globalStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  /* === CSS VARIABLES (Design System) === */
  :root {
    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    
    /* Colors */
    --color-primary: #6366f1;
    --color-primary-dark: #4f46e5;
    --color-secondary: #3b82f6;
    --color-accent: #0ea5e9;
    
    --gradient-primary: linear-gradient(135deg, #6366f1 0%, #3b82f6 50%, #0ea5e9 100%);
    --gradient-hero: linear-gradient(135deg, #6366f1 0%, #3b82f6 100%);
    --gradient-success: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
    
    --color-bg: #f8fafc;
    --color-bg-alt: #f1f5f9;
    --color-card: #ffffff;
    --color-border: #e2e8f0;
    
    --color-text-primary: #1e293b;
    --color-text-secondary: #64748b;
    --color-text-muted: #94a3b8;
    
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
    --shadow-xl: 0 20px 40px -10px rgba(0, 0, 0, 0.15);
    --shadow-glow: 0 20px 40px rgba(99, 102, 241, 0.25);
    
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
  }

  /* === DASHBOARD CONTAINER === */
  .teacher-dashboard {
    font-family: var(--font-family);
    background: var(--color-bg);
    min-height: 100vh;
    padding: 1.5rem;
  }

  /* === LOADING STATE === */
  .dashboard-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    color: var(--color-text-secondary);
  }

  .loading-spinner {
    width: 48px;
    height: 48px;
    border: 4px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* === GRID LAYOUT === */
  .dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 340px;
    gap: 1.5rem;
    max-width: 1200px;
    margin: 0 auto;
    align-items: start;
  }

  .dashboard-left {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .dashboard-right {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    position: sticky;
    top: 1.5rem;
  }

  /* === HERO CARD === */
  .hero-card {
    background: var(--gradient-hero);
    border-radius: var(--radius-xl);
    padding: 2.5rem;
    color: #fff;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-glow);
  }

  .hero-decoration {
    position: absolute;
    top: -50px;
    right: -50px;
    width: 200px;
    height: 200px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 50%;
  }

  .hero-decoration-2 {
    position: absolute;
    bottom: -80px;
    left: -40px;
    width: 180px;
    height: 180px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 50%;
  }

  .hero-content {
    position: relative;
    z-index: 1;
  }

  .hero-icon {
    font-size: 2.5rem;
    margin-bottom: 0.75rem;
  }

  .hero-title {
    font-size: 1.75rem;
    font-weight: 800;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.02em;
  }

  .hero-subtitle {
    font-size: 1rem;
    opacity: 0.9;
    margin-bottom: 1.5rem;
    max-width: 400px;
    line-height: 1.5;
  }

  .hero-button {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #fff;
    color: var(--color-primary);
    border: none;
    padding: 1rem 1.75rem;
    border-radius: var(--radius-md);
    font-family: var(--font-family);
    font-weight: 700;
    font-size: 1rem;
    cursor: pointer;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    transition: all 0.2s ease;
  }

  .hero-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.25);
  }

  .hero-button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
  }

  .hero-button-icon {
    font-size: 1.25rem;
  }

  /* === SECTION CARD === */
  .section-card {
    background: var(--color-card);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--color-border);
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.25rem;
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0;
  }

  .section-icon {
    font-size: 1.25rem;
  }

  .section-link {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.875rem;
    color: var(--color-primary);
    text-decoration: none;
    font-weight: 600;
    transition: color 0.2s;
  }

  .section-link:hover {
    color: var(--color-primary-dark);
  }

  .section-link .arrow {
    transition: transform 0.2s;
  }

  .section-link:hover .arrow {
    transform: translateX(3px);
  }

  /* === SCHEDULE LIST === */
  .schedule-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .schedule-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: var(--color-bg);
    border-radius: var(--radius-md);
    border: 1px solid transparent;
    transition: all 0.2s ease;
  }

  .schedule-item:hover {
    border-color: var(--color-primary);
    background: #f8faff;
    transform: translateX(4px);
  }

  .schedule-time {
    display: flex;
    flex-direction: column;
    align-items: center;
    background: var(--gradient-primary);
    color: #fff;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-sm);
    min-width: 70px;
    text-align: center;
  }

  .schedule-date {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    opacity: 0.9;
  }

  .schedule-hour {
    font-size: 0.9rem;
    font-weight: 700;
  }

  .schedule-info {
    flex: 1;
    min-width: 0;
  }

  .schedule-title {
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: 0.25rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .schedule-group {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .schedule-status {
    font-size: 0.75rem;
    font-weight: 600;
  }

  .status-active {
    color: #10b981;
  }

  .status-pending {
    color: var(--color-text-muted);
  }

  /* === GROUPS GRID (Premium Cards) === */
  .groups-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
  }

  .group-card {
    display: flex;
    flex-direction: column;
    background: var(--color-card);
    border-radius: var(--radius-lg);
    overflow: hidden;
    text-decoration: none;
    border: 1px solid var(--color-border);
    transition: all 0.25s ease;
    position: relative;
  }

  .group-card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
    border-color: var(--color-primary);
  }

  .group-cover {
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }

  .group-icon {
    font-size: 2rem;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
  }

  .group-content {
    padding: 1rem;
    flex: 1;
  }

  .group-name {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0 0 0.5rem 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .group-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .group-students {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .meta-icon {
    font-size: 0.9rem;
  }

  .group-arrow {
    position: absolute;
    top: 50%;
    right: 0.75rem;
    transform: translateY(-50%);
    color: var(--color-text-muted);
    opacity: 0;
    transition: all 0.2s;
  }

  .group-card:hover .group-arrow {
    opacity: 1;
    right: 0.5rem;
    color: var(--color-primary);
  }

  /* === EMPTY STATE === */
  .empty-state {
    text-align: center;
    padding: 2rem 1rem;
    color: var(--color-text-secondary);
  }

  .empty-state.full-width {
    grid-column: 1 / -1;
  }

  .empty-icon {
    font-size: 2.5rem;
    display: block;
    margin-bottom: 0.75rem;
    opacity: 0.6;
  }

  .empty-state p {
    margin: 0 0 1rem 0;
  }

  .empty-action {
    display: inline-block;
    color: var(--color-primary);
    font-weight: 600;
    text-decoration: none;
  }

  .empty-action:hover {
    text-decoration: underline;
  }

  /* === STATS CARD === */
  .stats-card {
    background: var(--color-card);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--color-border);
  }

  .stats-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1rem;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0 0 1rem 0;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
  }

  .stat-tile {
    background: var(--color-bg);
    border-radius: var(--radius-md);
    padding: 1rem;
    text-align: center;
    border: 1px solid var(--color-border);
    transition: all 0.2s;
  }

  .stat-tile:hover {
    border-color: var(--color-primary);
    background: #f8faff;
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 800;
    color: var(--color-primary);
    margin-bottom: 0.25rem;
  }

  .stat-label {
    font-size: 0.7rem;
    color: var(--color-text-secondary);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  /* === PROGRESS CARD === */
  .progress-card {
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    border: 1px solid #bbf7d0;
  }

  .progress-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1rem;
    font-weight: 700;
    color: #166534;
    margin: 0 0 1.25rem 0;
  }

  .progress-item {
    margin-bottom: 1rem;
  }

  .progress-item:last-child {
    margin-bottom: 0;
  }

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .progress-label {
    font-size: 0.8rem;
    color: #166534;
    font-weight: 600;
  }

  .progress-value {
    font-size: 0.8rem;
    color: #166534;
    font-weight: 700;
  }

  .progress-bar {
    height: 8px;
    background: rgba(34, 197, 94, 0.2);
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #22c55e, #16a34a);
    border-radius: 4px;
    transition: width 0.5s ease;
  }

  /* === LINKS CARD === */
  .links-card {
    background: var(--color-card);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--color-border);
  }

  .links-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1rem;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0 0 1rem 0;
  }

  .links-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .link-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.875rem 1rem;
    background: var(--color-bg);
    border-radius: var(--radius-md);
    text-decoration: none;
    border: 1px solid transparent;
    transition: all 0.2s ease;
  }

  .link-item:hover {
    background: #f8faff;
    border-color: var(--color-primary);
    transform: translateX(4px);
  }

  .link-icon {
    font-size: 1.1rem;
  }

  .link-text {
    flex: 1;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-text-primary);
  }

  .link-arrow {
    color: var(--color-text-muted);
    font-weight: 600;
    transition: all 0.2s;
  }

  .link-item:hover .link-arrow {
    color: var(--color-primary);
    transform: translateX(3px);
  }

  /* === RESPONSIVE === */
  @media (max-width: 968px) {
    .dashboard-grid {
      grid-template-columns: 1fr;
    }

    .dashboard-right {
      position: static;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }
  }

  @media (max-width: 640px) {
    .teacher-dashboard {
      padding: 1rem;
    }

    .hero-card {
      padding: 1.5rem;
    }

    .hero-title {
      font-size: 1.5rem;
    }

    .groups-grid {
      grid-template-columns: 1fr;
    }

    .dashboard-right {
      grid-template-columns: 1fr;
    }
  }
`;

export default TeacherHomePage;
