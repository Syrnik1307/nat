import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Notification, ConfirmModal } from '../shared/components';
import useNotification from '../shared/hooks/useNotification';
import { getAccessToken } from '../apiService';
import './TeachersManage.css';

const statusLabels = {
  active: 'Активна',
  pending: 'Ожидает оплаты',
  expired: 'Истекла',
  cancelled: 'Отменена',
  trial: 'Триал',
  none: 'Нет подписки'
};

const PAGE_SIZE_OPTIONS = [50, 100, 200];

const TeachersManage = ({ onClose }) => {
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [sortKey, setSortKey] = useState('last_login');
  const [sortDir, setSortDir] = useState('desc');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [zoomFilter, setZoomFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedTeacherId, setSelectedTeacherId] = useState(null);
  const [storageInput, setStorageInput] = useState(5);
  const [zoomForm, setZoomForm] = useState({
    zoom_account_id: '',
    zoom_client_id: '',
    zoom_client_secret: '',
    zoom_user_id: '',
  });
  const [newPassword, setNewPassword] = useState('');
  const [showPasswordForm, setShowPasswordForm] = useState(false);

  const {
    notification,
    confirm,
    showNotification,
    closeNotification,
    showConfirm,
    closeConfirm
  } = useNotification();

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, statusFilter, zoomFilter, activeFilter, pageSize, sortKey, sortDir]);

  useEffect(() => {
    loadTeachers();
  }, [page, pageSize, debouncedSearch, statusFilter, zoomFilter, activeFilter, sortKey, sortDir]);

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

  // Список теперь фильтруется на бэке, поэтому оставляем как есть
  const filteredTeachers = useMemo(() => teachers, [teachers]);

  const loadTeachers = useCallback(async () => {
    try {
      setLoading(true);
      const token = getAccessToken();
      const params = new URLSearchParams({
        page,
        page_size: pageSize,
        sort: sortKey,
        order: sortDir,
      });
      if (debouncedSearch) params.append('q', debouncedSearch);
      if (statusFilter) params.append('status', statusFilter);
      if (zoomFilter) params.append('has_zoom', zoomFilter);
      if (activeFilter) params.append('active_recent', 'true');

      const response = await fetch(`/accounts/api/admin/teachers/?${params.toString()}`, {
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
      const list = Array.isArray(data?.results) ? data.results : [];
      setTeachers(list);
      setTotal(typeof data?.total === 'number' ? data.total : list.length);
      // reset selection on new page
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Ошибка загрузки учителей:', error);
      setActionError(error.message || 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedSearch, statusFilter, zoomFilter, activeFilter, sortKey, sortDir]);

  const loadTeacherProfile = async (teacherId) => {
    try {
      setProfileLoading(true);
      const token = getAccessToken();
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

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedIds(new Set(filteredTeachers.map((t) => t.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectOne = (teacherId, checked) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(teacherId);
      } else {
        next.delete(teacherId);
      }
      return next;
    });
  };

  const toggleSort = (key) => {
    if (sortKey === key) {
      setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
    setPage(1);
  };

  const handleBulk = async (action, extraPayload = {}) => {
    if (!selectedIds.size) return;
    if (action === 'delete') {
      const confirmed = await showConfirm({
        title: 'Удаление учителей',
        message: 'Удалить выбранных учителей? Это действие необратимо.',
        variant: 'danger',
        confirmText: 'Удалить',
      });
      if (!confirmed) return;
    }

    try {
      setActionLoading(true);
      setActionError('');
      const token = getAccessToken();
      const response = await fetch('/accounts/api/admin/teachers/bulk/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          action,
          ids: Array.from(selectedIds),
          ...extraPayload,
        })
      });
      const contentType = response.headers.get('content-type');
      const data = contentType && contentType.includes('application/json') ? await response.json() : {};
      if (!response.ok) {
        const text = !contentType || !contentType.includes('application/json') ? await response.text() : '';
        throw new Error(data.error || text?.slice(0, 180) || 'Не удалось выполнить действие');
      }

      const msg = data.message || `Готово: ${data.count || selectedIds.size} учителей`;
      setActionMessage(msg);
      if (action === 'reset_password' && Array.isArray(data.results) && data.results.length === 1) {
        const generated = data.results[0].generated_password;
        if (generated) {
          showNotification('info', 'Новый пароль', generated);
        }
      }
      if (action === 'delete' && selectedIds.has(selectedTeacherId)) {
        setSelectedTeacherId(null);
        setProfile(null);
      }
      setSelectedIds(new Set());
      await loadTeachers();
    } catch (error) {
      setActionError(error.message || 'Ошибка выполнения действия');
    } finally {
      setActionLoading(false);
    }
  };

  const handleBulkStorage = async () => {
    const value = window.prompt('Сколько ГБ добавить каждому?', '5');
    if (!value) return;
    const amount = Number(value);
    if (Number.isNaN(amount) || amount <= 0) {
      setActionError('Введите число больше 0');
      return;
    }
    await handleBulk('add_storage', { extra_gb: amount });
  };

  const handleSelectTeacher = (teacher) => {
    if (!teacher) {
      setSelectedTeacherId(null);
      setProfile(null);
      return;
    }
    setSelectedTeacherId(teacher.id);
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
      const token = getAccessToken();
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
      const token = getAccessToken();
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
      const token = getAccessToken();
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
      const token = getAccessToken();
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
      const token = getAccessToken();
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

  if (loading && teachers.length === 0) {
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
          <h2>Управление учителями</h2>
          <div className="tm-header-actions">
            <button className="tm-refresh" onClick={() => loadTeachers()} title="Обновить список">
              Обновить
            </button>
            <button className="tm-close" onClick={onClose}>Закрыть</button>
          </div>
        </div>
        <div className="tm-body">
          <div className="tm-left-panel">
            <div className="tm-controls">
              <input
                type="text"
                placeholder="Поиск по имени или email"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="">Статус подписки: все</option>
                <option value="active">Активна</option>
                <option value="pending">Ожидает оплаты</option>
                <option value="expired">Истекла</option>
                <option value="cancelled">Отменена</option>
                <option value="trial">Триал</option>
              </select>
              <select value={zoomFilter} onChange={(e) => setZoomFilter(e.target.value)}>
                <option value="">Zoom: все</option>
                <option value="true">Zoom настроен</option>
                <option value="false">Нет Zoom</option>
              </select>
              <label className="tm-checkbox">
                <input type="checkbox" checked={activeFilter} onChange={(e) => setActiveFilter(e.target.checked)} /> Активные (15 мин)
              </label>
              <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
                {PAGE_SIZE_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s} на странице</option>
                ))}
              </select>
            </div>

            <div className="tm-bulk-bar">
              <div className="tm-bulk-actions">
                <button className="btn-outline" disabled={!selectedIds.size || actionLoading} onClick={() => handleBulk('activate_subscription')}>Активировать</button>
                <button className="btn-outline" disabled={!selectedIds.size || actionLoading} onClick={() => handleBulk('deactivate_subscription')}>В ожидание</button>
                <button className="btn-outline" disabled={!selectedIds.size || actionLoading} onClick={handleBulkStorage}>+ ГБ</button>
                <button className="btn-outline" disabled={!selectedIds.size || actionLoading} onClick={() => handleBulk('reset_password')}>Сброс пароля</button>
                <button className="btn-outline danger" disabled={!selectedIds.size || actionLoading} onClick={() => handleBulk('delete')}>Удалить</button>
              </div>
              <div className="tm-pagination">
                <button disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>‹</button>
                <span>{page} / {totalPages}</span>
                <button disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>›</button>
              </div>
            </div>

            <div className="tm-table-wrap">
              <table className="tm-table">
                <thead>
                  <tr>
                    <th>
                      <input
                        type="checkbox"
                        checked={filteredTeachers.length > 0 && selectedIds.size === filteredTeachers.length}
                        onChange={(e) => handleSelectAll(e.target.checked)}
                      />
                    </th>
                    <th onClick={() => toggleSort('first_name')} className={sortKey === 'first_name' ? 'sorted' : ''}>Имя</th>
                    <th onClick={() => toggleSort('email')} className={sortKey === 'email' ? 'sorted' : ''}>Email</th>
                    <th>Подписка</th>
                    <th>Уроки/30д</th>
                    <th>Ученики</th>
                    <th onClick={() => toggleSort('created_at')} className={sortKey === 'created_at' ? 'sorted' : ''}>Создан</th>
                    <th onClick={() => toggleSort('last_login')} className={sortKey === 'last_login' ? 'sorted' : ''}>Последний вход</th>
                    <th>Zoom</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTeachers.map((teacher) => {
                    const status = teacher.subscription?.status || 'none';
                    const checked = selectedIds.has(teacher.id);
                    return (
                      <tr key={teacher.id} className={teacher.id === profile?.teacher?.id ? 'active' : ''}>
                        <td>
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => handleSelectOne(teacher.id, e.target.checked)}
                          />
                        </td>
                        <td onClick={() => handleSelectTeacher(teacher)} className="tm-click">
                          {teacher.last_name} {teacher.first_name}
                        </td>
                        <td onClick={() => handleSelectTeacher(teacher)} className="tm-click">{teacher.email}</td>
                        <td>
                          <span className={`tm-status-pill mini ${status}`}>{statusLabels[status] || 'Нет'}</span>
                        </td>
                        <td>{teacher.metrics?.lessons_last_30_days ?? 0}</td>
                        <td>{teacher.metrics?.total_students ?? 0}</td>
                        <td>{formatDate(teacher.created_at)}</td>
                        <td>{formatDateTime(teacher.last_login)}</td>
                        <td>{teacher.has_zoom_config ? 'Да' : 'Нет'}</td>
                      </tr>
                    );
                  })}
                  {!filteredTeachers.length && !loading && (
                    <tr><td colSpan="9" className="tm-empty">Учителя не найдены</td></tr>
                  )}
                  {loading && (
                    <tr><td colSpan="9" className="tm-loading">Загрузка...</td></tr>
                  )}
                </tbody>
              </table>
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
                        <span>Telegram</span>
                        <strong>
                          {profile.teacher.telegram_id ? (
                            <>
                              {profile.teacher.telegram_username && (
                                <span style={{ color: 'var(--accent-primary)' }}>@{profile.teacher.telegram_username}</span>
                              )}
                              {profile.teacher.telegram_username && ' '}
                              <span style={{ color: 'var(--text-light)', fontSize: '0.85em' }}>
                                (ID: {profile.teacher.telegram_id})
                              </span>
                            </>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>Не подключен</span>
                          )}
                        </strong>
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
                        <h4>Изменение пароля</h4>
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
