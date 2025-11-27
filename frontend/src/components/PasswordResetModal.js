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
  };

  const handleClose = () => {
    resetForm();
    onClose();
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

      const data = await response.json();

      if (data.success) {
        setSuccessMessage(`Код отправлен через ${method === 'telegram' ? 'Telegram' : 'WhatsApp'}`);
        setStep(3); // Переход к вводу кода
      } else {
        setError(data.error || 'Не удалось отправить код');
      }
    } catch (err) {
      setError('Ошибка соединения с сервером');
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

      const data = await response.json();

      if (data.success) {
        setToken(data.token);
        setSuccessMessage('Код подтверждён! Установите новый пароль');
        setStep(4); // Переход к установке пароля
      } else {
        setError(data.error || 'Неверный код');
      }
    } catch (err) {
      setError('Ошибка соединения с сервером');
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

      const data = await response.json();

      if (data.success) {
        setSuccessMessage('Пароль успешно изменён! Теперь вы можете войти с новым паролем');
        setTimeout(() => {
          handleClose();
        }, 2000);
      } else {
        setError(data.error || 'Не удалось изменить пароль');
      }
    } catch (err) {
      setError('Ошибка соединения с сервером');
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

        {/* Шаг 1: Ввод email и телефона */}
        {step === 1 && (
          <div className="step-content">
            <p>Введите ваш email и номер телефона</p>
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
            <button onClick={() => setStep(2)} disabled={loading || !email || !phone}>
              Далее
            </button>
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

        {error && <div className="error-message">{error}</div>}
        {successMessage && <div className="success-message">{successMessage}</div>}
      </div>
    </div>
  );
};

export default PasswordResetModal;
