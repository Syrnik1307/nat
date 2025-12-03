import React, { useState, useEffect } from 'react';
import './SystemSettings.css';
import apiService from '../apiService';

const SystemSettings = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState('email');
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.get('/api/admin/settings/');
      setSettings(data);
    } catch (err) {
      setError('Не удалось загрузить настройки: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);
      const updated = await apiService.put('/api/admin/settings/', settings);
      setSettings(updated);
      setSuccessMessage('Настройки успешно сохранены');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError('Не удалось сохранить: ' + (err.response?.data?.error || err.message));
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field, value) => {
    setSettings(prev => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <div className="settings-modal-overlay" onClick={onClose}>
        <div className="settings-modal" onClick={e => e.stopPropagation()}>
          <div className="settings-loading">Загрузка настроек...</div>
        </div>
      </div>
    );
  }

  if (!settings) {
    return null;
  }

  const tabs = [
    { id: 'email', label: 'Email', icon: '📧' },
    { id: 'notifications', label: 'Уведомления', icon: '🔔' },
    { id: 'zoom', label: 'Zoom', icon: '🎥' },
    { id: 'schedule', label: 'Расписание', icon: '📅' },
    { id: 'branding', label: 'Брендинг', icon: '🎨' },
  ];

  return (
    <div className="settings-modal-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={e => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Настройки системы</h2>
          <button className="settings-close" onClick={onClose}>×</button>
        </div>

        {error && <div className="settings-error">{error}</div>}
        {successMessage && <div className="settings-success">{successMessage}</div>}

        <div className="settings-tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`settings-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
            </button>
          ))}
        </div>

        <div className="settings-content">
          {activeTab === 'email' && (
            <div className="settings-section">
              <h3>Настройки Email</h3>
              
              <div className="settings-field">
                <label>Email отправителя</label>
                <input
                  type="email"
                  value={settings.email_from}
                  onChange={e => handleChange('email_from', e.target.value)}
                  placeholder="noreply@teachingpanel.com"
                />
              </div>

              <div className="settings-field-checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={settings.email_notifications_enabled}
                    onChange={e => handleChange('email_notifications_enabled', e.target.checked)}
                  />
                  <span>Email уведомления включены</span>
                </label>
              </div>

              <div className="settings-field-checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={settings.welcome_email_enabled}
                    onChange={e => handleChange('welcome_email_enabled', e.target.checked)}
                  />
                  <span>Отправлять приветственное письмо при регистрации</span>
                </label>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="settings-section">
              <h3>Настройки уведомлений</h3>
              
              <div className="settings-field">
                <label>Напоминание о занятии (часов)</label>
                <input
                  type="number"
                  min="0"
                  max="168"
                  value={settings.lesson_reminder_hours}
                  onChange={e => handleChange('lesson_reminder_hours', parseInt(e.target.value))}
                />
                <small>За сколько часов напоминать о предстоящем занятии</small>
              </div>

              <div className="settings-field">
                <label>Напоминание о дедлайне ДЗ (часов)</label>
                <input
                  type="number"
                  min="0"
                  max="168"
                  value={settings.homework_deadline_reminder_hours}
                  onChange={e => handleChange('homework_deadline_reminder_hours', parseInt(e.target.value))}
                />
                <small>За сколько часов напоминать о дедлайне домашнего задания</small>
              </div>

              <div className="settings-field-checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={settings.push_notifications_enabled}
                    onChange={e => handleChange('push_notifications_enabled', e.target.checked)}
                  />
                  <span>Push уведомления (browser notifications)</span>
                </label>
              </div>
            </div>
          )}

          {activeTab === 'zoom' && (
            <div className="settings-section">
              <h3>Настройки Zoom по умолчанию</h3>
              
              <div className="settings-field">
                <label>Длительность занятия (минут)</label>
                <input
                  type="number"
                  min="15"
                  max="480"
                  step="15"
                  value={settings.default_lesson_duration}
                  onChange={e => handleChange('default_lesson_duration', parseInt(e.target.value))}
                />
                <small>От 15 минут до 8 часов</small>
              </div>

              <div className="settings-field-checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={settings.auto_recording}
                    onChange={e => handleChange('auto_recording', e.target.checked)}
                  />
                  <span>Автоматическая запись занятий</span>
                </label>
              </div>

              <div className="settings-field-checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={settings.waiting_room_enabled}
                    onChange={e => handleChange('waiting_room_enabled', e.target.checked)}
                  />
                  <span>Комната ожидания включена</span>
                </label>
              </div>
            </div>
          )}

          {activeTab === 'schedule' && (
            <div className="settings-section">
              <h3>Правила расписания</h3>
              
              <div className="settings-field">
                <label>Минимум часов до занятия</label>
                <input
                  type="number"
                  min="0"
                  max="48"
                  value={settings.min_booking_hours}
                  onChange={e => handleChange('min_booking_hours', parseInt(e.target.value))}
                />
                <small>За сколько часов минимум можно забронировать занятие</small>
              </div>

              <div className="settings-field">
                <label>Максимум дней вперед</label>
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={settings.max_booking_days}
                  onChange={e => handleChange('max_booking_days', parseInt(e.target.value))}
                />
                <small>На сколько дней вперед можно бронировать занятия</small>
              </div>

              <div className="settings-field">
                <label>Отмена занятия (часов)</label>
                <input
                  type="number"
                  min="0"
                  max="72"
                  value={settings.cancellation_hours}
                  onChange={e => handleChange('cancellation_hours', parseInt(e.target.value))}
                />
                <small>За сколько часов можно отменить занятие без штрафа</small>
              </div>
            </div>
          )}

          {activeTab === 'branding' && (
            <div className="settings-section">
              <h3>Брендинг платформы</h3>
              
              <div className="settings-field">
                <label>Название платформы</label>
                <input
                  type="text"
                  value={settings.platform_name}
                  onChange={e => handleChange('platform_name', e.target.value)}
                  placeholder="Easy Teaching"
                />
              </div>

              <div className="settings-field">
                <label>Email поддержки</label>
                <input
                  type="email"
                  value={settings.support_email}
                  onChange={e => handleChange('support_email', e.target.value)}
                  placeholder="support@teachingpanel.com"
                />
              </div>

              <div className="settings-field">
                <label>URL логотипа</label>
                <input
                  type="url"
                  value={settings.logo_url}
                  onChange={e => handleChange('logo_url', e.target.value)}
                  placeholder="https://example.com/logo.png"
                />
                <small>Ссылка на изображение логотипа</small>
              </div>

              <div className="settings-field">
                <label>Основной цвет (HEX)</label>
                <div className="color-picker-wrapper">
                  <input
                    type="color"
                    value={settings.primary_color}
                    onChange={e => handleChange('primary_color', e.target.value)}
                    className="color-input"
                  />
                  <input
                    type="text"
                    value={settings.primary_color}
                    onChange={e => handleChange('primary_color', e.target.value)}
                    placeholder="#4F46E5"
                    className="hex-input"
                    pattern="^#[0-9A-Fa-f]{6}$"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="settings-footer">
          <button className="settings-btn-cancel" onClick={onClose}>
            Отмена
          </button>
          <button
            className="settings-btn-save"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SystemSettings;
