import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth';
import apiService, { getAccessToken } from '../apiService';
import TeachersManage from './TeachersManage';
import StudentsManage from './StudentsManage';
import StatusMessages from './StatusMessages';
import ZoomPoolManager from '../modules/core/zoom/ZoomPoolManager';
import ZoomPoolStats from './ZoomPoolStats';
import SystemSettings from './SystemSettings';
import '../styles/AdminPanel.css';
import StorageQuotaModal from '../modules/Admin/StorageQuotaModal';
import SubscriptionsModal from '../modules/Admin/SubscriptionsModal';
import StorageStats from './StorageStats';
import AdminReferrals from '../modules/Admin/AdminReferrals';

const AdminHomePage = () => {
  const { user } = useAuth();
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
  const [showZoomManager, setShowZoomManager] = useState(false);
  const [showZoomStats, setShowZoomStats] = useState(false);
  const [showGrowthStats, setShowGrowthStats] = useState(false);
  const [showSystemSettings, setShowSystemSettings] = useState(false);
  const [showStorageModal, setShowStorageModal] = useState(false);
  const [showSubscriptionsModal, setShowSubscriptionsModal] = useState(false);
  const [showStorageStats, setShowStorageStats] = useState(false);
  const [showReferrals, setShowReferrals] = useState(false);
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

  const StatCard = ({ icon, label, value, subValue, color }) => (
    <div className="admin-stat-card" style={{ borderLeft: `4px solid ${color}` }}>
      <div className="stat-icon" style={{ color }}>{icon}</div>
      <div className="stat-content">
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
        {subValue !== undefined && (
          <div className="stat-subvalue">
            <span className="online-indicator"></span>
            {subValue} онлайн
          </div>
        )}
      </div>
    </div>
  );

  const QuickAction = ({ icon, label, onClick, color }) => (
    <button className="admin-quick-action" onClick={onClick}>
      <div className="action-icon" style={{ backgroundColor: color }}>{icon}</div>
      <div className="action-label">{label}</div>
    </button>
  );

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
            <span className="admin-nav-icon">📊</span>
            Dashboard
          </a>
          <a className="admin-nav-item" onClick={() => setShowTeachersManage(true)}>
            <span className="admin-nav-icon">👨‍🏫</span>
            Учителя
          </a>
          <a className="admin-nav-item" onClick={() => setShowStudentsManage(true)}>
            <span className="admin-nav-icon">👨‍🎓</span>
            Ученики
          </a>
          <a className="admin-nav-item" onClick={() => setShowZoomManager(true)}>
            <span className="admin-nav-icon">📹</span>
            Zoom Pool
          </a>
          <a className="admin-nav-item" onClick={() => setShowSubscriptionsModal(true)}>
            <span className="admin-nav-icon">💳</span>
            Подписки
          </a>
          <a className="admin-nav-item" onClick={() => setShowStorageModal(true)}>
            <span className="admin-nav-icon">💾</span>
            Хранилище
          </a>
          <a className="admin-nav-item" onClick={() => setShowStatusMessages(true)}>
            <span className="admin-nav-icon">📢</span>
            Сообщения
          </a>
          <a className="admin-nav-item" onClick={() => setShowReferrals(true)}>
            <span className="admin-nav-icon">🔗</span>
            Рефы
          </a>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="admin-main-content">
        {/* Header */}
        <div className="admin-header">
          <div className="admin-welcome">
            <h1>Панель управления</h1>
            <p>Добро пожаловать, {user?.first_name || 'Администратор'}!</p>
          </div>
          <div className="admin-user-info">
            <div className="user-avatar">
              {user?.first_name?.charAt(0) || 'A'}
            </div>
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

        {/* Quick Actions */}
        <div className="admin-quick-actions">
          <div className="admin-quick-action-card" onClick={() => setShowCreateTeacher(true)}>
            <div className="admin-quick-action-icon">➕</div>
            <h3>Создать пользователя</h3>
          </div>
          
          <div className="admin-quick-action-card" onClick={() => setShowGrowthStats(true)}>
            <div className="admin-quick-action-icon">📈</div>
            <h3>Динамика роста</h3>
          </div>
          
          <div className="admin-quick-action-card" onClick={() => setShowZoomStats(true)}>
            <div className="admin-quick-action-icon">📊</div>
            <h3>Zoom аналитика</h3>
          </div>
          
          <div className="admin-quick-action-card" onClick={() => setShowStorageStats(true)}>
            <div className="admin-quick-action-icon">💾</div>
            <h3>Google Drive</h3>
          </div>
        </div>

        {/* Create Teacher Modal */}
        {showCreateTeacher && (
        <div className="admin-modal-overlay" onClick={() => setShowCreateTeacher(false)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>➕ Создать пользователя</h2>
              <button className="modal-close" onClick={() => setShowCreateTeacher(false)}>✕</button>
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
                    <span>👨‍🏫 Учитель</span>
                  </label>
                  <label style={{display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer'}}>
                    <input
                      type="radio"
                      name="userRole"
                      value="student"
                      checked={userRole === 'student'}
                      onChange={(e) => setUserRole(e.target.value)}
                    />
                    <span>☎ Ученик</span>
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

      {/* Zoom Pool Manager */}
      {showZoomManager && (
        <div className="admin-modal-overlay" onClick={() => setShowZoomManager(false)}>
          <div className="zoom-manager-modal" onClick={(e) => e.stopPropagation()}>
            <ZoomPoolManager onClose={() => setShowZoomManager(false)} />
          </div>
        </div>
      )}

      {/* Growth Stats Modal */}
      {showGrowthStats && (
        <div className="admin-modal-overlay" onClick={() => setShowGrowthStats(false)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📈 Динамика роста</h2>
              <button className="modal-close" onClick={() => setShowGrowthStats(false)}>✕</button>
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

      {/* System Status */}
      <div className="admin-section">
        <h2>🔧 Статус системы</h2>
        <div className="admin-system-status">
          <div className="status-item">
            <div className="status-indicator" style={{ backgroundColor: '#10b981' }}></div>
            <div className="status-label">Django Server</div>
            <div className="status-value">Работает</div>
          </div>
          <div className="status-item">
            <div className="status-indicator" style={{ backgroundColor: '#10b981' }}></div>
            <div className="status-label">React Frontend</div>
            <div className="status-value">Работает</div>
          </div>
          <div className="status-item">
            <div className="status-indicator" style={{ backgroundColor: '#10b981' }}></div>
            <div className="status-label">Zoom API</div>
            <div className="status-value">Подключено</div>
          </div>
          <div className="status-item">
            <div className="status-indicator" style={{ backgroundColor: '#f59e0b' }}></div>
            <div className="status-label">Celery Worker</div>
            <div className="status-value">Не запущен</div>
          </div>
          <div className="status-item">
            <div className="status-indicator" style={{ backgroundColor: '#10b981' }}></div>
            <div className="status-label">База данных</div>
            <div className="status-value">Работает</div>
          </div>
        </div>
      </div> {/* End admin-section */}
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
      
      {showZoomStats && (
        <div className="admin-modal-overlay" onClick={() => setShowZoomStats(false)}>
          <div className="admin-modal zoom-stats-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📊 Аналитика Zoom Pool</h2>
              <button className="modal-close" onClick={() => setShowZoomStats(false)}>✕</button>
            </div>
            <div className="modal-body">
              <ZoomPoolStats />
            </div>
          </div>
        </div>
      )}

      {showStorageModal && (
        <StorageQuotaModal onClose={() => setShowStorageModal(false)} />
      )}

      {showStorageStats && (
        <StorageStats onClose={() => setShowStorageStats(false)} />
      )}

      {showSubscriptionsModal && (
        <SubscriptionsModal onClose={() => setShowSubscriptionsModal(false)} />
      )}

      {showReferrals && (
        <AdminReferrals onClose={() => setShowReferrals(false)} />
      )}
    </div>
  );
};

export default AdminHomePage;
