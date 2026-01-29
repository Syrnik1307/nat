import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { getAccessToken } from '../apiService';
import TeachersManage from './TeachersManage';
import StudentsManage from './StudentsManage';
import StatusMessages from './StatusMessages';
import SystemSettings from './SystemSettings';
import StorageQuotaModal from '../modules/Admin/StorageQuotaModal';
import SystemErrorsModal from '../modules/Admin/SystemErrorsModal';
import StorageStats from './StorageStats';
import AdminReferrals from '../modules/Admin/AdminReferrals';
import BusinessMetricsDashboard from '../modules/Admin/BusinessMetricsDashboard';
import AdminDashboardWidget from '../modules/Admin/AdminDashboardWidget';
import '../styles/AdminPanel.css';

/* ========== SVG ICONS ========== */
const Icons = {
  dashboard: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </svg>
  ),
  teachers: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  students: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
      <path d="M6 12v5c3 3 9 3 12 0v-5" />
    </svg>
  ),
  storage: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  ),
  messages: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  settings: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  ),
  plus: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  analytics: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 21H4.6c-.56 0-.84 0-1.054-.109a1 1 0 0 1-.437-.437C3 20.24 3 19.96 3 19.4V3" />
      <path d="M7 14l4-4 4 4 6-6" />
    </svg>
  ),
  referrals: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
    </svg>
  ),
  metrics: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  errors: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  ),
  logout: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  ),
  wrench: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  ),
  close: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
};

const AdminHomePage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    total_users: 0,
    teachers: 0,
    students: 0,
    teachers_online: 0,
    students_online: 0,
    groups: 0,
    lessons: 0,
    zoom_accounts: 0
  });
  const [loading, setLoading] = useState(true);
  const [showCreateTeacher, setShowCreateTeacher] = useState(false);
  const [showTeachersManage, setShowTeachersManage] = useState(false);
  const [showStudentsManage, setShowStudentsManage] = useState(false);
  const [showStatusMessages, setShowStatusMessages] = useState(false);
  const [showGrowthStats, setShowGrowthStats] = useState(false);
  const [showSystemSettings, setShowSystemSettings] = useState(false);
  const [showStorageModal, setShowStorageModal] = useState(false);
  const [showStorageStats, setShowStorageStats] = useState(false);
  const [showReferrals, setShowReferrals] = useState(false);
  const [showBusinessMetrics, setShowBusinessMetrics] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);
  const profileRef = useRef(null);
  const [userRole, setUserRole] = useState('teacher');
  const [teacherForm, setTeacherForm] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    middle_name: ''
  });
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  useEffect(() => {
    loadStats();
  }, []);

  // Close profile dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setShowProfileDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = useCallback(async () => {
    setShowProfileDropdown(false);
    await logout();
    navigate('/auth-new', { replace: true });
  }, [logout, navigate]);

  const loadStats = async () => {
    try {
      const token = getAccessToken();
      const response = await fetch('/accounts/api/admin/stats/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setStats(data);
      setLoading(false);
    } catch (error) {
      console.error('Ошибка загрузки статистики:', error);
      setLoading(false);
    }
  };

  const handleCreateTeacher = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');

    // Валидация
    if (!teacherForm.email || !teacherForm.password || !teacherForm.first_name || !teacherForm.last_name) {
      setFormError('Заполните все обязательные поля');
      return;
    }

    const userTypeLabel = userRole === 'teacher' ? 'учителя' : 'ученика';

    try {
      const endpoint = userRole === 'teacher' 
        ? '/accounts/api/admin/create-teacher/'
        : '/accounts/api/admin/create-student/';
      
      console.log(`Отправка данных ${userTypeLabel}:`, { ...teacherForm, password: '***' });
      const token = getAccessToken();
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(teacherForm)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Unknown error');
      }
      console.log(`${userTypeLabel.charAt(0).toUpperCase() + userTypeLabel.slice(1)} создан успешно:`, data);
      setFormSuccess(`${userTypeLabel.charAt(0).toUpperCase() + userTypeLabel.slice(1)} успешно создан!`);
      
      // Сразу обновляем счетчики для мгновенной обратной связи
      if (userRole === 'teacher') {
        setStats(prev => ({
          ...prev,
          teachers: (prev?.teachers || 0) + 1,
          total_users: (prev?.total_users || 0) + 1
        }));
      } else {
        setStats(prev => ({
          ...prev,
          students: (prev?.students || 0) + 1,
          total_users: (prev?.total_users || 0) + 1
        }));
      }
      
      setTeacherForm({
        email: '',
        password: '',
        first_name: '',
        last_name: '',
        middle_name: ''
      });
      
      // Перезагружаем статистику с сервера
      await loadStats();
      
      // Закрываем форму через 2 секунды
      setTimeout(() => {
        setShowCreateTeacher(false);
        setFormSuccess('');
        setUserRole('teacher');
      }, 2000);
    } catch (error) {
      console.error(`Ошибка создания ${userTypeLabel}:`, error);
      const errorMsg = error.message || 'Ошибка создания учителя';
      setFormError(errorMsg);
    }
  };

  const growthPeriods = Array.isArray(stats?.growth_periods) ? stats.growth_periods : [];

  if (loading) {
    return (
      <div className="admin-home-page">
        <div className="admin-loading">Загрузка...</div>
      </div>
    );
  }

  return (
    <div className="admin-home-page">
      {/* Fixed Sidebar */}
      <aside className="admin-sidebar">
        <div className="admin-sidebar-logo">
          <h2>
            <span className="brand-easy">Easy</span> Teaching
          </h2>
        </div>
        <nav className="admin-sidebar-nav">
          <a className="admin-nav-item active">
            <span className="admin-nav-icon">{Icons.dashboard}</span>
            Dashboard
          </a>
          <a className="admin-nav-item" onClick={() => setShowTeachersManage(true)}>
            <span className="admin-nav-icon">{Icons.teachers}</span>
            Учителя
          </a>
          <a className="admin-nav-item" onClick={() => setShowStudentsManage(true)}>
            <span className="admin-nav-icon">{Icons.students}</span>
            Ученики
          </a>
          <a className="admin-nav-item" onClick={() => setShowStorageModal(true)}>
            <span className="admin-nav-icon">{Icons.storage}</span>
            Хранилище
          </a>
          <a className="admin-nav-item" onClick={() => setShowReferrals(true)}>
            <span className="admin-nav-icon">{Icons.referrals}</span>
            Рефералы
          </a>
          <a className="admin-nav-item" onClick={() => setShowBusinessMetrics(true)}>
            <span className="admin-nav-icon">{Icons.metrics}</span>
            Метрики
          </a>
          <a className="admin-nav-item" onClick={() => setShowErrors(true)}>
            <span className="admin-nav-icon">{Icons.errors}</span>
            Ошибки
          </a>
          <a className="admin-nav-item" onClick={() => setShowStatusMessages(true)}>
            <span className="admin-nav-icon">{Icons.messages}</span>
            Сообщения
          </a>
          <a className="admin-nav-item" onClick={() => setShowSystemSettings(true)}>
            <span className="admin-nav-icon">{Icons.settings}</span>
            Настройки
          </a>
        </nav>
        <div className="admin-sidebar-footer">
          <a className="admin-nav-item logout" onClick={handleLogout}>
            <span className="admin-nav-icon">{Icons.logout}</span>
            Выйти
          </a>
        </div>
      </aside>

      {/* Main Content */}
      <main className="admin-main-content">
        {/* Header */}
        <div className="admin-header">
          <div className="admin-welcome">
            <h1>Панель управления</h1>
            <p>Добро пожаловать, {user?.first_name || 'Администратор'}!</p>
          </div>
          <div className="admin-user-info" ref={profileRef}>
            <div className="user-avatar" onClick={() => setShowProfileDropdown(!showProfileDropdown)} style={{ cursor: 'pointer' }}>
              {user?.first_name?.charAt(0) || 'A'}
            </div>
            {showProfileDropdown && (
              <div className="admin-profile-dropdown">
                <div className="admin-profile-dropdown-header">
                  {user?.email || 'admin@example.com'}
                </div>
                <button className="admin-profile-dropdown-item" onClick={handleLogout}>
                  <span className="admin-nav-icon">{Icons.logout}</span>
                  Выйти
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Statistics Grid */}
        <div className="admin-stats">
          <div className="admin-stat-card">
            <span className="admin-stat-label">Всего пользователей</span>
            <div className="admin-stat-value">{stats.total_users}</div>
          </div>
          
          <div className="admin-stat-card">
            <span className="admin-stat-label">Учителя</span>
            <div className="admin-stat-value">{stats.teachers}</div>
            {stats.teachers_online > 0 && (
              <div className="admin-stat-change positive">
                <span className="admin-stat-change-icon">•</span>
                {stats.teachers_online} онлайн
              </div>
            )}
          </div>
          
          <div className="admin-stat-card">
            <span className="admin-stat-label">Ученики</span>
            <div className="admin-stat-value">{stats.students}</div>
            {stats.students_online > 0 && (
              <div className="admin-stat-change positive">
                <span className="admin-stat-change-icon">•</span>
                {stats.students_online} онлайн
              </div>
            )}
          </div>
          
          <div className="admin-stat-card">
            <span className="admin-stat-label">Группы</span>
            <div className="admin-stat-value">{stats.groups}</div>
          </div>
          
          <div className="admin-stat-card">
            <span className="admin-stat-label">Занятий проведено</span>
            <div className="admin-stat-value">{stats.lessons}</div>
          </div>
        </div>

        {/* NEW: Dashboard Widget with Health Checks & Charts */}
        <AdminDashboardWidget />

        {/* Quick Actions */}
        <div className="admin-quick-actions">
          <div className="admin-quick-action-card" onClick={() => setShowCreateTeacher(true)}>
            <div className="admin-quick-action-icon">{Icons.plus}</div>
            <h3>Создать пользователя</h3>
          </div>
          
          <div className="admin-quick-action-card" onClick={() => setShowGrowthStats(true)}>
            <div className="admin-quick-action-icon">{Icons.analytics}</div>
            <h3>Динамика роста</h3>
          </div>
          
          
          <div className="admin-quick-action-card" onClick={() => setShowStorageStats(true)}>
            <div className="admin-quick-action-icon">{Icons.storage}</div>
            <h3>Google Drive</h3>
          </div>
        </div>

        {/* Create Teacher Modal */}
        {showCreateTeacher && (
        <div className="admin-modal-overlay" onClick={() => setShowCreateTeacher(false)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Создать пользователя</h2>
              <button className="modal-close" onClick={() => setShowCreateTeacher(false)}>{Icons.close}</button>
            </div>
            <form onSubmit={handleCreateTeacher} className="teacher-form">
              {formError && <div className="form-error">{formError}</div>}
              {formSuccess && <div className="form-success">{formSuccess}</div>}
              
              <div className="form-group">
                <label>Тип пользователя *</label>
                <div style={{display: 'flex', gap: '1rem', marginTop: '0.5rem'}}>
                  <label style={{display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer'}}>
                    <input
                      type="radio"
                      name="userRole"
                      value="teacher"
                      checked={userRole === 'teacher'}
                      onChange={(e) => setUserRole(e.target.value)}
                    />
                    <span>Учитель</span>
                  </label>
                  <label style={{display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer'}}>
                    <input
                      type="radio"
                      name="userRole"
                      value="student"
                      checked={userRole === 'student'}
                      onChange={(e) => setUserRole(e.target.value)}
                    />
                    <span>Ученик</span>
                  </label>
                </div>
              </div>
              
              <div className="form-group">
                <label>Email *</label>
                <input
                  type="email"
                  value={teacherForm.email}
                  onChange={(e) => setTeacherForm({ ...teacherForm, email: e.target.value })}
                  placeholder="teacher@example.com"
                  required
                />
              </div>

              <div className="form-group">
                <label>Пароль *</label>
                <input
                  type="password"
                  value={teacherForm.password}
                  onChange={(e) => setTeacherForm({ ...teacherForm, password: e.target.value })}
                  placeholder="Минимум 8 символов"
                  required
                />
              </div>

              <div className="admin-form-row">
                <div className="form-group">
                  <label>Имя *</label>
                  <input
                    type="text"
                    value={teacherForm.first_name}
                    onChange={(e) => setTeacherForm({ ...teacherForm, first_name: e.target.value })}
                    placeholder="Иван"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Фамилия *</label>
                  <input
                    type="text"
                    value={teacherForm.last_name}
                    onChange={(e) => setTeacherForm({ ...teacherForm, last_name: e.target.value })}
                    placeholder="Иванов"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Отчество</label>
                <input
                  type="text"
                  value={teacherForm.middle_name}
                  onChange={(e) => setTeacherForm({ ...teacherForm, middle_name: e.target.value })}
                  placeholder="Иванович"
                />
              </div>

              <div className="form-actions">
                <button type="button" onClick={() => setShowCreateTeacher(false)} className="btn-cancel">
                  Отмена
                </button>
                <button type="submit" className="btn-submit">
                  {userRole === 'teacher' ? 'Создать учителя' : 'Создать ученика'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Teachers Management Modal */}
      {showTeachersManage && (
        <TeachersManage onClose={() => setShowTeachersManage(false)} />
      )}

      {/* Students Management Modal */}
      {showStudentsManage && (
        <StudentsManage onClose={() => setShowStudentsManage(false)} />
      )}


      {/* Growth Stats Modal */}
      {showGrowthStats && (
        <div className="admin-modal-overlay" onClick={() => setShowGrowthStats(false)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Динамика роста</h2>
              <button className="modal-close" onClick={() => setShowGrowthStats(false)}>{Icons.close}</button>
            </div>
            <div className="growth-modal-body">
              {growthPeriods.length === 0 ? (
                <div className="growth-empty">Недостаточно данных для построения динамики</div>
              ) : (
                <div className="growth-grid">
                  {growthPeriods.map((period) => (
                    <div key={period.key} className="growth-card">
                      <div className="growth-card-header">
                        <div className="growth-card-label">{period.label}</div>
                        <div className="growth-card-range">{period.range_label}</div>
                      </div>
                      <div className="growth-metrics">
                        <div className="growth-metric">
                          <span>Учителя</span>
                          <strong>{period.teachers}</strong>
                        </div>
                        <div className="growth-metric">
                          <span>Ученики</span>
                          <strong>{period.students}</strong>
                        </div>
                        <div className="growth-metric">
                          <span>Занятия</span>
                          <strong>{period.lessons}</strong>
                        </div>
                      </div>
                      <div className="growth-total">
                        <span>Всего новых пользователей</span>
                        <strong>{period.total_users}</strong>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      </main>

      {/* Modals */}
      {showTeachersManage && (
        <TeachersManage onClose={() => setShowTeachersManage(false)} />
      )}

      {showStatusMessages && (
        <StatusMessages onClose={() => setShowStatusMessages(false)} />
      )}
      
      {showSystemSettings && (
        <SystemSettings onClose={() => setShowSystemSettings(false)} />
      )}
      

      {showStorageModal && (
        <StorageQuotaModal onClose={() => setShowStorageModal(false)} />
      )}

      {showStorageStats && (
        <StorageStats onClose={() => setShowStorageStats(false)} />
      )}


      {/* Referrals Modal */}
      {showReferrals && (
        <AdminReferrals onClose={() => setShowReferrals(false)} />
      )}

      {/* Business Metrics Dashboard */}
      {showBusinessMetrics && (
        <BusinessMetricsDashboard onClose={() => setShowBusinessMetrics(false)} />
      )}

      {/* System Errors Modal */}
      {showErrors && (
        <SystemErrorsModal onClose={() => setShowErrors(false)} />
      )}
    </div>
  );
};

export default AdminHomePage;
