import React from 'react';

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
};

const TeacherComments = ({ comments }) => {
  if (!comments || comments.length === 0) return null;

  return (
    <div className="pd-section">
      <div className="pd-section-title">Заметки от преподавателя</div>
      <div className="pd-comments">
        {comments.map((c) => (
          <div className="pd-comment" key={c.id}>
            <p className="pd-comment-text">{c.text}</p>
            <div className="pd-comment-date">{formatDate(c.created_at)}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TeacherComments;
