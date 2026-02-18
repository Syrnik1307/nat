import React from 'react';

const MultipleChoiceQuestion = ({ question, onChange }) => {
  const { config = {} } = question;
  const options = Array.isArray(config.options) ? config.options : [];
  const selected = Array.isArray(config.correctOptionIds) ? config.correctOptionIds : [];

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    onChange({ ...question, config: nextConfig, correct_answer: nextConfig.correctOptionIds || [] });
  };

  const toggleCorrect = (id) => {
    const isChecked = selected.includes(id);
    const nextCorrect = isChecked ? selected.filter((item) => item !== id) : [...selected, id];
    updateConfig({ correctOptionIds: nextCorrect });
  };

  const updateOptionText = (id, text) => {
    const nextOptions = options.map((option) =>
      option.id === id ? { ...option, text } : option
    );
    updateConfig({ options: nextOptions });
  };

  const addOption = () => {
    const id = `opt-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
    updateConfig({
      options: [...options, { id, text: `Вариант ${options.length + 1}` }],
    });
  };

  const removeOption = (id) => {
    const nextOptions = options.filter((option) => option.id !== id);
    const nextCorrect = selected.filter((item) => item !== id);
    updateConfig({ options: nextOptions, correctOptionIds: nextCorrect });
  };

  return (
    <div className="hc-question-editor">
      <div className="form-group">
        <label className="form-label">Варианты ответов</label>
        <div className="hc-question-options" data-tour="q-multi-options">
          {options.map((option, index) => (
            <div key={option.id} className="hc-option-row">
              <label className="hc-option-checkbox">
                <input
                  type="checkbox"
                  checked={selected.includes(option.id)}
                  onChange={() => toggleCorrect(option.id)}
                />
                <span>Правильный</span>
              </label>
              <input
                className="form-input"
                value={option.text}
                onChange={(event) => updateOptionText(option.id, event.target.value)}
                placeholder={`Вариант ${index + 1}`}
              />
              <button
                type="button"
                className="gm-btn-icon"
                onClick={() => removeOption(option.id)}
                disabled={options.length <= 2}
                aria-label="Удалить вариант"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        <button type="button" className="gm-btn-surface" onClick={addOption} data-tour="q-multi-add">
          + Добавить вариант
        </button>
      </div>
    </div>
  );
};

export default MultipleChoiceQuestion;
