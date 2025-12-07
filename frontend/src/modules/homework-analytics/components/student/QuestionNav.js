import React from 'react';

const QuestionNav = ({ questions = [], currentIndex = 0, answers = {}, onSelect }) => {
  const getStatus = (question, index) => {
    if (index === currentIndex) return 'current';
    const value = answers[question.id];
    if (value == null) return 'pending';
    if (question.question_type === 'TEXT') {
      return value?.trim?.() ? 'answered' : 'pending';
    }
    if (question.question_type === 'SINGLE_CHOICE') {
      return value ? 'answered' : 'pending';
    }
    if (question.question_type === 'MULTIPLE_CHOICE' || question.question_type === 'MULTI_CHOICE') {
      return Array.isArray(value) && value.length ? 'answered' : 'pending';
    }
    if (question.question_type === 'LISTENING') {
      const answered = Object.values(value || {}).some((answer) => Boolean(answer?.trim?.()));
      return answered ? 'answered' : 'pending';
    }
    if (question.question_type === 'MATCHING') {
      const pairs = question.config?.pairs || [];
      const keys = Object.keys(value || {});
      return keys.length === pairs.length ? 'answered' : 'pending';
    }
    if (question.question_type === 'DRAG_DROP') {
      return (value || []).length ? 'answered' : 'pending';
    }
    if (question.question_type === 'FILL_BLANKS') {
      const list = Array.isArray(value) ? value : [];
      return list.every((answer) => Boolean(answer?.trim?.())) ? 'answered' : 'pending';
    }
    if (question.question_type === 'HOTSPOT') {
      return Array.isArray(value) && value.length ? 'answered' : 'pending';
    }
    return 'pending';
  };

  return (
    <div className="ht-question-nav">
      {questions.map((question, index) => {
        const status = getStatus(question, index);
        return (
          <button
            key={question.id}
            type="button"
            className={`ht-question-nav-item ${status}`}
            onClick={() => onSelect?.(index)}
          >
            {index + 1}
          </button>
        );
      })}
    </div>
  );
};

export default QuestionNav;
