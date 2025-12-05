import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth';
import { updateCurrentUser, changePassword, getSubscription, createSubscriptionPayment, cancelSubscription, getTelegramStatus, generateTelegramCode, unlinkTelegramAccount } from '../apiService';
import './ProfilePage.css';

const MAX_AVATAR_SIZE = 2 * 1024 * 1024;

const ProfilePage = () => {
  const { user, refreshUser } = useAuth();
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

  // Состояние для подписки (только для учителей)
  const [activeTab, setActiveTab] = useState('profile'); // 'profile' | 'security' | 'subscription'
  const [subscription, setSubscription] = useState(null);
  const [subscriptionLoading, setSubscriptionLoading] = useState(false);
  const [subscriptionError, setSubscriptionError] = useState('');

  const tabConfig = useMemo(() => {
    if (!user) {
      return [{ key: 'profile', label: 'Профиль' }];
    }
    const items = [
      { key: 'profile', label: 'Профиль' },
      { key: 'security', label: '🔒 Безопасность' },
    ];
    if (user.role === 'teacher') {
      items.push({ key: 'subscription', label: 'Моя подписка' });
    }
    return items;
  }, [user]);

  useEffect(() => {
    if (!user) return;
    setForm({
      firstName: user.first_name || '',
      middleName: user.middle_name || '',
      lastName: user.last_name || '',
      avatar: user.avatar || '',
    });
    setAvatarPreview(user.avatar || '');

    // Загрузка подписки для учителей
    if (user.role === 'teacher' && activeTab === 'subscription') {
      loadSubscription();
    }
  }, [user, activeTab]);

  const loadSubscription = async () => {
    setSubscriptionLoading(true);
    setSubscriptionError('');
    try {
      const { data } = await getSubscription();
      setSubscription(data);
    } catch (err) {
      console.error('Failed to load subscription:', err);
      setSubscriptionError('Не удалось загрузить данные подписки');
    } finally {
      setSubscriptionLoading(false);
    }
  };

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

  useEffect(() => {
    if (activeTab === 'security') {
      fetchTelegramStatus();
    }
  }, [activeTab, fetchTelegramStatus]);

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
    if (!window.confirm('Вы уверены, что хотите отвязать Telegram?')) {
      return;
    }
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

  const formatExpiration = (isoDate) => {
    if (!isoDate) {
      return '';
    }
    try {
      return new Date(isoDate).toLocaleString('ru-RU', {
        day: '2-digit',
        month: 'long',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (err) {
      console.error('Failed to format date', err);
      return isoDate;
    }
  };

  const handleCreatePayment = async (planType) => {
    try {
      const { data } = await createSubscriptionPayment(planType);
      setSubscription(data.subscription);
      const paymentUrl = data.payment?.payment_url;
      if (paymentUrl) {
        window.location.href = paymentUrl;
      }
    } catch (err) {
      console.error('Failed to create payment:', err);
      alert('Не удалось создать платёж. Попробуйте позже.');
    }
  };

  const handleCancelSubscription = async () => {
    if (!window.confirm('Отменить автопродление подписки? Доступ сохранится до конца оплаченного периода.')) {
      return;
    }
    try {
      const { data } = await cancelSubscription();
      setSubscription(data);
      alert('Автопродление отменено');
    } catch (err) {
      console.error('Failed to cancel subscription:', err);
      alert('Не удалось отменить подписку');
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

        {/* Tabs - только для учителей показываем вкладку подписки */}
        {user.role === 'teacher' && (
          <div className="profile-tabs">
            <button
              className={`profile-tab ${activeTab === 'profile' ? 'active' : ''}`}
              onClick={() => setActiveTab('profile')}
            >
              Профиль
            </button>
            <button
              className={`profile-tab ${activeTab === 'security' ? 'active' : ''}`}
              onClick={() => setActiveTab('security')}
            >
              🔒 Безопасность
            </button>
            <button
              className={`profile-tab ${activeTab === 'subscription' ? 'active' : ''}`}
              onClick={() => setActiveTab('subscription')}
            >
              Моя подписка
            </button>
          </div>
        )}

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
          
          {/* Секция смены пароля */}
          <section className="profile-password">
            <div className="profile-divider"></div>
            
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
        </form>
        )}

        {/* Security Tab */}
        {activeTab === 'security' && user.role === 'teacher' && (
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

              {telegramLoading ? (
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
                        : 'Telegram ещё не подключен. Сгенерируйте код и отправьте его боту Easy Teaching.'}
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
          </div>
        )}

        {/* Subscription Tab */}
        {activeTab === 'subscription' && user.role === 'teacher' && (
          <div className="profile-content subscription-tab">
            {subscriptionLoading ? (
              <div className="subscription-loading">
                <div className="spinner"></div>
                <p>Загрузка данных подписки...</p>
              </div>
            ) : subscriptionError ? (
              <div className="subscription-error">
                <span className="error-icon"></span>
                <p>{subscriptionError}</p>
                <button onClick={loadSubscription} className="retry-btn">
                  Повторить
                </button>
              </div>
            ) : subscription ? (
              <div className="subscription-content">
                <section className="subscription-info-section">
                  <h3>Текущая подписка</h3>
                  
                  <div className="subscription-card">
                    <div className="subscription-plan-badge">
                      {subscription.plan === 'trial' && '🎁 Пробная'}
                      {subscription.plan === 'monthly' && 'Месячная'}
                      {subscription.plan === 'yearly' && '🎯 Годовая'}
                    </div>
                    
                    <div className="subscription-status">
                      {subscription.status === 'active' && (
                        <span className="status-badge active">Активна</span>
                      )}
                      {subscription.status === 'pending' && (
                        <span className="status-badge pending">Ожидает оплаты</span>
                      )}
                      {subscription.status === 'cancelled' && (
                        <span className="status-badge cancelled">Отменена</span>
                      )}
                      {subscription.status === 'expired' && (
                        <span className="status-badge expired">⏱️ Истекла</span>
                      )}
                    </div>

                    <div className="subscription-details">
                      <div className="detail-row">
                        <span className="label">Начало:</span>
                        <span className="value">
                          {new Date(subscription.started_at).toLocaleDateString('ru-RU')}
                        </span>
                      </div>
                      <div className="detail-row">
                        <span className="label">Истекает:</span>
                        <span className="value">
                          {new Date(subscription.expires_at).toLocaleDateString('ru-RU')}
                        </span>
                      </div>
                      <div className="detail-row">
                        <span className="label">Автопродление:</span>
                        <span className="value">
                          {subscription.auto_renew ? 'Включено' : 'Выключено'}
                        </span>
                      </div>
                      <div className="detail-row">
                        <span className="label">Всего оплачено:</span>
                        <span className="value">
                          {subscription.total_paid} {subscription.currency || 'RUB'}
                        </span>
                      </div>
                    </div>
                  </div>
                </section>

                {subscription.status === 'active' && subscription.plan === 'trial' && (
                  <section className="subscription-upgrade-section">
                    <h3>Расширенные возможности</h3>
                    <p className="section-subtitle">
                      Выберите план для продолжения работы после пробного периода
                    </p>
                    
                    <div className="pricing-cards">
                      <div className="pricing-card">
                        <div className="pricing-header">
                          <h4>Месячная подписка</h4>
                          <div className="pricing-amount">990 ₽</div>
                          <div className="pricing-period">в месяц</div>
                        </div>
                        <ul className="pricing-features">
                          <li>Без ограничений по студентам</li>
                          <li>Zoom интеграция</li>
                          <li>Конструктор ДЗ</li>
                          <li>Материалы уроков</li>
                        </ul>
                        <button
                          onClick={() => handleCreatePayment('monthly')}
                          className="pricing-btn btn-primary"
                        >
                          Оплатить месяц
                        </button>
                      </div>

                      <div className="pricing-card featured">
                        <div className="pricing-badge">Выгодно</div>
                        <div className="pricing-header">
                          <h4>Годовая подписка</h4>
                          <div className="pricing-amount">9 900 ₽</div>
                          <div className="pricing-period">в год</div>
                          <div className="pricing-save">Экономия 990 ₽</div>
                        </div>
                        <ul className="pricing-features">
                          <li>Все возможности месячной</li>
                          <li>2 месяца в подарок</li>
                          <li>Приоритетная поддержка</li>
                          <li>Ранний доступ к новым функциям</li>
                        </ul>
                        <button
                          onClick={() => handleCreatePayment('yearly')}
                          className="pricing-btn btn-featured"
                        >
                          Оплатить год
                        </button>
                      </div>
                    </div>
                  </section>
                )}

                {subscription.status === 'active' && subscription.auto_renew && (
                  <section className="subscription-actions-section">
                    <button
                      onClick={handleCancelSubscription}
                      className="cancel-subscription-btn"
                    >
                      Отменить автопродление
                    </button>
                    <p className="cancel-hint">
                      Доступ сохранится до {new Date(subscription.expires_at).toLocaleDateString('ru-RU')}
                    </p>
                  </section>
                )}

                {subscription.payments && subscription.payments.length > 0 && (
                  <section className="subscription-payments-section">
                    <h3>История платежей</h3>
                    <div className="payments-list">
                      {subscription.payments.map(payment => (
                        <div key={payment.id} className="payment-row">
                          <div className="payment-info">
                            <span className="payment-amount">
                              {payment.amount} {payment.currency || 'RUB'}
                            </span>
                            <span className="payment-date">
                              {new Date(payment.created_at).toLocaleDateString('ru-RU')}
                            </span>
                          </div>
                          <span className={`payment-status status-${payment.status}`}>
                            {payment.status === 'succeeded' && 'Успешно'}
                            {payment.status === 'pending' && 'Ожидание'}
                            {payment.status === 'failed' && 'Ошибка'}
                            {payment.status === 'refunded' && 'Возврат'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </div>
            ) : (
              <div className="subscription-empty">
                <span className="empty-icon">💳</span>
                <p>Подписка не найдена</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfilePage;
