/**
 * Feature Flags для фронтенда
 * Синхронизированы с бэкендом
 */

const ENV = process.env.REACT_APP_ENV || 'development';

// Конфигурация по окружениям
const configs = {
  development: {
    apiUrl: 'http://127.0.0.1:8000',
    region: 'russia',
    features: {
      africaMarket: true,
      pwaOffline: true,
      mobileMoney: false,
      smsNotifications: false,
      multilingual: true,
      adaptiveVideo: true,
      yookassaPayments: true,
      telegramSupport: true,
    },
    currency: 'RUB',
    language: 'ru',
  },
  
  staging: {
    apiUrl: 'https://stage.lectiospace.ru',
    region: 'africa',
    features: {
      africaMarket: true,
      pwaOffline: true,
      mobileMoney: true,
      smsNotifications: true,
      multilingual: true,
      adaptiveVideo: true,
      yookassaPayments: true,
      telegramSupport: true,
    },
    currency: 'USD',
    language: 'en',
  },
  
  production_russia: {
    apiUrl: 'https://lectiospace.ru',
    region: 'russia',
    features: {
      africaMarket: false,
      pwaOffline: false,
      mobileMoney: false,
      smsNotifications: false,
      multilingual: false,
      adaptiveVideo: false,
      yookassaPayments: true,
      telegramSupport: true,
    },
    currency: 'RUB',
    language: 'ru',
  },
  
  production_africa: {
    apiUrl: 'https://teachpanel.com',
    region: 'africa',
    features: {
      africaMarket: true,
      pwaOffline: true,
      mobileMoney: true,
      smsNotifications: true,
      multilingual: true,
      adaptiveVideo: true,
      yookassaPayments: false,
      telegramSupport: false,
    },
    currency: 'USD',
    language: 'en',
  },
};

const config = configs[ENV];

export const featureFlags = {
  /**
   * Проверить, включена ли фича
   */
  isEnabled: (featureName) => {
    return config.features[featureName] || false;
  },
  
  /**
   * Получить текущий регион
   */
  getRegion: () => config.region,
  
  /**
   * Африканский ли регион
   */
  isAfricaRegion: () => config.region === 'africa',
  
  /**
   * Получить валюту
   */
  getCurrency: () => config.currency,
  
  /**
   * Получить язык по умолчанию
   */
  getLanguage: () => config.language,
};

export const apiConfig = {
  baseURL: config.apiUrl,
  region: config.region,
};

// Для отладки
if (ENV === 'development') {
  console.log('🎚️ Feature Flags:', config.features);
  console.log('🌍 Region:', config.region);
}

export default config;
