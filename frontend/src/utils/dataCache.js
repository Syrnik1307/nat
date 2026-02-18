/**
 * Smart Data Cache for API responses with STALE-WHILE-REVALIDATE
 * - Reduces redundant API calls when navigating between pages
 * - DEDUPLICATES parallel requests for the same resource
 * - STALE-WHILE-REVALIDATE: Shows cached data instantly, refreshes in background
 * - Configurable TTL per data type (static vs dynamic)
 */

// TTL presets for different data types
export const TTL = {
  INSTANT: 0,              // Always fetch
  SHORT: 30 * 1000,        // 30s - dynamic data (lessons for today)
  MEDIUM: 2 * 60 * 1000,   // 2min - semi-static (groups, homework list)
  LONG: 5 * 60 * 1000,     // 5min - static (user profile, stats)
  STATIC: 10 * 60 * 1000,  // 10min - rarely changes
};

const DEFAULT_TTL = TTL.SHORT;
const STALE_TTL_MULTIPLIER = 3; // Data is considered stale but usable for 3x TTL

const cache = new Map();

// In-flight requests map for deduplication
// When multiple components request the same data simultaneously,
// only ONE request is made and the promise is shared
const inFlight = new Map();

// Subscribers for cache updates (for Stale-While-Revalidate)
const subscribers = new Map();

/**
 * Subscribe to cache updates for a key
 * @param {string} key - Cache key
 * @param {Function} callback - Called when cache updates
 * @returns {Function} - Unsubscribe function
 */
export const subscribe = (key, callback) => {
  if (!subscribers.has(key)) {
    subscribers.set(key, new Set());
  }
  subscribers.get(key).add(callback);
  return () => subscribers.get(key)?.delete(callback);
};

/**
 * Notify subscribers of cache update
 */
const notifySubscribers = (key, data) => {
  subscribers.get(key)?.forEach(cb => {
    try { cb(data); } catch (_) { /* ignore */ }
  });
};

/**
 * Get cached data with STALE-WHILE-REVALIDATE pattern
 * @param {string} key - Cache key
 * @param {Function} fetcher - Async function that returns data
 * @param {number} ttl - Time to live in ms (use TTL.* constants)
 * @param {Object} options - Options
 * @param {boolean} options.forceRefresh - Ignore cache, always fetch
 * @param {boolean} options.backgroundOnly - Only refresh in background if stale
 * @returns {Promise<any>} - Cached or fresh data
 */
export const getCached = async (key, fetcher, ttl = DEFAULT_TTL, options = {}) => {
  const { forceRefresh = false, backgroundOnly = false } = options;
  const now = Date.now();
  const cached = cache.get(key);
  
  // Check if data is fresh (within TTL)
  const isFresh = cached && (now - cached.timestamp) < ttl;
  // Check if data is stale but still usable (within extended TTL)
  const isStale = cached && !isFresh && (now - cached.timestamp) < (ttl * STALE_TTL_MULTIPLIER);
  
  // If fresh and not forcing refresh, return immediately
  if (isFresh && !forceRefresh) {
    return cached.data;
  }
  
  // STALE-WHILE-REVALIDATE: Return stale data immediately, refresh in background
  if (isStale && !forceRefresh) {
    // Trigger background refresh (fire-and-forget)
    if (!inFlight.has(key)) {
      refreshInBackground(key, fetcher);
    }
    return cached.data;
  }
  
  // If backgroundOnly is set and we have stale data, just trigger refresh
  if (backgroundOnly && cached) {
    if (!inFlight.has(key)) {
      refreshInBackground(key, fetcher);
    }
    return cached.data;
  }
  
  // DEDUPLICATION: If request is already in flight, wait for it
  if (inFlight.has(key)) {
    // If we have stale data, return it while waiting
    if (cached) {
      return cached.data;
    }
    return inFlight.get(key);
  }
  
  // Create new request promise and store it
  const promise = (async () => {
    try {
      const data = await fetcher();
      cache.set(key, { data, timestamp: Date.now() });
      notifySubscribers(key, data);
      return data;
    } finally {
      // Remove from in-flight when done (success or error)
      inFlight.delete(key);
    }
  })();
  
  inFlight.set(key, promise);
  
  // If we have old cached data, return it immediately while promise resolves
  if (cached) {
    // Still await the promise to update cache, but return old data
    promise.catch(() => {}); // Prevent unhandled rejection
    return cached.data;
  }
  
  return promise;
};

/**
 * Refresh cache in background without blocking
 */
const refreshInBackground = (key, fetcher) => {
  const promise = (async () => {
    try {
      const data = await fetcher();
      cache.set(key, { data, timestamp: Date.now() });
      notifySubscribers(key, data);
      return data;
    } finally {
      inFlight.delete(key);
    }
  })();
  inFlight.set(key, promise);
  // Fire and forget - catch errors to prevent unhandled rejection
  promise.catch(() => {});
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

/**
 * Get cached data synchronously (for immediate render)
 * Returns undefined if not cached
 * @param {string} key - Cache key
 * @returns {any|undefined}
 */
export const getCachedSync = (key) => {
  const cached = cache.get(key);
  return cached?.data;
};

/**
 * Set data directly into cache (for optimistic updates)
 * @param {string} key - Cache key
 * @param {any} data - Data to cache
 */
export const setCache = (key, data) => {
  cache.set(key, { data, timestamp: Date.now() });
  notifySubscribers(key, data);
};

export default {
  getCached,
  getCachedSync,
  setCache,
  invalidateCache,
  prefetch,
  isCached,
  subscribe,
  TTL,
};
