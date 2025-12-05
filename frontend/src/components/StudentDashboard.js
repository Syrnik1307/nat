import React, { useEffect, useState } from 'react';
import { getLessons, getGroups, getHomeworkList, getGradebookForGroup, getSubmissions } from '../apiService';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';

const StudentDashboard = () => {
  const { logout } = useAuth();
  const [groups, setGroups] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [homework, setHomework] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [hwFilter, setHwFilter] = useState('all'); // all | pending | submitted | graded
  const [gradebook, setGradebook] = useState(null);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [groupsRes, lessonsRes, hwRes, subRes] = await Promise.all([
          getGroups(),
          getLessons({}),
          getHomeworkList({}),
          getSubmissions({}),
        ]);
        const groupsList = Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || [];
        setGroups(groupsList);
        setLessons(Array.isArray(lessonsRes.data) ? lessonsRes.data : lessonsRes.data.results || []);
        const hwList = Array.isArray(hwRes.data) ? hwRes.data : hwRes.data.results || [];
        setHomework(hwList);
        const subsList = Array.isArray(subRes.data) ? subRes.data : subRes.data.results || [];
        setSubmissions(subsList);
        if (groupsList.length) {
          setSelectedGroup(groupsList[0].id);
        }
      } catch (e) {
        setError('Ошибка загрузки данных');
      }
    };
    load();
  }, []);

  useEffect(() => {
    const loadGradebook = async () => {
      if (!selectedGroup) { setGradebook(null); return; }
      try {
        const res = await getGradebookForGroup(selectedGroup);
        setGradebook(res.data);
      } catch (e) {
        // ignore
      }
    };
    loadGradebook();
  }, [selectedGroup]);

  // Map homework to submission status
  const submissionIndex = submissions.reduce((acc, s) => { acc[s.homework] = s; return acc; }, {});
  const decoratedHomework = homework.map(hw => {
    const sub = submissionIndex[hw.id];
    return {
      ...hw,
      submission_status: sub ? sub.status : 'not_submitted',
      score: sub ? sub.total_score : null,
    };
  });

  const filteredHomework = decoratedHomework.filter(hw => {
    if (hwFilter === 'all') return true;
    if (hwFilter === 'pending') return hw.submission_status === 'not_submitted';
    if (hwFilter === 'submitted') return hw.submission_status === 'submitted';
    if (hwFilter === 'graded') return hw.submission_status === 'graded';
    return true;
  });

  return (
    <div style={{ padding:'1.5rem', maxWidth:1200, margin:'0 auto' }}>
      {/* Хлебные крошки навигации */}
      <div style={{ fontSize:'0.85rem', color:'#64748b', marginBottom:'1rem' }}>
        <span style={{ cursor:'pointer', color:'#2563eb' }} onClick={() => window.location.href='/student'}>🏠 Главная</span>
        {' > '}
        <span>Мой дашборд</span>
      </div>
      
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'1.5rem' }}>
        <h2 style={{ margin:0 }}>Дашборд ученика</h2>
        <button onClick={logout} style={{ background:'#ef4444', color:'#fff', border:'none', padding:'0.5rem 1rem', borderRadius:6, cursor:'pointer' }}>Выход</button>
      </div>
      {error && <div style={{ background:'#fee2e2', color:'#dc2626', padding:'1rem', borderRadius:8, marginBottom:'1rem' }}>{error}</div>}
      <section style={{ marginBottom:'2rem' }}>
        <h3>Мои группы</h3>
        <div style={{ display:'flex', flexWrap:'wrap', gap:'0.75rem' }}>
          {groups.map(g => (
            <div key={g.id} onClick={()=>setSelectedGroup(g.id)} style={{ cursor:'pointer', padding:'0.75rem 1rem', background: g.id===selectedGroup? '#dbeafe':'#f1f5f9', borderRadius:8, minWidth:160 }}>
              <strong>{g.name}</strong>
              <div style={{ fontSize:'0.75rem', color:'#555' }}>Учеников: {g.students?.length || 0}</div>
            </div>
          ))}
          {groups.length === 0 && <div>Нет групп.</div>}
        </div>
      </section>
      <section style={{ marginBottom:'2rem' }}>
        <h3>Ближайшие занятия</h3>
        {lessons.length === 0 ? (
          <div style={{ padding:'2rem', textAlign:'center', background:'#f8fafc', borderRadius:8, color:'#64748b' }}>
            <div style={{ fontSize:'2rem', marginBottom:'0.5rem' }}>📅</div>
            <div>У вас пока нет запланированных занятий</div>
          </div>
        ) : (
          <ul style={{ listStyle:'none', padding:0 }}>
            {lessons.slice(0,5).map(l => (
              <li key={l.id} style={{ padding:'1rem', borderRadius:8, background:'#f8fafc', marginBottom:'0.5rem', border:'1px solid #e2e8f0' }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <div>
                    <strong style={{ fontSize:'1.05rem', color:'#1e293b' }}>{l.title || 'Занятие'}</strong>
                    <div style={{ fontSize:'0.85rem', color:'#64748b', marginTop:'0.25rem' }}>
                      📅 {new Date(l.start_time).toLocaleString('ru-RU', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      {' · '}
                      👥 {l.group_name || `Группа ${l.group}`}
                    </div>
                  </div>
                  {l.zoom_join_url && (
                    <a href={l.zoom_join_url} target="_blank" rel="noopener noreferrer" style={{ background:'#2563eb', color:'#fff', padding:'0.5rem 1rem', borderRadius:6, textDecoration:'none', fontSize:'0.85rem' }}>
                      ○ Подключиться
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section style={{ marginBottom:'2rem' }}>
        <h3>Домашние задания</h3>
        <div style={{ display:'flex', gap:'0.5rem', marginBottom:'0.6rem', flexWrap:'wrap' }}>
          {['all','pending','submitted','graded'].map(f => (
            <button key={f} onClick={()=>setHwFilter(f)} style={{ background: hwFilter===f? '#2563eb':'#e2e8f0', color: hwFilter===f? '#fff':'#1e293b', border:'none', padding:'0.35rem 0.75rem', borderRadius:6, fontSize:'0.7rem', cursor:'pointer' }}>
              {f==='all' && 'Все'}
              {f==='pending' && 'Не сдано'}
              {f==='submitted' && 'Отправлено'}
              {f==='graded' && 'Проверено'}
            </button>
          ))}
        </div>
        <table style={{ width:'100%', borderCollapse:'collapse' }}>
          <thead>
            <tr style={{ textAlign:'left', borderBottom:'1px solid #ddd' }}>
              <th>Задание</th>
              <th>Статус</th>
              <th>Баллы</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filteredHomework.slice(0,10).map(hw => (
              <tr key={hw.id} style={{ borderBottom:'1px solid #eee' }}>
                <td>{hw.title}</td>
                <td style={{ fontSize:'0.7rem' }}>{
                  hw.submission_status === 'not_submitted' ? 'Не сдано' :
                  hw.submission_status === 'submitted' ? 'Отправлено' :
                  hw.submission_status === 'graded' ? 'Проверено' : hw.submission_status
                }</td>
                <td style={{ fontSize:'0.7rem' }}>{hw.score ?? '—'}</td>
                <td><Link to={`/homework/${hw.id}`} style={{ background:'#2563eb', color:'#fff', textDecoration:'none', padding:'0.3rem 0.6rem', borderRadius:6, fontSize:'0.7rem' }}>Открыть</Link></td>
              </tr>
            ))}
            {filteredHomework.length === 0 && (
              <tr><td colSpan={4} style={{ padding:'0.6rem' }}>Нет заданий.</td></tr>
            )}
          </tbody>
        </table>
        <div style={{ marginTop:'0.5rem' }}>
          <Link to="/homework" style={{ fontSize:'0.75rem', textDecoration:'none', color:'#2563eb' }}>Все задания →</Link>
        </div>
      </section>
      <section>
        <h3>Журнал (Gradebook)</h3>
        {!gradebook && <div>Выберите группу для просмотра журнала.</div>}
        {gradebook && (
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr style={{ textAlign:'left', borderBottom:'1px solid #ddd' }}>
                <th>Ученик</th>
                <th>Посещаемость %</th>
                <th>HW средний</th>
                <th>CP средний</th>
              </tr>
            </thead>
            <tbody>
              {gradebook.students.map(st => (
                <tr key={st.student_id} style={{ borderBottom:'1px solid #eee' }}>
                  <td>{st.student_name || st.student_email}</td>
                  <td>{st.attendance_percent ?? '—'}</td>
                  <td>{st.homework_avg ?? '—'}</td>
                  <td>{st.control_points_avg ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
};

export default StudentDashboard;
