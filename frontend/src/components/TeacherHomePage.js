import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useAuth } from '../auth';
import { getTeacherStatsSummary, getTeacherStatsBreakdown, getLessons, getGroups, startQuickLesson, getIndividualStudents, apiClient } from '../apiService';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import SwipeableLesson from './SwipeableLesson';
import SupportWidget from './SupportWidget';
import SubscriptionBanner from './SubscriptionBanner';
import TelegramWarningBanner from './TelegramWarningBanner';
import GroupDetailModal from './GroupDetailModal';
import StudentCardModal from './StudentCardModal';
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

// Прогресс-бар вынесен вверх чтобы использовать внутри компонента
const ProgressBar = ({ value, variant='default' }) => {
  const safe = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
  return (
    <div className={`progress-bar pb-${variant}`}> 
      <div className="progress-fill" style={{ width: `${safe}%` }} />
    </div>
  );
};

const TeacherHomePage = () => {
  const { accessTokenValid, subscription } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [groups, setGroups] = useState([]);
  const [todayLessons, setTodayLessons] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [breakdown, setBreakdown] = useState({ groups: [], students: [] });
  const [quickLessonLoading, setQuickLessonLoading] = useState(false);
  const [quickLessonError, setQuickLessonError] = useState(null);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  
  // Состояние для модальных окон
  const [groupDetailModal, setGroupDetailModal] = useState({ isOpen: false, group: null });
  const [studentCardModal, setStudentCardModal] = useState({ isOpen: false, studentId: null, groupId: null, isIndividual: false });

  // Проверяем успешную оплату
  useEffect(() => {
    if (searchParams.get('payment') === 'success') {
      setPaymentSuccess(true);
      // Убираем параметр из URL
      searchParams.delete('payment');
      setSearchParams(searchParams, { replace: true });
      
      // Скрываем уведомление через 5 секунд
      setTimeout(() => setPaymentSuccess(false), 5000);
    }
  }, [searchParams, setSearchParams]);

  const loadData = useCallback(async () => {
    if (!accessTokenValid) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const todayDate = new Date().toISOString().split('T')[0];
      const [groupsRes, lessonsRes, statsRes, breakdownRes, individualStudentsRes] = await Promise.all([
        getGroups(),
        getLessons({ date: todayDate, include_recurring: true }),
        getTeacherStatsSummary(),
        getTeacherStatsBreakdown(),
        getIndividualStudents(),
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
      
      // Получаем индивидуальных студентов и преобразуем их для отображения
      const individualStudents = Array.isArray(individualStudentsRes.data)
        ? individualStudentsRes.data
        : individualStudentsRes.data.results || [];
      
      const individualStudentsForDisplay = individualStudents.map(st => {
        const fullName = st.student_name || `${st.first_name || ''} ${st.last_name || ''}`.trim();
        return {
          id: st.user_id || st.student_id || st.id,
          name: fullName || st.email,
          email: st.email,
          group_id: null,
          group_name: 'Индивидуальный',
          attendance_percent: st.attendance_percent ?? 0,
          homework_percent: st.homework_percent ?? 0,
        };
      });
      
      setBreakdown({
        groups: breakdownRes.data?.groups || [],
        students: individualStudentsForDisplay
      });
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

  const handleQuickLessonCreate = useCallback(async () => {
    setQuickLessonLoading(true);
    setQuickLessonError(null);
    try {
      const response = await startQuickLesson();
      if (response?.data?.zoom_start_url) {
        window.open(response.data.zoom_start_url, '_blank', 'noopener,noreferrer');
      }
      await loadData();
    } catch (err) {
      console.error('Не удалось создать экспресс-урок:', err);
      const detail = err.response?.data?.detail || err.message || 'Не удалось создать урок.';
      setQuickLessonError(detail);
    } finally {
      setQuickLessonLoading(false);
    }
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

  const getLessonDuration = (lesson) => {
    // Используем duration_minutes с бэкенда если есть
    if (lesson.duration_minutes && lesson.duration_minutes > 0) {
      return lesson.duration_minutes;
    }
    // Fallback: расчет из времен
    if (lesson.start_time && lesson.end_time) {
      const start = new Date(lesson.start_time);
      const end = new Date(lesson.end_time);
      const durationMinutes = Math.round((end - start) / (1000 * 60));
      if (durationMinutes > 0) return durationMinutes;
    }
    // Дефолт 60 минут
    return 60;
  };

  const handleDeleteLesson = async (lessonId, deleteType) => {
    try {
      const lesson = todayLessons.find(l => l.id === lessonId);
      if (!lesson) {
        throw new Error('Урок не найден в расписании. Обновите страницу и попробуйте ещё раз.');
      }

      if (deleteType === 'single') {
        await apiClient.delete(`schedule/lessons/${lessonId}/`);
        await loadData();
        return { status: 'deleted', message: `Урок «${lesson.title}» удалён` };
      }

      if (deleteType === 'recurring') {
        const response = await apiClient.post('schedule/lessons/delete_recurring/', {
          title: lesson.title,
          group_id: lesson.group || lesson.group_id,
        });
        await loadData();
        return {
          status: 'deleted',
          count: response?.data?.count,
          message: response?.data?.message || 'Похожие уроки удалены',
        };
      }

      throw new Error('Неизвестный тип удаления');
    } catch (error) {
      console.error('Ошибка удаления урока:', error);
      throw error;
    }
  };

  const derivedStats = useMemo(() => {
    // Реальные данные с бэкенда
    const totalStudents = stats?.total_students || 0;
    const totalGroups = stats?.total_groups || 0;
    const lessonsCount = stats?.total_lessons || 0;
    const teachingMinutes = stats?.teaching_minutes || 0;
    const portalMinutes = stats?.portal_minutes || 0;
    
    // Уровни дерева знаний
    const levels = [
      {
        key: 'soil',
        name: 'Плодородная земля',
        minMinutes: 0,
        description: 'Питательная база для будущего леса знаний.',
      },
      {
        key: 'sprout',
        name: 'Росток знаний',
        minMinutes: 600,
        description: 'Первые 10 часов занятий превращаются в живой росток.',
      },
      {
        key: 'sapling',
        name: 'Молодой дуб',
        minMinutes: 6000,
        description: '100 часов совместной работы формируют крепкий ствол.',
      },
      {
        key: 'tree',
        name: 'Большое дерево',
        minMinutes: 12000,
        description: 'После 200 часов ваш дуб даёт тень целому поколению.',
      },
      {
        key: 'ancient',
        name: 'Вековой дуб',
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
      totalGroups,
      lessonsCount,
      teachingMinutes,
      portalMinutes,
      currentLevel,
      nextLevel,
      levelKey: currentLevel.key,
      levelProgress,
      progressPercent,
      minutesToNext,
      hoursToNext,
    };
  }, [stats]);

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
      <TelegramWarningBanner />
      
      <SubscriptionBanner 
        subscription={subscription} 
        onPayClick={() => navigate('/teacher/subscription')} 
      />

      {/* Уведомление об успешной оплате */}
      {paymentSuccess && (
        <div style={{
          position: 'fixed',
          top: '80px',
          right: '20px',
          zIndex: 9999,
          background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
          color: 'white',
          padding: '16px 24px',
          borderRadius: '12px',
          boxShadow: '0 10px 40px rgba(16, 185, 129, 0.4)',
          animation: 'slideInRight 0.5s ease',
          maxWidth: '400px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(255,255,255,0.3)', flexShrink: 0 }}></div>
            <div>
              <div style={{ fontWeight: 600, marginBottom: '4px' }}>Платёж успешен!</div>
              <div style={{ fontSize: '14px', opacity: 0.9 }}>
                Ваша подписка активирована
              </div>
            </div>
          </div>
        </div>
      )}
      
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
            aria-label="Записи уроков"
            onClick={() => navigate('/teacher/recordings')}
            style={{ marginRight: '1rem' }}
          >
            <span className="header-message-icon" aria-hidden="true">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.6" fill="none"/>
                <polygon points="10,8 16,12 10,16" fill="currentColor"/>
              </svg>
            </span>
            <span className="header-message-label">Записи</span>
          </button>
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
          <span>{error}</span>
          <button onClick={loadData}>Повторить</button>
        </div>
      )}

      <div className="content-grid">
        {/* Левая колонка: Расписание на сегодня */}
        <div className="main-content">
          <section className="schedule-section">
            <div className="section-header">
              <h2 className="section-title">
                Расписание на сегодня
              </h2>
              <Link to="/calendar" className="link-all">
                Весь календарь →
              </Link>
            </div>

            {todayLessons.length === 0 ? (
              <div className="empty-state">
                <h3>Сегодня нет занятий</h3>
                <p>Вы можете запланировать новые уроки в календаре</p>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleQuickLessonCreate}
                  disabled={quickLessonLoading}
                >
                  {quickLessonLoading ? 'Создание...' : 'Создать урок'}
                </button>
                {quickLessonError && (
                  <div className="error-inline" role="status">
                    {quickLessonError}
                  </div>
                )}
              </div>
            ) : (
              <div className="lessons-list">
                {todayLessons.map((lesson) => (
                  <SwipeableLesson
                    key={lesson.id}
                    lesson={lesson}
                    onDelete={handleDeleteLesson}
                    formatTime={formatTime}
                    getLessonDuration={getLessonDuration}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Сводная статистика */}
          <section className="summary-stats">
            <h2 className="summary-title">Статистика</h2>
            <div className="group-breakdown">
              <h3 className="gb-title">Группы</h3>
              {(!breakdown?.groups || breakdown.groups.length === 0) && (
                <div className="gb-empty">Нет данных по группам</div>
              )}
              {breakdown?.groups && breakdown.groups.map(g => (
                <div 
                  key={g.id} 
                  className="group-row"
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setGroupDetailModal({ isOpen: true, group: g });
                    }
                  }}
                  onClick={() => setGroupDetailModal({ isOpen: true, group: g })}
                  style={{ cursor: 'pointer', transition: 'background-color 0.2s' }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <div className="group-meta">
                    <div className="group-info">
                      <div className="group-name">{g.name}</div>
                      <div className="group-sub">Учеников: {g.students_count}</div>
                    </div>
                  </div>
                  <div className="metric-block">
                    <div className="metric-label">Посещаемость</div>
                    <ProgressBar value={g.attendance_percent} />
                    <div className="metric-value">{g.attendance_percent != null ? g.attendance_percent + '%' : '—'}</div>
                  </div>
                  <div className="metric-block">
                    <div className="metric-label">Домашнее</div>
                    <ProgressBar value={g.homework_percent} variant="homework" />
                    <div className="metric-value">{g.homework_percent != null ? g.homework_percent + '%' : '—'}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="students-breakdown">
              <h3 className="gb-title">Индивидуальные ученики</h3>
              {(!breakdown?.students || breakdown.students.length === 0) && (
                <div className="gb-empty">Нет индивидуальных учеников</div>
              )}
              {breakdown?.students && breakdown.students.map(st => (
                <div 
                  key={st.id} 
                  className="student-row"
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setStudentCardModal({ 
                        isOpen: true, 
                        studentId: st.id, 
                        groupId: st.group_id || null,
                        isIndividual: !st.group_id
                      });
                    }
                  }}
                  onClick={() => setStudentCardModal({ 
                    isOpen: true, 
                    studentId: st.id, 
                    groupId: st.group_id || null,
                    isIndividual: !st.group_id
                  })}
                  style={{ cursor: 'pointer', transition: 'background-color 0.2s' }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <div className="student-meta">
                    <div className="student-info">
                      <div className="student-name">{st.name}</div>
                      <div className="student-sub">{st.group_name || 'Индивидуальный'}</div>
                    </div>
                  </div>
                  <div className="metric-block">
                    <div className="metric-label">Посещаемость</div>
                    <ProgressBar value={st.attendance_percent} />
                    <div className="metric-value">{st.attendance_percent != null ? st.attendance_percent + '%' : '—'}</div>
                  </div>
                  <div className="metric-block">
                    <div className="metric-label">Домашнее</div>
                    <ProgressBar value={st.homework_percent} variant="homework" />
                    <div className="metric-value">{st.homework_percent != null ? st.homework_percent + '%' : '—'}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Правая колонка: прогресс и группы */}
        <aside className="sidebar">
          <section className="impact-dashboard">
            <div className="impact-header">
              <h2 className="section-title">
                Прогресс преподавателя
              </h2>
            </div>

            <TreeGrowth stage={derivedStats.levelKey} progress={derivedStats.levelProgress} />

            <div className="badge-card">
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
              </div>
            </div>

            <div className="impact-grid">
              <div className="impact-card">
                <span className="impact-label">Проведено уроков</span>
                <span className="impact-value">{derivedStats.lessonsCount}</span>
                <span className="impact-sub">завершённых занятий</span>
              </div>
              <div className="impact-card">
                <span className="impact-label">Минут на платформе</span>
                <span className="impact-value">{derivedStats.portalMinutes}</span>
                <span className="impact-sub">совместной работы</span>
              </div>
              <div className="impact-card">
                <span className="impact-label">Количество учеников</span>
                <span className="impact-value">{derivedStats.totalStudents}</span>
                <span className="impact-sub">индивидуальные + из групп</span>
              </div>
              <div className="impact-card">
                <span className="impact-label">Количество групп</span>
                <span className="impact-value">{derivedStats.totalGroups}</span>
                <span className="impact-sub">активных групп</span>
              </div>
            </div>
          </section>

        </aside>
      </div>
      
      {/* Модальное окно с детальной информацией о группе */}
      <GroupDetailModal
        group={groupDetailModal.group}
        isOpen={groupDetailModal.isOpen}
        onClose={() => setGroupDetailModal({ isOpen: false, group: null })}
        onStudentClick={(studentId, groupId) => {
          setGroupDetailModal({ isOpen: false, group: null });
          setStudentCardModal({ 
            isOpen: true, 
            studentId, 
            groupId,
            isIndividual: false
          });
        }}
      />
      
      {/* Модальное окно с карточкой ученика */}
      <StudentCardModal
        studentId={studentCardModal.studentId}
        groupId={studentCardModal.groupId}
        isIndividual={studentCardModal.isIndividual}
        isOpen={studentCardModal.isOpen}
        onClose={() => setStudentCardModal({ isOpen: false, studentId: null, groupId: null, isIndividual: false })}
      />
      
      <SupportWidget />
    </div>
  );
};

// ProgressBar уже объявлен выше

export default TeacherHomePage;
