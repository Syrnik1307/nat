/**
 * SessionTracker — фоновый трекинг времени на платформе.
 * 
 * Механизм:
 * - Отправляет heartbeat POST /api/session/heartbeat/ каждые 60 сек
 * - При закрытии вкладки/выходе отправляет POST /api/session/close/ через sendBeacon
 * - Пауза при неактивной вкладке (visibilitychange)
 * - Автостарт при логине, автостоп при логауте
 * 
 * Использование:
 *   import { sessionTracker } from './sessionTracker';
 *   sessionTracker.start();  // при логине
 *   sessionTracker.stop();   // при логауте
 */
import { apiClient } from './apiService';

const HEARTBEAT_INTERVAL_MS = 60_000; // 60 секунд
const API_BASE = '/api'; // setupProxy добавит /api/

class SessionTracker {
    constructor() {
        this._intervalId = null;
        this._isRunning = false;
        this._isTabVisible = true;
        this._todayMinutes = 0;
        this._sessionMinutes = 0;
        this._listeners = new Set();
        
        // Привязка обработчиков
        this._handleVisibilityChange = this._handleVisibilityChange.bind(this);
        this._handleBeforeUnload = this._handleBeforeUnload.bind(this);
    }
    
    /**
     * Запускает трекинг. Вызывать после успешного логина.
     */
    start() {
        if (this._isRunning) return;
        this._isRunning = true;
        
        // Первый heartbeat сразу
        this._sendHeartbeat();
        
        // Периодический heartbeat
        this._intervalId = setInterval(() => {
            if (this._isTabVisible) {
                this._sendHeartbeat();
            }
        }, HEARTBEAT_INTERVAL_MS);
        
        // Слушаем видимость вкладки
        document.addEventListener('visibilitychange', this._handleVisibilityChange);
        
        // Закрытие сессии при уходе
        window.addEventListener('beforeunload', this._handleBeforeUnload);
    }
    
    /**
     * Останавливает трекинг. Вызывать при логауте.
     */
    stop() {
        if (!this._isRunning) return;
        this._isRunning = false;
        
        if (this._intervalId) {
            clearInterval(this._intervalId);
            this._intervalId = null;
        }
        
        document.removeEventListener('visibilitychange', this._handleVisibilityChange);
        window.removeEventListener('beforeunload', this._handleBeforeUnload);
        
        // Отправляем close
        this._closeSession();
        
        this._todayMinutes = 0;
        this._sessionMinutes = 0;
    }
    
    /**
     * Подписка на обновления времени.
     * callback получает { todayMinutes, sessionMinutes }
     */
    subscribe(callback) {
        this._listeners.add(callback);
        // Немедленно сообщим текущее значение
        callback({ todayMinutes: this._todayMinutes, sessionMinutes: this._sessionMinutes });
        return () => this._listeners.delete(callback);
    }
    
    /**
     * Текущее время за сегодня в минутах.
     */
    get todayMinutes() {
        return this._todayMinutes;
    }
    
    /**
     * Текущая длительность сессии в минутах.
     */
    get sessionMinutes() {
        return this._sessionMinutes;
    }
    
    // --- Private ---
    
    async _sendHeartbeat() {
        try {
            const res = await apiClient.post('/session/heartbeat/');
            const data = res.data;
            
            this._todayMinutes = data.today_total_minutes || 0;
            this._sessionMinutes = data.session_duration_minutes || 0;
            
            // Уведомляем подписчиков
            this._notifyListeners();
        } catch (err) {
            // Тихо проглатываем — не ломаем UX из-за трекинга
            // 401 будет обработан interceptor'ом в apiService
            if (err?.response?.status === 401) {
                this.stop();
            }
        }
    }
    
    _closeSession() {
        // Используем sendBeacon для надёжной отправки при закрытии
        const token = localStorage.getItem('tp_access_token');
        if (!token) return;
        
        try {
            const url = `${window.location.origin}/api/session/close/`;
            const blob = new Blob([JSON.stringify({})], { type: 'application/json' });
            
            // sendBeacon не поддерживает заголовки, поэтому запасной вариант
            // Используем fetch с keepalive
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({}),
                keepalive: true,
            }).catch(() => {
                // Fallback: sendBeacon (без auth, сервер закроет по таймауту)
                navigator.sendBeacon?.(url, blob);
            });
        } catch {
            // Ignore - сессия закроется по таймауту (3 мин без heartbeat)
        }
    }
    
    _handleVisibilityChange() {
        this._isTabVisible = !document.hidden;
        
        if (this._isTabVisible && this._isRunning) {
            // Вкладка стала видимой — отправляем heartbeat сразу
            this._sendHeartbeat();
        }
    }
    
    _handleBeforeUnload() {
        this._closeSession();
    }
    
    _notifyListeners() {
        const data = {
            todayMinutes: this._todayMinutes,
            sessionMinutes: this._sessionMinutes,
        };
        this._listeners.forEach(cb => {
            try { cb(data); } catch {}
        });
    }
}

// Singleton instance
export const sessionTracker = new SessionTracker();
export default sessionTracker;
