import React from 'react';

/**
 * Компонент редактирования вопроса типа FILE_UPLOAD для учителей.
 * Позволяет настроить допустимые типы файлов, максимальный размер и инструкции.
 */
const FileUploadQuestion = ({ question, onChange }) => {
  const { config = {} } = question;

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    onChange({ ...question, config: nextConfig });
  };

  // Текущие значения с defaults
  const allowedTypes = config.allowedTypes || ['image', 'document'];
  const maxFiles = config.maxFiles || 1;
  const maxSizeMB = config.maxSizeMB || 10;
  const instructions = config.instructions || '';

  const toggleAllowedType = (type) => {
    let newTypes;
    if (allowedTypes.includes(type)) {
      newTypes = allowedTypes.filter(t => t !== type);
      // Нельзя убрать все типы
      if (newTypes.length === 0) {
        newTypes = [type === 'image' ? 'document' : 'image'];
      }
    } else {
      newTypes = [...allowedTypes, type];
    }
    updateConfig({ allowedTypes: newTypes });
  };

  return (
    <div className="hc-question-editor">
      <div className="form-group">
        <label className="form-label">Разрешенные типы файлов</label>
        <div className="gm-checkbox-group" data-tour="q-file-types" style={{ display: 'flex', gap: '16px' }}>
          <label className="gm-checkbox-label">
            <input
              type="checkbox"
              checked={allowedTypes.includes('image')}
              onChange={() => toggleAllowedType('image')}
            />
            <span className="gm-checkbox-text">Изображения (JPG, PNG, GIF)</span>
          </label>
          <label className="gm-checkbox-label">
            <input
              type="checkbox"
              checked={allowedTypes.includes('document')}
              onChange={() => toggleAllowedType('document')}
            />
            <span className="gm-checkbox-text">Документы (PDF, Word, Excel)</span>
          </label>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Максимальное количество файлов</label>
        <select
          className="form-select"
          data-tour="q-file-max-count"
          value={maxFiles}
          onChange={(e) => updateConfig({ maxFiles: parseInt(e.target.value, 10) })}
        >
          <option value={1}>1 файл</option>
          <option value={2}>2 файла</option>
          <option value={3}>3 файла</option>
          <option value={5}>5 файлов</option>
        </select>
      </div>

      <div className="form-group">
        <label className="form-label">Максимальный размер файла (MB)</label>
        <select
          className="form-select"
          data-tour="q-file-max-size"
          value={maxSizeMB}
          onChange={(e) => updateConfig({ maxSizeMB: parseInt(e.target.value, 10) })}
        >
          <option value={5}>5 MB</option>
          <option value={10}>10 MB</option>
          <option value={25}>25 MB</option>
          <option value={50}>50 MB</option>
        </select>
      </div>

      <div className="form-group" data-tour="q-file-instructions">
        <label className="form-label">Инструкции для ученика</label>
        <textarea
          className="form-textarea"
          rows={2}
          value={instructions}
          onChange={(e) => updateConfig({ instructions: e.target.value })}
          placeholder="Например: Загрузите фото выполненного задания"
        />
        <small className="form-hint">Отобразится над полем загрузки файла</small>
      </div>

      <div className="hc-info-box" style={{ 
        padding: '12px', 
        background: 'var(--bg-secondary, #f9fafb)', 
        borderRadius: '8px',
        fontSize: '13px',
        color: 'var(--text-secondary, #6b7280)'
      }}>
        Ученик сможет загрузить файл с компьютера, перетащить его в поле загрузки, 
        или вставить изображение из буфера обмена (Ctrl+V).
      </div>
    </div>
  );
};

export default FileUploadQuestion;
