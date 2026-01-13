import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { useNotifications } from '../shared/context/NotificationContext';
import {
  updateCurrentUser,
  changePassword,
  getTelegramStatus,
  generateTelegramCode,
  unlinkTelegramAccount,
  getNotificationSettings,
  patchNotificationSettings,
} from '../apiService';
import SubscriptionPage from './SubscriptionPage';
import './ProfilePage.css';

const MAX_AVATAR_SIZE = 2 * 1024 * 1024;

const ProfilePage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const { showConfirm } = useNotifications();
  const [form, setForm] = useState({
    firstName: '',
    middleName: '',
    lastName: '',
    avatar: '',
  });
  const [avatarPreview, setAvatarPreview] = useState('');
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  
  // Состояние для смены пароля
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');

  // Telegram linking state
  const [telegramInfo, setTelegramInfo] = useState(null);
  const [telegramLoading, setTelegramLoading] = useState(false);
  const [telegramError, setTelegramError] = useState('');
  const [telegramSuccess, setTelegramSuccess] = useState('');
  const [codeInfo, setCodeInfo] = useState(null);
  const [codeLoading, setCodeLoading] = useState(false);
  const [codeMessage, setCodeMessage] = useState('');
  const [codeError, setCodeError] = useState('');

  // Telegram notification settings state
  const [notificationSettings, setNotificationSettings] = useState(null);
  const [notificationLoading, setNotificationLoading] = useState(false);
  const [notificationSaving, setNotificationSaving] = useState(false);
  const [notificationError, setNotificationError] = useState('');
  const [notificationSuccess, setNotificationSuccess] = useState('');

  const resolveInitialTab = () => {
    const params = new URLSearchParams(location.search);
    const tab = params.get('tab');
    return tab || 'profile';
  };

  const [activeTab, setActiveTab] = useState(resolveInitialTab); // 'profile' | 'security' | 'subscription'

  const tabConfig = useMemo(() => {
    if (!user) {
      return [{ key: 'profile', label: 'Профиль' }];
    }
    const items = [
      { key: 'profile', label: 'Профиль' },
      { key: 'telegram', label: 'Уведомления' },
      { key: 'security', label: 'Безопасность' },
    ];
    if (user.role === 'teacher') {
      items.push({ key: 'subscription', label: 'Моя подписка' });
    }
    return items;
  }, [user]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tabParam = params.get('tab');
    const allowedKeys = tabConfig.map((tab) => tab.key);

    if (tabParam && allowedKeys.includes(tabParam)) {
      setActiveTab(tabParam);
    } else if (!allowedKeys.includes(activeTab)) {
      setActiveTab('profile');
    }
  }, [location.search, tabConfig, activeTab]);

  const handleTabChange = (tabKey) => {
    setActiveTab(tabKey);
    const params = new URLSearchParams(location.search);
    if (tabKey === 'profile') {
      params.delete('tab');
    } else {
      params.set('tab', tabKey);
    }
    const search = params.toString();
    navigate({ pathname: location.pathname, search: search ? `?${search}` : '' }, { replace: true });
  };

  useEffect(() => {
    if (!user) return;
    setForm({
      firstName: user.first_name || '',
      middleName: user.middle_name || '',
      lastName: user.last_name || '',
      avatar: user.avatar || '',
    });
    setAvatarPreview(user.avatar || '');
  }, [user]);

  const fetchTelegramStatus = useCallback(async () => {
    setTelegramLoading(true);
    setTelegramError('');
    try {
      const { data } = await getTelegramStatus();
      setTelegramInfo(data);
    } catch (err) {
      console.error('Failed to load telegram status:', err);
      setTelegramError('Не удалось загрузить статус Telegram. Попробуйте позже.');
    } finally {
      setTelegramLoading(false);
    }
  }, []);

  const fetchNotificationSettings = useCallback(async () => {
    setNotificationLoading(true);
    setNotificationError('');
    try {
      const { data } = await getNotificationSettings();
      setNotificationSettings(data);
    } catch (err) {
      console.error('Failed to load notification settings:', err);
      setNotificationError('Не удалось загрузить настройки уведомлений. Попробуйте позже.');
    } finally {
      setNotificationLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'telegram' && !telegramInfo && !telegramLoading) {
      fetchTelegramStatus();
    }
    if (activeTab === 'telegram' && !notificationSettings && !notificationLoading) {
      fetchNotificationSettings();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const handleToggleNotificationSetting = (key) => {
    setNotificationSuccess('');
    setNotificationError('');
    setNotificationSettings(prev => {
      if (!prev) return prev;
      return { ...prev, [key]: !prev[key] };
    });
  };

  const handleChangeNotificationNumber = (key, value) => {
    setNotificationSuccess('');
    setNotificationError('');
    const num = parseInt(value, 10);
    if (!isNaN(num) && num >= 0) {
      setNotificationSettings(prev => {
        if (!prev) return prev;
        return { ...prev, [key]: num };
      });
    }
  };

  const handleSaveNotificationSettings = async () => {
    if (!notificationSettings) return;

    setNotificationSaving(true);
    setNotificationError('');
    setNotificationSuccess('');
    try {
      const payload = {
        telegram_enabled: notificationSettings.telegram_enabled,
        // Базовые — учитель
        notify_homework_submitted: notificationSettings.notify_homework_submitted,
        notify_subscription_expiring: notificationSettings.notify_subscription_expiring,
        notify_payment_success: notificationSettings.notify_payment_success,
        // Аналитика — учитель
        notify_absence_alert: notificationSettings.notify_absence_alert,
        absence_alert_threshold: notificationSettings.absence_alert_threshold,
        notify_performance_drop: notificationSettings.notify_performance_drop,
        performance_drop_percent: notificationSettings.performance_drop_percent,
        notify_group_health: notificationSettings.notify_group_health,
        notify_grading_backlog: notificationSettings.notify_grading_backlog,
        grading_backlog_threshold: notificationSettings.grading_backlog_threshold,
        grading_backlog_hours: notificationSettings.grading_backlog_hours,
        notify_inactive_student: notificationSettings.notify_inactive_student,
        inactive_student_days: notificationSettings.inactive_student_days,
        // Базовые — ученик
        notify_homework_graded: notificationSettings.notify_homework_graded,
        notify_homework_deadline: notificationSettings.notify_homework_deadline,
        notify_lesson_reminders: notificationSettings.notify_lesson_reminders,
        notify_new_homework: notificationSettings.notify_new_homework,
        // Аналитика — ученик
        notify_student_absence_warning: notificationSettings.notify_student_absence_warning,
        notify_control_point_deadline: notificationSettings.notify_control_point_deadline,
        notify_achievement: notificationSettings.notify_achievement,
        notify_inactivity_nudge: notificationSettings.notify_inactivity_nudge,
      };
      const { data } = await patchNotificationSettings(payload);
      setNotificationSettings(data);
      setNotificationSuccess('Настройки уведомлений сохранены.');
    } catch (err) {
      console.error('Failed to save notification settings:', err);
      setNotificationError('Не удалось сохранить настройки. Попробуйте позже.');
    } finally {
      setNotificationSaving(false);
    }
  };

  const handleGenerateTelegramCode = async () => {
    setCodeLoading(true);
    setCodeError('');
    setCodeMessage('');
    try {
      const { data } = await generateTelegramCode();
      setCodeInfo(data);
      setCodeMessage('Новый код создан. Он действует около 10 минут.');
    } catch (err) {
      console.error('Failed to generate telegram code:', err);
      setCodeError(err.response?.data?.detail || 'Не удалось создать код. Попробуйте позже.');
    } finally {
      setCodeLoading(false);
    }
  };

  const handleCopyValue = async (value, label = 'значение') => {
    if (!value) {
      return;
    }
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = value;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCodeMessage(`${label} скопировано в буфер обмена`);
      setTimeout(() => setCodeMessage(''), 3000);
    } catch (err) {
      console.error('Failed to copy value:', err);
      setCodeError('Не удалось скопировать. Скопируйте вручную.');
      setTimeout(() => setCodeError(''), 3000);
    }
  };

  const handleOpenTelegram = (url) => {
    if (url) {
      window.open(url, '_blank', 'noopener');
    }
  };

  const handleUnlinkTelegram = async () => {
    const confirmed = await showConfirm({
      title: 'Отвязать Telegram',
      message: 'Вы уверены, что хотите отвязать Telegram?',
      variant: 'warning',
      confirmText: 'Отвязать',
      cancelText: 'Отмена'
    });
    if (!confirmed) return;
    setTelegramError('');
    setTelegramSuccess('');
    try {
      await unlinkTelegramAccount();
      setCodeInfo(null);
      setTelegramSuccess('Telegram успешно отвязан.');
      setTimeout(() => setTelegramSuccess(''), 4000);
      await fetchTelegramStatus();
    } catch (err) {
      console.error('Failed to unlink telegram:', err);
      setTelegramError(err.response?.data?.detail || 'Не удалось отвязать Telegram. Попробуйте позже.');
    }
  };

  const registrationDate = useMemo(() => {
    if (!user?.created_at) return '';
    try {
      return new Date(user.created_at).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
    } catch (_err) {
      return '';
    }
  }, [user]);

  const telegramLinked = Boolean(telegramInfo?.telegram_linked);
  const telegramUsername = telegramInfo?.telegram_username || null;
  const deepLink = useMemo(() => {
    const dl = codeInfo?.deep_link;
    if (dl) return dl;
    const code = codeInfo?.code;
    const bot = codeInfo?.bot_username;
    return code && bot ? `https://t.me/${bot}?start=${code}` : '';
  }, [codeInfo]);
  const qrCodeUrl = deepLink
    ? `https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(deepLink)}&size=200x200`
    : '';

  const isTeacher = user?.role === 'teacher';
  const isStudent = user?.role === 'student';

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_AVATAR_SIZE) {
      setErrorMessage('Размер изображения не должен превышать 2 МБ');
      return;
    }

    const reader = new FileReader();
    reader.onloadend = () => {
      setForm((prev) => ({ ...prev, avatar: reader.result || '' }));
      setAvatarPreview(reader.result || '');
      setErrorMessage('');
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveAvatar = () => {
    setForm((prev) => ({ ...prev, avatar: '' }));
    setAvatarPreview('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setSuccessMessage('');
    setErrorMessage('');

    try {
      await updateCurrentUser({
        first_name: form.firstName,
        middle_name: form.middleName,
        last_name: form.lastName,
        avatar: form.avatar || '',
      });
      await refreshUser();
      setSuccessMessage('Профиль обновлен');
    } catch (err) {
      console.error('Не удалось обновить профиль', err);
      setErrorMessage('Не удалось сохранить изменения. Попробуйте ещё раз.');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    setPasswordSaving(true);
    setPasswordSuccess('');
    setPasswordError('');

    // Валидация
    if (!passwordForm.oldPassword || !passwordForm.newPassword || !passwordForm.confirmPassword) {
      setPasswordError('Заполните все поля');
      setPasswordSaving(false);
      return;
    }

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError('Новые пароли не совпадают');
      setPasswordSaving(false);
      return;
    }

    if (passwordForm.newPassword.length < 8) {
      setPasswordError('Пароль должен содержать минимум 8 символов');
      setPasswordSaving(false);
      return;
    }

    try {
      await changePassword(passwordForm.oldPassword, passwordForm.newPassword);
      setPasswordSuccess('Пароль успешно изменён');
      setPasswordForm({ oldPassword: '', newPassword: '', confirmPassword: '' });
      setTimeout(() => {
        setShowPasswordForm(false);
        setPasswordSuccess('');
      }, 2000);
    } catch (err) {
      console.error('Не удалось изменить пароль', err);
      setPasswordError(err.response?.data?.detail || 'Не удалось изменить пароль. Проверьте текущий пароль.');
    } finally {
      setPasswordSaving(false);
    }
  };

  if (!user) {
    return (
      <div className="profile-page">
        <div className="profile-card loading">
          Загрузка профиля...
        </div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="profile-card">
        <header className="profile-header">
          <div>
            <h1>Профиль</h1>
            <p className="profile-subtitle">Обновите свои данные и фотографию</p>
          </div>
        </header>

        {/* Tabs - для всех пользователей */}
        <div className="profile-tabs">
          {tabConfig.map((tab) => (
            <button
              key={tab.key}
              className={`profile-tab ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => handleTabChange(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <form className="profile-content" onSubmit={handleSubmit}>
          <section className="profile-avatar">
            <div className={`avatar-preview ${avatarPreview ? 'with-image' : ''}`}>
              {avatarPreview ? (
                <img src={avatarPreview} alt="Аватар" />
              ) : (
                <span className="avatar-placeholder">Добавьте фото</span>
              )}
            </div>

            <label className="avatar-upload">
              <input type="file" accept="image/*" onChange={handleFileChange} />
              Загрузить фотографию
            </label>

            {avatarPreview && (
              <button type="button" className="avatar-remove" onClick={handleRemoveAvatar}>
                Удалить фото
              </button>
            )}

            <p className="avatar-hint">PNG или JPG до 2 МБ</p>
          </section>

          <section className="profile-form">
            <div className="field-group">
              <label htmlFor="lastName">Фамилия</label>
              <input
                id="lastName"
                type="text"
                value={form.lastName}
                onChange={(event) => setForm((prev) => ({ ...prev, lastName: event.target.value }))}
                placeholder="Иванов"
              />
            </div>

            <div className="field-group">
              <label htmlFor="firstName">Имя</label>
              <input
                id="firstName"
                type="text"
                value={form.firstName}
                onChange={(event) => setForm((prev) => ({ ...prev, firstName: event.target.value }))}
                placeholder="Иван"
              />
            </div>

            <div className="field-group">
              <label htmlFor="middleName">Отчество</label>
              <input
                id="middleName"
                type="text"
                value={form.middleName}
                onChange={(event) => setForm((prev) => ({ ...prev, middleName: event.target.value }))}
                placeholder="Иванович"
              />
            </div>

            <div className="profile-divider"></div>

            <div className="field-group read-only">
              <label>Email</label>
              <div className="stroked-field">{user.email}</div>
            </div>

            {/* Телефон удалён по запросу */}

            {registrationDate && (
              <div className="field-group read-only">
                <label>Дата регистрации</label>
                <div className="stroked-field">{registrationDate}</div>
              </div>
            )}

            <div className="form-actions">
              <button type="submit" className="primary" disabled={saving}>
                {saving ? 'Сохранение...' : 'Сохранить изменения'}
              </button>
            </div>

            {successMessage && <p className="form-message success">{successMessage}</p>}
            {errorMessage && <p className="form-message error">{errorMessage}</p>}
          </section>
        </form>
        )}

        {/* Security Tab */}
        {activeTab === 'security' && user && (
          <div className="profile-content">
            <section className="profile-password">
              <div className="password-header">
                <div>
                  <h3>Безопасность</h3>
                  <p className="profile-subtitle">Управление паролем и настройками безопасности</p>
                </div>
                {!showPasswordForm && (
                  <button 
                    type="button" 
                    className="secondary"
                    onClick={() => setShowPasswordForm(true)}
                  >
                    Изменить пароль
                  </button>
                )}
              </div>

              {showPasswordForm && (
                <div className="password-form">
                  <div className="field-group">
                    <label htmlFor="oldPassword">Текущий пароль</label>
                    <input
                      id="oldPassword"
                      type="password"
                      value={passwordForm.oldPassword}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, oldPassword: e.target.value }))}
                      placeholder="Введите текущий пароль"
                    />
                  </div>

                  <div className="field-group">
                    <label htmlFor="newPassword">Новый пароль</label>
                    <input
                      id="newPassword"
                      type="password"
                      value={passwordForm.newPassword}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, newPassword: e.target.value }))}
                      placeholder="Минимум 8 символов"
                    />
                    <span className="field-hint">Используйте заглавные и строчные буквы, цифры</span>
                  </div>

                  <div className="field-group">
                    <label htmlFor="confirmPassword">Подтвердите новый пароль</label>
                    <input
                      id="confirmPassword"
                      type="password"
                      value={passwordForm.confirmPassword}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, confirmPassword: e.target.value }))}
                      placeholder="Повторите новый пароль"
                    />
                  </div>

                  <div className="form-actions">
                    <button 
                      type="button" 
                      className="primary"
                      onClick={handlePasswordSubmit}
                      disabled={passwordSaving}
                    >
                      {passwordSaving ? 'Сохранение...' : 'Сохранить пароль'}
                    </button>
                    <button 
                      type="button" 
                      className="secondary"
                      onClick={() => {
                        setShowPasswordForm(false);
                        setPasswordForm({ oldPassword: '', newPassword: '', confirmPassword: '' });
                        setPasswordError('');
                        setPasswordSuccess('');
                      }}
                      disabled={passwordSaving}
                    >
                      Отмена
                    </button>
                  </div>

                  {passwordSuccess && <p className="form-message success">{passwordSuccess}</p>}
                  {passwordError && <p className="form-message error">{passwordError}</p>}
                </div>
              )}
            </section>
          </div>
        )}

        {/* Telegram Tab */}
        {activeTab === 'telegram' && user && (
          <div className="profile-content telegram-tab">
            <section className="telegram-section">
              <div className="telegram-header">
                <div>
                  <h3>Telegram бот</h3>
                  <p className="profile-subtitle">
                    Подключите Telegram, чтобы получать уведомления и быстро подтверждать действия
                  </p>
                </div>
                <span className={`telegram-status-pill ${telegramLinked ? 'linked' : 'unlinked'}`}>
                  {telegramLinked ? 'Привязан' : 'Не привязан'}
                </span>
              </div>

              {telegramLoading && !telegramInfo ? (
                <div className="telegram-loading">
                  <div className="spinner" />
                  <p>Проверяем статус...</p>
                </div>
              ) : (
                <div className="telegram-grid">
                  <div className="telegram-card">
                    <h4>Статус подключения</h4>
                    <p className="telegram-status-text">
                      {telegramLinked
                        ? `Аккаунт ${telegramUsername ? '@' + telegramUsername : 'подтверждён'} уже связан.`
                        : 'Telegram ещё не подключен. Сгенерируйте код и отправьте его боту Lectio Space.'}
                    </p>
                    <div className="telegram-actions-row">
                      <button
                        type="button"
                        className="primary"
                        onClick={handleGenerateTelegramCode}
                        disabled={codeLoading}
                      >
                        {codeLoading ? 'Создание кода...' : telegramLinked ? 'Обновить код' : 'Получить код'}
                      </button>
                      {telegramLinked && (
                        <button
                          type="button"
                          className="danger-link"
                          onClick={handleUnlinkTelegram}
                        >
                          Отключить Telegram
                        </button>
                      )}
                    </div>
                    <ul className="telegram-instructions">
                      <li>1. Нажмите «Получить код».</li>
                      <li>2. Откройте Telegram и отправьте код боту.</li>
                      <li>3. Получите подтверждение о привязке.</li>
                    </ul>
                  </div>

                  <div className="telegram-card code-card">
                    <h4>Код подтверждения</h4>
                    {codeInfo ? (
                      <>
                        <div className="code-row">
                          <div>
                            <span className="code-label">Ваш код</span>
                            <div className="code-value">{codeInfo.code}</div>
                          </div>
                          <button
                            type="button"
                            className="ghost"
                            onClick={() => handleCopyValue(codeInfo.code, 'Код Telegram')}
                          >
                            Скопировать
                          </button>
                        </div>
                        {deepLink && (
                          <div className="code-row">
                            <div>
                              <span className="code-label">Ссылка для открытия бота</span>
                              <div className="code-value code-value-small">{deepLink}</div>
                            </div>
                            <div className="code-row-actions">
                              <button
                                type="button"
                                className="ghost"
                                onClick={() => handleCopyValue(deepLink, 'Ссылка')}
                              >
                                Скопировать
                              </button>
                              <button
                                type="button"
                                className="secondary"
                                onClick={() => handleOpenTelegram(deepLink)}
                              >
                                Открыть Telegram
                              </button>
                            </div>
                          </div>
                        )}

                        {qrCodeUrl && (
                          <div className="qr-wrapper">
                            <img src={qrCodeUrl} alt="QR код для открытия бота" />
                            <span>Наведите камеру, чтобы открыть бота</span>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="code-placeholder">
                        <p>Код пока не создан. Нажмите «Получить код», чтобы начать привязку.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {(telegramSuccess || codeMessage || telegramError || codeError) && (
                <div className="telegram-messages">
                  {telegramSuccess && <p className="form-message success">{telegramSuccess}</p>}
                  {codeMessage && <p className="form-message success">{codeMessage}</p>}
                  {telegramError && <p className="form-message error">{telegramError}</p>}
                  {codeError && <p className="form-message error">{codeError}</p>}
                </div>
              )}
            </section>

            <section className="telegram-section notifications-section">
              <div className="telegram-header">
                <div>
                  <h3>Настройки уведомлений</h3>
                  <p className="profile-subtitle">Выберите, какие события будут приходить в Telegram</p>
                </div>
                {notificationSettings && (
                  <span
                    className={`telegram-status-pill ${notificationSettings.telegram_enabled ? 'linked' : 'unlinked'}`}
                  >
                    {notificationSettings.telegram_enabled ? 'Включены' : 'Выключены'}
                  </span>
                )}
              </div>

              {!telegramLinked && (
                <p className="notifications-hint">
                  Чтобы уведомления приходили в Telegram, сначала привяжите Telegram-аккаунт выше.
                </p>
              )}

              {notificationLoading && !notificationSettings ? (
                <div className="telegram-loading">
                  <div className="spinner" />
                  <p>Загружаем настройки...</p>
                </div>
              ) : notificationSettings ? (
                <div className="notifications-unified">
                  {/* Главный переключатель */}
                  <div className="notifications-master-toggle">
                    <label className="notification-toggle-switch">
                      <input
                        type="checkbox"
                        checked={Boolean(notificationSettings.telegram_enabled)}
                        onChange={() => handleToggleNotificationSetting('telegram_enabled')}
                      />
                      <span className="toggle-slider"></span>
                    </label>
                    <div className="toggle-label">
                      <span className="toggle-title">Telegram-уведомления</span>
                      <span className="toggle-desc">
                        {notificationSettings.telegram_enabled 
                          ? 'Уведомления включены' 
                          : 'Все уведомления отключены'}
                      </span>
                    </div>
                  </div>

                  {notificationSettings.telegram_enabled && (
                    <div className="notifications-categories">
                      {/* Занятия */}
                      <div className="notification-category">
                        <div className="category-header">
                          <h4>Занятия</h4>
                        </div>
                        <div className="category-items">
                          <label className="notification-item-compact">
                            <input
                              type="checkbox"
                              checked={Boolean(notificationSettings.notify_lesson_reminders)}
                              onChange={() => handleToggleNotificationSetting('notify_lesson_reminders')}
                            />
                            <span>Напоминания перед уроком</span>
                          </label>
                          {isStudent && (
                            <label className="notification-item-compact">
                              <input
                                type="checkbox"
                                checked={Boolean(notificationSettings.notify_control_point_deadline)}
                                onChange={() => handleToggleNotificationSetting('notify_control_point_deadline')}
                              />
                              <span>Контрольные точки</span>
                            </label>
                          )}
                        </div>
                      </div>

                      {/* Домашние задания */}
                      <div className="notification-category">
                        <div className="category-header">
                          <h4>Домашние задания</h4>
                        </div>
                        <div className="category-items">
                          {isTeacher && (
                            <>
                              <label className="notification-item-compact">
                                <input
                                  type="checkbox"
                                  checked={Boolean(notificationSettings.notify_homework_submitted)}
                                  onChange={() => handleToggleNotificationSetting('notify_homework_submitted')}
                                />
                                <span>Ученик сдал ДЗ</span>
                              </label>
                              <label className="notification-item-compact">
                                <input
                                  type="checkbox"
                                  checked={Boolean(notificationSettings.notify_grading_backlog)}
                                  onChange={() => handleToggleNotificationSetting('notify_grading_backlog')}
                                />
                                <span>Накопились непроверенные работы</span>
                              </label>
                              {notificationSettings.notify_grading_backlog && (
                                <div className="notification-inline-settings">
                                  <div className="inline-setting">
                                    <span>После</span>
                                    <input
                                      type="number"
                                      min="1"
                                      max="50"
                                      value={notificationSettings.grading_backlog_threshold || 5}
                                      onChange={(e) => handleChangeNotificationNumber('grading_backlog_threshold', e.target.value)}
                                    />
                                    <span>работ</span>
                                  </div>
                                  <div className="inline-setting">
                                    <span>ожидающих</span>
                                    <input
                                      type="number"
                                      min="12"
                                      max="168"
                                      value={notificationSettings.grading_backlog_hours || 48}
                                      onChange={(e) => handleChangeNotificationNumber('grading_backlog_hours', e.target.value)}
                                    />
                                    <span>ч</span>
                                  </div>
                                </div>
                              )}
                            </>
                          )}
                          {isStudent && (
                            <>
                              <label className="notification-item-compact">
                                <input
                                  type="checkbox"
                                  checked={Boolean(notificationSettings.notify_new_homework)}
                                  onChange={() => handleToggleNotificationSetting('notify_new_homework')}
                                />
                                <span>Новое домашнее задание</span>
                              </label>
                              <label className="notification-item-compact">
                                <input
                                  type="checkbox"
                                  checked={Boolean(notificationSettings.notify_homework_deadline)}
                                  onChange={() => handleToggleNotificationSetting('notify_homework_deadline')}
                                />
                                <span>Приближается дедлайн</span>
                              </label>
                              <label className="notification-item-compact">
                                <input
                                  type="checkbox"
                                  checked={Boolean(notificationSettings.notify_homework_graded)}
                                  onChange={() => handleToggleNotificationSetting('notify_homework_graded')}
                                />
                                <span>ДЗ проверено</span>
                              </label>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Ученики — только для учителя */}
                      {isTeacher && (
                        <div className="notification-category">
                          <div className="category-header">
                            <h4>Ученики</h4>
                          </div>
                          <div className="category-items">
                            <label className="notification-item-compact">
                              <input
                                type="checkbox"
                                checked={Boolean(notificationSettings.notify_absence_alert)}
                                onChange={() => handleToggleNotificationSetting('notify_absence_alert')}
                              />
                              <span>Серия пропусков</span>
                            </label>
                            {notificationSettings.notify_absence_alert && (
                              <div className="notification-inline-settings">
                                <div className="inline-setting">
                                  <span>После</span>
                                  <input
                                    type="number"
                                    min="0"
                                    max="10"
                                    value={notificationSettings.absence_alert_threshold || 3}
                                    onChange={(e) => handleChangeNotificationNumber('absence_alert_threshold', e.target.value)}
                                  />
                                  <span>пропусков подряд</span>
                                </div>
                              </div>
                            )}

                            <label className="notification-item-compact">
                              <input
                                type="checkbox"
                                checked={Boolean(notificationSettings.notify_performance_drop)}
                                onChange={() => handleToggleNotificationSetting('notify_performance_drop')}
                              />
                              <span>Падение успеваемости</span>
                            </label>
                            {notificationSettings.notify_performance_drop && (
                              <div className="notification-inline-settings">
                                <div className="inline-setting">
                                  <span>Снижение на</span>
                                  <input
                                    type="number"
                                    min="5"
                                    max="50"
                                    value={notificationSettings.performance_drop_percent || 20}
                                    onChange={(e) => handleChangeNotificationNumber('performance_drop_percent', e.target.value)}
                                  />
                                  <span>%</span>
                                </div>
                              </div>
                            )}

                            <label className="notification-item-compact">
                              <input
                                type="checkbox"
                                checked={Boolean(notificationSettings.notify_inactive_student)}
                                onChange={() => handleToggleNotificationSetting('notify_inactive_student')}
                              />
                              <span>Неактивные ученики</span>
                            </label>
                            {notificationSettings.notify_inactive_student && (
                              <div className="notification-inline-settings">
                                <div className="inline-setting">
                                  <span>Без активности</span>
                                  <input
                                    type="number"
                                    min="3"
                                    max="30"
                                    value={notificationSettings.inactive_student_days || 7}
                                    onChange={(e) => handleChangeNotificationNumber('inactive_student_days', e.target.value)}
                                  />
                                  <span>дней</span>
                                </div>
                              </div>
                            )}

                            <label className="notification-item-compact">
                              <input
                                type="checkbox"
                                checked={Boolean(notificationSettings.notify_group_health)}
                                onChange={() => handleToggleNotificationSetting('notify_group_health')}
                              />
                              <span>Аномалии в группе</span>
                            </label>
                          </div>
                        </div>
                      )}

                      {/* Прогресс — только для ученика */}
                      {isStudent && (
                        <div className="notification-category">
                          <div className="category-header">
                            <h4>Мой прогресс</h4>
                          </div>
                          <div className="category-items">
                            <label className="notification-item-compact">
                              <input
                                type="checkbox"
                                checked={Boolean(notificationSettings.notify_student_absence_warning)}
                                onChange={() => handleToggleNotificationSetting('notify_student_absence_warning')}
                              />
                              <span>Предупреждения о пропусках</span>
                            </label>
                            <label className="notification-item-compact">
                              <input
                                type="checkbox"
                                checked={Boolean(notificationSettings.notify_achievement)}
                                onChange={() => handleToggleNotificationSetting('notify_achievement')}
                              />
                              <span>Достижения</span>
                            </label>
                            <label className="notification-item-compact">
                              <input
                                type="checkbox"
                                checked={Boolean(notificationSettings.notify_inactivity_nudge)}
                                onChange={() => handleToggleNotificationSetting('notify_inactivity_nudge')}
                              />
                              <span>Напоминания об активности</span>
                            </label>
                          </div>
                        </div>
                      )}

                      {/* Оплаты — только для учителя */}
                      {isTeacher && (
                        <div className="notification-category">
                          <div className="category-header">
                            <h4>Оплаты и подписка</h4>
                          </div>
                          <div className="category-items">
                            <label className="notification-item-compact">
                              <input
                                type="checkbox"
                                checked={Boolean(notificationSettings.notify_payment_success)}
                                onChange={() => handleToggleNotificationSetting('notify_payment_success')}
                              />
                              <span>Успешная оплата</span>
                            </label>
                            <label className="notification-item-compact">
                              <input
                                type="checkbox"
                                checked={Boolean(notificationSettings.notify_subscription_expiring)}
                                onChange={() => handleToggleNotificationSetting('notify_subscription_expiring')}
                              />
                              <span>Подписка истекает</span>
                            </label>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="code-placeholder">
                  <p>Настройки пока недоступны. Попробуйте обновить страницу.</p>
                </div>
              )}

              <div className="notifications-actions">
                <button
                  type="button"
                  className="primary"
                  onClick={handleSaveNotificationSettings}
                  disabled={notificationSaving || notificationLoading || !notificationSettings}
                >
                  {notificationSaving ? 'Сохранение...' : 'Сохранить настройки'}
                </button>
              </div>

              {(notificationSuccess || notificationError) && (
                <div className="telegram-messages">
                  {notificationSuccess && <p className="form-message success">{notificationSuccess}</p>}
                  {notificationError && <p className="form-message error">{notificationError}</p>}
                </div>
              )}
            </section>
          </div>
        )}

        {/* Subscription Tab */}
        {activeTab === 'subscription' && user.role === 'teacher' && (
          <div className="profile-content subscription-tab">
            <SubscriptionPage embedded />
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfilePage;
