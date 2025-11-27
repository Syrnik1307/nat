import React, { useState, useEffect } from 'react';
import './StatusMessages.css';

const StatusMessages = ({ onClose }) => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newMessage, setNewMessage] = useState('');
  const [target, setTarget] = useState('all');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadMessages();
  }, []);

  const loadMessages = async () => {
    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('/accounts/api/admin/status-messages/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      const normalized = Array.isArray(data)
        ? data
        : Array.isArray(data?.results)
          ? data.results
          : [];
      if (!Array.isArray(data)) {
        console.warn('Status messages API returned unexpected shape:', data);
      }
      setMessages(normalized);
      setLoading(false);
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error);
      setLoading(false);
    }
  };

  const handleCreateMessage = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!newMessage.trim()) {
      setError('Введите сообщение');
      return;
    }

    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('/accounts/api/admin/status-messages/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: newMessage,
          target: target
        })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Ошибка создания');
      }

      setSuccess('Сообщение создано!');
      setNewMessage('');
      setTarget('all');
      await loadMessages();

      setTimeout(() => setSuccess(''), 3000);
    } catch (error) {
      setError(error.message);
    }
  };

  const handleDeleteMessage = async (messageId) => {
    if (!window.confirm('Удалить это сообщение?')) {
      return;
    }

    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch(`/accounts/api/admin/status-messages/${messageId}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error('Ошибка удаления');
      }

      await loadMessages();
    } catch (error) {
      alert('Ошибка: ' + error.message);
    }
  };

  const getTargetLabel = (target) => {
    switch (target) {
      case 'teachers': return '👨‍🏫 Учителя';
      case 'students': return '🎓 Ученики';
      case 'all': return '👥 Все';
      default: return target;
    }
  };

  if (loading) {
    return (
      <div className="status-messages-overlay">
        <div className="status-messages-modal">
          <div className="sm-loading">Загрузка...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="status-messages-overlay" onClick={onClose}>
      <div className="status-messages-modal" onClick={(e) => e.stopPropagation()}>
        <div className="sm-header">
          <h2>📢 Сообщения статус-бара</h2>
          <button className="sm-close" onClick={onClose}>✕</button>
        </div>

        <div className="sm-content">
          {/* Форма создания и список */}
          <div className="sm-two-columns">
            {/* Левая колонка: Форма */}
            <div className="sm-column">
              <h3>Новое сообщение</h3>
              <form onSubmit={handleCreateMessage}>
                {error && <div className="form-error">{error}</div>}
                {success && <div className="form-success">{success}</div>}

                <div className="form-group">
                  <label>Сообщение</label>
                  <textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Введите сообщение для пользователей"
                    rows="4"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Для кого</label>
                  <div className="target-buttons">
                    <button
                      type="button"
                      className={`target-btn ${target === 'all' ? 'active' : ''}`}
                      onClick={() => setTarget('all')}
                    >
                      👥 Все
                    </button>
                    <button
                      type="button"
                      className={`target-btn ${target === 'teachers' ? 'active' : ''}`}
                      onClick={() => setTarget('teachers')}
                    >
                      👨‍🏫 Учителя
                    </button>
                    <button
                      type="button"
                      className={`target-btn ${target === 'students' ? 'active' : ''}`}
                      onClick={() => setTarget('students')}
                    >
                      🎓 Ученики
                    </button>
                  </div>
                </div>

                <button type="submit" className="sm-create-btn">
                  📤 Отправить
                </button>
              </form>
            </div>

            {/* Правая колонка: Список сообщений */}
            <div className="sm-column">
              <h3>Активные сообщения ({Array.isArray(messages) ? messages.length : 0})</h3>
              {!Array.isArray(messages) || messages.length === 0 ? (
                <div className="sm-empty">Нет активных сообщений</div>
              ) : (
                <div className="sm-messages">
                  {messages.map((msg) => (
                    <div key={msg.id} className="sm-message-item">
                      <div className="sm-message-header">
                        <span className="sm-message-target">{getTargetLabel(msg.target)}</span>
                        <button
                          className="sm-delete-btn"
                          onClick={() => handleDeleteMessage(msg.id)}
                          title="Удалить"
                        >
                          🗑️
                        </button>
                      </div>
                      <div className="sm-message-text">{msg.message}</div>
                      <div className="sm-message-meta">
                        {new Date(msg.created_at).toLocaleString('ru-RU')}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatusMessages;
