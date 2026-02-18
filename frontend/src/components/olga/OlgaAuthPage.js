import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth';
import { Input, Button, Notification } from '../../shared/components';
import PasswordResetModal from '../PasswordResetModal';
import EyeIcon from '../icons/EyeIcon';
import './OlgaAuthPage.css';

/**
 * OlgaAuthPage — кастомная страница авторизации для тенанта «Ольга фарфоровые цветы».
 *
 * Отличия от основной AuthPage:
 * - Нет выбора роли (все — покупатели курсов, роль 'student')
 * - Брендинг Ольги: тёплая золотисто-коричневая тема
 * - Упрощённая форма: вход ↔ регистрация на одном экране
 * - Декоративные элементы: цветочный паттерн, фарфоровая эстетика
 */
const OlgaAuthPage = () => {
  const navigate = useNavigate();
  const { login, register, accessTokenValid } = useAuth();

  // Если уже авторизован — редирект в личный кабинет
  useEffect(() => {
    if (accessTokenValid) {
      navigate('/olga/my', { replace: true });
    }
  }, [accessTokenValid, navigate]);

  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [formData, setFormData] = useState({
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    honeypot: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(() => localStorage.getItem('remember_me') === 'true');
  const [errors, setErrors] = useState({});
  const [showResetModal, setShowResetModal] = useState(false);

  // Уведомления
  const [notification, setNotification] = useState({ isOpen: false, type: 'info', title: '', message: '' });
  const showNotification = (type, title, message) => setNotification({ isOpen: true, type, title, message });
  const closeNotification = () => setNotification(prev => ({ ...prev, isOpen: false }));

  // Защита от ботов
  const [loginAttempts, setLoginAttempts] = useState(0);
  const [blocked, setBlocked] = useState(false);
  const [blockTimer, setBlockTimer] = useState(0);

  useEffect(() => {
    let interval;
    if (blockTimer > 0) {
      interval = setInterval(() => {
        setBlockTimer(prev => {
          if (prev <= 1) { setBlocked(false); setLoginAttempts(0); return 0; }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [blockTimer]);

  // Валидация
  const validateEmail = (email) => {
    if (!email) return 'Email обязателен';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Неверный формат email';
    return '';
  };

  const validatePassword = (password) => {
    if (!password) return 'Пароль обязателен';
    if (password.length < 8) return 'Минимум 8 символов';
    if (!/[A-ZА-Я]/.test(password)) return 'Нужна заглавная буква';
    if (!/[a-zа-я]/.test(password)) return 'Нужна строчная буква';
    if (!/[0-9]/.test(password)) return 'Нужна цифра';
    return '';
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setErrors(prev => ({ ...prev, [field]: '' }));
    setError(null);
  };

  const validateForm = () => {
    const newErrors = {};
    if (formData.honeypot) { setBlocked(true); setBlockTimer(300); return false; }

    const emailErr = validateEmail(formData.email);
    if (emailErr) newErrors.email = emailErr;

    const passErr = validatePassword(formData.password);
    if (passErr) newErrors.password = passErr;

    if (mode === 'register') {
      if (!formData.firstName) newErrors.firstName = 'Имя обязательно';
      if (!formData.lastName) newErrors.lastName = 'Фамилия обязательна';
      if (formData.password !== formData.confirmPassword) newErrors.confirmPassword = 'Пароли не совпадают';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleLogin = async () => {
    setLoading(true);
    try {
      await login({
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
        roleSelection: 'student',
      });
      if (rememberMe) localStorage.setItem('remember_me', 'true');
      else localStorage.removeItem('remember_me');

      showNotification('success', 'Добро пожаловать!', '');
      setTimeout(() => navigate('/olga/my', { replace: true }), 400);
      setLoginAttempts(0);
    } catch (err) {
      const attempts = loginAttempts + 1;
      setLoginAttempts(attempts);
      if (attempts >= 5) { setBlocked(true); setBlockTimer(180); }

      const detail = err.response?.data?.detail || '';
      let msg = 'Проверьте email и пароль';
      if (detail.includes('inactive')) msg = 'Аккаунт деактивирован';
      else if (err.message === 'Network Error') msg = 'Нет подключения к серверу';

      setError(msg);
      showNotification('error', 'Ошибка входа', msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    setLoading(true);
    try {
      await register({
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
        firstName: formData.firstName,
        lastName: formData.lastName,
        phone: formData.phone.trim(),
        role: 'student',
        birthDate: null,
      });
      showNotification('success', 'Регистрация завершена', 'Добро пожаловать!');
      navigate('/olga/my', { replace: true });
    } catch (err) {
      const msg = err.message || 'Не удалось зарегистрироваться';
      setError(msg);
      showNotification('error', 'Ошибка регистрации', msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (blocked) {
      const m = Math.floor(blockTimer / 60);
      const s = blockTimer % 60;
      setError(`Попробуйте через ${m}:${String(s).padStart(2, '0')}`);
      return;
    }
    if (!validateForm()) return;
    if (mode === 'login') await handleLogin();
    else await handleRegister();
  };

  return (
    <div className="olga-auth-page">
      {/* Декоративный фон */}
      <div className="olga-auth-bg">
        <div className="olga-auth-pattern" />
        <div className="olga-auth-glow" />
      </div>

      <div className="olga-auth-card">
        {/* Логотип / заголовок */}
        <div className="olga-auth-header">
          <div className="olga-logo-mark">
            <span className="olga-logo-flower">✿</span>
          </div>
          <h1 className="olga-auth-title">Ольга</h1>
          <p className="olga-auth-tagline">фарфоровые цветы</p>
          <p className="olga-auth-desc">
            {mode === 'login'
              ? 'Войдите, чтобы продолжить обучение'
              : 'Создайте аккаунт для доступа к курсам'}
          </p>
        </div>

        {/* Табы: Вход / Регистрация */}
        <div className="olga-auth-tabs">
          <button
            className={`olga-tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => { setMode('login'); setError(null); setErrors({}); }}
            type="button"
          >
            Вход
          </button>
          <button
            className={`olga-tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => { setMode('register'); setError(null); setErrors({}); }}
            type="button"
          >
            Регистрация
          </button>
        </div>

        <form className="olga-auth-form" onSubmit={handleSubmit}>
          {/* Honeypot */}
          <input
            type="text"
            name="website"
            className="honeypot"
            value={formData.honeypot}
            onChange={(e) => handleChange('honeypot', e.target.value)}
            tabIndex={-1}
            autoComplete="off"
          />

          {mode === 'register' && (
            <div className="olga-form-row">
              <div className="olga-form-group">
                <label htmlFor="olga-firstName">Имя</label>
                <Input
                  id="olga-firstName"
                  type="text"
                  value={formData.firstName}
                  onChange={(e) => handleChange('firstName', e.target.value)}
                  error={errors.firstName}
                  placeholder="Ваше имя"
                  disabled={loading || blocked}
                />
              </div>
              <div className="olga-form-group">
                <label htmlFor="olga-lastName">Фамилия</label>
                <Input
                  id="olga-lastName"
                  type="text"
                  value={formData.lastName}
                  onChange={(e) => handleChange('lastName', e.target.value)}
                  error={errors.lastName}
                  placeholder="Ваша фамилия"
                  disabled={loading || blocked}
                />
              </div>
            </div>
          )}

          <div className="olga-form-group">
            <label htmlFor="olga-email">Email</label>
            <Input
              id="olga-email"
              type="email"
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
              error={errors.email}
              placeholder="your@email.com"
              disabled={loading || blocked}
              autoComplete="email"
            />
          </div>

          {mode === 'register' && (
            <div className="olga-form-group">
              <label htmlFor="olga-phone">Телефон</label>
              <Input
                id="olga-phone"
                type="tel"
                value={formData.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
                placeholder="+7 (999) 123-45-67"
                disabled={loading || blocked}
              />
            </div>
          )}

          <div className="olga-form-group">
            <label htmlFor="olga-password">Пароль</label>
            <div className="olga-password-wrap">
              <Input
                id="olga-password"
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={(e) => handleChange('password', e.target.value)}
                error={errors.password}
                placeholder="Минимум 8 символов"
                disabled={loading || blocked}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                disablePasswordToggle
              />
              <button
                type="button"
                className="olga-toggle-password"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                <EyeIcon open={showPassword} />
              </button>
            </div>
          </div>

          {mode === 'register' && (
            <div className="olga-form-group">
              <label htmlFor="olga-confirmPassword">Подтвердите пароль</label>
              <Input
                id="olga-confirmPassword"
                type={showPassword ? 'text' : 'password'}
                value={formData.confirmPassword}
                onChange={(e) => handleChange('confirmPassword', e.target.value)}
                error={errors.confirmPassword}
                placeholder="Повторите пароль"
                disabled={loading || blocked}
                autoComplete="new-password"
                disablePasswordToggle
              />
            </div>
          )}

          {mode === 'login' && (
            <div className="olga-form-options">
              <label className="olga-checkbox-label">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  disabled={loading || blocked}
                />
                <span>Запомнить меня</span>
              </label>
              <button
                type="button"
                className="olga-link-btn"
                onClick={() => setShowResetModal(true)}
                disabled={loading || blocked}
              >
                Забыли пароль?
              </button>
            </div>
          )}

          {error && (
            <div className="olga-error-msg" role="alert">{error}</div>
          )}

          <Button
            type="submit"
            disabled={loading || blocked}
            className="olga-submit-btn"
          >
            {loading
              ? 'Подождите...'
              : mode === 'login' ? 'Войти' : 'Создать аккаунт'}
          </Button>
        </form>

        {/* Нижний текст */}
        <div className="olga-auth-footer">
          <p className="olga-footer-text">
            Авторские курсы по созданию фарфоровых цветов
          </p>
        </div>
      </div>

      {/* Модалка сброса пароля */}
      <PasswordResetModal
        isOpen={showResetModal}
        onClose={() => setShowResetModal(false)}
      />

      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />
    </div>
  );
};

export default OlgaAuthPage;
