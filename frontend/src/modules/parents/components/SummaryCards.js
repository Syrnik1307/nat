import React from 'react';

const getColorClass = (value, thresholdGood = 80, thresholdWarn = 50) => {
  if (value >= thresholdGood) return 'pd-card--green';
  if (value >= thresholdWarn) return 'pd-card--yellow';
  return 'pd-card--red';
};

const SummaryCards = ({ subject }) => {
  const {
    total_lessons,
    attended_lessons,
    attendance_pct,
    hw_total,
    hw_done,
    hw_avg_score,
  } = subject;

  const hwDonePct = hw_total > 0 ? Math.round((hw_done / hw_total) * 100) : 0;

  return (
    <div className="pd-summary">
      <div className="pd-card">
        <div className="pd-card-value">{total_lessons}</div>
        <div className="pd-card-label">Уроков</div>
        <div className="pd-card-sub">проведено</div>
      </div>

      <div className={`pd-card ${getColorClass(attendance_pct)}`}>
        <div className="pd-card-value">{attendance_pct}%</div>
        <div className="pd-card-label">Посещаемость</div>
        <div className="pd-card-sub">{attended_lessons}/{total_lessons}</div>
      </div>

      <div className={`pd-card ${getColorClass(hwDonePct)}`}>
        <div className="pd-card-value">{hw_done}/{hw_total}</div>
        <div className="pd-card-label">ДЗ сдано</div>
      </div>

      <div className={`pd-card ${hw_avg_score != null ? getColorClass(hw_avg_score) : ''}`}>
        <div className="pd-card-value">
          {hw_avg_score != null ? `${Math.round(hw_avg_score)}%` : '--'}
        </div>
        <div className="pd-card-label">Средний балл</div>
      </div>
    </div>
  );
};

export default SummaryCards;
