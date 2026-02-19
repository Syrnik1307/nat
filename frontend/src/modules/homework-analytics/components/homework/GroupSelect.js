import React, { useState, useMemo } from 'react';
import './GroupSelect.css';

const getStudentsText = (count) => {
  if (count % 10 === 1 && count % 100 !== 11) return 'ученик';
  if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) return 'ученика';
  return 'учеников';
};

const GroupSelect = ({
  groups = [],
  selectedGroupIds = [],
  onChange,
  loading = false,
  error = null,
  onRetry,
}) => {
  const [search, setSearch] = useState('');

  const filteredGroups = useMemo(() => {
    if (!search.trim()) return groups;
    const query = search.toLowerCase().trim();
    return groups.filter((group) => group.name.toLowerCase().includes(query));
  }, [groups, search]);

  const handleToggleGroup = (groupId) => {
    const next = selectedGroupIds.includes(groupId)
      ? selectedGroupIds.filter((id) => id !== groupId)
      : [...selectedGroupIds, groupId];
    onChange(next);
  };

  const handleSelectAll = () => {
    if (selectedGroupIds.length === groups.length) {
      onChange([]);
    } else {
      onChange(groups.map((g) => g.id));
    }
  };

  return (
    <div className="gs-container">
      {/* Поиск */}
      <div className="gs-search-wrap">
        <svg className="gs-search-icon" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
          <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
        </svg>
        <input
          className="gs-search-input"
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Поиск групп..."
        />
        {search && (
          <button
            type="button"
            className="gs-search-clear"
            onClick={() => setSearch('')}
            aria-label="Очистить поиск"
          >
            ×
          </button>
        )}
      </div>

      {/* Выбрать все / снять все */}
      {groups.length > 1 && !loading && !error && (
        <button
          type="button"
          className="gs-select-all-btn"
          onClick={handleSelectAll}
        >
          {selectedGroupIds.length === groups.length ? 'Снять все' : 'Выбрать все'}
        </button>
      )}

      {/* Загрузка */}
      {loading && (
        <div className="gs-loading">
          <div className="gs-spinner" />
          <span>Загрузка групп...</span>
        </div>
      )}

      {/* Ошибка */}
      {error && (
        <div className="gs-error">
          <span>{error}</span>
          {onRetry && (
            <button type="button" className="gs-retry-btn" onClick={onRetry}>
              Повторить
            </button>
          )}
        </div>
      )}

      {/* Список групп */}
      {!loading && !error && (
        <div className="gs-list">
          {filteredGroups.length === 0 ? (
            <div className="gs-empty">
              {search
                ? 'Группы не найдены по запросу'
                : 'Нет доступных групп'}
            </div>
          ) : (
            filteredGroups.map((group) => {
              const checked = selectedGroupIds.includes(group.id);
              const count = group.students_count ?? group.students?.length ?? 0;

              return (
                <label
                  key={group.id}
                  className={`gs-group-item ${checked ? 'gs-group-item--selected' : ''}`}
                >
                  <span className={`gs-checkbox ${checked ? 'gs-checkbox--checked' : ''}`}>
                    {checked && (
                      <svg viewBox="0 0 12 10" fill="none" width="12" height="10">
                        <path
                          d="M1 5.5L4 8.5L11 1.5"
                          stroke="white"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </span>
                  <input
                    type="checkbox"
                    className="gs-hidden-checkbox"
                    checked={checked}
                    onChange={() => handleToggleGroup(group.id)}
                  />
                  <span className="gs-group-info">
                    <span className="gs-group-name">{group.name}</span>
                    <span className="gs-group-count">
                      ({count} {getStudentsText(count)})
                    </span>
                  </span>
                </label>
              );
            })
          )}
        </div>
      )}

      {/* Счётчик выбранных */}
      {!loading && selectedGroupIds.length > 0 && (
        <div className="gs-selected-count">
          Выбрано: {selectedGroupIds.length} из {groups.length}
        </div>
      )}
    </div>
  );
};

export default GroupSelect;
