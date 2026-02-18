import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import './PasswordReset.css';

const PasswordResetPage = () => {
  const { uid, token: urlToken } = useParams();
  const [searchParams] = useSearchParams();
  const telegramToken = searchParams.get('token'); // Токен из Telegram
  const navigate = useNavigate();
  
  const [step, setStep] = useState('validate'); // 'validate' | 'reset' | 'success' | 'error'
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [isTelegramReset, setIsTelegramReset] = useState(false);

  useEffect(() => {
    if (telegramToken) {
      // Сброс через Telegram
      setIsTelegramReset(true);
      setStep('reset');
    } else if (uid && urlToken) {
      // Старый метод (email)
      validateToken();
    } else {
      setError('Неверная ссылка для сброса пароля');
      setStep('error');
    }
  }, [uid, urlToken, telegramToken]);

  const validateToken = async () => {
    try {
      const response = await fetch(
        `/accounts/api/password-reset/validate/${uid}/${urlToken}/`
      );
      const data = await response.json();
      
      if (data.valid) {
        setUserEmail(data.email);
        setStep('reset');
      } else {
        setError(data.error || 'Недействительная ссылка');
        setStep('error');
      }
    } catch (err) {
      setError('Не удалось проверить ссылку');
      setStep('error');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (password.length < 8) {
      setError('Пароль должен содержать минимум 8 символов');
      return;
    }
    
    if (password !== confirmPassword) {
      setError('Пароли не совпадают');
      return;
    }
    
    setLoading(true);
    
    try {
      let response;
      
      if (isTelegramReset) {
        // Сброс через Telegram токен
        response = await fetch('/accounts/api/password-reset-telegram/confirm/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            token: telegramToken,
            new_password: password,
          }),
        });
      } else {
        // Старый метод (email)
        response = await fetch('/accounts/api/password-reset/confirm/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            uid,
            token: urlToken,
            password,
          }),
        });
      }
      
      const data = await response.json();
      
      if (response.ok) {
        setStep('success');
        setTimeout(() => {
          navigate('/auth');
        }, 3000);
      } else {
        setError(data.detail || data.error || 'Не удалось сбросить пароль');
      }
    } catch (err) {
      setError('Ошибка сети. Попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="password-reset-container">
      <div className="password-reset-card">
        {step === 'validate' && (
          <div className="reset-step">
            <div className="loading-spinner"></div>
            <h2>Проверка ссылки...</h2>
          </div>
        )}

        {step === 'reset' && (
          <div className="reset-step">
            <h2>Сброс пароля</h2>
            <p className="reset-subtitle">Для аккаунта: <strong>{userEmail}</strong></p>
            
            <form onSubmit={handleSubmit} className="reset-form">
              <div className="form-group">
                <label>Новый пароль</label>
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Минимум 6 символов"
                    disabled={loading}
                    required
                  />
                  <button
                    type="button"
                    className="toggle-password"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? '●' : '▪'}
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label>Подтвердите пароль</label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Повторите пароль"
                  disabled={loading}
                  required
                />
              </div>

              {error && <div className="reset-error">{error}</div>}

              <button type="submit" className="reset-submit-btn" disabled={loading}>
                {loading ? 'Сохранение...' : 'Сбросить пароль'}
              </button>
            </form>
          </div>
        )}

        {step === 'success' && (
          <div className="reset-step reset-success">
            <div className="success-icon">✓</div>
            <h2>Пароль успешно изменен!</h2>
            <p>Перенаправление на страницу входа...</p>
          </div>
        )}

        {step === 'error' && (
          <div className="reset-step reset-error-state">
            <div className="error-icon">✕</div>
            <h2>Ошибка</h2>
            <p>{error}</p>
            <button
              className="reset-back-btn"
              onClick={() => navigate('/auth')}
            >
              Вернуться ко входу
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PasswordResetPage;
