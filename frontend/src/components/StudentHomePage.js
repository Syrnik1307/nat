import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { getLessons, getHomeworkList, getSubmissions, getGroups } from '../apiService';
import Logo from './Logo';
import JoinGroupModal from './JoinGroupModal';
import SupportWidget from './SupportWidget';
import '../styles/StudentHome.css';

const StudentHomePage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [lessons, setLessons] = useState([]);
  const [homework, setHomework] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [groups, setGroups] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [lessonsRes, hwRes, subRes, groupsRes] = await Promise.all([
        getLessons({}),
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
    }
  };

  const handleJoinSuccess = () => {
    loadData();
  };

  const getStudentsText = (count) => {
    if (count === 1) return 'ученик';
    if (count >= 2 && count <= 4) return 'ученика';
    return 'учеников';
  };

  const getInitials = () => {
    if (user?.first_name) {
      const parts = user.first_name.split(' ');
      if (parts.length > 1) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return user.first_name.substring(0, 2).toUpperCase();
    }
    if (user?.email) {
      return user.email.substring(0, 2).toUpperCase();
    }
    return 'UC';
  };

  const handleLogout = () => {
    logout();
    navigate('/auth');
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

  return (
    <div className="student-home">
      {/* Navigation Bar */}
      <nav className="student-navbar">
        <div className="student-navbar-content">
          <div className="student-navbar-left">
            <Logo size={34} />
          </div>
          
          <div className="student-navbar-center">
            <Link to="/student/courses" className="student-nav-link">
              Мои курсы
            </Link>
            <Link to="/calendar" className="student-nav-link">
              Расписание
            </Link>
            <Link to="/homework" className="student-nav-link">
              Домашнее задание
            </Link>
            <Link to="/student/stats" className="student-nav-link">
              Моя статистика
            </Link>
          </div>

          <div className="student-navbar-right">
            <div className="student-profile-section">
              <button 
                className="student-profile-button"
                onClick={() => setShowProfileMenu(!showProfileMenu)}
              >
                <div className="student-avatar">
                  {getInitials()}
                </div>
              </button>
              
              {showProfileMenu && (
                <div className="student-profile-dropdown">
                  <div className="student-profile-header">
                    Вы: {user?.first_name || user?.email || 'Ученик'}
                  </div>
                  <Link to="/profile" className="student-dropdown-item" onClick={() => setShowProfileMenu(false)}>
                    Профиль
                  </Link>
                  <Link to="/messages" className="student-dropdown-item" onClick={() => setShowProfileMenu(false)}>
                    Сообщения
                  </Link>
                  <Link to="/help" className="student-dropdown-item" onClick={() => setShowProfileMenu(false)}>
                    Вопросы и Ответы
                  </Link>
                  <button className="student-dropdown-item student-logout" onClick={handleLogout}>
                    <span>🚪</span> Выйти
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="student-main-content">
        <div className="student-container">
          <h1 className="student-page-title">Мои курсы</h1>

          {/* Today's status */}
          <div className="student-today-status">
            <div className="student-status-icon">📅</div>
            <div className="student-status-text">
              Сегодня <span className="student-status-date">Суббота, 22 ноября</span>
            </div>
          </div>

          <p className="student-status-message">{message}</p>

          {/* Course List */}
          <div className="student-courses-section">
            <div className="student-section-header">
              <h2>Список курсов</h2>
              <button onClick={() => setShowJoinModal(true)} className="student-link-button">
                Есть промокод?
              </button>
            </div>

            {groups.length === 0 ? (
              <div className="student-empty-state">
                <div className="student-empty-icon">📚</div>
                <p>У вас пока нет активных курсов</p>
                <button onClick={() => setShowJoinModal(true)} className="student-join-first-btn">
                  Присоединиться к группе
                </button>
              </div>
            ) : (
              <div className="student-courses-grid">
                {groups.map(group => (
                  <div key={group.id} className="student-course-card">
                    <div className="student-course-logo">
                      📚
                    </div>
                    <div className="student-course-info">
                      <h3>{group.name}</h3>
                      <p className="student-course-progress">
                        Преподаватель: {group.teacher?.first_name || group.teacher?.email || 'Не указан'}
                      </p>
                      <p className="student-course-students">
                        {group.student_count || 0} {getStudentsText(group.student_count || 0)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Join Group Modal */}
      {showJoinModal && (
        <JoinGroupModal 
          onClose={() => setShowJoinModal(false)}
          onSuccess={handleJoinSuccess}
        />
      )}

      {/* Floating action buttons (like in screenshots) */}
      <div className="student-floating-buttons">
        <button className="student-fab student-fab-chat" title="Чат">
          💬
        </button>
        <button className="student-fab student-fab-whatsapp" title="WhatsApp">
          📱
        </button>
        <button className="student-fab student-fab-telegram" title="Telegram">
          ✈️
        </button>
        <button className="student-fab student-fab-email" title="Email">
          ✉️
        </button>
        <button className="student-fab student-fab-support" title="Поддержка">
          🎓
        </button>
        <button className="student-fab student-fab-audio" title="Аудио">
          🎵
        </button>
      </div>
      <SupportWidget />
    </div>
  );
};

export default StudentHomePage;
