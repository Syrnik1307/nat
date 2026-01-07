import React, { useState, useEffect } from 'react';
import {
  PieChart, Pie, Cell, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';
import { apiClient } from '../../apiService';
import './GroupAnalyticsSummaryTab.css';

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#00C49F', '#FFBB28'];

const GroupAnalyticsSummaryTab = ({ groupId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  const loadSummary = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/dashboard/group-transcript-summary/', {
        params: { group_id: groupId }
      });
      setData(response.data);
    } catch (err) {
      console.error('Failed to load group analytics summary:', err);
      setError('Не удалось загрузить сводную аналитику.');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}м ${secs}с`;
  };

  if (loading) return <div className="tab-loading">Загрузка аналитики...</div>;
  if (error) return <div className="tab-error">{error}</div>;
  if (!data || !data.total_lessons_analyzed) {
    return <div className="tab-empty">Нет данных для аналитики по этой группе (нужны записи с транскрибацией).</div>;
  }

  const { talk_time_leaderboard, mentions_leaderboard, total_lessons_analyzed } = data;

  // Prepare data for charts
  // Top 5 talkers
  const pieData = talk_time_leaderboard.slice(0, 5).map(item => ({
    name: item.name,
    value: Math.round(item.seconds / 60 * 10) / 10 // mins
  }));

  // Top mentions
  const barData = mentions_leaderboard.slice(0, 8);

  return (
    <div className="group-analytics-summary">
      <div className="summary-header">
        <h3>📊 Сводная аналитика</h3>
        <p>Проанализировано уроков: <strong>{total_lessons_analyzed}</strong></p>
      </div>

      <div className="analytics-charts-grid">
        <div className="chart-card">
          <h4>Время речи (Топовые студенты, мин)</h4>
          <div className="chart-container">
             <ResponsiveContainer width="100%" height={250}>
               <PieChart>
                 <Pie
                   data={pieData}
                   cx="50%"
                   cy="50%"
                   outerRadius={80}
                   fill="#8884d8"
                   dataKey="value"
                   label
                 >
                   {pieData.map((entry, index) => (
                     <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                   ))}
                 </Pie>
                 <RechartsTooltip />
                 <Legend />
               </PieChart>
             </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-card">
          <h4>Упоминания имен студента учителем</h4>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={250}>
               <BarChart data={barData} layout="vertical">
                 <CartesianGrid strokeDasharray="3 3" />
                 <XAxis type="number" />
                 <YAxis type="category" dataKey="name" width={100} style={{ fontSize: '12px' }} />
                 <RechartsTooltip />
                 <Bar dataKey="count" fill="#82ca9d" name="Раз" />
               </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      
      <div className="analytics-insights">
        <h4>Лидеры активности</h4>
        <ul>
          {talk_time_leaderboard.slice(0, 3).map((s, i) => (
            <li key={i}>{i+1}. {s.name} ({formatTime(s.seconds)})</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default GroupAnalyticsSummaryTab;
