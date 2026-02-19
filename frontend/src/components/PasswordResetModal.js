import React, { useState } from 'react';
import './PasswordResetModal.css';

const PasswordResetModal = ({ isOpen, onClose }) => {
  const [step, setStep] = useState(1); // 1: email/phone, 2: method, 3: code, 4: new password
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [method, setMethod] = useState('telegram'); // telegram или whatsapp
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  // Режим: 'choose' (выбор метода), 'email' (простой email-сброс), 'code' (через Telegram/WhatsApp)
  const [resetMode, setResetMode] = useState('choose');

  const resetForm = () => {
    setStep(1);
    setEmail('');
    setPhone('');
    setMethod('telegram');
    setCode('');
    setNewPassword('');
    setConfirmPassword('');
    setToken('');
    setError('');
    setSuccessMessage('');
    setResetMode('choose');
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  /**
   * Извлекает текст ошибки из ответа API (поддерживает data.error, data.detail, data.message)
   */
  const extractError = (data) => {
    return data?.error || data?.detail || data?.message || 'Неизвестная ошибка';
  };

  /**
   * Простой email-сброс: генерирует временный пароль и отправляет на email
   */
  const handleEmailReset = async () => {
    setError('');
    setLoading(true);

    if (!email) {
      setError('Введите email');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch('/accounts/api/password-reset/request/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      let data;
      try {
        data = await response.json();
      } catch {
        console.error('[PasswordReset] Не удалось прочитать тело ответа, статус:', response.status);
        setError(`Ошибка сервера (HTTP ${response.status}). Попробуйте позже.`);
        return;
      }

      if (response.ok) {
        setSuccessMessage(data.message || 'Новый пароль отправлен на ваш email. Проверьте почту (включая папку Спам).');
        setStep(5); // Успех
      } else {
        const errMsg = extractError(data);
        setError(errMsg);
        console.error('[PasswordReset] Ошибка email-сброса:', errMsg);
      }
    } catch (err) {
      console.error('[PasswordReset] Сетевая ошибка:', err);
      setError('Ошибка соединения с сервером. Проверьте интернет.');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestCode = async () => {
    setError('');
    setLoading(true);

    if (!email || !phone) {
      setError('Введите email и номер телефона');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch('/accounts/api/password-reset/request-code/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, phone, method })
      });

      let data;
      try {
        data = await response.json();
      } catch {
        console.error('[PasswordReset] Не удалось прочитать тело ответа, статус:', response.status);
        setError(`Ошибка сервера (HTTP ${response.status}). Попробуйте позже.`);
        return;
      }

      if (data.success) {
        setSuccessMessage(`Код отправлен через ${method === 'telegram' ? 'Telegram' : 'WhatsApp'}`);
        setStep(3); // Переход к вводу кода
      } else {
        const errMsg = extractError(data);
        setError(errMsg);
        console.error('[PasswordReset] Ошибка запроса кода:', errMsg);
      }
    } catch (err) {
      console.error('[PasswordReset] Сетевая ошибка:', err);
      setError('Ошибка соединения с сервером. Проверьте интернет.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    setError('');
    setLoading(true);

    if (!code) {
      setError('Введите код');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch('/accounts/api/password-reset/verify-code/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code })
      });

      let data;
      try {
        data = await response.json();
      } catch {
        console.error('[PasswordReset] Не удалось прочитать тело ответа, статус:', response.status);
        setError(`Ошибка сервера (HTTP ${response.status}). Попробуйте позже.`);
        return;
      }

      if (data.success) {
        setToken(data.token);
        setSuccessMessage('Код подтверждён! Установите новый пароль');
        setStep(4); // Переход к установке пароля
      } else {
        const errMsg = extractError(data);
        setError(errMsg);
        console.error('[PasswordReset] Ошибка проверки кода:', errMsg);
      }
    } catch (err) {
      console.error('[PasswordReset] Сетевая ошибка:', err);
      setError('Ошибка соединения с сервером. Проверьте интернет.');
    } finally {
      setLoading(false);
    }
  };

  const handleSetPassword = async () => {
    setError('');
    setLoading(true);

    if (!newPassword || !confirmPassword) {
      setError('Заполните оба поля пароля');
      setLoading(false);
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Пароли не совпадают');
      setLoading(false);
      return;
    }

    if (newPassword.length < 6) {
      setError('Пароль должен содержать минимум 6 символов');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch('/accounts/api/password-reset/set-password/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPassword })
      });

      let data;
      try {
        data = await response.json();
      } catch {
        console.error('[PasswordReset] Не удалось прочитать тело ответа, статус:', response.status);
        setError(`Ошибка сервера (HTTP ${response.status}). Попробуйте позже.`);
        return;
      }

      if (data.success) {
        setSuccessMessage('Пароль успешно изменён! Теперь вы можете войти с новым паролем');
        setTimeout(() => {
          handleClose();
        }, 2000);
      } else {
        const errMsg = extractError(data);
        setError(errMsg);
        console.error('[PasswordReset] Ошибка установки пароля:', errMsg);
      }
    } catch (err) {
      console.error('[PasswordReset] Сетевая ошибка:', err);
      setError('Ошибка соединения с сервером. Проверьте интернет.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="password-reset-modal-overlay" onClick={handleClose}>
      <div className="password-reset-modal" onClick={(e) => e.stopPropagation()}>
        <button className="close-button" onClick={handleClose}>×</button>
        
        <h2>Восстановление пароля</h2>

        {/* Ошибка — всегда сверху для видимости */}
        {error && (
          <div className="error-message" role="alert">
            ⚠️ {error}
          </div>
        )}

        {/* Шаг выбора метода восстановления */}
        {step === 1 && resetMode === 'choose' && (
          <div className="step-content">
            <p>Выберите способ восстановления пароля</p>
            <input
              type="email"
              placeholder="Введите ваш email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
            />
            <button
              onClick={() => { setResetMode('email'); handleEmailReset(); }}
              disabled={loading || !email}
              className="email-reset-btn"
            >
              📧 Получить новый пароль на email
            </button>
            <div className="divider-text">или</div>
            <button
              onClick={() => setResetMode('code')}
              disabled={loading || !email}
              className="telegram-reset-btn"
            >
              📱 Восстановить через Telegram / WhatsApp
            </button>
          </div>
        )}

        {/* Режим email — успех */}
        {step === 5 && (
          <div className="step-content">
            <div className="success-icon-block">✅</div>
            <p className="success-text">{successMessage}</p>
            <button onClick={handleClose}>
              Закрыть
            </button>
          </div>
        )}

        {/* Шаг 1 (Telegram/WhatsApp): Ввод телефона */}
        {step === 1 && resetMode === 'code' && (
          <div className="step-content">
            <p>Введите номер телефона, указанный при регистрации</p>
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
            />
            <input
              type="tel"
              placeholder="+7 (999) 123-45-67"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={loading}
            />
            <div className="button-group">
              <button onClick={() => setResetMode('choose')} disabled={loading} className="back-button">
                Назад
              </button>
              <button onClick={() => setStep(2)} disabled={loading || !email || !phone}>
                Далее
              </button>
            </div>
          </div>
        )}

        {/* Шаг 2: Выбор метода отправки */}
        {step === 2 && (
          <div className="step-content">
            <p>Выберите способ получения кода</p>
            <div className="method-selection">
              <label className={method === 'telegram' ? 'selected' : ''}>
                <input
                  type="radio"
                  value="telegram"
                  checked={method === 'telegram'}
                  onChange={(e) => setMethod(e.target.value)}
                  disabled={loading}
                />
                <span>📱 Telegram</span>
              </label>
              <label className={method === 'whatsapp' ? 'selected' : ''}>
                <input
                  type="radio"
                  value="whatsapp"
                  checked={method === 'whatsapp'}
                  onChange={(e) => setMethod(e.target.value)}
                  disabled={loading}
                />
                <span>💬 WhatsApp</span>
              </label>
            </div>
            <div className="button-group">
              <button onClick={() => setStep(1)} disabled={loading} className="back-button">
                Назад
              </button>
              <button onClick={handleRequestCode} disabled={loading}>
                {loading ? 'Отправка...' : 'Отправить код'}
              </button>
            </div>
          </div>
        )}

        {/* Шаг 3: Ввод кода */}
        {step === 3 && (
          <div className="step-content">
            <p>Введите код из {method === 'telegram' ? 'Telegram' : 'WhatsApp'}</p>
            <input
              type="text"
              placeholder="Код (6 цифр)"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={6}
              disabled={loading}
            />
            <div className="button-group">
              <button onClick={() => setStep(2)} disabled={loading} className="back-button">
                Назад
              </button>
              <button onClick={handleVerifyCode} disabled={loading || code.length < 6}>
                {loading ? 'Проверка...' : 'Подтвердить'}
              </button>
            </div>
            <button onClick={handleRequestCode} disabled={loading} className="resend-button">
              Отправить код повторно
            </button>
          </div>
        )}

        {/* Шаг 4: Установка нового пароля */}
        {step === 4 && (
          <div className="step-content">
            <p>Установите новый пароль</p>
            <input
              type="password"
              placeholder="Новый пароль"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={loading}
            />
            <input
              type="password"
              placeholder="Подтвердите пароль"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={loading}
            />
            <small>Минимум 6 символов, включая заглавную букву, строчную букву и цифру</small>
            <button onClick={handleSetPassword} disabled={loading}>
              {loading ? 'Сохранение...' : 'Изменить пароль'}
            </button>
          </div>
        )}

        {successMessage && step !== 5 && <div className="success-message">{successMessage}</div>}
      </div>
    </div>
  );
};

export default PasswordResetModal;
