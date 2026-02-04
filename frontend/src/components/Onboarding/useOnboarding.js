import { useEffect, useRef, useCallback, useState } from 'react';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import './onboarding.css';

const STORAGE_PREFIX = 'lectio_onboarding_';
const TOUR_VERSION = 'v1'; // Инкрементировать при изменении шагов

// Глобальный трекер запущенных туров в этой сессии (по ключу)
const startedTours = new Set();

/**
 * Проверка, нужно ли показать тур (только после регистрации)
 * Возвращает true только если пользователь только что зарегистрировался
 */
const shouldShowTour = (userId) => {
  if (!userId) return false;
  try {
    return localStorage.getItem(`lectio_show_tour_${userId}`) === 'true';
  } catch {
    return false;
  }
};

/**
 * Сбрасывает флаг "нужен тур" после его показа
 */
const clearShowTourFlag = (userId) => {
  if (!userId) return;
  try {
    localStorage.removeItem(`lectio_show_tour_${userId}`);
  } catch {
    // ignore
  }
};

/**
 * Хук для управления онбординг-туром
 * @param {string} tourKey - Уникальный ключ тура (teacher, student)
 * @param {Array} steps - Массив шагов тура
 * @param {Object} options - Дополнительные опции driver.js
 * @param {string} options.userId - ID пользователя для привязки прогресса
 */
export const useOnboarding = (tourKey, steps, options = {}) => {
  const driverRef = useRef(null);
  const { userId } = options;
  // Ключ включает userId чтобы каждый пользователь имел свой прогресс
  const storageKey = userId 
    ? `${STORAGE_PREFIX}${tourKey}_${userId}_${TOUR_VERSION}`
    : `${STORAGE_PREFIX}${tourKey}_${TOUR_VERSION}`;
  
  // Инициализируем state из localStorage
  const [completed, setCompleted] = useState(() => {
    const value = localStorage.getItem(storageKey);
    console.log(`[Onboarding:${tourKey}] Init - storageKey=${storageKey}, value=${value}`);
    return value === 'true';
  });

  const markCompleted = useCallback(() => {
    console.log(`[Onboarding:${tourKey}] Marking completed`);
    localStorage.setItem(storageKey, 'true');
    setCompleted(true);
  }, [storageKey, tourKey]);

  const resetTour = useCallback(() => {
    console.log(`[Onboarding:${tourKey}] Resetting tour`);
    localStorage.removeItem(storageKey);
    setCompleted(false);
    startedTours.delete(tourKey); // Разрешаем повторный запуск
  }, [storageKey, tourKey]);

  const startTour = useCallback(() => {
    console.log(`[Onboarding:${tourKey}] startTour called, steps count:`, steps?.length);
    
    if (!steps || steps.length === 0) {
      console.warn(`[Onboarding:${tourKey}] No steps provided`);
      return;
    }

    // Проверяем, что все элементы существуют в DOM
    const validSteps = steps.filter(step => {
      if (!step.element) return true; // Шаг без element (intro)
      const el = document.querySelector(step.element);
      if (!el) {
        console.warn(`[Onboarding:${tourKey}] Element not found:`, step.element);
      }
      return el || !step.element;
    });

    console.log(`[Onboarding:${tourKey}] Valid steps:`, validSteps.length, 'of', steps.length);

    if (validSteps.length === 0) {
      console.warn(`[Onboarding:${tourKey}] No valid steps found in DOM`);
      return;
    }

    // Уничтожаем предыдущий инстанс если есть
    if (driverRef.current) {
      try {
        driverRef.current.destroy();
      } catch (e) {
        // ignore
      }
    }

    console.log(`[Onboarding:${tourKey}] Creating driver instance...`);
    
    driverRef.current = driver({
      showProgress: true,
      showButtons: ['next', 'previous', 'close'],
      popoverClass: 'lectio-tour-popover',
      overlayColor: 'rgba(15, 23, 42, 0.75)',
      stagePadding: 10,
      stageRadius: 12,
      popoverOffset: 12,
      smoothScroll: true,
      allowClose: true,
      doneBtnText: 'Готово',
      closeBtnText: 'Пропустить',
      nextBtnText: 'Далее',
      prevBtnText: 'Назад',
      progressText: '{{current}} из {{total}}',
      ...options,
      steps: validSteps,
      onDestroyed: () => {
        console.log(`[Onboarding:${tourKey}] Tour destroyed, marking complete`);
        markCompleted();
        options.onComplete?.();
      },
    });

    console.log(`[Onboarding:${tourKey}] Calling drive()...`);
    driverRef.current.drive();
  }, [steps, options, markCompleted, tourKey]);

  // Автозапуск при первом входе - ТОЛЬКО после регистрации
  useEffect(() => {
    console.log(`[Onboarding:${tourKey}] useEffect - completed=${completed}, hasStarted=${startedTours.has(tourKey)}, stepsLen=${steps?.length}, userId=${userId}`);
    
    // Не запускаем если уже завершён
    if (completed) {
      console.log(`[Onboarding:${tourKey}] Skipping - already completed`);
      return;
    }
    
    // Не запускаем если уже стартовали в этой сессии
    if (startedTours.has(tourKey)) {
      console.log(`[Onboarding:${tourKey}] Skipping - already started this session`);
      return;
    }

    if (!steps || steps.length === 0) {
      console.log(`[Onboarding:${tourKey}] Skipping - no steps`);
      return;
    }
    
    // КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: тур показывается только если пользователь только что зарегистрировался
    // Флаг lectio_show_tour_{userId} устанавливается в auth.js при регистрации
    if (!shouldShowTour(userId)) {
      console.log(`[Onboarding:${tourKey}] Skipping - no show_tour flag (not a new registration)`);
      return;
    }

    console.log(`[Onboarding:${tourKey}] Will auto-start in 2000ms (new user registration detected)`);
    startedTours.add(tourKey); // Помечаем что этот тур стартовали

    // Ждём пока страница полностью загрузится
    const timer = setTimeout(() => {
      console.log(`[Onboarding:${tourKey}] Timer fired, calling startTour()`);
      // Сбрасываем флаг "нужен тур" чтобы не показывать повторно
      clearShowTourFlag(userId);
      startTour();
    }, 2000);

    return () => {
      clearTimeout(timer);
    };
  }, [completed, steps, tourKey, startTour, userId]);

  // Cleanup при размонтировании
  useEffect(() => {
    return () => {
      if (driverRef.current) {
        try {
          driverRef.current.destroy();
        } catch (e) {
          // ignore
        }
      }
    };
  }, []);

  return {
    startTour,
    resetTour,
    isCompleted: completed,
    driverInstance: driverRef.current,
  };
};

export default useOnboarding;
