import React from 'react';

const ProgressBar = ({ percent = 0 }) => {
  const capped = Math.min(100, Math.max(0, Number(percent) || 0));
  return (
    <div className="ht-progress-bar">
      <div className="ht-progress-track">
        <div className="ht-progress-fill" style={{ width: `${capped}%` }} />
      </div>
      <span className="ht-progress-label">{capped}% выполнено</span>
    </div>
  );
};

export default ProgressBar;
