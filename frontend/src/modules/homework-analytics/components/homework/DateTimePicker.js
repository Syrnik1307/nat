import React, { useEffect, useMemo, useRef, useState } from 'react';

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const MONTHS = [
  'Январь',
  'Февраль',
  'Март',
  'Апрель',
  'Май',
  'Июнь',
  'Июль',
  'Август',
  'Сентябрь',
  'Октябрь',
  'Ноябрь',
  'Декабрь',
];
const DAY_IN_MS = 24 * 60 * 60 * 1000;

const pad = (value) => value.toString().padStart(2, '0');

const safeParse = (value) => {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed;
};

const formatLocalValue = (value) => {
  if (!value) {
    return '';
  }
  return [
    `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`,
    `${pad(value.getHours())}:${pad(value.getMinutes())}`,
  ].join('T');
};

const isSameDay = (left, right) => {
  if (!left || !right) {
    return false;
  }
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
};

const startOfWeek = (value) => {
  const clone = new Date(value);
  const weekday = (clone.getDay() + 6) % 7; // Monday-first grid
  clone.setDate(clone.getDate() - weekday);
  clone.setHours(0, 0, 0, 0);
  return clone;
};

const buildCalendarDays = (anchor) => {
  const firstDayOfMonth = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  const gridStart = startOfWeek(firstDayOfMonth);
  const days = [];

  for (let index = 0; index < 42; index += 1) {
    const date = new Date(gridStart);
    date.setDate(gridStart.getDate() + index);
    days.push({
      date,
      isCurrentMonth: date.getMonth() === anchor.getMonth(),
      isToday: isSameDay(date, new Date()),
    });
  }

  return days;
};

const stripTime = (value) => {
  if (!value) {
    return null;
  }
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
};

const getRelativeLabel = (value) => {
  const today = stripTime(new Date());
  const target = stripTime(value);
  if (!today || !target) {
    return '';
  }
  const deltaDays = Math.round((target - today) / DAY_IN_MS);
  if (deltaDays === 0) {
    return 'Сегодня';
  }
  if (deltaDays === 1) {
    return 'Завтра';
  }
  if (deltaDays === -1) {
    return 'Вчера';
  }
  if (deltaDays > 1 && deltaDays < 7) {
    return `Через ${deltaDays} д.`;
  }
  if (deltaDays < -1 && deltaDays > -7) {
    return `${Math.abs(deltaDays)} д. назад`;
  }
  return value.toLocaleDateString('ru-RU', { weekday: 'long' });
};

const QUICK_PRESETS = [
  { label: 'Сегодня вечером', days: 0, hours: 20, minutes: 0 },
  { label: 'Завтра утром', days: 1, hours: 9, minutes: 0 },
  { label: 'Через 3 дня', days: 3, hours: 12, minutes: 0 },
  { label: 'Через неделю', days: 7, hours: 10, minutes: 0 },
];

const DateTimePicker = ({ value, onChange }) => {
  const parsed = useMemo(() => safeParse(value), [value]);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState(parsed);
  const [viewDate, setViewDate] = useState(() => parsed || new Date());
  const [timeState, setTimeState] = useState(() => {
    const base = parsed || new Date();
    return {
      hours: base.getHours(),
      minutes: Math.round(base.getMinutes() / 5) * 5,
    };
  });
  const wrapperRef = useRef(null);

  useEffect(() => {
    setSelectedDate(parsed);
    if (parsed) {
      setViewDate(parsed);
      setTimeState({ hours: parsed.getHours(), minutes: parsed.getMinutes() });
    }
  }, [parsed]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  const calendarDays = useMemo(() => buildCalendarDays(viewDate), [viewDate]);

  const emitChange = (nextDate, customTime) => {
    if (!nextDate) {
      setSelectedDate(null);
      if (onChange) {
        onChange('');
      }
      return;
    }
    const hours = typeof customTime?.hours === 'number' ? customTime.hours : timeState.hours;
    const minutes = typeof customTime?.minutes === 'number' ? customTime.minutes : timeState.minutes;
    const updated = new Date(nextDate);
    updated.setHours(hours, minutes, 0, 0);
    setSelectedDate(updated);
    setTimeState({ hours, minutes });
    if (onChange) {
      onChange(formatLocalValue(updated));
    }
  };

  const handleDaySelect = (day) => {
    emitChange(day);
  };

  const handleMonthShift = (shift) => {
    const next = new Date(viewDate);
    next.setMonth(viewDate.getMonth() + shift);
    setViewDate(next);
  };

  const handleTimeInput = (field, raw) => {
    const numeric = Number(raw);
    if (Number.isNaN(numeric)) {
      return;
    }
    const limits = field === 'hours' ? [0, 23] : [0, 59];
    const valueWithinRange = Math.min(limits[1], Math.max(limits[0], numeric));
    const nextTime = { ...timeState, [field]: valueWithinRange };
    setTimeState(nextTime);
    emitChange(selectedDate || new Date(), nextTime);
  };

  const handleTimeStep = (field, delta) => {
    const max = field === 'hours' ? 23 : 55;
    const step = field === 'hours' ? 1 : 5;
    const wrapAt = field === 'hours' ? 24 : 60;
    const raw = timeState[field] + delta * step;
    const wrapped = (raw % wrapAt + wrapAt) % wrapAt;
    const limited = Math.min(max, wrapped);
    const nextTime = { ...timeState, [field]: limited };
    setTimeState(nextTime);
    emitChange(selectedDate || new Date(), nextTime);
  };

  const handlePreset = ({ days, hours, minutes }) => {
    const base = new Date();
    base.setHours(0, 0, 0, 0);
    base.setDate(base.getDate() + days);
    setViewDate(base);
    emitChange(base, { hours, minutes });
    setIsOpen(false);
  };

  const handleClear = () => {
    setSelectedDate(null);
    if (onChange) {
      onChange('');
    }
  };

  const displayDate = selectedDate
    ? selectedDate.toLocaleDateString('ru-RU', {
        weekday: 'short',
        day: 'numeric',
        month: 'long',
      })
    : 'Выберите дату и время';

  const displayTime = selectedDate
    ? selectedDate.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    : '--:--';

  const helperText = selectedDate ? getRelativeLabel(selectedDate) : 'Кликните, чтобы открыть календарь';

  return (
    <div className="dtp-field" ref={wrapperRef}>
      <label className="form-label">Дедлайн</label>
      <div className={`dtp-display ${isOpen ? 'is-open' : ''} ${selectedDate ? 'is-filled' : ''}`}>
        <button type="button" className="dtp-trigger" onClick={() => setIsOpen((previous) => !previous)}>
          <div>
            <div className="dtp-trigger-label">{displayDate}</div>
            <div className="dtp-trigger-sub">{helperText}</div>
          </div>
          <span className="dtp-trigger-time">{displayTime}</span>
        </button>
        {selectedDate && (
          <button type="button" className="dtp-clear" onClick={handleClear} aria-label="Очистить дедлайн">
            ×
          </button>
        )}
      </div>

      {isOpen && (
        <div className="dtp-popover">
          <div className="dtp-header">
            <button type="button" onClick={() => handleMonthShift(-1)} aria-label="Предыдущий месяц">
              ←
            </button>
            <div>
              <strong>
                {MONTHS[viewDate.getMonth()]}
                {' '}
                {viewDate.getFullYear()}
              </strong>
              <span>{getRelativeLabel(viewDate)}</span>
            </div>
            <button type="button" onClick={() => handleMonthShift(1)} aria-label="Следующий месяц">
              →
            </button>
          </div>

          <div className="dtp-weekdays">
            {WEEKDAYS.map((day) => (
              <span key={day}>{day}</span>
            ))}
          </div>

          <div className="dtp-calendar-grid">
            {calendarDays.map(({ date, isCurrentMonth, isToday }) => {
              const isSelected = selectedDate ? isSameDay(date, selectedDate) : false;
              const classes = [
                'dtp-day',
                isCurrentMonth ? 'current' : 'muted',
                isToday ? 'today' : '',
                isSelected ? 'selected' : '',
              ]
                .filter(Boolean)
                .join(' ');
              return (
                <button key={date.toISOString()} type="button" className={classes} onClick={() => handleDaySelect(date)}>
                  <span>{date.getDate()}</span>
                </button>
              );
            })}
          </div>

          <div className="dtp-chips">
            {QUICK_PRESETS.map((preset) => (
              <button type="button" key={preset.label} onClick={() => handlePreset(preset)}>
                {preset.label}
              </button>
            ))}
          </div>

          <div className="dtp-time-grid">
            <div>
              <span className="dtp-time-label">Часы</span>
              <div className="dtp-spin-group">
                <button type="button" onClick={() => handleTimeStep('hours', -1)} aria-label="Уменьшить часы">
                  −
                </button>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={timeState.hours}
                  onChange={(event) => handleTimeInput('hours', event.target.value)}
                />
                <button type="button" onClick={() => handleTimeStep('hours', 1)} aria-label="Увеличить часы">
                  +
                </button>
              </div>
            </div>
            <div>
              <span className="dtp-time-label">Минуты</span>
              <div className="dtp-spin-group">
                <button type="button" onClick={() => handleTimeStep('minutes', -1)} aria-label="Уменьшить минуты">
                  −
                </button>
                <input
                  type="number"
                  min="0"
                  max="59"
                  step="5"
                  value={timeState.minutes}
                  onChange={(event) => handleTimeInput('minutes', event.target.value)}
                />
                <button type="button" onClick={() => handleTimeStep('minutes', 1)} aria-label="Увеличить минуты">
                  +
                </button>
              </div>
            </div>
          </div>

          <div className="dtp-footer">
            <button type="button" className="gm-btn-surface" onClick={() => setIsOpen(false)}>
              Готово
            </button>
            {!selectedDate && (
              <button type="button" className="gm-btn-primary" onClick={() => emitChange(new Date())}>
                Поставить на сегодня
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DateTimePicker;
