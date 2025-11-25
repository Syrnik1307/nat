import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth';
import apiService from '../apiService';
import './TeachersManage.css';

const TeachersManage = ({ onClose }) => {
  const { user } = useAuth();
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTeacher, setSelectedTeacher] = useState(null);
  const [showZoomForm, setShowZoomForm] = useState(false);
  const [zoomForm, setZoomForm] = useState({
    zoom_account_id: '',
    zoom_client_id: '',
    zoom_client_secret: '',
    zoom_user_id: ''
  });
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  useEffect(() => {
    loadTeachers();
    // Автообновление списка каждые 5 секунд
    const interval = setInterval(loadTeachers, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadTeachers = async () => {
    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('http://72.56.81.163:8001/accounts/api/admin/teachers/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error('Failed to load teachers');
      }

      const data = await response.json();
      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.results)
          ? data.results
          : [];

      setTeachers(list);
      setLoading(false);
    } catch (error) {
      console.error('Ошибка загрузки учителей:', error);
      setTeachers([]);
      setLoading(false);
    }
  };

  const handleSelectTeacher = (teacher) => {
    setSelectedTeacher(teacher);
    setZoomForm({
      zoom_account_id: teacher.zoom_account_id || '',
      zoom_client_id: teacher.zoom_client_id || '',
      zoom_client_secret: teacher.zoom_client_secret || '',
      zoom_user_id: teacher.zoom_user_id || ''
    });
    setShowZoomForm(true);
    setFormError('');
    setFormSuccess('');
  };

  const handleUpdateZoom = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');

    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`http://72.56.81.163:8001/accounts/api/admin/teachers/${selectedTeacher.id}/zoom/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(zoomForm)
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to update');
      }
      setFormSuccess('Zoom credentials успешно обновлены!');
      // Перезагружаем список учителей
      loadTeachers();
      // Закрываем форму через 2 секунды
      setTimeout(() => {
        setShowZoomForm(false);
        setSelectedTeacher(null);
        setFormSuccess('');
      }, 2000);
    } catch (error) {
      setFormError(error.response?.data?.error || 'Ошибка обновления Zoom credentials');
    }
  };

  const handleDeleteTeacher = async (teacherId, teacherName) => {
    if (!window.confirm(`Вы уверены, что хотите удалить учителя ${teacherName}? Это действие нельзя отменить.`)) {
      return;
    }

    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`http://72.56.81.163:8001/accounts/api/admin/teachers/${teacherId}/delete/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to delete');
      }
      
      // Обновляем список учителей
      await loadTeachers();
      
      // Если удаляем текущего выбранного учителя, закрываем форму
      if (selectedTeacher?.id === teacherId) {
        setShowZoomForm(false);
        setSelectedTeacher(null);
      }
    } catch (error) {
      alert('Ошибка удаления учителя: ' + (error.message || 'Неизвестная ошибка'));
    }
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

  const teacherList = Array.isArray(teachers) ? teachers : [];

  return (
    <div className="teachers-manage-overlay" onClick={onClose}>
      <div className="teachers-manage-modal" onClick={(e) => e.stopPropagation()}>
        <div className="tm-header">
          <h2>👨‍🏫 Управление учителями</h2>
          <button className="tm-refresh" onClick={loadTeachers} title="Обновить список">
            🔄
          </button>
          <button className="tm-close" onClick={onClose}>✕</button>
        </div>

        <div className="tm-content">
          {!showZoomForm ? (
            <div className="tm-teachers-list">
              <div className="tm-list-header">
                <span>Учитель</span>
                <span>Email</span>
                <span>Zoom статус</span>
                <span>Действия</span>
              </div>
              {teacherList.map((teacher) => (
                <div 
                  key={teacher.id} 
                  className="tm-teacher-item"
                >
                  <div className="tm-teacher-name" onClick={() => handleSelectTeacher(teacher)}>
                    {teacher.last_name} {teacher.first_name} {teacher.middle_name}
                  </div>
                  <div className="tm-teacher-email" onClick={() => handleSelectTeacher(teacher)}>{teacher.email}</div>
                  <div className={`tm-zoom-status ${teacher.has_zoom_config ? 'configured' : 'not-configured'}`} onClick={() => handleSelectTeacher(teacher)}>
                    {teacher.has_zoom_config ? (
                      <>
                        <span className="status-icon">✓</span>
                        Настроен
                      </>
                    ) : (
                      <>
                        <span className="status-icon">⚠</span>
                        Не настроен
                      </>
                    )}
                  </div>
                  <div className="tm-teacher-actions">
                    <button 
                      className="tm-delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteTeacher(teacher.id, `${teacher.first_name} ${teacher.last_name}`);
                      }}
                      title="Удалить учителя"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
              {teacherList.length === 0 && (
                <div className="tm-empty">Нет учителей в системе</div>
              )}
            </div>
          ) : (
            <div className="tm-zoom-form">
              <button className="tm-back" onClick={() => setShowZoomForm(false)}>
                ← Назад к списку
              </button>
              
              <div className="tm-selected-teacher">
                <h3>Настройка Zoom для: {selectedTeacher.last_name} {selectedTeacher.first_name}</h3>
                <p className="tm-teacher-email-small">{selectedTeacher.email}</p>
              </div>

              <form onSubmit={handleUpdateZoom}>
                {formError && <div className="form-error">{formError}</div>}
                {formSuccess && <div className="form-success">{formSuccess}</div>}

                <div className="form-group">
                  <label>Zoom Account ID *</label>
                  <input
                    type="text"
                    value={zoomForm.zoom_account_id}
                    onChange={(e) => setZoomForm({ ...zoomForm, zoom_account_id: e.target.value })}
                    placeholder="6w5GrnCgSgaHwMFFbhmlKw"
                    required
                  />
                  <small>Account ID из Zoom App Marketplace</small>
                </div>

                <div className="form-group">
                  <label>Zoom Client ID *</label>
                  <input
                    type="text"
                    value={zoomForm.zoom_client_id}
                    onChange={(e) => setZoomForm({ ...zoomForm, zoom_client_id: e.target.value })}
                    placeholder="vNl9EzZTy6h2UifsGVERg"
                    required
                  />
                  <small>Client ID из Zoom App</small>
                </div>

                <div className="form-group">
                  <label>Zoom Client Secret *</label>
                  <input
                    type="password"
                    value={zoomForm.zoom_client_secret}
                    onChange={(e) => setZoomForm({ ...zoomForm, zoom_client_secret: e.target.value })}
                    placeholder="••••••••••••••••••••"
                    required
                  />
                  <small>Client Secret из Zoom App</small>
                </div>

                <div className="form-group">
                  <label>Zoom User ID</label>
                  <input
                    type="text"
                    value={zoomForm.zoom_user_id}
                    onChange={(e) => setZoomForm({ ...zoomForm, zoom_user_id: e.target.value })}
                    placeholder="me или email@example.com"
                  />
                  <small>User ID в Zoom (можно оставить пустым, будет использовано 'me')</small>
                </div>

                <div className="tm-help">
                  <h4>📚 Где взять Zoom credentials:</h4>
                  <ol>
                    <li>Перейдите на <a href="https://marketplace.zoom.us/" target="_blank" rel="noopener noreferrer">Zoom App Marketplace</a></li>
                    <li>Создайте Server-to-Server OAuth приложение</li>
                    <li>Скопируйте Account ID, Client ID и Client Secret</li>
                    <li>Активируйте необходимые scopes для создания встреч</li>
                  </ol>
                </div>

                <div className="form-actions">
                  <button type="button" onClick={() => setShowZoomForm(false)} className="btn-cancel">
                    Отмена
                  </button>
                  <button type="submit" className="btn-submit">
                    Сохранить Zoom credentials
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TeachersManage;
