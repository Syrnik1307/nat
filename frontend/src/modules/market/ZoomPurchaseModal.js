/**
 * ZoomPurchaseModal - Modal for purchasing Zoom accounts.
 * Two-step flow: Account Type -> Form -> Payment
 */
import React, { useState } from 'react';
import { apiClient } from '../../apiService';
import { Modal, Button, Input } from '../../shared/components';
import './ZoomPurchaseModal.css';

// Icons
const UserPlusIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="8.5" cy="7" r="4" />
    <line x1="20" y1="8" x2="20" y2="14" />
    <line x1="23" y1="11" x2="17" y2="11" />
  </svg>
);

const UserCheckIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="8.5" cy="7" r="4" />
    <polyline points="17 11 19 13 23 9" />
  </svg>
);

const AlertCircleIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);

const ZoomPurchaseModal = ({ product, onClose, onComplete }) => {
  const [step, setStep] = useState(1); // 1 = type selection, 2 = form
  const [isNewAccount, setIsNewAccount] = useState(null); // null, true, false
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Form state
  const [formData, setFormData] = useState({
    zoomEmail: '',
    zoomPassword: '',
    contactInfo: '',
    autoConnect: true,
    randomEmail: false,
  });
  const [formErrors, setFormErrors] = useState({});

  const handleTypeSelect = (type) => {
    setIsNewAccount(type === 'new');
    setStep(2);
    setError('');
    setFormErrors({});
    // Reset form when switching types
    setFormData({
      zoomEmail: '',
      zoomPassword: '',
      contactInfo: '',
      autoConnect: true,
      randomEmail: false,
    });
  };

  const handleInputChange = (field) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field
    if (formErrors[field]) {
      setFormErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  const handleRandomEmailToggle = () => {
    setFormData((prev) => ({
      ...prev,
      randomEmail: !prev.randomEmail,
      zoomEmail: !prev.randomEmail ? '' : prev.zoomEmail,
    }));
  };

  const validateForm = () => {
    const errors = {};

    // Validate email for new account (if not random)
    if (isNewAccount && !formData.randomEmail && !formData.zoomEmail.trim()) {
      errors.zoomEmail = 'Укажите email или выберите "Случайный"';
    } else if (isNewAccount && !formData.randomEmail) {
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailPattern.test(formData.zoomEmail.trim())) {
        errors.zoomEmail = 'Некорректный формат email';
      }
    }

    // Validate login for existing account
    if (!isNewAccount && !formData.zoomEmail.trim()) {
      errors.zoomEmail = 'Укажите логин Zoom';
    }

    // Validate password
    const password = formData.zoomPassword.trim();
    if (!password) {
      errors.zoomPassword = 'Укажите пароль';
    } else if (password.length < 8) {
      errors.zoomPassword = 'Минимум 8 символов';
    } else if (!/[a-zA-Z]/.test(password)) {
      errors.zoomPassword = 'Должен содержать букву';
    } else if (!/\d/.test(password)) {
      errors.zoomPassword = 'Должен содержать цифру';
    }

    // Validate contact info
    if (!formData.contactInfo.trim()) {
      errors.contactInfo = 'Укажите Telegram или телефон';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setLoading(true);
    setError('');

    try {
      const payload = {
        product_id: product.id,
        is_new_account: isNewAccount,
        zoom_email: formData.zoomEmail.trim(),
        zoom_password: formData.zoomPassword,
        contact_info: formData.contactInfo.trim(),
        auto_connect: formData.autoConnect,
        random_email: formData.randomEmail,
      };

      const response = await apiClient.post('/market/buy/', payload);

      if (response.data.payment_url) {
        onComplete(response.data.payment_url);
      } else {
        setError('Не удалось получить ссылку на оплату');
      }
    } catch (err) {
      console.error('Purchase error:', err);
      const detail = err.response?.data?.detail || err.response?.data?.zoom_password?.[0] || 'Произошла ошибка';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('ru-RU').format(price);
  };

  const renderStepOne = () => (
    <div className="zoom-step-content">
      <h3 className="zoom-step-title">Выберите тип</h3>
      <div className="zoom-type-options">
        <button
          className={`zoom-type-option ${isNewAccount === true ? 'selected' : ''}`}
          onClick={() => handleTypeSelect('new')}
        >
          <div className="zoom-type-icon">
            <UserPlusIcon />
          </div>
          <div className="zoom-type-info">
            <span className="zoom-type-name">Создать новый аккаунт</span>
            <span className="zoom-type-desc">Мы создадим для вас новый Zoom Pro аккаунт</span>
          </div>
        </button>

        <button
          className={`zoom-type-option ${isNewAccount === false ? 'selected' : ''}`}
          onClick={() => handleTypeSelect('existing')}
        >
          <div className="zoom-type-icon">
            <UserCheckIcon />
          </div>
          <div className="zoom-type-info">
            <span className="zoom-type-name">Оплатить существующий</span>
            <span className="zoom-type-desc">Продлить подписку на ваш Zoom аккаунт</span>
          </div>
        </button>
      </div>
    </div>
  );

  const renderStepTwo = () => (
    <div className="zoom-step-content">
      <button className="zoom-back-btn" onClick={() => setStep(1)}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
          <polyline points="15 18 9 12 15 6" />
        </svg>
        Назад
      </button>

      <h3 className="zoom-step-title">
        {isNewAccount ? 'Данные нового аккаунта' : 'Данные существующего аккаунта'}
      </h3>

      <div className="zoom-form">
        {/* Email/Login field */}
        <div className="zoom-form-group">
          <Input
            label={isNewAccount ? 'Email для Zoom' : 'Логин Zoom'}
            type={isNewAccount ? 'email' : 'text'}
            placeholder={isNewAccount ? 'your@email.com' : 'Логин или email'}
            value={formData.zoomEmail}
            onChange={handleInputChange('zoomEmail')}
            error={formErrors.zoomEmail}
            disabled={isNewAccount && formData.randomEmail}
          />
          {isNewAccount && (
            <label className="zoom-checkbox">
              <input
                type="checkbox"
                checked={formData.randomEmail}
                onChange={handleRandomEmailToggle}
              />
              <span>Мне все равно (сгенерировать случайный email)</span>
            </label>
          )}
        </div>

        {/* Password field */}
        <div className="zoom-form-group">
          <Input
            label="Пароль Zoom"
            type="text"
            placeholder="Минимум 8 символов, буква и цифра"
            value={formData.zoomPassword}
            onChange={handleInputChange('zoomPassword')}
            error={formErrors.zoomPassword}
            helperText="Требования Zoom: минимум 8 символов, хотя бы 1 буква и 1 цифра"
          />
        </div>

        {/* Contact info */}
        <div className="zoom-form-group">
          <Input
            label="Ваш Telegram или телефон"
            type="text"
            placeholder="@username или +7..."
            value={formData.contactInfo}
            onChange={handleInputChange('contactInfo')}
            error={formErrors.contactInfo}
            helperText="Для связи по вопросам заказа"
          />
        </div>

        {/* Auto-connect checkbox */}
        <label className="zoom-checkbox zoom-checkbox-highlight">
          <input
            type="checkbox"
            checked={formData.autoConnect}
            onChange={handleInputChange('autoConnect')}
          />
          <span>Автоматически подключить этот аккаунт к платформе Lectio Space</span>
        </label>

        {/* Warning */}
        <div className="zoom-warning">
          <AlertCircleIcon />
          <span>Подключение может занять до 24 часов из-за большого количества заказов</span>
        </div>

        {/* Error message */}
        {error && <div className="zoom-error">{error}</div>}
      </div>
    </div>
  );

  const footer = (
    <div className="zoom-modal-footer">
      <div className="zoom-price-summary">
        <span className="zoom-price-label">К оплате:</span>
        <span className="zoom-price-value">{formatPrice(product.price)} ₽</span>
      </div>
      {step === 2 && (
        <Button
          variant="primary"
          onClick={handleSubmit}
          loading={loading}
          disabled={loading}
        >
          Оплатить
        </Button>
      )}
    </div>
  );

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={product.title}
      size="medium"
      footer={footer}
    >
      {step === 1 ? renderStepOne() : renderStepTwo()}
    </Modal>
  );
};

export default ZoomPurchaseModal;
