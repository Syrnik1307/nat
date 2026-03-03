import React from 'react';
import {
    RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
    Radar, ResponsiveContainer, Tooltip
} from 'recharts';

/**
 * Radar chart for visualizing student knowledge across exam topics.
 * 
 * @param {Array} topics - [{ topic_title, topic_number, score_percent, attempts_count, topic_max_points }]
 * @param {number} size - chart height (default 400)
 */
const KnowledgeRadarChart = ({ topics = [], size = 400 }) => {
    if (!topics.length) {
        return (
            <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                minHeight: 200, color: '#94a3b8', fontSize: 14,
            }}>
                Нет данных для отображения
            </div>
        );
    }

    const data = topics.map(t => ({
        name: `#${t.topic_number}`,
        fullName: t.topic_title,
        value: Math.round(t.score_percent),
        attempts: t.attempts_count,
        maxPoints: t.topic_max_points,
    }));

    const CustomTooltip = ({ active, payload }) => {
        if (!active || !payload?.length) return null;
        const d = payload[0].payload;
        return (
            <div style={{
                background: '#fff', border: '1px solid #e2e8f0',
                borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                fontSize: 13,
            }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                    Задание {d.name}: {d.fullName}
                </div>
                <div style={{ color: getColor(d.value) }}>
                    {d.value}% освоения
                </div>
                <div style={{ color: '#64748b', fontSize: 12 }}>
                    {d.attempts} {pluralize(d.attempts, 'попытка', 'попытки', 'попыток')}
                    {' \u00B7 '}макс. {d.maxPoints}б
                </div>
            </div>
        );
    };

    return (
        <ResponsiveContainer width="100%" height={size}>
            <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                />
                <PolarRadiusAxis
                    angle={90}
                    domain={[0, 100]}
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                    tickCount={5}
                />
                <Radar
                    name="Освоение"
                    dataKey="value"
                    stroke="#4F46E5"
                    fill="#4F46E5"
                    fillOpacity={0.15}
                    strokeWidth={2}
                    dot={{ r: 4, fill: '#4F46E5' }}
                    activeDot={{ r: 6, fill: '#4F46E5', stroke: '#fff', strokeWidth: 2 }}
                />
                <Tooltip content={<CustomTooltip />} />
            </RadarChart>
        </ResponsiveContainer>
    );
};

function getColor(percent) {
    if (percent >= 70) return '#16a34a';
    if (percent >= 40) return '#d97706';
    return '#dc2626';
}

function pluralize(n, one, few, many) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod100 >= 11 && mod100 <= 19) return many;
    if (mod10 === 1) return one;
    if (mod10 >= 2 && mod10 <= 4) return few;
    return many;
}

export default KnowledgeRadarChart;
