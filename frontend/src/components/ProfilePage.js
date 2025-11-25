import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth';
import { updateCurrentUser, changePassword } from '../apiService';
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
      </div>
    </div>
  );
};

export default ProfilePage;
