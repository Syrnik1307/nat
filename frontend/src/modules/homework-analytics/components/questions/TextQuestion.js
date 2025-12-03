import React from 'react';
import FileUploader from './FileUploader';

const TextQuestion = ({ question, onChange }) => {
  const { config = {} } = question;

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    onChange({ ...question, config: nextConfig, correct_answer: nextConfig.correctAnswer || null });
  };

  return (
    <div className="hc-question-editor">
      <div className="form-group">
        <label className="form-label">Изображение к вопросу (опционально)</label>
        <small className="gm-hint">Прикрепите картинку, если вопрос нужно задать визуально (JPG, PNG, GIF, WebP, до 50 МБ)</small>
        <FileUploader
          fileType="image"
          currentUrl={config.imageUrl || ''}
          onUploadSuccess={(url) => updateConfig({ imageUrl: url })}
          accept="image/*"
        />
      </div>

      {config.imageUrl && (
        <div className="hc-image-preview">
          <img src={config.imageUrl} alt="Изображение вопроса" />
        </div>
      )}

      <div className="form-group">
        <label className="form-label">Формат ответа</label>
        <div className="gm-tab-switch">
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

      <div className="form-group">
        <label className="form-label">Правильный ответ (опционально)</label>
        <textarea
          className="form-textarea"
          rows={config.answerLength === 'long' ? 4 : 2}
          value={config.correctAnswer || ''}
          onChange={(event) => updateConfig({ correctAnswer: event.target.value })}
          placeholder="Добавьте эталонный ответ для автопроверки"
        />
      </div>
    </div>
  );
};

export default TextQuestion;
