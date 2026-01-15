/**
 * Simple Data Cache for API responses
 * Reduces redundant API calls when navigating between pages
 * Cache expires after TTL (default 30 seconds)
 */

const DEFAULT_TTL = 30 * 1000; // 30 seconds
const cache = new Map();

/**
 * Get cached data or fetch new
 * @param {string} key - Cache key
 * @param {Function} fetcher - Async function that returns data
 * @param {number} ttl - Time to live in ms
 * @returns {Promise<any>} - Cached or fresh data
 */
export const getCached = async (key, fetcher, ttl = DEFAULT_TTL) => {
  const now = Date.now();
  const cached = cache.get(key);
  
  if (cached && (now - cached.timestamp) < ttl) {
    return cached.data;
  }
  
  // Fetch fresh data
  const data = await fetcher();
  cache.set(key, { data, timestamp: now });
  return data;
};

/**
 * Invalidate cache entry
 * @param {string} key - Cache key or prefix
 */
export const invalidateCache = (key) => {
  if (key) {
    // Если передан ключ - удаляем конкретный или по префиксу
    for (const k of cache.keys()) {
      if (k === key || k.startsWith(key + ':')) {
        cache.delete(k);
      }
    }
  } else {
    cache.clear();
  }
};

/**
 * Prefetch data into cache
 * @param {string} key - Cache key
 * @param {Function} fetcher - Async function
 */
export const prefetch = (key, fetcher) => {
  // Fire and forget - prefetch in background
  getCached(key, fetcher).catch(() => {});
};

/**
 * Check if key is cached and fresh
 * @param {string} key - Cache key
 * @param {number} ttl - Time to live in ms
 * @returns {boolean}
 */
export const isCached = (key, ttl = DEFAULT_TTL) => {
  const cached = cache.get(key);
  if (!cached) return false;
  return (Date.now() - cached.timestamp) < ttl;
};

export default {
  getCached,
  invalidateCache,
  prefetch,
  isCached,
};
