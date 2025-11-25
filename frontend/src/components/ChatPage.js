import React, { useState, useEffect } from 'react';
import ChatList from './ChatList';
import ChatThread from './ChatThread';
import GroupChatModal from './GroupChatModal';
import { Button } from '../shared/components';
import './ChatPage.css';

/**
 * Главная страница чата
 * Управляет отображением списка чатов и треда сообщений
 */
const ChatPage = () => {
  const [selectedChat, setSelectedChat] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    loadCurrentUser();
    
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const loadCurrentUser = async () => {
    try {
      const userStr = localStorage.getItem('user');
      if (userStr) {
        const user = JSON.parse(userStr);
        setCurrentUser(user);
      }
    } catch (error) {
      console.error('Ошибка загрузки пользователя:', error);
    }
  };

  const handleChatSelect = (chat) => {
    setSelectedChat(chat);
  };

  const handleBack = () => {
    setSelectedChat(null);
  };

  const handleGroupChatCreated = (newChat) => {
    setSelectedChat(newChat);
    setShowGroupModal(false);
  };

  const isTeacher = currentUser?.role === 'teacher';

  // Мобильная версия: показываем либо список, либо тред
  if (isMobile) {
    return (
      <div className="chat-page mobile">
        {!selectedChat ? (
          <>
            <div className="chat-page-header">
              <Button
                variant="primary"
                onClick={() => setShowGroupModal(true)}
              >
                👥 Создать групповой чат
              </Button>
            </div>
            
            <ChatList
              onChatSelect={handleChatSelect}
              currentUserId={currentUser?.id}
              currentUserRole={currentUser?.role}
            />
          </>
        ) : (
          <ChatThread
            chat={selectedChat}
            currentUserId={currentUser?.id}
            onBack={handleBack}
          />
        )}
        
        <GroupChatModal
          isOpen={showGroupModal}
          onClose={() => setShowGroupModal(false)}
          onSuccess={handleGroupChatCreated}
        />
      </div>
    );
  }

  // Десктопная версия: двухколоночный layout
  return (
    <div className="chat-page desktop">
      <div className="chat-page-sidebar">
        <div className="chat-page-header">
          <Button
            variant="primary"
            size="medium"
            onClick={() => setShowGroupModal(true)}
          >
            👥 Создать групповой чат
          </Button>
        </div>
        
        <ChatList
          onChatSelect={handleChatSelect}
          currentUserId={currentUser?.id}
          currentUserRole={currentUser?.role}
        />
      </div>
      
      <div className="chat-page-main">
        <ChatThread
          chat={selectedChat}
          currentUserId={currentUser?.id}
          onBack={handleBack}
        />
      </div>
      
      <GroupChatModal
        isOpen={showGroupModal}
        onClose={() => setShowGroupModal(false)}
        onSuccess={handleGroupChatCreated}
      />
    </div>
  );
};

export default ChatPage;
