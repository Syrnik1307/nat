/**
 * Finance API service functions
 */
import { apiClient } from './apiService';

// =====================
// Finance API
// =====================

/**
 * Get all wallets (teacher view)
 */
export const getFinanceWallets = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.group_id) queryParams.append('group_id', params.group_id);
  if (params.search) queryParams.append('search', params.search);
  if (params.status) queryParams.append('status', params.status); // ok, low, debt
  const query = queryParams.toString();
  return apiClient.get(`/finance/wallets/${query ? '?' + query : ''}`);
};

/**
 * Get single wallet details
 */
export const getFinanceWallet = (walletId) => {
  return apiClient.get(`/finance/wallets/${walletId}/`);
};

/**
 * Create wallet for student
 */
export const createFinanceWallet = (data) => {
  return apiClient.post('/finance/wallets/', data);
};

/**
 * Update wallet (price, debt limit, notes)
 */
export const updateFinanceWallet = (walletId, data) => {
  return apiClient.patch(`/finance/wallets/${walletId}/`, data);
};

/**
 * Deposit money to wallet
 */
export const depositToWallet = (walletId, amount, description = '') => {
  return apiClient.post(`/finance/wallets/${walletId}/deposit/`, {
    amount: String(amount),
    description
  });
};

/**
 * Charge lesson from wallet
 */
export const chargeFromWallet = (walletId, lessonId, overridePrice = null, description = '') => {
  const data = { lesson_id: lessonId, description };
  if (overridePrice !== null) {
    data.override_price = String(overridePrice);
  }
  return apiClient.post(`/finance/wallets/${walletId}/charge/`, data);
};

/**
 * Adjust wallet balance (manual correction)
 */
export const adjustWalletBalance = (walletId, amount, description) => {
  return apiClient.post(`/finance/wallets/${walletId}/adjust/`, {
    amount: String(amount),
    description
  });
};

/**
 * Refund lesson charge
 */
export const refundFromWallet = (walletId, lessonId, description = '') => {
  return apiClient.post(`/finance/wallets/${walletId}/refund/`, {
    lesson_id: lessonId,
    description
  });
};

/**
 * Get wallet transaction history
 */
export const getWalletTransactions = (walletId, limit = 100, offset = 0) => {
  return apiClient.get(`/finance/wallets/${walletId}/transactions/?limit=${limit}&offset=${offset}`);
};

/**
 * Get student's own balance (student view)
 */
export const getMyBalance = () => {
  return apiClient.get('/finance/my-balance/');
};

/**
 * Get finance dashboard stats (teacher view)
 */
export const getFinanceDashboard = () => {
  return apiClient.get('/finance/dashboard/');
};
