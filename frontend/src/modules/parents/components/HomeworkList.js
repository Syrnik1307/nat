import React from 'react';

const statusLabels = {
  done: 'Сдано',
  pending: 'На проверке',
  overdue: 'Просрочено',
  not_submitted: 'Не сдано',
  revision: 'Доработка',
};

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
};

const HomeworkList = ({ homeworkList, selectedMonth, onMonthChange }) => {
  // Generate month options (last 12 months)
  const monthOptions = React.useMemo(() => {
    const options = [];
    const now = new Date();
    for (let i = 0; i < 12; i++) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      const label = d.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' });
      options.push({ value, label });
    }
    return options;
  }, []);

  return (
    <div className="pd-section">
      <div className="pd-section-title">
        <span>Домашние задания</span>
        <select
          className="pd-month-select"
          value={selectedMonth}
          onChange={(e) => onMonthChange(e.target.value)}
        >
          {monthOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {(!homeworkList || homeworkList.length === 0) ? (
        <div className="pd-empty-hw">Нет домашних заданий за этот месяц</div>
      ) : (
        <div className="pd-hw-list">
          {homeworkList.map((hw, idx) => (
            <div className="pd-hw-item" key={idx}>
              <div className="pd-hw-info">
                <div className="pd-hw-title">{hw.title}</div>
                <div className="pd-hw-dates">
                  Задано: {formatDate(hw.assigned_date)}
                  {hw.deadline && ` | Дедлайн: ${formatDate(hw.deadline)}`}
                  {hw.submitted_date && ` | Сдано: ${formatDate(hw.submitted_date)}`}
                </div>
              </div>
              {hw.score != null && (
                <div className="pd-hw-score">
                  {hw.score}/{hw.max_score}
                </div>
              )}
              <span className={`pd-hw-badge pd-hw-badge--${hw.status}`}>
                {statusLabels[hw.status] || hw.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default HomeworkList;
