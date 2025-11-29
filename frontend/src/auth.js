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

  const loadUser = useCallback(async () => {
    try {
      const res = await getCurrentUser();
      setUser(res.data);
      if (res.data?.role) {
        setRole(res.data.role);
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
  }, []);

  const check = useCallback(async () => {
    const path = typeof window !== 'undefined' ? window.location.pathname : '';

    // Если мы на странице авторизации, всегда считаем пользователя неавторизованным:
    // - жёстко чистим токены
    // - НЕ пытаемся авто-логиниться через refresh
    if (path.startsWith('/auth')) {
      try {
        await apiLogout();
      } catch (_) {}
      clearTokens(true);
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
      await loadUser();
      setLoading(false);
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
          await loadUser();
          setLoading(false);
          return;
        }
      } catch (err) {
        console.error('Не удалось обновить токен:', err);
      }
    }
    
    // Если ничего не помогло - пользователь не авторизован
    clearTokens(true);
    setAccessTokenValid(false);
    setRole(null);
    setUser(null);
    setLoading(false);
  }, [loadUser]);

  useEffect(() => { check(); }, [check]);

  const login = useCallback(async ({ email, password, roleSelection, rememberMe }) => {
    // Перед логином жёстко очищаем токены и любые старые флаги
    clearTokens(true);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    await apiLogin(email, password);

    // Если пользователь выбрал "Запомнить меня", сохраняем флаг для будущих сессий
    if (rememberMe) {
      localStorage.setItem('tp_remember_session', 'true');
    } else {
      localStorage.removeItem('tp_remember_session');
    }

    const userRole = getRoleFromToken();
    const resolvedRole = userRole || roleSelection || null;
    setRole(resolvedRole);
    setAccessTokenValid(true);
    await loadUser();
    return resolvedRole;
  }, [loadUser]);

  const register = useCallback(async ({ email, password, firstName, lastName, phone, role: initialRole, birthDate }) => {
    // 1. Регистрация пользователя
    const regRes = await apiClient.post('jwt/register/', {
      email,
      password,
      first_name: firstName,
      last_name: lastName,
      phone: phone || '',
      role: initialRole,
      birth_date: birthDate || null,
      recaptcha_token: null,
    });

    // 2. Очистим устаревшие ключи (совместимость со старым кодом)
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    // 3. Сохраняем первичные токены регистрации (может отличаться по срокам) 
    setTokens({ access: regRes.data.access, refresh: regRes.data.refresh });

    // 4. Дополнительно вызываем login для гарантии корректного формата токена
    try {
      const loginRes = await apiLogin(email, password); // перезапишет токены
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
    return userRole;
  }, [loadUser]);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch (_) {}
    clearTokens(true);
    localStorage.removeItem('tp_remember_session');
    setAccessTokenValid(false);
    setRole(null);
    setUser(null);
    window.location.href = '/auth-new';
  }, []);

  const refreshUser = useCallback(async () => loadUser(), [loadUser]);

  return (
    <AuthContext.Provider value={{ accessTokenValid, role, loading, user, login, logout, refreshUser, register }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

export const Protected = ({ allowRoles, children }) => {
  const { accessTokenValid, role, loading } = useAuth();
  if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Проверка авторизации...</div>;
  if (!accessTokenValid) return <Navigate to="/login" replace />;
  if (allowRoles && !allowRoles.includes(role)) return <div style={{ padding: '2rem', textAlign: 'center' }}>Недостаточно прав.</div>;
  return children;
};
