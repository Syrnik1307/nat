import React, { useState, useEffect, useCallback, useRef } from 'react';
import { supportApi } from '../apiService';
import { featureFlags } from '../config/featureFlags';
import FileDropzone from '../shared/components/FileDropzone';
import './SupportPage.css';
import './AdminSupportPage.css';

// Icons
const ArrowLeftIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
  </svg>
);
const SendIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);
const UserCheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2"/><circle cx="8.5" cy="7" r="4"/><polyline points="17 11 19 13 23 9"/>
  </svg>
);

const STATUS_LABELS = {
  new: 'Новый', in_progress: 'В работе', waiting_user: 'Ожид. ответа',
  resolved: 'Решён', closed: 'Закрыт',
};
const STATUS_COLORS = {
  new: 'adm-status--new', in_progress: 'adm-status--progress',
  waiting_user: 'adm-status--waiting', resolved: 'adm-status--resolved', closed: 'adm-status--closed',
};
const PRIORITY_LABELS = {
  p0: 'P0', p1: 'P1', p2: 'P2', p3: 'P3',
};
const PRIORITY_COLORS = {
  p0: 'adm-priority--p0', p1: 'adm-priority--p1', p2: 'adm-priority--p2', p3: 'adm-priority--p3',
};

async function uploadFiles(files, setFiles) {
  const updated = [...files];
  const ids = [];
  for (let i = 0; i < updated.length; i++) {
    if (updated[i].id) { ids.push(updated[i].id); continue; }
    updated[i] = { ...updated[i], uploading: true, progress: 0 };
    setFiles([...updated]);
    try {
      const res = await supportApi.uploadFile(updated[i].file, (pct) => {
        updated[i] = { ...updated[i], progress: pct };
        setFiles([...updated]);
      });
      updated[i] = { ...updated[i], id: res.data.id, uploading: false, progress: 100 };
      ids.push(res.data.id);
    } catch {
      updated[i] = { ...updated[i], uploading: false, error: 'Ошибка загрузки' };
    }
    setFiles([...updated]);
  }
  return ids;
}

// ===================== Dashboard =====================
function Dashboard({ stats }) {
  if (!stats) return null;
  return (
    <div className="adm-dashboard">
      <div className="adm-stat-cards">
        <div className="adm-stat-card">
          <span className="adm-stat-card__value">{stats.open_total}</span>
          <span className="adm-stat-card__label">Открытых</span>
        </div>
        <div className="adm-stat-card adm-stat-card--warn">
          <span className="adm-stat-card__value">{stats.by_status?.new || 0}</span>
          <span className="adm-stat-card__label">Новых</span>
        </div>
        <div className="adm-stat-card">
          <span className="adm-stat-card__value">{stats.resolved_today}</span>
          <span className="adm-stat-card__label">Решено сегодня</span>
        </div>
        <div className="adm-stat-card adm-stat-card--danger">
          <span className="adm-stat-card__value">{stats.sla_breached}</span>
          <span className="adm-stat-card__label">SLA нарушен</span>
        </div>
      </div>
    </div>
  );
}

// ===================== Ticket List =====================
function AdminTicketList({ tickets, loading, onSelect, filters, setFilters }) {
  return (
    <div className="adm-list">
      <div className="adm-list__filters">
        <select
          className="adm-select"
          value={filters.status || ''}
          onChange={(e) => setFilters({ ...filters, status: e.target.value || undefined })}
        >
          <option value="">Все статусы</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          className="adm-select"
          value={filters.priority || ''}
          onChange={(e) => setFilters({ ...filters, priority: e.target.value || undefined })}
        >
          <option value="">Все приоритеты</option>
          {Object.entries(PRIORITY_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          className="adm-select"
          value={filters.assigned_to || ''}
          onChange={(e) => setFilters({ ...filters, assigned_to: e.target.value || undefined })}
        >
          <option value="">Все тикеты</option>
          <option value="me">Мои</option>
          <option value="unassigned">Без назначения</option>
        </select>
      </div>

      {loading ? (
        <div className="adm-list__loading">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="adm-skeleton adm-skeleton--row" />
          ))}
        </div>
      ) : tickets.length === 0 ? (
        <div className="adm-empty">Нет тикетов по заданным фильтрам</div>
      ) : (
        <div className="adm-table">
          <div className="adm-table__header">
            <span className="adm-table__col adm-table__col--id">#</span>
            <span className="adm-table__col adm-table__col--priority">P</span>
            <span className="adm-table__col adm-table__col--subject">Тема</span>
            <span className="adm-table__col adm-table__col--user">От</span>
            <span className="adm-table__col adm-table__col--status">Статус</span>
            <span className="adm-table__col adm-table__col--date">Дата</span>
          </div>
          {tickets.map((t, idx) => (
            <button
              key={t.id}
              className="adm-table__row"
              onClick={() => onSelect(t.id)}
              style={{ animationDelay: `${idx * 30}ms` }}
            >
              <span className="adm-table__col adm-table__col--id">{t.id}</span>
              <span className="adm-table__col adm-table__col--priority">
                <span className={`adm-priority ${PRIORITY_COLORS[t.priority] || ''}`}>
                  {PRIORITY_LABELS[t.priority] || t.priority}
                </span>
              </span>
              <span className="adm-table__col adm-table__col--subject">
                {t.subject}
                {t.unread_count > 0 && <span className="adm-unread-dot" />}
              </span>
              <span className="adm-table__col adm-table__col--user">{t.user_email}</span>
              <span className="adm-table__col adm-table__col--status">
                <span className={`adm-status ${STATUS_COLORS[t.status] || ''}`}>
                  {STATUS_LABELS[t.status] || t.status}
                </span>
              </span>
              <span className="adm-table__col adm-table__col--date">
                {new Date(t.created_at).toLocaleDateString('ru-RU')}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ===================== Admin Ticket Detail =====================
function AdminTicketDetail({ ticketId, onBack }) {
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [messageText, setMessageText] = useState('');
  const [sending, setSending] = useState(false);
  const [files, setFiles] = useState([]);
  const [quickResponses, setQuickResponses] = useState([]);
  const messagesEndRef = useRef(null);
  const v2 = featureFlags.isEnabled('supportV2');

  const loadTicket = useCallback(async () => {
    try {
      const res = await supportApi.getTicket(ticketId);
      setTicket(res.data);
      supportApi.markRead(ticketId).catch(() => {});
    } catch { /* ignore */ } finally { setLoading(false); }
  }, [ticketId]);

  useEffect(() => {
    loadTicket();
    supportApi.getQuickResponses().then((r) => setQuickResponses(r.data)).catch(() => {});
    const iv = setInterval(loadTicket, 15000);
    return () => clearInterval(iv);
  }, [loadTicket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [ticket?.messages]);

  const handleSend = async () => {
    if (!messageText.trim() && files.length === 0) return;
    setSending(true);
    try {
      let attachmentIds = [];
      if (files.length > 0 && v2) attachmentIds = await uploadFiles(files, setFiles);
      await supportApi.addMessage(ticketId, messageText, attachmentIds);
      setMessageText('');
      setFiles([]);
      await loadTicket();
    } catch { /* ignore */ } finally { setSending(false); }
  };

  const handleAssign = async () => { await supportApi.assign(ticketId); loadTicket(); };
  const handleResolve = async () => { await supportApi.resolve(ticketId); loadTicket(); };
  const handleReopen = async () => { await supportApi.reopen(ticketId); loadTicket(); };
  const handlePriority = async (p) => { await supportApi.setPriority(ticketId, p); loadTicket(); };

  if (loading) {
    return (
      <div className="adm-detail">
        <div className="adm-detail__header">
          <button className="sp-btn sp-btn--icon" onClick={onBack}><ArrowLeftIcon /></button>
          <div className="adm-skeleton" style={{ width: 250, height: 20 }} />
        </div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="adm-detail">
        <div className="adm-detail__header">
          <button className="sp-btn sp-btn--icon" onClick={onBack}><ArrowLeftIcon /></button>
          <span>Тикет не найден</span>
        </div>
      </div>
    );
  }

  const isResolved = ['resolved', 'closed'].includes(ticket.status);

  return (
    <div className="adm-detail">
      <div className="adm-detail__header">
        <button className="sp-btn sp-btn--icon" onClick={onBack}><ArrowLeftIcon /></button>
        <div className="adm-detail__header-info">
          <span className="adm-detail__title">#{ticket.id} {ticket.subject}</span>
          <div className="adm-detail__meta">
            <span className={`adm-status ${STATUS_COLORS[ticket.status] || ''}`}>
              {STATUS_LABELS[ticket.status]}
            </span>
            <span className={`adm-priority ${PRIORITY_COLORS[ticket.priority] || ''}`}>
              {PRIORITY_LABELS[ticket.priority]}
            </span>
            <span className="adm-detail__user">{ticket.user_email}</span>
          </div>
        </div>
      </div>

      {/* Admin controls */}
      <div className="adm-detail__controls">
        {!ticket.assigned_to && (
          <button className="sp-btn sp-btn--secondary sp-btn--sm" onClick={handleAssign}>
            <UserCheckIcon /> Взять
          </button>
        )}
        <select
          className="adm-select adm-select--sm"
          value={ticket.priority}
          onChange={(e) => handlePriority(e.target.value)}
        >
          {Object.entries(PRIORITY_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        {isResolved ? (
          <button className="sp-btn sp-btn--secondary sp-btn--sm" onClick={handleReopen}>Переоткрыть</button>
        ) : (
          <button className="sp-btn sp-btn--success sp-btn--sm" onClick={handleResolve}>Решён</button>
        )}
      </div>

      {/* Tech context */}
      {(ticket.browser_info || ticket.build_version || ticket.page_url) && (
        <details className="adm-detail__tech">
          <summary>Техническая информация</summary>
          <div className="adm-detail__tech-grid">
            {ticket.page_url && <div><strong>URL:</strong> {ticket.page_url}</div>}
            {ticket.browser_info && <div><strong>Браузер:</strong> {ticket.browser_info}</div>}
            {ticket.build_version && <div><strong>Билд:</strong> {ticket.build_version}</div>}
            {ticket.error_message && <div><strong>Ошибка:</strong> {ticket.error_message}</div>}
          </div>
        </details>
      )}

      {/* Messages */}
      <div className="adm-detail__messages">
        <div className="sp-message sp-message--user">
          <div className="sp-message__bubble">
            <div className="sp-message__text">{ticket.description}</div>
            {ticket.ticket_attachments?.map((att) => (
              <a key={att.id} href={att.url} target="_blank" rel="noopener noreferrer" className="sp-message__attachment">
                {att.original_name}
              </a>
            ))}
          </div>
          <span className="sp-message__time">{new Date(ticket.created_at).toLocaleString('ru-RU')}</span>
        </div>

        {ticket.messages?.map((msg) => (
          <div key={msg.id} className={`sp-message ${msg.is_staff_reply ? 'sp-message--staff' : 'sp-message--user'}`}>
            <div className="sp-message__bubble">
              {msg.is_staff_reply && <span className="sp-message__author">{msg.author_name}</span>}
              <div className="sp-message__text">{msg.message}</div>
              {msg.attachments?.map((att) => (
                <a key={att.id} href={att.url} target="_blank" rel="noopener noreferrer" className="sp-message__attachment">
                  {att.original_name}
                </a>
              ))}
            </div>
            <span className="sp-message__time">{new Date(msg.created_at).toLocaleString('ru-RU')}</span>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Reply area */}
      {!isResolved && (
        <div className="adm-detail__reply">
          {quickResponses.length > 0 && (
            <div className="adm-detail__quick">
              {quickResponses.map((qr) => (
                <button
                  key={qr.id}
                  className="adm-quick-btn"
                  onClick={() => setMessageText(qr.message)}
                  title={qr.message}
                >
                  {qr.title}
                </button>
              ))}
            </div>
          )}
          {v2 && <FileDropzone files={files} onChange={setFiles} maxFiles={5} disabled={sending} />}
          <div className="sp-chat__input-row">
            <textarea
              className="sp-chat__textarea"
              placeholder="Ответ от поддержки..."
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
              }}
              disabled={sending}
              rows={2}
            />
            <button
              className="sp-btn sp-btn--primary sp-btn--icon"
              onClick={handleSend}
              disabled={sending || (!messageText.trim() && files.length === 0)}
            >
              <SendIcon />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ===================== Main =====================
const AdminSupportPage = () => {
  const [view, setView] = useState('list');
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [filters, setFilters] = useState({});

  const loadData = useCallback(async () => {
    try {
      const [ticketsRes, statsRes] = await Promise.all([
        supportApi.getTickets(filters),
        supportApi.getStats(),
      ]);
      setTickets(ticketsRes.data.results || ticketsRes.data);
      setStats(statsRes.data);
    } catch { /* ignore */ } finally { setLoading(false); }
  }, [filters]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  useEffect(() => {
    const iv = setInterval(loadData, 30000);
    return () => clearInterval(iv);
  }, [loadData]);

  if (view === 'detail' && selectedId) {
    return (
      <div className="adm-page">
        <AdminTicketDetail
          ticketId={selectedId}
          onBack={() => { setView('list'); setSelectedId(null); loadData(); }}
        />
      </div>
    );
  }

  return (
    <div className="adm-page">
      <h1 className="adm-page__title">Поддержка</h1>
      <Dashboard stats={stats} />
      <AdminTicketList
        tickets={tickets}
        loading={loading}
        onSelect={(id) => { setSelectedId(id); setView('detail'); }}
        filters={filters}
        setFilters={setFilters}
      />
    </div>
  );
};

export default AdminSupportPage;
