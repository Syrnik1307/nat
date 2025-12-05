import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import apiService from '../apiService';
import Card from '../shared/components/Card';
import Button from '../shared/components/Button';
import Input from '../shared/components/Input';
import Modal from '../shared/components/Modal';
import './AdminDashboard.css';

const AdminDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [zoomAccounts, setZoomAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editAccount, setEditAccount] = useState(null);
  const [formData, setFormData] = useState({
    email: '',
    api_key: '',
    api_secret: '',
    max_concurrent_meetings: 1
  });
  const [error, setError] = useState('');

  // Проверка доступа - только админ
  useEffect(() => {
    if (user && user.role !== 'admin') {
      navigate('/');
    }
  }, [user, navigate]);

  useEffect(() => {
    if (user?.role === 'admin') {
      loadZoomAccounts();
    }
  }, [user]);

  const loadZoomAccounts = async () => {
    try {
      setLoading(true);
      const response = await apiService.getZoomAccounts();
      setZoomAccounts(response.data || []);
    } catch (err) {
      console.error('Failed to load Zoom accounts:', err);
      setError('Не удалось загрузить Zoom аккаунты');
    } finally {
      setLoading(false);
    }
  };

  const handleAddAccount = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      await apiService.createZoomAccount(formData);
      setShowAddModal(false);
      setFormData({
        email: '',
        api_key: '',
        api_secret: '',
        max_concurrent_meetings: 1
      });
      loadZoomAccounts();
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка при создании аккаунта');
    }
  };

  const handleEditAccount = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      await apiService.updateZoomAccount(editAccount.id, formData);
      setEditAccount(null);
      setFormData({
        email: '',
        api_key: '',
        api_secret: '',
        max_concurrent_meetings: 1
      });
      loadZoomAccounts();
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка при обновлении аккаунта');
    }
  };

  const handleDeleteAccount = async (id) => {
    if (!window.confirm('Вы уверены, что хотите удалить этот Zoom аккаунт?')) {
      return;
    }
    
    try {
      await apiService.deleteZoomAccount(id);
      loadZoomAccounts();
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка при удалении аккаунта');
    }
  };

  const handleReleaseAccount = async (id) => {
    try {
      await apiService.releaseZoomAccount(id);
      loadZoomAccounts();
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка при освобождении аккаунта');
    }
  };

  const openEditModal = (account) => {
    setEditAccount(account);
    setFormData({
      email: account.email,
      api_key: account.api_key,
      api_secret: account.api_secret,
      max_concurrent_meetings: account.max_concurrent_meetings
    });
  };

  const closeModal = () => {
    setShowAddModal(false);
    setEditAccount(null);
    setFormData({
      email: '',
      api_key: '',
      api_secret: '',
      max_concurrent_meetings: 1
    });
    setError('');
  };

  if (!user || user.role !== 'admin') {
    return null;
  }

  return (
    <div className="admin-dashboard">
      <div className="admin-header">
        <h1>🔧 Панель администратора</h1>
        <p className="admin-subtitle">Управление системой и Zoom Pool</p>
      </div>

      {/* Zoom Pool Management Section */}
      <section className="admin-section">
        <div className="section-header">
          <h2>📹 Управление Zoom Pool</h2>
          <Button onClick={() => setShowAddModal(true)}>
            + Добавить аккаунт
          </Button>
        </div>

        {error && (
          <div className="error-banner">
            {error}
            <button onClick={() => setError('')}>✕</button>
          </div>
        )}

        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Загрузка аккаунтов...</p>
          </div>
        ) : (
          <div className="zoom-accounts-grid">
            {zoomAccounts.length === 0 ? (
              <Card className="empty-state">
                <p>📭 Нет добавленных Zoom аккаунтов</p>
                <Button onClick={() => setShowAddModal(true)}>
                  Добавить первый аккаунт
                </Button>
              </Card>
            ) : (
              zoomAccounts.map(account => (
                <Card key={account.id} className="zoom-account-card">
                  <div className="account-header">
                    <div className="account-email">
                      <span className="email-icon">✉</span>
                      {account.email}
                    </div>
                    <div className={`status-badge ${account.is_active ? 'active' : 'inactive'}`}>
                      {account.is_active ? '✓ Активен' : '✕ Неактивен'}
                    </div>
                  </div>

                  <div className="account-stats">
                    <div className="stat">
                      <span className="stat-label">Встречи:</span>
                      <span className="stat-value">
                        {account.current_meetings} / {account.max_concurrent_meetings}
                      </span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Доступность:</span>
                      <span className={`availability ${account.is_available ? 'available' : 'busy'}`}>
                        {account.is_available ? '🟢 Доступен' : '🔴 Занят'}
                      </span>
                    </div>
                  </div>

                  {account.last_used_at && (
                    <div className="last-used">
                      Последнее использование: {new Date(account.last_used_at).toLocaleString('ru-RU')}
                    </div>
                  )}

                  <div className="account-actions">
                    <Button 
                      variant="secondary" 
                      size="small"
                      onClick={() => openEditModal(account)}
                    >
                      ✏️ Изменить
                    </Button>
                    {account.current_meetings > 0 && (
                      <Button 
                        variant="secondary" 
                        size="small"
                        onClick={() => handleReleaseAccount(account.id)}
                      >
                        🔓 Освободить
                      </Button>
                    )}
                    <Button 
                      variant="danger" 
                      size="small"
                      onClick={() => handleDeleteAccount(account.id)}
                    >
                      🗑️ Удалить
                    </Button>
                  </div>
                </Card>
              ))
            )}
          </div>
        )}
      </section>

      {/* Add/Edit Account Modal */}
      <Modal 
        isOpen={showAddModal || editAccount !== null} 
        onClose={closeModal}
        title={editAccount ? 'Редактировать Zoom аккаунт' : 'Добавить Zoom аккаунт'}
      >
        <form onSubmit={editAccount ? handleEditAccount : handleAddAccount} className="account-form">
          {error && <div className="form-error">{error}</div>}
          
          <Input
            label="Email аккаунта Zoom"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            required
            placeholder="zoom@example.com"
          />

          <Input
            label="API Key"
            type="text"
            value={formData.api_key}
            onChange={(e) => setFormData({...formData, api_key: e.target.value})}
            required
            placeholder="Введите API Key"
          />

          <Input
            label="API Secret"
            type="password"
            value={formData.api_secret}
            onChange={(e) => setFormData({...formData, api_secret: e.target.value})}
            required
            placeholder="Введите API Secret"
          />

          <Input
            label="Максимум одновременных встреч"
            type="number"
            min="1"
            max="10"
            value={formData.max_concurrent_meetings}
            onChange={(e) => setFormData({...formData, max_concurrent_meetings: parseInt(e.target.value)})}
            required
          />

          <div className="modal-actions">
            <Button type="button" variant="secondary" onClick={closeModal}>
              Отмена
            </Button>
            <Button type="submit">
              {editAccount ? 'Сохранить' : 'Добавить'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* System Stats Section (placeholder) */}
      <section className="admin-section">
        <h2>📊 Статистика системы</h2>
        <div className="stats-grid">
          <Card className="stat-card">
            <div className="stat-icon">👥</div>
            <div className="stat-info">
              <div className="stat-title">Всего пользователей</div>
              <div className="stat-number">—</div>
            </div>
          </Card>
          <Card className="stat-card">
            <div className="stat-icon">📚</div>
            <div className="stat-info">
              <div className="stat-title">Активных групп</div>
              <div className="stat-number">—</div>
            </div>
          </Card>
          <Card className="stat-card">
            <div className="stat-icon">📅</div>
            <div className="stat-info">
              <div className="stat-title">Уроков сегодня</div>
              <div className="stat-number">—</div>
            </div>
          </Card>
          <Card className="stat-card">
            <div className="stat-icon">📹</div>
            <div className="stat-info">
              <div className="stat-title">Zoom аккаунтов</div>
              <div className="stat-number">{zoomAccounts.length}</div>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
};

export default AdminDashboard;
