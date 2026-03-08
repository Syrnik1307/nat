import React from 'react';

const TelegramConnect = ({ connected, botLink }) => {
  return (
    <div className="pd-telegram">
      <div className="pd-telegram-info">
        <p className="pd-telegram-title">Уведомления в Telegram</p>
        {connected ? (
          <p className="pd-telegram-connected">Подключено</p>
        ) : (
          <p className="pd-telegram-desc">
            Получайте уведомления о пропущенных ДЗ, оценках и важных событиях
          </p>
        )}
      </div>
      {!connected && botLink && (
        <a
          href={botLink}
          target="_blank"
          rel="noopener noreferrer"
          className="pd-telegram-btn"
        >
          Подключить
        </a>
      )}
    </div>
  );
};

export default TelegramConnect;
