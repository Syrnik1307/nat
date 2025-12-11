import React, { useEffect, useState } from 'react';
import { getHomeworkList } from '../apiService';
import { Link } from 'react-router-dom';

const HomeworkList = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await getHomeworkList({});
        const arr = Array.isArray(res.data) ? res.data : res.data.results || [];
        setItems(arr);
      } catch (e) {
        setError('Ошибка загрузки домашних заданий');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <div style={wrap}>Загрузка...</div>;
  if (error) return <div style={wrap} className="error">{error}</div>;

  return (
    <div style={wrap}>
      {/* Хлебные крошки */}
      <div style={{fontSize:'0.85rem', color:'#64748b', marginBottom:'1rem'}}>
        <span style={{cursor:'pointer', color:'#2563eb'}} onClick={() => window.history.back()}>← Назад</span>
      </div>
      
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'1.5rem'}}>
        <h2 style={{margin:0}}>Домашние задания</h2>
        <div style={{fontSize:'0.85rem', color:'#64748b'}}>
          Всего заданий: {items.length}
        </div>
      </div>
      
      {items.length === 0 ? (
        <div style={{padding:'3rem', textAlign:'center', background:'#f8fafc', borderRadius:12, border:'1px solid #e2e8f0'}}>
          <div style={{fontSize:'3rem', marginBottom:'1rem'}}>📝</div>
          <h3 style={{color:'#64748b', marginBottom:'0.5rem'}}>Пока нет домашних заданий</h3>
          <p style={{color:'#94a3b8'}}>Ваш преподаватель скоро добавит новые задания</p>
        </div>
      ) : (
        <ul style={list}>
          {items.map(hw => (
            <li key={hw.id} style={li}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:'1rem'}}>
                <div style={{flex:1}}>
                  <strong style={{fontSize:'1.05rem', color:'#1e293b'}}>{hw.title}</strong><br />
                  <div style={{marginTop:'0.5rem', display:'flex', gap:'1rem', alignItems:'center'}}>
                    <small style={{color:'#64748b'}}>Урок: {hw.lesson || hw.lesson_id || 'Не указан'}</small>
                    {hw.deadline && (
                      <small style={{color:'#ef4444', fontWeight:'500'}}>
                        ⏰ Срок: {new Date(hw.deadline).toLocaleDateString('ru-RU')}
                      </small>
                    )}
                    {hw.max_score && (
                      <small style={{color:'#2563eb'}}>
                        🎯 Макс. балл: {hw.max_score}
                      </small>
                    )}
                  </div>
                </div>
                <div style={{display:'flex',gap:'0.5rem'}}>
                  <Link to={`/student/homework/${hw.id}`} style={btnPrimary}>Открыть</Link>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

const wrap = { padding:'1.5rem', maxWidth:900, margin:'0 auto' };
const list = { listStyle:'none', padding:0, margin:0, display:'grid', gap:'0.75rem' };
const li = { background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:12, padding:'0.9rem 1rem' };
const btnPrimary = { background:'#2563eb', color:'#fff', textDecoration:'none', padding:'0.45rem 0.85rem', borderRadius:6, fontSize:'0.85rem' };

export default HomeworkList;
