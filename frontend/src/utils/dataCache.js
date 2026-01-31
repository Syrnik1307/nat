/**
 * Smart Data Cache for API responses with REQUEST DEDUPLICATION
 * - Reduces redundant API calls when navigating between pages
 * - DEDUPLICATES parallel requests for the same resource
 * - Cache expires after TTL (default 30 seconds)
 */

const DEFAULT_TTL = 30 * 1000; // 30 seconds
const cache = new Map();

// In-flight requests map for deduplication
// When multiple components request the same data simultaneously,
// only ONE request is made and the promise is shared
const inFlight = new Map();

/**
 * Get cached data or fetch new WITH REQUEST DEDUPLICATION
 * @param {string} key - Cache key
 * @param {Function} fetcher - Async function that returns data
 * @param {number} ttl - Time to live in ms
 * @returns {Promise<any>} - Cached or fresh data
 */
export const getCached = async (key, fetcher, ttl = DEFAULT_TTL) => {
  const now = Date.now();
  const cached = cache.get(key);
  
  // Return cached data if fresh
  if (cached && (now - cached.timestamp) < ttl) {
    return cached.data;
  }
  
  // DEDUPLICATION: If request is already in flight, wait for it
  if (inFlight.has(key)) {
    return inFlight.get(key);
  }
  
  // Create new request promise and store it
  const promise = (async () => {
    try {
      const data = await fetcher();
      cache.set(key, { data, timestamp: Date.now() });
      return data;
    } finally {
      // Remove from in-flight when done (success or error)
      inFlight.delete(key);
    }
  })();
  
  inFlight.set(key, promise);
  return promise;
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
