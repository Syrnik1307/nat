import React, { useState, useEffect } from 'react';

const TextQuestion = ({ question, onChange }) => {
  const { config = {} } = question;
  const [localAnswer, setLocalAnswer] = useState(config.correctAnswer || '');

  // Синхронизируем локальное состояние с props при изменении question.config
  useEffect(() => {
    setLocalAnswer(config.correctAnswer || '');
  }, [config.correctAnswer]);

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    onChange({ ...question, config: nextConfig, correct_answer: nextConfig.correctAnswer || null });
  };

  const handleAnswerChange = (e) => {
    setLocalAnswer(e.target.value);
  };

  const handleAnswerBlur = () => {
    // Обновляем parent только когда пользователь закончил вводить
    if (localAnswer !== config.correctAnswer) {
      updateConfig({ correctAnswer: localAnswer });
    }
  };

  return (
    <div className="hc-question-editor">
      <div className="form-group">
        <label className="form-label">Формат ответа</label>
        <div className="gm-tab-switch" data-tour="q-text-format">
          <button
            type="button"
            className={`gm-tab-button ${config.answerLength !== 'long' ? 'active' : ''}`}
            onClick={() => updateConfig({ answerLength: 'short' })}
          >
            Короткий
          </button>
          <button
            type="button"
            className={`gm-tab-button ${config.answerLength === 'long' ? 'active' : ''}`}
            onClick={() => updateConfig({ answerLength: 'long' })}
          >
            Развернутый
          </button>
        </div>
      </div>

      <div className="form-group" data-tour="q-text-answer">
        <label className="form-label">Правильный ответ (опционально)</label>
        <textarea
          className="form-textarea"
          rows={config.answerLength === 'long' ? 3 : 1}
          value={localAnswer}
          onChange={handleAnswerChange}
          onBlur={handleAnswerBlur}
          placeholder="Эталонный ответ для автопроверки"
        />
      </div>
    </div>
  );
};

export default TextQuestion;
