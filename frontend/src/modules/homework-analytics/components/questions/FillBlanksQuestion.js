import React, { useEffect } from 'react';

const detectBlanks = (template) => (template.match(/\[___\]/g) || []).length;

const FillBlanksQuestion = ({ question, onChange }) => {
  const { config = {} } = question;
  const answers = Array.isArray(config.answers) ? config.answers : [];
  const template = config.template || '';

  useEffect(() => {
    const blanks = detectBlanks(template);
    if (blanks !== answers.length) {
      const nextAnswers = Array.from({ length: blanks }, (_, index) => answers[index] || '');
      onChange({
        ...question,
        config: {
          ...config,
          answers: nextAnswers,
        },
        correct_answer: nextAnswers,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [template]);

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    const nextQuestion = { ...question, config: nextConfig };
    if (Array.isArray(nextConfig.answers)) {
      nextQuestion.correct_answer = nextConfig.answers;
    }
    onChange(nextQuestion);
  };

  const updateAnswer = (index, value) => {
    const nextAnswers = [...answers];
    nextAnswers[index] = value;
    updateConfig({ answers: nextAnswers });
  };

  return (
    <div className="hc-question-editor">
      <div className="form-group">
        <label className="form-label">Текст с пропусками</label>
        <textarea
          className="form-textarea"
          data-tour="q-fillblanks-template"
          rows={4}
          value={template}
          onChange={(event) => updateConfig({ template: event.target.value })}
          placeholder="Используйте [___] для обозначения пропусков"
        />
        <small className="gm-hint">Количество полей ответов обновляется автоматически при изменении шаблона.</small>
      </div>

      <div className="form-group" data-tour="q-fillblanks-settings">
        <label className="form-label">Настройки проверки</label>
        <div className="hc-inline-fields">
          <label className="hc-inline-switch">
            <input
              type="checkbox"
              checked={Boolean(config.caseSensitive)}
              onChange={(event) => updateConfig({ caseSensitive: event.target.checked })}
            />
            <span>Учитывать регистр</span>
          </label>
          <select
            className="form-input"
            value={config.matchingStrategy || 'exact'}
            onChange={(event) => updateConfig({ matchingStrategy: event.target.value })}
          >
            <option value="exact">Строгое совпадение</option>
            <option value="loose">Допускать близкие варианты</option>
          </select>
        </div>
      </div>

      {answers.length > 0 && (
        <div className="hc-subsection" data-tour="q-fillblanks-answers">
          <div className="hc-subsection-header">
            <span>Ответы ({answers.length})</span>
          </div>
          <div className="hc-sublist">
            {answers.map((answer, index) => (
              <div key={`blank-${index}`} className="hc-subitem">
                <label className="form-label">Пропуск {index + 1}</label>
                <input
                  className="form-input"
                  value={answer}
                  onChange={(event) => updateAnswer(index, event.target.value)}
                  placeholder="Правильный ответ"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FillBlanksQuestion;
