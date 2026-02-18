import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { 
  joinGroupByCode, 
  getGroupByInviteCode, 
  getIndividualInviteCodeByCode, 
  joinIndividualByCode 
} from '../apiService';
import '../styles/JoinGroupModal.css';

const JoinGroupModal = ({ onClose, onSuccess, initialCode = '' }) => {
  const [inviteCode, setInviteCode] = useState(initialCode);
  const [loading, setLoading] = useState(false);
  const [loadingGroupInfo, setLoadingGroupInfo] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [groupInfo, setGroupInfo] = useState(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isIndividualCode, setIsIndividualCode] = useState(false);

  const normalizedCode = (code) => code.trim().toUpperCase();

  const loadGroupInfo = useCallback(async (code) => {
    const cleanedCode = normalizedCode(code);
    if (!cleanedCode) {
      setError('Введите код приглашения');
      setShowConfirm(false);
      return;
    }

    setLoadingGroupInfo(true);
    setError('');
    setSuccess('');
    setIsIndividualCode(false);
    
    try {
      // Сначала пробуем обычные группы
      const response = await getGroupByInviteCode(cleanedCode);
      setGroupInfo(response.data);
      setShowConfirm(true);
      setInviteCode(cleanedCode);
      setIsIndividualCode(false);
    } catch (err) {
      // Если не нашли обычную группу, пробуем индивидуальный инвайт-код
      try {
        const individualResponse = await getIndividualInviteCodeByCode(cleanedCode);
        const data = individualResponse.data;
        // Преобразуем данные индивидуального кода в формат для отображения
        setGroupInfo({
          name: `Индивидуально • ${data.subject || 'Без предмета'}`,
          description: 'Индивидуальные занятия',
          teacher: data.teacher || {},
          student_count: 0,
          is_individual: true
        });
        setShowConfirm(true);
        setInviteCode(cleanedCode);
        setIsIndividualCode(true);
      } catch (individualErr) {
        // Оба эндпоинта не нашли код
        const errorMsg = err.response?.data?.error || individualErr.response?.data?.error || 'Группа с таким кодом не найдена';
        setError(errorMsg);
        setShowConfirm(false);
      }
    } finally {
      setLoadingGroupInfo(false);
    }
  }, []);

  useEffect(() => {
    if (initialCode) {
      loadGroupInfo(initialCode.trim().toUpperCase());
    }
  }, [initialCode, loadGroupInfo]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!showConfirm) {
      await loadGroupInfo(inviteCode);
      return;
    }

    await handleConfirmJoin();
  };

  const handleConfirmJoin = async () => {
    const cleanedCode = normalizedCode(inviteCode);
    if (!cleanedCode) {
      setError('Введите код приглашения');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // Используем соответствующий эндпоинт в зависимости от типа кода
      const response = isIndividualCode 
        ? await joinIndividualByCode(cleanedCode)
        : await joinGroupByCode(cleanedCode);
      setSuccess(response.data.message || 'Вы успешно присоединились!');

      setTimeout(() => {
        if (onSuccess) onSuccess(response.data.group);
        onClose();
      }, 1200);
    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Не удалось присоединиться';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const content = (
    <div className="join-modal-layer" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="join-modal-shell" onClick={(e) => e.stopPropagation()}>
        <button className="join-modal-close" aria-label="Закрыть" onClick={onClose}>×</button>

        {!showConfirm ? (
          <>
            <h2 className="join-modal-title">Присоединиться к группе</h2>
            <p className="join-modal-subtitle">Введите промокод или код приглашения от преподавателя</p>

            <form onSubmit={handleSubmit} className="join-modal-form">
              <label className="join-field-label" htmlFor="invite-code">Код приглашения</label>
              <input
                id="invite-code"
                type="text"
                className="join-code-input"
                placeholder="Например: ABC12345"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                maxLength={8}
                autoFocus
                disabled={loadingGroupInfo}
              />

              {error && <div className="join-error-message">{error}</div>}
              {success && <div className="join-success-message">{success}</div>}

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
              <p>Код приглашения состоит из 8 символов.</p>
              <p>Получите его у преподавателя или из QR-кода.</p>
            </div>
          </>
        ) : (
          <>
            <h2 className="join-modal-title">
              {isIndividualCode ? 'Присоединиться к занятиям?' : 'Присоединиться к группе?'}
            </h2>

            {groupInfo && (
              <div className="join-group-preview">
                <div className="join-group-name">{groupInfo.name}</div>
                {groupInfo.description && <div className="join-group-description">{groupInfo.description}</div>}
                <div className="join-group-stats">
                  <div className="join-stat">
                    <span className="join-stat-label">Преподаватель</span>
                    <span className="join-stat-value">{groupInfo.teacher?.first_name || groupInfo.teacher?.email || 'Не указан'}</span>
                  </div>
                  {!isIndividualCode && (
                    <div className="join-stat">
                      <span className="join-stat-label">Учеников</span>
                      <span className="join-stat-value">{groupInfo.student_count || 0}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {error && <div className="join-error-message">{error}</div>}
            {success && <div className="join-success-message">✓ {success}</div>}

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

  return createPortal(content, document.body);
};

export default JoinGroupModal;
