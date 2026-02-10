import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  GraduationCap,
  Target,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Clock,
  Sigma,
  Triangle,
  TrendingUp,
  FileText,
  ChevronDown,
  ChevronRight,
  BookOpen,
  RotateCcw,
  Calendar,
  X,
} from 'lucide-react';
import './StudentKnowledgeTree.css';

/* ─── Mock Data (будет заменено на API) ─────────────────── */

const examData = {
  examName: 'ЕГЭ: Математика (профиль)',
  predictedScore: 72,
  maxScore: 100,
  completionPercent: 68,
  totalTopics: 12,
  masteredTopics: 5,
  criticalTopics: 3,
  sections: [
    {
      id: 'algebra',
      name: 'Алгебра',
      icon: 'sigma',
      status: 'progress',
      topics: [
        {
          id: 'equations',
          name: 'Уравнения и неравенства',
          status: 'mastered',
          tasks: [
            { id: 'task-1', name: 'Задание #1', status: 'mastered', successRate: 94, totalAttempts: 32, lastPracticed: '2 дня назад', sparklineData: [60, 65, 72, 80, 85, 90, 94], description: 'Линейные уравнения и простые выражения' },
            { id: 'task-5', name: 'Задание #5', status: 'mastered', successRate: 88, totalAttempts: 25, lastPracticed: '1 день назад', sparklineData: [50, 55, 68, 75, 82, 85, 88], description: 'Квадратные уравнения и системы' },
          ],
        },
        {
          id: 'logarithms',
          name: 'Логарифмы',
          status: 'progress',
          tasks: [
            { id: 'task-7', name: 'Задание #7', status: 'progress', successRate: 65, totalAttempts: 18, lastPracticed: '3 дня назад', sparklineData: [30, 35, 45, 50, 55, 60, 65], description: 'Логарифмические уравнения и свойства' },
            { id: 'task-9', name: 'Задание #9', status: 'progress', successRate: 58, totalAttempts: 14, lastPracticed: '5 дней назад', sparklineData: [20, 28, 35, 42, 48, 52, 58], description: 'Логарифмические неравенства' },
          ],
        },
        {
          id: 'functions',
          name: 'Функции и графики',
          status: 'mastered',
          tasks: [
            { id: 'task-10', name: 'Задание #10', status: 'mastered', successRate: 91, totalAttempts: 28, lastPracticed: '1 день назад', sparklineData: [70, 75, 80, 85, 88, 90, 91], description: 'Чтение графиков и свойства функций' },
          ],
        },
      ],
    },
    {
      id: 'geometry',
      name: 'Геометрия',
      icon: 'triangle',
      status: 'critical',
      topics: [
        {
          id: 'planimetry',
          name: 'Планиметрия',
          status: 'critical',
          tasks: [
            { id: 'task-3', name: 'Задание #3', status: 'critical', successRate: 35, totalAttempts: 22, lastPracticed: '1 неделю назад', sparklineData: [15, 20, 25, 28, 30, 32, 35], description: 'Треугольники, окружности и площади' },
            { id: 'task-6', name: 'Задание #6', status: 'critical', successRate: 42, totalAttempts: 19, lastPracticed: '4 дня назад', sparklineData: [10, 18, 25, 30, 35, 38, 42], description: 'Углы, касательные, вписанные окружности' },
          ],
        },
        {
          id: 'stereometry',
          name: 'Стереометрия',
          status: 'critical',
          tasks: [
            { id: 'task-8', name: 'Задание #8', status: 'critical', successRate: 28, totalAttempts: 15, lastPracticed: '2 недели назад', sparklineData: [5, 10, 15, 18, 22, 25, 28], description: '3D-фигуры: объёмы, поверхности, сечения' },
          ],
        },
        {
          id: 'trigonometry',
          name: 'Тригонометрия',
          status: 'progress',
          tasks: [
            { id: 'task-13', name: 'Задание #13', status: 'progress', successRate: 55, totalAttempts: 20, lastPracticed: '3 дня назад', sparklineData: [20, 30, 35, 40, 45, 50, 55], description: 'Тригонометрические уравнения и тождества' },
          ],
        },
      ],
    },
    {
      id: 'calculus',
      name: 'Матанализ',
      icon: 'trending-up',
      status: 'mastered',
      topics: [
        {
          id: 'derivatives',
          name: 'Производные',
          status: 'mastered',
          tasks: [
            { id: 'task-12', name: 'Задание #12', status: 'mastered', successRate: 92, totalAttempts: 30, lastPracticed: '2 дня назад', sparklineData: [60, 68, 75, 82, 86, 90, 92], description: 'Вычисление производных и их применение' },
          ],
        },
        {
          id: 'integrals',
          name: 'Интегралы',
          status: 'progress',
          tasks: [
            { id: 'task-14', name: 'Задание #14', status: 'progress', successRate: 70, totalAttempts: 16, lastPracticed: '4 дня назад', sparklineData: [30, 40, 48, 55, 60, 65, 70], description: 'Определённые интегралы и площадь под кривой' },
          ],
        },
      ],
    },
    {
      id: 'word-problems',
      name: 'Текстовые задачи',
      icon: 'file-text',
      status: 'progress',
      topics: [
        {
          id: 'economics',
          name: 'Экономические задачи',
          status: 'mastered',
          tasks: [
            { id: 'task-17', name: 'Задание #17', status: 'mastered', successRate: 87, totalAttempts: 22, lastPracticed: '1 день назад', sparklineData: [55, 62, 70, 75, 80, 84, 87], description: 'Оптимизация и экономическое моделирование' },
          ],
        },
        {
          id: 'probability',
          name: 'Вероятность и статистика',
          status: 'progress',
          tasks: [
            { id: 'task-4', name: 'Задание #4', status: 'progress', successRate: 72, totalAttempts: 24, lastPracticed: '2 дня назад', sparklineData: [40, 48, 55, 60, 65, 68, 72], description: 'Классическая вероятность и комбинаторика' },
          ],
        },
        {
          id: 'number-theory',
          name: 'Теория чисел',
          status: 'locked',
          tasks: [
            { id: 'task-19', name: 'Задание #19', status: 'locked', successRate: 0, totalAttempts: 0, lastPracticed: null, sparklineData: [0, 0, 0, 0, 0, 0, 0], description: 'Делимость, остатки и задачи с цифрами' },
          ],
        },
      ],
    },
  ],
};

/* ─── Helpers ───────────────────────────────────────────── */

const sectionIcons = {
  sigma: <Sigma size={20} />,
  triangle: <Triangle size={20} />,
  'trending-up': <TrendingUp size={20} />,
  'file-text': <FileText size={20} />,
};

const statusLabels = {
  mastered: 'Освоено (>85%)',
  progress: 'В процессе (50-85%)',
  critical: 'Критично (<50%)',
  locked: 'Не начато',
};

const statusIcon = {
  mastered: <CheckCircle2 size={16} className="skt-icon-mastered" />,
  progress: <Clock size={16} className="skt-icon-progress" />,
  critical: <AlertTriangle size={16} className="skt-icon-critical" />,
  locked: <Lock size={16} className="skt-icon-locked" />,
};

const rateColor = (r) => (r > 85 ? 'skt-rate-mastered' : r >= 50 ? 'skt-rate-progress' : r > 0 ? 'skt-rate-critical' : 'skt-rate-locked');
const rateBgColor = (r) => (r > 85 ? 'skt-bar-mastered' : r >= 50 ? 'skt-bar-progress' : r > 0 ? 'skt-bar-critical' : 'skt-bar-locked');

function getTopicCompletion(t) {
  if (!t.tasks.length) return 0;
  return Math.round(t.tasks.reduce((a, b) => a + b.successRate, 0) / t.tasks.length);
}

function getSectionCompletion(s) {
  const all = s.topics.flatMap((t) => t.tasks);
  if (!all.length) return 0;
  return Math.round(all.reduce((a, b) => a + b.successRate, 0) / all.length);
}

const whyMatters = {
  'task-1': 'Задание #1 встречается в каждом варианте и дает лёгкие баллы. Освоив его, вы обретёте уверенность для сложных задач.',
  'task-3': 'Планиметрия стоит до 6 баллов на экзамене. Слабая геометрия влияет на задания #6 и #16.',
  'task-5': 'Квадратные уравнения — основа алгебры. Они встречаются в оптимизации и текстовых задачах.',
  'task-6': 'Задачи на углы и касательные требуют пространственного мышления, необходимого и для стереометрии.',
  'task-7': 'Логарифмы связывают алгебру с математическим анализом. Они открывают экспоненциальные задачи.',
  'task-8': '3D-геометрия — одна из самых сложных секций, но даёт много баллов. Начните с формул объёмов.',
  'task-9': 'Логарифмические неравенства сочетают две сложных темы. Освойте основы прежде, чем переходить дальше.',
  'task-10': 'Графики функций встречаются в нескольких заданиях. Навык чтения графиков упрощает сложные задачи.',
  'task-12': 'Производные — ворота в матанализ. Они появляются в оптимизации, касательных и вычислении площадей.',
  'task-13': 'Тригонометрические тождества используются во многих заданиях. Сильная тригонометрия упрощает геометрию.',
  'task-14': 'Интегралы завершают ваш инструментарий по матанализу. Редкие, но высокобалльные задания.',
  'task-17': 'Экономические задачи предсказуемы и шаблонны. Выучите паттерны для гарантированных баллов.',
  'task-4': 'Вероятность появляется каждый год. Одна из самых выгодных тем для подготовки.',
  'task-19': 'Задачи по теории чисел сложны, но дают много баллов. Требуют творческого подхода.',
};

/* ─── Score Header ──────────────────────────────────────── */

function ScoreHeader({ data }) {
  const scoreClass = data.predictedScore >= 80 ? 'skt-score-high' : data.predictedScore >= 60 ? 'skt-score-mid' : 'skt-score-low';
  const strokeColor = data.predictedScore >= 80 ? 'var(--color-success)' : data.predictedScore >= 60 ? 'var(--color-warning)' : 'var(--color-error)';
  const circum = 2 * Math.PI * 44;
  const offset = circum * (1 - data.predictedScore / data.maxScore);

  return (
    <header className="skt-header-card">
      <div className="skt-header-glow skt-header-glow-1" />
      <div className="skt-header-glow skt-header-glow-2" />

      <div className="skt-header-content">
        {/* Left */}
        <div className="skt-header-left">
          <div className="skt-header-title-row">
            <div className="skt-header-icon">
              <GraduationCap size={20} />
            </div>
            <div>
              <p className="skt-header-label">Подготовка к экзамену</p>
              <h1 className="skt-header-title">{data.examName}</h1>
            </div>
          </div>

          <div className="skt-header-progress">
            <div className="skt-header-progress-meta">
              <span className="skt-header-progress-label">Общий прогресс</span>
              <span className="skt-header-progress-value">{data.completionPercent}%</span>
            </div>
            <div className="skt-header-progress-bar">
              <div
                className="skt-header-progress-fill"
                style={{ width: `${data.completionPercent}%` }}
              />
            </div>
          </div>
        </div>

        {/* Right */}
        <div className="skt-header-right">
          {/* Score ring */}
          <div className="skt-score-ring-wrapper">
            <div className="skt-score-ring">
              <svg className="skt-score-ring-svg" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="44" fill="none" stroke="var(--border-light)" strokeWidth="4" />
                <circle
                  cx="50" cy="50" r="44" fill="none"
                  stroke={strokeColor}
                  strokeWidth="4" strokeLinecap="round"
                  strokeDasharray={circum}
                  strokeDashoffset={offset}
                  className="skt-score-ring-arc"
                />
              </svg>
              <div className="skt-score-ring-text">
                <span className={`skt-score-ring-number ${scoreClass}`}>{data.predictedScore}</span>
                <span className="skt-score-ring-max">/{data.maxScore}</span>
              </div>
            </div>
            <p className="skt-score-ring-label">Прогноз балла</p>
          </div>

          {/* Stats */}
          <div className="skt-header-stats">
            <div className="skt-header-stat">
              <Target size={16} className="skt-icon-primary" />
              <span className="skt-header-stat-label">Темы</span>
              <span className="skt-header-stat-value">{data.totalTopics}</span>
            </div>
            <div className="skt-header-stat">
              <CheckCircle2 size={16} className="skt-icon-mastered" />
              <span className="skt-header-stat-label">Освоено</span>
              <span className="skt-header-stat-value skt-rate-mastered">{data.masteredTopics}</span>
            </div>
            <div className="skt-header-stat">
              <AlertTriangle size={16} className="skt-icon-critical" />
              <span className="skt-header-stat-label">Критично</span>
              <span className="skt-header-stat-value skt-rate-critical">{data.criticalTopics}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

/* ─── Tree Node (task bubble) ───────────────────────────── */

function TreeNodeButton({ task, onClick }) {
  const clickable = task.status !== 'locked';

  return (
    <button
      onClick={() => clickable && onClick(task)}
      disabled={!clickable}
      className={`skt-task-node skt-task-${task.status} ${!clickable ? 'skt-task-disabled' : ''}`}
      aria-label={`${task.name}: ${task.description}. Статус: ${task.status}. Успешность: ${task.successRate}%`}
      title={`${task.description} | Попыток: ${task.totalAttempts}${task.lastPracticed ? ` | Последняя: ${task.lastPracticed}` : ''}`}
    >
      <div className="skt-task-node-top">
        {statusIcon[task.status]}
        <span className="skt-task-name">{task.name}</span>
      </div>
      <span className={`skt-task-rate ${rateColor(task.successRate)}`}>
        {task.status === 'locked' ? '---' : `${task.successRate}%`}
      </span>
      {task.status === 'critical' && (
        <span className="skt-task-pulse" />
      )}
    </button>
  );
}

/* ─── Detail Panel (slide-in drawer) ────────────────────── */

function DetailPanel({ task, open, onClose }) {
  const panelRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (open) document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  useEffect(() => {
    if (open) document.body.style.overflow = 'hidden';
    else document.body.style.overflow = '';
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  if (!task) return null;

  const stLabel = (r) =>
    r > 85 ? { text: 'Освоено', cls: 'mastered' }
    : r >= 50 ? { text: 'В процессе', cls: 'progress' }
    : r > 0 ? { text: 'Критический пробел', cls: 'critical' }
    : { text: 'Не начато', cls: 'locked' };

  const st = stLabel(task.successRate);
  const sparkMax = Math.max(...task.sparklineData, 1);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`skt-panel-backdrop ${open ? 'skt-panel-backdrop-visible' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={`${task.name} — детали`}
        className={`skt-panel ${open ? 'skt-panel-open' : ''}`}
      >
        {/* Header */}
        <div className="skt-panel-header">
          <div>
            <div className={`skt-panel-status-badge skt-badge-${st.cls}`}>
              {st.text}
            </div>
            <h2 className="skt-panel-title">{task.name}: {task.description}</h2>
            <p className="skt-panel-subtitle">Обзор результатов и рекомендации</p>
          </div>
          <button
            onClick={onClose}
            className="skt-panel-close"
            aria-label="Закрыть панель"
          >
            <X size={20} />
          </button>
        </div>

        <div className="skt-panel-body">
          {/* Stats grid */}
          <div className="skt-panel-stats-grid">
            <div className="skt-panel-stat-card">
              <Target size={16} className="skt-icon-primary" />
              <span className="skt-panel-stat-value">{task.successRate}%</span>
              <span className="skt-panel-stat-label">Успешность</span>
            </div>
            <div className="skt-panel-stat-card">
              <RotateCcw size={16} className="skt-icon-primary" />
              <span className="skt-panel-stat-value">{task.totalAttempts}</span>
              <span className="skt-panel-stat-label">Попыток</span>
            </div>
            <div className="skt-panel-stat-card">
              <Calendar size={16} className="skt-icon-primary" />
              <span className="skt-panel-stat-value">{task.lastPracticed ?? 'Никогда'}</span>
              <span className="skt-panel-stat-label">Последняя</span>
            </div>
          </div>

          {/* Why this matters */}
          <div className="skt-panel-insight">
            <h3 className="skt-panel-insight-title">
              <TrendingUp size={16} className="skt-icon-primary" />
              Почему это важно
            </h3>
            <p className="skt-panel-insight-text">
              {whyMatters[task.id] || 'Эта тема — ключевой строительный блок для успешной сдачи экзамена. Сосредоточьтесь на понимании базовых концепций.'}
            </p>
          </div>

          {/* Bar chart */}
          <div className="skt-panel-chart">
            <h3 className="skt-panel-chart-title">Прогресс по времени</h3>
            <div className="skt-panel-chart-bars">
              {task.sparklineData.map((val, i) => (
                <div key={i} className="skt-panel-chart-col">
                  <span className="skt-panel-chart-label">{val}%</span>
                  <div
                    className={`skt-panel-chart-bar ${rateBgColor(val)}`}
                    style={{ height: `${Math.max(4, (val / sparkMax) * 48)}px` }}
                  />
                </div>
              ))}
            </div>
            <div className="skt-panel-chart-legend">
              <span>Старые</span>
              <span>Новые</span>
            </div>
          </div>

          {/* Actions */}
          <div className="skt-panel-actions">
            <button className="skt-panel-btn skt-panel-btn-fix">
              <RotateCcw size={16} />
              Исправить ошибки
            </button>
            <button className="skt-panel-btn skt-panel-btn-theory">
              <BookOpen size={16} />
              Изучить теорию
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/* ─── Skill Tree ────────────────────────────────────────── */

function SkillTree({ sections, onTaskClick }) {
  const [expandedSections, setExpandedSections] = useState(new Set(sections.map((s) => s.id)));
  const [expandedTopics, setExpandedTopics] = useState(new Set(sections.flatMap((s) => s.topics.map((t) => t.id))));

  const toggleSection = (id) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleTopic = (id) => {
    setExpandedTopics((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  return (
    <div>
      {/* Legend */}
      <div className="skt-legend">
        <span className="skt-legend-label">Обозначения:</span>
        {['mastered', 'progress', 'critical', 'locked'].map((s) => (
          <div key={s} className="skt-legend-item">
            <div className={`skt-legend-dot skt-dot-${s}`} />
            <span className="skt-legend-text">{statusLabels[s]}</span>
          </div>
        ))}
      </div>

      {/* Sections */}
      <div className="skt-sections">
        {sections.map((section) => {
          const comp = getSectionCompletion(section);
          const expanded = expandedSections.has(section.id);

          return (
            <div key={section.id} className={`skt-section skt-section-${section.status}`}>
              {/* Section header */}
              <button
                onClick={() => toggleSection(section.id)}
                className="skt-section-header"
                aria-expanded={expanded}
              >
                <div className={`skt-section-icon skt-section-icon-${section.status}`}>
                  {sectionIcons[section.icon]}
                </div>
                <div className="skt-section-info">
                  <h2 className="skt-section-name">{section.name}</h2>
                  <p className="skt-section-meta">
                    {section.topics.length} тем &middot; {comp}% выполнено
                  </p>
                </div>
                <div className="skt-section-progressbar-wrap">
                  <div className="skt-section-progress-bar">
                    <div className={`skt-section-progress-fill skt-dot-${section.status}`} style={{ width: `${comp}%` }} />
                  </div>
                  <span className={`skt-section-progress-text skt-rate-${section.status}`}>{comp}%</span>
                </div>
                {expanded ? <ChevronDown size={20} className="skt-chevron" /> : <ChevronRight size={20} className="skt-chevron" />}
              </button>

              {/* Topics */}
              {expanded && (
                <div className="skt-topics-wrapper">
                  <div className="skt-topics-tree">
                    {section.topics.map((topic) => {
                      const tComp = getTopicCompletion(topic);
                      const tExp = expandedTopics.has(topic.id);

                      return (
                        <div key={topic.id}>
                          <button
                            onClick={() => toggleTopic(topic.id)}
                            className="skt-topic-header"
                            aria-expanded={tExp}
                          >
                            <div className={`skt-topic-dot skt-dot-${topic.status}`} />
                            <div className="skt-topic-info">
                              <h3 className="skt-topic-name">{topic.name}</h3>
                              <p className="skt-topic-meta">
                                {topic.tasks.length} {topic.tasks.length === 1 ? 'задание' : topic.tasks.length < 5 ? 'задания' : 'заданий'} &middot; {tComp}% среднее
                              </p>
                            </div>
                            <span className={`skt-topic-percent skt-rate-${topic.status}`}>{tComp}%</span>
                            {tExp ? <ChevronDown size={16} className="skt-chevron" /> : <ChevronRight size={16} className="skt-chevron" />}
                          </button>

                          {tExp && (
                            <div className="skt-tasks-list">
                              {topic.tasks.map((task) => (
                                <TreeNodeButton key={task.id} task={task} onClick={onTaskClick} />
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Main Page ─────────────────────────────────────────── */

const StudentKnowledgeTree = () => {
  const [selectedTask, setSelectedTask] = useState(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const handleTaskClick = useCallback((task) => {
    setSelectedTask(task);
    setPanelOpen(true);
  }, []);

  const handleClosePanel = useCallback(() => {
    setPanelOpen(false);
  }, []);

  return (
    <div className="skt-page">
      <div className="skt-container">
        <ScoreHeader data={examData} />
        <div className="skt-tree-section">
          <SkillTree sections={examData.sections} onTaskClick={handleTaskClick} />
        </div>
        <DetailPanel task={selectedTask} open={panelOpen} onClose={handleClosePanel} />
      </div>
    </div>
  );
};

export default StudentKnowledgeTree;
