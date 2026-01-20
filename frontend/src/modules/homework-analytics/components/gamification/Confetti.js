import React from 'react';

// Простая заглушка для эффекта конфетти.
// При желании можно заменить на библиотеку (react-confetti) или кастомную реализацию.
export default function Confetti() {
  return (
    <div aria-hidden="true" style={{pointerEvents: 'none'}}>
      {/* Небольшой визуальный индикатор: можно заменить на анимацию */}
      <div style={{position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'flex-start'}}>
        <span style={{fontSize: 48}}></span>
      </div>
    </div>
  );
}
