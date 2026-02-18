import React from 'react';

const DragDropQuestion = ({ question, onChange }) => {
  const { config = {} } = question;
  const items = Array.isArray(config.items) ? config.items : [];

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    const nextQuestion = { ...question, config: nextConfig };
    nextQuestion.correct_answer = nextConfig.correctOrder || [];
    onChange(nextQuestion);
  };

  const syncOrder = (nextItems) => {
    const nextOrder = nextItems.map((item) => item.id);
    updateConfig({ items: nextItems, correctOrder: nextOrder });
  };

  const addItem = () => {
    const id = `dd-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
    syncOrder([...items, { id, text: `Элемент ${items.length + 1}` }]);
  };

  const updateItemText = (id, text) => {
    const nextItems = items.map((item) =>
      item.id === id ? { ...item, text } : item
    );
    syncOrder(nextItems);
  };

  const moveItem = (id, direction) => {
    const index = items.findIndex((item) => item.id === id);
    if (index < 0) return;
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= items.length) return;
    const nextItems = [...items];
    const [moved] = nextItems.splice(index, 1);
    nextItems.splice(newIndex, 0, moved);
    syncOrder(nextItems);
  };

  const removeItem = (id) => {
    const nextItems = items.filter((item) => item.id !== id);
    syncOrder(nextItems);
  };

  return (
    <div className="hc-question-editor">
      <div className="hc-subsection" data-tour="q-dragdrop-items">
        <div className="hc-subsection-header">
          <span>Элементы ({items.length})</span>
          <button type="button" className="gm-btn-surface" onClick={addItem} data-tour="q-dragdrop-add">
            + Добавить элемент
          </button>
        </div>
        {items.length === 0 ? (
          <div className="hc-subsection-empty">Добавьте минимум два элемента.</div>
        ) : (
          <div className="hc-sublist">
            {items.map((item, index) => (
              <div key={item.id} className="hc-subitem">
                <div className="hc-subitem-header">
                  <strong>Элемент {index + 1}</strong>
                  <div className="hc-inline-actions" data-tour="q-dragdrop-reorder">
                    <button
                      type="button"
                      className="gm-btn-icon"
                      onClick={() => moveItem(item.id, -1)}
                      disabled={index === 0}
                      aria-label="Переместить вверх"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      className="gm-btn-icon"
                      onClick={() => moveItem(item.id, 1)}
                      disabled={index === items.length - 1}
                      aria-label="Переместить вниз"
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      className="gm-btn-icon"
                      onClick={() => removeItem(item.id)}
                      aria-label="Удалить элемент"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <input
                  className="form-input"
                  value={item.text}
                  onChange={(event) => updateItemText(item.id, event.target.value)}
                  placeholder="Текст элемента"
                  data-tour="q-dragdrop-item-text"
                />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="hc-preview-placeholder">
        Ученики увидят эти элементы и должны будут расставить их в правильном порядке.
      </div>
    </div>
  );
};

export default DragDropQuestion;
