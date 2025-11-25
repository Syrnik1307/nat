import React from 'react';

const MatchingQuestion = ({ question, onChange }) => {
  const { config = {} } = question;
  const pairs = Array.isArray(config.pairs) ? config.pairs : [];

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    onChange({ ...question, config: nextConfig });
  };

  const updatePairs = (nextPairs) => updateConfig({ pairs: nextPairs });

  const addPair = () => {
    const id = `pair-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
    updatePairs([...pairs, { id, left: '', right: '' }]);
  };

  const updatePair = (id, patch) => {
    const nextPairs = pairs.map((pair) =>
      pair.id === id ? { ...pair, ...patch } : pair
    );
    updatePairs(nextPairs);
  };

  const removePair = (id) => {
    updatePairs(pairs.filter((pair) => pair.id !== id));
  };

  return (
    <div className="hc-question-editor">
      <div className="hc-subsection">
        <div className="hc-subsection-header">
          <span>Пары ({pairs.length})</span>
          <button type="button" className="gm-btn-surface" onClick={addPair}>
            + Добавить пару
          </button>
        </div>
        {pairs.length === 0 ? (
          <div className="hc-subsection-empty">Добавьте пару элементов.</div>
        ) : (
          <div className="hc-sublist">
            {pairs.map((pair, index) => (
              <div key={pair.id} className="hc-subitem">
                <div className="hc-subitem-header">
                  <strong>Пара {index + 1}</strong>
                  <button
                    type="button"
                    className="gm-btn-icon"
                    onClick={() => removePair(pair.id)}
                    aria-label="Удалить пару"
                  >
                    ✕
                  </button>
                </div>
                <div className="hc-inline-fields">
                  <div className="form-group">
                    <label className="form-label">Левая колонка</label>
                    <input
                      className="form-input"
                      value={pair.left}
                      onChange={(event) => updatePair(pair.id, { left: event.target.value })}
                      placeholder="Например: Столица"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Правая колонка</label>
                    <input
                      className="form-input"
                      value={pair.right}
                      onChange={(event) => updatePair(pair.id, { right: event.target.value })}
                      placeholder="Например: Берлин"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <label className="hc-inline-switch">
        <input
          type="checkbox"
          checked={Boolean(config.shuffleRightColumn)}
          onChange={(event) => updateConfig({ shuffleRightColumn: event.target.checked })}
        />
        <span>Перемешивать правую колонку для ученика</span>
      </label>
    </div>
  );
};

export default MatchingQuestion;
