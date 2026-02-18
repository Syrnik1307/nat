import React, { useEffect, useState } from 'react';
import { getHomework, createSubmission, getSubmissions } from '../apiService';
import { useParams } from 'react-router-dom';
import { useNotifications } from '../shared/context/NotificationContext';

const HomeworkSubmission = () => {
  const { id } = useParams();
  const { toast } = useNotifications();
  const [homework, setHomework] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [answer, setAnswer] = useState('');
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await getHomework(id);
        setHomework(res.data);
        // Optionally check if already submitted
        const subs = await getSubmissions({ homework: id });
        const arr = Array.isArray(subs.data) ? subs.data : subs.data.results || [];
        if (arr.length) setSubmitted(true);
      } catch (e) {
        setError('Ошибка загрузки задания');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!answer.trim()) return;
    setSubmitting(true);
    try {
      await createSubmission({ homework: parseInt(id,10), answers: [{ question_id: null, response_text: answer }] });
      setSubmitted(true);
    } catch (er) {
      toast.error(er.response?.data ? JSON.stringify(er.response.data) : 'Ошибка отправки');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div style={wrap}>Загрузка...</div>;
  if (error) return <div style={wrap} className="error">{error}</div>;
  if (!homework) return <div style={wrap}>Не найдено</div>;

  return (
    <div style={wrap}>
      <h2>{homework.title}</h2>
      <p style={{whiteSpace:'pre-wrap'}}>{homework.description || 'Описание отсутствует.'}</p>
      {submitted ? (
        <div style={infoBox}>Ответ уже отправлен. Спасибо!</div>
      ) : (
        <form onSubmit={handleSubmit} style={form}>
          <label style={label}>Ваш ответ (текстовые вопросы демо)</label>
          <textarea style={textarea} rows={5} value={answer} onChange={e=>setAnswer(e.target.value)} />
          <button disabled={submitting || !answer.trim()} style={btnPrimary}>{submitting ? 'Отправка...' : 'Отправить'}</button>
        </form>
      )}
    </div>
  );
};

const wrap = { padding:'1.5rem', maxWidth:800, margin:'0 auto' };
const form = { display:'grid', gap:'0.75rem', marginTop:'1rem' };
const label = { fontSize:'0.75rem', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.5px' };
const textarea = { width:'100%', padding:'0.6rem 0.7rem', border:'1px solid #cbd5e1', borderRadius:8, fontSize:'0.85rem', resize:'vertical' };
const btnPrimary = { background:'#2563eb', color:'#fff', border:'none', padding:'0.6rem 1.1rem', borderRadius:8, fontWeight:600, cursor:'pointer', fontSize:'0.9rem' };
const infoBox = { background:'#ecfdf5', border:'1px solid #6ee7b7', padding:'0.9rem 1rem', borderRadius:10, color:'#065f46', fontSize:'0.85rem' };

export default HomeworkSubmission;
