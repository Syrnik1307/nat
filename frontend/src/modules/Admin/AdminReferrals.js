import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../apiService';
import { useNotifications } from '../../shared/context/NotificationContext';
import './AdminReferrals.css';

/**
 * Полный интерфейс управления реферальными ссылками для админа.
 * - Создание/редактирование ссылок
 * - Привязка к партнёру/каналу
 * - Статистика: клики, регистрации, оплаты
 * - Управление выплатами
 */
const AdminReferrals = ({ onClose }) => {
  const { toast, showConfirm } = useNotifications();
  const [links, setLinks] = useState([]);
  const [totals, setTotals] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedLink, setSelectedLink] = useState(null);
  const [linkDetail, setLinkDetail] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showCommissions, setShowCommissions] = useState(false);
  const [commissions, setCommissions] = useState([]);
  const [commissionTotals, setCommissionTotals] = useState({});
  const [overallStats, setOverallStats] = useState(null);
  const [copySuccess, setCopySuccess] = useState('');

  // Форма создания/редактирования
  const [form, setForm] = useState({
    name: '',
    code: '',
    partner_name: '',
    partner_contact: '',
    commission_amount: '750.00',
    utm_source: 'telegram',
    utm_medium: 'referral',
    utm_campaign: '',
    notes: '',
    is_active: true,
  });
  const [formError, setFormError] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  const loadLinks = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('admin/referrals/');
      setLinks(res.data.links || []);
      setTotals(res.data.totals || {});
    } catch (err) {
      console.error('Ошибка загрузки ссылок:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadOverallStats = useCallback(async () => {
    try {
      const res = await apiClient.get('admin/referrals/stats/');
      setOverallStats(res.data);
    } catch (err) {
      console.error('Ошибка загрузки статистики:', err);
    }
  }, []);

  const loadLinkDetail = useCallback(async (linkId) => {
    try {
      const res = await apiClient.get(`admin/referrals/${linkId}/`);
      setLinkDetail(res.data);
    } catch (err) {
      console.error('Ошибка загрузки деталей:', err);
    }
  }, []);

  const loadCommissions = useCallback(async () => {
    try {
      const res = await apiClient.get('admin/referrals/commissions/');
      setCommissions(res.data.commissions || []);
      setCommissionTotals(res.data.totals || {});
    } catch (err) {
      console.error('Ошибка загрузки комиссий:', err);
    }
  }, []);

  useEffect(() => {
    loadLinks();
    loadOverallStats();
  }, [loadLinks, loadOverallStats]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setFormError('');
    
    if (!form.name.trim()) {
      setFormError('Название обязательно');
      return;
    }

    try {
      if (isEditing && selectedLink) {
        await apiClient.put(`admin/referrals/${selectedLink.id}/`, form);
      } else {
        await apiClient.post('admin/referrals/', form);
      }
      setShowCreateModal(false);
      resetForm();
      loadLinks();
      loadOverallStats();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Ошибка сохранения');
    }
  };

  const handleDelete = async (linkId) => {
    const confirmed = await showConfirm({
      title: 'Удаление ссылки',
      message: 'Удалить эту ссылку?',
      variant: 'danger',
      confirmText: 'Удалить',
      cancelText: 'Отмена'
    });
    if (!confirmed) return;
    try {
      await apiClient.delete(`admin/referrals/${linkId}/`);
      loadLinks();
      setSelectedLink(null);
      setLinkDetail(null);
    } catch (err) {
      toast.error('Ошибка удаления');
    }
  };

  const handlePayout = async (linkId, amount) => {
    try {
      await apiClient.post(`admin/referrals/${linkId}/payout/`, { amount });
      loadLinks();
      if (linkDetail) loadLinkDetail(linkId);
      toast.success('Выплата записана');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка выплаты');
    }
  };

  const handleMarkCommissionsPaid = async (ids) => {
    try {
      await apiClient.post('admin/referrals/commissions/', { commission_ids: ids });
      loadCommissions();
      loadOverallStats();
      toast.success('Комиссии отмечены как выплаченные');
    } catch (err) {
      toast.error('Ошибка');
    }
  };

  const resetForm = () => {
    setForm({
      name: '',
      code: '',
      partner_name: '',
      partner_contact: '',
      commission_amount: '750.00',
      utm_source: 'telegram',
      utm_medium: 'referral',
      utm_campaign: '',
      notes: '',
      is_active: true,
    });
    setIsEditing(false);
    setSelectedLink(null);
  };

  const openEditModal = (link) => {
    setForm({
      name: link.name,
      code: link.code,
      partner_name: link.partner_name,
      partner_contact: link.partner_contact,
      commission_amount: link.commission_amount,
      utm_source: link.utm_source,
      utm_medium: link.utm_medium,
      utm_campaign: link.utm_campaign,
      notes: link.notes,
      is_active: link.is_active,
    });
    setSelectedLink(link);
    setIsEditing(true);
    setShowCreateModal(true);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopySuccess(text);
      setTimeout(() => setCopySuccess(''), 2000);
    });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-referrals-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🔗 Реферальные ссылки</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="referrals-content">
          {/* Общая статистика */}
          {overallStats && (
            <div className="referrals-stats-overview">
              <div className="stat-box">
                <div className="stat-value">{overallStats.links?.total || 0}</div>
                <div className="stat-label">Ссылок</div>
              </div>
              <div className="stat-box">
                <div className="stat-value">{overallStats.clicks || 0}</div>
                <div className="stat-label">Кликов</div>
              </div>
              <div className="stat-box">
                <div className="stat-value">{overallStats.registrations || 0}</div>
                <div className="stat-label">Регистраций</div>
              </div>
              <div className="stat-box">
                <div className="stat-value">{overallStats.payments || 0}</div>
                <div className="stat-label">Оплат</div>
              </div>
              <div className="stat-box highlight">
                <div className="stat-value">{overallStats.commissions?.pending || '0.00'} ₽</div>
                <div className="stat-label">К выплате</div>
              </div>
              <div className="stat-box">
                <div className="stat-value">{overallStats.conversions?.click_to_registration || 0}%</div>
                <div className="stat-label">Клик→Рег</div>
              </div>
            </div>
          )}

          {/* Действия */}
          <div className="referrals-actions">
            <button className="btn-primary" onClick={() => { resetForm(); setShowCreateModal(true); }}>
              ➕ Создать ссылку
            </button>
            <button className="btn-secondary" onClick={() => { setShowCommissions(true); loadCommissions(); }}>
              💰 Комиссии
            </button>
          </div>

          {/* Список ссылок */}
          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : (
            <div className="referrals-table-container">
              <table className="referrals-table">
                <thead>
                  <tr>
                    <th>Название</th>
                    <th>Код</th>
                    <th>Партнёр</th>
                    <th>Клики</th>
                    <th>Рег.</th>
                    <th>Оплат</th>
                    <th>Заработано</th>
                    <th>К выплате</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {links.map((link) => (
                    <tr key={link.id} className={!link.is_active ? 'inactive' : ''}>
                      <td>
                        <div className="link-name">{link.name}</div>
                        <div className="link-url" onClick={() => copyToClipboard(link.full_url)}>
                          {copySuccess === link.full_url ? '✓ Скопировано!' : link.full_url.substring(0, 40) + '...'}
                        </div>
                      </td>
                      <td><code>{link.code}</code></td>
                      <td>
                        <div>{link.partner_name || '-'}</div>
                        <small>{link.partner_contact}</small>
                      </td>
                      <td>{link.clicks_count}</td>
                      <td>{link.registrations_count}</td>
                      <td>{link.payments_count}</td>
                      <td>{link.total_earned} ₽</td>
                      <td className={parseFloat(link.pending_payout) > 0 ? 'pending-amount' : ''}>
                        {link.pending_payout} ₽
                      </td>
                      <td>
                        <div className="action-buttons">
                          <button 
                            className="btn-icon" 
                            title="Детали"
                            onClick={() => { setSelectedLink(link); loadLinkDetail(link.id); }}
                          >
                            👁️
                          </button>
                          <button 
                            className="btn-icon" 
                            title="Редактировать"
                            onClick={() => openEditModal(link)}
                          >
                            ✏️
                          </button>
                          <button 
                            className="btn-icon" 
                            title="Копировать ссылку"
                            onClick={() => copyToClipboard(link.full_url)}
                          >
                            📋
                          </button>
                          {parseFloat(link.pending_payout) > 0 && (
                            <button 
                              className="btn-icon payout" 
                              title="Выплатить"
                              onClick={() => {
                                const amount = prompt(`Сумма выплаты (макс: ${link.pending_payout} ₽):`, link.pending_payout);
                                if (amount) handlePayout(link.id, amount);
                              }}
                            >
                              💸
                            </button>
                          )}
                          <button 
                            className="btn-icon danger" 
                            title="Удалить"
                            onClick={() => handleDelete(link.id)}
                          >
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {links.length === 0 && (
                <div className="empty-state">
                  Нет реферальных ссылок. Создайте первую!
                </div>
              )}
            </div>
          )}

          {/* Итоги */}
          {totals && links.length > 0 && (
            <div className="referrals-totals">
              <span>Итого: {totals.clicks || 0} кликов, {totals.registrations || 0} рег., {totals.payments || 0} оплат</span>
              <span>Заработано: {totals.earned || '0.00'} ₽ | Выплачено: {totals.paid_out || '0.00'} ₽ | К выплате: {totals.pending || '0.00'} ₽</span>
            </div>
          )}
        </div>

        {/* Модалка создания/редактирования */}
        {showCreateModal && (
          <div className="inner-modal-overlay" onClick={() => setShowCreateModal(false)}>
            <div className="inner-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>{isEditing ? '✏️ Редактировать ссылку' : '➕ Новая реферальная ссылка'}</h3>
                <button className="modal-close" onClick={() => setShowCreateModal(false)}>✕</button>
              </div>
              <form onSubmit={handleCreate} className="referral-form">
                {formError && <div className="form-error">{formError}</div>}
                
                <div className="form-row">
                  <div className="form-group">
                    <label>Название *</label>
                    <input
                      type="text"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      placeholder="ТГ канал @example"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Код (авто если пусто)</label>
                    <input
                      type="text"
                      value={form.code}
                      onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                      placeholder="ABC123"
                      disabled={isEditing}
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Имя партнёра</label>
                    <input
                      type="text"
                      value={form.partner_name}
                      onChange={(e) => setForm({ ...form, partner_name: e.target.value })}
                      placeholder="Иван Иванов"
                    />
                  </div>
                  <div className="form-group">
                    <label>Контакт для выплат</label>
                    <input
                      type="text"
                      value={form.partner_contact}
                      onChange={(e) => setForm({ ...form, partner_contact: e.target.value })}
                      placeholder="@telegram или номер карты"
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Комиссия за оплату (₽)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={form.commission_amount}
                      onChange={(e) => setForm({ ...form, commission_amount: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>UTM Campaign</label>
                    <input
                      type="text"
                      value={form.utm_campaign}
                      onChange={(e) => setForm({ ...form, utm_campaign: e.target.value })}
                      placeholder="channel_name"
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>UTM Source</label>
                    <input
                      type="text"
                      value={form.utm_source}
                      onChange={(e) => setForm({ ...form, utm_source: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>UTM Medium</label>
                    <input
                      type="text"
                      value={form.utm_medium}
                      onChange={(e) => setForm({ ...form, utm_medium: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Заметки</label>
                  <textarea
                    value={form.notes}
                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                    placeholder="Детали сотрудничества..."
                    rows={2}
                  />
                </div>

                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={form.is_active}
                      onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    />
                    Активна
                  </label>
                </div>

                <div className="form-actions">
                  <button type="button" className="btn-cancel" onClick={() => setShowCreateModal(false)}>
                    Отмена
                  </button>
                  <button type="submit" className="btn-submit">
                    {isEditing ? 'Сохранить' : 'Создать'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Модалка деталей ссылки */}
        {linkDetail && (
          <div className="inner-modal-overlay" onClick={() => { setLinkDetail(null); setSelectedLink(null); }}>
            <div className="inner-modal wide" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>📊 {linkDetail.link.name}</h3>
                <button className="modal-close" onClick={() => { setLinkDetail(null); setSelectedLink(null); }}>✕</button>
              </div>
              <div className="link-detail-content">
                <div className="detail-section">
                  <h4>Ссылка</h4>
                  <div className="link-url-full" onClick={() => copyToClipboard(linkDetail.link.full_url)}>
                    {linkDetail.link.full_url}
                    <span className="copy-hint">{copySuccess === linkDetail.link.full_url ? '✓' : '📋'}</span>
                  </div>
                </div>

                <div className="detail-section">
                  <h4>Статистика</h4>
                  <div className="detail-stats">
                    <div>Кликов: <strong>{linkDetail.link.clicks_count}</strong></div>
                    <div>Регистраций: <strong>{linkDetail.link.registrations_count}</strong></div>
                    <div>Оплат: <strong>{linkDetail.link.payments_count}</strong></div>
                    <div>Заработано: <strong>{linkDetail.link.total_earned} ₽</strong></div>
                    <div>Выплачено: <strong>{linkDetail.link.total_paid_out} ₽</strong></div>
                    <div className="pending">К выплате: <strong>{linkDetail.link.pending_payout} ₽</strong></div>
                  </div>
                </div>

                <div className="detail-section">
                  <h4>Регистрации ({linkDetail.registrations?.length || 0})</h4>
                  {linkDetail.registrations?.length > 0 ? (
                    <table className="mini-table">
                      <thead>
                        <tr>
                          <th>Email</th>
                          <th>Имя</th>
                          <th>Дата</th>
                          <th>Оплата</th>
                        </tr>
                      </thead>
                      <tbody>
                        {linkDetail.registrations.map((reg, idx) => (
                          <tr key={idx}>
                            <td>{reg.email}</td>
                            <td>{reg.name}</td>
                            <td>{formatDate(reg.registered_at)}</td>
                            <td>{reg.has_payment ? `✅ ${reg.payment_amount} ₽` : '❌'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="empty-mini">Нет регистраций</div>
                  )}
                </div>

                <div className="detail-section">
                  <h4>Последние клики</h4>
                  {linkDetail.clicks?.length > 0 ? (
                    <div className="clicks-list">
                      {linkDetail.clicks.slice(0, 10).map((click, idx) => (
                        <div key={idx} className="click-item">
                          <span>{formatDate(click.created_at)}</span>
                          <span>{click.ip}</span>
                          {click.resulted_in_registration && <span className="tag">→ Рег: {click.user_email}</span>}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-mini">Нет кликов</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Модалка комиссий */}
        {showCommissions && (
          <div className="inner-modal-overlay" onClick={() => setShowCommissions(false)}>
            <div className="inner-modal wide" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>💰 Комиссии</h3>
                <button className="modal-close" onClick={() => setShowCommissions(false)}>✕</button>
              </div>
              <div className="commissions-content">
                <div className="commissions-summary">
                  <span>К выплате: <strong>{commissionTotals.pending || '0.00'} ₽</strong></span>
                  <span>Выплачено: <strong>{commissionTotals.paid || '0.00'} ₽</strong></span>
                  {commissions.filter(c => c.status === 'pending').length > 0 && (
                    <button 
                      className="btn-small"
                      onClick={() => handleMarkCommissionsPaid(commissions.filter(c => c.status === 'pending').map(c => c.id))}
                    >
                      Отметить все выплаченными
                    </button>
                  )}
                </div>

                <table className="commissions-table">
                  <thead>
                    <tr>
                      <th>Реферер</th>
                      <th>Приглашённый</th>
                      <th>Сумма</th>
                      <th>Статус</th>
                      <th>Дата</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commissions.map((c) => (
                      <tr key={c.id} className={c.status}>
                        <td>
                          <div>{c.referrer_name}</div>
                          <small>{c.referrer_email}</small>
                        </td>
                        <td>
                          <div>{c.referred_user_name}</div>
                          <small>{c.referred_user_email}</small>
                        </td>
                        <td>{c.amount} ₽</td>
                        <td>
                          <span className={`status-badge ${c.status}`}>
                            {c.status === 'pending' ? '⏳ Ожидает' : c.status === 'paid' ? '✅ Выплачено' : '❌ Отменено'}
                          </span>
                        </td>
                        <td>{formatDate(c.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {commissions.length === 0 && (
                  <div className="empty-state">Нет комиссий</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminReferrals;
