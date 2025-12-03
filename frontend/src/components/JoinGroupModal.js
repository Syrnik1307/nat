import React, { useState, useEffect } from 'react';
import { joinGroupByCode, getGroupByInviteCode } from '../apiService';
import '../styles/JoinGroupModal.css';

const JoinGroupModal = ({ onClose, onSuccess, initialCode = '' }) => {
  const [inviteCode, setInviteCode] = useState(initialCode);
  const [loading, setLoading] = useState(false);
  const [loadingGroupInfo, setLoadingGroupInfo] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [groupInfo, setGroupInfo] = useState(null);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    // If initial code provided, load group info and show confirmation
    if (initialCode) {
      loadGroupInfo(initialCode);
    }
  }, [initialCode]);

  const loadGroupInfo = async (code) => {
    setLoadingGroupInfo(true);
    setError('');
    try {
      const response = await getGroupByInviteCode(code);
      setGroupInfo(response.data);
      setShowConfirm(true);
    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Группа с таким кодом не найдена';
      setError(errorMsg);
      setShowConfirm(false);
    } finally {
      setLoadingGroupInfo(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!inviteCode.trim()) {
      setError('Введите код приглашения');
      return;
    }

    // If not showing confirm yet, load group info first
    if (!showConfirm) {
      await loadGroupInfo(inviteCode.trim().toUpperCase());
      return;
    }

    // If confirm shown, proceed with join
    await handleConfirmJoin();
  };

  const handleConfirmJoin = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await joinGroupByCode(inviteCode.trim().toUpperCase());
      setSuccess(response.data.message || 'Вы успешно присоединились к группе!');
      
      setTimeout(() => {
        if (onSuccess) onSuccess(response.data.group);
        onClose();
      }, 1500);
    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Не удалось присоединиться к группе';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="join-modal-overlay" onClick={onClose}>
      <div className="join-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="join-modal-close" onClick={onClose}>×</button>
        
        {!showConfirm ? (
          // Step 1: Enter code
          <>
            <div className="join-modal-icon">🎓</div>
            <h2>Присоединиться к группе</h2>
            <p className="join-modal-subtitle">Введите код приглашения от преподавателя</p>

            <form onSubmit={handleSubmit}>
              <div className="join-input-group">
                <input
                  type="text"
                  className="join-code-input"
                  placeholder="Например: ABC12345"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                  maxLength={8}
                  autoFocus
                  disabled={loadingGroupInfo}
                />
              </div>

              {error && (
                <div className="join-error-message">
                  ⚠️ {error}
                </div>
              )}

              {success && (
                <div className="join-success-message">
                  ✓ {success}
                </div>
              )}

              <div className="join-actions">
                <button 
                  type="button" 
                  className="join-cancel-btn" 
                  onClick={onClose}
                  disabled={loadingGroupInfo}
                >
                  Отмена
                </button>
                <button 
                  type="submit" 
                  className="join-submit-btn"
                  disabled={loadingGroupInfo || !inviteCode.trim()}
                >
                  {loadingGroupInfo ? 'Проверка...' : 'Продолжить'}
                </button>
              </div>
            </form>

            <div className="join-help-text">
              <p>💡 Код приглашения состоит из 8 символов</p>
              <p>Вы можете получить его от преподавателя или отсканировать QR-код</p>
            </div>
          </>
        ) : (
          // Step 2: Confirm join
          <>
            <div className="join-modal-icon">🎓</div>
            <h2>Присоединиться к группе?</h2>
            
            {groupInfo && (
              <div className="join-group-preview">
                <div className="join-group-name">{groupInfo.name}</div>
                {groupInfo.description && (
                  <div className="join-group-description">{groupInfo.description}</div>
                )}
                <div className="join-group-stats">
                  <div className="join-stat">
                    <span className="join-stat-label">Преподаватель:</span>
                    <span className="join-stat-value">
                      {groupInfo.teacher?.first_name || groupInfo.teacher?.email || 'Не указан'}
                    </span>
                  </div>
                  <div className="join-stat">
                    <span className="join-stat-label">Учеников:</span>
                    <span className="join-stat-value">{groupInfo.student_count || 0}</span>
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div className="join-error-message">
                ⚠️ {error}
              </div>
            )}

            {success && (
              <div className="join-success-message">
                ✓ {success}
              </div>
            )}

            <div className="join-actions">
              <button 
                type="button" 
                className="join-cancel-btn" 
                onClick={onClose}
                disabled={loading}
              >
                Отмена
              </button>
              <button 
                type="button"
                className="join-submit-btn"
                onClick={handleConfirmJoin}
                disabled={loading}
              >
                {loading ? 'Присоединение...' : 'Присоединиться'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default JoinGroupModal;
