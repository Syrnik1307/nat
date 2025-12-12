import React, { useState, useEffect, useMemo } from 'react';
import { Notification, ConfirmModal } from '../shared/components';
import useNotification from '../shared/hooks/useNotification';
import './TeachersManage.css';

const statusLabels = {
  active: 'Активна',
  pending: 'Ожидает оплаты',
  expired: 'Истекла',
  cancelled: 'Отменена',
  trial: 'Триал',
  none: 'Нет подписки'
};

const TeachersManage = ({ onClose }) => {
  const { notification, confirm, closeNotification, showConfirm, closeConfirm } = useNotification();
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTeacherId, setSelectedTeacherId] = useState(null);
  const [selectedTeacher, setSelectedTeacher] = useState(null);
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [storageInput, setStorageInput] = useState(5);
  const [actionMessage, setActionMessage] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [zoomForm, setZoomForm] = useState({
    zoom_account_id: '',
    zoom_client_id: '',
    zoom_client_secret: '',
    zoom_user_id: ''
  });

  useEffect(() => {
    loadTeachers();
    const interval = setInterval(() => loadTeachers(true), 20000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!selectedTeacherId && teachers.length > 0) {
      handleSelectTeacher(teachers[0]);
    }
  }, [teachers, selectedTeacherId]);

  useEffect(() => {
    if (selectedTeacherId) {
      loadTeacherProfile(selectedTeacherId);
    }
  }, [selectedTeacherId]);

  useEffect(() => {
    if (profile?.zoom) {
      setZoomForm({
        zoom_account_id: profile.zoom.zoom_account_id || '',
        zoom_client_id: profile.zoom.zoom_client_id || '',
        zoom_client_secret: profile.zoom.zoom_client_secret || '',
        zoom_user_id: profile.zoom.zoom_user_id || ''
      });
    }
  }, [profile]);

  const filteredTeachers = useMemo(() => {
    if (!searchTerm) return teachers;
    return teachers.filter((teacher) => {
      const fullName = `${teacher.last_name || ''} ${teacher.first_name || ''} ${teacher.middle_name || ''}`.toLowerCase();
      return fullName.includes(searchTerm.toLowerCase()) || (teacher.email || '').toLowerCase().includes(searchTerm.toLowerCase());
    });
  }, [teachers, searchTerm]);

  const loadTeachers = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('/accounts/api/admin/teachers/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text?.slice(0, 180) || 'Не удалось загрузить список учителей');
      }
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Сервер вернул не-JSON при загрузке учителей');
      }
      const data = await response.json();
      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.results)
          ? data.results
          : [];
      setTeachers(list);
      if (selectedTeacherId) {
        const updated = list.find((item) => item.id === selectedTeacherId);
        if (updated) setSelectedTeacher(updated);
      }
    } catch (error) {
      console.error('Ошибка загрузки учителей:', error);
      if (!silent) {
        setActionError(error.message || 'Ошибка загрузки данных');
      }
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const loadTeacherProfile = async (teacherId) => {
    try {
      setProfileLoading(true);
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`/accounts/api/admin/teachers/${teacherId}/profile/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text?.slice(0, 180) || 'Не удалось загрузить профиль');
      }
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        throw new Error(text?.slice(0, 180) || 'Ответ профиля не JSON');
      }
      const data = await response.json();
      setProfile(data);
    } catch (error) {
      console.error('Ошибка загрузки профиля:', error);
      setActionError(error.message || 'Ошибка загрузки профиля');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleSelectTeacher = (teacher) => {
    if (!teacher) {
      setSelectedTeacherId(null);
      setSelectedTeacher(null);
      setProfile(null);
      return;
    }
    setSelectedTeacherId(teacher.id);
    setSelectedTeacher(teacher);
    setActionError('');
    setActionMessage('');
  };

  const handleDeleteTeacher = async (teacherId, teacherName) => {
    const confirmed = await showConfirm({
      title: 'Удаление учителя',
      message: `Удалить учителя ${teacherName}?`,
      variant: 'danger',
      confirmText: 'Удалить',
      cancelText: 'Отмена'
    });
    if (!confirmed) return;
    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`/accounts/api/admin/teachers/${teacherId}/delete/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Не удалось удалить');
      }
      await loadTeachers();
      if (selectedTeacherId === teacherId) {
        setSelectedTeacherId(null);
        setSelectedTeacher(null);
        setProfile(null);
      }
      setActionMessage('Учитель удален');
    } catch (error) {
      setActionError(error.message || 'Ошибка удаления учителя');
    }
  };

  const handleSubscriptionAction = async (action) => {
    if (!selectedTeacherId) return;
    try {
      setActionLoading(true);
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`/accounts/api/admin/teachers/${selectedTeacherId}/subscription/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ action, days: 28 })
      });
      const contentType = response.headers.get('content-type');
      const data = contentType && contentType.includes('application/json') ? await response.json() : {};
      if (!response.ok) {
        const text = !contentType || !contentType.includes('application/json') ? await response.text() : '';
        throw new Error(data.error || text?.slice(0, 180) || 'Не удалось обновить подписку');
      }
      setProfile((prev) => prev ? { ...prev, subscription: data.subscription } : prev);
      setActionMessage(action === 'activate' ? 'Подписка активирована на 28 дней' : 'Подписка переведена в ожидание');
      loadTeachers(true);
    } catch (error) {
      setActionError(error.message || 'Ошибка обновления подписки');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddStorage = async () => {
    if (!selectedTeacherId) return;
    if (!storageInput || Number(storageInput) <= 0) {
      setActionError('Введите количество гигабайт больше 0');
      return;
    }
    try {
      setActionLoading(true);
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`/accounts/api/admin/teachers/${selectedTeacherId}/storage/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ extra_gb: Number(storageInput) })
      });
      const contentType = response.headers.get('content-type');
      const data = contentType && contentType.includes('application/json') ? await response.json() : {};
      if (!response.ok) {
        const text = !contentType || !contentType.includes('application/json') ? await response.text() : '';
        throw new Error(data.error || text?.slice(0, 180) || 'Не удалось увеличить хранилище');
      }
      setProfile((prev) => prev ? { ...prev, subscription: data.subscription } : prev);
      setActionMessage(`Добавлено ${storageInput} ГБ к хранилищу`);
      setStorageInput(5);
      loadTeachers(true);
    } catch (error) {
      setActionError(error.message || 'Ошибка увеличения хранилища');
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateZoom = async (e) => {
    e.preventDefault();
    if (!selectedTeacherId) return;
    try {
      setActionLoading(true);
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`/accounts/api/admin/teachers/${selectedTeacherId}/zoom/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(zoomForm)
      });
      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        const data = contentType && contentType.includes('application/json') ? await response.json() : {};
        const text = !contentType || !contentType.includes('application/json') ? await response.text() : '';
        throw new Error(data.error || text?.slice(0, 180) || 'Не удалось сохранить Zoom данные');
      }
      setActionMessage('Zoom credentials сохранены');
      loadTeachers(true);
    } catch (error) {
      setActionError(error.message || 'Ошибка сохранения Zoom данных');
    } finally {
      setActionLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (!selectedTeacherId || !newPassword) return;
    if (newPassword.length < 6) {
      setActionError('Пароль должен быть минимум 6 символов');
      return;
    }
    try {
      setActionLoading(true);
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`/accounts/api/admin/teachers/${selectedTeacherId}/change-password/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ new_password: newPassword })
      });
      const contentType = response.headers.get('content-type');
      const data = contentType && contentType.includes('application/json') ? await response.json() : {};
      if (!response.ok) {
        throw new Error(data.error || 'Не удалось изменить пароль');
      }
      setActionMessage(data.message || 'Пароль успешно изменен');
      setNewPassword('');
      setShowPasswordForm(false);
    } catch (error) {
      setActionError(error.message || 'Ошибка изменения пароля');
    } finally {
      setActionLoading(false);
    }
  };

  const formatDate = (value) => {
    if (!value) return '—';
    return new Date(value).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const formatDateTime = (value) => {
    if (!value) return '—';
    return new Date(value).toLocaleString('ru-RU');
  };

  const formatDuration = (minutes) => {
    if (!minutes) return '0 ч';
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours === 0) return `${mins} мин`;
    if (mins === 0) return `${hours} ч`;
    return `${hours} ч ${mins} мин`;
  };

  if (loading) {
    return (
      <div className="teachers-manage-overlay">
        <div className="teachers-manage-modal">
          <div className="tm-loading">Загрузка...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="teachers-manage-overlay" onClick={onClose}>
      <div className="teachers-manage-modal" onClick={(e) => e.stopPropagation()}>
        <div className="tm-header">
          <h2>👨‍🏫 Управление учителями</h2>
          <div className="tm-header-actions">
            <button className="tm-refresh" onClick={() => loadTeachers()} title="Обновить список">
              🔄
            </button>
            <button className="tm-close" onClick={onClose}>✕</button>
          </div>
        </div>
        <div className="tm-body">
          <div className="tm-left-panel">
            <div className="tm-search-box">
              <input
                type="text"
                placeholder="Поиск по имени или email"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="tm-teacher-cards">
              {filteredTeachers.map((teacher) => {
                const status = teacher.subscription?.status || 'none';
                return (
                  <button
                    key={teacher.id}
                    className={`tm-teacher-card ${teacher.id === selectedTeacherId ? 'active' : ''}`}
                    onClick={() => handleSelectTeacher(teacher)}
                  >
                    <div className="tm-teacher-card-name">
                      {teacher.last_name} {teacher.first_name}
                    </div>
                    <div className="tm-teacher-card-email">{teacher.email}</div>
                    <div className="tm-teacher-card-meta">
                      <span className={`tm-status-pill mini ${status}`}>
                        {statusLabels[status] || status}
                      </span>
                      <span className="tm-meta-value">
                        {teacher.metrics?.lessons_last_30_days || 0} уроков · {teacher.metrics?.total_students || 0} учеников
                      </span>
                    </div>
                    <div className="tm-card-footer">
                      <span>{teacher.days_on_platform} дней на платформе</span>
                      <button
                        className="tm-delete-inline"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteTeacher(teacher.id, `${teacher.first_name} ${teacher.last_name}`);
                        }}
                      >
                        🗑️
                      </button>
                    </div>
                  </button>
                );
              })}
              {filteredTeachers.length === 0 && (
                <div className="tm-empty">Учителя не найдены</div>
              )}
            </div>
          </div>
          <div className="tm-right-panel">
            {actionError && <div className="tm-banner error">{actionError}</div>}
            {actionMessage && <div className="tm-banner success">{actionMessage}</div>}
            {!selectedTeacherId && (
              <div className="tm-empty-state">Выберите учителя слева, чтобы увидеть подробности</div>
            )}
            {selectedTeacherId && (
              <div className="tm-details">
                {profileLoading && !profile && <div className="tm-loading">Загрузка данных...</div>}
                {profile && (
                  <>
                    <div className="tm-detail-header">
                      <div>
                        <h3>{profile.teacher.last_name} {profile.teacher.first_name}</h3>
                        <p>{profile.teacher.email}</p>
                      </div>
                      <span className={`tm-status-pill ${profile.subscription?.status || 'none'}`}>
                        {statusLabels[profile.subscription?.status] || 'Нет подписки'}
                      </span>
                    </div>

                    <div className="tm-info-grid">
                      <div>
                        <span>Телефон</span>
                        <strong>{profile.teacher.phone_number || '—'}</strong>
                      </div>
                      <div>
                        <span>На платформе</span>
                        <strong>{profile.teacher.days_on_platform} дней</strong>
                      </div>
                      <div>
                        <span>Создан</span>
                        <strong>{formatDate(profile.teacher.created_at)}</strong>
                      </div>
                      <div>
                        <span>Последний вход</span>
                        <strong>{formatDateTime(profile.teacher.last_login)}</strong>
                      </div>
                    </div>

                    <div className="tm-metrics-grid">
                      <div className="tm-metric-card">
                        <span>Уроков за 30 дней</span>
                        <strong>{profile.metrics.lessons_last_30_days || 0}</strong>
                        <small>Всего: {profile.metrics.total_lessons || 0}</small>
                      </div>
                      <div className="tm-metric-card">
                        <span>Время преподавания (30 дней)</span>
                        <strong>{formatDuration(profile.metrics.teaching_minutes_last_30_days)}</strong>
                        <small>{profile.metrics.teaching_hours_last_30_days} ч</small>
                      </div>
                      <div className="tm-metric-card">
                        <span>Ученики</span>
                        <strong>{profile.metrics.total_students || 0}</strong>
                        <small>Групп: {profile.metrics.total_groups || 0}</small>
                      </div>
                    </div>

                    <div className="tm-section">
                      <div className="tm-section-header">
                        <h4>Подписка</h4>
                        <span className="tm-plan-label">{profile.subscription?.plan || '—'}</span>
                      </div>
                      <div className="tm-subscription-details">
                        <div>
                          <span>Статус</span>
                          <strong>{statusLabels[profile.subscription?.status] || 'Нет'}</strong>
                        </div>
                        <div>
                          <span>Действует до</span>
                          <strong>{formatDateTime(profile.subscription?.expires_at)}</strong>
                        </div>
                        <div>
                          <span>Осталось дней</span>
                          <strong>{profile.subscription?.remaining_days ?? 0}</strong>
                        </div>
                        <div>
                          <span>Хранилище</span>
                          <strong>{profile.subscription?.used_storage_gb || 0} / {profile.subscription?.total_storage_gb || 0} ГБ</strong>
                        </div>
                      </div>
                      <div className="tm-storage-progress">
                        <div
                          className="tm-storage-progress-bar"
                          style={{ width: `${profile.subscription?.storage_usage_percent || 0}%` }}
                        />
                      </div>
                      <div className="tm-actions-row">
                        <button
                          className="btn-submit"
                          disabled={actionLoading}
                          onClick={() => handleSubscriptionAction('activate')}
                        >
                          Активировать на 28 дней
                        </button>
                        <button
                          className="btn-outline"
                          disabled={actionLoading}
                          onClick={() => handleSubscriptionAction('deactivate')}
                        >
                          Деактивировать
                        </button>
                      </div>
                      <div className="tm-storage-form">
                        <input
                          type="number"
                          min="1"
                          value={storageInput}
                          onChange={(e) => setStorageInput(e.target.value)}
                        />
                        <button
                          className="btn-submit"
                          disabled={actionLoading}
                          onClick={handleAddStorage}
                        >
                          + ГБ хранилища
                        </button>
                      </div>
                    </div>

                    <div className="tm-section">
                      <div className="tm-section-header">
                        <h4>Zoom credentials</h4>
                        {profile.zoom?.has_zoom_config ? <span className="tm-status-pill success">Настроено</span> : <span className="tm-status-pill warning">Не настроено</span>}
                      </div>
                      <form onSubmit={handleUpdateZoom} className="tm-zoom-grid">
                        <div className="form-group">
                          <label>Zoom Account ID *</label>
                          <input
                            type="text"
                            value={zoomForm.zoom_account_id}
                            onChange={(e) => setZoomForm({ ...zoomForm, zoom_account_id: e.target.value })}
                            required
                          />
                        </div>
                        <div className="form-group">
                          <label>Zoom Client ID *</label>
                          <input
                            type="text"
                            value={zoomForm.zoom_client_id}
                            onChange={(e) => setZoomForm({ ...zoomForm, zoom_client_id: e.target.value })}
                            required
                          />
                        </div>
                        <div className="form-group">
                          <label>Zoom Client Secret *</label>
                          <input
                            type="password"
                            value={zoomForm.zoom_client_secret}
                            onChange={(e) => setZoomForm({ ...zoomForm, zoom_client_secret: e.target.value })}
                            required
                          />
                        </div>
                        <div className="form-group">
                          <label>Zoom User ID</label>
                          <input
                            type="text"
                            value={zoomForm.zoom_user_id}
                            onChange={(e) => setZoomForm({ ...zoomForm, zoom_user_id: e.target.value })}
                          />
                        </div>
                        <div className="tm-actions-row">
                          <button type="submit" className="btn-submit" disabled={actionLoading}>
                            Сохранить Zoom данные
                          </button>
                        </div>
                      </form>
                    </div>

                    <div className="tm-section">
                      <div className="tm-section-header">
                        <h4>🔐 Изменение пароля</h4>
                      </div>
                      {!showPasswordForm ? (
                        <button 
                          className="btn-outline" 
                          onClick={() => setShowPasswordForm(true)}
                        >
                          Сменить пароль учителю
                        </button>
                      ) : (
                        <form onSubmit={handleChangePassword} className="tm-password-form">
                          <div className="form-group">
                            <label>Новый пароль *</label>
                            <input
                              type="password"
                              value={newPassword}
                              onChange={(e) => setNewPassword(e.target.value)}
                              placeholder="Минимум 6 символов"
                              minLength={6}
                              required
                            />
                          </div>
                          <div className="tm-actions-row">
                            <button type="submit" className="btn-submit" disabled={actionLoading}>
                              Сохранить пароль
                            </button>
                            <button 
                              type="button" 
                              className="btn-outline" 
                              onClick={() => {
                                setShowPasswordForm(false);
                                setNewPassword('');
                              }}
                            >
                              Отмена
                            </button>
                          </div>
                        </form>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        <Notification
          isOpen={notification.isOpen}
          onClose={closeNotification}
          type={notification.type}
          title={notification.title}
          message={notification.message}
        />

        <ConfirmModal
          isOpen={confirm.isOpen}
          onClose={closeConfirm}
          onConfirm={confirm.onConfirm}
          title={confirm.title}
          message={confirm.message}
          variant={confirm.variant}
          confirmText={confirm.confirmText}
          cancelText={confirm.cancelText}
        />
      </div>
    </div>
  );
};

export default TeachersManage;
