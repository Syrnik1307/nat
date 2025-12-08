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
import QuickLessonButton from './WinterQuickLessonButton';
import './TeacherHomePage.css';

const WinterNightCard = () => {
  const snowflakes = Array.from({ length: 30 }, (_, idx) => idx);
  
  return (
    <div className="winter-hero" aria-label="Зимний ночной лес с новогодней ёлкой">
      {/* Фон: ночное небо */}
      <svg className="winter-forest-bg" viewBox="0 0 400 280" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="winterSky" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#1a2642" />
            <stop offset="100%" stopColor="#2d3e5f" />
          </linearGradient>
          <radialGradient id="moonGlow" cx="80%" cy="20%" r="15%">
            <stop offset="0%" stopColor="#fffacd" stopOpacity="0.9" />
            <stop offset="40%" stopColor="#fff8dc" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#1a2642" stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width="400" height="280" fill="url(#winterSky)" />
        {/* Луна */}
        <circle cx="320" cy="60" r="25" fill="#fffacd" opacity="0.95" />
        <circle cx="315" cy="58" r="25" fill="#1a2642" opacity="0.3" />
        <ellipse cx="320" cy="60" rx="35" ry="35" fill="url(#moonGlow)" />
        {/* Звёзды */}
        {[...Array(15)].map((_, i) => {
          const x = 30 + (i * 27) % 340;
          const y = 20 + (i * 13) % 80;
          const size = 1.5 + (i % 3) * 0.5;
          return <circle key={i} cx={x} cy={y} r={size} fill="white" opacity={0.7 + (i % 3) * 0.1} />;
        })}
      </svg>

      {/* Лес с новогодней ёлкой */}
      <svg className="winter-forest" viewBox="0 0 400 280" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
        <defs>
          <linearGradient id="treeGreen" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#2d5a2d" />
            <stop offset="100%" stopColor="#1a3a1a" />
          </linearGradient>
          <radialGradient id="ornamentRed" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ff4444" />
            <stop offset="100%" stopColor="#cc0000" />
          </radialGradient>
          <radialGradient id="ornamentGold" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffd700" />
            <stop offset="100%" stopColor="#daa520" />
          </radialGradient>
          <radialGradient id="ornamentBlue" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#4da6ff" />
            <stop offset="100%" stopColor="#0066cc" />
          </radialGradient>
        </defs>
        
        {/* Дальние ёлки (тёмный фон) */}
        <g opacity="0.3">
          <g transform="translate(60, 220) scale(0.5)">
            <rect x="-3" y="20" width="6" height="30" fill="#3a3a3a" />
            <polygon points="0,0 -30,20 30,20" fill="#1a2a1a" />
            <polygon points="0,18 -32,38 32,38" fill="#0f1f0f" />
            <ellipse cx="0" cy="20" rx="32" ry="6" fill="rgba(255,255,255,0.3)" />
          </g>
          <g transform="translate(340, 230) scale(0.6)">
            <rect x="-3" y="15" width="6" height="25" fill="#3a3a3a" />
            <polygon points="0,0 -25,15 25,15" fill="#1a2a1a" />
            <polygon points="0,13 -28,28 28,28" fill="#0f1f0f" />
            <ellipse cx="0" cy="15" rx="28" ry="5" fill="rgba(255,255,255,0.3)" />
          </g>
        </g>
        
        {/* Средние ёлки по бокам (полутень) */}
        <g opacity="0.5">
          <g transform="translate(120, 210) scale(0.7)">
            <rect x="-3" y="25" width="6" height="35" fill="#4a4a3a" />
            <polygon points="0,0 -35,25 35,25" fill="#2a3a2a" />
            <polygon points="0,22 -38,45 38,45" fill="#1a2a1a" />
            <ellipse cx="0" cy="25" rx="38" ry="8" fill="rgba(255,255,255,0.4)" />
            <ellipse cx="0" cy="45" rx="40" ry="8" fill="rgba(255,255,255,0.35)" />
          </g>
          <g transform="translate(280, 215) scale(0.65)">
            <rect x="-3" y="22" width="6" height="32" fill="#4a4a3a" />
            <polygon points="0,0 -32,22 32,22" fill="#2a3a2a" />
            <polygon points="0,20 -35,40 35,40" fill="#1a2a1a" />
            <ellipse cx="0" cy="22" rx="35" ry="7" fill="rgba(255,255,255,0.4)" />
            <ellipse cx="0" cy="40" rx="37" ry="7" fill="rgba(255,255,255,0.35)" />
          </g>
        </g>
        
        {/* Главная новогодняя ёлка (по центру, самая яркая) */}
        {/* Ствол ёлки */}
        <rect x="185" y="220" width="30" height="50" rx="4" fill="#5a4a3a" />
        
        {/* Ярусы ёлки (снизу вверх) */}
        <polygon points="200,220 120,220 200,160" fill="url(#treeGreen)" />
        <polygon points="200,220 280,220 200,160" fill="#1a4a1a" />
        
        <polygon points="200,175 130,175 200,125" fill="url(#treeGreen)" />
        <polygon points="200,175 270,175 200,125" fill="#1a4a1a" />
        
        <polygon points="200,140 145,140 200,95" fill="url(#treeGreen)" />
        <polygon points="200,140 255,140 200,95" fill="#1a4a1a" />
        
        <polygon points="200,110 160,110 200,70" fill="url(#treeGreen)" />
        <polygon points="200,110 240,110 200,70" fill="#1a4a1a" />
        
        <polygon points="200,85 175,85 200,55" fill="url(#treeGreen)" />
        <polygon points="200,85 225,85 200,55" fill="#1a4a1a" />
        
        {/* Снег на ветвях */}
        <ellipse cx="200" cy="220" rx="85" ry="12" fill="rgba(255,255,255,0.75)" />
        <ellipse cx="200" cy="175" rx="72" ry="10" fill="rgba(255,255,255,0.75)" />
        <ellipse cx="200" cy="140" rx="58" ry="9" fill="rgba(255,255,255,0.75)" />
        <ellipse cx="200" cy="110" rx="42" ry="7" fill="rgba(255,255,255,0.75)" />
        <ellipse cx="200" cy="85" rx="26" ry="6" fill="rgba(255,255,255,0.75)" />
        
        {/* Новогодние игрушки */}
        <circle cx="170" cy="200" r="8" fill="url(#ornamentRed)" opacity="0.9" />
        <circle cx="230" cy="195" r="7" fill="url(#ornamentGold)" opacity="0.9" />
        <circle cx="150" cy="165" r="6" fill="url(#ornamentBlue)" opacity="0.9" />
        <circle cx="250" cy="160" r="6" fill="url(#ornamentRed)" opacity="0.9" />
        <circle cx="185" cy="150" r="5" fill="url(#ornamentGold)" opacity="0.9" />
        <circle cx="215" cy="145" r="5" fill="url(#ornamentBlue)" opacity="0.9" />
        <circle cx="175" cy="120" r="4" fill="url(#ornamentRed)" opacity="0.9" />
        <circle cx="225" cy="115" r="4" fill="url(#ornamentGold)" opacity="0.9" />
        <circle cx="190" cy="95" r="3.5" fill="url(#ornamentBlue)" opacity="0.9" />
        <circle cx="210" cy="92" r="3.5" fill="url(#ornamentRed)" opacity="0.9" />
        
        {/* Золотая звезда на вершине */}
        <g transform="translate(200, 50)">
          <polygon points="0,-15 4,-5 15,-5 6,2 9,13 0,7 -9,13 -6,2 -15,-5 -4,-5" 
                   fill="#ffd700" 
                   stroke="#daa520" 
                   strokeWidth="1"
                   filter="drop-shadow(0 0 6px rgba(255, 215, 0, 0.8))" />
        </g>
        
        {/* Снег на земле */}
        <ellipse cx="200" cy="270" rx="120" ry="8" fill="rgba(255,255,255,0.85)" />
        <rect x="0" y="262" width="400" height="18" fill="#f5f9fc" />
      </svg>

      {/* Падающие снежинки */}
      <div className="winter-snow" aria-hidden="true">
        {snowflakes.map((flake) => {
          const leftPos = Math.random() * 100;
          const duration = 10 + Math.random() * 8;
          const delay = Math.random() * 5;
          const size = 3 + Math.random() * 5;
          
          return (
            <span 
              key={flake} 
              className="snowflake" 
              style={{
                left: `${leftPos}%`,
                width: `${size}px`,
                height: `${size}px`,
                animationDuration: `${duration}s`,
                animationDelay: `${delay}s`,
                boxShadow: `0 0 ${size + 3}px rgba(255,255,255,0.95), 0 0 ${size * 2}px rgba(200,230,255,0.7)`
              }} 
            />
          );
        })}
      </div>
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
        name: '⛄ Снежное поле',
        minMinutes: 0,
        description: 'Зимняя база для будущего леса знаний. Снег укрывает землю, готовясь к весне.',
      },
      {
        key: 'sprout',
        name: '☃️ Снеговик-новичок',
        minMinutes: 600,
        description: 'Первые 10 часов занятий превращаются в маленького снеговика!',
      },
      {
        key: 'sapling',
        name: '🎄 Ёлка молодая',
        minMinutes: 6000,
        description: '100 часов совместной работы украшают ёлку игрушками.',
      },
      {
        key: 'tree',
        name: '🎁 Большая ёлка с подарками',
        minMinutes: 12000,
        description: 'После 200 часов ваша ёлка дарит радость целому поколению.',
      },
      {
        key: 'ancient',
        name: '⭐ Волшебная ёлка',
        minMinutes: 24000,
        description: 'Легендарная ёлка знаний со звездой на вершине, которой восхищаются все!',
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
          background: 'linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%)',
          color: 'white',
          padding: '16px 24px',
          borderRadius: '12px',
          boxShadow: '0 10px 40px rgba(37, 99, 235, 0.4)',
          animation: 'slideInRight 0.5s ease',
          maxWidth: '400px',
          border: '2px solid rgba(255, 255, 255, 0.3)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ fontSize: '24px' }}>🎉</div>
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
          <QuickLessonButton onSuccess={loadData} />
          <button 
            type="button" 
            className="header-message-button" 
            aria-label="Записи уроков"
            onClick={() => navigate('/teacher/recordings')}
            style={{ marginLeft: '1rem' }}
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

            <WinterNightCard />

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
