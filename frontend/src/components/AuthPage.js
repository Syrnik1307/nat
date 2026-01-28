import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { clearTokens } from '../apiService';
import { Input, Button, Notification } from '../shared/components';
import { TELEGRAM_RESET_DEEPLINK } from '../constants';
import SupportWidget from './SupportWidget';
import './AuthPage.css';
import EyeIcon from './icons/EyeIcon';
// import { useRecaptcha } from '../hooks/useRecaptcha'; // отключено

/**
 * Единая страница аутентификации (вход/регистрация)
 * 
 * Функционал:
 * 1. Выбор роли: Ученик или Преподаватель (Админ входит как преподаватель)
 * 2. Форма входа с email/телефон + пароль
 * 3. Переключение на регистрацию
 * 4. Восстановление пароля через Telegram
 * 
 * Защита от ботов:
 * - Rate limiting (макс. 5 попыток в минуту)
 * - CAPTCHA после 3 неудачных попыток
 * - Блокировка IP при подозрительной активности
 * - Honeypot поле (скрытое для людей, видимое для ботов)
 */

const AuthPage = () => {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  // const { executeRecaptcha } = useRecaptcha(); // отключено

  const isDev = process.env.NODE_ENV !== 'production';
  
  useEffect(() => {
    // Если токены есть — пользователь уже залогинен, редиректим на home
    try {
      const hasTokens = !!(localStorage.getItem('tp_access_token') && localStorage.getItem('tp_refresh_token'));
      if (hasTokens) {
        navigate('/home-new', { replace: true });
        return undefined;
      }
      // Очищаем устаревшие ключи (совместимость со старым кодом)
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } catch (_) {}
    
    return undefined;
  }, [navigate]);
  
  // === ШАГИ АУТЕНТИФИКАЦИИ ===
  // 'role' = Выбор роли
  // 1 = Форма входа/регистрации
  const [step, setStep] = useState('role');
  const [role, setRole] = useState(null); // 'student' | 'teacher'
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  
  // === ДАННЫЕ ФОРМЫ ===
  const [formData, setFormData] = useState({
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    telegramUsername: '', // Telegram для восстановления пароля
    honeypot: '', // Защита от ботов
    notificationConsent: false, // Согласие на уведомления в Telegram
  });
  
  // === UI СОСТОЯНИЯ ===
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(() => {
    // По умолчанию включено, если явно не отключено
    const stored = localStorage.getItem('remember_me');
    return stored === null ? true : stored === 'true';
  });
  
  // === УВЕДОМЛЕНИЯ ===
  const [notification, setNotification] = useState({
    isOpen: false,
    type: 'info',
    title: '',
    message: '',
  });
  
  // === ЗАЩИТА ОТ БОТОВ ===
  const [loginAttempts, setLoginAttempts] = useState(0);
  const [showCaptcha, setShowCaptcha] = useState(false);
  const [captchaVerified, setCaptchaVerified] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [blockTimer, setBlockTimer] = useState(0);
  
  // === ВАЛИДАЦИЯ ===
  const [errors, setErrors] = useState({});
  
  // === ФУНКЦИЯ ПОКАЗА УВЕДОМЛЕНИЙ ===
  const showNotification = (type, title, message) => {
    setNotification({
      isOpen: true,
      type,
      title,
      message,
    });
  };
  
  const closeNotification = () => {
    setNotification({
      ...notification,
      isOpen: false,
    });
  };

  // === ТАЙМЕР БЛОКИРОВКИ ===
  useEffect(() => {
    let interval;
    if (blockTimer > 0) {
      interval = setInterval(() => {
        setBlockTimer(prev => {
          if (prev <= 1) {
            setBlocked(false);
            setLoginAttempts(0);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [blockTimer]);

  // === ВАЛИДАЦИЯ EMAIL ===
  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) return 'Email обязателен';
    if (!emailRegex.test(email)) return 'Неверный формат email';
    return '';
  };

  // === ВАЛИДАЦИЯ ТЕЛЕФОНА ===
  const validatePhone = (phone) => {
    // Телефон необязателен
    if (!phone) return '';
    
    // Поддержка СНГ: +7 (РФ/Казахстан), +380 (Украина), +375 (Беларусь), 
    // +998 (Узбекистан), +996 (Кыргызстан), +992 (Таджикистан), +994 (Азербайджан),
    // +995 (Грузия), +374 (Армения), +373 (Молдова), +993 (Туркменистан)
    const cleaned = phone.replace(/[\s\-\(\)]/g, '');
    const phoneRegex = /^(\+7|8|7|\+380|\+375|\+998|\+996|\+992|\+994|\+995|\+374|\+373|\+993)[0-9]{9,10}$/;
    if (!phoneRegex.test(cleaned)) return 'Неверный формат телефона';
    return '';
  };

  // === ВАЛИДАЦИЯ ПАРОЛЯ ===
  const validatePassword = (password) => {
    if (!password) return 'Пароль обязателен';
    if (password.length < 8) return 'Минимум 8 символов';
    if (!/[A-ZА-Я]/.test(password)) return 'Нужна хотя бы одна заглавная буква';
    if (!/[a-zа-я]/.test(password)) return 'Нужна хотя бы одна строчная буква';
    if (!/[0-9]/.test(password)) return 'Нужна хотя бы одна цифра';
    return '';
  };

  // === ОБРАБОТКА ИЗМЕНЕНИЙ ===
  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setErrors(prev => ({ ...prev, [field]: '' }));
    setError(null);
  };

  // === ВАЛИДАЦИЯ ФОРМЫ ===
  const validateForm = () => {
    const newErrors = {};

    if (isDev) {
      // eslint-disable-next-line no-console
      console.log('[AuthPage] validateForm', { mode });
    }
    
    // Проверка honeypot (должно быть пустым)
    if (formData.honeypot) {
      if (isDev) {
        // eslint-disable-next-line no-console
        console.log('[AuthPage] honeypot triggered');
      }
      setBlocked(true);
      setBlockTimer(300); // 5 минут блокировки
      return false;
    }
    
    const emailError = validateEmail(formData.email);
    if (emailError) {
      if (isDev) {
        // eslint-disable-next-line no-console
        console.log('[AuthPage] email error:', emailError);
      }
      newErrors.email = emailError;
    }
    
    const passwordError = validatePassword(formData.password);
    if (passwordError) {
      if (isDev) {
        // eslint-disable-next-line no-console
        console.log('[AuthPage] password error:', passwordError);
      }
      newErrors.password = passwordError;
    }
    
    if (mode === 'register') {
      if (isDev) {
        // eslint-disable-next-line no-console
        console.log('[AuthPage] register validation');
      }
      
      if (!formData.firstName) {
        if (isDev) {
          // eslint-disable-next-line no-console
          console.log('[AuthPage] firstName empty');
        }
        newErrors.firstName = 'Имя обязательно';
      }
      if (!formData.lastName) {
        if (isDev) {
          // eslint-disable-next-line no-console
          console.log('[AuthPage] lastName empty');
        }
        newErrors.lastName = 'Фамилия обязательна';
      }
      
      const phoneError = validatePhone(formData.phone);
      if (phoneError) {
        if (isDev) {
          // eslint-disable-next-line no-console
          console.log('[AuthPage] phone error:', phoneError);
        }
        newErrors.phone = phoneError;
      }
      
      if (formData.password !== formData.confirmPassword) {
        if (isDev) {
          // eslint-disable-next-line no-console
          console.log('[AuthPage] passwords mismatch');
        }
        newErrors.confirmPassword = 'Пароли не совпадают';
      }
    }

    if (isDev) {
      // eslint-disable-next-line no-console
      console.log('[AuthPage] validation errors:', Object.keys(newErrors));
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // === ВХОД ===
  const handleLogin = async () => {
    setError(null);
    setLoading(true);
    
    try {
      // Перед стартом логина принудительно очищаем старые токены
      clearTokens();
      // Логирование для диагностики мобильных проблем
      if (isDev) {
        // eslint-disable-next-line no-console
        console.log('[AuthPage] login attempt', {
          email: formData.email?.trim().toLowerCase(),
          passwordLength: formData.password?.length,
          passwordHasSpaces: formData.password?.includes(' '),
          role,
          userAgent: navigator.userAgent,
        });
      }
      
      // reCAPTCHA отключена
      const recaptchaToken = null;

      const resolvedRole = await login({
        email: formData.email?.trim().toLowerCase(),
        password: formData.password?.trim(),
        roleSelection: role,
        rememberMe: rememberMe,
      });
      // Используем только роль из JWT токена (resolvedRole)
      const nextRole = resolvedRole || 'teacher';
      const roleRedirects = {
        teacher: '/home-new',
        student: '/student',
        admin: '/admin-home',
      };
      // Токены сохраняются в localStorage и автоматически истекают через 12 часов
      // Флаг remember_me больше не используется — всегда "запоминаем"
      
      // Показываем успешное уведомление
      showNotification('success', 'Вход выполнен', `Добро пожаловать, ${formData.email}!`);

      // Редирект сразу: профиль догрузится в фоне, а искусственная задержка ощущается как "долгий логин".
      navigate(roleRedirects[nextRole] || '/');
      
      // Сброс попыток при успешном входе
      setLoginAttempts(0);
      setShowCaptcha(false);
    } catch (err) {
      // Логирование ошибки для диагностики
      if (isDev) {
        // eslint-disable-next-line no-console
        console.error('[AuthPage] login error:', {
          status: err.response?.status,
          detail: err.response?.data?.detail,
          message: err.message,
        });
      }
      
      // Увеличиваем счетчик попыток
      const newAttempts = loginAttempts + 1;
      setLoginAttempts(newAttempts);
      
      // Определяем тип ошибки и формируем сообщение
      const errorDetail = err.response?.data?.detail || '';
      let errorTitle = 'Ошибка входа';
      let errorMessage = errorDetail || 'Проверьте правильность введённых данных';
      
      // Проверяем различные типы ошибок
      if (err.response?.status === 502) {
        errorTitle = 'Сбой сервера (502)';
        errorMessage = 'Временная ошибка шлюза. Попробуйте ещё раз через минуту.';
      } else if (err.response?.status === 500) {
        errorTitle = 'Внутренняя ошибка (500)';
        errorMessage = 'На сервере произошла ошибка. Сообщите поддержке, если повторяется.';
      } else if (err.response?.status === 401) {
        // Используем сообщение от бэкенда (например "Неверный email или пароль")
        errorTitle = 'Ошибка авторизации';
        errorMessage = errorDetail || 'Неверный email или пароль';
      } else if (errorDetail.includes('inactive') || errorDetail.includes('деактивирован')) {
        errorTitle = 'Аккаунт неактивен';
        errorMessage = errorDetail;
      } else if (errorDetail.includes('блокирован') || errorDetail.includes('попыток')) {
        errorTitle = 'Доступ ограничен';
        errorMessage = errorDetail;
      } else if (err.message === 'Network Error' || !err.response) {
        errorTitle = 'Ошибка подключения';
        errorMessage = 'Не удалось подключиться к серверу. Проверьте интернет-соединение.';
      }
      
      // Показываем CAPTCHA после 3 попыток
      if (newAttempts >= 3) {
        setShowCaptcha(true);
        errorTitle = 'Требуется проверка';
        errorMessage = 'Слишком много неудачных попыток. Пожалуйста, подтвердите, что вы не робот.';
      }
      
      // Блокируем после 5 попыток
      if (newAttempts >= 5) {
        setBlocked(true);
        setBlockTimer(180); // 3 минуты блокировки
        errorTitle = 'Доступ заблокирован';
        errorMessage = 'Превышено количество попыток входа. Попробуйте через 3 минуты.';
      }
      
      // Устанавливаем текст ошибки и показываем уведомление
      setError(errorMessage);
      showNotification('error', errorTitle, errorMessage);
      
      // Анимация ошибки
      const form = document.querySelector('.auth-form');
      if (form) {
        form.style.animation = 'shake 0.5s';
        setTimeout(() => form.style.animation = '', 500);
      }
    } finally {
      setLoading(false);
    }
  };

  // === РЕГИСТРАЦИЯ ===
  const handleRegister = async () => {
    setError(null);
    setLoading(true);
    try {
      console.log('🚀 Централизованная регистрация через auth.register()', {
        email: formData.email,
        firstName: formData.firstName,
        lastName: formData.lastName,
        phone: formData.phone,
        role,
        rememberMe,
        notificationConsent: formData.notificationConsent
      });
      const resolvedRole = await register({
        email: formData.email.trim().toLowerCase(),
        password: formData.password.trim(),
        firstName: formData.firstName.trim(),
        lastName: formData.lastName.trim(),
        phone: formData.phone.trim(),
        role,
        birthDate: null,
        rememberMe,
        notificationConsent: formData.notificationConsent,
      });
      console.log('✅ Регистрация завершена. Роль из токена:', resolvedRole);
      showNotification('success', 'Регистрация выполнена', 'Добро пожаловать!');

      // Асинхронно отправим письмо верификации (не блокируем редирект)
      (async () => {
        try {
          const resp = await fetch('/accounts/api/email/send-verification/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: formData.email.trim().toLowerCase() })
          });
          const vData = await resp.json();
          if (resp.ok) {
            console.log('📧 Код верификации отправлен:', vData);
          } else {
            console.warn('⚠️ Не удалось отправить код верификации:', vData);
          }
        } catch (mailErr) {
          console.warn('⚠️ Ошибка фоновой отправки письма верификации:', mailErr);
        }
      })();

      // После регистрации перенаправляем в зависимости от роли
      const roleRedirects = {
        teacher: '/home-new',
        admin: '/admin-home',
        student: '/student',
      };
      const nextPath = roleRedirects[resolvedRole] || '/';
      console.log('✅ Регистрация успешна, перенаправление на', nextPath);
      navigate(nextPath, { replace: true });
    } catch (err) {
      console.error('❌ Ошибка регистрации:', err);
      showNotification('error', 'Ошибка регистрации', err.message || 'Не удалось зарегистрироваться');
      setError(err.message || 'Ошибка регистрации');
    } finally {
      setLoading(false);
    }
  };

  // === ОТПРАВКА ФОРМЫ ===
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    console.log('🚀🚀🚀 handleSubmit вызван в AuthPage! 🚀🚀🚀');
    console.log('  - mode:', mode);
    console.log('  - formData:', formData);
    console.log('  - blocked:', blocked);
    console.log('  - showCaptcha:', showCaptcha);
    console.log('  - captchaVerified:', captchaVerified);
    
    // Проверка блокировки
    if (blocked) {
      const minutes = Math.floor(blockTimer / 60);
      const seconds = blockTimer % 60;
      const errorMsg = `Доступ заблокирован. Попробуйте через ${minutes}:${seconds.toString().padStart(2, '0')}`;
      setError(errorMsg);
      showNotification('error', 'Доступ заблокирован', errorMsg);
      return;
    }
    
    // Проверка CAPTCHA
    if (showCaptcha && !captchaVerified) {
      setError('Пройдите проверку CAPTCHA');
      showNotification('warning', 'Требуется проверка', 'Пожалуйста, пройдите проверку CAPTCHA');
      return;
    }
    
    // Валидация
    console.log('  - Вызов validateForm()...');
    if (!validateForm()) {
      showNotification('error', 'Ошибка заполнения формы', 'Пожалуйста, проверьте правильность заполнения всех полей');
      return;
    }
    
    if (mode === 'login') {
      console.log('  - Режим: ВХОД');
      await handleLogin();
    } else {
      console.log('  - Режим: РЕГИСТРАЦИЯ');
      await handleRegister();
    }
  };

  const openTelegramResetFlow = () => {
    if (loading || blocked) {
      return;
    }

    const newTab = window.open(TELEGRAM_RESET_DEEPLINK, '_blank');
    if (!newTab) {
      window.location.href = TELEGRAM_RESET_DEEPLINK;
    }

    showNotification(
      'info',
      'Откройте Telegram',
      'Мы открыли бота Lectio Space. Нажмите Start и выполните команду /reset.'
    );
  };

  // === ВЫБОР РОЛИ ===
  const selectRole = (selectedRole) => {
    // Всегда начинаем со входа после выбора роли
    setMode('login');
    setRole(selectedRole);
    setStep(1);
  };

  // === ПЕРЕКЛЮЧЕНИЕ РЕЖИМА ===
  const toggleMode = () => {
    setMode(mode === 'login' ? 'register' : 'login');
    setError(null);
    setErrors({});
  };

  // === ШАГ 1: ВЫБОР РОЛИ ===
  if (step === 'role') {
    return (
      <>
        <div className="auth-container">
          <div className="auth-pattern" aria-hidden="true" />
          <div className="auth-brand">
            <h1>
              <span className="brand-primary">Lectio</span>
              <span className="brand-secondary"> Space</span>
            </h1>
          </div>
          
          <div className="auth-content">
            <div className="auth-header">
              <h1 className="auth-title">Добро пожаловать!</h1>
              <p className="auth-subtitle">Выберите вашу роль для входа</p>
            </div>

            <div className="role-selection">
              <div 
                className="role-card"
                onClick={() => selectRole('student')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && selectRole('student')}
              >
                <div className="role-icon">👨‍🎓</div>
                <h3 className="role-title">Ученик</h3>
                <p className="role-description">
                  Доступ к урокам и заданиям
                </p>
              </div>

              <div 
                className="role-card"
                onClick={() => selectRole('teacher')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && selectRole('teacher')}
              >
                <div className="role-icon">👨‍🏫</div>
                <h3 className="role-title">Учитель</h3>
                <p className="role-description">
                  Управление группами и уроками
                </p>
              </div>
            </div>
          </div>
        </div>
        <SupportWidget />
      </>
    );
  }

  // === РЕНДЕР: ШАГ 1 - ФОРМА ВХОДА/РЕГИСТРАЦИИ ===
  if (step === 1) {
    return (
      <div className="auth-container">
        <div className="auth-pattern" aria-hidden="true" />
        <div className="auth-content">
          <div className="auth-header">
            <h1 className="auth-title">
              {mode === 'login' ? 'Вход' : 'Регистрация'}
            </h1>
            <p className="auth-subtitle">
              {mode === 'login' 
                ? `как ${role === 'student' ? 'ученик' : 'учитель'}`
                : `как ${role === 'student' ? 'ученик' : 'учитель'}`
              }
            </p>
          </div>

          <div className="auth-backlink">
            <button 
              className="back-button"
              onClick={() => { setStep('role'); setMode('login'); }}
              aria-label="Вернуться к выбору роли"
              type="button"
            >
              ← Назад
            </button>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            {/* Honeypot для защиты от ботов */}
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
              <>
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="firstName">Имя *</label>
                    <Input
                      id="firstName"
                      type="text"
                      value={formData.firstName}
                      onChange={(e) => handleChange('firstName', e.target.value)}
                      error={errors.firstName}
                      placeholder="Введите имя"
                      disabled={loading || blocked}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="lastName">Фамилия *</label>
                    <Input
                      id="lastName"
                      type="text"
                      value={formData.lastName}
                      onChange={(e) => handleChange('lastName', e.target.value)}
                      error={errors.lastName}
                      placeholder="Введите фамилию"
                      disabled={loading || blocked}
                    />
                  </div>
                </div>
              </>
            )}

            <div className="form-group">
              <label htmlFor="email">Email *</label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => handleChange('email', e.target.value)}
                error={errors.email}
                placeholder="example@mail.com"
                disabled={loading || blocked}
                autoComplete="email"
              />
            </div>

            {mode === 'register' && (
              <div className="form-group">
                <label htmlFor="phone">Номер телефона *</label>
                <Input
                  id="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => handleChange('phone', e.target.value)}
                  error={errors.phone}
                  placeholder="+7 (999) 123-45-67"
                  disabled={loading || blocked}
                />
              </div>
            )}

            <div className="form-group">
              <label htmlFor="password">Пароль *</label>
              <div className="password-input">
                <Input
                  id="password"
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
                  className="toggle-password"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                >
                  <EyeIcon open={showPassword} />
                </button>
              </div>
            </div>

            {mode === 'register' && (
              <div className="form-group">
                <label htmlFor="confirmPassword">Подтвердите пароль *</label>
                <Input
                  id="confirmPassword"
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
              <div className="form-options">
                <label className="checkbox-label">
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
                  className="link-button"
                  onClick={openTelegramResetFlow}
                  disabled={loading || blocked}
                >
                  Забыли пароль?
                </button>
              </div>
            )}

            {mode === 'register' && (
              <div className="form-options register-options">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    disabled={loading || blocked}
                  />
                  <span>Запомнить меня</span>
                </label>
                <label className="checkbox-label notification-consent">
                  <input
                    type="checkbox"
                    checked={formData.notificationConsent}
                    onChange={(e) => handleChange('notificationConsent', e.target.checked)}
                    disabled={loading || blocked}
                  />
                  <span>Я согласен получать уведомления в Telegram о занятиях и домашних заданиях</span>
                </label>
              </div>
            )}

            {/* CAPTCHA */}
            {showCaptcha && (
              <div className="captcha-container">
                <div className="captcha-box">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={captchaVerified}
                      onChange={(e) => setCaptchaVerified(e.target.checked)}
                      disabled={loading || blocked}
                    />
                    <span>Я не робот ✓</span>
                  </label>
                </div>
                <p className="captcha-note">
                  Для безопасности подтвердите, что вы человек
                </p>
              </div>
            )}

            {error && (
              <div className="error-message" role="alert">
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={loading || blocked}
              className="submit-button"
            >
              {loading ? 'Загрузка...' : (mode === 'login' ? 'Войти' : 'Зарегистрироваться')}
            </Button>

            <div className="auth-switch">
              <p>
                {mode === 'login' ? 'Нет аккаунта? ' : 'Уже есть аккаунт? '}
                <button
                  type="button"
                  className="link-button"
                  onClick={toggleMode}
                  disabled={loading || blocked}
                >
                  {mode === 'login' ? 'Создать' : 'Войти'}
                </button>
              </p>
            </div>

            {/* Кнопка убрана - редирект происходит автоматически */}
          </form>

          
        </div>
        
        <SupportWidget />
      </div>
    );
  }

  return (
    <>
      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />
      <SupportWidget />
    </>
  );
};

export default AuthPage;
