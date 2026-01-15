import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import '../styles/StudentNavBar.css';

const navItems = [
  { to: '/student', label: 'Мои курсы' },
  { to: '/calendar', label: 'Расписание' },
  { to: '/homework', label: 'Домашнее задание' },
  { to: '/student/recordings', label: 'Записи уроков' },
  { to: '/student/materials', label: 'Материалы' },
  { to: '/student/stats', label: 'Моя статистика' },
];

const StudentNavBar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ top: 0, right: 0 });
  const profileButtonRef = useRef(null);

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
    navigate('/auth');
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

        <div className="student-navbar-center">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `student-nav-link${isActive ? ' active' : ''}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>

        <div className="student-navbar-right">
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
    </nav>
  );
};

export default StudentNavBar;
