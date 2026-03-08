import React from 'react';

const FinanceStub = ({ data }) => {
  if (data) {
    // Future: render actual finance data (lesson balance, payment history)
    return null;
  }

  return (
    <div className="pd-section">
      <div className="pd-section-title">Финансы</div>
      <div className="pd-stub">
        <p className="pd-stub-title">Скоро</p>
        <p className="pd-stub-desc">Баланс уроков и история оплат</p>
      </div>
    </div>
  );
};

export default FinanceStub;
