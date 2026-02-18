/**
 * Image Preloader Utility
 * Preloads images for smoother transitions in homework questions
 */

// Кеш загруженных изображений
const preloadedImages = new Set();

// Очередь preload задач (чтобы не создавать десятки параллельных запросов)
const preloadQueue = [];
const queuedImages = new Set();
let activeWorkers = 0;
const DEFAULT_CONCURRENCY = 2;

// Нормализация URL для картинок (включая Google Drive)
const normalizeImageUrl = (url) => {
  if (!url) return '';
  
  // blob/data URL — не трогаем
  if (url.startsWith('blob:') || url.startsWith('data:')) {
    return url;
  }
  
  // Конвертация Google Drive ссылок
  if (url.includes('drive.google.com')) {
    let fileId = null;
    
    const ucMatch = url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
    if (ucMatch) fileId = ucMatch[1];
    
    const fileMatch = url.match(/\/file\/d\/([a-zA-Z0-9_-]+)/);
    if (fileMatch) fileId = fileMatch[1];
    
    const openMatch = url.match(/\/open\?id=([a-zA-Z0-9_-]+)/);
    if (openMatch) fileId = openMatch[1];
    
    if (fileId) {
      return `https://lh3.googleusercontent.com/d/${fileId}`;
    }
  }
  
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  
  if (url.startsWith('/')) {
    return url;
  }
  
  return `/media/${url}`;
};

/**
 * Preload одного изображения
 * @param {string} url - URL изображения
 * @returns {Promise<void>}
 */
export const preloadImage = (url) => {
  const normalized = normalizeImageUrl(url);
  if (!normalized || preloadedImages.has(normalized)) {
    return Promise.resolve();
  }
  
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      preloadedImages.add(normalized);
      resolve();
    };
    img.onerror = () => {
      // Не добавляем в кеш при ошибке, чтобы можно было повторить
      resolve();
    };
    img.src = normalized;
  });
};

/**
 * Запустить обработку очереди preload (с ограничением конкурентности)
 */
const schedulePump = (target) => {
  if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
    requestIdleCallback(() => pumpQueue(target), { timeout: 1500 });
  } else {
    setTimeout(() => pumpQueue(target), 50);
  }
};

const pumpQueue = (concurrency = DEFAULT_CONCURRENCY) => {
  const target = Math.max(1, Math.min(4, Number(concurrency) || DEFAULT_CONCURRENCY));
  if (activeWorkers >= target) return;

  const startWorkers = () => {
    if (activeWorkers >= target) return;
    const nextUrl = preloadQueue.shift();
    if (!nextUrl) return;
    queuedImages.delete(nextUrl);

    activeWorkers += 1;
    preloadImage(nextUrl)
      .catch(() => {})
      .finally(() => {
        activeWorkers -= 1;
        if (preloadQueue.length > 0) {
          schedulePump(target);
        }
      });

    // Добираем воркеры до лимита
    startWorkers();
  };

  startWorkers();
};

/**
 * Preload множества изображений (fire and forget) с троттлингом
 * @param {string[]} urls - массив URL
 * @param {{ concurrency?: number, max?: number }} [options]
 */
export const preloadImages = (urls, options = {}) => {
  if (typeof window === 'undefined') return;
  if (!Array.isArray(urls) || urls.length === 0) return;

  const max = Number.isFinite(options.max) ? Math.max(0, options.max) : null;
  const list = max ? urls.slice(0, max) : urls;

  list.forEach((url) => {
    const normalized = normalizeImageUrl(url);
    if (!normalized) return;
    if (preloadedImages.has(normalized)) return;
    if (queuedImages.has(normalized)) return;
    preloadQueue.push(normalized);
    queuedImages.add(normalized);
  });

  // Стартуем очередь в idle, чтобы не мешать основному рендеру/загрузке
  const concurrency = options.concurrency;
  if ('requestIdleCallback' in window) {
    requestIdleCallback(() => pumpQueue(concurrency), { timeout: 1500 });
  } else {
    setTimeout(() => pumpQueue(concurrency), 50);
  }
};

/**
 * Извлечь все URL изображений из вопросов ДЗ
 * @param {Array} questions - массив вопросов
 * @returns {string[]} - массив URL
 */
export const extractQuestionImages = (questions) => {
  if (!Array.isArray(questions)) return [];
  
  const urls = [];
  questions.forEach((q) => {
    if (q.config?.imageUrl) {
      urls.push(q.config.imageUrl);
    }
    if (q.config?.explanationImageUrl) {
      urls.push(q.config.explanationImageUrl);
    }
    // Для HOTSPOT и других типов с изображениями
    if (q.config?.backgroundImage) {
      urls.push(q.config.backgroundImage);
    }
  });
  
  return urls;
};

/**
 * Preload изображений соседних вопросов (prev, current, next)
 * @param {Array} questions - все вопросы
 * @param {number} currentIndex - текущий индекс
 */
export const preloadAdjacentQuestionImages = (questions, currentIndex) => {
  if (!Array.isArray(questions) || questions.length === 0) return;
  
  const indicesToPreload = [
    currentIndex - 1,
    currentIndex + 1,
    currentIndex + 2, // Preload на шаг вперед
  ].filter((i) => i >= 0 && i < questions.length);
  
  const urls = [];
  indicesToPreload.forEach((i) => {
    const q = questions[i];
    if (q?.config?.imageUrl) urls.push(q.config.imageUrl);
    if (q?.config?.explanationImageUrl) urls.push(q.config.explanationImageUrl);
  });

  // Для соседних вопросов держим конкурентность низкой,
  // чтобы не забивать сеть и не мешать текущей картинке.
  preloadImages(urls, { concurrency: 1, max: 4 });
};

/**
 * Проверить, загружено ли изображение
 * @param {string} url 
 * @returns {boolean}
 */
export const isImagePreloaded = (url) => {
  const normalized = normalizeImageUrl(url);
  return preloadedImages.has(normalized);
};

const imagePreloaderApi = {
  preloadImage,
  preloadImages,
  extractQuestionImages,
  preloadAdjacentQuestionImages,
  isImagePreloaded,
};

export default imagePreloaderApi;
