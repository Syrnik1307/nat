import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth';
import './OlgaNavBar.css';

/**
 * OlgaNavBar — навигационная панель для тенанта Ольги.
 * Минималистичная, тёплые тона, шрифт Georgia.
 */
const OlgaNavBar = () => {
  const { user, role, accessTokenValid, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const hasStoredToken = Boolean(localStorage.getItem('tp_access_token'));
  const isAuthenticated = accessTokenValid || Boolean(user) || hasStoredToken;

  const handleLogout = () => {
    setShowProfileMenu(false);
    setMenuOpen(false);
    logout();
    navigate('/olga/courses', { replace: true });
  };

  const userInitial = (user?.first_name || user?.email || 'U').charAt(0).toUpperCase();
  const userName = user?.first_name || 'Пользователь';

  return (
    <nav className="olga-navbar">
      <div className="olga-navbar-inner">
        {/* Логотип */}
        <NavLink to="/olga/courses" className="olga-navbar-brand">
          <span className="olga-navbar-flower">✿</span>
          <span className="olga-navbar-name">Ольга</span>
        </NavLink>

        {/* Бургер-меню (мобильное) */}
        <button
          className={`olga-burger ${menuOpen ? 'open' : ''}`}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Меню"
        >
          <span /><span /><span />
        </button>

        {/* Навигация */}
        <div className={`olga-navbar-links ${menuOpen ? 'show' : ''}`}>
          {/* Публичная ссылка на каталог — всегда видна */}
          <NavLink
            to="/olga/courses"
            className={({ isActive }) => `olga-nav-link ${isActive ? 'active' : ''}`}
            onClick={() => { setMenuOpen(false); setShowProfileMenu(false); }}
          >
            Курсы
          </NavLink>

          {/* Ссылка на ЛК — только для авторизованных */}
          {isAuthenticated && (
            <NavLink
              to="/olga/my"
              className={({ isActive }) => `olga-nav-link ${isActive ? 'active' : ''}`}
              onClick={() => { setMenuOpen(false); setShowProfileMenu(false); }}
            >
              Мой кабинет
            </NavLink>
          )}

          {/* Админские ссылки */}
          {isAuthenticated && ['teacher', 'admin'].includes(role || user?.role) && (
            <>
              <NavLink
                to="/olga/admin"
                className={({ isActive }) => `olga-nav-link ${isActive ? 'active' : ''}`}
                onClick={() => { setMenuOpen(false); setShowProfileMenu(false); }}
              >
                Медиа
              </NavLink>
              <NavLink
                to="/olga/admin/courses"
                className={({ isActive }) => `olga-nav-link ${isActive ? 'active' : ''}`}
                onClick={() => { setMenuOpen(false); setShowProfileMenu(false); }}
              >
                Конструктор курсов
              </NavLink>
            </>
          )}

          {/* Аватар + меню профиля — для авторизованных */}
          {isAuthenticated ? (
            <div className="olga-navbar-user-menu">
              <div className="olga-profile-menu-container">
                <button
                  type="button"
                  className="olga-profile-button"
                  onClick={() => setShowProfileMenu(prev => !prev)}
                  aria-label="Меню профиля"
                  aria-expanded={showProfileMenu}
                >
                  <div className="olga-avatar" aria-hidden="true">
                    {user?.avatar ? (
                      <img src={user.avatar} alt="Аватар" />
                    ) : (
                      <span className="olga-avatar-initial">{userInitial}</span>
                    )}
                  </div>
                  <span className="olga-profile-name">{userName}</span>
                  <span className={`olga-chevron ${showProfileMenu ? 'open' : ''}`}>▼</span>
                </button>

                {showProfileMenu && (
                  <div className="olga-profile-dropdown">
                    <div className="olga-dropdown-header">
                      <div className="olga-user-info">
                        <p className="olga-user-name">
                          {user?.first_name || 'Пользователь'} {user?.last_name || ''}
                        </p>
                        <p className="olga-user-role">
                          {(role || user?.role) === 'teacher'
                            ? 'Учитель'
                            : (role || user?.role) === 'student'
                              ? 'Ученик'
                              : 'Администратор'}
                        </p>
                      </div>
                    </div>

                    <div className="olga-dropdown-divider"></div>

                    <NavLink
                      to="/olga/my"
                      className="olga-dropdown-item"
                      onClick={() => {
                        setShowProfileMenu(false);
                        setMenuOpen(false);
                      }}
                    >
                      <span>📚</span>
                      <span>Мой кабинет</span>
                    </NavLink>
                    <NavLink
                      to="/olga/profile"
                      className="olga-dropdown-item"
                      onClick={() => {
                        setShowProfileMenu(false);
                        setMenuOpen(false);
                      }}
                    >
                      <span>⚙️</span>
                      <span>Настройки профиля</span>
                    </NavLink>
                    <button
                      type="button"
                      className="olga-dropdown-item olga-dropdown-item-logout"
                      onClick={handleLogout}
                    >
                      <span>🚪</span>
                      <span>Выйти</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Кнопка «Войти» для неавторизованных */
            <NavLink
              to="/olga/auth"
              className="olga-nav-link olga-login-link"
              onClick={() => setMenuOpen(false)}
            >
              Войти
            </NavLink>
          )}
        </div>
      </div>
    </nav>
  );
};

export default OlgaNavBar;
