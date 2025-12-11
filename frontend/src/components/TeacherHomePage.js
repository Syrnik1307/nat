import React, { useEffect, useState } from 'react';
import { getTeacherStatsSummary, getLessons, getGroups, startQuickLesson } from '../apiService';
import { Link } from 'react-router-dom';
import SubscriptionBanner from './SubscriptionBanner';

/* =====================================================
   TEACHER HOME PAGE - Enterprise Indigo Theme
   Design: Professional SaaS, NO EMOJIS, SVG Icons Only
   ===================================================== */

// =====================================================
// SVG ICON COMPONENTS (Lucide-style)
// =====================================================

const IconVideo = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m22 8-6 4 6 4V8Z"/>
    <rect width="14" height="12" x="2" y="6" rx="2" ry="2"/>
  </svg>
);

const IconCalendar = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
    <line x1="16" x2="16" y1="2" y2="6"/>
    <line x1="8" x2="8" y1="2" y2="6"/>
    <line x1="3" x2="21" y1="10" y2="10"/>
  </svg>
);

const IconUsers = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const IconBarChart = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <line x1="12" x2="12" y1="20" y2="10"/>
    <line x1="18" x2="18" y1="20" y2="4"/>
    <line x1="6" x2="6" y1="20" y2="16"/>
  </svg>
);

const IconTarget = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10"/>
    <circle cx="12" cy="12" r="6"/>
    <circle cx="12" cy="12" r="2"/>
  </svg>
);

const IconClock = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12,6 12,12 16,14"/>
  </svg>
);

const IconUser = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
);

const IconDisc = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10"/>
    <circle cx="12" cy="12" r="2"/>
  </svg>
);

const IconTrendingUp = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polyline points="23,6 13.5,15.5 8.5,10.5 1,18"/>
    <polyline points="17,6 23,6 23,12"/>
  </svg>
);

const IconChevronRight = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m9 18 6-6-6-6"/>
  </svg>
);

const IconPlay = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polygon points="5,3 19,12 5,21 5,3"/>
  </svg>
);

const IconBook = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>
  </svg>
);

const IconFolder = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
  </svg>
);

const IconGraduationCap = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
    <path d="M6 12v5c3 3 9 3 12 0v-5"/>
  </svg>
);

// =====================================================
// MAIN COMPONENT
// =====================================================

const TeacherHomePage = () => {
  const [stats, setStats] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  
  // Modal state for lesson start
  const [showStartModal, setShowStartModal] = useState(false);
  const [recordLesson, setRecordLesson] = useState(true);
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const [startError, setStartError] = useState(null);

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

  const openStartModal = () => {
    setStartError(null);
    setRecordLesson(true);
    setSelectedGroupId(groups.length > 0 ? groups[0].id : '');
    setShowStartModal(true);
  };

  const handleQuickStart = async () => {
    if (starting) return;
    setStarting(true);
    setStartError(null);
    try {
      const res = await startQuickLesson({
        record_lesson: recordLesson,
        group_id: selectedGroupId || undefined,
      });
      if (res.data?.zoom_start_url) {
        window.open(res.data.zoom_start_url, '_blank');
        setShowStartModal(false);
      } else if (res.data?.start_url) {
        window.open(res.data.start_url, '_blank');
        setShowStartModal(false);
      }
    } catch (err) {
      setStartError(err.response?.data?.detail || 'Ошибка запуска урока');
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

  // Generate consistent color index for group based on name
  const getGroupColorIndex = (name) => {
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return hash % 6;
  };

  if (loading) {
    return (
      <div className="dashboard-container">
        <style>{globalStyles}</style>
        <div className="dashboard-loading">
          <div className="loading-spinner"></div>
          <p>Загрузка данных...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <style>{globalStyles}</style>
      
      {/* Subscription Banner */}
      <SubscriptionBanner />

      {/* Start Lesson Modal */}
      {showStartModal && (
        <>
          <div className="modal-overlay" onClick={() => setShowStartModal(false)} />
          <div className="start-modal">
            <h3 className="start-modal-title">
              <IconVideo size={20} />
              <span>Настройки урока</span>
            </h3>

            {/* Group Selection */}
            <div className="start-modal-field">
              <label className="start-modal-label">Группа</label>
              <select
                className="start-modal-select"
                value={selectedGroupId}
                onChange={(e) => setSelectedGroupId(e.target.value)}
              >
                <option value="">Без группы (индивидуальный)</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>{g.name}</option>
                ))}
              </select>
            </div>

            {/* Record Option */}
            <label className={`start-modal-checkbox ${recordLesson ? 'checked' : ''}`}>
              <input
                type="checkbox"
                checked={recordLesson}
                onChange={(e) => setRecordLesson(e.target.checked)}
              />
              <IconDisc size={18} />
              <span>Записывать урок</span>
            </label>

            {recordLesson && (
              <div className="start-modal-hint">
                <IconDisc size={14} />
                <span>Запись будет доступна в разделе «Записи» после окончания</span>
              </div>
            )}

            {startError && (
              <div className="start-modal-error">{startError}</div>
            )}

            <div className="start-modal-actions">
              <button
                className="start-modal-btn primary"
                onClick={handleQuickStart}
                disabled={starting}
              >
                <IconPlay size={16} />
                <span>{starting ? 'Запуск...' : 'Начать урок'}</span>
              </button>
              <button
                className="start-modal-btn secondary"
                onClick={() => setShowStartModal(false)}
              >
                Отмена
              </button>
            </div>
          </div>
        </>
      )}

      {/* Main Grid - No page title, starts directly with content */}
      <div className="dashboard-grid">
        {/* LEFT COLUMN */}
        <div className="dashboard-left">
          {/* Hero: Start Lesson */}
          <div className="hero-card">
            <div className="hero-glow"></div>
            <div className="hero-pattern">
              <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <pattern id="hero-dots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
                    <circle cx="2" cy="2" r="1" fill="rgba(255,255,255,0.1)"/>
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#hero-dots)"/>
              </svg>
            </div>
            <div className="hero-content">
              <div className="hero-icon-wrapper">
                <IconVideo size={32} className="hero-icon" />
              </div>
              <h2 className="hero-title">Начать урок</h2>
              <p className="hero-subtitle">Мгновенный запуск Zoom-конференции для вашего следующего занятия</p>
              <button
                className="hero-button"
                onClick={openStartModal}
                disabled={starting}
              >
                <IconPlay size={18} />
                <span>Запустить урок</span>
              </button>
            </div>
          </div>

          {/* Schedule Section */}
          <div className="section-card">
            <div className="section-header">
              <div className="section-title-group">
                <div className="section-icon-wrapper">
                  <IconCalendar size={18} />
                </div>
                <h3 className="section-title">Расписание</h3>
              </div>
              <Link to="/recurring-lessons/manage" className="section-link">
                Все занятия
                <IconChevronRight size={16} />
              </Link>
            </div>
            <div className="schedule-list">
              {lessons.length > 0 ? (
                lessons.map((lesson) => (
                  <div key={lesson.id} className="schedule-item">
                    <div className="schedule-time-badge">
                      <span className="schedule-date">{formatDate(lesson.start_time)}</span>
                      <span className="schedule-hour">{formatTime(lesson.start_time)}</span>
                    </div>
                    <div className="schedule-info">
                      <div className="schedule-title">{lesson.title || 'Без названия'}</div>
                      <div className="schedule-group">{lesson.group_name || `Группа #${lesson.group}`}</div>
                    </div>
                    <div className="schedule-status">
                      {lesson.zoom_start_url ? (
                        <span className="status-badge status-active">Активен</span>
                      ) : (
                        <span className="status-badge status-pending">Ожидает</span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-state">
                  <IconCalendar size={40} className="empty-icon" />
                  <p>Нет предстоящих занятий</p>
                </div>
              )}
            </div>
          </div>

          {/* Groups Section - Premium Cards */}
          <div className="section-card">
            <div className="section-header">
              <div className="section-title-group">
                <div className="section-icon-wrapper">
                  <IconUsers size={18} />
                </div>
                <h3 className="section-title">Группы</h3>
              </div>
              <Link to="/groups/manage" className="section-link">
                Управление
                <IconChevronRight size={16} />
              </Link>
            </div>
            <div className="groups-grid">
              {groups.length > 0 ? (
                groups.map((group) => {
                  const colorIndex = getGroupColorIndex(group.name);
                  return (
                    <Link
                      key={group.id}
                      to={`/attendance/${group.id}`}
                      className="group-card"
                    >
                      <div className={`group-cover group-cover-${colorIndex}`}>
                        <IconGraduationCap size={28} className="group-cover-icon" />
                        <svg className="group-pattern" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
                          <defs>
                            <pattern id={`pattern-${group.id}`} x="0" y="0" width="16" height="16" patternUnits="userSpaceOnUse">
                              <circle cx="1" cy="1" r="1" fill="rgba(255,255,255,0.15)"/>
                            </pattern>
                          </defs>
                          <rect width="100%" height="100%" fill={`url(#pattern-${group.id})`}/>
                        </svg>
                      </div>
                      <div className="group-body">
                        <h4 className="group-name">{group.name}</h4>
                        <div className="group-meta">
                          <IconUser size={14} />
                          <span>{group.students?.length || 0} учеников</span>
                        </div>
                      </div>
                      <div className="group-arrow">
                        <IconChevronRight size={18} />
                      </div>
                    </Link>
                  );
                })
              ) : (
                <div className="empty-state full-width">
                  <IconUsers size={40} className="empty-icon" />
                  <p>Нет групп</p>
                  <Link to="/groups/manage" className="empty-action">Создать группу</Link>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN - Stats Only (No Quick Links) */}
        <div className="dashboard-right">
          {/* Statistics Card - Expanded */}
          <div className="stats-card">
            <div className="stats-header">
              <div className="stats-icon-wrapper">
                <IconBarChart size={20} />
              </div>
              <h3 className="stats-title">Статистика</h3>
            </div>
            <div className="stats-grid">
              <div className="stat-tile">
                <div className="stat-icon">
                  <IconBook size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.total_lessons || 0}</div>
                  <div className="stat-label">Уроков проведено</div>
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-icon">
                  <IconUsers size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.total_students || 0}</div>
                  <div className="stat-label">Учеников</div>
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-icon">
                  <IconFolder size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.total_groups || 0}</div>
                  <div className="stat-label">Групп</div>
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-icon">
                  <IconCalendar size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.upcoming_lessons?.length || 0}</div>
                  <div className="stat-label">Ближайшие</div>
                </div>
              </div>
            </div>
          </div>

          {/* Progress Card - Expanded */}
          <div className="progress-card">
            <div className="progress-header">
              <div className="progress-icon-wrapper">
                <IconTarget size={20} />
              </div>
              <h3 className="progress-title">Прогресс</h3>
            </div>
            
            <div className="progress-list">
              <div className="progress-item">
                <div className="progress-item-header">
                  <div className="progress-item-label">
                    <IconClock size={16} />
                    <span>Часов на платформе</span>
                  </div>
                  <span className="progress-item-value">{Math.round((stats?.portal_minutes || 0) / 60)}</span>
                </div>
                <div className="progress-bar-track">
                  <div 
                    className="progress-bar-fill"
                    style={{ width: `${Math.min((stats?.portal_minutes || 0) / 60, 100)}%` }}
                  ></div>
                </div>
              </div>

              <div className="progress-item">
                <div className="progress-item-header">
                  <div className="progress-item-label">
                    <IconVideo size={16} />
                    <span>Часов занятий</span>
                  </div>
                  <span className="progress-item-value">{Math.round((stats?.teaching_minutes || 0) / 60)}</span>
                </div>
                <div className="progress-bar-track">
                  <div 
                    className="progress-bar-fill"
                    style={{ width: `${Math.min((stats?.teaching_minutes || 0) / 60, 100)}%` }}
                  ></div>
                </div>
              </div>

              <div className="progress-item">
                <div className="progress-item-header">
                  <div className="progress-item-label">
                    <IconFolder size={16} />
                    <span>Активные группы</span>
                  </div>
                  <span className="progress-item-value">{stats?.total_groups || 0}</span>
                </div>
                <div className="progress-bar-track">
                  <div 
                    className="progress-bar-fill"
                    style={{ width: `${Math.min((stats?.total_groups || 0) * 20, 100)}%` }}
                  ></div>
                </div>
              </div>

              <div className="progress-item">
                <div className="progress-item-header">
                  <div className="progress-item-label">
                    <IconUsers size={16} />
                    <span>Всего учеников</span>
                  </div>
                  <span className="progress-item-value">{stats?.total_students || 0}</span>
                </div>
                <div className="progress-bar-track">
                  <div 
                    className="progress-bar-fill"
                    style={{ width: `${Math.min((stats?.total_students || 0) * 5, 100)}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* =====================================================
   GLOBAL STYLES - Enterprise Indigo Theme
   NO EMOJIS, Professional Design
   ===================================================== */
const globalStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  /* === CSS VARIABLES - INDIGO THEME === */
  :root {
    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    
    /* Indigo Color Palette */
    --indigo-50: #eef2ff;
    --indigo-100: #e0e7ff;
    --indigo-200: #c7d2fe;
    --indigo-300: #a5b4fc;
    --indigo-400: #818cf8;
    --indigo-500: #6366f1;
    --indigo-600: #4f46e5;
    --indigo-700: #4338ca;
    --indigo-800: #3730a3;
    --indigo-900: #312e81;
    
    --color-primary: var(--indigo-600);
    --color-primary-hover: var(--indigo-700);
    --color-primary-light: var(--indigo-100);
    
    --gradient-primary: linear-gradient(135deg, var(--indigo-700) 0%, var(--indigo-500) 100%);
    --gradient-hero: linear-gradient(135deg, var(--indigo-800) 0%, var(--indigo-600) 50%, var(--indigo-500) 100%);
    
    /* Neutrals */
    --slate-50: #f8fafc;
    --slate-100: #f1f5f9;
    --slate-200: #e2e8f0;
    --slate-300: #cbd5e1;
    --slate-400: #94a3b8;
    --slate-500: #64748b;
    --slate-600: #475569;
    --slate-700: #334155;
    --slate-800: #1e293b;
    --slate-900: #0f172a;
    
    --color-bg: var(--slate-50);
    --color-card: #ffffff;
    --color-border: var(--slate-200);
    --color-text-primary: var(--slate-800);
    --color-text-secondary: var(--slate-500);
    --color-text-muted: var(--slate-400);
    
    /* Shadows */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.04);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
    --shadow-indigo: 0 20px 40px -10px rgba(79, 70, 229, 0.35);
    
    /* Border Radius */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-xl: 18px;
  }

  /* === DASHBOARD CONTAINER === */
  .dashboard-container {
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
    width: 44px;
    height: 44px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* === GRID LAYOUT === */
  .dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 360px;
    gap: 1.5rem;
    max-width: 1240px;
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
    box-shadow: var(--shadow-indigo);
  }

  .hero-glow {
    position: absolute;
    top: -100px;
    right: -100px;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
    border-radius: 50%;
  }

  .hero-pattern {
    position: absolute;
    inset: 0;
    opacity: 0.5;
  }

  .hero-content {
    position: relative;
    z-index: 1;
  }

  .hero-icon-wrapper {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: var(--radius-md);
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
  }

  .hero-icon {
    color: #fff;
  }

  .hero-title {
    font-size: 1.75rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.025em;
  }

  .hero-subtitle {
    font-size: 0.95rem;
    opacity: 0.85;
    margin-bottom: 1.75rem;
    max-width: 420px;
    line-height: 1.6;
  }

  .hero-button {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #fff;
    color: var(--indigo-700);
    border: none;
    padding: 0.875rem 1.5rem;
    border-radius: var(--radius-md);
    font-family: var(--font-family);
    font-weight: 600;
    font-size: 0.95rem;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transition: all 0.2s ease;
  }

  .hero-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
  }

  .hero-button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
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

  .section-title-group {
    display: flex;
    align-items: center;
    gap: 0.625rem;
  }

  .section-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: var(--indigo-100);
    border-radius: var(--radius-sm);
    color: var(--indigo-600);
  }

  .section-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0;
  }

  .section-link {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.8rem;
    color: var(--color-primary);
    text-decoration: none;
    font-weight: 500;
    transition: all 0.2s;
  }

  .section-link:hover {
    color: var(--color-primary-hover);
  }

  .section-link:hover svg {
    transform: translateX(2px);
  }

  .section-link svg {
    transition: transform 0.2s;
  }

  /* === SCHEDULE LIST === */
  .schedule-list {
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
  }

  .schedule-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.875rem 1rem;
    background: var(--slate-50);
    border-radius: var(--radius-md);
    border: 1px solid transparent;
    transition: all 0.2s ease;
  }

  .schedule-item:hover {
    border-color: var(--indigo-200);
    background: var(--indigo-50);
  }

  .schedule-time-badge {
    display: flex;
    flex-direction: column;
    align-items: center;
    background: var(--gradient-primary);
    color: #fff;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-sm);
    min-width: 68px;
    text-align: center;
  }

  .schedule-date {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    opacity: 0.9;
    letter-spacing: 0.5px;
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
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: 0.2rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .schedule-group {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .schedule-status {
    flex-shrink: 0;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.35rem 0.65rem;
    border-radius: 100px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .status-active {
    background: #dcfce7;
    color: #166534;
  }

  .status-pending {
    background: var(--slate-100);
    color: var(--slate-500);
  }

  /* === GROUPS GRID === */
  .groups-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
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
    transform: translateY(-3px);
    box-shadow: var(--shadow-lg);
    border-color: var(--indigo-300);
  }

  .group-cover {
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
  }

  .group-cover-0 { background: linear-gradient(135deg, var(--indigo-600), var(--indigo-400)); }
  .group-cover-1 { background: linear-gradient(135deg, #0ea5e9, #38bdf8); }
  .group-cover-2 { background: linear-gradient(135deg, #10b981, #34d399); }
  .group-cover-3 { background: linear-gradient(135deg, #f59e0b, #fbbf24); }
  .group-cover-4 { background: linear-gradient(135deg, #ec4899, #f472b6); }
  .group-cover-5 { background: linear-gradient(135deg, #8b5cf6, #a78bfa); }

  .group-cover-icon {
    color: rgba(255, 255, 255, 0.9);
    z-index: 1;
  }

  .group-pattern {
    position: absolute;
    inset: 0;
  }

  .group-body {
    padding: 1rem;
    flex: 1;
  }

  .group-name {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0 0 0.5rem 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .group-meta {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8rem;
    color: var(--color-text-secondary);
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
    padding: 2.5rem 1rem;
    color: var(--color-text-secondary);
  }

  .empty-state.full-width {
    grid-column: 1 / -1;
  }

  .empty-icon {
    color: var(--color-text-muted);
    margin-bottom: 0.75rem;
  }

  .empty-state p {
    margin: 0 0 0.75rem 0;
    font-size: 0.9rem;
  }

  .empty-action {
    display: inline-block;
    color: var(--color-primary);
    font-weight: 600;
    font-size: 0.85rem;
    text-decoration: none;
  }

  .empty-action:hover {
    text-decoration: underline;
  }

  /* === STATS CARD (Expanded) === */
  .stats-card {
    background: var(--color-card);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--color-border);
  }

  .stats-header {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    margin-bottom: 1.25rem;
  }

  .stats-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: var(--indigo-100);
    border-radius: var(--radius-sm);
    color: var(--indigo-600);
  }

  .stats-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
  }

  .stat-tile {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: var(--slate-50);
    border-radius: var(--radius-md);
    padding: 1rem;
    border: 1px solid var(--color-border);
    transition: all 0.2s;
  }

  .stat-tile:hover {
    border-color: var(--indigo-200);
    background: var(--indigo-50);
  }

  .stat-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    background: var(--indigo-100);
    border-radius: var(--radius-sm);
    color: var(--indigo-600);
    flex-shrink: 0;
  }

  .stat-content {
    min-width: 0;
  }

  .stat-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--color-text-primary);
    line-height: 1.2;
  }

  .stat-label {
    font-size: 0.7rem;
    color: var(--color-text-secondary);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }

  /* === PROGRESS CARD (Expanded) === */
  .progress-card {
    background: var(--color-card);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--color-border);
  }

  .progress-header {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    margin-bottom: 1.5rem;
  }

  .progress-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: var(--indigo-100);
    border-radius: var(--radius-sm);
    color: var(--indigo-600);
  }

  .progress-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0;
  }

  .progress-list {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .progress-item {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .progress-item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .progress-item-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    font-weight: 500;
  }

  .progress-item-label svg {
    color: var(--indigo-400);
  }

  .progress-item-value {
    font-size: 0.8rem;
    color: var(--color-text-primary);
    font-weight: 600;
  }

  .progress-bar-track {
    height: 6px;
    background: var(--slate-100);
    border-radius: 100px;
    overflow: hidden;
  }

  .progress-bar-fill {
    height: 100%;
    background: var(--gradient-primary);
    border-radius: 100px;
    transition: width 0.5s ease;
  }

  /* === RESPONSIVE === */
  @media (max-width: 1024px) {
    .dashboard-grid {
      grid-template-columns: 1fr;
    }

    .dashboard-right {
      position: static;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }
  }

  @media (max-width: 640px) {
    .dashboard-container {
      padding: 1rem;
    }

    .hero-card {
      padding: 1.75rem;
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

    .stats-grid {
      grid-template-columns: 1fr;
    }
  }

  /* === START LESSON MODAL === */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    z-index: 1000;
  }

  .start-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: #fff;
    border-radius: var(--radius-xl);
    padding: 1.75rem;
    width: 400px;
    max-width: 92vw;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.2);
    z-index: 1001;
  }

  .start-modal-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0 0 1.25rem 0;
  }

  .start-modal-title svg {
    color: var(--color-primary);
  }

  .start-modal-field {
    margin-bottom: 1rem;
  }

  .start-modal-label {
    display: block;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--color-text-secondary);
    margin-bottom: 0.5rem;
  }

  .start-modal-select {
    width: 100%;
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: #fff;
    color: var(--color-text-primary);
    cursor: pointer;
    transition: border-color 0.15s;
  }

  .start-modal-select:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px var(--color-primary-light);
  }

  .start-modal-checkbox {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.85rem 1rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    background: #f9fafb;
    cursor: pointer;
    transition: all 0.15s;
    margin-bottom: 0.75rem;
  }

  .start-modal-checkbox.checked {
    background: var(--indigo-50);
    border-color: var(--indigo-200);
  }

  .start-modal-checkbox input {
    width: 1.1rem;
    height: 1.1rem;
    accent-color: var(--color-primary);
    cursor: pointer;
  }

  .start-modal-checkbox svg {
    color: var(--color-text-secondary);
  }

  .start-modal-checkbox.checked svg {
    color: var(--color-primary);
  }

  .start-modal-checkbox span {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--color-text-primary);
  }

  .start-modal-hint {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: var(--indigo-50);
    border-radius: var(--radius-md);
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    margin-bottom: 1rem;
  }

  .start-modal-hint svg {
    color: var(--color-primary);
    flex-shrink: 0;
    margin-top: 1px;
  }

  .start-modal-error {
    padding: 0.75rem 1rem;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: var(--radius-md);
    color: #dc2626;
    font-size: 0.85rem;
    margin-bottom: 1rem;
  }

  .start-modal-actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1rem;
  }

  .start-modal-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
    font-weight: 600;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.15s;
    border: none;
  }

  .start-modal-btn.primary {
    background: var(--gradient-primary);
    color: #fff;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
  }

  .start-modal-btn.primary:hover:not(:disabled) {
    box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4);
    transform: translateY(-1px);
  }

  .start-modal-btn.primary:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .start-modal-btn.secondary {
    background: #f3f4f6;
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
  }

  .start-modal-btn.secondary:hover {
    background: #e5e7eb;
  }
`;

export default TeacherHomePage;
