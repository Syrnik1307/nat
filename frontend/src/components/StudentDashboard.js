import React, { useEffect, useMemo, useState, useRef } from 'react';
import { getStudentStatsSummary } from '../apiService';
import { getCached } from '../utils/dataCache';
import '../styles/dashboard.css';
import '../styles/StudentStats.css';

// SVG Icons (Lucide style)
const IconUsers = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const IconCalendar = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
    <line x1="16" x2="16" y1="2" y2="6"/>
    <line x1="8" x2="8" y1="2" y2="6"/>
    <line x1="3" x2="21" y1="10" y2="10"/>
  </svg>
);

const IconClipboard = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect width="8" height="4" x="8" y="2" rx="1" ry="1"/>
    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
    <path d="m9 14 2 2 4-4"/>
  </svg>
);

const IconAlertTriangle = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>
    <path d="M12 9v4"/>
    <path d="M12 17h.01"/>
  </svg>
);

const StudentDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const initialLoadDone = useRef(false);

  useEffect(() => {
    const load = async (useCache = true) => {
      const cacheTTL = 30000; // 30 секунд

      if (useCache) {
        try {
          const cachedData = await getCached('student:stats', async () => {
            const res = await getStudentStatsSummary();
            return res.data;
          }, cacheTTL);
          setData(cachedData);
          setLoading(false);
          return;
        } catch (e) {
          console.error('Error loading cached stats:', e);
        }
      }

      // Fallback: загружаем без кэша
      try {
        setLoading(true);
        setError(null);
        const res = await getStudentStatsSummary();
        setData(res.data);
      } catch (e) {
        setError('Не удалось загрузить статистику. Попробуйте обновить страницу.');
      } finally {
        setLoading(false);
      }
    };
    load(!initialLoadDone.current);
    initialLoadDone.current = true;
  }, []);

  const overall = data?.overall || null;
  const groups = data?.groups || [];
  const hasGroups = groups.length > 0;

  const overallCards = useMemo(() => {
    const attendancePercent = overall?.attendance_percent;
    const homeworkPercent = overall?.homework_percent;
    const errors = overall?.homework_errors ?? 0;
    const checked = overall?.homework_answers_checked ?? 0;

    return [
      {
        icon: <IconUsers size={22} />,
        label: 'Группы',
        value: overall?.groups_count ?? 0,
        hint: 'Все ваши курсы',
      },
      {
        icon: <IconCalendar size={22} />,
        label: 'Посещаемость',
        value: attendancePercent == null ? '—' : `${attendancePercent}%`,
        hint: `${overall?.attendance_present ?? 0}/${overall?.attendance_total_marked ?? 0} отмечено`,
      },
      {
        icon: <IconClipboard size={22} />,
        label: 'Выполнено ДЗ',
        value: homeworkPercent == null ? '—' : `${homeworkPercent}%`,
        hint: `${overall?.homeworks_completed ?? 0}/${overall?.homeworks_total ?? 0} заданий`,
      },
      {
        icon: <IconAlertTriangle size={22} />,
        label: 'Ошибки в ДЗ',
        value: checked ? errors : '—',
        hint: checked ? `по ${checked} проверенным ответам` : 'нет проверенных ответов',
      },
    ];
  }, [overall]);

  return (
    <div className="student-stats">
      <div className="dashboard-container">
        <div className="student-stats-header">
          <div>
            <h1 className="student-stats-title">Моя статистика</h1>
            <p className="student-stats-subtitle">Посещаемость, выполненное ДЗ и ошибки — по всем группам</p>
          </div>
        </div>

        {error && <div className="student-stats-error">{error}</div>}

        <div className="dashboard-grid">
          {overallCards.map((c) => (
            <div key={c.label} className="stats-card">
              <div className="stats-card-header">
                <div className="stats-card-icon">{c.icon}</div>
              </div>
              <div className="stats-card-value">{loading ? '—' : c.value}</div>
              <div className="stats-card-label">{c.label}</div>
              <div className="stats-card-trend positive">
                <span className="student-stats-muted">{loading ? 'Загрузка…' : c.hint}</span>
              </div>
            </div>
          ))}
        </div>

        <section className="dashboard-section">
          <h2 className="dashboard-section-title">📚 Группы</h2>
          {!loading && !hasGroups && (
            <div className="student-stats-empty">
              <p className="student-stats-empty-title">У вас пока нет групп</p>
              <div>Присоединитесь к группе по коду — и статистика появится автоматически.</div>
            </div>
          )}
          {hasGroups && (
            <div className="stats-card">
              <div style={{ overflowX: 'auto' }}>
                <table className="student-stats-table">
                  <thead>
                    <tr>
                      <th>Группа</th>
                      <th>Преподаватель</th>
                      <th>Посещаемость</th>
                      <th>ДЗ выполнено</th>
                      <th>Ошибки</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groups.map((g) => {
                      const attPct = g.attendance_percent;
                      const hwPct = g.homework_percent;
                      const errors = g.homework_errors ?? 0;
                      const checked = g.homework_answers_checked ?? 0;
                      return (
                        <tr key={g.id}>
                          <td>
                            <div style={{ fontWeight: 800 }}>{g.name}</div>
                            <div className="student-stats-muted">учеников: {g.students_count ?? '—'}</div>
                          </td>
                          <td>
                            <div style={{ fontWeight: 700 }}>
                              {g.teacher?.first_name || g.teacher?.email || '—'}
                            </div>
                          </td>
                          <td>
                            <span className="student-stats-metric">
                              <strong>{attPct == null ? '—' : `${attPct}%`}</strong>
                              <span className="student-stats-muted">({g.attendance_present ?? 0}/{g.attendance_total_marked ?? 0})</span>
                            </span>
                          </td>
                          <td>
                            <span className="student-stats-metric">
                              <strong>{hwPct == null ? '—' : `${hwPct}%`}</strong>
                              <span className="student-stats-muted">({g.homeworks_completed ?? 0}/{g.homeworks_total ?? 0})</span>
                            </span>
                          </td>
                          <td>
                            <span className="student-stats-metric">
                              <strong>{checked ? errors : '—'}</strong>
                              <span className="student-stats-muted">{checked ? `из ${checked} ответов` : 'нет проверок'}</span>
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default StudentDashboard;
