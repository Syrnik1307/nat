import React, { useCallback, useEffect, useState } from 'react';
import { Modal, Button } from '../../shared/components';
import { apiClient } from '../../apiService';

const fmtDateTime = (iso) => {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('ru-RU');
  } catch {
    return iso;
  }
};

const badgeStyle = (severity) => {
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '2px 8px',
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 600,
    border: '1px solid rgba(255,255,255,0.10)',
    background: 'rgba(255,255,255,0.06)',
    color: 'rgba(255,255,255,0.8)'
  };

  if (severity === 'critical') {
    return { ...base, background: 'rgba(239,68,68,0.12)', color: '#ef4444', borderColor: 'rgba(239,68,68,0.25)' };
  }
  if (severity === 'error') {
    return { ...base, background: 'rgba(245,158,11,0.10)', color: '#f59e0b', borderColor: 'rgba(245,158,11,0.25)' };
  }
  if (severity === 'warning') {
    return { ...base, background: 'rgba(99,102,241,0.10)', color: '#818cf8', borderColor: 'rgba(99,102,241,0.25)' };
  }
  return base;
};

const SystemErrorsModal = ({ onClose }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [counts, setCounts] = useState({ all: 0, critical: 0, error: 0, warning: 0 });

  const [q, setQ] = useState('');
  const [severity, setSeverity] = useState('');
  const [includeResolved, setIncludeResolved] = useState(false);

  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);

  const loadCounts = useCallback(async () => {
    try {
      const res = await apiClient.get('admin/errors/counts/');
      setCounts({
        all: res?.data?.all || 0,
        critical: res?.data?.critical || 0,
        error: res?.data?.error || 0,
        warning: res?.data?.warning || 0,
      });
    } catch (e) {
      console.error(e);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = {
        limit,
        offset,
      };
      if (q.trim()) params.q = q.trim();
      if (severity) params.severity = severity;
      if (includeResolved) params.include_resolved = 1;

      const res = await apiClient.get('admin/errors/', { params });
      setItems(res?.data?.results || []);
      setCount(res?.data?.count || 0);
    } catch (e) {
      console.error(e);
      const data = e?.response?.data;
      const fallback = typeof data === 'string' ? 'Ответ сервера не распознан' : 'Не удалось загрузить ошибки. Попробуйте ещё раз.';
      setError(data?.error || data?.detail || fallback);
    } finally {
      setLoading(false);
    }
  }, [includeResolved, limit, offset, q, severity]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    loadCounts();
  }, [loadCounts]);

  const canPrev = offset > 0;
  const canNext = offset + limit < count;

  return (
    <Modal isOpen onClose={onClose} title="Ошибки" size="fullscreen">
      <div style={{ display: 'grid', gap: 12, minWidth: 900 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px 220px', gap: 10 }}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Поиск: код, источник, текст, email преподавателя"
            style={{
              padding: '10px 12px',
              borderRadius: 10,
              border: '1px solid rgba(255,255,255,0.10)',
              background: 'rgba(255,255,255,0.04)',
              color: '#fff'
            }}
          />
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            style={{
              padding: '10px 12px',
              borderRadius: 10,
              border: '1px solid rgba(255,255,255,0.10)',
              background: 'rgba(255,255,255,0.04)',
              color: '#fff'
            }}
          >
            <option value="">Все уровни</option>
            <option value="warning">warning</option>
            <option value="error">error</option>
            <option value="critical">critical</option>
          </select>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', justifyContent: 'flex-end' }}>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, color: 'rgba(255,255,255,0.8)' }}>
              <input
                type="checkbox"
                checked={includeResolved}
                onChange={(e) => setIncludeResolved(e.target.checked)}
              />
              Показать решённые
            </label>
            <Button variant="secondary" onClick={() => { setOffset(0); load(); loadCounts(); }}>
              Обновить
            </Button>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {[
            { key: '', label: 'Все', count: counts.all },
            { key: 'critical', label: 'Критические', count: counts.critical },
            { key: 'error', label: 'Ошибки', count: counts.error },
            { key: 'warning', label: 'Предупреждения', count: counts.warning },
          ].map((tab) => {
            const isActive = severity === tab.key;
            return (
              <button
                key={tab.key || 'all'}
                type="button"
                onClick={() => { setSeverity(tab.key); setOffset(0); }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  borderRadius: 10,
                  border: isActive ? '1px solid rgba(255,255,255,0.20)' : '1px solid rgba(255,255,255,0.08)',
                  background: isActive ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.03)',
                  color: isActive ? '#fff' : 'rgba(255,255,255,0.75)',
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600
                }}
              >
                <span>{tab.label}</span>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '2px 8px',
                  borderRadius: 999,
                  background: 'rgba(255,255,255,0.08)',
                  color: 'rgba(255,255,255,0.85)',
                  fontSize: 12,
                  fontWeight: 700
                }}>
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>

        {error && (
          <div style={{ padding: 12, borderRadius: 10, background: 'rgba(239,68,68,0.10)', border: '1px solid rgba(239,68,68,0.20)', color: '#ef4444', fontSize: 13 }}>
            {error}
          </div>
        )}

        <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.55)' }}>
          Всего: {count}. Показано: {items.length}.
        </div>

        <div style={{ border: '1px solid rgba(255,255,255,0.08)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '150px 110px 160px 1fr 220px 110px', gap: 0, padding: '10px 12px', background: 'rgba(255,255,255,0.03)', fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
            <div>Время</div>
            <div>Уровень</div>
            <div>Код</div>
            <div>Описание</div>
            <div>Преподаватель</div>
            <div style={{ textAlign: 'right' }}>Повт.</div>
          </div>

          {loading ? (
            <div style={{ padding: 14, color: 'rgba(255,255,255,0.6)', fontSize: 13 }}>
              Загрузка...
            </div>
          ) : items.length === 0 ? (
            <div style={{ padding: 14, color: 'rgba(255,255,255,0.6)', fontSize: 13 }}>
              Ошибок нет.
            </div>
          ) : (
            <div>
              {items.map((it) => {
                const teacher = it.teacher?.name || it.teacher?.email || '—';
                return (
                  <details key={it.id} style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                    <summary
                      style={{
                        listStyle: 'none',
                        cursor: 'pointer',
                        display: 'grid',
                        gridTemplateColumns: '150px 110px 160px 1fr 220px 110px',
                        gap: 0,
                        padding: '12px 12px',
                        fontSize: 13,
                        color: 'rgba(255,255,255,0.85)'
                      }}
                    >
                      <div style={{ color: 'rgba(255,255,255,0.6)' }}>{fmtDateTime(it.last_seen_at)}</div>
                      <div><span style={badgeStyle(it.severity)}>{it.severity}</span></div>
                      <div style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12, color: 'rgba(255,255,255,0.75)' }}>{it.code || '—'}</div>
                      <div style={{ paddingRight: 10 }}>{it.message || '—'}</div>
                      <div style={{ color: 'rgba(255,255,255,0.75)' }}>{teacher}</div>
                      <div style={{ textAlign: 'right', color: 'rgba(255,255,255,0.65)' }}>{it.occurrences || 1}</div>
                    </summary>

                    <div style={{ padding: '0 12px 12px 12px', color: 'rgba(255,255,255,0.75)', fontSize: 13 }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
                        <div>
                          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>Источник</div>
                          <div style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>{it.source || '—'}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>Процесс</div>
                          <div style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>{it.process || '—'}</div>
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 10 }}>
                        <div>
                          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>HTTP</div>
                          <div style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                            {(it.request_method || '—') + ' ' + (it.request_path || '')}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>Первое появление</div>
                          <div style={{ fontSize: 12 }}>{fmtDateTime(it.created_at)}</div>
                        </div>
                      </div>

                      {it.details && Object.keys(it.details).length > 0 && (
                        <div style={{ marginTop: 12 }}>
                          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', marginBottom: 6 }}>Детали</div>
                          <pre style={{ margin: 0, padding: 10, borderRadius: 10, background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.08)', overflow: 'auto', maxHeight: 260, fontSize: 12, color: 'rgba(255,255,255,0.78)' }}>
{JSON.stringify(it.details, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </details>
                );
              })}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <Button
              variant="secondary"
              disabled={!canPrev || loading}
              onClick={() => setOffset((v) => Math.max(0, v - limit))}
            >
              Назад
            </Button>
            <Button
              variant="secondary"
              disabled={!canNext || loading}
              onClick={() => setOffset((v) => v + limit)}
            >
              Вперёд
            </Button>
            <select
              value={limit}
              onChange={(e) => { setLimit(Number(e.target.value)); setOffset(0); }}
              style={{
                padding: '10px 12px',
                borderRadius: 10,
                border: '1px solid rgba(255,255,255,0.10)',
                background: 'rgba(255,255,255,0.04)',
                color: '#fff'
              }}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <Button variant="secondary" onClick={onClose}>Закрыть</Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default SystemErrorsModal;
