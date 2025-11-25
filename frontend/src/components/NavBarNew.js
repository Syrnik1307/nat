import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import './NavBar.css';

/**
 * Навигационная панель
 * 
 * Обновленная версия с синей цветовой схемой
 * 
 * Меню для преподавателя:
 * - Главная
 * - Занятия (бывшее "Расписание")
 * - Конструктор ДЗ (бывшее "Шаблоны")
 * - Управление учениками (бывшее "Управление группами")
 * - Календарь
 * - Материалы
 * 
 * Убрано:
 * - Личные беседы
 * - Шаблоны
 */

const NavBar = () => {
  const { accessTokenValid, role, logout, user } = useAuth();
  const navigate = useNavigate();
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showLessonsMenu, setShowLessonsMenu] = useState(false);
  const [bannerVisible, setBannerVisible] = useState(true);
  const [messages, setMessages] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);

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
      const base = process.env.REACT_APP_API_BASE_URL || 'http://72.56.81.163:8001/api/';
      const response = await fetch(base + 'accounts/api/status-messages/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      const activeMessages = data.filter(msg => msg.is_active);
      setMessages(activeMessages);
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error);
    }
  };

  useEffect(() => {
    if (!(accessTokenValid && role === 'teacher')) {
      setShowLessonsMenu(false);
    }
  }, [accessTokenValid, role]);

  const homePath = (() => {
    if (!accessTokenValid) return '/auth-new';
    if (role === 'teacher') return '/home-new';
    if (role === 'student') return '/student';
    if (role === 'admin') return '/admin';
    return '/auth-new';
  })();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const teacherMessages = messages.filter(m => m.target === 'teachers' || m.target === 'all');
  const studentMessages = messages.filter(m => m.target === 'students' || m.target === 'all');
  const currentMessage = messages.length > 0 ? messages[currentIndex] : null;

  return (
    <>
      {/* Status Bar - для админа две колонки, для остальных одна */}
      {bannerVisible && accessTokenValid && (
        role === 'admin' ? (
          // Админ видит две колонки
          teacherMessages.length > 0 || studentMessages.length > 0 ? (
            <div className="navbar-status admin-status">
              <div className="status-split">
                {/* Левая часть - для учителей */}
                <div className="status-half status-teachers">
                  <div className="status-label">👨‍🏫 Учителям</div>
                  {teacherMessages.length > 0 ? (
                    <span className="status-message">{teacherMessages[0].message}</span>
                  ) : (
                    <span className="status-empty">Нет сообщений</span>
                  )}
                </div>
                
                {/* Правая часть - для учеников */}
                <div className="status-half status-students">
                  <div className="status-label">🎓 Ученикам</div>
                  {studentMessages.length > 0 ? (
                    <span className="status-message">{studentMessages[0].message}</span>
                  ) : (
                    <span className="status-empty">Нет сообщений</span>
                  )}
                </div>
                
                <button className="status-action" onClick={() => setBannerVisible(false)}>
                  скрыть
                </button>
              </div>
            </div>
          ) : null
        ) : (
          // Учителя/студенты видят одну колонку
          currentMessage && (
            <div className="navbar-status">
              <div className="status-inner">
                <span className="status-message">
                  {currentMessage.message}
                </span>
                <button className="status-action" onClick={() => setBannerVisible(false)}>
                  скрыть
                </button>
              </div>
            </div>
          )
        )
      )}
      <nav className="navbar">
        <div className="navbar-container">
        {/* Логотип */}
        <Link to={homePath} className="navbar-logo">
          <span className="logo-icon">📚</span>
          <span className="logo-text">Teaching Panel</span>
        </Link>

        {/* Навигационное меню */}
        <div className="navbar-menu">
          {/* Общие пункты */}
          <Link to={homePath} className="nav-link">
            <span className="nav-icon">🏠</span>
            <span>Главная</span>
          </Link>

          {/* Меню для преподавателя */}
          {accessTokenValid && role === 'teacher' && (
            <>
              <div 
                className={`nav-dropdown ${showLessonsMenu ? 'open' : ''}`}
                onMouseLeave={() => setShowLessonsMenu(false)}
              >
                <button
                  type="button"
                  className="nav-link nav-dropdown-trigger"
                  onClick={() => setShowLessonsMenu(prev => !prev)}
                  onMouseEnter={() => setShowLessonsMenu(true)}
                  aria-haspopup="true"
                  aria-expanded={showLessonsMenu}
                >
                  <span className="nav-icon">📅</span>
                  <span>Занятия</span>
                  <span className={`caret ${showLessonsMenu ? 'open' : ''}`}>▾</span>
                </button>
                {showLessonsMenu && (
                  <div className="nav-dropdown-menu" role="menu">
                    <Link
                      to="/calendar"
                      className="nav-dropdown-item"
                      onClick={() => setShowLessonsMenu(false)}
                      role="menuitem"
                    >
                      <span className="item-icon">📆</span>
                      <span>Календарь</span>
                    </Link>
                    <Link
                      to="/recurring-lessons/manage"
                      className="nav-dropdown-item"
                      onClick={() => setShowLessonsMenu(false)}
                      role="menuitem"
                    >
                      <span className="item-icon">➕</span>
                      <span>Создать занятие</span>
                    </Link>
                  </div>
                )}
              </div>
              
              <Link to="/homework/manage" className="nav-link">
                <span className="nav-icon">📝</span>
                <span>Конструктор ДЗ</span>
              </Link>
              
              <Link to="/groups/manage" className="nav-link">
                <span className="nav-icon">👥</span>
                <span>Управление учениками</span>
              </Link>
              
              <Link to="/materials" className="nav-link">
                <span className="nav-icon">📚</span>
                <span>Материалы</span>
              </Link>
            </>
          )}

          {/* Меню для ученика */}
          {accessTokenValid && role === 'student' && (
            <>
              <Link to="/student" className="nav-link">
                <span className="nav-icon">📚</span>
                <span>Мои курсы</span>
              </Link>
              
              <Link to="/homework" className="nav-link">
                <span className="nav-icon">📝</span>
                <span>Домашние задания</span>
              </Link>
              
              <Link to="/calendar" className="nav-link">
                <span className="nav-icon">📆</span>
                <span>Календарь</span>
              </Link>
            </>
          )}

          {/* Меню для админа */}
          {accessTokenValid && role === 'admin' && (
            <Link to="/admin" className="nav-link nav-link-highlight">
              <span className="nav-icon">🔧</span>
              <span>Админ-панель</span>
            </Link>
          )}
        </div>

        {/* Правая часть: кнопки входа или профиль */}
        <div className="navbar-actions">
          {!accessTokenValid ? (
            <>
              <Link to="/login" className="btn-login">
                Войти
              </Link>
            </>
          ) : (
            <div className="profile-menu-container">
              <button 
                className="profile-button"
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                aria-label="Меню профиля"
              >
                <div className="avatar">
                  {user?.avatar ? (
                    <img src={user.avatar} alt="Аватар" />
                  ) : (
                    <span className="avatar-icon">👤</span>
                  )}
                </div>
                <span className="profile-name">
                  {user?.first_name || 'Пользователь'}
                </span>
                <span className={`chevron ${showProfileMenu ? 'open' : ''}`}>
                  ▼
                </span>
              </button>

              {showProfileMenu && (
                <div className="profile-dropdown">
                  <div className="dropdown-header">
                    <div className="user-info">
                      <p className="user-name">
                        {user?.first_name} {user?.last_name}
                      </p>
                      <p className="user-role">
                        {role === 'teacher' ? 'Учитель' : 
                         role === 'student' ? 'Ученик' : 'Администратор'}
                      </p>
                    </div>
                  </div>
                  
                  <div className="dropdown-divider"></div>
                  
                  <Link 
                    to="/profile" 
                    className="dropdown-item"
                    onClick={() => setShowProfileMenu(false)}
                  >
                    <span>⚙️</span>
                    <span>Настройки профиля</span>
                  </Link>
                  
                  <button 
                    className="dropdown-item"
                    onClick={handleLogout}
                  >
                    <span>🚪</span>
                    <span>Выйти</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      </nav>
    </>
  );
};

export default NavBar;
