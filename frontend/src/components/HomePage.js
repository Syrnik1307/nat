import React, { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { getTeacherStatsSummary, getLessons, getGroups, getHomeworkList } from '../apiService';
import { Link } from 'react-router-dom';
import SupportWidget from './SupportWidget';

const HomePage = () => {
  const { accessTokenValid, role } = useAuth();
  const [teacherStats, setTeacherStats] = useState(null);
  const [upcomingLessons, setUpcomingLessons] = useState([]);
  const [groups, setGroups] = useState([]);
  const [homework, setHomework] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState('week');

  useEffect(() => {
    const load = async () => {
      if (!accessTokenValid) return;
      setLoading(true);
      try {
        if (role === 'teacher') {
          const [statsRes, lessonsRes, groupsRes] = await Promise.all([
            getTeacherStatsSummary(),
            getLessons({}),
            getGroups(),
          ]);
          setTeacherStats(statsRes.data);
          const lessonList = Array.isArray(lessonsRes.data) ? lessonsRes.data : lessonsRes.data.results || [];
          setUpcomingLessons(lessonList.slice(0,5));
          setGroups(Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || []);
        } else if (role === 'student') {
          const [lessonsRes, groupsRes, hwRes] = await Promise.all([
            getLessons({}),
            getGroups(),
            getHomeworkList({}),
          ]);
          const lessonList = Array.isArray(lessonsRes.data) ? lessonsRes.data : lessonsRes.data.results || [];
          setUpcomingLessons(lessonList.slice(0,5));
          setGroups(Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || []);
          setHomework(Array.isArray(hwRes.data) ? hwRes.data : hwRes.data.results || []);
        }
      } catch (_) {
        // ignore for landing
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [accessTokenValid, role]);

  if (!accessTokenValid) {
    return (
      <div style={styles.heroWrap}>
        <div style={styles.heroCard}>
          <h1 style={styles.heroTitle}>Добро пожаловать в Easy Teaching</h1>
          <p style={styles.heroSubtitle}>Расписание, задания, аналитика и Zoom – всё в одном месте.</p>
          <div style={{ display:'flex', gap:'1rem', marginTop:'1.5rem' }}>
            <a href="/login" style={styles.ctaPrimary}>Войти</a>
            <a href="https://docs.example.com" style={styles.ctaSecondary}>Документация</a>
          </div>
          <div style={styles.featureGrid}>
            <Feature icon="" title="Расписание" text="Гибкое расписание и повторяющиеся занятия" />
            <Feature icon="" title="Домашки" text="Автоматическая проверка и баллы" />
            <Feature icon="" title="Аналитика" text="Посещаемость и успеваемость" />
            <Feature icon="" title="Zoom" text="Пул лицензий и записи" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.pageContainer}>
      <div style={styles.pageHeader}>
        <h1 style={styles.pageTitle}>Главная</h1>
        <div style={styles.filterTabs}>
          <button 
            style={{...styles.filterTab, ...(activeFilter === 'day' ? styles.filterTabActive : {})}}
            onClick={() => setActiveFilter('day')}
          >
            На день
          </button>
          <button 
            style={{...styles.filterTab, ...(activeFilter === 'week' ? styles.filterTabActive : {})}}
            onClick={() => setActiveFilter('week')}
          >
            На неделю
          </button>
          <button 
            style={{...styles.filterTab, ...(activeFilter === 'month' ? styles.filterTabActive : {})}}
            onClick={() => setActiveFilter('month')}
          >
            На месяц
          </button>
          <button 
            style={{...styles.filterTab, ...(activeFilter === 'quarter' ? styles.filterTabActive : {})}}
            onClick={() => setActiveFilter('quarter')}
          >
            На квартал
          </button>
          <button 
            style={{...styles.filterTab, ...(activeFilter === 'year' ? styles.filterTabActive : {})}}
            onClick={() => setActiveFilter('year')}
          >
            На год
          </button>
        </div>
      </div>

      {loading && <div style={styles.loading}>Загрузка...</div>}

      <div style={styles.mainGrid}>
        <div style={styles.mainContent}>
          {role === 'teacher' && teacherStats && (
            <section style={styles.statsSection}>
              <div style={styles.statsGrid}>
                <StatCard icon="" label="Уроков" value={teacherStats.total_lessons} color="#FF6B35" />
                <StatCard icon="⏱️" label="Средняя длит." value={`${Math.round((teacherStats.average_duration_seconds || 0) / 60)} мин`} color="#2563eb" />
                <StatCard icon="" label="Записано" value={`${teacherStats.recording_ratio_percent}%`} color="#16a34a" />
                <StatCard icon="" label="Учеников" value={teacherStats.total_students} color="#9333ea" />
              </div>
            </section>
          )}

          <section style={styles.lessonsSection}>
            <h2 style={styles.sectionTitle}>
              Расписание
              {role === 'teacher' && (
                <Link to="/recurring-lessons/manage" style={styles.linkSmall}> → Управление</Link>
              )}
            </h2>
            <div style={styles.lessonsList}>
              {upcomingLessons.map(l => (
                <LessonCard 
                  key={l.id}
                  title={l.title}
                  time={new Date(l.start_time).toLocaleString('ru-RU', { 
                    weekday: 'long',
                    day: 'numeric', 
                    month: 'long',
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                  group={l.group_name || l.group}
                  location={l.location || 'Онлайн'}
                  teacher="Никита Сыромятников"
                />
              ))}
              {upcomingLessons.length === 0 && (
                <div style={styles.emptyState}>
                  <div style={styles.emptyIcon}></div>
                  <p>Сегодня нет занятий</p>
                </div>
              )}
            </div>
          </section>
        </div>

        <aside style={styles.sidebar}>
          {(role === 'student' || homework.length > 0) && (
            <div style={styles.sidebarCard}>
              <h3 style={styles.sidebarTitle}>
                <span></span>
                Нужно сделать
              </h3>
              <div style={styles.tasksList}>
                {homework.slice(0, 5).map((hw, idx) => (
                  <TaskItem 
                    key={hw.id || idx}
                    title={hw.title}
                    deadline="До 15.10.25"
                    count={19}
                  />
                ))}
                {homework.length === 0 && (
                  <>
                    <TaskItem title="Проверить работы с развёрн..." deadline="До 15.10.25" count={19} />
                    <TaskItem title="Отправить результаты точки..." deadline="До 15.02.25" count={22} />
                    <TaskItem title="Отправить отбивку о пропуске" deadline="До 25.09.25" count={4} />
                  </>
                )}
              </div>
            </div>
          )}

          <div style={styles.sidebarCard}>
            <h3 style={styles.sidebarTitle}>
              <span></span>
              Мои группы
            </h3>
            <div style={styles.groupsList}>
              {groups.slice(0, 3).map(g => (
                <GroupItem 
                  key={g.id}
                  name={g.name}
                  students={g.students?.length || 0}
                  attendance={94}
                  homework={77}
                />
              ))}
              {groups.length === 0 && <p style={styles.emptyText}>Нет групп</p>}
            </div>
            {role === 'teacher' && (
              <div style={{ marginTop:'1rem' }}>
                <Link to="/groups/manage" style={styles.btnManage}>
                  <span>➕</span>
                  <span>Управление группами</span>
                </Link>
              </div>
            )}
          </div>
        </aside>
      </div>
      <SupportWidget />
    </div>
  );
};

const Feature = ({ icon, title, text }) => (
  <div style={styles.featureItem}>
    <div style={styles.featureIcon}>{icon}</div>
    <div style={{ fontWeight:600, color:'#111827' }}>{title}</div>
    <div style={{ fontSize:'0.85rem', color:'#6b7280' }}>{text}</div>
  </div>
);

const StatCard = ({ icon, label, value, color }) => (
  <div style={{...styles.statCard, borderLeft:`4px solid ${color}`}}>
    <div style={styles.statIcon}>{icon}</div>
    <div>
      <div style={styles.statValue}>{value}</div>
      <div style={styles.statLabel}>{label}</div>
    </div>
  </div>
);

const LessonCard = ({ title, time, group, location, teacher }) => (
  <div style={styles.lessonCard}>
    <div style={styles.lessonHeader}>
      <div>
        <div style={styles.lessonTitle}>{title}</div>
        <div style={styles.lessonTeacher}>Учитель: {teacher}</div>
        <div style={styles.lessonGroup}>Группа: {group}</div>
      </div>
      <div style={styles.lessonTime}>{time}</div>
    </div>
    <div style={styles.lessonMeta}>
      <div style={styles.lessonMetaItem}>
        <span>📍</span>
        <span>{location}</span>
      </div>
      <div style={styles.lessonMetaItem}>
        <span></span>
        <span>Занятие онлайн</span>
      </div>
    </div>
    <div style={styles.lessonActions}>
      <button style={styles.btnOutline}>Отметить посещение</button>
      <button style={styles.btnOutline}>Начать занятие</button>
    </div>
  </div>
);

const TaskItem = ({ title, deadline, count }) => (
  <div style={styles.taskItem}>
    <div style={styles.taskTitle}>{title} ({count})</div>
    <div style={styles.taskDeadline}>⏰ {deadline}</div>
  </div>
);

const GroupItem = ({ name, students, attendance, homework }) => (
  <div style={styles.groupItem}>
    <div style={styles.groupName}>{name}</div>
    <div style={styles.groupInfo}>
      Учеников: {students} • Посещаемость: {attendance}% • Домашнее задание: {homework}%
    </div>
  </div>
);

const styles = {
  heroWrap: { 
    display:'flex', 
    justifyContent:'center', 
    padding:'4rem 2rem',
    background:'linear-gradient(135deg, #fff7ed 0%, #ffffff 100%)'
  },
  heroCard: { 
    maxWidth:1000, 
    width:'100%', 
    background:'#ffffff', 
    borderRadius:20, 
    padding:'3rem', 
    boxShadow:'0 20px 40px rgba(0,0,0,0.08)'
  },
  heroTitle: { 
    fontSize:'2.5rem', 
    margin:'0 0 1rem', 
    fontWeight:700, 
    background:'linear-gradient(135deg, #FF6B35 0%, #F7931E 100%)', 
    WebkitBackgroundClip:'text', 
    WebkitTextFillColor:'transparent',
    backgroundClip:'text'
  },
  heroSubtitle: { 
    fontSize:'1.1rem', 
    lineHeight:1.6, 
    maxWidth:700, 
    color:'#4b5563' 
  },
  ctaPrimary: { 
    background:'#FF6B35', 
    color:'#fff', 
    textDecoration:'none', 
    padding:'0.875rem 1.75rem', 
    borderRadius:10, 
    fontWeight:600,
    fontSize:'1rem',
    display:'inline-block'
  },
  ctaSecondary: { 
    background:'#f3f4f6', 
    color:'#374151', 
    textDecoration:'none', 
    padding:'0.875rem 1.75rem', 
    borderRadius:10, 
    fontWeight:600,
    fontSize:'1rem',
    display:'inline-block'
  },
  featureGrid: { 
    display:'grid', 
    gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))', 
    gap:'1.25rem', 
    marginTop:'3rem' 
  },
  featureItem: { 
    background:'#f9fafb', 
    border:'1px solid #e5e7eb', 
    padding:'1.5rem', 
    borderRadius:12, 
    display:'flex', 
    flexDirection:'column', 
    gap:'0.5rem',
    transition:'all 0.2s ease'
  },
  featureIcon: { 
    fontSize:'2rem' 
  },
  pageContainer: {
    padding:'2rem',
    maxWidth:'1400px',
    margin:'0 auto',
    background:'#ffffff'
  },
  pageHeader: {
    marginBottom:'2rem'
  },
  pageTitle: {
    fontSize:'1.875rem',
    fontWeight:600,
    color:'#111827',
    marginBottom:'1.5rem'
  },
  filterTabs: {
    display:'flex',
    gap:'0.5rem',
    flexWrap:'wrap',
    borderBottom:'1px solid #e5e7eb',
    paddingBottom:'0.5rem'
  },
  filterTab: {
    padding:'0.5rem 1.25rem',
    background:'transparent',
    border:'none',
    borderRadius:20,
    fontSize:'0.9rem',
    cursor:'pointer',
    transition:'all 0.2s ease',
    color:'#6b7280',
    fontWeight:500
  },
  filterTabActive: {
    background:'#FF6B35',
    color:'white'
  },
  loading: {
    textAlign:'center',
    padding:'3rem',
    color:'#6b7280'
  },
  mainGrid: {
    display:'grid',
    gridTemplateColumns:'1fr 380px',
    gap:'2rem'
  },
  mainContent: {
    minWidth:0
  },
  sidebar: {
    minWidth:0
  },
  statsSection: {
    marginBottom:'2rem'
  },
  statsGrid: {
    display:'grid',
    gridTemplateColumns:'repeat(auto-fit, minmax(200px, 1fr))',
    gap:'1rem'
  },
  statCard: {
    background:'white',
    border:'1px solid #e5e7eb',
    borderRadius:12,
    padding:'1.25rem',
    display:'flex',
    alignItems:'center',
    gap:'1rem',
    transition:'all 0.2s ease'
  },
  statIcon: {
    fontSize:'2rem'
  },
  statValue: {
    fontSize:'1.75rem',
    fontWeight:700,
    color:'#111827'
  },
  statLabel: {
    fontSize:'0.875rem',
    color:'#6b7280'
  },
  lessonsSection: {
    marginBottom:'2rem'
  },
  sectionTitle: {
    fontSize:'1.5rem',
    fontWeight:600,
    color:'#111827',
    marginBottom:'1.25rem'
  },
  lessonsList: {
    display:'flex',
    flexDirection:'column',
    gap:'1rem'
  },
  lessonCard: {
    background:'#ffffff',
    border:'1px solid #e5e7eb',
    borderRadius:12,
    padding:'1.5rem',
    transition:'all 0.2s ease'
  },
  lessonHeader: {
    display:'flex',
    justifyContent:'space-between',
    alignItems:'flex-start',
    marginBottom:'1rem'
  },
  lessonTitle: {
    fontSize:'1.125rem',
    fontWeight:600,
    color:'#111827',
    marginBottom:'0.5rem'
  },
  lessonTeacher: {
    fontSize:'0.875rem',
    color:'#6b7280',
    marginBottom:'0.25rem'
  },
  lessonGroup: {
    fontSize:'0.875rem',
    color:'#6b7280'
  },
  lessonTime: {
    fontSize:'0.875rem',
    color:'#FF6B35',
    fontWeight:600,
    whiteSpace:'nowrap',
    marginLeft:'1rem'
  },
  lessonMeta: {
    display:'flex',
    gap:'1.5rem',
    marginBottom:'1rem'
  },
  lessonMetaItem: {
    display:'flex',
    alignItems:'center',
    gap:'0.5rem',
    fontSize:'0.875rem',
    color:'#6b7280'
  },
  lessonActions: {
    display:'flex',
    gap:'0.75rem',
    flexWrap:'wrap'
  },
  btnOutline: {
    padding:'0.5rem 1rem',
    border:'1px solid #e5e7eb',
    background:'white',
    borderRadius:8,
    fontSize:'0.875rem',
    cursor:'pointer',
    transition:'all 0.2s ease',
    color:'#374151',
    fontWeight:500
  },
  emptyState: {
    textAlign:'center',
    padding:'3rem',
    color:'#9ca3af'
  },
  emptyIcon: {
    fontSize:'3rem',
    marginBottom:'1rem'
  },
  sidebarCard: {
    background:'#ffffff',
    border:'1px solid #e5e7eb',
    borderRadius:12,
    padding:'1.5rem',
    marginBottom:'1.5rem'
  },
  sidebarTitle: {
    fontSize:'1rem',
    fontWeight:600,
    color:'#111827',
    marginBottom:'1.25rem',
    display:'flex',
    alignItems:'center',
    gap:'0.5rem'
  },
  tasksList: {
    display:'flex',
    flexDirection:'column'
  },
  taskItem: {
    padding:'0.875rem 0',
    borderBottom:'1px solid #f3f4f6',
    fontSize:'0.875rem'
  },
  taskTitle: {
    color:'#111827',
    marginBottom:'0.375rem',
    fontWeight:500
  },
  taskDeadline: {
    color:'#dc2626',
    fontSize:'0.8rem'
  },
  groupsList: {
    display:'flex',
    flexDirection:'column',
    gap:'0.75rem'
  },
  groupItem: {
    padding:'1rem',
    background:'#f9fafb',
    border:'1px solid #e5e7eb',
    borderRadius:10,
    cursor:'pointer',
    transition:'all 0.2s ease'
  },
  groupName: {
    fontWeight:600,
    color:'#111827',
    marginBottom:'0.375rem'
  },
  groupInfo: {
    fontSize:'0.8rem',
    color:'#6b7280'
  },
  emptyText: {
    color:'#9ca3af',
    fontSize:'0.875rem',
    textAlign:'center'
  },
  btnManage: {
    display:'flex',
    alignItems:'center',
    justifyContent:'center',
    gap:'0.5rem',
    padding:'0.75rem 1rem',
    background:'#FF6B35',
    color:'white',
    textDecoration:'none',
    borderRadius:8,
    fontSize:'0.9rem',
    fontWeight:600,
    transition:'all 0.2s ease'
  },
  linkSmall: {
    fontSize:'0.875rem',
    color:'#FF6B35',
    textDecoration:'none',
    marginLeft:'0.75rem',
    fontWeight:500
  }
};

export default HomePage;
