import React from 'react';

const SingleChoiceQuestion = ({ question, onChange }) => {
  const { config = {} } = question;
  const options = Array.isArray(config.options) ? config.options : [];

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    onChange({ ...question, config: nextConfig, correct_answer: nextConfig.correctOptionId || null });
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
    const nextConfig = { ...config, options: nextOptions };
    if (config.correctOptionId === id) {
      nextConfig.correctOptionId = nextOptions[0]?.id || null;
    }
    onChange({ ...question, config: nextConfig, correct_answer: nextConfig.correctOptionId || null });
  };

  return (
    <div className="hc-question-editor">
      <div className="form-group">
        <label className="form-label">Варианты ответов</label>
        <div className="hc-question-options" data-tour="q-single-options">
          {options.map((option, index) => (
            <div key={option.id} className="hc-option-row">
              <label className="hc-option-radio">
                <input
                  type="radio"
                  name={`single-choice-${question.id}`}
                  checked={config.correctOptionId === option.id}
                  onChange={() => updateConfig({ correctOptionId: option.id })}
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
        <button type="button" className="gm-btn-surface" onClick={addOption} data-tour="q-single-add">
          + Добавить вариант
        </button>
      </div>
    </div>
  );
};

export default SingleChoiceQuestion;
