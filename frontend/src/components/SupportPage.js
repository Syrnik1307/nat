import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../auth';
import { supportApi } from '../apiService';
import { featureFlags } from '../config/featureFlags';
import FileDropzone from '../shared/components/FileDropzone';
import './SupportPage.css';

// SVG Icons
const PlusIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
);
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
const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);
const RefreshIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
  </svg>
);

const STATUS_LABELS = {
  new: 'Новый',
  in_progress: 'В работе',
  waiting_user: 'Ожидает ответа',
  resolved: 'Решён',
  closed: 'Закрыт',
};
const STATUS_COLORS = {
  new: 'status--new',
  in_progress: 'status--progress',
  waiting_user: 'status--waiting',
  resolved: 'status--resolved',
  closed: 'status--closed',
};

const FILTER_TABS = [
  { id: 'all', label: 'Все' },
  { id: 'open', label: 'Открытые' },
  { id: 'resolved', label: 'Закрытые' },
];

// ===================== Collect browser context =====================
function collectBrowserContext() {
  return {
    user_agent: navigator.userAgent,
    page_url: window.location.href,
    screen_resolution: `${window.screen.width}x${window.screen.height}`,
    browser_info: `${navigator.language} ${navigator.platform}`,
    build_version: document.querySelector('meta[name="build-version"]')?.content || '',
  };
}

// ===================== Upload helpers =====================
async function uploadFiles(files, setFiles) {
  const updated = [...files];
  const ids = [];
  for (let i = 0; i < updated.length; i++) {
    if (updated[i].id) {
      ids.push(updated[i].id);
      continue;
    }
    updated[i] = { ...updated[i], uploading: true, progress: 0 };
    setFiles([...updated]);
    try {
      const res = await supportApi.uploadFile(updated[i].file, (pct) => {
        updated[i] = { ...updated[i], progress: pct };
        setFiles([...updated]);
      });
      updated[i] = { ...updated[i], id: res.data.id, uploading: false, progress: 100 };
      ids.push(res.data.id);
    } catch (err) {
      updated[i] = { ...updated[i], uploading: false, error: 'Ошибка загрузки' };
    }
    setFiles([...updated]);
  }
  return ids;
}

// ===================== Sub-components =====================

function TicketList({ tickets, loading, filter, setFilter, onSelect, onCreate }) {
  const filtered = tickets.filter((t) => {
    if (filter === 'open') return !['resolved', 'closed'].includes(t.status);
    if (filter === 'resolved') return ['resolved', 'closed'].includes(t.status);
    return true;
  });

  return (
    <div className="sp-list">
      <div className="sp-list__header">
        <h1 className="sp-list__title">Поддержка</h1>
        <button className="sp-btn sp-btn--primary" onClick={onCreate}>
          <PlusIcon /> Создать обращение
        </button>
      </div>

      <div className="sp-tabs">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.id}
            className={`sp-tab ${filter === tab.id ? 'sp-tab--active' : ''}`}
            onClick={() => setFilter(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="sp-list__loading">
          {[1, 2, 3].map((i) => (
            <div key={i} className="sp-skeleton sp-skeleton--ticket" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="sp-empty">
          <p className="sp-empty__text">
            {filter === 'all'
              ? 'У вас пока нет обращений'
              : filter === 'open'
              ? 'Нет открытых обращений'
              : 'Нет закрытых обращений'}
          </p>
          {filter === 'all' && (
            <button className="sp-btn sp-btn--secondary" onClick={onCreate}>
              Создать первое обращение
            </button>
          )}
        </div>
      ) : (
        <div className="sp-list__items">
          {filtered.map((ticket, idx) => (
            <button
              key={ticket.id}
              className="sp-ticket-card"
              onClick={() => onSelect(ticket.id)}
              style={{ animationDelay: `${idx * 40}ms` }}
            >
              <div className="sp-ticket-card__top">
                <span className="sp-ticket-card__id">#{ticket.id}</span>
                <span className={`sp-status ${STATUS_COLORS[ticket.status] || ''}`}>
                  {STATUS_LABELS[ticket.status] || ticket.status}
                </span>
              </div>
              <div className="sp-ticket-card__subject">{ticket.subject}</div>
              <div className="sp-ticket-card__bottom">
                <span className="sp-ticket-card__date">
                  {new Date(ticket.created_at).toLocaleDateString('ru-RU')}
                </span>
                {ticket.unread_count > 0 && (
                  <span className="sp-ticket-card__unread">{ticket.unread_count}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function TicketChat({ ticketId, onBack }) {
  const { user } = useAuth();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [messageText, setMessageText] = useState('');
  const [sending, setSending] = useState(false);
  const [files, setFiles] = useState([]);
  const messagesEndRef = useRef(null);
  const v2 = featureFlags.isEnabled('supportV2');

  const loadTicket = useCallback(async () => {
    try {
      const res = await supportApi.getTicket(ticketId);
      setTicket(res.data);
      supportApi.markRead(ticketId).catch(() => {});
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    loadTicket();
    const interval = setInterval(loadTicket, 15000);
    return () => clearInterval(interval);
  }, [loadTicket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [ticket?.messages]);

  const handleSend = async () => {
    if (!messageText.trim() && files.length === 0) return;
    setSending(true);
    try {
      let attachmentIds = [];
      if (files.length > 0 && v2) {
        attachmentIds = await uploadFiles(files, setFiles);
      }
      await supportApi.addMessage(ticketId, messageText, attachmentIds);
      setMessageText('');
      setFiles([]);
      await loadTicket();
    } catch {
      // ignore
    } finally {
      setSending(false);
    }
  };

  const handleResolve = async () => {
    await supportApi.resolve(ticketId);
    loadTicket();
  };

  const handleReopen = async () => {
    await supportApi.reopen(ticketId);
    loadTicket();
  };

  if (loading) {
    return (
      <div className="sp-chat">
        <div className="sp-chat__header">
          <button className="sp-btn sp-btn--icon" onClick={onBack}><ArrowLeftIcon /></button>
          <div className="sp-skeleton" style={{ width: 200, height: 20 }} />
        </div>
        <div className="sp-chat__body">
          {[1, 2, 3].map((i) => (
            <div key={i} className="sp-skeleton sp-skeleton--message" />
          ))}
        </div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="sp-chat">
        <div className="sp-chat__header">
          <button className="sp-btn sp-btn--icon" onClick={onBack}><ArrowLeftIcon /></button>
          <span>Тикет не найден</span>
        </div>
      </div>
    );
  }

  const isResolved = ['resolved', 'closed'].includes(ticket.status);

  return (
    <div className="sp-chat">
      <div className="sp-chat__header">
        <button className="sp-btn sp-btn--icon" onClick={onBack}><ArrowLeftIcon /></button>
        <div className="sp-chat__header-info">
          <span className="sp-chat__header-subject">{ticket.subject}</span>
          <span className={`sp-status ${STATUS_COLORS[ticket.status] || ''}`}>
            {STATUS_LABELS[ticket.status] || ticket.status}
          </span>
        </div>
        <div className="sp-chat__header-actions">
          {isResolved ? (
            <button className="sp-btn sp-btn--secondary sp-btn--sm" onClick={handleReopen}>
              <RefreshIcon /> Переоткрыть
            </button>
          ) : (
            <button className="sp-btn sp-btn--success sp-btn--sm" onClick={handleResolve}>
              <CheckIcon /> Проблема решена
            </button>
          )}
        </div>
      </div>

      <div className="sp-chat__body">
        {/* Initial ticket message */}
        <div className="sp-message sp-message--user">
          <div className="sp-message__bubble">
            <div className="sp-message__text">{ticket.description}</div>
            {ticket.error_message && (
              <div className="sp-message__meta">Ошибка: {ticket.error_message}</div>
            )}
            {ticket.ticket_attachments?.map((att) => (
              <a key={att.id} href={att.url} target="_blank" rel="noopener noreferrer" className="sp-message__attachment">
                {att.original_name}
              </a>
            ))}
          </div>
          <span className="sp-message__time">
            {new Date(ticket.created_at).toLocaleString('ru-RU')}
          </span>
        </div>

        {/* Messages */}
        {ticket.messages?.map((msg) => (
          <div key={msg.id} className={`sp-message ${msg.is_staff_reply ? 'sp-message--staff' : 'sp-message--user'}`}>
            <div className="sp-message__bubble">
              {msg.is_staff_reply && (
                <span className="sp-message__author">{msg.author_name}</span>
              )}
              <div className="sp-message__text">{msg.message}</div>
              {msg.attachments?.map((att) => (
                <a key={att.id} href={att.url} target="_blank" rel="noopener noreferrer" className="sp-message__attachment">
                  {att.original_name}
                </a>
              ))}
            </div>
            <span className="sp-message__time">
              {new Date(msg.created_at).toLocaleString('ru-RU')}
            </span>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {!isResolved && (
        <div className="sp-chat__input-area">
          {v2 && (
            <FileDropzone files={files} onChange={setFiles} maxFiles={5} disabled={sending} />
          )}
          <div className="sp-chat__input-row">
            <textarea
              className="sp-chat__textarea"
              placeholder="Напишите сообщение..."
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={sending}
              rows={1}
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

function CreateTicketForm({ onCreated, onCancel }) {
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [files, setFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const v2 = featureFlags.isEnabled('supportV2');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!subject.trim() || !description.trim()) {
      setErrorMsg('Заполните тему и описание');
      return;
    }
    setSubmitting(true);
    setErrorMsg('');
    try {
      let attachmentIds = [];
      if (files.length > 0 && v2) {
        attachmentIds = await uploadFiles(files, setFiles);
      }
      const res = await supportApi.createTicket({
        subject: subject.trim(),
        description: description.trim(),
        attachment_ids: attachmentIds,
        ...collectBrowserContext(),
      });
      onCreated(res.data.id);
    } catch (err) {
      setErrorMsg(err?.response?.data?.detail || 'Ошибка при создании обращения');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="sp-create">
      <div className="sp-create__header">
        <button className="sp-btn sp-btn--icon" onClick={onCancel}><ArrowLeftIcon /></button>
        <h2 className="sp-create__title">Новое обращение</h2>
      </div>

      <form className="sp-create__form" onSubmit={handleSubmit}>
        <div className="sp-field">
          <label className="sp-field__label" htmlFor="sp-subject">Тема</label>
          <input
            id="sp-subject"
            className="sp-field__input"
            type="text"
            placeholder="Кратко опишите проблему"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            maxLength={200}
            disabled={submitting}
            autoFocus
          />
        </div>

        <div className="sp-field">
          <label className="sp-field__label" htmlFor="sp-desc">Описание</label>
          <textarea
            id="sp-desc"
            className="sp-field__textarea"
            placeholder="Подробно опишите что произошло, что вы ожидали и как воспроизвести проблему"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={5}
            disabled={submitting}
          />
        </div>

        {v2 && (
          <div className="sp-field">
            <label className="sp-field__label">Скриншоты / файлы</label>
            <FileDropzone files={files} onChange={setFiles} disabled={submitting} />
          </div>
        )}

        {errorMsg && <div className="sp-create__error">{errorMsg}</div>}

        <button
          type="submit"
          className="sp-btn sp-btn--primary sp-btn--lg"
          disabled={submitting}
        >
          {submitting ? 'Отправка...' : 'Отправить'}
        </button>
      </form>
    </div>
  );
}

// ===================== Main Component =====================

const SupportPage = () => {
  const [view, setView] = useState('list');
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [selectedTicketId, setSelectedTicketId] = useState(null);

  const loadTickets = useCallback(async () => {
    try {
      const res = await supportApi.getTickets();
      setTickets(res.data.results || res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTickets();
  }, [loadTickets]);

  const handleSelectTicket = (id) => {
    setSelectedTicketId(id);
    setView('chat');
  };

  const handleBackToList = () => {
    setView('list');
    setSelectedTicketId(null);
    loadTickets();
  };

  const handleCreated = (id) => {
    setSelectedTicketId(id);
    setView('chat');
    loadTickets();
  };

  if (view === 'chat' && selectedTicketId) {
    return (
      <div className="sp-page">
        <TicketChat ticketId={selectedTicketId} onBack={handleBackToList} />
      </div>
    );
  }

  if (view === 'create') {
    return (
      <div className="sp-page">
        <CreateTicketForm onCreated={handleCreated} onCancel={handleBackToList} />
      </div>
    );
  }

  return (
    <div className="sp-page">
      <TicketList
        tickets={tickets}
        loading={loading}
        filter={filter}
        setFilter={setFilter}
        onSelect={handleSelectTicket}
        onCreate={() => setView('create')}
      />
    </div>
  );
};

export default SupportPage;
