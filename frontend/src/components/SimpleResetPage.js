import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import './SimpleResetPage.css';

const SimpleResetPage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Валидация пароля в реальном времени
  const checks = useMemo(() => ({
    length: password.length >= 8,
    upper: /[A-ZА-ЯЁ]/.test(password),
    lower: /[a-zа-яё]/.test(password),
    digit: /\d/.test(password),
  }), [password]);

  const allValid = checks.length && checks.upper && checks.lower && checks.digit;
  const passwordsMatch = password && confirmPassword && password === confirmPassword;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email) {
      setError('Введите email');
      return;
    }

    if (!allValid) {
      setError('Пароль не соответствует требованиям');
      return;
    }

    if (!passwordsMatch) {
      setError('Пароли не совпадают');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('/accounts/api/simple-reset/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          new_password: password,
        }),
      });

      let data;
      try {
        data = await response.json();
      } catch {
        console.error('[SimpleReset] Не удалось прочитать ответ, HTTP', response.status);
        setError(`Ошибка сервера (HTTP ${response.status}). Попробуйте позже.`);
        return;
      }

      if (response.ok && data.success) {
        setSuccess(true);
        setTimeout(() => navigate('/auth-new'), 3000);
      } else {
        const msg = data.error || data.detail || data.message || 'Не удалось сбросить пароль';
        setError(msg);
        console.error('[SimpleReset] Ошибка:', msg);
      }
    } catch (err) {
      console.error('[SimpleReset] Сетевая ошибка:', err);
      setError('Ошибка сети. Попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="simple-reset-wrapper">
        <div className="simple-reset-card">
          <div className="success-icon">✓</div>
          <h2>Пароль успешно изменён!</h2>
          <p className="success-text">Перенаправление на страницу входа...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="simple-reset-wrapper">
      <div className="simple-reset-card">
        <h2>Сброс пароля</h2>
        <p className="subtitle">Введите email и новый пароль</p>

        <form onSubmit={handleSubmit} className="reset-form" noValidate>
          {/* Email */}
          <div className="field">
            <label htmlFor="sr-email">Email</label>
            <input
              id="sr-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              autoComplete="email"
              disabled={loading}
            />
          </div>

          {/* New password */}
          <div className="field">
            <label htmlFor="sr-pass">Новый пароль</label>
            <div className="password-wrapper">
              <input
                id="sr-pass"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Минимум 8 символов"
                autoComplete="new-password"
                disabled={loading}
              />
              <button
                type="button"
                className="toggle-vis"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          {/* Confirm password */}
          <div className="field">
            <label htmlFor="sr-confirm">Подтвердите пароль</label>
            <div className="password-wrapper">
              <input
                id="sr-confirm"
                type={showConfirm ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Повторите пароль"
                autoComplete="new-password"
                disabled={loading}
              />
              <button
                type="button"
                className="toggle-vis"
                onClick={() => setShowConfirm(!showConfirm)}
                tabIndex={-1}
                aria-label={showConfirm ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showConfirm ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          {/* Password requirements */}
          {password.length > 0 && (
            <div className="requirements">
              <p className="req-title">Требования к паролю:</p>
              <ul>
                <li className={checks.length ? 'ok' : ''}>{checks.length ? '✔' : '✖'} Минимум 8 символов</li>
                <li className={checks.upper ? 'ok' : ''}>{checks.upper ? '✔' : '✖'} Заглавная буква</li>
                <li className={checks.lower ? 'ok' : ''}>{checks.lower ? '✔' : '✖'} Строчная буква</li>
                <li className={checks.digit ? 'ok' : ''}>{checks.digit ? '✔' : '✖'} Цифра</li>
              </ul>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="reset-error" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="submit-btn"
            disabled={loading || !email || !allValid || !passwordsMatch}
          >
            {loading ? 'Сохранение...' : 'Сбросить пароль'}
          </button>
        </form>

        <button
          type="button"
          className="back-link"
          onClick={() => navigate('/auth-new')}
        >
          Вернуться ко входу
        </button>
      </div>
    </div>
  );
};

export default SimpleResetPage;
