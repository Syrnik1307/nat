/**
 * Environment Banner - показывает в каком окружении сидишь
 * ТОЛЬКО на staging, в проде не показывается
 */
import React from 'react';
import { featureFlags } from '../config/featureFlags';
import './EnvironmentBanner.css';

function EnvironmentBanner() {
  const env = process.env.REACT_APP_ENV || 'development';
  
  // В проде не показываем banner
  if (env === 'production_russia' || env === 'production_africa') {
    return null;
  }
  
  const bannerConfig = {
    development: {
      color: '#10B981', // зеленый
      text: '🔧 ЛОКАЛЬНАЯ РАЗРАБОТКА',
      desc: 'localhost:3000'
    },
    staging: {
      color: '#F59E0B', // оранжевый
      text: '🧪 ТЕСТОВЫЙ СЕРВЕР (STAGING)',
      desc: 'lectiospace.online - не для пользователей!'
    }
  };
  
  const config = bannerConfig[env] || bannerConfig.staging;
  
  return (
    <div 
      className="environment-banner" 
      style={{ backgroundColor: config.color }}
    >
      <div className="environment-banner-content">
        <span className="environment-banner-text">{config.text}</span>
        <span className="environment-banner-desc">{config.desc}</span>
        
        {/* Показываем активные feature flags */}
        {env === 'staging' && (
          <div className="environment-banner-flags">
            Активные фичи: 
            {featureFlags.isEnabled('pwaOffline') && ' PWA'}
            {featureFlags.isEnabled('mobileMoney') && ' Mobile$'}
            {featureFlags.isEnabled('multilingual') && ' i18n'}
          </div>
        )}
      </div>
    </div>
  );
}

export default EnvironmentBanner;
