import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Navigate } from 'react-router-dom';
import {
  login as apiLogin,
  logout as apiLogout,
  verifyToken,
  getAccessToken,
  getCurrentUser,
  setTokens,
  clearTokens,
  apiClient,
} from './apiService';
import { AuthCheckingSkeleton } from './shared/components';

// Утилита: определяет, что мы на домене Ольги
const isOlgaHost = () => {
  const h = window.location.hostname || '';
  return h === 'olga.lectiospace.ru' || h.startsWith('olga.');
};

const AuthContext = createContext(null);

// Decode role from JWT token
const getRoleFromToken = () => {
  const token = getAccessToken();
  if (!token) return null;
  try {
    const part = token.split('.')[1];
    if (!part) return null;
    const base64 = part.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64 + '='.repeat((4 - base64.length % 4) % 4);
    const payload = JSON.parse(atob(padded));
    return payload.role || null;
  } catch {
    return null;
  }
};

export const AuthProvider = ({ children }) => {
  const [accessTokenValid, setAccessTokenValid] = useState(false);
  const [role, setRole] = useState(null); // 'teacher' | 'student' | 'admin'
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [subscription, setSubscription] = useState(null);

  // Захват referral/UTM меток из URL при первом заходе
  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        const url = new URL(window.location.href);
        const params = url.searchParams;
        const ref = params.get('ref');
        const utm_source = params.get('utm_source');
        const utm_medium = params.get('utm_medium');
        const utm_campaign = params.get('utm_campaign');
        const channel = params.get('channel');
        if (ref) localStorage.setItem('tp_referral_code', ref);
        if (utm_source) localStorage.setItem('tp_utm_source', utm_source);
        if (utm_medium) localStorage.setItem('tp_utm_medium', utm_medium);
        if (utm_campaign) localStorage.setItem('tp_utm_campaign', utm_campaign);
        if (channel) localStorage.setItem('tp_channel', channel);
        // Дополнительно сохраним источник URL как ref_url и анонимный cookie_id
        // Сохраняем ref_url только если есть ref параметр
        if (ref) {
          localStorage.setItem('tp_ref_url', url.href);
        }
        if (!localStorage.getItem('tp_cookie_id')) {
          const rand = Math.random().toString(36).slice(2) + Date.now().toString(36);
          localStorage.setItem('tp_cookie_id', rand);
        }
      }
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn('Failed to capture referral params:', e);
    }
  }, []);

  const loadSubscription = useCallback(async () => {
    try {
      const res = await apiClient.get('subscription/');
      setSubscription(res.data);
      return res.data;
    } catch (err) {
      console.error('Не удалось загрузить подписку', err);
      setSubscription(null);
      return null;
    }
  }, []);

  const loadUser = useCallback(async () => {
    try {
      // Загружаем user и подписку параллельно для ускорения
      const userPromise = getCurrentUser();
      
      const res = await userPromise;
      setUser(res.data);
      if (res.data?.role) {
        setRole(res.data.role);
      }
      // Загружаем подписку для teacher в фоне (не блокируем UI)
      if (res.data?.role === 'teacher') {
        loadSubscription(); // Без await - грузим в фоне
      }
      return res.data;
    } catch (err) {
      if (err?.response?.status === 401) {
        setAccessTokenValid(false);
        setRole(null);
      }
      console.error('Ошибка загрузки профиля', err);
      setUser(null);
      return null;
    }
  }, [loadSubscription]);

  const check = useCallback(async () => {
    const path = typeof window !== 'undefined' ? window.location.pathname : '';

    // Если мы на странице авторизации, всегда считаем пользователя неавторизованным:
    // - жёстко чистим токены
    // - НЕ пытаемся авто-логиниться через refresh
    if (path.startsWith('/auth')) {
      try {
        apiLogout();
      } catch (_) {}
      clearTokens();
      setAccessTokenValid(false);
      setRole(null);
      setUser(null);
      setLoading(false);
      return;
    }

    const ok = await verifyToken();
    if (ok) {
      setAccessTokenValid(true);
      const userRole = getRoleFromToken();
      setRole(userRole);
      // Снимаем loading сразу после проверки токена - UI может рендериться
      setLoading(false);
      // Загружаем user в фоне
      loadUser();
      return;
    }
    
    // Если access токен невалиден, пытаемся обновить через refresh
    const refreshToken = localStorage.getItem('tp_refresh_token');
    if (refreshToken) {
      try {
        const res = await fetch(`/api/jwt/refresh/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh: refreshToken })
        });
        
        if (res.ok) {
          const data = await res.json();
          localStorage.setItem('tp_access_token', data.access);
          setAccessTokenValid(true);
          const userRole = getRoleFromToken();
          setRole(userRole);
          // Снимаем loading сразу - UI рендерится
          setLoading(false);
          // Загружаем user в фоне
          loadUser();
          return;
        }
      } catch (err) {
        console.error('Не удалось обновить токен:', err);
      }
    }
    
    // Если ничего не помогло - пользователь не авторизован
    clearTokens();
    setAccessTokenValid(false);
    setRole(null);
    setUser(null);
    setLoading(false);
  }, [loadUser]);

  useEffect(() => { check(); }, [check]);

  const login = useCallback(async ({ email, password, roleSelection, rememberMe }) => {
    // Перед логином очищаем старые токены
    clearTokens();
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    await apiLogin(email, password, rememberMe);

    // Токены сохраняются в localStorage и автоматически истекают через 12ч (JWT exp)

    const userRole = getRoleFromToken();
    const resolvedRole = userRole || roleSelection || null;
    setRole(resolvedRole);
    setAccessTokenValid(true);
    // Важно для скорости: не блокируем редирект ожиданием /api/me/.
    // Профиль подтянется в фоне, как и при auto-login по refresh.
    loadUser();
    return resolvedRole;
  }, [loadUser]);

  const register = useCallback(async ({ email, password, firstName, lastName, phone, role: initialRole, birthDate, rememberMe = true, notificationConsent = false }) => {
    // 1. Регистрация пользователя (при регистрации всегда запоминаем устройство)
    const regRes = await apiClient.post('jwt/register/', {
      email,
      password,
      first_name: firstName,
      last_name: lastName,
      phone: phone || '',
      role: initialRole,
      birth_date: birthDate || null,
      recaptcha_token: null,
      remember_me: rememberMe,
      notification_consent: notificationConsent,
      // Реферальные поля
      referral_code: localStorage.getItem('tp_referral_code') || '',
      utm_source: localStorage.getItem('tp_utm_source') || '',
      utm_medium: localStorage.getItem('tp_utm_medium') || '',
      utm_campaign: localStorage.getItem('tp_utm_campaign') || '',
      channel: localStorage.getItem('tp_channel') || '',
      ref_url: localStorage.getItem('tp_ref_url') || '',
      cookie_id: localStorage.getItem('tp_cookie_id') || '',
    });

    // Токены сохраняются в localStorage и автоматически истекают через 12ч (JWT exp)

    // 2. Очистим устаревшие ключи (совместимость со старым кодом)
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    // 3. Сохраняем первичные токены регистрации (может отличаться по срокам) 
    setTokens({ access: regRes.data.access, refresh: regRes.data.refresh });

    // 4. Дополнительно вызываем login для гарантии корректного формата токена (с remember_me)
    try {
      const loginRes = await apiLogin(email, password, rememberMe); // перезапишет токены
      if (loginRes?.access) {
        // Перезапись уже сделана внутри apiLogin через setTokens
      }
    } catch (e) {
      console.warn('Login после регистрации не удался, продолжаем с регистрационными токенами:', e);
    }

    // 5. Верифицируем токен сразу
    try {
      const ok = await verifyToken();
      setAccessTokenValid(ok);
    } catch (_) {
      setAccessTokenValid(true); // оптимистично
    }

    // 6. Определяем роль: из токена или из переданной initialRole
    const userRole = getRoleFromToken() || initialRole || null;
    setRole(userRole);

    // 7. Загружаем профиль (роль может уточниться)
    try { await loadUser(); } catch (e) { console.warn('Не удалось загрузить профиль после регистрации:', e); }
    
    // 8. Устанавливаем флаг для показа онбординг-тура (только при регистрации!)
    try {
      // Получаем userId из JWT токена
      const token = localStorage.getItem('tp_access_token');
      if (token) {
        const part = token.split('.')[1];
        if (part) {
          const base64 = part.replace(/-/g, '+').replace(/_/g, '/');
          const padded = base64 + '='.repeat((4 - base64.length % 4) % 4);
          const payload = JSON.parse(atob(padded));
          if (payload.user_id) {
            localStorage.setItem(`lectio_show_tour_${payload.user_id}`, 'true');
          }
        }
      }
    } catch (e) {
      console.warn('Не удалось установить флаг тура:', e);
    }
    
    return userRole;
  }, [loadUser]);

  const logout = useCallback(async () => {
    // Показываем skeleton для плавного перехода (избегаем "дребезга")
    setLoading(true);
    
    // Очищаем токены синхронно
    clearTokens();
    
    // API logout в фоне (fire and forget)
    try {
      apiLogout();
    } catch (_) {}
    
    // Небольшая задержка для fade-out эффекта, затем очищаем состояние
    await new Promise(r => setTimeout(r, 100));
    
    setAccessTokenValid(false);
    setRole(null);
    setUser(null);
    setSubscription(null);
    setLoading(false);
    
    // Редирект на страницу логина
    // Используем мягкий подход - React компоненты Protected/Routes 
    // сами обработают неавторизованное состояние и сделают редирект
  }, []);

  const refreshUser = useCallback(async () => loadUser(), [loadUser]);

  const refreshSubscription = useCallback(async () => loadSubscription(), [loadSubscription]);

  return (
    <AuthContext.Provider value={{ accessTokenValid, role, loading, user, subscription, login, logout, refreshUser, register, refreshSubscription }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

export const Protected = ({ allowRoles, children }) => {
  const { accessTokenValid, role, loading } = useAuth();
  if (loading) return <AuthCheckingSkeleton />;
  if (!accessTokenValid) return <Navigate to="/auth-new" replace />;
  if (allowRoles && !allowRoles.includes(role)) return <div style={{ padding: '2rem', textAlign: 'center' }}>Недостаточно прав.</div>;
  return children;
};
