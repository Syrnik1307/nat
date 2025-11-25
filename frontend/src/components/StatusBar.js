import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth';
import './StatusBar.css';

const StatusBar = () => {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    loadMessages();
    // Обновляем сообщения каждые 30 секунд
    const interval = setInterval(loadMessages, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (messages.length > 1) {
      // Переключаем сообщения каждые 5 секунд
      const interval = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % messages.length);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [messages.length]);

  const loadMessages = async () => {
    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('http://72.56.81.163:8001/accounts/api/status-messages/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      // Фильтруем только активные сообщения
      const activeMessages = data.filter(msg => msg.is_active);
      setMessages(activeMessages);
    } catch (error) {
      console.error('Ошибка загрузки сообщений статус-бара:', error);
    }
  };

  if (messages.length === 0) {
    return null;
  }

  const currentMessage = messages[currentIndex];

  return (
    <div className="status-bar">
      <div className="status-bar-content">
        <span className="status-bar-icon">📢</span>
        <span className="status-bar-message">{currentMessage.message}</span>
        {messages.length > 1 && (
          <span className="status-bar-counter">
            {currentIndex + 1} / {messages.length}
          </span>
        )}
      </div>
    </div>
  );
};

export default StatusBar;
