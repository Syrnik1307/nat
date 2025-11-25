import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useAuth } from '../auth';
import { getTeacherStatsSummary, getLessons, getGroups } from '../apiService';
import { Link, useNavigate } from 'react-router-dom';
import StartLessonButton from '../modules/core/zoom/StartLessonButton';
import './TeacherHomePage.css';

const TreeGrowth = ({ stage, progress }) => {
  const safeProgress = Number.isFinite(progress)
    ? Math.min(Math.max(progress, 0), 1)
    : 0;

  return (
    <div
      className="tree-growth"
      data-stage={stage}
      style={{ '--growth-progress': safeProgress.toFixed(2) }}
    >
      <div className="tree-sky" aria-hidden="true"></div>
      <div className="tree-fireflies" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <div className="tree-sprout" aria-hidden="true">
        <div className="stem"></div>
        <div className="leaf left"></div>
        <div className="leaf right"></div>
      </div>
      <div className="tree-trunk" aria-hidden="true"></div>
      <div className="tree-crown crown-main" aria-hidden="true"></div>
      <div className="tree-crown crown-second" aria-hidden="true"></div>
      <div className="tree-ground" aria-hidden="true"></div>
    </div>
  );
};

/**
 * Главная страница преподавателя
 *
 * Отображает:
 * 1. Расписание на сегодня
 * 2. Прогресс преподавателя и накопленные показатели
 */

const TeacherHomePage = () => {
  const { accessTokenValid } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [groups, setGroups] = useState([]);
  const [todayLessons, setTodayLessons] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    if (!accessTokenValid) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const todayDate = new Date().toISOString().split('T')[0];
      const [groupsRes, lessonsRes, statsRes] = await Promise.all([
        getGroups(),
        getLessons({ date: todayDate }),
        getTeacherStatsSummary(),
      ]);

      const groupsList = Array.isArray(groupsRes.data) 
        ? groupsRes.data 
        : groupsRes.data.results || [];
      
      const lessonsList = Array.isArray(lessonsRes.data)
        ? lessonsRes.data
        : lessonsRes.data.results || [];

      setGroups(groupsList);
      setTodayLessons(lessonsList);
      setStats(statsRes.data);
    } catch (err) {
      console.error('Ошибка загрузки данных:', err);
      setError('Не удалось загрузить данные. Попробуйте обновить страницу.');
    } finally {
      setLoading(false);
    }
  }, [accessTokenValid]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', { 
      day: 'numeric', 
      month: 'long',
      weekday: 'long' 
    });
  };

  const derivedStats = useMemo(() => {
    const totalGroupsStudents = groups.reduce((acc, group) => acc + (group.students_count || 0), 0);
    const totalStudents = stats?.total_students || totalGroupsStudents;
    const lessonsCount = stats?.total_lessons || todayLessons.length || 0;
    const avgDuration = stats?.avg_lesson_duration_minutes || stats?.average_duration || 60;
    const teachingMinutes = stats?.total_teaching_minutes || stats?.teaching_minutes || lessonsCount * avgDuration;
    const portalMinutes = stats?.total_portal_minutes || Math.round(teachingMinutes * 1.15 + 90);
    const homeworkSaved = stats?.auto_check_time_saved || Math.round((stats?.auto_checked_homework || 0) * 8.5);
    const attendanceRaw = stats?.attendance_rate_percent ?? stats?.attendance_rate ?? stats?.average_attendance ?? null;
    const normalizedAttendance = Number.isFinite(attendanceRaw)
      ? Math.max(0, Math.min(100, Math.round(attendanceRaw)))
      : 92;
    const newHomework = stats?.new_homework_count ?? stats?.homework_created_this_week ?? stats?.auto_checked_homework ?? 0;
    const levels = [
      {
        key: 'soil',
        name: 'Плодородная земля',
        badge: '🌍',
        minMinutes: 0,
        description: 'Питательная база для будущего леса знаний.',
      },
      {
        key: 'sprout',
        name: 'Росток знаний',
        badge: '🌱',
        minMinutes: 600,
        description: 'Первые 10 часов занятий превращаются в живой росток.',
      },
      {
        key: 'sapling',
        name: 'Молодой дуб',
        badge: '🌿',
        minMinutes: 6000,
        description: '100 часов совместной работы формируют крепкий ствол.',
      },
      {
        key: 'tree',
        name: 'Большое дерево',
        badge: '🌳',
        minMinutes: 12000,
        description: 'После 200 часов ваш дуб даёт тень целому поколению.',
      },
      {
        key: 'ancient',
        name: 'Вековой дуб',
        badge: '🪵',
        minMinutes: 24000,
        description: 'Легендарное дерево знаний, которым вдохновляются другие.',
      },
    ];
    const currentLevel = levels
      .slice()
      .reverse()
      .find(level => teachingMinutes >= level.minMinutes) || levels[0];
    const nextLevel = levels.find(level => level.minMinutes > currentLevel.minMinutes);
    const minutesToNext = nextLevel ? Math.max(0, nextLevel.minMinutes - teachingMinutes) : 0;
    const levelRange = nextLevel
      ? Math.max(1, nextLevel.minMinutes - currentLevel.minMinutes)
      : Math.max(1, teachingMinutes || 1);
    const levelProgress = nextLevel
      ? Math.min(1, Math.max(0, (teachingMinutes - currentLevel.minMinutes) / levelRange))
      : 1;
    const progressPercent = nextLevel
      ? Math.min(
          100,
          Math.round(
            ((teachingMinutes - currentLevel.minMinutes) /
              (nextLevel.minMinutes - currentLevel.minMinutes)) *
              100
          )
        )
      : 100;
    const hoursToNext = nextLevel ? Math.ceil(minutesToNext / 60) : 0;

    return {
      totalStudents,
      lessonsCount,
      teachingMinutes,
      portalMinutes,
      homeworkSaved,
      currentLevel,
      nextLevel,
      levelKey: currentLevel.key,
      levelProgress,
      progressPercent,
      minutesToNext,
      hoursToNext,
      treeCurrency: Math.max(0, Math.floor(teachingMinutes / 30)),
      attendanceRate: normalizedAttendance,
      newHomeworkCount: Math.max(0, newHomework),
    };
  }, [groups, stats, todayLessons]);

  if (loading) {
    return (
      <div className="teacher-home-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Загрузка...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="teacher-home-page">
      {/* Заголовок страницы */}
      <div className="page-header">
        <div className="header-content">
          <h1 className="page-title">Главная</h1>
          <p className="page-subtitle">
            {formatDate(new Date().toISOString())}
          </p>
        </div>
        <div className="header-actions">
          <button 
            type="button" 
            className="header-message-button" 
            aria-label="Сообщения"
            onClick={() => navigate('/chat')}
          >
            <span className="header-message-icon" aria-hidden="true">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M6.5 8.5H17.5"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                />
                <path
                  d="M6.5 12H14"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                />
                <path
                  d="M4.5 5.75C4.5 4.7835 5.2835 4 6.25 4H17.75C18.7165 4 19.5 4.7835 19.5 5.75V14.25C19.5 15.2165 18.7165 16 17.75 16H12.6C12.2279 16 11.8746 16.1397 11.6071 16.3896L8.80535 18.9993C8.28679 19.4827 7.5 19.1174 7.5 18.3975V16.75C7.5 16.0596 6.94036 15.5 6.25 15.5H6.25C5.2835 15.5 4.5 14.7165 4.5 13.75V5.75Z"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            <span className="header-message-label">Сообщения</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={loadData}>Повторить</button>
        </div>
      )}

      <div className="content-grid">
        {/* Левая колонка: Расписание на сегодня */}
        <div className="main-content">
          <section className="schedule-section">
            <div className="section-header">
              <h2 className="section-title">
                <span className="icon">📅</span>
                Расписание на сегодня
              </h2>
              <Link to="/calendar" className="link-all">
                Весь календарь →
              </Link>
            </div>

            {todayLessons.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">📭</div>
                <h3>Сегодня нет занятий</h3>
                <p>Вы можете запланировать новые уроки в календаре</p>
                <Link to="/recurring-lessons/manage" className="btn btn-secondary">
                  Добавить урок
                </Link>
              </div>
            ) : (
              <div className="lessons-list">
                {todayLessons.map((lesson) => (
                  <div key={lesson.id} className="lesson-card">
                    <div className="lesson-time">
                      <span className="time">{formatTime(lesson.start_time)}</span>
                      <span className="duration">
                        {lesson.duration || '60'} мин
                      </span>
                    </div>
                    <div className="lesson-info">
                      <h3 className="lesson-title">{lesson.title}</h3>
                      <div className="lesson-meta">
                        <span className="group">
                          👥 {lesson.group_name || 'Группа'}
                        </span>
                        {lesson.zoom_link && (
                          <a 
                            href={lesson.zoom_link} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="zoom-link"
                          >
                            🎥 Zoom
                          </a>
                        )}
                      </div>
                    </div>
                    <div className="lesson-actions">
                      <StartLessonButton 
                        lessonId={lesson.id} 
                        groupName={lesson.group_name || 'Группа'}
                        onSuccess={() => {
                          // Можно добавить обновление данных после старта
                          console.log('Занятие успешно начато!');
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Сводная статистика */}
          <section className="summary-stats">
            <h2 className="summary-title">Статистика</h2>
            <div className="summary-grid">
              <div className="summary-card">
                <div className="summary-icon students">🧑‍🏫</div>
                <div className="summary-copy">
                  <span className="summary-label">УЧЕНИКОВ</span>
                  <span className="summary-value">{derivedStats.totalStudents}</span>
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-icon lessons">📚</div>
                <div className="summary-copy">
                  <span className="summary-label">УРОКОВ</span>
                  <span className="summary-value">{derivedStats.lessonsCount}</span>
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-icon attendance">✅</div>
                <div className="summary-copy">
                  <span className="summary-label">ПОСЕЩАЕМОСТЬ</span>
                  <span className="summary-value">{derivedStats.attendanceRate}%</span>
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-icon homework">📝</div>
                <div className="summary-copy">
                  <span className="summary-label">НОВЫХ ДЗ</span>
                  <span className="summary-value">{derivedStats.newHomeworkCount}</span>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Правая колонка: прогресс и группы */}
        <aside className="sidebar">
          <section className="impact-dashboard">
            <div className="impact-header">
              <h2 className="section-title">
                <span className="icon">🌳</span>
                Прогресс преподавателя
              </h2>
              <span className="impact-tag">листья: {derivedStats.treeCurrency}</span>
            </div>

            <TreeGrowth stage={derivedStats.levelKey} progress={derivedStats.levelProgress} />

            <div className="badge-card">
              <div className="badge-icon">{derivedStats.currentLevel.badge}</div>
              <div className="badge-info">
                <span className="badge-title">{derivedStats.currentLevel.name}</span>
                <span className="badge-subtitle">{derivedStats.currentLevel.description}</span>
                {derivedStats.nextLevel ? (
                  <span className="badge-subtitle">
                    До стадии «{derivedStats.nextLevel.name}»: {derivedStats.hoursToNext} ч занятий
                  </span>
                ) : (
                  <span className="badge-subtitle">Вы достигли максимального уровня! 🔥</span>
                )}
              </div>
            </div>

            <div className="level-progress">
              <div className="progress-track">
                <div className="progress-thumb" style={{ width: `${derivedStats.progressPercent}%` }}></div>
              </div>
              <div className="progress-meta">
                <span>{derivedStats.teachingMinutes} мин занятий</span>
                <span>{derivedStats.treeCurrency} листьев для магазина</span>
              </div>
            </div>

            <div className="impact-grid">
              <div className="impact-card">
                <span className="impact-label">Проведено уроков</span>
                <span className="impact-value">{derivedStats.lessonsCount}</span>
                <span className="impact-sub">каждый час = новые листья</span>
              </div>
              <div className="impact-card">
                <span className="impact-label">Минут на платформе</span>
                <span className="impact-value">{derivedStats.portalMinutes}</span>
                <span className="impact-sub">совместной работы</span>
              </div>
              <div className="impact-card">
                <span className="impact-label">Листья знаний</span>
                <span className="impact-value">{derivedStats.treeCurrency}</span>
                <span className="impact-sub">покупка курсов и книг внутри</span>
              </div>
              <div className="impact-card">
                <span className="impact-label">Экономия времени</span>
                <span className="impact-value">{derivedStats.homeworkSaved}</span>
                <span className="impact-sub">минут автопроверкой ДЗ</span>
              </div>
            </div>
          </section>

        </aside>
      </div>
    </div>
  );
};

export default TeacherHomePage;
