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
 * Компонент для выбора учеников из групп.
 * Поддерживает:
 * - Выбор нескольких групп
 * - Выбор конкретных учеников в каждой группе
 * - Режим "все ученики группы" / "конкретные ученики"
 * 
 * @param {Object} props
 * @param {Array} props.value - Текущее значение: [{groupId, studentIds: [], allStudents: bool}]
 * @param {Function} props.onChange - Callback при изменении
 * @param {Array} props.groups - Список групп (опционально, иначе загружается)
 * @param {Array} props.individualStudents - Индивидуально выбранные ученики (без группы)
 * @param {Function} props.onIndividualChange - Callback для индивидуальных учеников
 */
const StudentPicker = ({
  value = [],
  onChange,
  groups: propGroups = null,
  individualStudents = [],
  onIndividualChange,
  disabled = false,
}) => {
  const normalizeId = useCallback((id) => String(id ?? ''), []);
  const toNumberId = useCallback((id) => {
    const num = Number(id);
    return Number.isFinite(num) ? num : id;
  }, []);
  const [groups, setGroups] = useState(propGroups || []);
  const [loadingGroups, setLoadingGroups] = useState(!propGroups);
  const [expandedGroups, setExpandedGroups] = useState(new Set());
  const [groupStudents, setGroupStudents] = useState({}); // {groupId: [students]}
  const [loadingStudents, setLoadingStudents] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [studentModalGroupKey, setStudentModalGroupKey] = useState(null);
  const [studentModalSearch, setStudentModalSearch] = useState('');

  // Загрузка групп
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

  // Загрузка учеников группы при раскрытии
  const loadGroupStudents = useCallback(async (groupId) => {
    const normalizedGroupId = normalizeId(groupId);
    if (groupStudents[normalizedGroupId] || loadingStudents[normalizedGroupId]) return;
    
    setLoadingStudents(prev => ({ ...prev, [normalizedGroupId]: true }));
    try {
      const res = await getGroupStudents(Number(groupId));
      const raw = res.data?.results || res.data?.students || res.data || [];
      const students = Array.isArray(raw) ? raw : [];
      setGroupStudents(prev => ({ ...prev, [normalizedGroupId]: students }));
    } catch (err) {
      console.error('Failed to load students for group', groupId, err);
      // Fallback: попробуем использовать студентов из groups
      const group = groups.find(g => normalizeId(g.id) === normalizedGroupId);
      if (group?.students) {
        setGroupStudents(prev => ({ ...prev, [normalizedGroupId]: Array.isArray(group.students) ? group.students : [] }));
      }
    } finally {
      setLoadingStudents(prev => ({ ...prev, [normalizedGroupId]: false }));
    }
  }, [groupStudents, loadingStudents, groups, normalizeId]);

  // Индекс выбранных групп и учеников
  const selectionIndex = useMemo(() => {
    const index = {};
    value.forEach(item => {
      const groupKey = normalizeId(item.groupId);
      const ids = Array.isArray(item.studentIds) ? item.studentIds : [];
      index[groupKey] = {
        allStudents: item.allStudents !== false && ids.length === 0,
        studentIds: new Set(ids.map(normalizeId)),
      };
    });
    return index;
  }, [value, normalizeId]);

  // Toggle группы
  const toggleGroup = (groupId) => {
    const normalizedGroupId = normalizeId(groupId);
    const isSelected = !!selectionIndex[normalizedGroupId];
    
    if (isSelected) {
      // Удаляем группу
      onChange(value.filter(v => normalizeId(v.groupId) !== normalizedGroupId));
    } else {
      // Добавляем группу (по умолчанию все ученики)
      onChange([...value, { groupId, allStudents: true, studentIds: [] }]);
    }
  };

  // Toggle "все ученики" / "конкретные"
  const toggleAllStudents = (groupId) => {
    const groupKey = normalizeId(groupId);
    const current = selectionIndex[groupKey];
    if (!current) return;
    
    const newValue = value.map(v => {
      if (normalizeId(v.groupId) === groupKey) {
        return { ...v, allStudents: !current.allStudents, studentIds: [] };
      }
      return v;
    });
    onChange(newValue);
  };

  const openStudentModal = (groupId) => {
    const groupKey = normalizeId(groupId);
    setStudentModalSearch('');
    setStudentModalGroupKey(groupKey);
    loadGroupStudents(groupId);
  };

  const closeStudentModal = useCallback(() => {
    setStudentModalGroupKey(null);
    setStudentModalSearch('');
  }, []);

  // Toggle конкретного ученика
  const toggleStudent = (groupId, studentId) => {
    const groupKey = normalizeId(groupId);
    const current = selectionIndex[groupKey];
    if (!current) return;
    
    const studentKey = normalizeId(studentId);
    const currentIds = new Set(current.studentIds);
    if (currentIds.has(studentKey)) {
      currentIds.delete(studentKey);
    } else {
      currentIds.add(studentKey);
    }
    
    const newValue = value.map(v => {
      if (normalizeId(v.groupId) === groupKey) {
        return { ...v, allStudents: false, studentIds: Array.from(currentIds).map(toNumberId) };
      }
      return v;
    });
    onChange(newValue);
  };

  // Развернуть/свернуть группу
  const toggleExpand = (groupId) => {
    const groupKey = normalizeId(groupId);
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupKey)) {
      newExpanded.delete(groupKey);
      if (studentModalGroupKey === groupKey) {
        closeStudentModal();
      }
    } else {
      newExpanded.add(groupKey);
      loadGroupStudents(groupId);
    }
    setExpandedGroups(newExpanded);
  };

  useEffect(() => {
    if (!studentModalGroupKey) return;

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (e) => {
      if (e.key === 'Escape') closeStudentModal();
    };

    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [studentModalGroupKey, closeStudentModal]);

  // Фильтрация групп по поиску
  const filteredGroups = useMemo(() => {
    if (!searchQuery.trim()) return groups;
    const query = searchQuery.toLowerCase();
    return groups.filter(g => String(g?.name || '').toLowerCase().includes(query));
  }, [groups, searchQuery]);

  // Подсчет выбранных
  const selectedCount = value.length;
  const studentsCount = value.reduce((acc, v) => {
    if (v.allStudents) {
      const group = groups.find(g => normalizeId(g.id) === normalizeId(v.groupId));
      return acc + (group?.students_count || group?.students?.length || 0);
    }
    return acc + (v.studentIds?.length || 0);
  }, 0);

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
    const query = studentModalSearch.trim().toLowerCase();
    if (!query) return all;
    return all.filter((s) => {
      const name = `${s?.first_name || ''} ${s?.last_name || ''}`.trim().toLowerCase();
      const email = String(s?.email || '').toLowerCase();
      return name.includes(query) || email.includes(query);
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
      {studentModalGroupKey && modalGroup && modalSelection && !modalSelection.allStudents && (
        <div className="sp-modal-backdrop" onClick={closeStudentModal} role="presentation">
          <div className="sp-modal" role="dialog" aria-modal="true" aria-label="Выбор учеников" onClick={(e) => e.stopPropagation()}>
            <div className="sp-modal-header">
              <div className="sp-modal-title">
                <div className="sp-modal-group-name">{modalGroup.name}</div>
                <div className="sp-modal-subtitle">
                  Выбрано: {modalSelection?.studentIds?.size || 0}
                </div>
              </div>
              <button type="button" className="sp-modal-close" onClick={closeStudentModal} aria-label="Закрыть" disabled={disabled}>
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
                  onChange={(e) => setStudentModalSearch(e.target.value)}
                  disabled={disabled}
                />
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
                modalStudents.map((student) => {
                  const studentKey = normalizeId(student?.id);
                  const isStudentSelected = modalSelection?.studentIds?.has(studentKey);
                  const fullName = `${student?.first_name || ''} ${student?.last_name || ''}`.trim() || student?.email;

                  return (
                    <label key={studentKey} className="sp-student-item sp-student-item-modal">
                      <input
                        type="checkbox"
                        checked={!!isStudentSelected}
                        onChange={() => toggleStudent(modalGroup.id, student?.id)}
                        disabled={disabled}
                      />
                      <span className="sp-checkbox-custom">
                        {isStudentSelected && <IconCheck size={12} />}
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

      {/* Поиск */}
      <div className="student-picker-search">
        <IconSearch size={16} />
        <input
          type="text"
          placeholder="Поиск группы..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          disabled={disabled}
        />
      </div>

      {/* Статистика */}
      <div className="student-picker-stats">
        <span className="stat-badge">
          <IconUsers size={14} />
          {selectedCount} групп
        </span>
        {studentsCount > 0 && (
          <span className="stat-badge">
            ~{studentsCount} учеников
          </span>
        )}
      </div>

      {/* Список групп */}
      <div className="student-picker-groups">
        {filteredGroups.length === 0 ? (
          <div className="student-picker-empty">
            {searchQuery ? 'Группы не найдены' : 'Нет доступных групп'}
          </div>
        ) : (
          filteredGroups.map(group => {
            const groupKey = normalizeId(group.id);
            const isSelected = !!selectionIndex[groupKey];
            const isExpanded = expandedGroups.has(groupKey);
            const selection = selectionIndex[groupKey];
            const studentsRaw = groupStudents[groupKey];
            const students = Array.isArray(studentsRaw) ? studentsRaw : [];
            const isLoadingStudents = !!loadingStudents[groupKey];

            return (
              <div key={group.id} className={`sp-group ${isSelected ? 'selected' : ''}`}>
                {/* Заголовок группы */}
                <div className="sp-group-header">
                  <label className="sp-group-checkbox">
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
                    <button
                      type="button"
                      className="sp-expand-btn"
                      onClick={() => toggleExpand(group.id)}
                      disabled={disabled}
                    >
                      <span className={isExpanded ? 'rotated' : ''}>
                        <IconChevronDown size={16} />
                      </span>
                    </button>
                  )}
                </div>

                {/* Опции выбора учеников (когда развернуто) */}
                {isSelected && isExpanded && (
                  <div className="sp-group-students">
                    {/* Переключатель "все / конкретные" */}
                    <div className="sp-mode-toggle">
                      <button
                        type="button"
                        className={`sp-mode-btn ${selection?.allStudents ? 'active' : ''}`}
                        onClick={() => {
                          if (!selection?.allStudents) {
                            closeStudentModal();
                            toggleAllStudents(group.id);
                          }
                        }}
                        disabled={disabled}
                      >
                        Все ученики
                      </button>
                      <button
                        type="button"
                        className={`sp-mode-btn ${!selection?.allStudents ? 'active' : ''}`}
                        onClick={() => {
                          if (selection?.allStudents) {
                            toggleAllStudents(group.id);
                          }
                          openStudentModal(group.id);
                        }}
                        disabled={disabled}
                      >
                        Выбрать
                      </button>
                    </div>

                    {selection?.allStudents && (
                      <div className="sp-students-hint">
                        Сейчас выбраны все ученики. Переключитесь на «Выбрать», чтобы отметить конкретных.
                      </div>
                    )}

                    {selection?.allStudents ? (
                      <div className="sp-students-list is-readonly">
                        {isLoadingStudents ? (
                          <div className="sp-loading-students">Загрузка...</div>
                        ) : students.length === 0 ? (
                          <div className="sp-no-students">Нет учеников в группе</div>
                        ) : (
                          students.map(student => {
                            const studentKey = normalizeId(student?.id);
                            const fullName = `${student?.first_name || ''} ${student?.last_name || ''}`.trim() || student?.email;

                            return (
                              <label key={studentKey} className="sp-student-item">
                                <input
                                  type="checkbox"
                                  checked={false}
                                  onChange={() => {}}
                                  disabled
                                />
                                <span className="sp-checkbox-custom small" />
                                <span className="sp-student-name">{fullName}</span>
                              </label>
                            );
                          })
                        )}
                      </div>
                    ) : (
                      <div className="sp-custom-summary">
                        <div className="sp-custom-summary-text">
                          Выбрано учеников: {selection?.studentIds?.size || 0}
                        </div>
                        <button
                          type="button"
                          className="sp-custom-summary-btn"
                          onClick={() => openStudentModal(group.id)}
                          disabled={disabled}
                        >
                          Открыть список
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default StudentPicker;
