import React from 'react';

const clampPercent = (value) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  if (number < 0) return 0;
  if (number > 100) return 100;
  return Math.round(number * 10) / 10;
};

const HotspotQuestion = ({ question, onChange }) => {
  const { config = {} } = question;
  const hotspots = Array.isArray(config.hotspots) ? config.hotspots : [];

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    const nextQuestion = { ...question, config: nextConfig };
    nextQuestion.correct_answer = nextConfig.hotspots || [];
    onChange(nextQuestion);
  };

  const updateHotspots = (nextHotspots) => updateConfig({ hotspots: nextHotspots });

  const addHotspot = () => {
    const id = `hotspot-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
    updateHotspots([
      ...hotspots,
      {
        id,
        label: `Область ${hotspots.length + 1}`,
        x: 10,
        y: 10,
        width: 20,
        height: 20,
        isCorrect: true,
      },
    ]);
  };

  const updateHotspot = (id, patch) => {
    const nextHotspots = hotspots.map((item) =>
      item.id === id ? { ...item, ...patch } : item
    );
    updateHotspots(nextHotspots);
  };

  const removeHotspot = (id) => {
    updateHotspots(hotspots.filter((item) => item.id !== id));
  };

  return (
    <div className="hc-question-editor">
      <div className="form-group">
        <label className="form-label">Ссылка на изображение</label>
        <input
          className="form-input"
          placeholder="https://example.com/image.png"
          value={config.imageUrl || ''}
          onChange={(event) => updateConfig({ imageUrl: event.target.value })}
        />
        <small className="gm-hint">Мы добавим визуальную разметку, когда подключим react-image-annotate.</small>
      </div>

      {config.imageUrl && (
        <div className="hc-image-preview">
          <img src={config.imageUrl} alt="Предпросмотр задания" />
        </div>
      )}

      <div className="form-group">
        <label className="form-label">Попыток на ответ</label>
        <input
          className="form-input"
          type="number"
          min={1}
          value={config.maxAttempts || 1}
          onChange={(event) => updateConfig({ maxAttempts: Math.max(1, Number(event.target.value) || 1) })}
        />
      </div>

      <div className="hc-subsection">
        <div className="hc-subsection-header">
          <span>Области ({hotspots.length})</span>
          <button type="button" className="gm-btn-surface" onClick={addHotspot}>
            + Добавить область
          </button>
        </div>
        {hotspots.length === 0 ? (
          <div className="hc-subsection-empty">Добавьте область, чтобы отметить правильные зоны.</div>
        ) : (
          <div className="hc-sublist">
            {hotspots.map((hotspot, index) => (
              <div key={hotspot.id} className="hc-subitem">
                <div className="hc-subitem-header">
                  <strong>{hotspot.label || `Область ${index + 1}`}</strong>
                  <div className="hc-inline-actions">
                    <button
                      type="button"
                      className="gm-btn-icon"
                      onClick={() => removeHotspot(hotspot.id)}
                      aria-label="Удалить область"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Название</label>
                  <input
                    className="form-input"
                    value={hotspot.label || ''}
                    onChange={(event) => updateHotspot(hotspot.id, { label: event.target.value })}
                    placeholder="Например: Верхний левый сектор"
                  />
                </div>
                <div className="hc-inline-fields">
                  <div className="form-group">
                    <label className="form-label">X (в %)</label>
                    <input
                      className="form-input"
                      type="number"
                      value={hotspot.x}
                      onChange={(event) => updateHotspot(hotspot.id, { x: clampPercent(event.target.value) })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Y (в %)</label>
                    <input
                      className="form-input"
                      type="number"
                      value={hotspot.y}
                      onChange={(event) => updateHotspot(hotspot.id, { y: clampPercent(event.target.value) })}
                    />
                  </div>
                </div>
                <div className="hc-inline-fields">
                  <div className="form-group">
                    <label className="form-label">Ширина (%)</label>
                    <input
                      className="form-input"
                      type="number"
                      value={hotspot.width}
                      onChange={(event) => updateHotspot(hotspot.id, { width: clampPercent(event.target.value) })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Высота (%)</label>
                    <input
                      className="form-input"
                      type="number"
                      value={hotspot.height}
                      onChange={(event) => updateHotspot(hotspot.id, { height: clampPercent(event.target.value) })}
                    />
                  </div>
                </div>
                <label className="hc-inline-switch">
                  <input
                    type="checkbox"
                    checked={Boolean(hotspot.isCorrect)}
                    onChange={(event) => updateHotspot(hotspot.id, { isCorrect: event.target.checked })}
                  />
                  <span>Отметить как правильную область</span>
                </label>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default HotspotQuestion;
