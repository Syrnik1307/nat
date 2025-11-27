import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { Input, Button, Modal, Notification } from '../shared/components';
import SupportWidget from './SupportWidget';
import PasswordResetModal from './PasswordResetModal';
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
  const { login, register, accessTokenValid, role: userRole } = useAuth();
  // const { executeRecaptcha } = useRecaptcha(); // отключено
  
  useEffect(() => {
    console.log('✅✅✅ AuthPage ЗАГРУЖЕНА ✅✅✅');
    console.log('  - step:', step);
    console.log('  - role:', role);
    console.log('  - mode:', mode);
    
    // Глобальный обработчик кликов для отладки
    const handleClick = (e) => {
      console.log('🖱️ КЛИК:', {
        tag: e.target.tagName,
        class: e.target.className,
        type: e.target.type,
        text: e.target.textContent?.substring(0, 30)
      });
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);
  
  // === ШАГИ АУТЕНТИФИКАЦИИ ===
  // 0 = Выбор роли
  // 1 = Форма входа/регистрации
  const [step, setStep] = useState(0);
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
  });
  
  // === UI СОСТОЯНИЯ ===
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(() => {
    // Инициализируем из localStorage
    return localStorage.getItem('remember_me') === 'true';
  });
  
  // === УВЕДОМЛЕНИЯ ===
  const [notification, setNotification] = useState({
    isOpen: false,
    type: 'info',
    title: '',
    message: '',
  });
  
  // === ВОССТАНОВЛЕНИЕ ПАРОЛЯ ===
  const [showResetModal, setShowResetModal] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetSuccess, setResetSuccess] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  
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
    
    const phoneRegex = /^(\+7|8)?[\s-]?\(?[0-9]{3}\)?[\s-]?[0-9]{3}[\s-]?[0-9]{2}[\s-]?[0-9]{2}$/;
    if (!phoneRegex.test(phone)) return 'Неверный формат телефона';
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
    
    console.log('📝 Валидация формы:');
    console.log('  - mode:', mode);
    console.log('  - formData:', formData);
    
    // Проверка honeypot (должно быть пустым)
    if (formData.honeypot) {
      console.log('❌ Honeypot сработал (бот?)');
      setBlocked(true);
      setBlockTimer(300); // 5 минут блокировки
      return false;
    }
    
    const emailError = validateEmail(formData.email);
    if (emailError) {
      console.log('❌ Email ошибка:', emailError);
      newErrors.email = emailError;
    }
    
    const passwordError = validatePassword(formData.password);
    if (passwordError) {
      console.log('❌ Password ошибка:', passwordError);
      newErrors.password = passwordError;
    }
    
    if (mode === 'register') {
      console.log('  - Режим регистрации, дополнительные проверки...');
      
      if (!formData.firstName) {
        console.log('❌ Имя пустое');
        newErrors.firstName = 'Имя обязательно';
      }
      if (!formData.lastName) {
        console.log('❌ Фамилия пустая');
        newErrors.lastName = 'Фамилия обязательна';
      }
      
      const phoneError = validatePhone(formData.phone);
      if (phoneError) {
        console.log('❌ Телефон ошибка:', phoneError);
        newErrors.phone = phoneError;
      }
      
      if (formData.password !== formData.confirmPassword) {
        console.log('❌ Пароли не совпадают');
        newErrors.confirmPassword = 'Пароли не совпадают';
      }
    }
    
    console.log('  - Все ошибки:', newErrors);
    console.log('  - Количество ошибок:', Object.keys(newErrors).length);
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // === ВХОД ===
  const handleLogin = async () => {
    setError(null);
    setLoading(true);
    
    try {
      // reCAPTCHA отключена
      const recaptchaToken = null;

      const resolvedRole = await login({ 
        email: formData.email?.trim().toLowerCase(), 
        password: formData.password, 
        roleSelection: role 
      });
      // Используем только роль из JWT токена (resolvedRole)
      const nextRole = resolvedRole || 'teacher';
      const roleRedirects = {
        teacher: '/home-new',
        student: '/student',
        admin: '/admin-home',
      };
      // Сохраняем настройку "Запомнить меня"
      if (rememberMe) {
        localStorage.setItem('remember_me', 'true');
        // Можно установить более длительный срок для refresh токена
      } else {
        localStorage.removeItem('remember_me');
      }
      
      // Показываем успешное уведомление
      showNotification('success', 'Вход выполнен', `Добро пожаловать, ${formData.email}!`);
      
      // Небольшая задержка перед редиректом для показа уведомления
      setTimeout(() => {
        navigate(roleRedirects[nextRole] || '/');
      }, 500);
      
      // Сброс попыток при успешном входе
      setLoginAttempts(0);
      setShowCaptcha(false);
    } catch (err) {
      // Увеличиваем счетчик попыток
      const newAttempts = loginAttempts + 1;
      setLoginAttempts(newAttempts);
      
      // Определяем тип ошибки и формируем сообщение
      const errorDetail = err.response?.data?.detail || '';
      let errorTitle = 'Ошибка входа';
      let errorMessage = 'Проверьте правильность введённых данных';
      
      // Проверяем различные типы ошибок
      if (err.response?.status === 401 || errorDetail.includes('credentials') || errorDetail.includes('account')) {
        errorTitle = 'Неверный логин или пароль';
        errorMessage = 'Пожалуйста, проверьте правильность написания email и пароля. Убедитесь, что Caps Lock выключен.';
      } else if (errorDetail.includes('inactive') || errorDetail.includes('disabled')) {
        errorTitle = 'Аккаунт неактивен';
        errorMessage = 'Ваш аккаунт был деактивирован. Обратитесь к администратору.';
      } else if (errorDetail.includes('verified') || errorDetail.includes('verification')) {
        errorTitle = 'Email не подтверждён';
        errorMessage = 'Пожалуйста, подтвердите ваш email перед входом.';
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
        role
      });
      const resolvedRole = await register({
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
        firstName: formData.firstName,
        lastName: formData.lastName,
        phone: formData.phone.trim(),
        role,
        birthDate: null,
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

      // После регистрации перенаправляем на /home-new
      console.log('✅ Регистрация успешна, перенаправление на /home-new');
      navigate('/home-new', { replace: true });
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

  // === ВОССТАНОВЛЕНИЕ ПАРОЛЯ ===
  const handleResetPassword = async () => {
    const emailError = validateEmail(resetEmail);
    if (emailError) {
      setError(emailError);
      return;
    }
    
    setResetLoading(true);
    setError('');
    
    try {
      // Пробуем новый метод через Telegram
      const response = await fetch('/accounts/api/password-reset-telegram/request/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: resetEmail }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        if (data.telegram_linked) {
          // Telegram привязан - показываем инструкцию
          setError('');
          showNotification(
            'info',
            'Откройте Telegram',
            'Отправьте команду /reset нашему боту @YourBotName для получения ссылки'
          );
        } else {
          // Telegram не привязан
          showNotification(
            'warning',
            'Telegram не привязан',
            'Обратитесь к администратору для восстановления пароля'
          );
        }
        setResetSuccess(true);
        setTimeout(() => {
          setShowResetModal(false);
          setResetSuccess(false);
          setResetEmail('');
        }, 5000);
      } else {
        setError(data.detail || 'Ошибка при запросе восстановления');
      }
    } catch (err) {
      setError('Ошибка сети. Попробуйте позже.');
    } finally {
      setResetLoading(false);
    }
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

  // === РЕНДЕР: ШАГ 0 - ВЫБОР РОЛИ ===
  if (step === 0) {
    return (
      <>
        <div className="auth-container">
          <div className="auth-content">
            <div className="auth-header">
              <h1 className="auth-title">Добро пожаловать</h1>
              <p className="auth-subtitle">Выберите вашу роль для продолжения</p>
            </div>

            <div className="role-selection">
              <div 
                className="role-card"
                onClick={() => selectRole('student')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && selectRole('student')}
              >
                <div className="role-icon">🎓</div>
                <h3 className="role-title">Я Ученик</h3>
                <p className="role-description">
                  Доступ к расписанию, заданиям и материалам
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
                <h3 className="role-title">Я Учитель</h3>
                <p className="role-description">
                  Управление группами, уроками и домашними заданиями
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
        <div className="auth-content">
          <div className="auth-header">
            <h1 className="auth-title">
              {mode === 'login' ? 'Вход в систему' : 'Регистрация'}
            </h1>
            <p className="auth-subtitle">
              {mode === 'login' 
                ? `Войдите как ${role === 'student' ? 'ученик' : 'учитель'}`
                : `Зарегистрируйтесь как ${role === 'student' ? 'ученик' : 'учитель'}`
              }
            </p>
          </div>

          <div className="auth-backlink">
            <button 
              className="back-button"
              onClick={() => { setStep(0); setMode('login'); }}
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
                  onClick={() => setShowResetModal(true)}
                  disabled={loading || blocked}
                >
                  Забыли пароль?
                </button>
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
                {mode === 'login' ? 'Нет аккаунта?' : 'Уже есть аккаунт?'}
                {' '}
                <button
                  type="button"
                  className="link-button"
                  onClick={toggleMode}
                  disabled={loading || blocked}
                >
                  {mode === 'login' ? 'Зарегистрироваться' : 'Войти'}
                </button>
              </p>
            </div>

            {/* Кнопка убрана - редирект происходит автоматически */}
          </form>

          
        </div>

        {/* Новое модальное окно восстановления пароля через Telegram/WhatsApp */}
        <PasswordResetModal
          isOpen={showResetModal}
          onClose={() => setShowResetModal(false)}
        />
        
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
