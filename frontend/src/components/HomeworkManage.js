import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getHomeworkList, createHomework, deleteHomework, getGroups } from '../apiService';

const HomeworkManage = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState({ 
    title:'', 
    description:'', 
    group:'',
    deadline:'',
    max_score:100 
  });

  const load = async () => {
    setLoading(true);
    try {
      const [hwRes, grpRes] = await Promise.all([
        getHomeworkList({}),
        getGroups()
      ]);
      const arr = Array.isArray(hwRes.data) ? hwRes.data : hwRes.data.results || [];
      setItems(arr);
      setGroups(Array.isArray(grpRes.data) ? grpRes.data : grpRes.data.results || []);
    } catch (e) {
      setError('Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  };
  useEffect(()=>{ load(); }, []);

  const submitCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const payload = { 
        title: form.title, 
        description: form.description, 
        group: form.group ? parseInt(form.group,10) : null,
        deadline: form.deadline || null,
        max_score: parseInt(form.max_score, 10) || 100
      };
      await createHomework(payload);
      setForm({ title:'', description:'', group:'', deadline:'', max_score:100 });
      setFormOpen(false);
      load();
    } catch (er) {
      alert(er.response?.data ? JSON.stringify(er.response.data) : 'Ошибка создания');
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Удалить задание?')) return;
    try {
      await deleteHomework(id);
      load();
    } catch (er) {
      alert('Ошибка удаления');
    }
  };

  if (loading) return <div className="page-container"><div style={styles.loading}>Загрузка...</div></div>;
  if (error) return <div className="page-container"><div style={styles.error}>{error}</div></div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Управление домашними заданиями</h1>
      </div>
      
      <div style={{ marginBottom:'1.5rem' }}>
        <button
          onClick={() => navigate('/homework/constructor')}
          style={{ ...styles.btnPrimary, marginRight: '0.75rem', background: '#2563eb' }}
        >
          ⚙️ Конструктор ДЗ
        </button>
        <button onClick={()=>setFormOpen(s=>!s)} style={styles.btnPrimary}>
          {formOpen ? '✕ Отмена' : '➕ Новая точка контроля'}
        </button>
      </div>
      
      {formOpen && (
        <form onSubmit={submitCreate} className="form-modern">
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Название задания</label>
              <input className="form-input" required value={form.title} onChange={e=>setForm({...form,title:e.target.value})} placeholder="Введите название" />
            </div>
            <div className="form-group">
              <label className="form-label">Группа</label>
              <select className="form-select" required value={form.group} onChange={e=>setForm({...form,group:e.target.value})}>
                <option value="">Выберите группу</option>
                {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
            </div>
          </div>
          
          <div className="form-group">
            <label className="form-label">Описание</label>
            <textarea className="form-textarea" rows={4} value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Опишите задание" />
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Дедлайн</label>
              <input className="form-input" type="datetime-local" value={form.deadline} onChange={e=>setForm({...form,deadline:e.target.value})} />
            </div>
            <div className="form-group">
              <label className="form-label">Макс. балл</label>
              <input className="form-input" type="number" value={form.max_score} onChange={e=>setForm({...form,max_score:e.target.value})} />
            </div>
          </div>
          
          <div>
            <button disabled={creating} type="submit" style={styles.btnPrimary}>
              {creating ? 'Создание...' : 'Создать задание'}
            </button>
          </div>
        </form>
      )}
      
      <div style={{ marginTop:'2rem' }}>
        <h2 style={styles.sectionTitle}>Список заданий</h2>
        <div style={styles.homeworkGrid}>
          {items.map(it => (
            <div key={it.id} className="lesson-card">
              <div style={styles.hwHeader}>
                <div>
                  <div className="lesson-title">{it.title}</div>
                  <div style={styles.hwMeta}>
                    <span className="badge badge-blue">{it.group_name || 'Без группы'}</span>
                    {it.deadline && <span style={{color:'#dc2626',fontSize:'0.85rem'}}>⏰ {new Date(it.deadline).toLocaleString('ru-RU')}</span>}
                  </div>
                </div>
                <div style={styles.hwScore}>
                  <span style={{fontSize:'1.5rem',fontWeight:700,color:'#FF6B35'}}>{it.max_score}</span>
                  <span style={{fontSize:'0.75rem',color:'#6b7280'}}>баллов</span>
                </div>
              </div>
              <p style={styles.hwDescription}>{it.description}</p>
              <div style={{ display:'flex', gap:'0.5rem', marginTop:'1rem' }}>
                <button onClick={()=>remove(it.id)} style={styles.btnDanger}>🗑️ Удалить</button>
              </div>
            </div>
          ))}
          {items.length === 0 && (
            <div style={styles.emptyState}>Нет заданий. Создайте первое!</div>
          )}
        </div>
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
    borderRadius:12
  },
  sectionTitle: {
    fontSize:'1.25rem',
    fontWeight:600,
    color:'#111827',
    marginBottom:'1.5rem'
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
  btnDanger: {
    background:'#dc2626',
    color:'#fff',
    border:'none',
    padding:'0.5rem 1rem',
    borderRadius:6,
    fontSize:'0.85rem',
    cursor:'pointer',
    fontWeight:500
  },
  homeworkGrid: {
    display:'grid',
    gap:'1.25rem'
  },
  hwHeader: {
    display:'flex',
    justifyContent:'space-between',
    alignItems:'flex-start',
    marginBottom:'1rem'
  },
  hwMeta: {
    display:'flex',
    gap:'1rem',
    alignItems:'center',
    marginTop:'0.5rem'
  },
  hwScore: {
    display:'flex',
    flexDirection:'column',
    alignItems:'center',
    padding:'0.5rem 1rem',
    background:'#fff7ed',
    borderRadius:8
  },
  hwDescription: {
    color:'#6b7280',
    fontSize:'0.9rem',
    lineHeight:1.6
  },
  emptyState: {
    textAlign:'center',
    padding:'3rem',
    color:'#9ca3af',
    fontSize:'1rem'
  }
};

export default HomeworkManage;
