import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { ChevronRight, BookOpen, Target, TrendingUp, AlertTriangle, Minus, Map } from 'lucide-react';
import { useAuth } from '../auth';
import {
  getExamTypes,
  getSubjects,
  getStudentProgress,
  getGroupProgress,
} from '../knowledgeMapService';
import { apiClient } from '../apiService';
import './KnowledgeMapPage.css';

// ========== Вспомогательные функции ==========

const getMasteryColor = (level) => {
  if (level >= 80) return '#10b981';
  if (level >= 50) return '#6366f1';
  if (level >= 25) return '#f59e0b';
  if (level > 0) return '#ef4444';
  return '#d1d5db';
};

const trendIcon = (trend) => {
  switch (trend) {
    case 'rising': return <TrendingUp size={12} />;
    case 'falling': return <AlertTriangle size={12} />;
    case 'stable': return <Minus size={12} />;
    default: return null;
  }
};

const trendLabel = (trend) => {
  switch (trend) {
    case 'rising': return 'Рост';
    case 'falling': return 'Спад';
    case 'stable': return 'Стабильно';
    case 'new': return 'Мало данных';
    default: return '';
  }
};

// ========== Skeleton ==========

const SectionSkeleton = () => (
  <div className="km-section">
    <div className="km-section-header" style={{ pointerEvents: 'none' }}>
      <div className="km-section-left">
        <div className="km-skeleton-bar" style={{ width: 200 }} />
      </div>
      <div className="km-skeleton-bar" style={{ width: 60 }} />
    </div>
  </div>
);

// ========== Topic Row ==========

const TopicRow = ({ topic }) => {
  const mastery = topic.mastery;
  const level = mastery ? mastery.mastery_level : 0;
  const status = mastery ? mastery.status : 'not_started';
  const trend = mastery ? mastery.trend : null;

  return (
    <div className="km-topic">
      {topic.task_number && (
        <span className={`km-task-num ${topic.difficulty}`}>
          {topic.task_number}
        </span>
      )}
      <span className={`km-status-dot ${status}`} />
      <div className="km-topic-info">
        <div className="km-topic-name">{topic.name}</div>
        <div className="km-topic-meta">
          <span className={`km-difficulty ${topic.difficulty}`}>
            {topic.difficulty === 'base' ? 'Базовый' : topic.difficulty === 'medium' ? 'Повышенный' : 'Высокий'}
          </span>
          {mastery && mastery.attempted_count > 0 && (
            <span>
              {mastery.attempted_count} попыт. / {mastery.success_count} усп.
            </span>
          )}
        </div>
      </div>
      <div className="km-topic-stats">
        <div className="km-topic-bar">
          <div
            className="km-topic-bar-fill"
            style={{ width: `${level}%`, background: getMasteryColor(level) }}
          />
        </div>
        <span className="km-topic-percent" style={{ color: getMasteryColor(level) }}>
          {Math.round(level)}%
        </span>
        {trend && trend !== 'new' && (
          <span className={`km-topic-trend ${trend}`}>
            {trendIcon(trend)} {trendLabel(trend)}
          </span>
        )}
      </div>
    </div>
  );
};

// ========== Section ==========

const SectionBlock = ({ section }) => {
  const [expanded, setExpanded] = useState(true);
  const avgMastery = section.avg_mastery || 0;

  return (
    <div className="km-section">
      <div className="km-section-header" onClick={() => setExpanded(!expanded)}>
        <div className="km-section-left">
          <ChevronRight
            className={`km-section-chevron ${expanded ? 'expanded' : ''}`}
            size={18}
          />
          <span className="km-section-name">{section.name}</span>
          <span className="km-section-badge" style={{ background: '#f1f5f9', color: '#64748b' }}>
            {section.topics_count || section.topics?.length || 0} тем
          </span>
        </div>
        <div className="km-section-right">
          <div className="km-section-progress-bar">
            <div
              className="km-section-progress-fill"
              style={{
                width: `${avgMastery}%`,
                background: getMasteryColor(avgMastery),
              }}
            />
          </div>
          <span className="km-section-percent" style={{ color: getMasteryColor(avgMastery) }}>
            {Math.round(avgMastery)}%
          </span>
        </div>
      </div>
      {expanded && section.topics && (
        <div className="km-topics">
          {section.topics.map((topic) => (
            <TopicRow key={topic.id} topic={topic} />
          ))}
        </div>
      )}
    </div>
  );
};

// ========== Group Topic Row (avg mastery across students) ==========

const GroupTopicRow = ({ topic }) => {
  const level = topic.avg_mastery || 0;
  const ratio = `${topic.students_attempted || 0}/${topic.total_students || 0}`;

  return (
    <div className="km-topic">
      {topic.task_number && (
        <span className={`km-task-num base`}>
          {topic.task_number}
        </span>
      )}
      <div className="km-topic-info">
        <div className="km-topic-name">{topic.name}</div>
        <div className="km-topic-meta">
          <span>Пытались: {ratio}</span>
        </div>
      </div>
      <div className="km-topic-stats">
        <div className="km-topic-bar">
          <div
            className="km-topic-bar-fill"
            style={{ width: `${level}%`, background: getMasteryColor(level) }}
          />
        </div>
        <span className="km-topic-percent" style={{ color: getMasteryColor(level) }}>
          {Math.round(level)}%
        </span>
      </div>
    </div>
  );
};

const GroupSectionBlock = ({ section }) => {
  const [expanded, setExpanded] = useState(true);
  const topics = section.topics || [];
  const vals = topics.filter(t => t.avg_mastery > 0).map(t => t.avg_mastery);
  const avg = vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : 0;

  return (
    <div className="km-section">
      <div className="km-section-header" onClick={() => setExpanded(!expanded)}>
        <div className="km-section-left">
          <ChevronRight
            className={`km-section-chevron ${expanded ? 'expanded' : ''}`}
            size={18}
          />
          <span className="km-section-name">{section.name}</span>
          <span className="km-section-badge" style={{ background: '#f1f5f9', color: '#64748b' }}>
            {topics.length} тем
          </span>
        </div>
        <div className="km-section-right">
          <div className="km-section-progress-bar">
            <div className="km-section-progress-fill" style={{ width: `${avg}%`, background: getMasteryColor(avg) }} />
          </div>
          <span className="km-section-percent" style={{ color: getMasteryColor(avg) }}>
            {avg}%
          </span>
        </div>
      </div>
      {expanded && (
        <div className="km-topics">
          {topics.map((t) => <GroupTopicRow key={t.id} topic={t} />)}
        </div>
      )}
    </div>
  );
};

// ========== Main Page ==========

const KnowledgeMapPage = () => {
  const { role } = useAuth();
  const isTeacher = role === 'teacher' || role === 'admin';

  // Filters
  const [examTypes, setExamTypes] = useState([]);
  const [selectedExamType, setSelectedExamType] = useState('');
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [groups, setGroups] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const [students, setStudents] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState('');
  const [viewMode, setViewMode] = useState('student'); // 'student' | 'group'

  // Data
  const [progressData, setProgressData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  // Load exam types
  useEffect(() => {
    const load = async () => {
      try {
        const res = await getExamTypes();
        const types = res.data.results || res.data || [];
        setExamTypes(types);
        if (types.length > 0) setSelectedExamType(types[0].code);
      } catch (e) {
        console.error('Failed to load exam types', e);
      }
    };
    load();
  }, []);

  // Load groups for teacher
  useEffect(() => {
    if (!isTeacher) return;
    const loadGroups = async () => {
      try {
        const res = await apiClient.get('/groups/');
        const data = res.data.results || res.data || [];
        setGroups(data);
      } catch (e) {
        console.error('Failed to load groups', e);
      }
    };
    loadGroups();
  }, [isTeacher]);

  // Load subjects when exam type changes
  useEffect(() => {
    if (!selectedExamType) return;
    const load = async () => {
      try {
        const res = await getSubjects(selectedExamType);
        const data = res.data.results || res.data || [];
        setSubjects(data);
        setSelectedSubjectId(data.length > 0 ? String(data[0].id) : '');
        setInitialLoading(false);
      } catch (e) {
        console.error('Failed to load subjects', e);
        setInitialLoading(false);
      }
    };
    load();
  }, [selectedExamType]);

  // Load students when group changes
  useEffect(() => {
    if (!selectedGroupId) { setStudents([]); return; }
    const group = groups.find(g => String(g.id) === selectedGroupId);
    if (group && group.students) {
      setStudents(group.students);
      if (group.students.length > 0 && viewMode === 'student') {
        setSelectedStudentId(String(group.students[0].id));
      }
    } else {
      // fetch group students
      apiClient.get(`/groups/${selectedGroupId}/`).then(res => {
        const s = res.data.students || [];
        setStudents(s);
        if (s.length > 0 && viewMode === 'student') {
          setSelectedStudentId(String(s[0].id));
        }
      }).catch(() => setStudents([]));
    }
  }, [selectedGroupId, groups, viewMode]);

  // Fetch progress data
  const fetchProgress = useCallback(async () => {
    if (!selectedSubjectId) return;
    setLoading(true);
    try {
      if (viewMode === 'group' && selectedGroupId) {
        const res = await getGroupProgress(selectedGroupId, selectedSubjectId);
        setProgressData({ ...res.data, mode: 'group' });
      } else if (selectedStudentId) {
        const res = await getStudentProgress(selectedStudentId, selectedSubjectId);
        setProgressData({ ...res.data, mode: 'student' });
      } else {
        setProgressData(null);
      }
    } catch (e) {
      console.error('Failed to load progress', e);
      setProgressData(null);
    } finally {
      setLoading(false);
    }
  }, [selectedSubjectId, selectedGroupId, selectedStudentId, viewMode]);

  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);

  // Summary stats
  const summary = useMemo(() => {
    if (!progressData) return null;
    if (progressData.mode === 'group') {
      return {
        mastery: progressData.overall_mastery || 0,
        totalStudents: progressData.total_students || 0,
      };
    }
    return {
      mastery: progressData.overall_mastery || 0,
      stability: progressData.overall_stability || 0,
      mastered: progressData.topics_mastered || 0,
      inProgress: progressData.topics_in_progress || 0,
      needsReview: progressData.topics_needs_review || 0,
      notStarted: progressData.topics_not_started || 0,
      total: progressData.topics_total || 0,
    };
  }, [progressData]);

  // ========== Render ==========

  return (
    <div className="knowledge-map-page">
      <div className="km-header">
        <h1>Карта знаний</h1>
        <p>Прогресс по темам экзамена</p>
      </div>

      {/* Filters */}
      <div className="km-filters">
        <select
          className="km-filter-select"
          value={selectedExamType}
          onChange={(e) => setSelectedExamType(e.target.value)}
        >
          {examTypes.map((et) => (
            <option key={et.code} value={et.code}>{et.name}</option>
          ))}
        </select>

        <select
          className="km-filter-select"
          value={selectedSubjectId}
          onChange={(e) => setSelectedSubjectId(e.target.value)}
        >
          <option value="">Выберите предмет</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        {isTeacher && (
          <>
            <select
              className="km-filter-select"
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value)}
            >
              <option value="student">По ученику</option>
              <option value="group">По группе</option>
            </select>

            <select
              className="km-filter-select"
              value={selectedGroupId}
              onChange={(e) => setSelectedGroupId(e.target.value)}
            >
              <option value="">Выберите группу</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>

            {viewMode === 'student' && students.length > 0 && (
              <select
                className="km-filter-select"
                value={selectedStudentId}
                onChange={(e) => setSelectedStudentId(e.target.value)}
              >
                <option value="">Выберите ученика</option>
                {students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.last_name} {s.first_name || s.email}
                  </option>
                ))}
              </select>
            )}
          </>
        )}
      </div>

      {/* Loading */}
      {(loading || initialLoading) && (
        <div className="km-sections">
          {[1, 2, 3].map((i) => <SectionSkeleton key={i} />)}
        </div>
      )}

      {/* No data yet */}
      {!loading && !initialLoading && !progressData && (
        <div className="km-empty">
          <Map className="km-empty-icon" size={48} />
          <h3>Выберите предмет и ученика</h3>
          <p>Карта знаний покажет прогресс по каждой теме экзамена</p>
        </div>
      )}

      {/* Student mode */}
      {!loading && progressData && progressData.mode === 'student' && summary && (
        <>
          <div className="km-summary">
            <div className="km-summary-card mastery">
              <div className="km-summary-value">{Math.round(summary.mastery)}%</div>
              <div className="km-summary-label">Общий уровень</div>
            </div>
            <div className="km-summary-card mastered">
              <div className="km-summary-value">{summary.mastered}</div>
              <div className="km-summary-label">Освоено</div>
            </div>
            <div className="km-summary-card in-progress">
              <div className="km-summary-value">{summary.inProgress}</div>
              <div className="km-summary-label">В процессе</div>
            </div>
            <div className="km-summary-card needs-review">
              <div className="km-summary-value">{summary.needsReview}</div>
              <div className="km-summary-label">Повторить</div>
            </div>
            <div className="km-summary-card not-started">
              <div className="km-summary-value">{summary.notStarted}</div>
              <div className="km-summary-label">Не начато</div>
            </div>
          </div>

          <div className="km-sections">
            {(progressData.sections || []).map((section) => (
              <SectionBlock key={section.id} section={section} />
            ))}
          </div>
        </>
      )}

      {/* Group mode */}
      {!loading && progressData && progressData.mode === 'group' && (
        <>
          <div className="km-summary">
            <div className="km-summary-card mastery">
              <div className="km-summary-value">{Math.round(summary.mastery)}%</div>
              <div className="km-summary-label">Средний уровень</div>
            </div>
            <div className="km-summary-card not-started">
              <div className="km-summary-value">{summary.totalStudents}</div>
              <div className="km-summary-label">Учеников</div>
            </div>
          </div>

          {/* Student chips */}
          {progressData.students && progressData.students.length > 0 && (
            <div className="km-group-students">
              <h3>Ученики (по уровню освоения)</h3>
              <div className="km-student-list">
                {progressData.students.map((s) => (
                  <button
                    key={s.id}
                    className={`km-student-chip ${String(s.id) === selectedStudentId ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedStudentId(String(s.id));
                      setViewMode('student');
                    }}
                  >
                    <span>{s.name}</span>
                    <span className="km-student-mastery">{Math.round(s.avg_mastery)}%</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="km-sections">
            {(progressData.sections || []).map((section) => (
              <GroupSectionBlock key={section.id} section={section} />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default KnowledgeMapPage;
