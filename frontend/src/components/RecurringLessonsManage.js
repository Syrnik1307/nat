import React, { useEffect, useState } from 'react';
import { getGroups, getRecurringLessons, createRecurringLesson, updateRecurringLesson, deleteRecurringLesson, generateLessonsFromRecurring, getLessons } from '../apiService';

const initialForm = { title:'', group_id:'', day_of_week:'', week_type:'ALL', start_time:'', end_time:'', start_date:'', end_date:'', topics:'', location:'' };

const dayOptions = [
  { value:0, label:'Понедельник' },
  { value:1, label:'Вторник' },
  { value:2, label:'Среда' },
  { value:3, label:'Четверг' },
  { value:4, label:'Пятница' },
  { value:5, label:'Суббота' },
  { value:6, label:'Воскресенье' },
];

const weekTypeOptions = [
  { value:'ALL', label:'Каждая' },
  { value:'UPPER', label:'Верхняя' },
  { value:'LOWER', label:'Нижняя' },
];

const RecurringLessonsManage = () => {
  const [groups, setGroups] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all');

  useEffect(() => {
    const load = async () => {
      try {
        const [groupsRes, recurringRes] = await Promise.all([
          getGroups(),
          getRecurringLessons({}),
        ]);
        setGroups(Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || []);
        setItems(Array.isArray(recurringRes.data) ? recurringRes.data : recurringRes.data.results || []);
      } catch (e) {
        setError('Ошибка загрузки данных');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const refresh = async () => {
    const res = await getRecurringLessons({});
    setItems(Array.isArray(res.data) ? res.data : res.data.results || []);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form, day_of_week: parseInt(form.day_of_week, 10) };
      if (editingId) {
        await updateRecurringLesson(editingId, payload);
      } else {
        await createRecurringLesson(payload);
      }
      await refresh();
      setForm(initialForm);
      setEditingId(null);
    } catch (e) {
      alert(e.response?.data ? JSON.stringify(e.response.data) : 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (item) => {
    setEditingId(item.id);
    setForm({
      title: item.title,
      group_id: item.group?.id || item.group_id,
      day_of_week: item.day_of_week,
      week_type: item.week_type,
      start_time: item.start_time.slice(0,5),
      end_time: item.end_time.slice(0,5),
      start_date: item.start_date,
      end_date: item.end_date,
      topics: item.topics || '',
      location: item.location || '',
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(initialForm);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Удалить регулярный урок?')) return;
    try {
      await deleteRecurringLesson(id);
      await refresh();
    } catch (e) {
      alert('Ошибка удаления');
    }
  };

  if (loading) return <div style={styles.loading}>Загрузка...</div>;
  if (error) return <div style={styles.error}>{error}</div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Регулярные уроки</h1>
        <div className="filter-tabs">
          <button className={`filter-tab ${activeFilter === 'all' ? 'active' : ''}`} onClick={() => setActiveFilter('all')}>Все</button>
          <button className={`filter-tab ${activeFilter === 'upper' ? 'active' : ''}`} onClick={() => setActiveFilter('upper')}>Верхняя неделя</button>
          <button className={`filter-tab ${activeFilter === 'lower' ? 'active' : ''}`} onClick={() => setActiveFilter('lower')}>Нижняя неделя</button>
        </div>
      </div>
      
      <form onSubmit={handleSubmit} className="form-modern">
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Название занятия</label>
            <input className="form-input" required value={form.title} onChange={e=>setForm({ ...form, title:e.target.value })} placeholder="Введите название" />
          </div>
          <div className="form-group">
            <label className="form-label">Группа</label>
            <select className="form-select" required value={form.group_id} onChange={e=>setForm({ ...form, group_id:e.target.value })}>
              <option value="" disabled>Выберите группу</option>
              {groups.map(g=> <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          </div>
        </div>
        
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">День недели</label>
            <select className="form-select" required value={form.day_of_week} onChange={e=>setForm({ ...form, day_of_week:e.target.value })}>
              <option value="" disabled>Выберите день</option>
              {dayOptions.map(d=> <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Периодичность</label>
            <select className="form-select" required value={form.week_type} onChange={e=>setForm({ ...form, week_type:e.target.value })}>
              {weekTypeOptions.map(w=> <option key={w.value} value={w.value}>{w.label}</option>)}
            </select>
          </div>
        </div>
        
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Время начала</label>
            <input className="form-input" type="time" required value={form.start_time} onChange={e=>setForm({ ...form, start_time:e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">Время окончания</label>
            <input className="form-input" type="time" required value={form.end_time} onChange={e=>setForm({ ...form, end_time:e.target.value })} />
          </div>
        </div>
        
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Дата начала</label>
            <input className="form-input" type="date" required value={form.start_date} onChange={e=>setForm({ ...form, start_date:e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">Дата окончания</label>
            <input className="form-input" type="date" required value={form.end_date} onChange={e=>setForm({ ...form, end_date:e.target.value })} />
          </div>
        </div>
        
        {/* Темы занятия удалены по запросу */}
        
        <div style={styles.formActions}>
          <button disabled={saving} type="submit" style={styles.btnPrimary}>
            {saving ? 'Сохранение...' : editingId ? '✓ Сохранить изменения' : '+ Добавить урок'}
          </button>
          {editingId && (
            <button type="button" onClick={cancelEdit} style={styles.btnSecondary}>Отмена</button>
          )}
        </div>
      </form>
      
      <div style={{ marginTop:'2rem' }}>
        <h2 style={styles.sectionTitle}>Список регулярных уроков</h2>
        <table className="table-modern">
          <thead>
            <tr>
              <th>Название</th>
              <th>Группа</th>
              <th>День недели</th>
              <th>Неделя</th>
              <th>Время</th>
              <th>Период</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id}>
                <td style={{ fontWeight:600 }}>{item.title}</td>
                <td>
                  <span className="badge badge-blue">{item.group?.name || '—'}</span>
                </td>
                <td>{item.day_of_week_display}</td>
                <td>
                  <span className={`badge ${item.week_type === 'ALL' ? 'badge-gray' : 'badge-orange'}`}>
                    {item.week_type_display}
                  </span>
                </td>
                <td style={{ color:'#2563eb', fontWeight:600 }}>{item.start_time.slice(0,5)}–{item.end_time.slice(0,5)}</td>
                <td style={{ fontSize:'0.85rem', color:'#6b7280' }}>{item.start_date} → {item.end_date}</td>
                <td>
                  <div style={{ display:'flex', gap:'0.5rem' }}>
                    <button onClick={()=>startEdit(item)} className="btn-icon" title="Редактировать">✏️</button>
                    <button onClick={()=>handleDelete(item.id)} className="btn-icon" title="Удалить">🗑️</button>
                    <button onClick={()=>{
                      const until = window.prompt('Сгенерировать занятия до даты (YYYY-MM-DD):');
                      if (!until) return;
                      const dry = window.confirm('Только посмотреть (dry-run)? OK=Да, Cancel=Создать');
                      generateLessonsFromRecurring(item.id, { until_date: until, dry_run: dry })
                        .then(async res=>{
                          alert(dry ? `Будет создано: ${res.data.would_create_count}` : `Создано занятий: ${res.data.created_count}`);
                          if (!dry) {
                            // Refresh calendar lessons implicitly (not auto-creating zoom meetings)
                            await getLessons({ group: item.group?.id || item.group_id });
                          }
                        })
                        .catch(err=>{
                          alert(err.response?.data?.detail || 'Ошибка генерации');
                        });
                    }} className="btn-icon" title="Сгенерировать занятия (без авто Zoom)">🔄</button>
                  </div>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={7} style={{ textAlign:'center', padding:'2rem', color:'#9ca3af' }}>Нет регулярных уроков</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const styles = {
  loading: {
    textAlign:'center',
    padding:'3rem',
    color:'#6b7280'
  },
  error: {
    textAlign:'center',
    padding:'2rem',
    color:'#dc2626',
    background:'#fef2f2',
    border:'1px solid #fecaca',
    borderRadius:12,
    margin:'2rem'
  },
  sectionTitle: {
    fontSize:'1.25rem',
    fontWeight:600,
    color:'#111827',
    marginBottom:'1rem'
  },
  formActions: {
    display:'flex',
    gap:'0.75rem',
    alignItems:'center',
    marginTop:'0.5rem'
  },
  btnPrimary: {
    background:'#2563eb',
    color:'#fff',
    border:'none',
    padding:'0.75rem 1.5rem',
    borderRadius:8,
    fontSize:'0.95rem',
    cursor:'pointer',
    fontWeight:600,
    transition:'all 0.2s ease'
  },
  btnSecondary: {
    background:'#f3f4f6',
    color:'#374151',
    border:'1px solid #e5e7eb',
    padding:'0.75rem 1.5rem',
    borderRadius:8,
    fontSize:'0.95rem',
    cursor:'pointer',
    fontWeight:500,
    transition:'all 0.2s ease'
  }
};

export default RecurringLessonsManage;
