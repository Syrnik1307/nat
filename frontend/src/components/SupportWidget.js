import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth';
import './SupportWidget.css';

const SupportWidget = () => {
  const { accessTokenValid } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [tickets, setTickets] = useState([]);
  const [currentTicket, setCurrentTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  
  // Форма нового тикета
  const [showNewTicketForm, setShowNewTicketForm] = useState(false);
  const [newTicket, setNewTicket] = useState({
    subject: '',
    description: '',
    category: 'technical',
    priority: 'normal'
  });

  useEffect(() => {
    if (accessTokenValid) {
      loadTickets();
      loadUnreadCount();
      const interval = setInterval(loadUnreadCount, 30000); // Каждые 30 сек
      return () => clearInterval(interval);
    }
  }, [accessTokenValid]);

  const loadTickets = async () => {
    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('/api/support/tickets/', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setTickets(data.results || data);
      } else if (response.status === 404) {
        // Support module not available - silently disable widget
        return null;
      }
    } catch (err) {
      // Silently fail if support module not available
      return null;
    }
  };

  const loadUnreadCount = async () => {
    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('/api/support/unread-count/', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setUnreadCount(data.unread || data.total || 0);
      } else if (response.status === 404) {
        // Support module not available
        return null;
      }
    } catch (err) {
      // Silently fail if support module not available
      return null;
    }
  };

  const createTicket = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('/api/support/tickets/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ...newTicket,
          page_url: window.location.href,
          user_agent: navigator.userAgent
        })
      });

      if (response.ok) {
        const data = await response.json();
        await loadTickets();
        setShowNewTicketForm(false);
        setNewTicket({
          subject: '',
          description: '',
          category: 'technical',
          priority: 'normal'
        });
        openTicket(data);
      }
    } catch (err) {
      console.error('Error creating ticket:', err);
      alert('Ошибка при создании обращения');
    } finally {
      setLoading(false);
    }
  };

  const openTicket = async (ticket) => {
    setCurrentTicket(ticket);
    setMessages(ticket.messages || []);
    setShowNewTicketForm(false);
    
    // Отметить как прочитанное
    try {
      const token = localStorage.getItem('tp_access_token');
      await fetch(`/api/support/tickets/${ticket.id}/mark_read/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      loadUnreadCount();
    } catch (err) {
      console.error('Error marking as read:', err);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`/api/support/tickets/${currentTicket.id}/add_message/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: newMessage
        })
      });

      if (response.ok) {
        const data = await response.json();
        setMessages([...messages, data]);
        setNewMessage('');
      }
    } catch (err) {
      console.error('Error sending message:', err);
      alert('Ошибка при отправке сообщения');
    } finally {
      setLoading(false);
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'new': return 'Новый';
      case 'in_progress': return 'В работе';
      case 'waiting_user': return 'Ожидает ответа';
      case 'resolved': return 'Решён';
      case 'closed': return 'Закрыт';
      default: return status;
    }
  };

  return (
    <>
      {/* Плавающая кнопка */}
      <button
        className={`support-fab ${isOpen ? 'support-fab-open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="Поддержка"
        aria-label={isOpen ? 'Закрыть чат поддержки' : 'Открыть чат поддержки'}
      >
        {unreadCount > 0 && (
          <span className="support-fab-badge">{unreadCount}</span>
        )}
        {isOpen ? '×' : '💬'}
      </button>

      {/* Виджет поддержки */}
      {isOpen && (
        <div className="support-widget">
          <div className="support-widget-header">
            <h3>💬 Поддержка</h3>
            <button
              className="support-widget-close"
              onClick={() => setIsOpen(false)}
            >
              ×
            </button>
          </div>

          <div className="support-widget-body">
            {!currentTicket && !showNewTicketForm && (
              <>
                <div className="support-tickets-header">
                  <h4>Мои обращения</h4>
                  <button
                    className="support-new-ticket-btn"
                    onClick={() => setShowNewTicketForm(true)}
                  >
                    + Создать
                  </button>
                </div>

                <div className="support-tickets-list">
                  {tickets.length === 0 ? (
                    <div className="support-empty-state">
                      <p>У вас пока нет обращений</p>
                      <button
                        className="support-create-first-btn"
                        onClick={() => setShowNewTicketForm(true)}
                      >
                        Создать первое обращение
                      </button>
                    </div>
                  ) : (
                    tickets.map(ticket => (
                      <div
                        key={ticket.id}
                        className="support-ticket-item"
                        onClick={() => openTicket(ticket)}
                      >
                        <div className="support-ticket-header-row">
                          <span className="support-ticket-id">#{ticket.id}</span>
                          <span
                            className="support-ticket-status"
                            data-status={ticket.status}
                          >
                            {getStatusText(ticket.status)}
                          </span>
                        </div>
                        <h5>{ticket.subject}</h5>
                        <p>{ticket.description.substring(0, 60)}...</p>
                        <small>{new Date(ticket.created_at).toLocaleString('ru-RU')}</small>
                        {ticket.unread_count > 0 && (
                          <span className="support-ticket-unread">{ticket.unread_count} новых</span>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </>
            )}

            {showNewTicketForm && (
              <div className="support-new-ticket-form">
                <button
                  className="support-back-btn"
                  onClick={() => setShowNewTicketForm(false)}
                >
                  ← Назад
                </button>
                <h4>Новое обращение</h4>
                <form onSubmit={createTicket}>
                  <div className="support-form-group">
                    <label>Тема *</label>
                    <input
                      type="text"
                      value={newTicket.subject}
                      onChange={(e) => setNewTicket({...newTicket, subject: e.target.value})}
                      placeholder="Кратко опишите проблему"
                      required
                    />
                  </div>

                  <div className="support-form-group">
                    <label>Описание *</label>
                    <textarea
                      value={newTicket.description}
                      onChange={(e) => setNewTicket({...newTicket, description: e.target.value})}
                      placeholder="Подробно опишите что произошло..."
                      rows="4"
                      required
                    />
                  </div>

                  <div className="support-form-row">
                    <div className="support-form-group">
                      <label>Категория</label>
                      <select
                        value={newTicket.category}
                        onChange={(e) => setNewTicket({...newTicket, category: e.target.value})}
                      >
                        <option value="technical">Техническая проблема</option>
                        <option value="account">Вопрос по аккаунту</option>
                        <option value="feature">Вопрос по функционалу</option>
                        <option value="other">Другое</option>
                      </select>
                    </div>

                    <div className="support-form-group">
                      <label>Приоритет</label>
                      <select
                        value={newTicket.priority}
                        onChange={(e) => setNewTicket({...newTicket, priority: e.target.value})}
                      >
                        <option value="low">Низкий</option>
                        <option value="normal">Обычный</option>
                        <option value="high">Высокий</option>
                        <option value="urgent">Срочный</option>
                      </select>
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="support-submit-btn"
                    disabled={loading}
                  >
                    {loading ? 'Отправка...' : 'Отправить обращение'}
                  </button>
                </form>
              </div>
            )}

            {currentTicket && (
              <div className="support-ticket-chat">
                <button
                  className="support-back-btn"
                  onClick={() => {
                    setCurrentTicket(null);
                    setMessages([]);
                    loadTickets();
                  }}
                >
                  ← Назад к списку
                </button>

                <div className="support-ticket-info">
                  <h4>#{currentTicket.id} {currentTicket.subject}</h4>
                  <span
                    className="support-ticket-status"
                    data-status={currentTicket.status}
                  >
                    {getStatusText(currentTicket.status)}
                  </span>
                </div>

                <div className="support-messages-list">
                  {messages.map(msg => (
                    <div
                      key={msg.id}
                      className={`support-message ${msg.is_staff_reply ? 'support-message-staff' : 'support-message-user'}`}
                    >
                      <div className="support-message-author">{msg.author_name}</div>
                      <div className="support-message-text">{msg.message}</div>
                      <div className="support-message-time">
                        {new Date(msg.created_at).toLocaleString('ru-RU')}
                      </div>
                    </div>
                  ))}
                </div>

                <form onSubmit={sendMessage} className="support-message-form">
                  <textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Введите сообщение..."
                    rows="2"
                    disabled={loading}
                  />
                  <button
                    type="submit"
                    disabled={loading || !newMessage.trim()}
                  >
                    Отправить
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default SupportWidget;
