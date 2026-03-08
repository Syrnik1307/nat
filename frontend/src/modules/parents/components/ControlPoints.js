import React from 'react';

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
};

const ControlPoints = ({ controlPoints }) => {
  if (!controlPoints || controlPoints.length === 0) return null;

  return (
    <div className="pd-section">
      <div className="pd-section-title">Контрольные точки</div>
      <div className="pd-cp-grid">
        {controlPoints.map((cp, idx) => (
          <div className="pd-cp-item" key={idx}>
            <div className="pd-cp-title">{cp.title}</div>
            <div className="pd-cp-date">{formatDate(cp.date)}</div>
            <div className="pd-cp-score">
              {cp.points}/{cp.max_points}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ControlPoints;
