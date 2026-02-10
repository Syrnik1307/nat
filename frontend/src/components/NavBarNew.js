import React, { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { getAccessToken, getLessons, getGroups, getHomeworkList, getTeacherStatsSummary } from '../apiService';
import { prefetch, TTL } from '../utils/dataCache';
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
 * - Домашние задания (бывшее "Конструктор ДЗ")
 * - Управление учениками (бывшее "Управление группами")
 * - Календарь
 * - Материалы
 * 
 * Убрано:
 * - Личные беседы
 * - Шаблоны
 */

// === PREFETCH FUNCTIONS для мгновенных переходов ===
// Запускаются при hover/focus на ссылку меню

const prefetchTeacherHome = () => {
  const now = new Date();
  const yyyy = String(now.getFullYear());
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const today = `${yyyy}-${mm}-${dd}`;
  
  prefetch('teacher:stats', () => getTeacherStatsSummary().then(r => r.data), TTL.LONG);
  prefetch(`teacher:lessons:${today}`, () => getLessons({ date: today, include_recurring: true })
    .then(r => Array.isArray(r.data) ? r.data : r.data.results || []), TTL.SHORT);
  prefetch('teacher:groups', () => getGroups()
    .then(r => Array.isArray(r.data) ? r.data : r.data.results || []), TTL.MEDIUM);
};

const prefetchCalendar = () => {
  const now = new Date();
  const in30 = new Date();
  in30.setDate(now.getDate() + 30);
  
  prefetch('teacher:calendar', () => getLessons({
    start: now.toISOString(),
    end: in30.toISOString(),
    include_recurring: true,
  }).then(r => Array.isArray(r.data) ? r.data : r.data.results || []), TTL.SHORT);
};

const prefetchGroups = () => {
  prefetch('teacher:groups', () => getGroups()
    .then(r => Array.isArray(r.data) ? r.data : r.data.results || []), TTL.MEDIUM);
};

const prefetchHomework = () => {
  prefetch('teacher:homework', () => getHomeworkList({})
    .then(r => Array.isArray(r.data) ? r.data : r.data.results || []), TTL.MEDIUM);
  prefetchGroups();
};

const prefetchAnalytics = () => {
  prefetch('teacher:stats', () => getTeacherStatsSummary().then(r => r.data), TTL.LONG);
  prefetchGroups();
};

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
  const profileDropdownRef = useRef(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, right: 0 });
  const lessonsDropdownRef = useRef(null);
  const lessonsButtonRef = useRef(null);
  const lessonsMenuRef = useRef(null);
  const [lessonsMenuPosition, setLessonsMenuPosition] = useState({ top: 0, left: 0, minWidth: 200 });

  useEffect(() => {
    if (accessTokenValid) {
      // Отложенная загрузка сообщений - не блокирует первый рендер
      const timer = setTimeout(loadMessages, 2000);
      const interval = setInterval(loadMessages, 30000);
      return () => {
        clearTimeout(timer);
        clearInterval(interval);
      };
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

  const loadMessages = async () => {
    try {
      const token = getAccessToken();
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

  const updateLessonsMenuPosition = () => {
    if (!lessonsButtonRef.current) return;
    const rect = lessonsButtonRef.current.getBoundingClientRect();

    const desiredMinWidth = Math.max(200, Math.round(rect.width));
    const maxLeft = Math.max(8, window.innerWidth - desiredMinWidth - 8);
    const left = Math.min(Math.max(8, rect.left), maxLeft);

    setLessonsMenuPosition({
      top: Math.round(rect.bottom),
      left: Math.round(left),
      minWidth: desiredMinWidth,
    });
  };

  useEffect(() => {
    if (!showLessonsMenu || showMobileMenu) return undefined;

    updateLessonsMenuPosition();

    const handle = () => updateLessonsMenuPosition();
    window.addEventListener('scroll', handle, true);
    window.addEventListener('resize', handle);

    return () => {
      window.removeEventListener('scroll', handle, true);
      window.removeEventListener('resize', handle);
    };
  }, [showLessonsMenu, showMobileMenu]);

  useEffect(() => {
    if (!showLessonsMenu) return undefined;

    const handleDocumentClick = (event) => {
      const target = event.target;

      const clickInsideTrigger = lessonsDropdownRef.current && lessonsDropdownRef.current.contains(target);
      const clickInsideMenu = lessonsMenuRef.current && lessonsMenuRef.current.contains(target);

      // More robust for portals / SVG / nested targets
      const path = typeof event.composedPath === 'function' ? event.composedPath() : null;
      const clickInPath = (node) => (node && Array.isArray(path) ? path.includes(node) : false);

      const inside =
        clickInsideTrigger ||
        clickInsideMenu ||
        clickInPath(lessonsDropdownRef.current) ||
        clickInPath(lessonsMenuRef.current);

      if (!inside) {
        setShowLessonsMenu(false);
      }
    };

    const handleEsc = (event) => {
      if (event.key === 'Escape') {
        setShowLessonsMenu(false);
      }
    };

    // Use click (not mousedown) so Link navigation isn't canceled by unmounting
    document.addEventListener('click', handleDocumentClick);
    document.addEventListener('keydown', handleEsc);

    return () => {
      document.removeEventListener('click', handleDocumentClick);
      document.removeEventListener('keydown', handleEsc);
    };
  }, [showLessonsMenu]);

  const homePath = (() => {
    if (!accessTokenValid) return '/auth-new';
    if (role === 'teacher') return '/home-new';
    if (role === 'student') return '/student';
    if (role === 'admin') return '/admin-home';
    return '/auth-new';
  })();

  const handleLogout = () => {
    logout();
    navigate('/auth-new', { replace: true });
  };

  const menuContent = (
    <>
      {/* Общие пункты */}
      <Link 
        to={homePath} 
        className="nav-link"
        onClick={() => setShowMobileMenu(false)}
        onMouseEnter={role === 'teacher' ? prefetchTeacherHome : undefined}
        onFocus={role === 'teacher' ? prefetchTeacherHome : undefined}
      >
        <span className="nav-icon"></span>
        <span>Главная</span>
      </Link>

      {/* Меню для преподавателя */}
      {accessTokenValid && role === 'teacher' && (
        <>
          <div 
            ref={lessonsDropdownRef}
            className={`nav-dropdown ${showLessonsMenu ? 'open' : ''}`}
          >
            <button
              type="button"
              className="nav-link nav-dropdown-trigger"
              ref={lessonsButtonRef}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (!showMobileMenu) {
                  updateLessonsMenuPosition();
                }
                setShowLessonsMenu(prev => !prev);
              }}
              onMouseEnter={prefetchCalendar}
              onFocus={prefetchCalendar}
              aria-expanded={showLessonsMenu}
              aria-haspopup="true"
            >
              <span className="nav-icon"></span>
              <span>Занятия</span>
              <span className={`caret ${showLessonsMenu ? 'open' : ''}`}>▾</span>
            </button>
            {/* В мобильном боковом меню рендерим inline, на десктопе — через портал (чтобы не перекрывалось слоями) */}
            {showMobileMenu && showLessonsMenu && (
              <div className="nav-dropdown-menu" role="menu">
                <button
                  type="button"
                  className="nav-dropdown-item"
                  onClick={() => {
                    setShowLessonsMenu(false);
                    setShowMobileMenu(false);
                    navigate('/calendar');
                  }}
                  role="menuitem"
                >
                  <span className="item-icon"></span>
                  <span>Календарь</span>
                </button>
                <button
                  type="button"
                  className="nav-dropdown-item"
                  onClick={() => {
                    setShowLessonsMenu(false);
                    setShowMobileMenu(false);
                    navigate('/recurring-lessons/manage');
                  }}
                  role="menuitem"
                >
                  <span className="item-icon"></span>
                  <span>Создать занятие</span>
                </button>
              </div>
            )}
          </div>

          {!showMobileMenu && showLessonsMenu && createPortal(
            <div
              ref={lessonsMenuRef}
              className="nav-dropdown-menu tp-allow-fixed"
              role="menu"
              style={{
                position: 'fixed',
                top: lessonsMenuPosition.top,
                left: lessonsMenuPosition.left,
                minWidth: lessonsMenuPosition.minWidth,
                display: 'flex',
                zIndex: 2147483000,
              }}
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
            >
              <Link
                to="/calendar"
                className="nav-dropdown-item"
                onClick={() => {
                  setShowLessonsMenu(false);
                  setShowMobileMenu(false);
                }}
                role="menuitem"
              >
                <span className="item-icon"></span>
                <span>Календарь</span>
              </Link>
              <Link
                to="/recurring-lessons/manage"
                className="nav-dropdown-item"
                onClick={() => {
                  setShowLessonsMenu(false);
                  setShowMobileMenu(false);
                }}
                role="menuitem"
              >
                <span className="item-icon"></span>
                <span>Создать занятие</span>
              </Link>
            </div>,
            document.body
          )}
          
          <Link 
            to="/homework/constructor" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
            onMouseEnter={prefetchHomework}
            onFocus={prefetchHomework}
            data-tour="nav-homework"
          >
            <span className="nav-icon"></span>
            <span>ДЗ</span>
          </Link>
          
          <Link 
            to="/groups/manage" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
            onMouseEnter={prefetchGroups}
            onFocus={prefetchGroups}
          >
            <span className="nav-icon"></span>
            <span>Ученики</span>
          </Link>
          
          <Link 
            to="/teacher/materials" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
          >
            <span className="nav-icon"></span>
            <span>Материалы</span>
          </Link>
          
          <Link 
            to="/teacher/recordings" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
            data-tour="nav-recordings"
          >
            <span className="nav-icon"></span>
            <span>Записи</span>
          </Link>

          <Link 
            to="/analytics" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
            onMouseEnter={prefetchAnalytics}
            onFocus={prefetchAnalytics}
            data-tour="nav-analytics"
          >
            <span className="nav-icon"></span>
            <span>Аналитика</span>
          </Link>

          <Link 
            to="/knowledge-map" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
          >
            <span className="nav-icon"></span>
            <span>Карта знаний</span>
          </Link>

          <Link 
            to="/exams" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
          >
            <span className="nav-icon"></span>
            <span>Экзамены</span>
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
            data-tour="student-navbar"
          >
            <span className="nav-icon"></span>
            <span>Мои курсы</span>
          </Link>
          
          <Link 
            to="/homework" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
            data-tour="nav-homework-student"
          >
            <span className="nav-icon"></span>
            <span>Домашние задания</span>
          </Link>

          <Link 
            to="/exams" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
          >
            <span className="nav-icon"></span>
            <span>Экзамены</span>
          </Link>
          
          <Link 
            to="/calendar" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
            data-tour="nav-calendar-student"
          >
            <span className="nav-icon"></span>
            <span>Календарь</span>
          </Link>
        </>
      )}

      {/* Меню для админа */}
      {accessTokenValid && role === 'admin' && (
        <>
          <Link 
            to="/admin-home" 
            className="nav-link nav-link-highlight"
            onClick={() => setShowMobileMenu(false)}
          >
            <span className="nav-icon"></span>
            <span>Админ-панель</span>
          </Link>

          <Link 
            to="/analytics" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
          >
            <span className="nav-icon"></span>
            <span>Аналитика</span>
          </Link>
        </>
      )}

      {/* Мобильный профиль и выход */}
      {accessTokenValid && (
        <div className="mobile-profile-section">
          <div className="mobile-profile-divider"></div>
          <Link 
            to="/profile" 
            className="nav-link"
            onClick={() => setShowMobileMenu(false)}
          >
            <span className="nav-icon"></span>
            <span>Профиль</span>
          </Link>
          <button 
            className="nav-link mobile-logout-btn"
            onClick={() => {
              setShowMobileMenu(false);
              handleLogout();
            }}
          >
            <span className="nav-icon"></span>
            <span>Выйти</span>
          </button>
        </div>
      )}
    </>
  );

  const teacherMessages = messages.filter(m => m.target === 'teachers' || m.target === 'all');
  const studentMessages = messages.filter(m => m.target === 'students' || m.target === 'all');
  const currentMessage = messages.length > 0 ? messages[currentIndex] : null;

  const updateProfileMenuPosition = () => {
    if (!profileButtonRef.current) return;
    const rect = profileButtonRef.current.getBoundingClientRect();
    setMenuPosition({
      top: rect.bottom + 12,
      right: Math.max(window.innerWidth - rect.right, 16),
    });
  };

  useEffect(() => {
    if (!showProfileMenu) {
      return undefined;
    }

    updateProfileMenuPosition();
    window.addEventListener('scroll', updateProfileMenuPosition);
    window.addEventListener('resize', updateProfileMenuPosition);

    // Закрытие при клике снаружи
    const handleClickOutside = (event) => {
      const target = event.target;
      const clickInsideButton = profileButtonRef.current && profileButtonRef.current.contains(target);
      const clickInsideDropdown = profileDropdownRef.current && profileDropdownRef.current.contains(target);
      
      if (!clickInsideButton && !clickInsideDropdown) {
        setShowProfileMenu(false);
      }
    };

    // Небольшая задержка чтобы не закрыть сразу
    const timer = setTimeout(() => {
      document.addEventListener('click', handleClickOutside);
    }, 10);

    return () => {
      clearTimeout(timer);
      document.removeEventListener('click', handleClickOutside);
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
                  <div className="status-label">Учителям</div>
                  {teacherMessages.length > 0 ? (
                    <span className="status-message">{teacherMessages[0].message}</span>
                  ) : (
                    <span className="status-empty">Нет сообщений</span>
                  )}
                </div>
                
                {/* Правая часть - для учеников */}
                <div className="status-half status-students">
                  <div className="status-label">Ученикам</div>
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
      <nav className="navbar" data-tour="teacher-navbar">
        <div className="navbar-container">
        {/* Логотип */}
        <Link to={homePath} className="navbar-logo" aria-label="Lectio Space">
          <Logo size={40} withText={true} />
        </Link>

        {/* Burger button для мобильных - ПЕРЕД меню */}
        <button 
          className={`burger-button ${showMobileMenu ? 'open' : ''}`}
          onClick={() => setShowMobileMenu(!showMobileMenu)}
          aria-label="Toggle menu"
          style={{ display: 'none' }}
        >
          <span className={`burger-line ${showMobileMenu ? 'open' : ''}`}></span>
          <span className={`burger-line ${showMobileMenu ? 'open' : ''}`}></span>
          <span className={`burger-line ${showMobileMenu ? 'open' : ''}`}></span>
        </button>

        {/* Навигационное меню: на мобильном через портал поверх всех слоев */}
        {showMobileMenu
          ? createPortal(
              <>
                <div 
                  className="mobile-menu-overlay"
                  onClick={() => setShowMobileMenu(false)}
                />
                <div className={`navbar-menu navbar-menu-portal ${showMobileMenu ? 'mobile-open' : ''}`}>
                  {menuContent}
                </div>
              </>,
              document.body
            )
          : (
              <div className={`navbar-menu ${showMobileMenu ? 'mobile-open' : ''}`}>
                {menuContent}
              </div>
            )}

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
                  ref={profileDropdownRef}
                  className="profile-dropdown tp-allow-fixed"
                  style={{ position: 'fixed', top: menuPosition.top, right: menuPosition.right, zIndex: 99999, backgroundColor: '#fff' }}
                  onMouseDown={(e) => e.stopPropagation()}
                  onClick={(e) => e.stopPropagation()}
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
                    <span></span>
                    <span>Профиль</span>
                  </Link>
                  
                  <button 
                    className="dropdown-item"
                    onClick={handleLogout}
                  >
                    <span></span>
                    <span>Выйти</span>
                  </button>
                </div>,
                document.body
              )}
            </div>
          )}
        </div>

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
