import React from 'react';
import './SubscriptionBanner.css';

const SubscriptionBanner = ({ subscription, onPayClick }) => {
  if (!subscription) return null;

  const isActive = subscription.status === 'active' && new Date(subscription.expires_at) > new Date();
  
  if (isActive) return null;

  const daysLeft = subscription.expires_at 
    ? Math.ceil((new Date(subscription.expires_at) - new Date()) / (1000 * 60 * 60 * 24))
    : 0;

  const isExpired = daysLeft <= 0;
  const isExpiringSoon = !isExpired && daysLeft <= 7;
  const isPending = subscription.status === 'pending';

  return (
    <div className={`subscription-banner ${isExpired || isPending ? 'expired' : isExpiringSoon ? 'warning' : ''}`}>
      <div className="banner-content">
        <div className="banner-icon">
          {isExpired || isPending ? '!' : '⭕'}
        </div>
        <div className="banner-text">
          {isPending ? (
            <>
              <strong>Подписка не оплачена</strong>
              <p>Для запуска занятий через Zoom необходимо оформить подписку. После оплаты вы получите доступ ко всем функциям.</p>
            </>
          ) : isExpired ? (
            <>
              <strong>Подписка истекла</strong>
              <p>Доступ к урокам, записям и другим функциям ограничен. Оплатите подписку для продолжения работы.</p>
            </>
          ) : subscription.status === 'cancelled' ? (
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
          <button className="pay-button" onClick={onPayClick}>
            💳 Оплатить подписку
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionBanner;
