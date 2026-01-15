import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getLessons, getHomeworkList, getSubmissions, getGroups, joinLesson } from '../apiService';
import JoinGroupModal from './JoinGroupModal';
import SupportWidget from './SupportWidget';
import { Button, StudentDashboardSkeleton } from '../shared/components';
import '../styles/StudentHome.css';

// Calendar SVG Icon
const IconCalendar = ({ size = 16, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
    <line x1="16" x2="16" y1="2" y2="6"/>
    <line x1="8" x2="8" y1="2" y2="6"/>
    <line x1="3" x2="21" y1="10" y2="10"/>
  </svg>
);

const StudentHomePage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [lessons, setLessons] = useState([]);
  const [homework, setHomework] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [groups, setGroups] = useState([]);
  const [inviteCodeFromUrl, setInviteCodeFromUrl] = useState('');
  const [joinLoading, setJoinLoading] = useState(false);
  const [joinError, setJoinError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get('code');
    if (code) {
      setInviteCodeFromUrl(code);
      setShowJoinModal(true);
      navigate('/student', { replace: true });
    }
  }, [location.search, navigate]);

  useEffect(() => {
    if (showJoinModal) {
      document.body.style.overflow = 'hidden';
      document.documentElement.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
      document.documentElement.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
      document.documentElement.style.overflow = '';
    };
  }, [showJoinModal]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const now = new Date();
      const in30 = new Date();
      in30.setDate(now.getDate() + 30);
      const [lessonsRes, hwRes, subRes, groupsRes] = await Promise.all([
        getLessons({
          start: now.toISOString(),
          end: in30.toISOString(),
          include_recurring: true,
        }),
        getHomeworkList({}),
        getSubmissions({}),
        getGroups(),
      ]);
      setLessons(Array.isArray(lessonsRes.data) ? lessonsRes.data : lessonsRes.data.results || []);
      const hwList = Array.isArray(hwRes.data) ? hwRes.data : hwRes.data.results || [];
      setHomework(hwList);
      const subsList = Array.isArray(subRes.data) ? subRes.data : subRes.data.results || [];
      setSubmissions(subsList);
      const groupsList = Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || [];
      setGroups(groupsList);
    } catch (e) {
      console.error('Error loading data:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleJoinSuccess = () => {
    setInviteCodeFromUrl(''); // Clear the code after successful join
    loadData();
  };

  const getStudentsText = (count) => {
    if (count === 1) return 'ученик';
    if (count >= 2 && count <= 4) return 'ученика';
    return 'учеников';
  };

  const getCourseLabel = (name) => {
    if (!name) return 'CS';
    return name.trim().slice(0, 2).toUpperCase();
  };

  // Calculate stats
  const submissionIndex = submissions.reduce((acc, s) => { acc[s.homework] = s; return acc; }, {});
  const decoratedHomework = homework.map(hw => {
    const sub = submissionIndex[hw.id];
    return {
      ...hw,
      submission_status: sub ? sub.status : 'not_submitted',
    };
  });
  const pendingHomework = decoratedHomework.filter(hw => hw.submission_status === 'not_submitted');

  const today = new Date();
  const todayLessons = lessons.filter(l => {
    const lessonDate = new Date(l.start_time);
    return lessonDate.toDateString() === today.toDateString();
  });

  const hasLessonsToday = todayLessons.length > 0;
  const message = hasLessonsToday 
    ? `Сегодня у вас ${todayLessons.length} ${todayLessons.length === 1 ? 'занятие' : 'занятия'}`
    : 'Сегодня либо нет занятий, либо они уже закончились';

  // Выбираем ближайший урок сегодня (если несколько)
  const nextTodayLesson = hasLessonsToday
    ? [...todayLessons]
        .filter(l => !!l.start_time)
        .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))[0]
    : null;

  const formatTimeHHMM = (dt) => {
    if (!dt) return '';
    const d = new Date(dt);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const nextLessonTimeText = (() => {
    if (!nextTodayLesson?.start_time) return '';
    const startText = formatTimeHHMM(nextTodayLesson.start_time);
    const endText = formatTimeHHMM(nextTodayLesson.end_time);
    if (!startText) return '';
    return endText ? `${startText}–${endText}` : startText;
  })();

  const handleJoinLesson = async () => {
    if (!nextTodayLesson || !nextTodayLesson.id) return;

    // Виртуальные уроки из recurring (id строковый), к ним join невозможен
    if (typeof nextTodayLesson.id !== 'number') {
      setJoinError('Ссылка появится, когда преподаватель создаст/запустит урок.');
      return;
    }

    setJoinError('');
    setJoinLoading(true);
    try {
      const resp = await joinLesson(nextTodayLesson.id);
      // Используем универсальную ссылку (поддерживает Zoom и Google Meet)
      const url = resp?.data?.join_url || resp?.data?.zoom_join_url;
      const platform = resp?.data?.platform;
      
      if (!url) {
        setJoinError('Ссылка пока недоступна. Попробуйте позже.');
        return;
      }
      
      // Для Google Meet показываем предупреждение о необходимости Google аккаунта
      if (platform === 'google_meet') {
        const confirmed = window.confirm(
          'Для входа в Google Meet вам потребуется Google аккаунт.\n\n' +
          'Если у вас нет Google аккаунта, создайте его бесплатно на google.com\n\n' +
          'Нажмите OK, чтобы перейти к уроку.'
        );
        if (!confirmed) {
          setJoinLoading(false);
          return;
        }
      }
      
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (e) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail;
      if (status === 409) {
        setJoinError(detail || 'Ссылка появится, когда преподаватель начнёт занятие.');
      } else if (status === 403) {
        setJoinError(detail || 'Нет доступа к этому уроку.');
      } else {
        setJoinError(detail || e?.message || 'Не удалось получить ссылку.');
      }
    } finally {
      setJoinLoading(false);
    }
  };

  // Format today's date in Russian
  const formatTodayDate = () => {
    const days = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота'];
    const months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
    const dayName = days[today.getDay()];
    const day = today.getDate();
    const month = months[today.getMonth()];
    return `${dayName.charAt(0).toUpperCase() + dayName.slice(1)}, ${day} ${month}`;
  };

  // Show skeleton while loading
  if (isLoading) {
    return (
      <div className="student-home">
        <StudentDashboardSkeleton />
        {!showJoinModal && <SupportWidget />}
      </div>
    );
  }

  return (
    <div className="student-home">
      <main className="student-main-content">
        <div className="student-container">
          <h1 className="student-page-title">Мои курсы</h1>

          {/* Today's status - compact */}
          <div className="student-today-banner">
            <span className="student-today-date">
              <IconCalendar size={16} className="student-today-icon" />
              {formatTodayDate()}
            </span>
            <span className="student-today-separator">•</span>
            <span className={`student-today-status-text ${hasLessonsToday ? 'has-lessons' : ''}`}>
              {message}
            </span>

            {hasLessonsToday && nextLessonTimeText && (
              <>
                <span className="student-today-separator">•</span>
                <span className="student-today-next-time">
                  Ближайшее: {nextLessonTimeText}
                </span>
              </>
            )}

            {hasLessonsToday && (
              <div className="student-today-actions">
                <Button
                  variant="primary"
                  size="small"
                  loading={joinLoading}
                  onClick={handleJoinLesson}
                >
                  Присоединиться
                </Button>
              </div>
            )}
          </div>

          {joinError && (
            <div className="student-today-join-error" role="alert">
              {joinError}
            </div>
          )}

          {/* Today's Lessons with Topics */}
          {todayLessons.length > 0 && (
            <div className="student-lessons-today">
              <h2 className="student-section-title">Расписание на сегодня</h2>
              <div className="student-lessons-list">
                {todayLessons.map((lesson) => (
                  <div key={lesson.id} className="student-lesson-card">
                    <div className="student-lesson-time">
                      {formatTimeHHMM(lesson.start_time)} – {formatTimeHHMM(lesson.end_time)}
                    </div>
                    <div className="student-lesson-info">
                      <div className="student-lesson-group">{lesson.group_name || lesson.display_name || 'Группа'}</div>
                      {lesson.title && (
                        <div className="student-lesson-topic">Тема: {lesson.title}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Course List */}
          <div className="student-courses-section">
            <div className="student-section-header">
              <h2>Список курсов</h2>
              <button type="button" onClick={() => setShowJoinModal(true)} className="student-link-button">
                Есть промокод?
              </button>
            </div>

            {groups.length === 0 ? (
              <div className="student-empty-state">
                <div className="student-empty-icon-style" />
                <p>У вас пока нет активных курсов</p>
                <button onClick={() => setShowJoinModal(true)} className="student-join-first-btn">
                  Присоединиться к группе
                </button>
              </div>
            ) : (
              <div className="student-courses-grid">
                {groups.map(group => {
                  const studentCount = group.student_count || 0;
                  const teacherName = group.teacher?.first_name || group.teacher?.email || 'Не указан';

                  return (
                    <div key={group.id} className="student-course-card">
                      <div className="student-course-top">
                        <div className="student-course-badge">{getCourseLabel(group.name)}</div>
                        <div className="student-course-main">
                          <h3 className="student-course-title">{group.name}</h3>
                          <div className="student-course-chips">
                            <span className="student-chip">
                              <span className="student-chip-label">Преподаватель</span>
                              <span className="student-chip-value">{teacherName}</span>
                            </span>
                            <span className="student-chip student-chip-muted">
                              {studentCount} {getStudentsText(studentCount)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Join Group Modal */}
      {showJoinModal && (
        <JoinGroupModal 
          onClose={() => {
            setShowJoinModal(false);
            setInviteCodeFromUrl('');
          }}
          onSuccess={handleJoinSuccess}
          initialCode={inviteCodeFromUrl}
        />
      )}

      {!showJoinModal && <SupportWidget />}
    </div>
  );
};

export default StudentHomePage;
