import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import './SubscriptionBanner.css';

/* =====================================================
   SVG ICONS
   ===================================================== */

const IconAlertTriangle = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
    <line x1="12" x2="12" y1="9" y2="13"/>
    <line x1="12" x2="12.01" y1="17" y2="17"/>
  </svg>
);

const IconClock = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12,6 12,12 16,14"/>
  </svg>
);

const IconCreditCard = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect width="20" height="14" x="2" y="5" rx="2"/>
    <line x1="2" x2="22" y1="10" y2="10"/>
  </svg>
);

const IconLock = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
  </svg>
);

/* =====================================================
   SUBSCRIPTION BANNER COMPONENT
   ===================================================== */

const SubscriptionBanner = ({ subscription: propSubscription, onPayClick }) => {
  const navigate = useNavigate();
  const { subscription: authSubscription, role } = useAuth();
  
  // Используем переданную подписку или из контекста
  const subscription = propSubscription || authSubscription;
  
  // Показываем только для учителей
  if (role !== 'teacher') return null;
  if (!subscription) return null;

  const isActive = subscription.status === 'active' && new Date(subscription.expires_at) > new Date();
  
  // Если подписка активна - ничего не показываем
  if (isActive) return null;

  const daysLeft = subscription.expires_at 
    ? Math.ceil((new Date(subscription.expires_at) - new Date()) / (1000 * 60 * 60 * 24))
    : 0;

  const isExpired = daysLeft <= 0;
  const isExpiringSoon = !isExpired && daysLeft <= 7;
  const isPending = subscription.status === 'pending';
  
  // Проверяем заблокирован ли функционал (подписка истекла или pending)
  const isBlocked = isExpired || isPending;

  const handlePayClick = () => {
    if (onPayClick) {
      onPayClick();
    } else {
      navigate('/teacher/subscription');
    }
  };

  // =====================================================
  // БОЛЬШОЙ БЛОКИРУЮЩИЙ БАННЕР для истекшей/pending подписки
  // =====================================================
  if (isBlocked) {
    return (
      <div className="subscription-banner-overlay">
        <div className="subscription-banner-blocked">
          <div className="blocked-banner-icon">
            <IconLock size={48} />
          </div>
          
          <div className="blocked-banner-content">
            <h2 className="blocked-banner-title">
              {isPending ? 'Подписка не оформлена' : 'Подписка истекла'}
            </h2>
            
            <p className="blocked-banner-description">
              {isPending 
                ? 'Для работы с платформой необходимо оформить подписку. После оплаты вы получите полный доступ ко всем функциям: проведению занятий через Zoom, записям уроков, аналитике и управлению учениками.'
                : 'Доступ к основным функциям платформы временно ограничен. Оплатите подписку, чтобы продолжить проводить занятия, управлять записями и работать с учениками.'
              }
            </p>

            <div className="blocked-banner-features">
              <div className="blocked-feature">
                <IconLock size={18} />
                <span>Занятия через Zoom</span>
              </div>
              <div className="blocked-feature">
                <IconLock size={18} />
                <span>Записи уроков</span>
              </div>
              <div className="blocked-feature">
                <IconLock size={18} />
                <span>Загрузка материалов</span>
              </div>
            </div>

            <button className="blocked-banner-pay-btn" onClick={handlePayClick}>
              <IconCreditCard size={20} />
              <span>Оплатить подписку</span>
            </button>

            <p className="blocked-banner-hint">
              Возникли вопросы? Напишите нам в поддержку
            </p>
          </div>
        </div>
      </div>
    );
  }

  // =====================================================
  // Предупреждающий баннер для скоро истекающей подписки
  // =====================================================
  return (
    <div className={`subscription-banner ${isExpiringSoon ? 'warning' : ''}`}>
      <div className="banner-content">
        <div className="banner-icon">
          {isExpiringSoon ? <IconClock size={24} /> : <IconAlertTriangle size={24} />}
        </div>
        <div className="banner-text">
          {subscription.status === 'cancelled' ? (
            <>
              <strong>Подписка отменена</strong>
              <p>Доступ сохранится до {new Date(subscription.expires_at).toLocaleDateString('ru-RU')}. Продлите подписку для дальнейшей работы.</p>
            </>
          ) : (
            <>
              <strong>Подписка скоро истечёт</strong>
              <p>Осталось {daysLeft} {daysLeft === 1 ? 'день' : daysLeft < 5 ? 'дня' : 'дней'}. Продлите подписку чтобы не потерять доступ.</p>
            </>
          )}
        </div>
        <div className="banner-actions">
          <button className="pay-button" onClick={handlePayClick}>
            <IconCreditCard size={16} />
            <span>Оплатить</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionBanner;
