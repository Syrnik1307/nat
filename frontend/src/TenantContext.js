/**
 * TenantContext — глобальный контекст текущего тенанта.
 *
 * Хранит:
 *  - currentTenant: объект { id, uuid, slug, name, logo_url, email, phone, metadata, ... }
 *  - tenants: список всех тенантов пользователя
 *  - switchTenant(slug): сменить активный тенант
 *  - loading: идёт ли загрузка тенантов
 *
 * При инициализации загружает GET /api/tenants/my/ и сохраняет slug в localStorage.
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiClient } from './apiService';

const TENANT_SLUG_KEY = 'tp_current_tenant_slug';

const TenantContext = createContext(null);

export const getTenantSlug = () => localStorage.getItem(TENANT_SLUG_KEY);
export const setTenantSlug = (slug) => {
    if (slug) localStorage.setItem(TENANT_SLUG_KEY, slug);
    else localStorage.removeItem(TENANT_SLUG_KEY);
};

const isOlgaHost = () => {
    if (typeof window === 'undefined') return false;
    const hostname = window.location.hostname || '';
    return hostname === 'olga.lectiospace.ru' || hostname.startsWith('olga.');
};

const hasAuthToken = () => Boolean(localStorage.getItem('tp_access_token'));

export const TenantProvider = ({ children }) => {
    const [tenants, setTenants] = useState([]);
    const [currentTenant, setCurrentTenant] = useState(null);
    const [loading, setLoading] = useState(true);

    const loadTenants = useCallback(async () => {
        if (!hasAuthToken()) {
            if (isOlgaHost()) {
                setCurrentTenant({ slug: 'olga', name: 'Ольга фарфоровые цветы' });
                setTenantSlug('olga');
            }
            setTenants([]);
            setLoading(false);
            return;
        }

        try {
            const res = await apiClient.get('tenants/my/');
            const list = res.data; // [{ tenant: {...}, role, joined_at }, ...]
            setTenants(list);

            if (list.length === 0) {
                setCurrentTenant(null);
                setTenantSlug(null);
                setLoading(false);
                return;
            }

            // Попытаться восстановить последний выбранный slug
            const savedSlug = getTenantSlug();
            const saved = list.find(m => m.tenant.slug === savedSlug);
            if (saved) {
                setCurrentTenant(saved.tenant);
            } else {
                // Первый тенант по умолчанию
                setCurrentTenant(list[0].tenant);
                setTenantSlug(list[0].tenant.slug);
            }
        } catch (err) {
            const status = err?.response?.status;

            if (status === 404 && isOlgaHost()) {
                setTenants([]);
                setCurrentTenant({ slug: 'olga', name: 'Ольга фарфоровые цветы' });
                setTenantSlug('olga');
            } else {
                console.error('[TenantContext] Не удалось загрузить тенанты', err);
                setTenants([]);
                setCurrentTenant(null);
            }
        } finally {
            setLoading(false);
        }
    }, []);

    // Загружаем при монтировании
    useEffect(() => {
        loadTenants();
    }, [loadTenants]);

    const switchTenant = useCallback((slug) => {
        const found = tenants.find(m => m.tenant.slug === slug);
        if (found) {
            setCurrentTenant(found.tenant);
            setTenantSlug(slug);
        }
    }, [tenants]);

    const currentRole = tenants.find(m => m.tenant?.slug === currentTenant?.slug)?.role || null;

    return (
        <TenantContext.Provider value={{
            tenants,
            currentTenant,
            currentRole,
            loading,
            switchTenant,
            reloadTenants: loadTenants,
        }}>
            {children}
        </TenantContext.Provider>
    );
};

export const useTenant = () => {
    const ctx = useContext(TenantContext);
    if (!ctx) throw new Error('useTenant must be used within TenantProvider');
    return ctx;
};

export default TenantContext;
