import React, { useState, useEffect } from 'react';
import { useAuth } from '../../auth';
import { apiClient } from '../../apiService';
import { Input, Button, Notification } from '../../shared/components';
import './OlgaProfile.css';

/**
 * OlgaProfile — профиль пользователя для тенанта Ольги.
 */
const OlgaProfile = () => {
  const { user } = useAuth();
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
  });
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState({ isOpen: false, type: 'info', title: '', message: '' });

  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        phone: user.phone || '',
      });
    }
  }, [user]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiClient.patch('accounts/profile/', {
        first_name: formData.first_name,
        last_name: formData.last_name,
        phone: formData.phone,
      });
      setNotification({ isOpen: true, type: 'success', title: 'Сохранено', message: 'Профиль обновлён' });
    } catch (err) {
      setNotification({ isOpen: true, type: 'error', title: 'Ошибка', message: 'Не удалось сохранить' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="olga-profile-page">
      <div className="olga-profile-card">
        <div className="olga-profile-avatar">
          <span className="olga-avatar-letter">
            {(formData.first_name || formData.email || '?')[0].toUpperCase()}
          </span>
        </div>
        <h2 className="olga-profile-name">
          {formData.first_name} {formData.last_name}
        </h2>
        <p className="olga-profile-email">{formData.email}</p>

        <form className="olga-profile-form" onSubmit={handleSave}>
          <div className="olga-pf-row">
            <div className="olga-pf-group">
              <label>Имя</label>
              <Input
                type="text"
                value={formData.first_name}
                onChange={(e) => handleChange('first_name', e.target.value)}
                placeholder="Ваше имя"
              />
            </div>
            <div className="olga-pf-group">
              <label>Фамилия</label>
              <Input
                type="text"
                value={formData.last_name}
                onChange={(e) => handleChange('last_name', e.target.value)}
                placeholder="Ваша фамилия"
              />
            </div>
          </div>

          <div className="olga-pf-group">
            <label>Email</label>
            <Input
              type="email"
              value={formData.email}
              disabled
              placeholder="Email"
            />
            <span className="olga-pf-hint">Email нельзя изменить</span>
          </div>

          <div className="olga-pf-group">
            <label>Телефон</label>
            <Input
              type="tel"
              value={formData.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
              placeholder="+7 (999) 123-45-67"
            />
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="olga-profile-save"
          >
            {loading ? 'Сохранение...' : 'Сохранить'}
          </Button>
        </form>

        {/* Мои курсы */}
        <div className="olga-profile-courses">
          <h3>Мои курсы</h3>
          <p className="olga-pf-courses-hint">
            Здесь будут отображаться приобретённые курсы
          </p>
        </div>
      </div>

      <Notification
        isOpen={notification.isOpen}
        onClose={() => setNotification(prev => ({ ...prev, isOpen: false }))}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />
    </div>
  );
};

export default OlgaProfile;
