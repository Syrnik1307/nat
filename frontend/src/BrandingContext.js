/**
 * BrandingContext — глобальный контекст для брендинга текущего тенанта.
 * 
 * Хранит:
 *  - branding: объект с logo_url, colors, favicon и т.д.
 *  - loading: идёт ли загрузка
 * 
 * При инициализации загружает GET /api/tenants/public/<slug>/branding/
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiClient } from './apiService';
import { getTenantSlug } from './TenantContext';

const BrandingContext = createContext(null);

const DEFAULT_BRANDING = {
  name: 'Teaching Panel',
  logo_url: null,
  email: '',
  phone: '',
  website: '',
  metadata: {
    primary_color: '#2563eb',
    secondary_color: '#1e40af',
    accent_color: '#3b82f6',
    text_color: '#1f2937',
    bg_color: '#ffffff',
    favicon_url: null,
    link_color: '#2563eb',
    button_hover_color: '#1e40af',
  }
};

export const BrandingProvider = ({ children }) => {
  const [branding, setBranding] = useState(DEFAULT_BRANDING);
  const [loading, setLoading] = useState(true);

  const loadBranding = useCallback(async (slug) => {
    if (!slug) {
      setBranding(DEFAULT_BRANDING);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await apiClient.get(`tenants/public/${slug}/branding/`);
      
      const brandingData = {
        name: response.data.name || DEFAULT_BRANDING.name,
        logo_url: response.data.logo_url || null,
        email: response.data.email || '',
        phone: response.data.phone || '',
        website: response.data.website || '',
        metadata: {
          ...DEFAULT_BRANDING.metadata,
          ...response.data.metadata,
        }
      };
      
      setBranding(brandingData);
      
      // Apply branding to document
      applyBrandingToDocument(brandingData);
      
    } catch (error) {
      console.error('[BrandingContext] Failed to load branding', error);
      setBranding(DEFAULT_BRANDING);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load branding when tenant changes
  useEffect(() => {
    const slug = getTenantSlug();
    loadBranding(slug);
  }, [loadBranding]);

  return (
    <BrandingContext.Provider value={{
      branding,
      loading,
      reloadBranding: loadBranding,
    }}>
      {children}
    </BrandingContext.Provider>
  );
};

export const useBranding = () => {
  const ctx = useContext(BrandingContext);
  if (!ctx) throw new Error('useBranding must be used within BrandingProvider');
  return ctx;
};

/**
 * Apply branding colors and styles to the document
 */
export const applyBrandingToDocument = (branding) => {
  if (!branding?.metadata) return;

  const meta = branding.metadata;
  
  // Set CSS variables for global theming
  const style = document.documentElement.style;
  style.setPropertyValue('--primary-color', meta.primary_color || '#2563eb');
  style.setPropertyValue('--secondary-color', meta.secondary_color || '#1e40af');
  style.setPropertyValue('--accent-color', meta.accent_color || '#3b82f6');
  style.setPropertyValue('--text-color', meta.text_color || '#1f2937');
  style.setPropertyValue('--bg-color', meta.bg_color || '#ffffff');
  style.setPropertyValue('--link-color', meta.link_color || '#2563eb');
  style.setPropertyValue('--button-hover-color', meta.button_hover_color || '#1e40af');

  // Set favicon
  if (meta.favicon_url) {
    let favicon = document.querySelector('link[rel="icon"]');
    if (!favicon) {
      favicon = document.createElement('link');
      favicon.rel = 'icon';
      document.head.appendChild(favicon);
    }
    favicon.href = meta.favicon_url;
  }

  // Set page title
  if (branding.name) {
    document.title = branding.name;
  }
};

export default BrandingContext;
