import React, { useEffect, useState } from 'react';
import { useAuth, Protected } from '../auth';
import { getSubscription, createSubscriptionPayment, cancelSubscription } from '../apiService';

const fmtDate = (iso) => iso ? new Date(iso).toLocaleString() : '-';

export default function SubscriptionPage() {
  const { role } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sub, setSub] = useState(null);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await getSubscription();
      setSub(data);
    } catch (e) {
      setError('Не удалось загрузить подписку');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleBuy = async (plan) => {
    setCreating(true);
    setError('');
    try {
      const { data } = await createSubscriptionPayment(plan);
      setSub(data.subscription);
      const url = data.payment && data.payment.payment_url;
      if (url) window.location.href = url;
    } catch (e) {
      setError('Не удалось создать оплату');
    } finally {
      setCreating(false);
    }
  };

  const handleCancel = async () => {
    setCreating(true);
    setError('');
    try {
      const { data } = await cancelSubscription();
      setSub(data);
    } catch (e) {
      setError('Не удалось отменить подписку');
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <div style={{ padding: '2rem' }}>Загрузка...</div>;
  if (error) return <div style={{ padding: '2rem', color: 'crimson' }}>{error}</div>;

  const isActive = sub?.status === 'active';
  const isPending = sub?.status === 'pending';

  return (
    <div style={{ maxWidth: 800, margin: '2rem auto', padding: '1.5rem', background: 'white', borderRadius: 12, boxShadow: '0 4px 14px rgba(0,0,0,0.08)' }}>
      <h2 style={{ marginTop: 0 }}>Подписка</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <div><strong>План:</strong> {sub?.plan}</div>
          <div><strong>Статус:</strong> {sub?.status}</div>
          <div><strong>Начало:</strong> {fmtDate(sub?.started_at)}</div>
          <div><strong>Истекает:</strong> {fmtDate(sub?.expires_at)}</div>
          <div><strong>Автопродление:</strong> {sub?.auto_renew ? 'вкл' : 'выкл'}</div>
          <div><strong>Оплачено всего:</strong> {sub?.total_paid} {sub?.currency || 'RUB'}</div>
        </div>
      </div>

      <div style={{ marginTop: 24, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <button disabled={creating} onClick={() => handleBuy('monthly')} style={btnStyle('primary')}>Оплатить месяц · 990 ₽</button>
        <button disabled={creating} onClick={() => handleBuy('yearly')} style={btnStyle('secondary')}>Оплатить год · 9 900 ₽</button>
        {isActive && (
          <button disabled={creating} onClick={handleCancel} style={btnStyle('danger')}>Отменить автопродление</button>
        )}
        {isPending && <span style={{ color: '#a16207' }}>Ожидание оплаты...</span>}
      </div>
    </div>
  );
}

function btnStyle(variant) {
  const base = {
    padding: '10px 14px',
    borderRadius: 8,
    border: '1px solid transparent',
    cursor: 'pointer',
  };
  if (variant === 'primary') return { ...base, background: '#4F46E5', color: 'white' };
  if (variant === 'secondary') return { ...base, background: '#0EA5E9', color: 'white' };
  if (variant === 'danger') return { ...base, background: '#F43F5E', color: 'white' };
  return base;
}
