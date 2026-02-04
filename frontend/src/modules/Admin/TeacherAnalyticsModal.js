import React, { useState, useEffect } from 'react';
import { getAccessToken } from '../../apiService';
import './TeacherAnalyticsModal.css';

/**
 * TeacherAnalyticsModal - read-only modal to display detailed metrics for a teacher.
 * Shows integrations status, activity counts, growth metrics, and finance data.
 * 
 * @param {Object} props
 * @param {number} props.teacherId - ID of the teacher to fetch analytics for
 * @param {string} props.teacherName - Display name of the teacher (for header)
 * @param {string} props.teacherEmail - Email of the teacher (for header)
 * @param {Function} props.onClose - Callback to close the modal
 */
const TeacherAnalyticsModal = ({ teacherId, teacherName, teacherEmail, onClose }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (teacherId) {
      loadAnalytics();
    }
  }, [teacherId]);

  const loadAnalytics = async () => {
    setLoading(true);
    setError('');
    try {
      const token = getAccessToken();
      const response = await fetch(`/accounts/api/admin/teachers/${teacherId}/analytics/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || 'Не удалось загрузить аналитику');
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Analytics load error:', err);
      setError(err.message || 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (value) => {
    if (!value) return '—';
    return new Date(value).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const formatDateTime = (value) => {
    if (!value) return '—';
    return new Date(value).toLocaleString('ru-RU', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return '0';
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const getStatusLabel = (status) => {
    const labels = {
      active: 'Активна',
      pending: 'Ожидает оплаты',
      expired: 'Истекла',
      cancelled: 'Отменена',
      trial: 'Триал'
    };
    return labels[status] || status || 'Нет';
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="teacher-analytics-overlay" onClick={handleOverlayClick}>
      <div className="teacher-analytics-modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="ta-header">
          <div className="ta-header-info">
            <h2>{teacherName || 'Аналитика учителя'}</h2>
            <p>{teacherEmail}</p>
          </div>
          <button className="ta-close" onClick={onClose} title="Закрыть">
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="ta-content">
          {loading && (
            <div className="ta-loading">
              <div className="ta-spinner"></div>
              <span>Загрузка аналитики...</span>
            </div>
          )}

          {error && !loading && (
            <div className="ta-error">{error}</div>
          )}

          {data && !loading && (
            <>
              {/* Integrations Section */}
              <div className="ta-section">
                <h3 className="ta-section-title">Интеграции</h3>
                <div className="ta-integrations-list">
                  {/* Zoom */}
                  <div className="ta-integration-item">
                    <div className="ta-integration-info">
                      <div className="ta-integration-icon zoom">Z</div>
                      <div>
                        <div className="ta-integration-name">Zoom</div>
                        {data.integrations.zoom.user_id && (
                          <div className="ta-integration-detail">{data.integrations.zoom.user_id}</div>
                        )}
                      </div>
                    </div>
                    <span className={`ta-status-badge ${data.integrations.zoom.connected ? 'connected' : 'disconnected'}`}>
                      {data.integrations.zoom.connected ? 'Подключен' : 'Не подключен'}
                    </span>
                  </div>

                  {/* Google Meet */}
                  <div className="ta-integration-item">
                    <div className="ta-integration-info">
                      <div className="ta-integration-icon meet">G</div>
                      <div>
                        <div className="ta-integration-name">Google Meet</div>
                        {data.integrations.google_meet.email && (
                          <div className="ta-integration-detail">{data.integrations.google_meet.email}</div>
                        )}
                      </div>
                    </div>
                    <span className={`ta-status-badge ${data.integrations.google_meet.connected ? 'connected' : 'disconnected'}`}>
                      {data.integrations.google_meet.connected ? 'Подключен' : 'Не подключен'}
                    </span>
                  </div>

                  {/* Telegram */}
                  <div className="ta-integration-item">
                    <div className="ta-integration-info">
                      <div className="ta-integration-icon telegram">T</div>
                      <div>
                        <div className="ta-integration-name">Telegram</div>
                        {data.integrations.telegram.username && (
                          <div className="ta-integration-detail">@{data.integrations.telegram.username}</div>
                        )}
                      </div>
                    </div>
                    <span className={`ta-status-badge ${data.integrations.telegram.connected ? (data.integrations.telegram.verified ? 'verified' : 'connected') : 'disconnected'}`}>
                      {data.integrations.telegram.connected 
                        ? (data.integrations.telegram.verified ? 'Подтвержден' : 'Подключен')
                        : 'Не подключен'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Activity Section */}
              <div className="ta-section">
                <h3 className="ta-section-title">Активность</h3>
                <div className="ta-stats-grid">
                  <div className="ta-stat-card">
                    <span className="ta-stat-label">Групп создано</span>
                    <span className="ta-stat-value">{data.activity.groups_count}</span>
                  </div>
                  <div className="ta-stat-card">
                    <span className="ta-stat-label">Уроков всего</span>
                    <span className="ta-stat-value">{data.activity.total_lessons}</span>
                    <span className="ta-stat-sub">За 30 дней: {data.activity.lessons_last_30_days}</span>
                  </div>
                  <div className="ta-stat-card">
                    <span className="ta-stat-label">Домашних заданий</span>
                    <span className="ta-stat-value">{data.activity.homeworks_count}</span>
                  </div>
                </div>
              </div>

              {/* Growth Section */}
              <div className="ta-section">
                <h3 className="ta-section-title">Рост</h3>
                <div className="ta-stats-grid">
                  <div className="ta-stat-card">
                    <span className="ta-stat-label">Учеников добавлено</span>
                    <span className="ta-stat-value">{data.growth.total_students}</span>
                  </div>
                </div>
              </div>

              {/* Finance Section */}
              <div className="ta-section">
                <h3 className="ta-section-title">Финансы</h3>
                
                <div className="ta-finance-summary">
                  <div className="ta-finance-card">
                    <div className="ta-finance-label">Всего оплачено</div>
                    <div className="ta-finance-value">{formatCurrency(data.finance.total_paid)}</div>
                    <div className="ta-finance-sub">{data.finance.payments_count} платежей</div>
                  </div>
                </div>

                <div style={{ marginTop: '1rem' }}>
                  <div className="ta-subscription-row">
                    <span className="label">Статус подписки</span>
                    <span className={`ta-sub-status ${data.finance.subscription_status || 'none'}`}>
                      {getStatusLabel(data.finance.subscription_status)}
                    </span>
                  </div>
                  <div className="ta-subscription-row">
                    <span className="label">Тариф</span>
                    <span className="value">{data.finance.subscription_plan || '—'}</span>
                  </div>
                  <div className="ta-subscription-row">
                    <span className="label">Действует до</span>
                    <span className="value">{formatDateTime(data.finance.subscription_expires_at)}</span>
                  </div>
                  <div className="ta-subscription-row">
                    <span className="label">Последний платеж</span>
                    <span className="value">{formatDate(data.finance.last_payment_date)}</span>
                  </div>
                </div>
              </div>

              {/* Meta info */}
              <div className="ta-meta-row">
                <span>На платформе</span>
                <span>{data.teacher.days_on_platform} дней</span>
              </div>
              <div className="ta-meta-row" style={{ marginTop: 0, borderTop: 'none', paddingTop: 0 }}>
                <span>Последний вход</span>
                <span>{formatDateTime(data.teacher.last_login)}</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default TeacherAnalyticsModal;
