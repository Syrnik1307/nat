import React, { useEffect, useMemo, useState } from 'react';
import { getStudentStatsSummary } from '../apiService';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import '../styles/dashboard.css';
import '../styles/StudentStats.css';

const StudentDashboard = () => {
  const { logout } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
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
    load();
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
        icon: '👥',
        label: 'Группы',
        value: overall?.groups_count ?? 0,
        hint: 'Все ваши курсы',
      },
      {
        icon: '🗓️',
        label: 'Посещаемость',
        value: attendancePercent == null ? '—' : `${attendancePercent}%`,
        hint: `${overall?.attendance_present ?? 0}/${overall?.attendance_total_marked ?? 0} отмечено`,
      },
      {
        icon: '📝',
        label: 'Выполнено ДЗ',
        value: homeworkPercent == null ? '—' : `${homeworkPercent}%`,
        hint: `${overall?.homeworks_completed ?? 0}/${overall?.homeworks_total ?? 0} заданий`,
      },
      {
        icon: '⚠️',
        label: 'Ошибки в ДЗ',
        value: checked ? errors : '—',
        hint: checked ? `по ${checked} проверенным ответам` : 'нет проверенных ответов',
      },
    ];
  }, [overall]);

  return (
    <div className="student-stats">
      <div className="dashboard-container">
        <div className="student-stats-breadcrumbs">
          <Link to="/student">🏠 Главная</Link>
          {'  ›  '}
          <span>Моя статистика</span>
        </div>

        <div className="student-stats-header">
          <div>
            <h1 className="student-stats-title">Моя статистика</h1>
            <p className="student-stats-subtitle">Посещаемость, выполненное ДЗ и ошибки — по всем группам</p>
          </div>
          <div className="student-stats-actions">
            <button type="button" className="student-stats-btn danger" onClick={logout}>Выход</button>
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
