/**
 * SimpleResetPage - Простой сброс пароля
 * ========================================
 * Изолированный компонент, не трогает существующую auth логику.
 * 
 * Путь: /simple-reset
 * API: POST /api/accounts/simple-reset/
 * 
 * Добавлен: 2026-02-01
 */
import React, { useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Input, Button } from '../shared/components';
import './PasswordReset.css'; // Переиспользуем существующие стили

const SimpleResetPage = () => {
  const navigate = useNavigate();
  
  // Состояния формы
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  
  // UI состояния
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  
  // Валидация пароля
  const validatePassword = useCallback((password) => {
    if (!password) return 'Пароль обязателен';
    if (password.length < 8) return 'Минимум 8 символов';
    if (!/[A-ZА-Я]/.test(password)) return 'Нужна хотя бы одна заглавная буква';
    if (!/[a-zа-я]/.test(password)) return 'Нужна хотя бы одна строчная буква';
    if (!/[0-9]/.test(password)) return 'Нужна хотя бы одна цифра';
    return '';
  }, []);
  
  // Отправка формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Валидация email
    if (!email || !email.includes('@')) {
      setError('Введите корректный email');
      return;
    }
    
    // Валидация пароля
    const passwordError = validatePassword(newPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    
    // Проверка совпадения
    if (newPassword !== confirmPassword) {
      setError('Пароли не совпадают');
      return;
    }
    
    setLoading(true);
    
    try {
      const response = await fetch('/api/simple-reset/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          new_password: newPassword,
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        // Обработка ошибок
        if (response.status === 429) {
          setError('Слишком много попыток. Подождите 10 минут.');
        } else if (response.status === 404) {
          setError('Пользователь с таким email не найден');
        } else {
          setError(data.error || 'Произошла ошибка');
        }
        return;
      }
      
      // Успех
      setSuccess(true);
    } catch (err) {
      setError('Ошибка сети. Попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };
  
  // Переход на страницу входа
  const goToLogin = () => {
    navigate('/auth-new');
  };
  
  // Экран успеха
  if (success) {
    return (
      <div className="password-reset-container">
        <div className="password-reset-card">
          <div className="reset-step">
            <div className="success-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" strokeLinecap="round" strokeLinejoin="round"/>
                <polyline points="22 4 12 14.01 9 11.01" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h2>Пароль изменён</h2>
            <p className="reset-subtitle">
              Теперь вы можете войти с новым паролем
            </p>
            <Button 
              variant="primary" 
              onClick={goToLogin}
              style={{ width: '100%', marginTop: '16px' }}
            >
              Войти
            </Button>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="password-reset-container">
      <div className="password-reset-card">
        <div className="reset-step">
          <h2>Сброс пароля</h2>
          <p className="reset-subtitle">
            Введите email и новый пароль
          </p>
          
          <form className="reset-form" onSubmit={handleSubmit}>
            {/* Email */}
            <div className="form-group">
              <label htmlFor="reset-email">Email</label>
              <Input
                id="reset-email"
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                autoComplete="email"
              />
            </div>
            
            {/* New Password */}
            <div className="form-group">
              <label htmlFor="reset-new-password">Новый пароль</label>
              <div className="password-input-wrapper">
                <Input
                  id="reset-new-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Минимум 8 символов"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={loading}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  )}
                </button>
              </div>
            </div>
            
            {/* Confirm Password */}
            <div className="form-group">
              <label htmlFor="reset-confirm-password">Подтвердите пароль</label>
              <Input
                id="reset-confirm-password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Повторите пароль"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading}
                autoComplete="new-password"
              />
            </div>
            
            {/* Password Requirements */}
            <div className="password-requirements">
              <p className="requirements-title">Требования к паролю:</p>
              <ul>
                <li className={newPassword.length >= 8 ? 'valid' : ''}>
                  Минимум 8 символов
                </li>
                <li className={/[A-ZА-Я]/.test(newPassword) ? 'valid' : ''}>
                  Заглавная буква
                </li>
                <li className={/[a-zа-я]/.test(newPassword) ? 'valid' : ''}>
                  Строчная буква
                </li>
                <li className={/[0-9]/.test(newPassword) ? 'valid' : ''}>
                  Цифра
                </li>
              </ul>
            </div>
            
            {/* Error */}
            {error && (
              <div className="reset-error">
                {error}
              </div>
            )}
            
            {/* Submit */}
            <Button
              type="submit"
              variant="primary"
              disabled={loading}
              style={{ width: '100%' }}
            >
              {loading ? 'Сохранение...' : 'Сбросить пароль'}
            </Button>
          </form>
          
          {/* Back to Login */}
          <div className="reset-back-link">
            <Link to="/auth-new">Вернуться к входу</Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleResetPage;
