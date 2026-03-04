import React from 'react';

/**
 * ErrorBoundary — ловит JS-ошибки в React-дереве и:
 * 1. Показывает fallback UI вместо белого экрана
 * 2. Отправляет ошибку на бэкенд (→ Telegram алерт)
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    reportError({
      message: error?.message || String(error),
      stack: error?.stack,
      componentStack: errorInfo?.componentStack,
      url: window.location.href,
      source: 'ErrorBoundary',
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '40vh',
          padding: '32px',
          textAlign: 'center',
        }}>
          <h2 style={{ marginBottom: '12px', color: '#1a1a1a' }}>
            Произошла ошибка
          </h2>
          <p style={{ color: '#666', marginBottom: '20px', maxWidth: '400px' }}>
            Что-то пошло не так. Попробуйте обновить страницу.
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 24px',
              background: '#4F46E5',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 500,
            }}
          >
            Обновить страницу
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// --- Глобальный error reporter ---

const ERROR_ENDPOINT = '/api/frontend-errors/';
const THROTTLE_MS = 5000;
const MAX_ERRORS_PER_SESSION = 20;

let lastReportTime = 0;
let errorCount = 0;

function reportError(payload) {
  if (errorCount >= MAX_ERRORS_PER_SESSION) return;
  const now = Date.now();
  if (now - lastReportTime < THROTTLE_MS) return;
  lastReportTime = now;
  errorCount++;

  try {
    const body = JSON.stringify({
      ...payload,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
    });

    // navigator.sendBeacon надёжнее — работает даже при закрытии вкладки
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' });
      navigator.sendBeacon(ERROR_ENDPOINT, blob);
    } else {
      fetch(ERROR_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
      }).catch(() => {});
    }
  } catch {
    // Не падаем из-за ошибки в репортере
  }
}

// Глобальные обработчики (ловят ошибки вне React-дерева)
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    reportError({
      message: event.message,
      stack: event.error?.stack,
      url: window.location.href,
      source: 'window.onerror',
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    reportError({
      message: reason?.message || String(reason),
      stack: reason?.stack,
      url: window.location.href,
      source: 'unhandledrejection',
    });
  });
}

export default ErrorBoundary;
