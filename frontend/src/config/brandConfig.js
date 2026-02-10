/**
 * Brand Configuration
 * 
 * ЕДИНЫЙ ИСТОЧНИК ПРАВДЫ для всего брендинга платформы.
 * 
 * Когда будем делать multi-tenant (разные школы на одном движке),
 * этот файл будет заменён на динамическую загрузку из API:
 *   GET /api/school/config/ → { name, logo, colors, ... }
 * 
 * Пока что — статичный конфиг для Lectio Space.
 * 
 * ПРАВИЛО: Нигде в компонентах НЕ должно быть хардкод строк
 * "Lectio Space", "Lectio", "lectiospace.ru" и т.д.
 * Всё берём из этого файла.
 */

const brandConfig = {
  // === Название платформы ===
  name: 'Lectio Space',
  shortName: 'Lectio',
  nameParts: {
    primary: 'Lectio',    // цветная часть логотипа
    secondary: 'Space',   // серая часть логотипа
  },
  
  // === Описание (для meta tags, PWA) ===
  description: 'Lectio Space - Manage your courses, lessons, and homework',
  
  // === URLs ===
  siteUrl: process.env.REACT_APP_SITE_URL || 'https://lectiospace.ru',
  
  // === Telegram ===
  telegram: {
    botUsername: '@LectioSpaceBot',
    botUrl: 'https://t.me/LectioSpaceBot',
    supportBotUrl: 'https://t.me/help_lectio_space_bot',
    resetDeeplink: 'https://t.me/nat_panelbot?start=reset',
  },

  // === Цвета бренда (должны совпадать с CSS переменными в design-system.css) ===
  colors: {
    primary: '#4F46E5',       // --color-primary (Indigo-600)
    primaryDark: '#4338CA',   // --color-primary-dark (Indigo-700)
    primaryLight: '#818CF8',  // --color-primary-light (Indigo-400)
    secondary: '#94a3b8',     // серый для "Space" в логотипе
  },

  // === Шрифт ===
  fontFamily: "'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif",

  // === PWA ===
  pwa: {
    themeColor: '#3b82f6',
    backgroundColor: '#ffffff',
  },
  
  // === Логотип ===
  logo: {
    // Когда будет multi-tenant, здесь будет URL из API
    // logoUrl: null,  // '/api/school/logo/'
    ariaLabel: 'Lectio Space logo',
  },
};

export default brandConfig;

/**
 * Хелпер для получения display name
 * В multi-tenant будет: school.name
 */
export const getBrandName = () => brandConfig.name;
export const getBrandShortName = () => brandConfig.shortName;
