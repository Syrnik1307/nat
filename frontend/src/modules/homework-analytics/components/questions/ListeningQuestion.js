import React from 'react';
import FileUploader from './FileUploader';

const ListeningQuestion = React.memo(({ question, onChange }) => {
  const { config = {} } = question;
  const subQuestions = Array.isArray(config.subQuestions) ? config.subQuestions : [];

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    onChange({ ...question, config: nextConfig });
  };

  const updateSubQuestions = (next) => updateConfig({ subQuestions: next });

  const addSubQuestion = () => {
    const id = `listen-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
    updateSubQuestions([...subQuestions, { id, text: '', answer: '' }]);
  };

  const updateSubQuestion = (id, patch) => {
    const nextSubQuestions = subQuestions.map((item) =>
      item.id === id ? { ...item, ...patch } : item
    );
    updateSubQuestions(nextSubQuestions);
  };

  const removeSubQuestion = (id) => {
    updateSubQuestions(subQuestions.filter((item) => item.id !== id));
  };

  return (
    <div className="hc-question-editor">
      <div className="form-group">
        <label className="form-label">Аудиофайл</label>
        <FileUploader
          fileType="audio"
          currentUrl={config.audioUrl || ''}
          onUploadSuccess={(url, fileData) => updateConfig({
            audioUrl: url,
            audioFileId: fileData?.file_id || null,
          })}
          accept="audio/*"
        />
        <small className="gm-hint">Загрузите аудио (MP3, WAV, OGG, до 50 МБ)</small>
      </div>

      {config.audioUrl && (
        <div className="hc-audio-preview">
          <audio controls src={config.audioUrl}>
            Ваш браузер не поддерживает аудио.
          </audio>
        </div>
      )}

      <div className="form-group">
        <label className="form-label">Инструкция для учеников</label>
        <textarea
          className="form-textarea"
          rows={3}
          value={config.prompt || ''}
          onChange={(event) => updateConfig({ prompt: event.target.value })}
          placeholder="Например: Послушайте аудио и ответьте на вопросы."
        />
      </div>

      <div className="hc-subsection">
        <div className="hc-subsection-header">
          <span>Подвопросы ({subQuestions.length})</span>
          <button type="button" className="gm-btn-surface" onClick={addSubQuestion}>
            + Добавить подвопрос
          </button>
        </div>
        {subQuestions.length === 0 ? (
          <div className="hc-subsection-empty">Добавьте первый подвопрос.</div>
        ) : (
          <div className="hc-sublist">
            {subQuestions.map((item, index) => (
              <div key={item.id} className="hc-subitem">
                <div className="hc-subitem-header">
                  <strong>Вопрос {index + 1}</strong>
                  <button
                    type="button"
                    className="gm-btn-icon"
                    onClick={() => removeSubQuestion(item.id)}
                    aria-label="Удалить подвопрос"
                  >
                    ✕
                  </button>
                </div>
                <div className="form-group">
                  <label className="form-label">Формулировка</label>
                  <textarea
                    className="form-textarea"
                    rows={2}
                    value={item.text}
                    onChange={(event) => updateSubQuestion(item.id, { text: event.target.value })}
                    placeholder="Введите текст вопроса"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Правильный ответ</label>
                  <input
                    className="form-input"
                    value={item.answer || ''}
                    onChange={(event) => updateSubQuestion(item.id, { answer: event.target.value })}
                    placeholder="Введите ответ"
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  return prevProps.question.id === nextProps.question.id &&
         JSON.stringify(prevProps.question.config) === JSON.stringify(nextProps.question.config) &&
         prevProps.question.question_text === nextProps.question.question_text;
});

export default ListeningQuestion;
