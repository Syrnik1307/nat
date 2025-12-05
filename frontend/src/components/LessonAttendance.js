import React, { useEffect, useState } from 'react';
import { getLesson, markLessonAttendance } from '../apiService';
import { Notification } from '../shared/components';
import useNotification from '../shared/hooks/useNotification';

const STATUS_OPTIONS = [
  { value: 'present', label: 'Присутствовал' },
  { value: 'absent', label: 'Отсутствовал' },
  { value: 'excused', label: 'Уважительная причина' },
];

const LessonAttendance = ({ lessonId, onClose }) => {
  const { notification, showNotification, closeNotification } = useNotification();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [students, setStudents] = useState([]);
  const [zoomInfo, setZoomInfo] = useState(null);
  const [attendances, setAttendances] = useState({}); // studentId -> {status, notes}
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await getLesson(lessonId);
        const data = res.data;
        // Extract students from group
        const groupStudents = data.group?.students || [];
        setZoomInfo({
          started: !!data.zoom_start_url,
          join_url: data.zoom_join_url || null,
          start_url: data.zoom_start_url || null,
          meeting_id: data.zoom_meeting_id || null,
          account_email: data.zoom_account_email || data.zoom_account?.email || null
        });
        setStudents(groupStudents);
        // Map existing attendance
        const map = {};
        (data.attendances || []).forEach(a => {
          map[a.student] = { status: a.status, notes: a.notes || '' };
        });
        // Ensure defaults for all group students
        groupStudents.forEach(s => {
          if (!map[s.id]) map[s.id] = { status: 'absent', notes: '' };
        });
        setAttendances(map);
      } catch (e) {
        setError('Ошибка загрузки данных урока');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [lessonId]);

  const updateAttendance = (studentId, field, value) => {
    setAttendances(prev => ({ ...prev, [studentId]: { ...prev[studentId], [field]: value } }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = Object.entries(attendances).map(([studentId, val]) => ({
        student_id: parseInt(studentId, 10),
        status: val.status,
        notes: val.notes,
      }));
      await markLessonAttendance(lessonId, payload);
      showNotification('success', 'Успешно', 'Посещаемость сохранена');
      onClose(true);
    } catch (e) {
      showNotification('error', 'Ошибка', e.response?.data ? JSON.stringify(e.response.data) : 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <ModalFrame title="Посещаемость" onClose={()=>onClose(false)}><div>Загрузка...</div></ModalFrame>;
  }
  if (error) {
    return <ModalFrame title="Посещаемость" onClose={()=>onClose(false)}><div style={{color:'red'}}>{error}</div></ModalFrame>;
  }

  return (
    <ModalFrame title="Посещаемость" onClose={()=>onClose(false)}>
      {zoomInfo && (
        <div style={{ marginBottom:'0.75rem', padding:'0.5rem 0.75rem', background:'#f1f5f9', borderRadius:8, fontSize:'0.8rem' }}>
          <strong>Zoom статус:</strong> {zoomInfo.started ? 'создана' : 'не создана'}
          {zoomInfo.started && (
            <>
              <div style={{ marginTop:'0.35rem' }}>
                <a href={zoomInfo.start_url} target="_blank" rel="noreferrer" style={{ color:'#2563eb', marginRight:'0.75rem' }}>Start (преп.)</a>
                <a href={zoomInfo.join_url} target="_blank" rel="noreferrer" style={{ color:'#0d9488' }}>Join (студ.)</a>
              </div>
              {zoomInfo.account_email && <div style={{ marginTop:'0.3rem', color:'#475569' }}>Аккаунт: {zoomInfo.account_email}</div>}
            </>
          )}
        </div>
      )}
      <div style={{ maxHeight:'50vh', overflowY:'auto' }}>
        <table style={{ width:'100%', borderCollapse:'collapse' }}>
          <thead>
            <tr style={{ textAlign:'left', borderBottom:'1px solid #e2e8f0' }}>
              <th style={th}>Ученик</th>
              <th style={th}>Статус</th>
              <th style={th}>Заметки</th>
            </tr>
          </thead>
          <tbody>
            {students.map(s => (
              <tr key={s.id} style={{ borderBottom:'1px solid #f1f5f9' }}>
                <td style={td}>{(s.first_name || s.last_name) ? `${s.first_name} ${s.last_name}`.trim() : s.email}</td>
                <td style={td}>
                  <select
                    value={attendances[s.id]?.status || 'absent'}
                    onChange={e=>updateAttendance(s.id,'status', e.target.value)}
                    style={select}
                  >
                    {STATUS_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                  </select>
                </td>
                <td style={td}>
                  <input
                    type="text"
                    value={attendances[s.id]?.notes || ''}
                    onChange={e=>updateAttendance(s.id,'notes', e.target.value)}
                    style={input}
                    placeholder="Комментарий"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop:'1rem', display:'flex', justifyContent:'flex-end', gap:'0.5rem' }}>
        <button onClick={()=>onClose(false)} style={btnSecondary}>Отмена</button>
        <button disabled={saving} onClick={handleSave} style={btnPrimary}>{saving ? 'Сохранение...' : 'Сохранить'}</button>
      </div>
    </ModalFrame>
  );
};

const ModalFrame = ({ title, children, onClose }) => (
  <div style={overlay}>
    <div style={modal}>
      <div style={modalHeader}>
        <h4 style={{ margin:0 }}>{title}</h4>
        <button onClick={()=>onClose(false)} style={closeBtn}>×</button>
      </div>
      <div>{children}</div>
      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />
    </div>
  </div>
);

const overlay = { position:'fixed', top:0, left:0, right:0, bottom:0, background:'rgba(0,0,0,0.35)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 };
const modal = { background:'#fff', width:'min(760px, 92%)', borderRadius:12, padding:'1rem 1.25rem', boxShadow:'0 10px 30px rgba(0,0,0,0.25)', maxHeight:'80vh', display:'flex', flexDirection:'column' };
const modalHeader = { display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'0.75rem' };
const closeBtn = { background:'transparent', border:'none', fontSize:'1.3rem', cursor:'pointer', lineHeight:1 };
const th = { padding:'0.5rem 0.4rem', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', color:'#475569' };
const td = { padding:'0.5rem 0.4rem', fontSize:'0.85rem' };
const select = { padding:'0.35rem 0.5rem', fontSize:'0.8rem', border:'1px solid #cbd5e1', borderRadius:6, background:'#fff' };
const input = { width:'100%', padding:'0.35rem 0.5rem', fontSize:'0.8rem', border:'1px solid #cbd5e1', borderRadius:6 };
const btnPrimary = { background:'#2563eb', color:'#fff', border:'none', padding:'0.55rem 1rem', borderRadius:6, fontWeight:600 };
const btnSecondary = { background:'#f1f5f9', color:'#334155', border:'1px solid #cbd5e1', padding:'0.55rem 1rem', borderRadius:6 };

export default LessonAttendance;
