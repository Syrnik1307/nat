import React from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

const LessonAnalytics = ({ analytics }) => {
  if (!analytics || !analytics.stats) {
    return <div className="p-4 text-center text-gray-500">Нет данных для анализа</div>;
  }

  const { stats, summary } = analytics;
  const { speakers = [], mentions = [], total_duration = 0 } = stats;

  // Данные для круговой диаграммы (Время речи)
  const participationData = [
    { name: 'Учитель', value: summary.teacher_percent },
    { name: 'Ученики', value: summary.student_talk_time_percent }
  ].filter(d => d.value > 0);

  // Данные для диаграммы спикеров (Детально)
  const speakersData = speakers
    .map(s => ({ 
      name: s.name === 'Unknown' ? 'Неизвестный' : s.name, 
      value: parseFloat((s.duration / 60).toFixed(2)), // в минутах
      full: s
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10); // Топ 10 спикеров

  // Данные для упоминаний
  const mentionsData = mentions
    .map(m => ({
      name: m.student_name,
      count: m.count
    }))
    .sort((a, b) => b.count - a.count);

  return (
    <div className="analytics-container p-4">
        <h3 className="text-xl font-bold mb-4">Анализ участия (AI Transcript)</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Круговая диаграмма: Учитель vs Ученики */}
            <div className="card shadow p-4 rounded bg-white">
                <h4 className="text-lg font-semibold mb-2 text-center">Баланс речи</h4>
                <div style={{ width: '100%', height: 300 }}>
                    <ResponsiveContainer>
                        <PieChart>
                            <Pie
                                data={participationData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                fill="#8884d8"
                                paddingAngle={5}
                                dataKey="value"
                                label={({name, value}) => `${name}: ${value.toFixed(0)}%`}
                            >
                                {participationData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={index === 0 ? '#FF8042' : '#00C49F'} />
                                ))}
                            </Pie>
                            <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
                <div className="text-center mt-2 text-sm text-gray-600">
                    Всего разговоров: {(total_duration / 60).toFixed(1)} мин.
                </div>
            </div>

            {/* Столбцы: Упоминания имен */}
            <div className="card shadow p-4 rounded bg-white">
                <h4 className="text-lg font-semibold mb-2 text-center">Внимательность учителя (упоминания имен)</h4>
                {mentionsData.length > 0 ? (
                    <div style={{ width: '100%', height: 300 }}>
                        <ResponsiveContainer>
                            <BarChart data={mentionsData} layout="vertical" margin={{ left: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis type="number" />
                                <YAxis dataKey="name" type="category" width={100} />
                                <Tooltip />
                                <Bar dataKey="count" fill="#8884d8" name="Раз упомянут" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                ) : (
                    <div className="h-64 flex items-center justify-center text-gray-400">
                        Нет упоминаний имен в транскрипте
                    </div>
                )}
            </div>
        </div>

        {/* Детальная таблица спикеров */}
        <div className="mt-8">
            <h4 className="text-lg font-semibold mb-2">Активность участников</h4>
            <div className="overflow-x-auto">
                <table className="min-w-full bg-white border border-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="py-2 px-4 border-b text-left">Участник</th>
                            <th className="py-2 px-4 border-b text-left">Роль</th>
                            <th className="py-2 px-4 border-b text-right">Время (мин)</th>
                            <th className="py-2 px-4 border-b text-right">% Эфира</th>
                            <th className="py-2 px-4 border-b">
                                <span className="sr-only">Bar</span>
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {speakersData.map((s, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                                <td className="py-2 px-4 border-b font-medium">{s.name}</td>
                                <td className="py-2 px-4 border-b text-sm text-gray-500">
                                    {s.full.type === 'teacher' ? 'Преподаватель' : 
                                     s.full.type === 'student' ? 'Ученик' : 'Гость'}
                                </td>
                                <td className="py-2 px-4 border-b text-right">{s.value.toFixed(2)}</td>
                                <td className="py-2 px-4 border-b text-right">{s.full.percent.toFixed(1)}%</td>
                                <td className="py-2 px-4 border-b w-1/3">
                                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                                        <div 
                                            className="bg-blue-600 h-2.5 rounded-full" 
                                            style={{ width: `${s.full.percent}%` }}
                                        ></div>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
  );
};

export default LessonAnalytics;
