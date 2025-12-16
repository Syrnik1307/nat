import React, { useState, useEffect, useMemo } from 'react';
import { Notification, ConfirmModal } from '../shared/components';
import useNotification from '../shared/hooks/useNotification';
import { getAccessToken } from '../apiService';
import './StudentsManage.css';

const StudentsManage = ({ onClose }) => {
  const { notification, confirm, showNotification, closeNotification, showConfirm, closeConfirm } = useNotification();
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionError, setActionError] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [sortKey, setSortKey] = useState('last_login');
  const [sortDir, setSortDir] = useState('desc');

  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('active'); // active|archived|all
  const [teacherIdFilter, setTeacherIdFilter] = useState('');
  const [reloadSeq, setReloadSeq] = useState(0);

  const [teachers, setTeachers] = useState([]);
  const [teachersLoading, setTeachersLoading] = useState(false);
  const [teachersError, setTeachersError] = useState('');

  const [selectedStudentId, setSelectedStudentId] = useState(null);
  const [editForm, setEditForm] = useState({
    first_name: '',
    last_name: '',
    middle_name: '',
  });

  const PAGE_SIZE_OPTIONS = [50, 100, 200];
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const triggerReload = () => setReloadSeq((x) => x + 1);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        setTeachersLoading(true);
        setTeachersError('');
        const token = getAccessToken();

        const params = new URLSearchParams({
          page: '1',
          page_size: '200',
          sort: 'name',
          order: 'asc'
        });
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
        if (cancelled) return;
        setTeachers(list);
      } catch (error) {
        if (cancelled) return;
        setTeachersError(error.message || 'Ошибка загрузки учителей');
      } finally {
        if (!cancelled) setTeachersLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, statusFilter, teacherIdFilter, pageSize, sortKey, sortDir]);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        setLoading(true);
        setActionError('');
        const token = getAccessToken();

        const params = new URLSearchParams({
          page,
          page_size: pageSize,
          sort: sortKey,
          order: sortDir,
          status: statusFilter,
        });
        if (debouncedSearch) params.append('q', debouncedSearch);
        if (teacherIdFilter.trim()) params.append('teacher_id', teacherIdFilter.trim());

        const response = await fetch(`/accounts/api/admin/students/?${params.toString()}`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        );
        if (!response.ok) {
          const text = await response.text();
          throw new Error(text?.slice(0, 180) || 'Не удалось загрузить список учеников');
        }
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Сервер вернул не-JSON при загрузке учеников');
        }
        const data = await response.json();
        const list = Array.isArray(data?.results) ? data.results : [];
        if (cancelled) return;
        setStudents(list);
        setTotal(typeof data?.total === 'number' ? data.total : list.length);
      } catch (error) {
        console.error('Ошибка загрузки учеников:', error);
        if (cancelled) return;
        setActionError(error.message || 'Ошибка загрузки данных');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [page, pageSize, debouncedSearch, statusFilter, teacherIdFilter, sortKey, sortDir, reloadSeq]);

  useEffect(() => {
    if (students.length === 0) return;
    if (!selectedStudentId || !students.some((s) => s.id === selectedStudentId)) {
      setSelectedStudentId(students[0].id);
    }
  }, [students, selectedStudentId]);

  const selectedStudent = useMemo(
    () => students.find((s) => s.id === selectedStudentId) || null,
    [students, selectedStudentId]
  );

  useEffect(() => {
    if (!selectedStudent) return;
    setEditForm({
      first_name: selectedStudent.first_name || '',
      last_name: selectedStudent.last_name || '',
      middle_name: selectedStudent.middle_name || '',
    });
  }, [selectedStudent]);

  const handleSelectStudent = (student) => {
    setSelectedStudentId(student.id);
    setActionMessage('');
    setActionError('');
  };

  const toggleSort = (key) => {
    if (sortKey === key) {
      setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const formatDateTime = (value) => {
    if (!value) return '—';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString('ru-RU', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  };

  const formatLastSeen = (value) => {
    if (!value) return '—';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '—';
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const suffix = diffDays <= 0 ? 'сегодня' : `${diffDays}д назад`;
    return `${formatDateTime(value)} (${suffix})`;
  };

  const handleUpdateStudent = async (e) => {
    e.preventDefault();
    if (!selectedStudent) return;
    setActionError('');
    setActionMessage('');

    try {
      setActionLoading(true);
      const token = getAccessToken();
      const response = await fetch(`/accounts/api/admin/students/${selectedStudent.id}/update/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(editForm)
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to update');
      }
      setActionMessage('Данные ученика обновлены');
      triggerReload();
    } catch (error) {
      setActionError(error.message || 'Ошибка обновления данных');
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleArchive = async (student = null) => {
    const target = student || selectedStudent;
    if (!target) return;
    const nextActive = !target.is_active;
    const actionLabel = nextActive ? 'Восстановить' : 'Архивировать';

    const confirmed = await showConfirm({
      title: `${actionLabel} ученика`,
      message: nextActive
        ? 'Восстановить ученика и вернуть доступ к платформе?'
        : 'Архивировать ученика (заблокировать вход) без удаления данных?'
      ,
      variant: nextActive ? 'primary' : 'danger',
      confirmText: actionLabel,
      cancelText: 'Отмена'
    });
    if (!confirmed) return;

    try {
      setActionLoading(true);
      setActionError('');
      setActionMessage('');
      const token = getAccessToken();
      const response = await fetch(`/accounts/api/admin/students/${target.id}/update/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ is_active: nextActive })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Не удалось изменить статус');
      }
      setActionMessage(nextActive ? 'Ученик восстановлен' : 'Ученик архивирован');
      triggerReload();
    } catch (error) {
      setActionError(error.message || 'Ошибка изменения статуса');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteStudent = async (studentId, studentName) => {
    const confirmed = await showConfirm({
      title: 'Удаление ученика',
      message: `Вы уверены, что хотите удалить ученика ${studentName}? Это действие нельзя отменить.`,
      variant: 'danger',
      confirmText: 'Удалить',
      cancelText: 'Отмена'
    });
    if (!confirmed) return;

    try {
      setActionLoading(true);
      const token = getAccessToken();
      const response = await fetch(`/accounts/api/admin/students/${studentId}/delete/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to delete');
      }
      
      triggerReload();

      if (selectedStudentId === studentId) {
        setSelectedStudentId(null);
      }
      showNotification('success', 'Успешно', 'Ученик удален');
    } catch (error) {
      showNotification('error', 'Ошибка', 'Ошибка удаления ученика: ' + (error.message || 'Неизвестная ошибка'));
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="students-manage-overlay">
        <div className="students-manage-modal">
          <div className="sm-loading">Загрузка...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="students-manage-overlay" onClick={onClose}>
      <div className="students-manage-modal" onClick={(e) => e.stopPropagation()}>
        <div className="sm-header">
          <h2>Ученики</h2>
          <div className="sm-header-actions">
            <button className="sm-refresh" onClick={triggerReload} title="Обновить список">↻</button>
            <button className="sm-close" onClick={onClose} title="Закрыть">✕</button>
          </div>
        </div>

        <div className="sm-body">
          <div className="sm-left-panel">
            {(actionMessage || actionError) && (
              <div className={`sm-banner ${actionError ? 'error' : 'success'}`}>
                {actionError ? actionError : actionMessage}
              </div>
            )}

            <div className="sm-filters">
              <div className="sm-filter-row">
                <input
                  className="sm-search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Поиск: ФИО / email"
                />
                <select className="sm-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                  <option value="active">Активные</option>
                  <option value="archived">Архив</option>
                  <option value="all">Все</option>
                </select>
              </div>

              <div className="sm-filter-row">
                <select
                  className="sm-select sm-select-grow"
                  value={teacherIdFilter}
                  onChange={(e) => setTeacherIdFilter(e.target.value)}
                  disabled={teachersLoading}
                  title={teachersError || ''}
                >
                  <option value="">Все учителя</option>
                  {teachers.map((t) => {
                    const fullName = `${t.last_name || ''} ${t.first_name || ''}`.trim() || t.email;
                    return (
                      <option key={t.id} value={String(t.id)}>
                        {fullName} (ID: {t.id})
                      </option>
                    );
                  })}
                </select>

                <select className="sm-select" value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
                  {PAGE_SIZE_OPTIONS.map((n) => (
                    <option key={n} value={n}>{n} / стр</option>
                  ))}
                </select>
              </div>

              {teachersError && (
                <div className="sm-teachers-error">{teachersError}</div>
              )}

              <div className="sm-meta">
                <div>Всего: <b>{total}</b></div>
                <div className="sm-pager">
                  <button className="sm-page-btn" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>←</button>
                  <div className="sm-page-label">{page} / {totalPages}</div>
                  <button className="sm-page-btn" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>→</button>
                </div>
              </div>
            </div>

            <div className="sm-table-wrap">
              <table className="sm-table">
                <thead>
                  <tr>
                    <th className="sm-th" onClick={() => toggleSort('name')}>Ученик</th>
                    <th className="sm-th">Учителя</th>
                    <th className="sm-th" onClick={() => toggleSort('last_login')}>Последний вход</th>
                    <th className="sm-th">Статус</th>
                    <th className="sm-th sm-actions">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student) => {
                    const isSelected = student.id === selectedStudentId;
                    const teachers = Array.isArray(student.teachers) ? student.teachers : [];
                    const teacherPreview = teachers.slice(0, 2)
                      .map((t) => `${t.last_name || ''} ${t.first_name || ''}`.trim())
                      .filter(Boolean)
                      .join(', ');
                    const teacherSuffix = teachers.length > 2 ? ` +${teachers.length - 2}` : '';
                    return (
                      <tr
                        key={student.id}
                        className={`sm-row ${isSelected ? 'selected' : ''}`}
                        onClick={() => handleSelectStudent(student)}
                      >
                        <td className="sm-td">
                          <div className="sm-name">
                            {student.last_name} {student.first_name} {student.middle_name}
                          </div>
                          <div className="sm-sub">{student.email}</div>
                        </td>
                        <td className="sm-td" title={teachers.map((t) => `${t.last_name || ''} ${t.first_name || ''}`.trim()).filter(Boolean).join(', ')}>
                          {teacherPreview || '—'}{teacherSuffix}
                        </td>
                        <td className="sm-td">{formatLastSeen(student.last_login)}</td>
                        <td className="sm-td">
                          <span className={`sm-pill ${student.is_active ? 'active' : 'archived'}`}>
                            {student.is_active ? 'активен' : 'архив'}
                          </span>
                        </td>
                        <td className="sm-td sm-actions" onClick={(e) => e.stopPropagation()}>
                          <button
                            className="sm-mini"
                            disabled={actionLoading}
                            onClick={() => {
                              setSelectedStudentId(student.id);
                              handleToggleArchive(student);
                            }}
                            title={student.is_active ? 'Архивировать' : 'Восстановить'}
                          >
                            {student.is_active ? '🗄' : '↩'}
                          </button>
                          <button
                            className="sm-mini danger"
                            disabled={actionLoading}
                            onClick={() => handleDeleteStudent(student.id, `${student.last_name} ${student.first_name}`)}
                            title="Удалить"
                          >
                            ✕
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {students.length === 0 && (
                    <tr>
                      <td className="sm-empty" colSpan={5}>Нет учеников по выбранным фильтрам</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="sm-right-panel">
            {!selectedStudent ? (
              <div className="sm-empty-detail">Выберите ученика слева</div>
            ) : (
              <>
                <div className="sm-detail-header">
                  <div>
                    <h3>{selectedStudent.last_name} {selectedStudent.first_name}</h3>
                    <p>{selectedStudent.email}</p>
                  </div>
                  <span className={`sm-pill ${selectedStudent.is_active ? 'active' : 'archived'}`}>
                    {selectedStudent.is_active ? 'активен' : 'архив'}
                  </span>
                </div>

                <div className="sm-detail-grid">
                  <div className="sm-kv"><span>Регистрация</span><b>{formatDateTime(selectedStudent.created_at)}</b></div>
                  <div className="sm-kv"><span>Последний вход</span><b>{formatLastSeen(selectedStudent.last_login)}</b></div>
                </div>

                <div className="sm-section">
                  <div className="sm-section-title">Учителя</div>
                  <div className="sm-tags">
                    {(Array.isArray(selectedStudent.teachers) ? selectedStudent.teachers : []).length === 0 ? (
                      <span className="sm-muted">Нет привязанных учителей</span>
                    ) : (
                      (selectedStudent.teachers || []).map((t) => (
                        <span key={t.id} className="sm-tag">{t.last_name} {t.first_name}</span>
                      ))
                    )}
                  </div>
                </div>

                <div className="sm-section">
                  <div className="sm-section-title">Группы</div>
                  <div className="sm-tags">
                    {(Array.isArray(selectedStudent.groups) ? selectedStudent.groups : []).length === 0 ? (
                      <span className="sm-muted">Нет групп</span>
                    ) : (
                      (selectedStudent.groups || []).map((g) => (
                        <span key={g.id} className="sm-tag secondary">{g.name}</span>
                      ))
                    )}
                  </div>
                </div>

                <form className="sm-form" onSubmit={handleUpdateStudent}>
                  <div className="sm-section-title">Редактирование ФИО</div>
                  <div className="sm-form-row">
                    <label>Фамилия</label>
                    <input className="sm-input" value={editForm.last_name} onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })} />
                  </div>
                  <div className="sm-form-row">
                    <label>Имя</label>
                    <input className="sm-input" value={editForm.first_name} onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })} />
                  </div>
                  <div className="sm-form-row">
                    <label>Отчество</label>
                    <input className="sm-input" value={editForm.middle_name} onChange={(e) => setEditForm({ ...editForm, middle_name: e.target.value })} />
                  </div>

                  <div className="sm-detail-actions">
                    <button className="sm-btn" type="submit" disabled={actionLoading}>Сохранить</button>
                    <button className={`sm-btn ${selectedStudent.is_active ? 'danger' : ''}`} type="button" disabled={actionLoading} onClick={handleToggleArchive}>
                      {selectedStudent.is_active ? 'Архивировать' : 'Восстановить'}
                    </button>
                    <button
                      className="sm-btn danger"
                      type="button"
                      disabled={actionLoading}
                      onClick={() => handleDeleteStudent(selectedStudent.id, `${selectedStudent.last_name} ${selectedStudent.first_name}`)}
                    >
                      Удалить
                    </button>
                  </div>
                </form>
              </>
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

export default StudentsManage;
