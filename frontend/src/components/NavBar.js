import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import './NavBar.css';

const NavBar = () => {
  const { accessTokenValid, role, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [hideStatus, setHideStatus] = useState(false);

  useEffect(() => {
    if (accessTokenValid) {
      loadMessages();
      const interval = setInterval(loadMessages, 30000);
      return () => clearInterval(interval);
    }
  }, [accessTokenValid]);

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
      const token = localStorage.getItem('tp_access_token');
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
          {/* Left: Brand Logo */}
          <div className="navbar-logo">
            <h1>Lectio Space</h1>
          </div>

          {/* Center: Navigation Links */}
          <div className="navbar-center">
            <Link className="navbar-link" to="/">Главная</Link>
            {accessTokenValid && role === 'teacher' && (
              <>
                <Link className="navbar-link" to="/groups/manage">Занятия</Link>
                <Link className="navbar-link" to="/homework/manage">ДЗ</Link>
                <Link className="navbar-link" to="/recurring-lessons/manage">Расписание</Link>
                <Link className="navbar-link" to="/calendar">Календарь</Link>
                <Link className="navbar-link" to="/teacher-recordings">Записи</Link>
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
                    <span>👤</span>
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
