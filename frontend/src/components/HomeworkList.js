import React, { useEffect, useState, useMemo } from 'react';
import { getHomeworkList, getSubmissions, getGroups } from '../apiService';
import { Link, useNavigate } from 'react-router-dom';
import './HomeworkList.css';

// SVG Icons
const IconBook = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>
  </svg>
);

const IconClock = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12,6 12,12 16,14"/>
  </svg>
);

const IconCheck = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20,6 9,17 4,12"/>
  </svg>
);

const IconStar = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
  </svg>
);

const IconFilter = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46"/>
  </svg>
);

const HomeworkList = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Фильтры
  const [activeTab, setActiveTab] = useState('active'); // 'active' | 'completed'
  const [sourceFilter, setSourceFilter] = useState('all'); // 'all' | 'individual' | 'group_{id}'
  const [filterOpen, setFilterOpen] = useState(false);
  const filterRef = React.useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (filterRef.current && !filterRef.current.contains(e.target)) {
        setFilterOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [hwRes, subRes, groupsRes] = await Promise.all([
        getHomeworkList({}),
        getSubmissions({}),
        getGroups()
      ]);
      
      const hwList = Array.isArray(hwRes.data) ? hwRes.data : hwRes.data.results || [];
      const subList = Array.isArray(subRes.data) ? subRes.data : subRes.data.results || [];
      const groupsList = Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || [];
      
      setItems(hwList);
      setSubmissions(subList);
      setGroups(groupsList);
    } catch (e) {
      console.error('Error loading homework:', e);
      setError('Ошибка загрузки домашних заданий');
    } finally {
      setLoading(false);
    }
  };

  // Создаем индекс сабмишенов по homework_id
  const submissionIndex = useMemo(() => {
    const index = {};
    submissions.forEach(sub => {
      index[sub.homework] = sub;
    });
    return index;
  }, [submissions]);

  // Обогащаем задания статусами
  const decoratedItems = useMemo(() => {
    return items.map(hw => {
      const sub = submissionIndex[hw.id];
      return {
        ...hw,
        submission: sub,
        status: sub ? sub.status : 'not_started',
        score: sub?.total_score,
        maxScore: hw.max_score
      };
    });
  }, [items, submissionIndex]);

  // Фильтрация по источнику
  const filteredBySource = useMemo(() => {
    if (sourceFilter === 'all') return decoratedItems;
    if (sourceFilter === 'individual') {
      return decoratedItems.filter(hw => !hw.lesson?.group);
    }
    // group_{id}
    const groupId = parseInt(sourceFilter.replace('group_', ''), 10);
    return decoratedItems.filter(hw => hw.lesson?.group?.id === groupId || hw.group_id === groupId);
  }, [decoratedItems, sourceFilter]);

  const sourceFilterLabel = (value, groupList) => {
    if (value === 'all') return 'Все источники';
    if (value === 'individual') return 'Индивидуальные';
    const groupId = parseInt(value.replace('group_', ''), 10);
    const group = groupList.find((g) => g.id === groupId);
    return group ? `Материалы • ${group.name}` : 'Материалы группы';
  };

  // Разделение по табам
  const activeHomework = useMemo(() => {
    return filteredBySource.filter(hw => 
      hw.status === 'not_started' || hw.status === 'in_progress'
    );
  }, [filteredBySource]);

  const completedHomework = useMemo(() => {
    return filteredBySource.filter(hw => 
      hw.status === 'submitted' || hw.status === 'graded'
    );
  }, [filteredBySource]);

  const currentList = activeTab === 'active' ? activeHomework : completedHomework;

  // Статусы для отображения
  const getStatusConfig = (status) => {
    switch (status) {
      case 'not_started':
        return { label: 'Новое', className: 'status-new', icon: null };
      case 'in_progress':
        return { label: 'В процессе', className: 'status-progress', icon: <IconClock size={14} /> };
      case 'submitted':
        return { label: 'На проверке', className: 'status-submitted', icon: <IconClock size={14} /> };
      case 'graded':
        return { label: 'Проверено', className: 'status-graded', icon: <IconCheck size={14} /> };
      default:
        return { label: 'Новое', className: 'status-new', icon: null };
    }
  };

  const getActionButton = (hw) => {
    switch (hw.status) {
      case 'not_started':
        return { label: 'Начать', variant: 'primary' };
      case 'in_progress':
        return { label: 'Продолжить', variant: 'primary' };
      case 'submitted':
      case 'graded':
        return { label: 'Смотреть', variant: 'secondary' };
      default:
        return { label: 'Открыть', variant: 'primary' };
    }
  };

  const formatDeadline = (deadline) => {
    if (!deadline) return null;
    const date = new Date(deadline);
    const now = new Date();
    const diffMs = date - now;
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
      return { text: 'Просрочено', isOverdue: true };
    } else if (diffDays === 0) {
      return { text: 'Сегодня', isUrgent: true };
    } else if (diffDays === 1) {
      return { text: 'Завтра', isUrgent: true };
    } else if (diffDays <= 3) {
      return { text: `${diffDays} дн.`, isUrgent: true };
    } else {
      return { text: date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }), isNormal: true };
    }
  };

  if (loading) {
    return (
      <div className="hw-page">
        <div className="hw-container">
          <div className="hw-loading">
            <div className="hw-loading-spinner"></div>
            <span>Загрузка заданий...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="hw-page">
        <div className="hw-container">
          <div className="hw-error">
            <span className="hw-error-icon">⚠️</span>
            <p>{error}</p>
            <button className="hw-btn hw-btn-primary" onClick={loadData}>Повторить</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="hw-page">
      <div className="hw-container">
        {/* Header */}
        <header className="hw-header">
          <div className="hw-header-content">
            <div className="hw-header-icon">
              <IconBook size={28} />
            </div>
            <div className="hw-header-text">
              <h1 className="hw-title">Домашние задания</h1>
              <p className="hw-subtitle">
                {items.length === 0 
                  ? 'Пока нет заданий' 
                  : `${activeHomework.length} активных, ${completedHomework.length} завершённых`
                }
              </p>
            </div>
          </div>
        </header>

        {/* Filters */}
        {groups.length > 0 && (
          <div className="hw-filters" ref={filterRef}>
            <div className="hw-filter-group">
              <IconFilter size={18} />
              <button
                className="hw-filter-select"
                type="button"
                aria-haspopup="listbox"
                aria-expanded={filterOpen}
                onClick={() => setFilterOpen((v) => !v)}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') setFilterOpen(false);
                }}
              >
                <span>{sourceFilterLabel(sourceFilter, groups)}</span>
                <span className="hw-filter-caret" aria-hidden>{filterOpen ? '▴' : '▾'}</span>
              </button>
              {filterOpen && (
                <div className="hw-filter-menu" role="listbox" aria-label="Источник задания">
                  <button
                    className={`hw-filter-option ${sourceFilter === 'all' ? 'selected' : ''}`}
                    onClick={() => {
                      setSourceFilter('all');
                      setFilterOpen(false);
                    }}
                    role="option"
                    aria-selected={sourceFilter === 'all'}
                    type="button"
                  >
                    Все источники
                  </button>
                  <button
                    className={`hw-filter-option ${sourceFilter === 'individual' ? 'selected' : ''}`}
                    onClick={() => {
                      setSourceFilter('individual');
                      setFilterOpen(false);
                    }}
                    role="option"
                    aria-selected={sourceFilter === 'individual'}
                    type="button"
                  >
                    Индивидуальные
                  </button>
                  {groups.map((g) => {
                    const value = `group_${g.id}`;
                    return (
                      <button
                        key={g.id}
                        className={`hw-filter-option ${sourceFilter === value ? 'selected' : ''}`}
                        onClick={() => {
                          setSourceFilter(value);
                          setFilterOpen(false);
                        }}
                        role="option"
                        aria-selected={sourceFilter === value}
                        type="button"
                      >
                        Материалы • {g.name}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="hw-tabs">
          <button
            className={`hw-tab ${activeTab === 'active' ? 'active' : ''}`}
            onClick={() => setActiveTab('active')}
          >
            <span className="hw-tab-label">Активные</span>
            <span className="hw-tab-count">{activeHomework.length}</span>
          </button>
          <button
            className={`hw-tab ${activeTab === 'completed' ? 'active' : ''}`}
            onClick={() => setActiveTab('completed')}
          >
            <span className="hw-tab-label">Завершённые</span>
            <span className="hw-tab-count">{completedHomework.length}</span>
          </button>
        </div>

        {/* Content */}
        <div className="hw-content">
          {currentList.length === 0 ? (
            <div className="hw-empty">
              <div className="hw-empty-icon">
                {activeTab === 'active' ? '📝' : '✅'}
              </div>
              <h3 className="hw-empty-title">
                {activeTab === 'active' 
                  ? 'Нет активных заданий' 
                  : 'Нет завершённых заданий'
                }
              </h3>
              <p className="hw-empty-text">
                {activeTab === 'active'
                  ? 'Ваш преподаватель скоро добавит новые задания'
                  : 'Здесь будут отображаться выполненные работы'
                }
              </p>
            </div>
          ) : (
            <div className="hw-list">
              {currentList.map(hw => {
                const statusConfig = getStatusConfig(hw.status);
                const actionBtn = getActionButton(hw);
                const deadline = formatDeadline(hw.deadline);
                const groupName = hw.lesson?.group?.name || hw.group_name;

                return (
                  <div key={hw.id} className="hw-card">
                    <div className="hw-card-main">
                      <div className="hw-card-header">
                        <h3 className="hw-card-title">{hw.title}</h3>
                        <span className={`hw-status ${statusConfig.className}`}>
                          {statusConfig.icon}
                          {statusConfig.label}
                        </span>
                      </div>
                      
                      <div className="hw-card-meta">
                        {groupName && (
                          <span className="hw-meta-item hw-meta-group">
                            {groupName}
                          </span>
                        )}
                        {!groupName && (
                          <span className="hw-meta-item hw-meta-individual">
                            Индивидуальное
                          </span>
                        )}
                        {deadline && (
                          <span className={`hw-meta-item hw-meta-deadline ${deadline.isOverdue ? 'overdue' : ''} ${deadline.isUrgent ? 'urgent' : ''}`}>
                            <IconClock size={14} />
                            {deadline.text}
                          </span>
                        )}
                        {hw.maxScore && (
                          <span className="hw-meta-item hw-meta-score">
                            <IconStar size={14} />
                            {hw.score !== undefined ? `${hw.score}/${hw.maxScore}` : `Макс: ${hw.maxScore}`}
                          </span>
                        )}
                      </div>

                      {hw.description && (
                        <p className="hw-card-desc">{hw.description.slice(0, 100)}{hw.description.length > 100 ? '...' : ''}</p>
                      )}
                    </div>

                    <div className="hw-card-actions">
                      <Link 
                        to={`/student/homework/${hw.id}`} 
                        className={`hw-btn ${actionBtn.variant === 'primary' ? 'hw-btn-primary' : 'hw-btn-secondary'}`}
                      >
                        {actionBtn.label}
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HomeworkList;
