/**
 * ПРИМЕР: Использование feature flags во фронтенде
 */
import React from 'react';
import { featureFlags } from '../config/featureFlags';

function LessonPage({ lesson }) {
  // Проверяем, включена ли фича
  const showOfflineDownload = featureFlags.isEnabled('pwaOffline');
  const showMobileMoney = featureFlags.isEnabled('mobileMoney');
  const isAfrica = featureFlags.isAfricaRegion();
  
  return (
    <div>
      <h1>{lesson.title}</h1>
      
      {/* Видео - показываем разные качества */}
      <VideoPlayer 
        lesson={lesson}
        defaultQuality={isAfrica ? '360p' : '720p'}
        showAdaptive={featureFlags.isEnabled('adaptiveVideo')}
      />
      
      {/* Кнопка скачать - ТОЛЬКО если PWA включен */}
      {showOfflineDownload && (
        <button onClick={() => downloadForOffline(lesson)}>
          📥 Скачать для offline
        </button>
      )}
      
      {/* Способы оплаты - разные для регионов */}
      <PaymentMethods>
        {/* YooKassa - только Россия */}
        {featureFlags.isEnabled('yookassaPayments') && (
          <YooKassaButton />
        )}
        
        {/* Mobile Money - только Африка */}
        {showMobileMoney && (
          <MobileMoneyButton />
        )}
      </PaymentMethods>
      
      {/* Уведомления - разные каналы */}
      {featureFlags.isEnabled('smsNotifications') ? (
        <SMSNotificationSettings />
      ) : (
        <EmailNotificationSettings />
      )}
    </div>
  );
}

// HOC для защиты целых страниц feature flag'ом
export function withFeatureFlag(FeatureName, Component) {
  return function WrappedComponent(props) {
    if (!featureFlags.isEnabled(FeatureName)) {
      return <div>Feature not available</div>;
    }
    return <Component {...props} />;
  };
}

// Пример защищенного компонента
const OfflineDownloadPage = withFeatureFlag('pwaOffline', () => {
  return <div>Offline Downloads Manager</div>;
});

export default LessonPage;
