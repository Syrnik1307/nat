import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Button } from '../shared/components';
import './ChatThread.css';

/**
 * Компонент треда сообщений
 * Отображает историю сообщений и форму отправки
 */
const ChatThread = ({ chat, currentUserId, onBack }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (chat) {
      loadMessages();
      markChatAsRead();
      
      // Обновляем сообщения каждые 3 секунды
      const interval = setInterval(loadMessages, 3000);
      return () => clearInterval(interval);
    }
  }, [chat?.id]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadMessages = async () => {
    if (!chat?.id) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `/api/messages/?chat_id=${chat.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMessages(response.data);
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error);
    } finally {
      setLoading(false);
    }
  };

  const markChatAsRead = async () => {
    if (!chat?.id) return;
    
    try {
      const token = localStorage.getItem('access_token');
      await axios.post(
        '/api/messages/mark_chat_as_read/',
        { chat_id: chat.id },
        { headers: { Authorization: `Bearer ${token}` } }
      );
    } catch (error) {
      console.error('Ошибка отметки прочитанным:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    
    if (!newMessage.trim() || sending) return;
    
    setSending(true);
    const messageText = newMessage;
    setNewMessage('');
    
    try {
      const token = localStorage.getItem('access_token');
      await axios.post(
        '/api/messages/',
        {
          chat: chat.id,
          text: messageText
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Сразу загружаем новые сообщения
      await loadMessages();
      inputRef.current?.focus();
    } catch (error) {
      console.error('Ошибка отправки сообщения:', error);
      setNewMessage(messageText); // Возвращаем текст при ошибке
    } finally {
      setSending(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const getChatName = () => {
    if (chat.name) return chat.name;
    
    const otherParticipant = chat.participants.find(p => p.id !== currentUserId);
    if (otherParticipant) {
      return `${otherParticipant.first_name} ${otherParticipant.last_name}`;
    }
    
    return 'Неизвестный чат';
  };

  const getChatSubtitle = () => {
    if (chat.chat_type === 'group') {
      return `${chat.participants.length} участников`;
    }
    
    const otherParticipant = chat.participants.find(p => p.id !== currentUserId);
    return otherParticipant?.username_handle ? `@${otherParticipant.username_handle}` : '';
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    
    if (isToday) {
      return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    }
    
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday = date.toDateString() === yesterday.toDateString();
    
    if (isYesterday) {
      return 'Вчера ' + date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    }
    
    return date.toLocaleDateString('ru-RU', { 
      day: 'numeric', 
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const groupMessagesByDate = (messages) => {
    const groups = {};
    
    messages.forEach(message => {
      const date = new Date(message.created_at);
      const dateKey = date.toDateString();
      
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      groups[dateKey].push(message);
    });
    
    return groups;
  };

  const formatDateHeader = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    
    if (date.toDateString() === now.toDateString()) {
      return 'Сегодня';
    }
    
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (date.toDateString() === yesterday.toDateString()) {
      return 'Вчера';
    }
    
    return date.toLocaleDateString('ru-RU', { 
      day: 'numeric', 
      month: 'long',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(e);
    }
  };

  if (!chat) {
    return (
      <div className="chat-thread-empty">
        <span className="empty-icon">💬</span>
        <p>Выберите чат, чтобы начать общение</p>
      </div>
    );
  }

  const messageGroups = groupMessagesByDate(messages);

  return (
    <div className="chat-thread-container">
      {/* Header */}
      <div className="chat-thread-header">
        <button className="back-button" onClick={onBack}>
          ← Назад
        </button>
        
        <div className="chat-thread-info">
          <div className="chat-thread-avatar">
            {chat.chat_type === 'group' ? '👥' : '👤'}
          </div>
          
          <div className="chat-thread-details">
            <h3 className="chat-thread-name">{getChatName()}</h3>
            <p className="chat-thread-subtitle">{getChatSubtitle()}</p>
          </div>
        </div>
        
        <div className="chat-thread-actions">
          {/* Дополнительные действия могут быть добавлены здесь */}
        </div>
      </div>

      {/* Messages */}
      <div className="chat-thread-messages">
        {loading && messages.length === 0 ? (
          <div className="messages-loading">
            <span className="loader-icon">🔄</span>
            <p>Загрузка сообщений...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="messages-empty">
            <span className="empty-icon">💬</span>
            <p>Пока нет сообщений</p>
            <p className="empty-subtitle">Начните общение!</p>
          </div>
        ) : (
          Object.keys(messageGroups).map(dateKey => (
            <div key={dateKey} className="message-group">
              <div className="message-date-divider">
                <span>{formatDateHeader(dateKey)}</span>
              </div>
              
              {messageGroups[dateKey].map((message, index) => {
                const isOwn = message.sender.id === currentUserId;
                const prevMessage = messageGroups[dateKey][index - 1];
                const showAvatar = !prevMessage || prevMessage.sender.id !== message.sender.id;
                
                return (
                  <div
                    key={message.id}
                    className={`message ${isOwn ? 'own' : 'other'} ${!showAvatar ? 'continuation' : ''}`}
                  >
                    {!isOwn && showAvatar && (
                      <div className="message-avatar">
                        {message.sender.first_name[0]}
                      </div>
                    )}
                    
                    <div className="message-content">
                      {!isOwn && showAvatar && (
                        <div className="message-sender-name">
                          {message.sender.first_name} {message.sender.last_name}
                        </div>
                      )}
                      
                      <div className="message-bubble">
                        <p className="message-text">{message.text}</p>
                        <span className="message-time">{formatTime(message.created_at)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form className="chat-thread-input" onSubmit={sendMessage}>
        <textarea
          ref={inputRef}
          className="message-input"
          placeholder="Введите сообщение..."
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={sending}
        />
        
        <Button
          type="submit"
          variant="primary"
          disabled={!newMessage.trim() || sending}
          loading={sending}
        >
          {sending ? '⏳' : '📤'} Отправить
        </Button>
      </form>
    </div>
  );
};

export default ChatThread;
