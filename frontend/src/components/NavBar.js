import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import { getAccessToken, getTeacherStatsSummary } from '../apiService';
import './NavBar.css';

const NavBar = () => {
  const { accessTokenValid, role, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [hideStatus, setHideStatus] = useState(false);
  const [pendingHomeworkCount, setPendingHomeworkCount] = useState(0);

  useEffect(() => {
    if (accessTokenValid) {
      loadMessages();
      const interval = setInterval(loadMessages, 30000);
      return () => clearInterval(interval);
    }
  }, [accessTokenValid]);

  useEffect(() => {
    if (!accessTokenValid || role !== 'teacher') return;

    let isMounted = true;
    const loadPendingHomework = async () => {
      try {
        const res = await getTeacherStatsSummary();
        const pending = Number(res?.data?.pending_submissions || 0);
        if (isMounted) setPendingHomeworkCount(pending);
      } catch (error) {
        if (isMounted) setPendingHomeworkCount(0);
      }
    };

    loadPendingHomework();
    const interval = setInterval(loadPendingHomework, 60000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [accessTokenValid, role]);

  useEffect(() => {
    if (messages.length > 1) {
      const interval = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % messages.length);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [messages.length]);

  const loadMessages = async () => {
    try {
      const token = getAccessToken();
      console.log('Loading messages, token:', token ? 'exists' : 'missing');
      const response = await fetch('/accounts/api/status-messages/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      console.log('Response status:', response.status);
      const data = await response.json();
      console.log('Messages data:', data);
      const activeMessages = data.filter(msg => msg.is_active);
      console.log('Active messages:', activeMessages);
      setMessages(activeMessages);
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error);
    }
  };

  const currentMessage = messages.length > 0 ? messages[currentIndex] : null;

  return (
    <>
      <nav className="navbar-new">
        <div className="navbar-container">
          {/* Left: Brand Logo - STYLED LIKE AUTH PAGE */}
          <div className="navbar-logo">
            <h1>
              <span className="brand-primary">Lectio</span>
              <span className="brand-secondary">Space</span>
            </h1>
          </div>

          {/* Center: Navigation Links */}
          <div className="navbar-center">
            <Link className="navbar-link" to="/">Главная</Link>
            {accessTokenValid && role === 'teacher' && (
              <>
                <Link className="navbar-link" to="/groups/manage">Занятия</Link>
                <Link className="navbar-link" to="/homework/manage">
                  ДЗ
                  {pendingHomeworkCount > 0 && (
                    <span className="navbar-link-badge">{pendingHomeworkCount}</span>
                  )}
                </Link>
                <Link className="navbar-link" to="/recurring-lessons/manage">Расписание</Link>
                <Link className="navbar-link" to="/calendar">Календарь</Link>
                <Link className="navbar-link" to="/teacher-recordings">Записи</Link>
                <Link className="navbar-link" to="/analytics">Аналитика</Link>
              </>
            )}
            {accessTokenValid && role === 'student' && (
              <>
                <Link className="navbar-link" to="/student">Мои курсы</Link>
                <Link className="navbar-link" to="/homework">ДЗ</Link>
                <Link className="navbar-link" to="/calendar">Календарь</Link>
              </>
            )}
            {accessTokenValid && role === 'admin' && (
              <>
                <Link className="navbar-link" to="/admin-home">Панель</Link>
                <Link className="navbar-link" to="/groups/manage">Группы</Link>
              </>
            )}
          </div>

          {/* Right: Actions & Profile */}
          <div className="navbar-right">
            {!accessTokenValid && (
              <>
                <Link className="navbar-link" to="/login">Войти</Link>
              </>
            )}
            {accessTokenValid && (
              <>
                {/* Notifications Icon */}
                <button className="navbar-icon-button" title="Уведомления">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                    <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                  </svg>
                  <span className="navbar-icon-badge"></span>
                </button>

                {/* Messages Icon */}
                <button className="navbar-icon-button" title="Сообщения">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                </button>

                {/* Profile */}
                <div className="navbar-profile">
                  <button className="navbar-profile-button">
                    <span className="navbar-profile-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5Z" />
                        <path d="M3 21c0-4.5 3.5-6.5 9-6.5s9 2 9 6.5" />
                      </svg>
                    </span>
                    <span>Профиль</span>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Status Bar Messages */}
      {accessTokenValid && currentMessage && !hideStatus && (
        <div className="navbar-status">
          <div className="status-inner">
            <span className="status-message">
              {currentMessage.message}
            </span>
            <button className="status-action" onClick={() => setHideStatus(true)}>
              скрыть
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default NavBar;
