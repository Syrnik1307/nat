import React from 'react';

const KnowledgeMapStub = ({ data }) => {
  // data will be non-null when knowledge map is integrated
  if (data) {
    // Future: render actual knowledge map visualization
    return null;
  }

  return (
    <div className="pd-section">
      <div className="pd-section-title">Карта знаний</div>
      <div className="pd-stub">
        <p className="pd-stub-title">Скоро</p>
        <p className="pd-stub-desc">Визуализация прогресса по темам экзамена</p>
      </div>
    </div>
  );
};

export default KnowledgeMapStub;
