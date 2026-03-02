import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { getGroupStudents, getGroups } from '../../../../apiService';
import './StudentPicker.css';

// SVG Icons
const IconCheck = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20,6 9,17 4,12"/>
  </svg>
);

const IconUsers = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const IconSearch = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/>
    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);

const IconChevronDown = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6,9 12,15 18,9"/>
  </svg>
);

const IconX = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

/**
 * StudentPicker v3 — Modal-first design.
 * 
 * Compact trigger button in sidebar, full group list opens in a modal.
 * This prevents layout overflow issues regardless of how many groups exist.
 */
const StudentPicker = ({
  value = [],
  onChange,
  groups: propGroups = null,
  disabled = false,
}) => {
  const normalizeId = useCallback((id) => String(id ?? ''), []);
  const toNumberId = useCallback((id) => {
    const num = Number(id);
    return Number.isFinite(num) ? num : id;
  }, []);

  const [groups, setGroups] = useState(propGroups || []);
  const [loadingGroups, setLoadingGroups] = useState(!propGroups);
  const [groupStudents, setGroupStudents] = useState({});
  const [loadingStudents, setLoadingStudents] = useState({});

  // Modal states
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [groupSearchQuery, setGroupSearchQuery] = useState('');
  const [studentModalGroupKey, setStudentModalGroupKey] = useState(null);
  const [studentModalSearch, setStudentModalSearch] = useState('');

  // Load groups
  useEffect(() => {
    if (propGroups) {
      setGroups(propGroups);
      return;
    }
    const loadGroups = async () => {
      setLoadingGroups(true);
      try {
        const res = await getGroups();
        const data = res.data?.results || res.data || [];
        setGroups(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Failed to load groups:', err);
      } finally {
        setLoadingGroups(false);
      }
    };
    loadGroups();
  }, [propGroups]);

  // Load students for a group
  const loadGroupStudents = useCallback(async (groupId) => {
    const gid = normalizeId(groupId);
    if (groupStudents[gid] || loadingStudents[gid]) return;
    setLoadingStudents(prev => ({ ...prev, [gid]: true }));
    try {
      const res = await getGroupStudents(Number(groupId));
      const raw = res.data?.results || res.data?.students || res.data || [];
      setGroupStudents(prev => ({ ...prev, [gid]: Array.isArray(raw) ? raw : [] }));
    } catch {
      const group = groups.find(g => normalizeId(g.id) === gid);
      if (group?.students) {
        setGroupStudents(prev => ({ ...prev, [gid]: Array.isArray(group.students) ? group.students : [] }));
      }
    } finally {
      setLoadingStudents(prev => ({ ...prev, [gid]: false }));
    }
  }, [groupStudents, loadingStudents, groups, normalizeId]);

  // Selection index
  const selectionIndex = useMemo(() => {
    const index = {};
    value.forEach(item => {
      const gk = normalizeId(item.groupId);
      const ids = Array.isArray(item.studentIds) ? item.studentIds : [];
      index[gk] = {
        allStudents: item.allStudents !== false && ids.length === 0,
        studentIds: new Set(ids.map(normalizeId)),
      };
    });
    return index;
  }, [value, normalizeId]);

  // Toggle group
  const toggleGroup = useCallback((groupId) => {
    const gid = normalizeId(groupId);
    const isSelected = !!selectionIndex[gid];
    if (isSelected) {
      onChange(value.filter(v => normalizeId(v.groupId) !== gid));
    } else {
      onChange([...value, { groupId, allStudents: true, studentIds: [] }]);
    }
  }, [value, onChange, selectionIndex, normalizeId]);

  // Toggle all students for group
  const toggleAllStudents = useCallback((groupId) => {
    const gk = normalizeId(groupId);
    const current = selectionIndex[gk];
    if (!current) return;
    onChange(value.map(v =>
      normalizeId(v.groupId) === gk
        ? { ...v, allStudents: !current.allStudents, studentIds: [] }
        : v
    ));
  }, [value, onChange, selectionIndex, normalizeId]);

  // Toggle single student
  const toggleStudent = useCallback((groupId, studentId) => {
    const gk = normalizeId(groupId);
    const current = selectionIndex[gk];
    if (!current) return;
    const sk = normalizeId(studentId);
    const ids = new Set(current.studentIds);
    if (ids.has(sk)) ids.delete(sk); else ids.add(sk);
    onChange(value.map(v =>
      normalizeId(v.groupId) === gk
        ? { ...v, allStudents: false, studentIds: Array.from(ids).map(toNumberId) }
        : v
    ));
  }, [value, onChange, selectionIndex, normalizeId, toNumberId]);

  // Student modal
  const openStudentModal = useCallback((groupId) => {
    setStudentModalSearch('');
    setStudentModalGroupKey(normalizeId(groupId));
    loadGroupStudents(groupId);
  }, [normalizeId, loadGroupStudents]);

  const closeStudentModal = useCallback(() => {
    setStudentModalGroupKey(null);
    setStudentModalSearch('');
  }, []);

  // Group modal
  const openGroupModal = useCallback(() => {
    setGroupSearchQuery('');
    setShowGroupModal(true);
  }, []);

  const closeGroupModal = useCallback(() => {
    setShowGroupModal(false);
    setGroupSearchQuery('');
  }, []);

  // Lock body scroll when modal open
  useEffect(() => {
    const isOpen = showGroupModal || studentModalGroupKey;
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e) => {
      if (e.key === 'Escape') {
        if (studentModalGroupKey) closeStudentModal();
        else closeGroupModal();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener('keydown', onKey);
    };
  }, [showGroupModal, studentModalGroupKey, closeStudentModal, closeGroupModal]);

  // Filtered groups
  const filteredGroups = useMemo(() => {
    if (!groupSearchQuery.trim()) return groups;
    const q = groupSearchQuery.toLowerCase();
    return groups.filter(g => String(g?.name || '').toLowerCase().includes(q));
  }, [groups, groupSearchQuery]);

  // Counts
  const selectedCount = value.length;
  const studentsCount = value.reduce((acc, v) => {
    if (v.allStudents) {
      const g = groups.find(gr => normalizeId(gr.id) === normalizeId(v.groupId));
      return acc + (g?.students_count || g?.students?.length || 0);
    }
    return acc + (v.studentIds?.length || 0);
  }, 0);

  // Selected group names
  const selectedNames = useMemo(() => {
    return value.map(v => {
      const g = groups.find(gr => normalizeId(gr.id) === normalizeId(v.groupId));
      return g?.name || `Группа ${v.groupId}`;
    });
  }, [value, groups, normalizeId]);

  // Student modal data
  const modalGroup = useMemo(() => {
    if (!studentModalGroupKey) return null;
    return groups.find(g => normalizeId(g.id) === studentModalGroupKey) || null;
  }, [studentModalGroupKey, groups, normalizeId]);

  const modalSelection = useMemo(() => {
    if (!studentModalGroupKey) return null;
    return selectionIndex[studentModalGroupKey] || null;
  }, [studentModalGroupKey, selectionIndex]);

  const modalStudents = useMemo(() => {
    if (!studentModalGroupKey) return [];
    const raw = groupStudents[studentModalGroupKey];
    const all = Array.isArray(raw) ? raw : [];
    const q = studentModalSearch.trim().toLowerCase();
    if (!q) return all;
    return all.filter(s => {
      const name = `${s?.first_name || ''} ${s?.last_name || ''}`.trim().toLowerCase();
      return name.includes(q) || String(s?.email || '').toLowerCase().includes(q);
    });
  }, [studentModalGroupKey, groupStudents, studentModalSearch]);

  if (loadingGroups) {
    return (
      <div className="student-picker loading">
        <div className="student-picker-spinner" />
        <span>Загрузка групп...</span>
      </div>
    );
  }

  return (
    <div className={`student-picker ${disabled ? 'disabled' : ''}`}>
      {/* ===== COMPACT TRIGGER ===== */}
      <button
        type="button"
        className="sp-trigger"
        onClick={disabled ? undefined : openGroupModal}
        disabled={disabled}
      >
        <div className="sp-trigger-left">
          <IconUsers size={16} />
          <div className="sp-trigger-text">
            {selectedCount === 0 ? (
              <span className="sp-trigger-placeholder">Выберите группы</span>
            ) : (
              <span className="sp-trigger-value">
                {selectedCount} {selectedCount === 1 ? 'группа' : selectedCount < 5 ? 'группы' : 'групп'}
                {studentsCount > 0 && <span className="sp-trigger-students"> (~{studentsCount} уч.)</span>}
              </span>
            )}
          </div>
        </div>
        <IconChevronDown size={16} />
      </button>

      {/* Selected groups badges */}
      {selectedNames.length > 0 && (
        <div className="sp-selected-badges">
          {selectedNames.map((name, i) => (
            <span key={i} className="sp-badge">
              <span className="sp-badge-text">{name}</span>
              <button
                type="button"
                className="sp-badge-remove"
                onClick={(e) => {
                  e.stopPropagation();
                  if (!disabled) toggleGroup(value[i].groupId);
                }}
              >
                <IconX size={10} />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* ===== GROUP SELECTION MODAL ===== */}
      {showGroupModal && (
        <div className="sp-modal-backdrop" onClick={closeGroupModal} role="presentation">
          <div className="sp-modal sp-modal--groups" role="dialog" aria-modal="true" onClick={e => e.stopPropagation()}>
            <div className="sp-modal-header">
              <div className="sp-modal-title">
                <div className="sp-modal-group-name">Выбор групп</div>
                <div className="sp-modal-subtitle">
                  Выбрано: {selectedCount} групп, ~{studentsCount} учеников
                </div>
              </div>
              <button type="button" className="sp-modal-close" onClick={closeGroupModal}>
                <IconX size={18} />
              </button>
            </div>

            <div className="sp-modal-toolbar">
              <div className="sp-modal-search">
                <IconSearch size={16} />
                <input
                  type="text"
                  placeholder="Поиск группы..."
                  value={groupSearchQuery}
                  onChange={e => setGroupSearchQuery(e.target.value)}
                  autoFocus
                />
                {groupSearchQuery && (
                  <button type="button" className="sp-modal-search-clear" onClick={() => setGroupSearchQuery('')}>
                    <IconX size={14} />
                  </button>
                )}
              </div>
              <button type="button" className="sp-modal-done" onClick={closeGroupModal}>
                Готово
              </button>
            </div>

            <div className="sp-modal-list sp-modal-groups-list">
              {filteredGroups.length === 0 ? (
                <div className="sp-no-students">
                  {groupSearchQuery ? 'Группы не найдены' : 'Нет доступных групп'}
                </div>
              ) : (
                filteredGroups.map(group => {
                  const gk = normalizeId(group.id);
                  const isSelected = !!selectionIndex[gk];
                  const sel = selectionIndex[gk];

                  return (
                    <div key={group.id} className={`sp-group-row ${isSelected ? 'selected' : ''}`}>
                      <label className="sp-group-row-main">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleGroup(group.id)}
                          disabled={disabled}
                        />
                        <span className="sp-checkbox-custom">
                          {isSelected && <IconCheck size={12} />}
                        </span>
                        <span className="sp-group-name">{group.name}</span>
                        <span className="sp-group-count">
                          {group.students_count || group.students?.length || 0} уч.
                        </span>
                      </label>
                      
                      {isSelected && (
                        <div className="sp-group-row-actions">
                          <div className="sp-mode-toggle">
                            <button
                              type="button"
                              className={`sp-mode-btn ${sel?.allStudents ? 'active' : ''}`}
                              onClick={() => {
                                if (!sel?.allStudents) {
                                  closeStudentModal();
                                  toggleAllStudents(group.id);
                                }
                              }}
                            >
                              Все ученики
                            </button>
                            <button
                              type="button"
                              className={`sp-mode-btn ${!sel?.allStudents ? 'active' : ''}`}
                              onClick={() => {
                                if (sel?.allStudents) toggleAllStudents(group.id);
                                openStudentModal(group.id);
                              }}
                            >
                              Выбрать
                            </button>
                          </div>
                          {!sel?.allStudents && (
                            <span className="sp-group-row-selected-count">
                              Выбрано: {sel?.studentIds?.size || 0}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* ===== STUDENT SELECTION MODAL ===== */}
      {studentModalGroupKey && modalGroup && modalSelection && !modalSelection.allStudents && (
        <div className="sp-modal-backdrop" onClick={closeStudentModal} role="presentation">
          <div className="sp-modal" role="dialog" aria-modal="true" onClick={e => e.stopPropagation()}>
            <div className="sp-modal-header">
              <div className="sp-modal-title">
                <div className="sp-modal-group-name">{modalGroup.name}</div>
                <div className="sp-modal-subtitle">
                  Выбрано: {modalSelection?.studentIds?.size || 0}
                </div>
              </div>
              <button type="button" className="sp-modal-close" onClick={closeStudentModal} disabled={disabled}>
                <IconX size={18} />
              </button>
            </div>

            <div className="sp-modal-toolbar">
              <div className="sp-modal-search">
                <IconSearch size={16} />
                <input
                  type="text"
                  placeholder="Поиск ученика..."
                  value={studentModalSearch}
                  onChange={e => setStudentModalSearch(e.target.value)}
                  disabled={disabled}
                />
                {studentModalSearch && (
                  <button type="button" className="sp-modal-search-clear" onClick={() => setStudentModalSearch('')} disabled={disabled}>
                    <IconX size={14} />
                  </button>
                )}
              </div>
              <button type="button" className="sp-modal-done" onClick={closeStudentModal} disabled={disabled}>
                Готово
              </button>
            </div>

            <div className="sp-modal-list">
              {loadingStudents[studentModalGroupKey] ? (
                <div className="sp-loading-students">Загрузка...</div>
              ) : modalStudents.length === 0 ? (
                <div className="sp-no-students">Нет учеников</div>
              ) : (
                modalStudents.map(student => {
                  const sk = normalizeId(student?.id);
                  const isChecked = modalSelection?.studentIds?.has(sk);
                  const fullName = `${student?.first_name || ''} ${student?.last_name || ''}`.trim() || student?.email;
                  return (
                    <label key={sk} className="sp-student-item sp-student-item-modal">
                      <input
                        type="checkbox"
                        checked={!!isChecked}
                        onChange={() => toggleStudent(modalGroup.id, student?.id)}
                        disabled={disabled}
                      />
                      <span className="sp-checkbox-custom">
                        {isChecked && <IconCheck size={12} />}
                      </span>
                      <span className="sp-student-name">{fullName}</span>
                    </label>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentPicker;
