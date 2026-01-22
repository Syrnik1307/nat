import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';
import { prefetch } from '../utils/dataCache';
import { getLessons, getHomeworkList, getSubmissions, getGroups } from '../apiService';
import '../styles/StudentNavBar.css';

// SVG Icons для мобильного меню
const IconMenu = ({ size = 24 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="12" x2="21" y2="12"/>
    <line x1="3" y1="6" x2="21" y2="6"/>
    <line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
);

const IconX = ({ size = 24 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

// Prefetch функции для разных страниц
const prefetchStudentData = () => {
  const now = new Date();
  const in30 = new Date();
  in30.setDate(now.getDate() + 30);
  
  prefetch('student:lessons', () => getLessons({
    start: now.toISOString(),
    end: in30.toISOString(),
    include_recurring: true,
  }).then(res => Array.isArray(res.data) ? res.data : res.data.results || []));
  
  prefetch('student:groups', () => getGroups()
    .then(res => Array.isArray(res.data) ? res.data : res.data.results || []));
};

const prefetchHomeworkData = () => {
  prefetch('student:homework:list', () => getHomeworkList({})
    .then(res => Array.isArray(res.data) ? res.data : res.data.results || []));
  
  prefetch('student:homework:submissions', () => getSubmissions({})
    .then(res => Array.isArray(res.data) ? res.data : res.data.results || []));
  
  prefetch('student:groups', () => getGroups()
    .then(res => Array.isArray(res.data) ? res.data : res.data.results || []));
};

const navItems = [
  { to: '/student', label: 'Мои курсы', prefetch: prefetchStudentData },
  { to: '/calendar', label: 'Расписание' },
  { to: '/homework', label: 'Домашнее задание', prefetch: prefetchHomeworkData },
  { to: '/student/recordings', label: 'Записи уроков' },
  { to: '/student/materials', label: 'Материалы' },
  { to: '/student/stats', label: 'Моя статистика' },
];

const StudentNavBar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ top: 0, right: 0 });
  const profileButtonRef = useRef(null);

  // Закрываем мобильное меню при переходе на другую страницу
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  // Блокируем скролл body при открытом мобильном меню
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileMenuOpen]);

  // Calculate dropdown position based on button
  const updateMenuPosition = useCallback(() => {
    if (profileButtonRef.current) {
      const rect = profileButtonRef.current.getBoundingClientRect();
      setMenuPosition({
        top: rect.bottom + 8,
        right: window.innerWidth - rect.right,
      });
    }
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      // Ignore clicks on the profile button (handled by onClick)
      if (profileButtonRef.current && profileButtonRef.current.contains(event.target)) {
        return;
      }
      // Close if clicking outside
      setShowProfileMenu(false);
    };

    if (showProfileMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      window.addEventListener('resize', updateMenuPosition);
      window.addEventListener('scroll', updateMenuPosition, true);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('resize', updateMenuPosition);
      window.removeEventListener('scroll', updateMenuPosition, true);
    };
  }, [showProfileMenu, updateMenuPosition]);

  const getInitials = () => {
    if (user?.first_name) {
      const parts = user.first_name.trim().split(' ');
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

  const hasAvatar = user?.avatar && user.avatar.trim() !== '';

  const handleLogout = () => {
    setShowProfileMenu(false);
    logout();
    navigate('/auth-new', { replace: true });
  };

  const handleToggleMenu = () => {
    if (!showProfileMenu) {
      updateMenuPosition();
    }
    setShowProfileMenu((prev) => !prev);
  };

  return (
    <nav className="student-navbar">
      <div className="student-navbar-content">
        <div className="student-navbar-left">
          <NavLink to="/student" className="student-navbar-logo" aria-label="Lectio Space">
            <h1 className="student-logo-text">
              <span className="brand-primary">Lectio</span>
              <span className="brand-secondary">Space</span>
            </h1>
          </NavLink>
        </div>

        {/* Desktop: nav links в центре */}
        <div className="student-navbar-center student-navbar-center-desktop">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `student-nav-link${isActive ? ' active' : ''}`
              }
              onMouseEnter={item.prefetch}
            >
              {item.label}
            </NavLink>
          ))}
        </div>

        <div className="student-navbar-right">
          {/* Hamburger button для мобильных */}
          <button
            type="button"
            className="student-mobile-menu-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Закрыть меню' : 'Открыть меню'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <IconX size={24} /> : <IconMenu size={24} />}
          </button>

          <button
            type="button"
            className="student-profile-button"
            ref={profileButtonRef}
            onClick={handleToggleMenu}
            aria-haspopup="true"
            aria-expanded={showProfileMenu}
          >
            {hasAvatar ? (
              <div className="student-avatar student-avatar-image">
                <img src={user.avatar} alt="Аватар" />
              </div>
            ) : (
              <div className="student-avatar">{getInitials()}</div>
            )}
          </button>

          {showProfileMenu && createPortal(
            <div
              className="student-profile-dropdown"
              style={{
                position: 'fixed',
                top: menuPosition.top,
                right: menuPosition.right,
                zIndex: 2147483647,
              }}
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="student-profile-header">
                Вы: {user?.first_name || user?.email || 'Ученик'}
              </div>
              <NavLink
                to="/profile"
                className="student-dropdown-item"
                onClick={() => setShowProfileMenu(false)}
              >
                Профиль
              </NavLink>
              <button
                type="button"
                className="student-dropdown-item student-logout"
                onClick={handleLogout}
              >
                Выйти
              </button>
            </div>,
            document.body
          )}
        </div>
      </div>

      {/* Mobile: выдвижное меню */}
      {mobileMenuOpen && createPortal(
        <>
          {/* Backdrop */}
          <div 
            className="student-mobile-backdrop"
            onClick={() => setMobileMenuOpen(false)}
          />
          {/* Menu */}
          <div className="student-mobile-menu">
            <div className="student-mobile-menu-header">
              <span className="student-mobile-menu-title">Меню</span>
              <button
                type="button"
                className="student-mobile-menu-close"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Закрыть меню"
              >
                <IconX size={24} />
              </button>
            </div>
            <nav className="student-mobile-nav">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `student-mobile-nav-link${isActive ? ' active' : ''}`
                  }
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </>,
        document.body
      )}
    </nav>
  );
};

export default StudentNavBar;
