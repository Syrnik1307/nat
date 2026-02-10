import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Search, ChevronDown, BookOpen, Check } from 'lucide-react';
import { getExamTypes, getSubjects, getTopics } from '../../../../knowledgeMapService';
import './ExamTopicSelector.css';

/**
 * ExamTopicSelector — выбор тем экзамена при создании ДЗ.
 * 
 * Props:
 *   value: number[] — массив выбранных topic IDs
 *   onChange: (ids: number[]) => void
 */
const ExamTopicSelector = ({ value = [], onChange }) => {
  const [examTypes, setExamTypes] = useState([]);
  const [selectedExamType, setSelectedExamType] = useState('');
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [topics, setTopics] = useState([]);
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedTopics, setSelectedTopics] = useState([]); // full topic objects for display
  const dropdownRef = useRef(null);

  // Load exam types on mount
  useEffect(() => {
    getExamTypes().then(res => {
      const types = res.data.results || res.data || [];
      setExamTypes(types);
      if (types.length > 0 && !selectedExamType) {
        setSelectedExamType(types[0].code);
      }
    }).catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Load subjects when exam type changes
  useEffect(() => {
    if (!selectedExamType) return;
    getSubjects(selectedExamType).then(res => {
      const data = res.data.results || res.data || [];
      setSubjects(data);
    }).catch(() => {});
  }, [selectedExamType]);

  // Load topics when subject changes or search
  useEffect(() => {
    if (!selectedSubjectId && !search) {
      setTopics([]);
      return;
    }
    setLoading(true);
    const params = {};
    if (selectedSubjectId) params.subject_id = selectedSubjectId;
    if (search) params.search = search;
    if (selectedExamType) params.exam_type = selectedExamType;

    getTopics(params).then(res => {
      const data = res.data.results || res.data || [];
      setTopics(data);
    }).catch(() => setTopics([]))
      .finally(() => setLoading(false));
  }, [selectedSubjectId, search, selectedExamType]);

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // When value changes from parent (edit mode), load topic details
  useEffect(() => {
    if (value.length > 0 && selectedTopics.length === 0) {
      // Fetch details for selected topic ids
      Promise.all(value.map(id =>
        getTopics({ subject_id: '', search: '' }).then(res => {
          const all = res.data.results || res.data || [];
          return all.find(t => t.id === id);
        }).catch(() => null)
      )).then(results => {
        setSelectedTopics(results.filter(Boolean));
      });
    }
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleTopic = useCallback((topic) => {
    const isSelected = value.includes(topic.id);
    let newIds;
    let newTopics;
    if (isSelected) {
      newIds = value.filter(id => id !== topic.id);
      newTopics = selectedTopics.filter(t => t.id !== topic.id);
    } else {
      newIds = [...value, topic.id];
      newTopics = [...selectedTopics, topic];
    }
    setSelectedTopics(newTopics);
    onChange(newIds);
  }, [value, selectedTopics, onChange]);

  const removeTopic = useCallback((topicId) => {
    onChange(value.filter(id => id !== topicId));
    setSelectedTopics(prev => prev.filter(t => t.id !== topicId));
  }, [value, onChange]);

  return (
    <div className="exam-topic-selector" ref={dropdownRef}>
      <label className="form-label ets-label">
        <BookOpen size={14} style={{ marginRight: 4 }} />
        Темы экзамена
      </label>

      {/* Selected topics chips */}
      {selectedTopics.length > 0 && (
        <div className="ets-chips">
          {selectedTopics.map(t => (
            <span key={t.id} className="ets-chip">
              {t.task_number && <span className="ets-chip-num">{t.task_number}</span>}
              <span className="ets-chip-name">{t.name}</span>
              <button
                type="button"
                className="ets-chip-remove"
                onClick={() => removeTopic(t.id)}
              >
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Toggle button */}
      <button
        type="button"
        className={`ets-toggle ${open ? 'open' : ''}`}
        onClick={() => setOpen(!open)}
      >
        <span className="ets-toggle-text">
          {value.length > 0
            ? `Выбрано тем: ${value.length}`
            : 'Привязать к темам экзамена'}
        </span>
        <ChevronDown size={16} className={`ets-toggle-icon ${open ? 'rotated' : ''}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="ets-dropdown">
          {/* Filters row */}
          <div className="ets-filters">
            <select
              className="ets-select"
              value={selectedExamType}
              onChange={e => {
                setSelectedExamType(e.target.value);
                setSelectedSubjectId('');
              }}
            >
              {examTypes.map(et => (
                <option key={et.code} value={et.code}>{et.name}</option>
              ))}
            </select>
            <select
              className="ets-select"
              value={selectedSubjectId}
              onChange={e => setSelectedSubjectId(e.target.value)}
            >
              <option value="">Все предметы</option>
              {subjects.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          {/* Search */}
          <div className="ets-search-wrap">
            <Search size={14} className="ets-search-icon" />
            <input
              className="ets-search"
              placeholder="Поиск темы..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              autoFocus
            />
          </div>

          {/* Topics list */}
          <div className="ets-list">
            {loading && (
              <div className="ets-loading">Загрузка...</div>
            )}
            {!loading && topics.length === 0 && selectedSubjectId && (
              <div className="ets-empty">Темы не найдены</div>
            )}
            {!loading && !selectedSubjectId && !search && (
              <div className="ets-empty">Выберите предмет или введите запрос</div>
            )}
            {!loading && topics.map(topic => {
              const isSelected = value.includes(topic.id);
              return (
                <button
                  key={topic.id}
                  type="button"
                  className={`ets-option ${isSelected ? 'selected' : ''}`}
                  onClick={() => toggleTopic(topic)}
                >
                  <span className={`ets-check ${isSelected ? 'visible' : ''}`}>
                    <Check size={14} />
                  </span>
                  <span className="ets-option-info">
                    {topic.task_number && (
                      <span className="ets-option-num">{topic.task_number}</span>
                    )}
                    <span className="ets-option-name">{topic.name}</span>
                    <span className="ets-option-meta">
                      {topic.subject_name} / {topic.section_name}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExamTopicSelector;
