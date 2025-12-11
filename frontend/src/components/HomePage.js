import React, { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { getTeacherStatsSummary, getLessons, getGroups, getHomeworkList } from '../apiService';
import { Link } from 'react-router-dom';
import SupportWidget from './SupportWidget';
import './HomePage.css';

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
        const now = new Date();
        const in30 = new Date();
        in30.setDate(now.getDate() + 30);
        if (role === 'teacher') {
          const [statsRes, lessonsRes, groupsRes] = await Promise.all([
            getTeacherStatsSummary(),
            getLessons({
              start: now.toISOString(),
              end: in30.toISOString(),
              include_recurring: true,
            }),
            getGroups(),
          ]);
          setTeacherStats(statsRes.data);
          const lessonList = Array.isArray(lessonsRes.data) ? lessonsRes.data : lessonsRes.data.results || [];
          setUpcomingLessons(lessonList.slice(0,5));
          setGroups(Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || []);
        } else if (role === 'student') {
          const [lessonsRes, groupsRes, hwRes] = await Promise.all([
            getLessons({
              start: now.toISOString(),
              end: in30.toISOString(),
              include_recurring: true,
            }),
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
      <div className="home-hero-wrap">
        <div className="home-hero-card">
          <h1 className="home-hero-title">Добро пожаловать в Lectio Space</h1>
          <p className="home-hero-subtitle">Расписание, задания, аналитика и Zoom – всё в одном месте.</p>
          <div className="home-cta-buttons">
            <a href="/login" className="home-cta-primary">Войти</a>
            <a href="https://docs.example.com" className="home-cta-secondary">Документация</a>
          </div>
          <div className="home-feature-grid">
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
    <div className="home-page-container">
      <div className="home-page-header">
        <h1 className="home-page-title">Главная</h1>
        <div className="home-filter-tabs">
          <button 
            className={`home-filter-tab ${activeFilter === 'day' ? 'active' : ''}`}
            onClick={() => setActiveFilter('day')}
          >
            На день
          </button>
          <button 
            className={`home-filter-tab ${activeFilter === 'week' ? 'active' : ''}`}
            onClick={() => setActiveFilter('week')}
          >
            На неделю
          </button>
          <button 
            className={`home-filter-tab ${activeFilter === 'month' ? 'active' : ''}`}
            onClick={() => setActiveFilter('month')}
          >
            На месяц
          </button>
          <button 
            className={`home-filter-tab ${activeFilter === 'quarter' ? 'active' : ''}`}
            onClick={() => setActiveFilter('quarter')}
          >
            На квартал
          </button>
          <button 
            className={`home-filter-tab ${activeFilter === 'year' ? 'active' : ''}`}
            onClick={() => setActiveFilter('year')}
          >
            На год
          </button>
        </div>
      </div>

      {loading && <div className="home-loading">Загрузка...</div>}

      <div className="home-main-grid">
        <div className="home-main-content">
          {role === 'teacher' && teacherStats && (
            <section className="home-stats-section">
              <div className="home-stats-grid-dashboard">
                <StatCard icon="" label="Уроков" value={teacherStats.total_lessons} color="#FF6B35" />
                <StatCard icon="⏱️" label="Средняя длит." value={`${Math.round((teacherStats.average_duration_seconds || 0) / 60)} мин`} color="#2563eb" />
                <StatCard icon="" label="Записано" value={`${teacherStats.recording_ratio_percent}%`} color="#16a34a" />
                <StatCard icon="" label="Учеников" value={teacherStats.total_students} color="#9333ea" />
              </div>
            </section>
          )}

          <section className="home-lessons-section">
            <h2 className="home-section-title">
              Расписание
              {role === 'teacher' && (
                <Link to="/recurring-lessons/manage" className="home-link-small"> → Управление</Link>
              )}
            </h2>
            <div className="home-lessons-list">
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
                <div className="home-empty-state">
                  <div className="home-empty-icon"></div>
                  <p>Сегодня нет занятий</p>
                </div>
              )}
            </div>
          </section>
        </div>

        <aside className="home-sidebar">
          {(role === 'student' || homework.length > 0) && (
            <div className="home-sidebar-card">
              <h3 className="home-sidebar-title">
                <span></span>
                Нужно сделать
              </h3>
              <div className="home-tasks-list">
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

          <div className="home-sidebar-card">
            <h3 className="home-sidebar-title">
              <span></span>
              Мои группы
            </h3>
            <div className="home-groups-list">
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

const Feature = ({icon, title, text}) => (
  <div className="home-feature-item">
    <div className="home-feature-icon-box">{icon}</div>
    <div className="home-feature-title">{title}</div>
    <div className="home-feature-text">{text}</div>
  </div>
);

const StatCard = ({ icon, label, value, color }) => (
  <div className="home-stat-card" style={{borderLeft: `4px solid ${color}`}}>
    <div className="home-stat-icon">{icon}</div>
    <div>
      <div className="home-stat-value">{value}</div>
      <div className="home-stat-label">{label}</div>
    </div>
  </div>
);

const LessonCard = ({title, time, group, location, teacher}) => (
  <div className="home-lesson-card">
    <div className="home-lesson-header">
      <div>
        <div className="home-lesson-title">{title}</div>
        <div className="home-lesson-teacher">Учитель: {teacher}</div>
        <div className="home-lesson-group">Группа: {group}</div>
      </div>
      <div className="home-lesson-time">{time}</div>
    </div>
    <div className="home-lesson-meta">
      <div className="home-lesson-meta-item">
        <span>📍</span>
        <span>{location}</span>
      </div>
      <div className="home-lesson-meta-item">
        <span></span>
        <span>Занятие онлайн</span>
      </div>
    </div>
    <div className="home-lesson-actions">
      <button className="home-btn-outline">Отметить посещение</button>
      <button className="home-btn-outline">Начать занятие</button>
    </div>
  </div>
);

const TaskItem = ({ title, deadline, count }) => (
  <div className="home-task-item">
    <div className="home-task-title">{title} ({count})</div>
    <div className="home-task-deadline">⏰ {deadline}</div>
  </div>
);

const GroupItem = ({ name, students, attendance, homework }) => (
  <div className="home-group-item">
    <div className="home-group-name">{name}</div>
    <div className="home-group-info">
      Учеников: {students} • Посещаемость: {attendance}% • Домашнее задание: {homework}%
    </div>
  </div>
);

export default HomePage; 
