import React, { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { getTeacherStatsSummary, getLessons, getGroups, startQuickLesson } from '../apiService';
import { Link } from 'react-router-dom';
import SubscriptionBanner from './SubscriptionBanner';

/* =====================================================
   TEACHER HOME PAGE - Полностью переписанный компонент
   Макет: CSS Grid, 2 колонки (70% / 30%)
   ===================================================== */

const styles = {
  /* === MAIN WRAPPER === */
  pageWrapper: {
    fontFamily: "'Inter', sans-serif",
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '2rem 1.5rem',
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
  },

  /* === HEADER === */
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '2rem',
    paddingBottom: '1rem',
    borderBottom: '1px solid #e2e8f0',
  },
  logo: {
    fontSize: '1.75rem',
    fontWeight: 800,
    background: 'linear-gradient(135deg, #6366f1, #3b82f6)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
    letterSpacing: '-0.02em',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  userName: {
    fontSize: '0.9rem',
    color: '#64748b',
    fontWeight: 500,
  },
  logoutBtn: {
    background: '#ef4444',
    color: '#fff',
    border: 'none',
    padding: '0.5rem 1rem',
    borderRadius: '8px',
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: '0.85rem',
    transition: 'background 0.2s',
  },

  /* === GRID LAYOUT === */
  gridContainer: {
    display: 'grid',
    gridTemplateColumns: '1fr 340px',
    gap: '1.5rem',
    alignItems: 'start',
  },
  leftColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.5rem',
  },
  rightColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.5rem',
  },

  /* === HERO CARD (Quick Lesson) === */
  heroCard: {
    background: 'linear-gradient(135deg, #6366f1 0%, #3b82f6 50%, #0ea5e9 100%)',
    borderRadius: '20px',
    padding: '2.5rem',
    color: '#fff',
    boxShadow: '0 20px 40px rgba(99, 102, 241, 0.3)',
    position: 'relative',
    overflow: 'hidden',
  },
  heroPattern: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: '200px',
    height: '200px',
    background: 'radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%)',
    borderRadius: '50%',
    transform: 'translate(30%, -30%)',
  },
  heroTitle: {
    fontSize: '1.75rem',
    fontWeight: 800,
    marginBottom: '0.5rem',
    position: 'relative',
    zIndex: 1,
  },
  heroSubtitle: {
    fontSize: '1rem',
    opacity: 0.9,
    marginBottom: '1.5rem',
    position: 'relative',
    zIndex: 1,
  },
  heroButton: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    background: '#fff',
    color: '#6366f1',
    border: 'none',
    padding: '1rem 2rem',
    borderRadius: '12px',
    fontWeight: 700,
    fontSize: '1rem',
    cursor: 'pointer',
    boxShadow: '0 4px 15px rgba(0, 0, 0, 0.15)',
    transition: 'transform 0.2s, box-shadow 0.2s',
    position: 'relative',
    zIndex: 1,
  },

  /* === SECTION CARD (Schedule, Groups) === */
  sectionCard: {
    background: '#fff',
    borderRadius: '16px',
    padding: '1.5rem',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.06)',
    border: '1px solid #e2e8f0',
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
  },
  sectionTitle: {
    fontSize: '1.1rem',
    fontWeight: 700,
    color: '#1e293b',
    margin: 0,
  },
  sectionLink: {
    fontSize: '0.85rem',
    color: '#6366f1',
    textDecoration: 'none',
    fontWeight: 600,
  },

  /* === SCHEDULE LIST === */
  lessonItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    padding: '1rem',
    borderRadius: '12px',
    background: '#f8fafc',
    marginBottom: '0.75rem',
    transition: 'background 0.2s',
  },
  lessonTime: {
    background: 'linear-gradient(135deg, #6366f1, #3b82f6)',
    color: '#fff',
    padding: '0.5rem 0.75rem',
    borderRadius: '8px',
    fontSize: '0.8rem',
    fontWeight: 700,
    minWidth: '70px',
    textAlign: 'center',
  },
  lessonInfo: {
    flex: 1,
  },
  lessonTitle: {
    fontWeight: 600,
    color: '#1e293b',
    marginBottom: '0.25rem',
  },
  lessonGroup: {
    fontSize: '0.8rem',
    color: '#64748b',
  },

  /* === GROUPS GRID === */
  groupsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
    gap: '0.75rem',
  },
  groupCard: {
    background: '#f8fafc',
    borderRadius: '12px',
    padding: '1rem',
    textAlign: 'center',
    border: '1px solid #e2e8f0',
    transition: 'transform 0.2s, box-shadow 0.2s',
    cursor: 'pointer',
  },
  groupName: {
    fontWeight: 600,
    color: '#1e293b',
    marginBottom: '0.25rem',
  },
  groupCount: {
    fontSize: '0.8rem',
    color: '#64748b',
  },

  /* === STATS SECTION (Right Column) === */
  statsCard: {
    background: '#fff',
    borderRadius: '16px',
    padding: '1.5rem',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.06)',
    border: '1px solid #e2e8f0',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '1rem',
  },
  statTile: {
    background: '#f8fafc',
    borderRadius: '12px',
    padding: '1rem',
    textAlign: 'center',
    border: '1px solid #e2e8f0',
  },
  statValue: {
    fontSize: '1.5rem',
    fontWeight: 800,
    color: '#6366f1',
    marginBottom: '0.25rem',
  },
  statLabel: {
    fontSize: '0.75rem',
    color: '#64748b',
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },

  /* === PROGRESS CARD === */
  progressCard: {
    background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)',
    borderRadius: '16px',
    padding: '1.5rem',
    border: '1px solid #bbf7d0',
  },
  progressTitle: {
    fontSize: '1rem',
    fontWeight: 700,
    color: '#166534',
    marginBottom: '1rem',
  },
  progressItem: {
    marginBottom: '1rem',
  },
  progressLabel: {
    fontSize: '0.8rem',
    color: '#166534',
    fontWeight: 600,
    marginBottom: '0.5rem',
    display: 'flex',
    justifyContent: 'space-between',
  },
  progressBar: {
    height: '8px',
    background: '#bbf7d0',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #22c55e, #16a34a)',
    borderRadius: '4px',
  },

  /* === EMPTY STATE === */
  emptyState: {
    textAlign: 'center',
    padding: '2rem',
    color: '#64748b',
  },

  /* === LOADING === */
  loading: {
    textAlign: 'center',
    padding: '3rem',
    color: '#64748b',
  },

  /* === RESPONSIVE (handled inline) === */
};

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

  if (loading) {
    return (
      <div style={styles.pageWrapper}>
        <div style={styles.loading}>Загрузка...</div>
      </div>
    );
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        .hero-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
        }
        .group-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
        }
        .lesson-item:hover {
          background: #f1f5f9;
        }
        @media (max-width: 900px) {
          .dashboard-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>

      <div style={styles.pageWrapper}>
        {/* HEADER */}
        <header style={styles.header}>
          <div style={styles.logo}>Lectio Space</div>
          <div style={styles.headerRight}>
            <span style={styles.userName}>{user?.full_name || user?.email || 'Преподаватель'}</span>
            <button style={styles.logoutBtn} onClick={logout}>Выход</button>
          </div>
        </header>

        {/* SUBSCRIPTION BANNER */}
        <SubscriptionBanner />

        {/* MAIN GRID */}
        <div className="dashboard-grid" style={styles.gridContainer}>
          {/* LEFT COLUMN (70%) */}
          <div style={styles.leftColumn}>
            {/* HERO: Quick Lesson */}
            <div style={styles.heroCard}>
              <div style={styles.heroPattern}></div>
              <h2 style={styles.heroTitle}>🚀 Начать урок</h2>
              <p style={styles.heroSubtitle}>Мгновенный запуск Zoom-конференции для вашего следующего занятия</p>
              <button
                className="hero-btn"
                style={styles.heroButton}
                onClick={handleQuickStart}
                disabled={starting}
              >
                {starting ? '⏳ Запуск...' : '📹 Запустить Zoom'}
              </button>
            </div>

            {/* SCHEDULE */}
            <div style={styles.sectionCard}>
              <div style={styles.sectionHeader}>
                <h3 style={styles.sectionTitle}>📅 Расписание</h3>
                <Link to="/recurring-lessons/manage" style={styles.sectionLink}>Все занятия →</Link>
              </div>
              {lessons.length > 0 ? (
                lessons.map((lesson) => (
                  <div
                    key={lesson.id}
                    className="lesson-item"
                    style={styles.lessonItem}
                  >
                    <div style={styles.lessonTime}>
                      {formatDate(lesson.start_time)}<br />
                      {formatTime(lesson.start_time)}
                    </div>
                    <div style={styles.lessonInfo}>
                      <div style={styles.lessonTitle}>{lesson.title || 'Без названия'}</div>
                      <div style={styles.lessonGroup}>{lesson.group_name || `Группа #${lesson.group}`}</div>
                    </div>
                  </div>
                ))
              ) : (
                <div style={styles.emptyState}>Нет предстоящих занятий</div>
              )}
            </div>

            {/* GROUPS */}
            <div style={styles.sectionCard}>
              <div style={styles.sectionHeader}>
                <h3 style={styles.sectionTitle}>👥 Группы</h3>
                <Link to="/groups/manage" style={styles.sectionLink}>Управление →</Link>
              </div>
              {groups.length > 0 ? (
                <div style={styles.groupsGrid}>
                  {groups.map((group) => (
                    <Link
                      key={group.id}
                      to={`/attendance/${group.id}`}
                      style={{ textDecoration: 'none' }}
                    >
                      <div className="group-card" style={styles.groupCard}>
                        <div style={styles.groupName}>{group.name}</div>
                        <div style={styles.groupCount}>{group.students?.length || 0} учеников</div>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div style={styles.emptyState}>Нет групп</div>
              )}
            </div>
          </div>

          {/* RIGHT COLUMN (30%) */}
          <div style={styles.rightColumn}>
            {/* STATISTICS */}
            <div style={styles.statsCard}>
              <div style={styles.sectionHeader}>
                <h3 style={styles.sectionTitle}>📊 Статистика</h3>
              </div>
              <div style={styles.statsGrid}>
                <div style={styles.statTile}>
                  <div style={styles.statValue}>{stats?.total_lessons || 0}</div>
                  <div style={styles.statLabel}>Уроков</div>
                </div>
                <div style={styles.statTile}>
                  <div style={styles.statValue}>{stats?.total_students || 0}</div>
                  <div style={styles.statLabel}>Учеников</div>
                </div>
                <div style={styles.statTile}>
                  <div style={styles.statValue}>{stats?.recorded_lessons || 0}</div>
                  <div style={styles.statLabel}>Записей</div>
                </div>
                <div style={styles.statTile}>
                  <div style={styles.statValue}>{stats?.recording_ratio_percent || 0}%</div>
                  <div style={styles.statLabel}>С записью</div>
                </div>
              </div>
            </div>

            {/* TEACHER PROGRESS */}
            <div style={styles.progressCard}>
              <h3 style={styles.progressTitle}>🎯 Прогресс</h3>
              
              <div style={styles.progressItem}>
                <div style={styles.progressLabel}>
                  <span>Проведено уроков</span>
                  <span>{stats?.total_lessons || 0}</span>
                </div>
                <div style={styles.progressBar}>
                  <div style={{ ...styles.progressFill, width: `${Math.min((stats?.total_lessons || 0) * 2, 100)}%` }}></div>
                </div>
              </div>

              <div style={styles.progressItem}>
                <div style={styles.progressLabel}>
                  <span>Записи уроков</span>
                  <span>{stats?.recording_ratio_percent || 0}%</span>
                </div>
                <div style={styles.progressBar}>
                  <div style={{ ...styles.progressFill, width: `${stats?.recording_ratio_percent || 0}%` }}></div>
                </div>
              </div>

              <div style={styles.progressItem}>
                <div style={styles.progressLabel}>
                  <span>Активные группы</span>
                  <span>{groups.length}</span>
                </div>
                <div style={styles.progressBar}>
                  <div style={{ ...styles.progressFill, width: `${Math.min(groups.length * 20, 100)}%` }}></div>
                </div>
              </div>
            </div>

            {/* QUICK LINKS */}
            <div style={styles.sectionCard}>
              <h3 style={{ ...styles.sectionTitle, marginBottom: '1rem' }}>⚡ Быстрые ссылки</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <Link to="/homework/manage" style={{ ...styles.sectionLink, display: 'block', padding: '0.75rem', background: '#f8fafc', borderRadius: '8px' }}>📝 Домашние задания</Link>
                <Link to="/teacher/recordings" style={{ ...styles.sectionLink, display: 'block', padding: '0.75rem', background: '#f8fafc', borderRadius: '8px' }}>🎥 Записи уроков</Link>
                <Link to="/profile" style={{ ...styles.sectionLink, display: 'block', padding: '0.75rem', background: '#f8fafc', borderRadius: '8px' }}>⚙️ Профиль</Link>
                <Link to="/teacher/subscription" style={{ ...styles.sectionLink, display: 'block', padding: '0.75rem', background: '#f8fafc', borderRadius: '8px' }}>💳 Подписка</Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default TeacherHomePage;
