import React, { useEffect, useState } from 'react';
import { getTeacherStatsSummary, getGroups, getLessons, startLesson, startLessonNew, createLesson } from '../apiService';
import LessonAttendance from './LessonAttendance';
import { Notification } from '../shared/components';
import useNotification from '../shared/hooks/useNotification';
import { useNotifications } from '../shared/context/NotificationContext';
import { useAuth } from '../auth';

const TeacherDashboard = () => {
  const { notification, showNotification, closeNotification } = useNotification();
  const { toast } = useNotifications();
  const { logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [groups, setGroups] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [error, setError] = useState(null);
  const [startingLessonId, setStartingLessonId] = useState(null);
  const [showNewLesson, setShowNewLesson] = useState(false);
  const [newLesson, setNewLesson] = useState({ title:'', group:'', start_time:'', end_time:'', topics:'' });
  const [creating, setCreating] = useState(false);
  const [attendanceLessonId, setAttendanceLessonId] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, groupsRes, lessonsRes] = await Promise.all([
          getTeacherStatsSummary(),
          getGroups(),
          getLessons({}),
        ]);
        setStats(statsRes.data);
        setGroups(Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || []);
        setLessons(Array.isArray(lessonsRes.data) ? lessonsRes.data : lessonsRes.data.results || []);
      } catch (e) {
        setError('Ошибка загрузки данных');
      }
    };
    load();
  }, []);

  const handleStartLesson = async (id) => {
    setStartingLessonId(id);
    try {
      // Prefer new zoom pool endpoint; fallback to legacy if busy
      let res;
      try {
        res = await startLessonNew(id);
        showNotification('success', 'Урок запущен', 'Start URL: ' + (res.data.zoom_start_url || res.data.start_url));
      } catch (e) {
        // Fallback legacy
        res = await startLesson(id);
        showNotification('success', 'Урок запущен', res.data.message + '\nStart URL: ' + res.data.start_url);
      }
      // Refresh lessons to reflect zoom links
      const newLessons = await getLessons({});
      setLessons(Array.isArray(newLessons.data) ? newLessons.data : newLessons.data.results || []);
    } catch (e) {
      showNotification('error', 'Ошибка', e.response?.data?.message || 'Ошибка запуска');
    } finally {
      setStartingLessonId(null);
    }
  };

  const openAttendance = (lessonId) => setAttendanceLessonId(lessonId);
  const closeAttendance = (updated) => {
    setAttendanceLessonId(null);
    if (updated) { // refresh lessons to reflect potential changes later if needed
      (async () => {
        const refreshed = await getLessons({});
        setLessons(Array.isArray(refreshed.data) ? refreshed.data : refreshed.data.results || []);
      })();
    }
  };

  const handleCreateLesson = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const payload = {
        title: newLesson.title,
        group: parseInt(newLesson.group, 10),
        start_time: newLesson.start_time,
        end_time: newLesson.end_time,
        topics: newLesson.topics,
      };
      await createLesson(payload);
      const refreshed = await getLessons({});
      setLessons(Array.isArray(refreshed.data) ? refreshed.data : refreshed.data.results || []);
      setShowNewLesson(false);
      setNewLesson({ title:'', group:'', start_time:'', end_time:'', topics:'' });
    } catch (e) {
      toast.error(e.response?.data ? JSON.stringify(e.response.data) : 'Ошибка создания');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div style={{ padding:'1.5rem', maxWidth:1200, margin:'0 auto' }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'1rem' }}>
        <h2>Дашборд преподавателя</h2>
        <button onClick={logout} style={{ background:'#ef4444', color:'#fff', border:'none', padding:'0.5rem 1rem', borderRadius:6 }}>Выход</button>
      </div>
      {error && <div style={{ color:'red' }}>{error}</div>}
      {stats && (
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))', gap:'1rem', marginBottom:'2rem' }}>
          <StatCard label="Всего уроков" value={stats.total_lessons} />
          <StatCard label="Средняя длит. (сек)" value={stats.average_duration_seconds ?? '—'} />
          <StatCard label="Записано" value={`${stats.recorded_lessons} (${stats.recording_ratio_percent}%)`} />
          <StatCard label="Учеников" value={stats.total_students} />
        </div>
      )}
      <section style={{ marginBottom:'2rem' }}>
        <h3>Группы <span style={{fontSize:'0.75rem', fontWeight:400}}>| <a href="/groups/manage" style={{color:'#2563eb', textDecoration:'none'}}>Управление →</a></span></h3>
        <div style={{ display:'flex', flexWrap:'wrap', gap:'0.75rem' }}>
          {groups.map(g => (
            <div key={g.id} style={{ padding:'0.75rem 1rem', background:'#f1f5f9', borderRadius:8, minWidth:160 }}>
              <strong>{g.name}</strong>
              <div style={{ fontSize:'0.75rem', color:'#555' }}>Учеников: {g.students?.length || 0}</div>
            </div>
          ))}
          {groups.length === 0 && <div>Нет групп.</div>}
        </div>
      </section>
      <section>
        <h3>Уроки <span style={{fontSize:'0.8rem', fontWeight:400}}>| <a href="/homework/manage" style={{color:'#2563eb', textDecoration:'none'}}>Домашние задания →</a> | <a href="/recurring-lessons/manage" style={{color:'#2563eb', textDecoration:'none'}}>Регулярные уроки →</a></span></h3>
        <div style={{ marginBottom:'0.75rem' }}>
          <button onClick={()=>setShowNewLesson(s=>!s)} style={{ background:'#10b981', color:'#fff', border:'none', padding:'0.45rem 0.9rem', borderRadius:6 }}>
            {showNewLesson ? 'Отмена' : '➕ Новый урок'}
          </button>
        </div>
        {showNewLesson && (
          <form onSubmit={handleCreateLesson} style={{ background:'#f8fafc', padding:'0.9rem 1rem', border:'1px solid #e2e8f0', borderRadius:8, marginBottom:'1rem', display:'grid', gap:'0.6rem' }}>
            <div>
              <label style={formLabel}>Название</label>
              <input style={inputStyle} required value={newLesson.title} onChange={e=>setNewLesson({...newLesson,title:e.target.value})} />
            </div>
            <div>
              <label style={formLabel}>Группа</label>
              <select style={inputStyle} required value={newLesson.group} onChange={e=>setNewLesson({...newLesson,group:e.target.value})}>
                <option value="" disabled>Выберите группу</option>
                {groups.map(g=> <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'0.6rem' }}>
              <div>
                <label style={formLabel}>Начало</label>
                <input style={inputStyle} type="datetime-local" required value={newLesson.start_time} onChange={e=>setNewLesson({...newLesson,start_time:e.target.value})} />
              </div>
              <div>
                <label style={formLabel}>Окончание</label>
                <input style={inputStyle} type="datetime-local" required value={newLesson.end_time} onChange={e=>setNewLesson({...newLesson,end_time:e.target.value})} />
              </div>
            </div>
            <div>
              <label style={formLabel}>Темы</label>
              <textarea style={textareaStyle} rows={2} value={newLesson.topics} onChange={e=>setNewLesson({...newLesson,topics:e.target.value})} />
            </div>
            <div>
              <button disabled={creating} type="submit" style={{ background:'#2563eb', color:'#fff', border:'none', padding:'0.55rem 1rem', borderRadius:6 }}>
                {creating ? 'Создание...' : 'Создать урок'}
              </button>
            </div>
          </form>
        )}
        <table style={{ width:'100%', borderCollapse:'collapse' }}>
          <thead>
            <tr style={{ textAlign:'left', borderBottom:'1px solid #ddd' }}>
              <th>Название</th>
              <th>Группа</th>
              <th>Начало</th>
              <th>Zoom</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {lessons.map(l => (
              <tr key={l.id} style={{ borderBottom:'1px solid #eee' }}>
                <td>{l.title}</td>
                <td>{l.group_name || l.group}</td>
                <td>{new Date(l.start_time).toLocaleString()}</td>
                <td>{l.zoom_start_url ? <a href={l.zoom_start_url} target="_blank" rel="noreferrer">start</a> : '—'}</td>
                <td>
                  {!l.zoom_start_url && (
                    <button disabled={startingLessonId===l.id} onClick={()=>handleStartLesson(l.id)} style={{ background:'#2563eb', color:'#fff', border:'none', padding:'0.4rem 0.75rem', borderRadius:6 }}>
                      {startingLessonId===l.id ? '...' : 'Запустить'}
                    </button>
                  )}
                  {l.zoom_start_url && (
                    <button onClick={()=>openAttendance(l.id)} style={{ marginLeft:'0.4rem', background:'#0d9488', color:'#fff', border:'none', padding:'0.4rem 0.75rem', borderRadius:6 }}>
                      Посещаемость
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {lessons.length === 0 && (
              <tr><td colSpan={5} style={{ padding:'0.75rem' }}>Нет уроков.</td></tr>
            )}
          </tbody>
        </table>
      </section>
      {attendanceLessonId && (
        <LessonAttendance lessonId={attendanceLessonId} onClose={closeAttendance} />
      )}

      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />
    </div>
  );
};

const StatCard = ({ label, value }) => (
  <div style={{ background:'#1e3a8a', color:'#fff', padding:'1rem', borderRadius:10 }}>
    <div style={{ fontSize:'0.75rem', opacity:0.8 }}>{label}</div>
    <div style={{ fontSize:'1.4rem', fontWeight:600 }}>{value}</div>
  </div>
);

const formLabel = { display:'block', fontSize:'0.75rem', fontWeight:600, marginBottom:'0.25rem', textTransform:'uppercase', letterSpacing:'0.5px', color:'#475569' };
const inputStyle = { width:'100%', padding:'0.5rem 0.65rem', border:'1px solid #cbd5e1', borderRadius:6, fontSize:'0.85rem' };
const textareaStyle = { width:'100%', padding:'0.6rem 0.65rem', border:'1px solid #cbd5e1', borderRadius:6, fontSize:'0.85rem', resize:'vertical' };

export default TeacherDashboard;
