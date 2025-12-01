import React, { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import Logo from './Logo';
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
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const [bannerVisible, setBannerVisible] = useState(true);
  const [messages, setMessages] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const profileButtonRef = useRef(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, right: 0 });

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

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768 && showMobileMenu) {
        setShowMobileMenu(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [showMobileMenu]);

  useEffect(() => {
    if (showMobileMenu) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
      setShowLessonsMenu(false);
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [showMobileMenu]);

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768 && showMobileMenu) {
        setShowMobileMenu(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [showMobileMenu]);

  useEffect(() => {
    if (showMobileMenu) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
      setShowLessonsMenu(false);
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [showMobileMenu]);

  const loadMessages = async () => {
    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('/accounts/api/status-messages/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      // Проверяем статус ответа
      if (!response.ok) {
        console.warn('Статус-сообщения недоступны:', response.status);
        return;
      }
      
      // Проверяем, что ответ действительно JSON
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        console.warn('Получен не-JSON ответ от /accounts/api/status-messages/');
        return;
      }
      
      const data = await response.json();
      const activeMessages = Array.isArray(data) ? data.filter(msg => msg.is_active) : [];
      setMessages(activeMessages);
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error);
      setMessages([]); // Устанавливаем пустой массив при ошибке
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
    if (role === 'admin') return '/admin-home';
    return '/auth-new';
  })();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const teacherMessages = messages.filter(m => m.target === 'teachers' || m.target === 'all');
  const studentMessages = messages.filter(m => m.target === 'students' || m.target === 'all');
  const currentMessage = messages.length > 0 ? messages[currentIndex] : null;

  const updateProfileMenuPosition = () => {
    if (!profileButtonRef.current) return;
    const rect = profileButtonRef.current.getBoundingClientRect();
    setMenuPosition({
      top: rect.bottom + window.scrollY + 12,
      right: window.innerWidth - rect.right - window.scrollX,
    });
  };

  useEffect(() => {
    if (!showProfileMenu) {
      return undefined;
    }

    updateProfileMenuPosition();
    window.addEventListener('scroll', updateProfileMenuPosition);
    window.addEventListener('resize', updateProfileMenuPosition);

    return () => {
      window.removeEventListener('scroll', updateProfileMenuPosition);
      window.removeEventListener('resize', updateProfileMenuPosition);
    };
  }, [showProfileMenu]);

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
        <Link to={homePath} className="navbar-logo" aria-label="Teaching Panel">
          <Logo size={34} />
          <span className="logo-text">Teaching Panel</span>
        </Link>

        {/* Навигационное меню */}
        <div className={`navbar-menu ${showMobileMenu ? 'mobile-open' : ''}`}>
          {/* Общие пункты */}
          <Link 
            to={homePath} 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
          >
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
                      onClick={() => { setShowLessonsMenu(false); setShowMobileMenu(false); }}
                      role="menuitem"
                    >
                      <span className="item-icon">📆</span>
                      <span>Календарь</span>
                    </Link>
                    <Link
                      to="/recurring-lessons/manage"
                      className="nav-dropdown-item"
                      onClick={() => { setShowLessonsMenu(false); setShowMobileMenu(false); }}
                      role="menuitem"
                    >
                      <span className="item-icon">➕</span>
                      <span>Создать занятие</span>
                    </Link>
                  </div>
                )}
              </div>
              
              <Link 
                to="/homework/manage" 
                className="nav-link"
                onClick={() => setShowMobileMenu(false)}
              >
                <span className="nav-icon">📝</span>
                <span>Конструктор ДЗ</span>
              </Link>
              
              <Link 
                to="/groups/manage" 
                className="nav-link"
                onClick={() => setShowMobileMenu(false)}
              >
                <span className="nav-icon">👥</span>
                <span>Управление учениками</span>
              </Link>
              
              <Link 
                to="/materials" 
                className="nav-link"
                onClick={() => setShowMobileMenu(false)}
              >
                <span className="nav-icon">📚</span>
                <span>Материалы</span>
              </Link>
              
              <Link 
                to="/teacher/subscription" 
                className="nav-link"
                onClick={() => setShowMobileMenu(false)}
              >
                <span className="nav-icon">💳</span>
                <span>Подписка</span>
              </Link>
            </>
          )}

          {/* Меню для ученика */}
          {accessTokenValid && role === 'student' && (
            <>
              <Link 
                to="/student" 
                className="nav-link"
                onClick={() => setShowMobileMenu(false)}
              >
                <span className="nav-icon">📚</span>
                <span>Мои курсы</span>
              </Link>
              
              <Link 
                to="/homework" 
                className="nav-link"
                onClick={() => setShowMobileMenu(false)}
              >
                <span className="nav-icon">📝</span>
                <span>Домашние задания</span>
              </Link>
              
              <Link 
                to="/calendar" 
                className="nav-link"
                onClick={() => setShowMobileMenu(false)}
              >
                <span className="nav-icon">📆</span>
                <span>Календарь</span>
              </Link>
            </>
          )}

          {/* Меню для админа */}
          {accessTokenValid && role === 'admin' && (
            <Link 
              to="/admin-home" 
              className="nav-link nav-link-highlight"
              onClick={() => setShowMobileMenu(false)}
            >
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
                ref={profileButtonRef}
                onClick={() => {
                  if (!showProfileMenu) {
                    updateProfileMenuPosition();
                  }
                  setShowProfileMenu(!showProfileMenu);
                }}
                aria-label="Меню профиля"
              >
                <div className="avatar" aria-hidden="true">
                  {user?.avatar ? (
                    <img src={user.avatar} alt="Аватар" />
                  ) : (
                    <span className="avatar-initial">
                      {(user?.first_name || user?.email || 'U').charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>
                <span className="profile-name">
                  {user?.first_name || 'Пользователь'}
                </span>
                <span className={`chevron ${showProfileMenu ? 'open' : ''}`}>
                  ▼
                </span>
              </button>

              {showProfileMenu && createPortal(
                <div
                  className="profile-dropdown"
                  style={{ position: 'fixed', top: menuPosition.top, right: menuPosition.right, zIndex: 6500 }}
                >
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
                </div>,
                document.body
              )}
            </div>
          )}
        </div>

        {/* Burger button для мобильных */}
        <button 
          className={`burger-button ${showMobileMenu ? 'open' : ''}`}
          onClick={() => setShowMobileMenu(!showMobileMenu)}
          aria-label="Toggle menu"
        >
          <span className={`burger-line ${showMobileMenu ? 'open' : ''}`}></span>
          <span className={`burger-line ${showMobileMenu ? 'open' : ''}`}></span>
          <span className={`burger-line ${showMobileMenu ? 'open' : ''}`}></span>
        </button>

        {/* Overlay для закрытия меню */}
        {showMobileMenu && (
          <div 
            className="mobile-menu-overlay"
            onClick={() => setShowMobileMenu(false)}
          />
        )}
      </div>
      </nav>
    </>
  );
};

export default NavBar;
