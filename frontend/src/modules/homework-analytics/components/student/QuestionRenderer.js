import React from 'react';
import MediaPreview from '../shared/MediaPreview';
import CodeQuestionRenderer from './CodeQuestionRenderer';

const QuestionRenderer = ({ question, answer, onChange, disabled = false }) => {
  if (!question) return null;

  const { question_type: type, config = {} } = question;

  const handleTextChange = (event) => onChange(event.target.value);

  const handleSingleChoice = (optionId) => onChange(optionId);

  const handleMultipleChoice = (optionId) => {
    const list = Array.isArray(answer) ? [...answer] : [];
    if (list.includes(optionId)) {
      onChange(list.filter((value) => value !== optionId));
    } else {
      onChange([...list, optionId]);
    }
  };

  const handleListeningAnswer = (subId, value) => {
    const next = { ...(answer || {}) };
    next[subId] = value;
    onChange(next);
  };

  const handleMatching = (pairId, rightValue) => {
    const next = { ...(answer || {}) };
    next[pairId] = rightValue;
    onChange(next);
  };

  const handleDragDropMove = (itemId, direction) => {
    const current = Array.isArray(answer)
      ? [...answer]
      : (config.items || []).map((item) => item.id);
    const index = current.indexOf(itemId);
    if (index < 0) return;
    const target = index + direction;
    if (target < 0 || target >= current.length) return;
    const next = [...current];
    const [moved] = next.splice(index, 1);
    next.splice(target, 0, moved);
    onChange(next);
  };

  const handleFillBlank = (blankIndex, value) => {
    const next = Array.isArray(answer) ? [...answer] : (config.answers || []).map(() => '');
    next[blankIndex] = value;
    onChange(next);
  };

  const handleHotspotToggle = (hotspotId) => {
    const current = Array.isArray(answer) ? [...answer] : [];
    if (current.includes(hotspotId)) {
      onChange(current.filter((id) => id !== hotspotId));
    } else {
      onChange([...current, hotspotId]);
    }
  };

  if (type === 'TEXT') {
    const isLong = config.answerLength === 'long';
    if (isLong) {
      return (
        <textarea
          className="form-textarea"
          rows={4}
          value={answer || ''}
          onChange={handleTextChange}
          placeholder="Введите ответ"
            disabled={disabled}
        />
      );
    }
    return (
      <input
        className="form-input"
        value={answer || ''}
        onChange={handleTextChange}
        placeholder="Введите ответ"
          disabled={disabled}
      />
    );
  }

  if (type === 'SINGLE_CHOICE') {
    // Use question.choices (from backend with numeric IDs) instead of config.options
    const options = question.choices || config.options || [];
    return (
      <div className="ht-options ht-options-radio">
        {options.map((option) => (
          <label key={option.id} className="ht-option">
            <input
              type="radio"
              name={`single-${question.id}`}
              checked={answer === option.id}
              onChange={() => handleSingleChoice(option.id)}
                disabled={disabled}
            />
            <span>{option.text}</span>
          </label>
        ))}
      </div>
    );
  }

  if (type === 'MULTIPLE_CHOICE' || type === 'MULTI_CHOICE') {
    // Use question.choices (from backend with numeric IDs) instead of config.options
    const options = question.choices || config.options || [];
    const selected = Array.isArray(answer) ? answer : [];
    return (
      <div className="ht-options ht-options-checkbox">
        {options.map((option) => (
          <label key={option.id} className="ht-option">
            <input
              type="checkbox"
              checked={selected.includes(option.id)}
              onChange={() => handleMultipleChoice(option.id)}
                disabled={disabled}
            />
            <span>{option.text}</span>
          </label>
        ))}
      </div>
    );
  }

  if (type === 'LISTENING') {
    const subQuestions = config.subQuestions || [];
    return (
      <div className="ht-listening">
        {config.audioUrl && (
          <MediaPreview type="audio" src={config.audioUrl} alt="Аудио для прослушивания" />
        )}
        {config.prompt && <p className="ht-prompt">{config.prompt}</p>}
        <div className="ht-sub-questions">
          {subQuestions.map((subQuestion, index) => (
            <div key={subQuestion.id} className="ht-sub-question">
              <strong>Вопрос {index + 1}</strong>
              <p>{subQuestion.text}</p>
              <textarea
                className="form-textarea"
                rows={2}
                value={answer?.[subQuestion.id] || ''}
                onChange={(event) => handleListeningAnswer(subQuestion.id, event.target.value)}
                placeholder="Ответ ученика"
                  disabled={disabled}
              />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === 'MATCHING') {
    const pairs = config.pairs || [];
    const rightOptions = pairs.map((pair) => ({ id: pair.id, label: pair.right }));
    return (
      <div className="ht-matching">
        {pairs.map((pair, index) => (
          <div key={pair.id} className="ht-matching-row">
            <div className="ht-matching-left">
              <span>{index + 1}.</span>
              <span>{pair.left}</span>
            </div>
            <select
              className="form-input"
              value={answer?.[pair.id] || ''}
              onChange={(event) => handleMatching(pair.id, event.target.value)}
                disabled={disabled}
            >
              <option value="">Выберите соответствие</option>
              {rightOptions.map((option) => (
                <option key={option.id} value={option.label}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    );
  }

  if (type === 'DRAG_DROP') {
    const items = config.items || [];
    const order = Array.isArray(answer)
      ? answer
      : items.map((item) => item.id);
    const orderedItems = order
      .map((itemId) => items.find((item) => item.id === itemId))
      .filter(Boolean);
    return (
      <div className="ht-dragdrop">
        {orderedItems.map((item, index) => (
          <div key={item.id} className="ht-dragdrop-item">
            <span>{index + 1}.</span>
            <span>{item.text}</span>
            <div className="ht-inline-actions">
              <button
                type="button"
                className="gm-btn-icon"
                onClick={() => handleDragDropMove(item.id, -1)}
                disabled={index === 0}
                aria-label="Выше"
              >
                ↑
              </button>
              <button
                type="button"
                className="gm-btn-icon"
                onClick={() => handleDragDropMove(item.id, 1)}
                  disabled={index === orderedItems.length - 1 || disabled}
                aria-label="Ниже"
              >
                ↓
              </button>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (type === 'FILL_BLANKS') {
    const template = config.template || '';
    const splits = template.split(/\[___\]/g);
    const blanks = (template.match(/\[___\]/g) || []).length;
    const answersList = Array.isArray(answer)
      ? answer
      : Array.from({ length: blanks }, () => '');
    const elements = [];
    splits.forEach((part, index) => {
      elements.push(
        <span key={`part-${index}`} className="ht-text-part">
          {part}
        </span>
      );
      if (index < blanks) {
        elements.push(
          <input
            key={`blank-${index}`}
            className="form-input ht-inline-input"
            value={answersList[index] || ''}
            onChange={(event) => handleFillBlank(index, event.target.value)}
              disabled={disabled}
          />
        );
      }
    });
    return <div className="ht-fill-blanks">{elements}</div>;
  }

  if (type === 'HOTSPOT') {
    const hotspots = config.hotspots || [];
    return (
      <div className="ht-hotspot">
        {config.imageUrl && (
          <MediaPreview type="image" src={config.imageUrl} alt="Изображение для вопроса" />
        )}
        <div className="ht-hotspot-options">
          {hotspots.map((hotspot) => (
            <label key={hotspot.id} className="ht-option ht-option-hotspot">
              <input
                type="checkbox"
                checked={Array.isArray(answer) && answer.includes(hotspot.id)}
                onChange={() => handleHotspotToggle(hotspot.id)}
                  disabled={disabled}
              />
              <span>{hotspot.label || hotspot.id}</span>
            </label>
          ))}
        </div>
      </div>
    );
  }

  if (type === 'CODE') {
    return (
      <CodeQuestionRenderer
        question={question}
        answer={answer}
        onChange={onChange}
        disabled={disabled}
      />
    );
  }

  return <div>Тип вопроса пока не поддерживается.</div>;
};

export default QuestionRenderer;
