import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '../shared/components';
import './ChatList.css';

/**
 * Компонент списка чатов с поиском пользователей
 * Показывает активные чаты и непрочитанные сообщения
 */
const ChatList = ({ onChatSelect, currentUserId, currentUserRole }) => {
  const [chats, setChats] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('chats'); // 'chats' | 'search'

  useEffect(() => {
    loadChats();
    // Обновляем список чатов каждые 10 секунд
    const interval = setInterval(loadChats, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (searchQuery.trim().length >= 2) {
      searchUsers();
    } else {
      setSearchResults([]);
    }
  }, [searchQuery]);

  const loadChats = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get('/api/chats/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      // Убеждаемся, что данные - это массив
      setChats(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Ошибка загрузки чатов:', error);
      // При ошибке устанавливаем пустой массив
      setChats([]);
    }
  };

  const searchUsers = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(`/api/users/search/?q=${searchQuery}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSearchResults(response.data);
    } catch (error) {
      console.error('Ошибка поиска пользователей:', error);
    } finally {
      setLoading(false);
    }
  };

  const createPrivateChat = async (userId) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.post(
        '/api/chats/create_private/',
        { user_id: userId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Переключаемся на созданный чат
      onChatSelect(response.data);
      setActiveTab('chats');
      setSearchQuery('');
      loadChats();
    } catch (error) {
      console.error('Ошибка создания чата:', error);
    }
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'только что';
    if (minutes < 60) return `${minutes} мин назад`;
    if (hours < 24) return `${hours} ч назад`;
    if (days < 7) return `${days} д назад`;
    
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  };

  const getChatName = (chat) => {
    if (chat.name) return chat.name;
    
    // Для приватных чатов - имя собеседника
    const otherParticipant = chat.participants.find(p => p.id !== currentUserId);
    if (otherParticipant) {
      return `${otherParticipant.first_name} ${otherParticipant.last_name}`;
    }
    
    return 'Неизвестный чат';
  };

  const getChatUsername = (chat) => {
    if (chat.chat_type === 'group') return null;
    
    const otherParticipant = chat.participants.find(p => p.id !== currentUserId);
    return otherParticipant?.username_handle ? `@${otherParticipant.username_handle}` : null;
  };

  return (
    <div className="chat-list-container">
      <div className="chat-list-header">
        <h2 className="chat-list-title">Сообщения</h2>
        
        <div className="chat-tabs">
          <button
            className={`chat-tab ${activeTab === 'chats' ? 'active' : ''}`}
            onClick={() => setActiveTab('chats')}
          >
            <span className="chat-tab-icon">💬</span>
            Чаты
            {Array.isArray(chats) && chats.some(c => c.unread_count > 0) && (
              <span className="chat-tab-badge">
                {chats.reduce((sum, c) => sum + c.unread_count, 0)}
              </span>
            )}
          </button>
          
          <button
            className={`chat-tab ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            <span className="chat-tab-icon">🔍</span>
            Поиск
          </button>
        </div>
      </div>

      {activeTab === 'chats' ? (
        <div className="chat-list">
          {!Array.isArray(chats) || chats.length === 0 ? (
            <div className="chat-list-empty">
              <span className="empty-icon">💬</span>
              <p>У вас пока нет чатов</p>
              <p className="empty-subtitle">Используйте поиск, чтобы начать общение</p>
            </div>
          ) : (
            chats.map(chat => (
              <div
                key={chat.id}
                className={`chat-item ${chat.unread_count > 0 ? 'unread' : ''}`}
                onClick={() => onChatSelect(chat)}
              >
                <div className="chat-item-avatar">
                  {chat.chat_type === 'group' ? '⚠' : '☎'}
                </div>
                
                <div className="chat-item-content">
                  <div className="chat-item-header">
                    <div className="chat-item-name-wrapper">
                      <span className="chat-item-name">{getChatName(chat)}</span>
                      {getChatUsername(chat) && (
                        <span className="chat-item-username">{getChatUsername(chat)}</span>
                      )}
                    </div>
                    
                    {chat.last_message && (
                      <span className="chat-item-time">
                        {formatTime(chat.last_message.created_at)}
                      </span>
                    )}
                  </div>
                  
                  <div className="chat-item-footer">
                    <p className="chat-item-message">
                      {chat.last_message ? (
                        <>
                          {chat.last_message.sender.id === currentUserId ? (
                            <span className="message-sender">Вы: </span>
                          ) : (
                            <span className="message-sender">
                              {chat.last_message.sender.first_name}: 
                            </span>
                          )}
                          {chat.last_message.text}
                        </>
                      ) : (
                        <span className="no-messages">Нет сообщений</span>
                      )}
                    </p>
                    
                    {chat.unread_count > 0 && (
                      <span className="chat-item-badge">{chat.unread_count}</span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="chat-search">
          <div className="search-input-wrapper">
            <input
              type="text"
              className="search-input"
              placeholder="Поиск по @username, имени или email"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
            />
            {loading && <span className="search-loader">🔄</span>}
          </div>

          {searchQuery.length > 0 && searchQuery.length < 2 && (
            <p className="search-hint">Введите минимум 2 символа</p>
          )}

          <div className="search-results">
            {searchResults.length === 0 && searchQuery.length >= 2 && !loading ? (
              <div className="search-empty">
                <span className="empty-icon">🔍</span>
                <p>Ничего не найдено</p>
              </div>
            ) : (
              searchResults.map(user => (
                <div
                  key={user.id}
                  className="search-result-item"
                  onClick={() => createPrivateChat(user.id)}
                >
                  <div className="search-result-avatar">👤</div>
                  
                  <div className="search-result-content">
                    <div className="search-result-name">
                      {user.first_name} {user.last_name}
                    </div>
                    
                    <div className="search-result-details">
                      {user.username_handle && (
                        <span className="search-result-username">@{user.username_handle}</span>
                      )}
                      <span className="search-result-email">{user.email}</span>
                    </div>
                  </div>
                  
                  <button className="search-result-button">
                    Написать
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatList;
