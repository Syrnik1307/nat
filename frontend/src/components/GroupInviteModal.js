import React, { useState } from 'react';
import { regenerateGroupInviteCode } from '../apiService';
import '../styles/InviteModal.css';

const GroupInviteModal = ({ group, onClose }) => {
  const [inviteCode, setInviteCode] = useState(group?.invite_code || '');
  const [copied, setCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const inviteLink = `${window.location.origin}/student?code=${inviteCode}`;

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRegenerate = async () => {
    if (!window.confirm('Вы уверены? Старый код перестанет работать.')) return;
    
    setRegenerating(true);
    try {
      const response = await regenerateGroupInviteCode(group.id);
      setInviteCode(response.data.invite_code);
    } catch (error) {
      console.error('Error regenerating code:', error);
      alert('Ошибка при генерации нового кода');
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="invite-modal-overlay" onClick={onClose}>
      <div className="invite-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="invite-modal-close" onClick={onClose}>×</button>
        
        <h2>Пригласить учеников</h2>
        <p className="invite-modal-subtitle">Группа: {group?.name}</p>

        <div className="invite-section">
          <h3>Код приглашения</h3>
          <div className="invite-code-display">
            <span className="invite-code-text">{inviteCode}</span>
            <button 
              className="invite-copy-btn"
              onClick={() => handleCopy(inviteCode)}
            >
              {copied ? '✓ Скопировано' : '📋 Копировать'}
            </button>
          </div>
          <p className="invite-hint">Ученики могут ввести этот код на странице "Мои курсы"</p>
        </div>

        <div className="invite-section">
          <h3>Ссылка-приглашение</h3>
          <div className="invite-link-display">
            <input 
              type="text" 
              value={inviteLink} 
              readOnly 
              className="invite-link-input"
            />
            <button 
              className="invite-copy-btn"
              onClick={() => handleCopy(inviteLink)}
            >
              {copied ? '✓ Скопировано' : '📋 Копировать'}
            </button>
          </div>
        </div>

        <div className="invite-section">
          <h3>QR-код</h3>
          <div className="invite-qr-placeholder">
            <img 
              src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(inviteLink)}`}
              alt="QR Code"
              className="invite-qr-image"
            />
          </div>
          <p className="invite-hint">Покажите QR-код на экране, ученики отсканируют его</p>
        </div>

        <div className="invite-actions">
          <button 
            className="invite-regenerate-btn"
            onClick={handleRegenerate}
            disabled={regenerating}
          >
            {regenerating ? 'Генерация...' : '🔄 Создать новый код'}
          </button>
          <button className="invite-done-btn" onClick={onClose}>
            Готово
          </button>
        </div>
      </div>
    </div>
  );
};

export default GroupInviteModal;
