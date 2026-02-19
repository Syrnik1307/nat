/**
 * BrandingAdmin.js — Admin interface for managing tenant branding
 * Path: /admin/branding/
 * Allows admins to:
 * - Upload/change logo
 * - Set primary and secondary colors
 * - Change email/phone/website
 * - Set favicon
 */

import React, { useState, useEffect } from 'react';
import { useTenant } from '../TenantContext';
import { apiClient } from '../apiService';
import './BrandingAdmin.css';

const BrandingAdmin = () => {
  const { currentTenant, reloadTenants, currentRole } = useTenant();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    website: '',
    logo_url: '',
    metadata: {
      primary_color: '#2563eb',
      secondary_color: '#1e40af',
      accent_color: '#3b82f6',
      text_color: '#1f2937',
      bg_color: '#ffffff',
      favicon_url: '',
      link_color: '#2563eb',
      button_hover_color: '#1e40af',
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Load current tenant branding
  useEffect(() => {
    if (currentTenant) {
      setFormData({
        name: currentTenant.name || '',
        email: currentTenant.email || '',
        phone: currentTenant.phone || '',
        website: currentTenant.website || '',
        logo_url: currentTenant.logo_url || '',
        metadata: currentTenant.metadata || {
          primary_color: '#2563eb',
          secondary_color: '#1e40af',
          accent_color: '#3b82f6',
          text_color: '#1f2937',
          bg_color: '#ffffff',
          favicon_url: '',
          link_color: '#2563eb',
          button_hover_color: '#1e40af',
        }
      });
    }
  }, [currentTenant]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    if (name.startsWith('metadata_')) {
      const metaKey = name.replace('metadata_', '');
      setFormData(prev => ({
        ...prev,
        metadata: {
          ...prev.metadata,
          [metaKey]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // Validate required fields
      if (!formData.name.trim()) {
        throw new Error('Organization name is required');
      }

      // Prepare data for API
      const updateData = {
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        website: formData.website,
        logo_url: formData.logo_url,
        metadata: formData.metadata
      };

      // Update tenant via API
      const response = await apiClient.patch(
        `tenants/${currentTenant.id}/`,
        updateData
      );

      setSuccess('✓ Branding updated successfully!');
      
      // Reload tenant data
      setTimeout(() => {
        reloadTenants();
      }, 500);

    } catch (err) {
      setError(`✗ Error: ${err.message || 'Failed to update branding'}`);
    } finally {
      setLoading(false);
    }
  };

  // Check permissions
  if (!currentRole || !['admin', 'owner'].includes(currentRole)) {
    return (
      <div className="alert alert-danger">
        <h4>Access Denied</h4>
        <p>Only administrators can manage branding.</p>
      </div>
    );
  }

  return (
    <div className="branding-admin-container">
      <div className="branding-admin-header">
        <h2>📎 Manage Tenant Branding</h2>
        <p className="text-muted">Customize colors, logo, and contact information for {currentTenant?.name}</p>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <form onSubmit={handleSubmit} className="branding-form">
        {/* Basic Information */}
        <div className="form-section">
          <h4 className="section-title">📋 Organization Information</h4>
          
          <div className="form-group">
            <label htmlFor="name">Organization Name</label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              className="form-control"
              required
            />
          </div>

          <div className="row">
            <div className="col-md-6">
              <div className="form-group">
                <label htmlFor="email">Contact Email</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className="form-control"
                />
              </div>
            </div>
            <div className="col-md-6">
              <div className="form-group">
                <label htmlFor="phone">Contact Phone</label>
                <input
                  type="tel"
                  id="phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                  className="form-control"
                />
              </div>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="website">Website URL</label>
            <input
              type="url"
              id="website"
              name="website"
              value={formData.website}
              onChange={handleInputChange}
              className="form-control"
              placeholder="https://example.com"
            />
          </div>
        </div>

        {/* Logos & Media */}
        <div className="form-section">
          <h4 className="section-title">🖼️ Logos & Media</h4>
          
          <div className="form-group">
            <label htmlFor="logo_url">Logo URL</label>
            <input
              type="url"
              id="logo_url"
              name="logo_url"
              value={formData.logo_url}
              onChange={handleInputChange}
              className="form-control"
              placeholder="https://example.com/logo.png"
            />
            {formData.logo_url && (
              <div className="logo-preview">
                <img src={formData.logo_url} alt="Logo Preview" />
              </div>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="favicon_url">Favicon URL</label>
            <input
              type="url"
              id="favicon_url"
              name="metadata_favicon_url"
              value={formData.metadata.favicon_url}
              onChange={handleInputChange}
              className="form-control"
              placeholder="https://example.com/favicon.ico"
            />
          </div>
        </div>

        {/* Color Customization */}
        <div className="form-section">
          <h4 className="section-title">🎨 Color Scheme</h4>
          
          <div className="row">
            <div className="col-md-4">
              <div className="form-group">
                <label htmlFor="primary_color">Primary Color</label>
                <div className="color-input-group">
                  <input
                    type="color"
                    id="primary_color"
                    name="metadata_primary_color"
                    value={formData.metadata.primary_color}
                    onChange={handleInputChange}
                    className="form-control form-control-color"
                  />
                  <input
                    type="text"
                    name="metadata_primary_color"
                    value={formData.metadata.primary_color}
                    onChange={handleInputChange}
                    className="form-control form-control-hex"
                    placeholder="#2563eb"
                  />
                </div>
                <small className="text-muted">Used for buttons, links, navigation</small>
              </div>
            </div>

            <div className="col-md-4">
              <div className="form-group">
                <label htmlFor="secondary_color">Secondary Color</label>
                <div className="color-input-group">
                  <input
                    type="color"
                    id="secondary_color"
                    name="metadata_secondary_color"
                    value={formData.metadata.secondary_color}
                    onChange={handleInputChange}
                    className="form-control form-control-color"
                  />
                  <input
                    type="text"
                    name="metadata_secondary_color"
                    value={formData.metadata.secondary_color}
                    onChange={handleInputChange}
                    className="form-control form-control-hex"
                    placeholder="#1e40af"
                  />
                </div>
                <small className="text-muted">Used for secondary elements</small>
              </div>
            </div>

            <div className="col-md-4">
              <div className="form-group">
                <label htmlFor="accent_color">Accent Color</label>
                <div className="color-input-group">
                  <input
                    type="color"
                    id="accent_color"
                    name="metadata_accent_color"
                    value={formData.metadata.accent_color}
                    onChange={handleInputChange}
                    className="form-control form-control-color"
                  />
                  <input
                    type="text"
                    name="metadata_accent_color"
                    value={formData.metadata.accent_color}
                    onChange={handleInputChange}
                    className="form-control form-control-hex"
                    placeholder="#3b82f6"
                  />
                </div>
                <small className="text-muted">Used for highlights, badges</small>
              </div>
            </div>
          </div>

          <div className="row">
            <div className="col-md-4">
              <div className="form-group">
                <label htmlFor="link_color">Link Color</label>
                <div className="color-input-group">
                  <input
                    type="color"
                    id="link_color"
                    name="metadata_link_color"
                    value={formData.metadata.link_color}
                    onChange={handleInputChange}
                    className="form-control form-control-color"
                  />
                  <input
                    type="text"
                    name="metadata_link_color"
                    value={formData.metadata.link_color}
                    onChange={handleInputChange}
                    className="form-control form-control-hex"
                    placeholder="#2563eb"
                  />
                </div>
              </div>
            </div>

            <div className="col-md-4">
              <div className="form-group">
                <label htmlFor="button_hover_color">Button Hover Color</label>
                <div className="color-input-group">
                  <input
                    type="color"
                    id="button_hover_color"
                    name="metadata_button_hover_color"
                    value={formData.metadata.button_hover_color}
                    onChange={handleInputChange}
                    className="form-control form-control-color"
                  />
                  <input
                    type="text"
                    name="metadata_button_hover_color"
                    value={formData.metadata.button_hover_color}
                    onChange={handleInputChange}
                    className="form-control form-control-hex"
                    placeholder="#1e40af"
                  />
                </div>
              </div>
            </div>

            <div className="col-md-4">
              <div className="form-group">
                <label htmlFor="text_color">Text Color</label>
                <div className="color-input-group">
                  <input
                    type="color"
                    id="text_color"
                    name="metadata_text_color"
                    value={formData.metadata.text_color}
                    onChange={handleInputChange}
                    className="form-control form-control-color"
                  />
                  <input
                    type="text"
                    name="metadata_text_color"
                    value={formData.metadata.text_color}
                    onChange={handleInputChange}
                    className="form-control form-control-hex"
                    placeholder="#1f2937"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="row">
            <div className="col-md-6">
              <div className="form-group">
                <label htmlFor="bg_color">Background Color</label>
                <div className="color-input-group">
                  <input
                    type="color"
                    id="bg_color"
                    name="metadata_bg_color"
                    value={formData.metadata.bg_color}
                    onChange={handleInputChange}
                    className="form-control form-control-color"
                  />
                  <input
                    type="text"
                    name="metadata_bg_color"
                    value={formData.metadata.bg_color}
                    onChange={handleInputChange}
                    className="form-control form-control-hex"
                    placeholder="#ffffff"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Preview */}
        <div className="form-section">
          <h4 className="section-title">👁️ Preview</h4>
          <div className="branding-preview">
            <div className="preview-item" style={{
              backgroundColor: formData.metadata.primary_color,
              color: formData.metadata.text_color
            }}>
              <span>Primary Button</span>
            </div>
            <div className="preview-item" style={{
              backgroundColor: formData.metadata.secondary_color,
              color: formData.metadata.text_color
            }}>
              <span>Secondary Button</span>
            </div>
            <div className="preview-item" style={{
              backgroundColor: formData.metadata.accent_color,
              color: formData.metadata.text_color
            }}>
              <span>Accent Color</span>
            </div>
            <div className="preview-item" style={{
              backgroundColor: formData.metadata.bg_color,
              color: formData.metadata.text_color,
              border: `2px solid ${formData.metadata.primary_color}`
            }}>
              <span><a href="#" style={{ color: formData.metadata.link_color }}>Sample Link</a></span>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="form-section">
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary btn-lg"
            style={{
              backgroundColor: formData.metadata.primary_color,
              borderColor: formData.metadata.primary_color
            }}
          >
            {loading ? 'Saving...' : '💾 Save Branding'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default BrandingAdmin;
