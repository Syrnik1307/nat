import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Input, Button } from '../shared/components';
import { useAuth } from '../auth';
import { useNotifications } from '../shared/context/NotificationContext';
// import { useRecaptcha } from '../hooks/useRecaptcha'; // отключено

const RegisterPage = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const { toast } = useNotifications();
  // const { executeRecaptcha } = useRecaptcha(); // отключено
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    role: null,
    birthDate: '',
  });
  const [step, setStep] = useState(0); // 0=выбор роли, 1=форма

  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  // Валидация email
  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) return 'Email обязателен';
    if (!emailRegex.test(email)) return 'Неверный формат email';
    return '';
  };

  // Валидация пароля
  const validatePassword = (password) => {
    if (!password) return 'Пароль обязателен';
    if (password.length < 6) return 'Минимум 6 символов';
    if (!/[A-Z]/.test(password)) return 'Должна быть хотя бы одна заглавная буква';
    if (!/[a-z]/.test(password)) return 'Должна быть хотя бы одна строчная буква';
    if (!/[0-9]/.test(password)) return 'Должна быть хотя бы одна цифра';
    return '';
  };

  // Обработка изменения полей
  const handleChange = (field, value) => {
    setFormData({ ...formData, [field]: value });
    
    // Валидация в реальном времени
    let error = '';
    if (field === 'email') {
      error = validateEmail(value);
    } else if (field === 'password') {
      error = validatePassword(value);
    } else if (field === 'confirmPassword') {
      error = value !== formData.password ? 'Пароли не совпадают' : '';
    }
    
    setErrors({ ...errors, [field]: error });
  };

  // Отправка формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    console.log('🚀 handleSubmit вызван!');
    console.log('  - formData:', formData);
    console.log('  - agreedToTerms:', agreedToTerms);

    // Валидация всех полей
    const newErrors = {};
    newErrors.email = validateEmail(formData.email);
    newErrors.password = validatePassword(formData.password);
    newErrors.confirmPassword = formData.password !== formData.confirmPassword ? 'Пароли не совпадают' : '';
    newErrors.firstName = !formData.firstName ? 'Имя обязательно' : '';
    newErrors.lastName = !formData.lastName ? 'Фамилия обязательна' : '';
    
    if (!agreedToTerms) {
      newErrors.terms = 'Необходимо согласиться с условиями';
    }

    // Проверка на наличие ошибок
    const hasErrors = Object.values(newErrors).some(error => error !== '');
    console.log('  - hasErrors:', hasErrors);
    console.log('  - newErrors:', newErrors);
    
    if (hasErrors) {
      setErrors(newErrors);
      toast.warning('Пожалуйста, заполните все обязательные поля корректно');
      return;
    }

    setLoading(true);
    try {
      console.log('🔐 Начало процесса регистрации...');
      // reCAPTCHA отключена
      const recaptchaToken = null;

      console.log('📤 Регистрация через auth.register...');
      const resolvedRole = await register({
        email: formData.email,
        password: formData.password,
        firstName: formData.firstName,
        lastName: formData.lastName,
        role: formData.role,
        birthDate: formData.birthDate || null,
      });
      console.log('✅ Регистрация успешна! Роль:', resolvedRole);
      const target = resolvedRole === 'teacher'
        ? '/teacher'
        : resolvedRole === 'student'
          ? '/student'
          : '/redirect';
      // Сначала навигация SPA
      navigate(target, { replace: true });
      // Фолбэк перезагрузки если контекст ещё не успел примениться
      setTimeout(() => {
        if (window.location.pathname !== target) {
          window.location.href = target;
        }
      }, 300);
    } catch (err) {
      console.error('❌ Ошибка регистрации:', err);
      console.error('  - Статус:', err.response?.status);
      console.error('  - Данные ошибки:', err.response?.data);
      
      const errorMessage = err.response?.data?.detail || err.response?.data?.email?.[0] || 'Ошибка регистрации';
      const isRecaptchaError = err.response?.data?.recaptcha_error;
      
      toast.error(errorMessage);
      
      setErrors({
        submit: isRecaptchaError 
          ? `🤖 Защита от роботов: ${errorMessage}. Попробуйте обновить страницу.`
          : errorMessage,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-gradient-bg">
      {step === 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-xl)', width: '100%', zIndex: 1 }}>
          <header style={{ textAlign: 'center' }}>
            <h1 style={{ color: '#fff', fontSize: '2.75rem', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>Регистрация</h1>
            <p style={{ color: 'rgba(255,255,255,.8)', marginTop: 'var(--space-md)', fontSize: '1.0625rem', fontWeight: 400 }}>Выберите вашу роль для создания аккаунта</p>
          </header>
          <div className="role-card-grid" role="list">
            <div 
              className={`glass-card role-select ${formData.role === 'student' ? 'active' : ''}`}
              role="listitem"
              tabIndex={0}
              onClick={() => { 
                console.log('🎓 Выбрана роль: Ученик');
                setFormData({ ...formData, role: 'student' }); 
                setStep(1); 
              }}
              onKeyDown={(e) => { if (e.key === 'Enter') { setFormData({ ...formData, role: 'student' }); setStep(1); } }}
              aria-label="Выбрать роль ученик"
              style={{ cursor: 'pointer', pointerEvents: 'auto' }}
            >
              <div className="role-icon">☎</div>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>Я Ученик</h3>
              <p style={{ fontSize: '0.9375rem', lineHeight: 1.6, opacity: .85, margin: 0 }}>Расписание, задания, прогресс и внутренняя валюта роста.</p>
            </div>
            <div 
              className={`glass-card role-select ${formData.role === 'teacher' ? 'active' : ''}`}
              role="listitem"
              tabIndex={0}
              onClick={() => { 
                console.log('👨‍🏫 Выбрана роль: Преподаватель');
                setFormData({ ...formData, role: 'teacher' }); 
                setStep(1); 
              }}
              onKeyDown={(e) => { if (e.key === 'Enter') { setFormData({ ...formData, role: 'teacher' }); setStep(1); } }}
              aria-label="Выбрать роль преподаватель"
            >
              <div className="role-icon">👨‍🏫</div>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>Я Учитель</h3>
              <p style={{ fontSize: '0.9375rem', lineHeight: 1.6, opacity: .85, margin: 0 }}>Создание занятий, управление группами и контроль посещаемости.</p>
            </div>
          </div>
          <p className="auth-small-note">Роль можно сменить на следующем шаге.</p>
        </div>
      )}
      {step === 1 && (
      <div className="auth-form-card" style={{ zIndex: 1 }}>
        <h2 style={{ textAlign: 'center', marginBottom: 'var(--space-xl)', fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.01em' }}>
          {formData.role === 'teacher' ? 'Организатор регистрацию рея обучал' : 'Регистрация ученика'}
        </h2>

        <form onSubmit={handleSubmit}>
          {/* Смена роли */}
          <div style={{ textAlign: 'right', marginBottom: 'var(--space-md)' }}>
            <span 
              className="auth-change-role"
              onClick={() => { setStep(0); setFormData({ ...formData, role: null }); }}
            >Сменить роль</span>
          </div>
          {/* Имя и Фамилия */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label="Имя"
              type="text"
              value={formData.firstName}
              onChange={(e) => handleChange('firstName', e.target.value)}
              error={errors.firstName}
              placeholder="Иван"
              required
            />
            <Input
              label="Фамилия"
              type="text"
              value={formData.lastName}
              onChange={(e) => handleChange('lastName', e.target.value)}
              error={errors.lastName}
              placeholder="Иванов"
              required
            />
          </div>

          {/* Email */}
          <Input
            label="Email"
            type="email"
            value={formData.email}
            onChange={(e) => handleChange('email', e.target.value)}
            error={errors.email}
            placeholder="example@mail.com"
            required
          />

          {/* Пароль */}
          <Input
            label="Пароль"
            type="password"
            value={formData.password}
            onChange={(e) => handleChange('password', e.target.value)}
            error={errors.password}
            placeholder="Минимум 6 символов"
            required
          />

          {formData.password && (
            <div style={{
              fontSize: '0.8125rem',
              color: 'rgba(255,255,255,0.7)',
              marginTop: '-0.5rem',
              marginBottom: 'var(--space-md)',
              padding: 'var(--space-sm)',
              background: 'rgba(255,255,255,0.08)',
              borderRadius: 'var(--radius-md)',
              backdropFilter: 'blur(10px)',
            }}>
              <div style={{ marginBottom: '0.375rem', fontWeight: 600 }}>Требования к паролю:</div>
              <div style={{ color: formData.password.length >= 6 ? '#6ee7b7' : 'rgba(255,255,255,0.5)' }}>
                ✓ Минимум 6 символов
              </div>
              <div style={{ color: /[A-Z]/.test(formData.password) ? '#6ee7b7' : 'rgba(255,255,255,0.5)' }}>
                ✓ Заглавная буква
              </div>
              <div style={{ color: /[a-z]/.test(formData.password) ? '#6ee7b7' : 'rgba(255,255,255,0.5)' }}>
                ✓ Строчная буква
              </div>
              <div style={{ color: /[0-9]/.test(formData.password) ? '#6ee7b7' : 'rgba(255,255,255,0.5)' }}>
                ✓ Цифра
              </div>
            </div>
          )}

          {/* Подтверждение пароля */}
          <Input
            label="Повторите пароль"
            type="password"
            value={formData.confirmPassword}
            onChange={(e) => handleChange('confirmPassword', e.target.value)}
            error={errors.confirmPassword}
            placeholder="Повторите пароль"
            required
          />

          {/* Дата рождения */}
          <Input
            label="Дата рождения (опционально)"
            type="date"
            value={formData.birthDate}
            onChange={(e) => handleChange('birthDate', e.target.value)}
          />

          {/* Выбранная роль (readonly визуал) */}
          <div style={{ marginBottom: '1rem', fontSize: '.8rem', color: '#d1fae5' }}>
            Выбранная роль: <strong>{formData.role === 'teacher' ? 'Учитель' : 'Ученик'}</strong>
          </div>

          {/* Согласие с условиями */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={agreedToTerms}
                onChange={(e) => {
                  setAgreedToTerms(e.target.checked);
                  setErrors({ ...errors, terms: '' });
                }}
                style={{ marginTop: '0.25rem' }}
              />
              <span style={{ fontSize: '0.875rem', color: '#374151' }}>
                Я согласен с условиями использования и политикой конфиденциальности
              </span>
            </label>
            {errors.terms && (
              <div style={{ color: '#ef4444', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                {errors.terms}
              </div>
            )}
          </div>

          {/* Ошибка отправки */}
          {errors.submit && (
            <div style={{
              padding: '0.75rem',
              marginBottom: '1rem',
              backgroundColor: '#fef2f2',
              color: '#dc2626',
              borderRadius: '8px',
              fontSize: '0.875rem',
              border: '1px solid #fecaca',
            }}>
              {errors.submit}
            </div>
          )}

          {/* Кнопка регистрации */}
          <Button
            type="submit"
            variant="success"
            size="large"
            loading={loading}
            disabled={loading}
            style={{ width: '100%', marginBottom: '1rem' }}
            onClick={(e) => {
              console.log('🖱️ Клик по кнопке регистрации');
              console.log('  - Event type:', e.type);
              console.log('  - Button type:', e.target.type);
            }}
          >
            {loading ? 'Регистрация...' : 'Зарегистрироваться'}
          </Button>

          {/* Ссылка на вход */}
          <div style={{ textAlign: 'center', fontSize: '0.875rem', color: '#6b7280' }}>
            Уже есть аккаунт?{' '}
            <a
              href="/login"
              onClick={(e) => {
                e.preventDefault();
                navigate('/login');
              }}
              style={{
                color: '#10b981',
                textDecoration: 'none',
                fontWeight: '500',
              }}
              onMouseEnter={(e) => e.target.style.textDecoration = 'underline'}
              onMouseLeave={(e) => e.target.style.textDecoration = 'none'}
            >
              Войти
            </a>
          </div>
        </form>
      </div>
      )}
    </div>
  );
};

export default RegisterPage;
