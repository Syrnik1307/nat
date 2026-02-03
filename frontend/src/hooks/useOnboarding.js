/**
 * useOnboarding.js - Хук для автозапуска Driver.js туров
 * 
 * Функциональность:
 * - Автозапуск тура при первом входе пользователя
 * - Сохранение состояния в localStorage с версионированием
 * - Поддержка разных туров для разных страниц
 * - Фильтрация шагов по существующим элементам
 * - Ручной запуск/сброс тура
 * 
 * Версия: 3.0
 */

import { useEffect, useRef, useCallback } from 'react';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';

// Версия тура - инкрементируйте при существенных изменениях
const TOUR_VERSION = 'v3';

// Задержка перед автозапуском (ms)
const STARTUP_DELAY = 1500;

// Трекинг сессии для предотвращения повторных запусков
const sessionTriggered = new Set();

/**
 * Генерация ключа localStorage
 */
const getStorageKey = (tourName, userId) => {
  return `lectio_tour_${tourName}_${userId || 'guest'}_${TOUR_VERSION}`;
};

/**
 * Проверка существования элемента в DOM
 */
const elementExists = (selector) => {
  if (!selector) return true; // Шаги без элемента (intro/outro) всегда валидны
  try {
    return document.querySelector(selector) !== null;
  } catch {
    return false;
  }
};

/**
 * Фильтрация шагов - оставляем только те, чьи элементы существуют
 */
const filterValidSteps = (steps) => {
  return steps.filter(step => {
    if (!step.element) return true; // intro/outro шаги
    return elementExists(step.element);
  });
};

/**
 * Создание экземпляра Driver.js с кастомными стилями
 */
const createDriver = (onComplete) => {
  return driver({
    showProgress: true,
    animate: true,
    smoothScroll: true,
    allowClose: true,
    stagePadding: 10,
    stageRadius: 8,
    
    // Кнопки
    nextBtnText: 'Далее',
    prevBtnText: 'Назад',
    doneBtnText: 'Готово',
    
    // Прогресс
    progressText: '{{current}} из {{total}}',
    
    // Стили popover
    popoverClass: 'lectio-tour-popover',
    
    // Callbacks
    onDestroyed: () => {
      if (onComplete) onComplete();
    },
  });
};

/**
 * Основной хук для автозапуска тура
 * 
 * @param {string} tourName - Имя тура (teacher, student, homeworkConstructor, etc.)
 * @param {string|number} userId - ID пользователя
 * @param {Array} steps - Массив шагов тура
 * @param {Object} options - Дополнительные опции
 * @param {boolean} options.autoStart - Автозапуск (default: true)
 * @param {number} options.delay - Задержка перед запуском (default: 1500)
 * @param {Function} options.onComplete - Callback при завершении
 */
export const useOnboarding = (tourName, userId, steps, options = {}) => {
  const {
    autoStart = true,
    delay = STARTUP_DELAY,
    onComplete,
  } = options;

  const driverRef = useRef(null);
  const hasTriggeredRef = useRef(false);

  const storageKey = getStorageKey(tourName, userId);
  const sessionKey = `${tourName}_${userId}`;

  // Проверка, был ли тур уже пройден
  const isCompleted = useCallback(() => {
    try {
      return localStorage.getItem(storageKey) === 'completed';
    } catch {
      return false;
    }
  }, [storageKey]);

  // Отметка тура как пройденного
  const markCompleted = useCallback(() => {
    try {
      localStorage.setItem(storageKey, 'completed');
    } catch {
      console.warn('localStorage недоступен');
    }
  }, [storageKey]);

  // Сброс тура (для повторного просмотра)
  const resetTour = useCallback(() => {
    try {
      localStorage.removeItem(storageKey);
      sessionTriggered.delete(sessionKey);
      hasTriggeredRef.current = false;
    } catch {
      console.warn('localStorage недоступен');
    }
  }, [storageKey, sessionKey]);

  // Запуск тура вручную
  const startTour = useCallback(() => {
    if (!steps || steps.length === 0) {
      console.warn(`[useOnboarding] Нет шагов для тура "${tourName}"`);
      return;
    }

    const validSteps = filterValidSteps(steps);
    
    if (validSteps.length === 0) {
      console.warn(`[useOnboarding] Нет валидных шагов для тура "${tourName}"`);
      return;
    }

    // Уничтожаем предыдущий экземпляр
    if (driverRef.current) {
      try {
        driverRef.current.destroy();
      } catch {}
    }

    // Создаём новый driver
    driverRef.current = createDriver(() => {
      markCompleted();
      if (onComplete) onComplete();
    });

    // Устанавливаем шаги и запускаем
    driverRef.current.setSteps(validSteps);
    driverRef.current.drive();
  }, [steps, tourName, markCompleted, onComplete]);

  // Автозапуск при монтировании
  useEffect(() => {
    if (!autoStart) return;
    if (!userId) return;
    if (!steps || steps.length === 0) return;
    if (hasTriggeredRef.current) return;
    if (sessionTriggered.has(sessionKey)) return;
    if (isCompleted()) return;

    hasTriggeredRef.current = true;
    sessionTriggered.add(sessionKey);

    const timer = setTimeout(() => {
      // Проверяем ещё раз после задержки
      if (isCompleted()) return;
      
      startTour();
    }, delay);

    return () => clearTimeout(timer);
  }, [autoStart, userId, steps, sessionKey, delay, isCompleted, startTour]);

  // Cleanup при размонтировании
  useEffect(() => {
    return () => {
      if (driverRef.current) {
        try {
          driverRef.current.destroy();
        } catch {}
      }
    };
  }, []);

  return {
    startTour,
    resetTour,
    isCompleted: isCompleted(),
  };
};

/**
 * Хук для ручного управления туром (без автозапуска)
 */
export const useManualTour = (tourName, userId, steps) => {
  return useOnboarding(tourName, userId, steps, { autoStart: false });
};

/**
 * Хук-обёртка для Dashboard туров
 * Автоматически определяет шаги по роли
 */
export const useDashboardTour = (role, userId) => {
  // Динамический импорт шагов
  const getSteps = useCallback(() => {
    try {
      const config = require('../tourConfig').default;
      return role === 'teacher' ? config.teacher : config.student;
    } catch {
      return [];
    }
  }, [role]);

  return useOnboarding(role, userId, getSteps());
};

/**
 * Хук для тура конструктора ДЗ
 */
export const useHomeworkConstructorTour = (userId) => {
  const getSteps = useCallback(() => {
    try {
      return require('../tourConfig').homeworkConstructorSteps;
    } catch {
      return [];
    }
  }, []);

  return useOnboarding('homeworkConstructor', userId, getSteps(), {
    autoStart: false, // Вручную запускать через кнопку "Помощь"
  });
};

/**
 * Хук для тура страницы записей
 */
export const useRecordingsTour = (userId) => {
  const getSteps = useCallback(() => {
    try {
      return require('../tourConfig').recordingsSteps;
    } catch {
      return [];
    }
  }, []);

  return useOnboarding('recordings', userId, getSteps(), {
    autoStart: false,
  });
};

/**
 * Хук для тура профиля
 */
export const useProfileTour = (userId) => {
  const getSteps = useCallback(() => {
    try {
      return require('../tourConfig').profileSteps;
    } catch {
      return [];
    }
  }, []);

  return useOnboarding('profile', userId, getSteps(), {
    autoStart: false,
  });
};

/**
 * Хук для тура аналитики
 */
export const useAnalyticsTour = (userId) => {
  const getSteps = useCallback(() => {
    try {
      return require('../tourConfig').analyticsSteps;
    } catch {
      return [];
    }
  }, []);

  return useOnboarding('analytics', userId, getSteps(), {
    autoStart: false,
  });
};

// Экспорт по умолчанию
export default useOnboarding;

// Экспорт для обратной совместимости с useAppTour
export const useAppTour = useDashboardTour;
