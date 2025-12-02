import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { TELEGRAM_RESET_DEEPLINK } from '../constants';
import Logo from './Logo';
import '../styles/StudentNavBar.css';

const navItems = [
  { to: '/student', label: 'Мои курсы' },
  { to: '/calendar', label: 'Расписание' },
  { to: '/homework', label: 'Домашнее задание' },
  { to: '/student/recordings', label: '📹 Записи уроков' },
  { to: '/student/stats', label: 'Моя статистика' },
];

const StudentNavBar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showProfileMenu, setShowProfileMenu] = useState(false);

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

  const handleLogout = () => {
    logout();
    navigate('/auth');
  };

  const openTelegramResetFlow = () => {
    const newTab = window.open(TELEGRAM_RESET_DEEPLINK, '_blank');
    if (!newTab) {
      window.location.href = TELEGRAM_RESET_DEEPLINK;
    }
    setShowProfileMenu(false);
  };

  return (
    <nav className="student-navbar">
      <div className="student-navbar-content">
        <div className="student-navbar-left">
          <NavLink to="/student" aria-label="Teaching Panel">
            <Logo size={34} />
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
          <div className="student-profile-section">
            <button
              type="button"
              className="student-profile-button"
              onClick={() => setShowProfileMenu((prev) => !prev)}
              aria-haspopup="true"
              aria-expanded={showProfileMenu}
            >
              <div className="student-avatar">{getInitials()}</div>
            </button>

            {showProfileMenu && (
              <div className="student-profile-dropdown">
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
                <NavLink
                  to="/messages"
                  className="student-dropdown-item"
                  onClick={() => setShowProfileMenu(false)}
                >
                  Сообщения
                </NavLink>

                <NavLink
                  to="/help"
                  className="student-dropdown-item"
                  onClick={() => setShowProfileMenu(false)}
                >
                  Вопросы и Ответы
                </NavLink>
                <button
                  type="button"
                  className="student-dropdown-item"
                  onClick={openTelegramResetFlow}
                >
                  <span role="img" aria-hidden="true">🔑</span> Сбросить пароль
                </button>
                <button
                  type="button"
                  className="student-dropdown-item student-logout"
                  onClick={handleLogout}
                >
                  <span>🚪</span> Выйти
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default StudentNavBar;
