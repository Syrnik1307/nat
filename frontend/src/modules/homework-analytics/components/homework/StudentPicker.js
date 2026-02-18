import React, { useState, useEffect, useMemo } from 'react';
import { getGroups } from '../../../../apiService';
import './StudentPicker.css';

/**
 * StudentPicker — clean checkbox list for selecting groups & students.
 *
 * Groups API already returns `students` array inside each group object,
 * so no separate student-loading call is needed.
 *
 * Props:
 * @param {Array}    value    - [{groupId, studentIds: [], allStudents: bool}]
 * @param {Function} onChange - called with updated value array
 * @param {Array}    groups   - group list (optional, loads via API)
 * @param {boolean}  disabled
 */
const StudentPicker = ({
  value = [],
  onChange,
  groups: propGroups = null,
  disabled = false,
}) => {
  const [groups, setGroups] = useState(propGroups || []);
  const [loadingGroups, setLoadingGroups] = useState(!propGroups);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedGroupId, setExpandedGroupId] = useState(null);

  // --- Load groups (students come embedded in each group) ---
  useEffect(() => {
    if (propGroups) { setGroups(propGroups); return; }
    let cancelled = false;
    (async () => {
      setLoadingGroups(true);
      try {
        const res = await getGroups();
        const data = res.data?.results || res.data || [];
        if (!cancelled) setGroups(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('StudentPicker: failed to load groups', err);
      } finally {
        if (!cancelled) setLoadingGroups(false);
      }
    })();
    return () => { cancelled = true; };
  }, [propGroups]);

  // --- Helper: get students array from group object ---
  const getStudentsForGroup = (groupId) => {
    const group = groups.find(g => String(g.id) === String(groupId));
    return Array.isArray(group?.students) ? group.students : [];
  };

  // --- Selection helpers ---
  const selectionMap = useMemo(() => {
    const map = {};
    value.forEach(item => {
      map[String(item.groupId)] = {
        allStudents: item.allStudents !== false && (!item.studentIds || item.studentIds.length === 0),
        studentIds: new Set((item.studentIds || []).map(String)),
      };
    });
    return map;
  }, [value]);

  const isGroupSelected = (groupId) => !!selectionMap[String(groupId)];

  const toggleGroup = (groupId) => {
    if (disabled) return;
    const key = String(groupId);
    if (selectionMap[key]) {
      onChange(value.filter(v => String(v.groupId) !== key));
      if (expandedGroupId === key) setExpandedGroupId(null);
    } else {
      onChange([...value, { groupId, allStudents: true, studentIds: [] }]);
    }
  };

  const expandGroup = (groupId) => {
    const key = String(groupId);
    setExpandedGroupId(expandedGroupId === key ? null : key);
  };

  // Toggle individual student
  const toggleStudent = (groupId, studentId) => {
    if (disabled) return;
    const groupKey = String(groupId);
    const studentKey = String(studentId);
    const current = selectionMap[groupKey];
    if (!current) return;

    const students = getStudentsForGroup(groupId);
    let newIds;

    if (current.allStudents) {
      // Switching from "all" to individual: select all except this one
      newIds = students.map(s => String(s.id)).filter(id => id !== studentKey);
    } else {
      const currentIds = new Set(current.studentIds);
      if (currentIds.has(studentKey)) {
        currentIds.delete(studentKey);
      } else {
        currentIds.add(studentKey);
      }
      newIds = Array.from(currentIds);
    }

    // If all students are selected, switch back to allStudents mode
    const allSelected = students.length > 0 && newIds.length === students.length;

    onChange(value.map(v =>
      String(v.groupId) === groupKey
        ? { ...v, allStudents: allSelected, studentIds: allSelected ? [] : newIds.map(Number) }
        : v
    ));
  };

  const isStudentSelected = (groupId, studentId) => {
    const current = selectionMap[String(groupId)];
    if (!current) return false;
    if (current.allStudents) return true;
    return current.studentIds.has(String(studentId));
  };

  const toggleSelectAllStudents = (groupId) => {
    if (disabled) return;
    const groupKey = String(groupId);
    const current = selectionMap[groupKey];
    if (!current) return;

    const students = getStudentsForGroup(groupId);
    if (students.length === 0) return;

    const allSelected = current.allStudents ||
      (students.length > 0 && students.every(s => current.studentIds.has(String(s.id))));

    onChange(value.map(v =>
      String(v.groupId) === groupKey
        ? { ...v, allStudents: !allSelected, studentIds: [] }
        : v
    ));
  };

  // --- Filter groups ---
  const filteredGroups = useMemo(() => {
    if (!searchQuery.trim()) return groups;
    const q = searchQuery.toLowerCase();
    return groups.filter(g => (g.name || '').toLowerCase().includes(q));
  }, [groups, searchQuery]);

  const selectedGroupCount = value.length;

  // --- Loading ---
  if (loadingGroups) {
    return (
      <div className="sp-root sp-loading">
        <div className="sp-spinner" />
        <span>Загрузка групп...</span>
      </div>
    );
  }

  return (
    <div className={`sp-root ${disabled ? 'sp-disabled' : ''}`}>
      {/* Search */}
      <div className="sp-search-wrap">
        <svg className="sp-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input
          type="text"
          className="sp-search"
          placeholder="Поиск группы..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          disabled={disabled}
        />
      </div>

      {/* Summary */}
      <div className="sp-summary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
          <path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
        <span>{selectedGroupCount} групп</span>
      </div>

      {/* Group list */}
      <div className="sp-group-list">
        {filteredGroups.length === 0 && (
          <div className="sp-empty">Группы не найдены</div>
        )}
        {filteredGroups.map(group => {
          const gKey = String(group.id);
          const selected = isGroupSelected(group.id);
          const expanded = expandedGroupId === gKey && selected;
          const students = getStudentsForGroup(group.id);
          const studentCount = group.students_count || students.length || 0;

          return (
            <div key={group.id} className={`sp-group ${selected ? 'sp-group--selected' : ''}`}>
              {/* Group row */}
              <div className="sp-group-row" onClick={() => toggleGroup(group.id)}>
                <div className={`sp-checkbox ${selected ? 'sp-checkbox--checked' : ''}`}>
                  {selected && (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20,6 9,17 4,12"/>
                    </svg>
                  )}
                </div>
                <span className="sp-group-name">{group.name}</span>
                <span className="sp-group-count">{studentCount} уч.</span>
                {selected && studentCount > 0 && (
                  <button
                    type="button"
                    className="sp-expand-btn"
                    onClick={e => { e.stopPropagation(); expandGroup(group.id); }}
                    title={expanded ? 'Свернуть' : 'Выбрать учеников'}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                      style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s ease' }}>
                      <polyline points="6,9 12,15 18,9"/>
                    </svg>
                  </button>
                )}
              </div>

              {/* Expanded student list */}
              {expanded && (
                <div className="sp-students">
                  {students.length === 0 ? (
                    <div className="sp-students-empty">Нет учеников в группе</div>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="sp-select-all-btn"
                        onClick={() => toggleSelectAllStudents(group.id)}
                        disabled={disabled}
                      >
                        {(selectionMap[gKey]?.allStudents ||
                          (students.length > 0 && students.every(s => selectionMap[gKey]?.studentIds?.has(String(s.id)))))
                          ? 'Снять все'
                          : 'Выбрать все'}
                      </button>
                      <div className="sp-students-list">
                        {students.map(student => {
                          const checked = isStudentSelected(group.id, student.id);
                          return (
                            <div
                              key={student.id}
                              className={`sp-student ${checked ? 'sp-student--selected' : ''}`}
                              onClick={() => toggleStudent(group.id, student.id)}
                            >
                              <div className={`sp-checkbox sp-checkbox--sm ${checked ? 'sp-checkbox--checked' : ''}`}>
                                {checked && (
                                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="20,6 9,17 4,12"/>
                                  </svg>
                                )}
                              </div>
                              <div className="sp-student-avatar">
                                {(student.first_name || '?')[0]}
                              </div>
                              <span className="sp-student-name">
                                {student.first_name} {student.last_name}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default StudentPicker;
